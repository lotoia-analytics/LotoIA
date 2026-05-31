# -*- coding: utf-8 -*-
from __future__ import annotations

try:
    from . import _bootstrap  # type: ignore[import-not-found]  # noqa: F401
except ImportError:
    import _bootstrap  # type: ignore[no-redef]  # noqa: F401

import json
import math
import os
import re
import random
import subprocess
import threading
import time
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd
import streamlit as st
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from lotoia.database.adapter import InstitutionalDatabaseAdapter
from lotoia.database.contest_repository import ContestRepository
from lotoia.database.database import DEFAULT_DATABASE_PATH, GeneratedGame, GenerationEvent, ImportedContest, InstitutionalOutputSignature, LotofacilOfficialHistory, ReconciliationGame, ReconciliationRun, ScientificCalibrationDecision, ScientificInstitutionalMemory, create_database, get_engine, get_session
from lotoia.data.history_export import export_historical_csv
from lotoia.data.loader import load_draws_csv
from lotoia.analytics.lotofacil_scientific_core import LotofacilScientificCore, analyze_lotofacil_history, get_scientific_generation_policy
from lotoia.analytics.scientific_calibration_engine import (
    apply_supervised_calibration,
    build_calibration_context,
    evaluate_last_batch,
    generate_recalibration_policy,
    register_calibration_decision,
    recommend_next_strategy,
)
from lotoia.governance.scientific_commander import validate_scientific_batch
from lotoia.governance.output_commander import (
    game_signature as _game_signature,
    load_batch_output_signatures,
    output_commander_validate_games,
)
from lotoia.ingestion.result_sync_service import ResultSyncService
from lotoia.experiments.hb_geometry_audit import DEFAULT_HB_GEOMETRY_DIR, run_hb_geometry_audit
from lotoia.generator.engine import generate_ranked_games
from lotoia.statistics.basic import number_frequency


BUILD_MARKER = "institutional-clean-runtime-v1"
APP_BUILD = BUILD_MARKER
PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
LOGO_PATH = PROJECT_ROOT / "assets" / "logo.png"
HB_GEOMETRY_DIR = Path(os.fspath(DEFAULT_HB_GEOMETRY_DIR))
HB_GEOMETRY_PROGRESS_FILE = HB_GEOMETRY_DIR / "hb_geometry_audit.progress.json"
HB_GEOMETRY_JSON_FILE = HB_GEOMETRY_DIR / "hb_geometry_audit.json"
HB_GEOMETRY_CSV_FILE = HB_GEOMETRY_DIR / "hb_geometry_audit.csv"
SYNC_DIAGNOSTIC_FILE = REPORTS_DIR / "institutional_sync_diagnostics.json"
DB_PATH = DEFAULT_DATABASE_PATH
MAX_INSTITUTIONAL_DEZENAS_PER_GAME = 23
HISTORICAL_TEST_TABLES = (
    "generation_events",
    "generated_games",
    "reconciliation_runs",
    "reconciliation_games",
    "reconciliation_events",
    "operational_logs",
    "reset_events",
)
PURGE_ONLY_TABLES = ("institutional_output_signatures",)

PAGE_TARGETS = {
    "Auditoria Runtime": "audit",
    "Gerar Jogos": "generation",
    "Conferir Resultados": "conference",
    "Simular Resultados": "simulation",
    "Histórico Analítico": "history_analytical",
    "Histórico Institucional": "history_institutional",
    "Limpar Históricos": "clear_histories",
    "Apagar Histórico": "delete_history",
    "Comparativos histórico": "comparative_history",
    "Análises Estratégicas": "strategies_analysis",
    "Testar Estratégias": "strategies_test",
    "Simular Estratégias": "strategies_simulation",
    "Métricas HB": "hb_metrics",
    "Cobertura estrutural": "structural_coverage",
    "Replay institucional": "institutional_replay",
    "Benchmark resumido": "summary_benchmark",
    "Estatísticas operacionais": "operational_statistics",
    "HB Geometry": "hb_geometry",
}

PAGE_LABELS = {page_id: label for label, page_id in PAGE_TARGETS.items()}


def _canonical_page_id(value: str | None) -> str:
    text_value = str(value or "").strip()
    if not text_value:
        return "generation"
    if text_value in PAGE_TARGETS:
        return PAGE_TARGETS[text_value]
    if text_value in PAGE_LABELS:
        return text_value
    normalized = text_value.casefold()
    for label, page_id in PAGE_TARGETS.items():
        if label.casefold() == normalized:
            return page_id
    return "generation"


def _canonical_page_label(value: str | None) -> str:
    return PAGE_LABELS.get(_canonical_page_id(value), "Gerar Jogos")

_JOB_LOCK = threading.Lock()
_JOB_STATE: dict[str, Any] = {
    "running": False,
    "completed": False,
    "current_scenario": "-",
    "processed_batches": 0,
    "contests_processed": 0,
    "elapsed_time": 0.0,
    "error": "",
    "result": None,
    "started_at": None,
}


def _safe_json_load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _safe_csv_load(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def _persist_official_sync_diagnostics(payload: dict[str, Any]) -> None:
    try:
        SYNC_DIAGNOSTIC_FILE.parent.mkdir(parents=True, exist_ok=True)
        SYNC_DIAGNOSTIC_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _load_official_sync_diagnostics() -> dict[str, Any]:
    return _safe_json_load(SYNC_DIAGNOSTIC_FILE)


def _mask_database_url(database_url: str) -> str:
    text = str(database_url or "").strip()
    if not text:
        return "-"
    if "@" not in text:
        return text if len(text) <= 96 else f"{text[:48]}...{text[-24:]}"
    scheme, remainder = text.split("://", maxsplit=1) if "://" in text else ("", text)
    if "@" not in remainder:
        return text if len(text) <= 96 else f"{text[:48]}...{text[-24:]}"
    credentials, host_part = remainder.split("@", maxsplit=1)
    if ":" in credentials:
        username = credentials.split(":", maxsplit=1)[0]
        masked_credentials = f"{username}:***"
    else:
        masked_credentials = "***"
    prefix = f"{scheme}://" if scheme else ""
    return f"{prefix}{masked_credentials}@{host_part}"


def _resolve_active_commit() -> str:
    for env_name in (
        "RAILWAY_GIT_COMMIT_SHA",
        "RAILWAY_GIT_COMMIT",
        "GIT_COMMIT",
        "COMMIT_SHA",
        "SOURCE_VERSION",
    ):
        value = str(os.getenv(env_name, "") or "").strip()
        if value:
            return value[:12]
    try:
        value = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return value[:12] if value else "-"
    except Exception:
        return "-"


def _apply_institutional_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.0rem; padding-bottom: 2rem; max-width: 100%; }
        section[data-testid="stMain"] > div.block-container {
            max-width: 100%;
            padding-left: 1.1rem;
            padding-right: 1.1rem;
        }
        .stApp { background: linear-gradient(180deg, #fbfdff 0%, #f2f6fb 100%); }
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #f7fbff 0%, #eef4fa 100%);
            border-right: 1px solid rgba(18, 52, 86, 0.10);
        }
        section[data-testid="stSidebar"] .block-container {
            padding-top: 0.55rem;
            padding-left: 0.8rem;
            padding-right: 0.8rem;
        }
        section[data-testid="stSidebar"] img {
            width: 96% !important;
            max-width: 340px !important;
            display: block;
            margin: -0.2rem auto 0.7rem auto;
        }
        .lotoia-sidebar-divider {
            border-top: 1px solid rgba(18, 52, 86, 0.14);
            margin: 0.6rem 0;
        }
        .lotoia-nav-hint {
            font-size: 0.84rem;
            letter-spacing: 0.07em;
            text-transform: uppercase;
            color: #7a8795;
            margin-bottom: 0.35rem;
        }
        .lotoia-sidebar-title {
            color: #123456;
            font-size: 1.18rem;
            font-weight: 800;
            letter-spacing: 0.01em;
            margin: 0.1rem 0 0.15rem 0;
        }
        .lotoia-section-title {
            font-size: 2.04rem;
            font-weight: 800;
            color: #123456;
            margin-bottom: 0.2rem;
            letter-spacing: 0.01em;
        }
        .lotoia-section-subtitle {
            font-size: 1.10rem;
            color: #5a6b7e;
            margin-bottom: 1rem;
            line-height: 1.5;
        }
        .lotoia-kpi-card {
            background: linear-gradient(180deg, #ffffff 0%, #f7fbff 100%);
            border: 1px solid rgba(18, 52, 86, 0.10);
            border-radius: 16px;
            padding: 0.95rem 1rem 0.85rem 1rem;
            box-shadow: 0 6px 22px rgba(18, 52, 86, 0.05);
            min-height: 114px;
        }
        .lotoia-kpi-label {
            color: #5a6b7e;
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            margin-bottom: 0.35rem;
        }
        .lotoia-kpi-value {
            color: #123456;
            font-size: 1.72rem;
            font-weight: 800;
            line-height: 1.1;
            margin-bottom: 0.3rem;
        }
        .lotoia-kpi-caption {
            color: #718399;
            font-size: 0.8rem;
            line-height: 1.4;
        }
        .lotoia-operational-hint {
            color: #6d7f92;
            font-size: 0.86rem;
            margin-top: -0.15rem;
            margin-bottom: 0.5rem;
        }
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid rgba(18, 52, 86, 0.10);
            border-radius: 14px;
            padding: 0.85rem 0.95rem;
            box-shadow: 0 4px 14px rgba(18, 52, 86, 0.04);
        }
        div[data-testid="stMetric"] label {
            color: #5a6b7e;
            font-size: 0.78rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }
        div[data-testid="stMetric"] [data-testid="metric-container"] {
            gap: 0.2rem;
        }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: #123456;
            font-weight: 800;
        }
        section[data-testid="stMain"] .stButton > button {
            border-radius: 12px;
            border: 1px solid rgba(18, 52, 86, 0.12);
            background: #ffffff;
            color: #123456;
            min-height: 38px;
            font-weight: 700;
            box-shadow: 0 3px 10px rgba(18, 52, 86, 0.04);
        }
        section[data-testid="stMain"] .stButton > button:hover {
            border-color: rgba(18, 52, 86, 0.20);
            background: #f8fbff;
        }
        section[data-testid="stMain"] .stButton > button[kind="primary"] {
            background: linear-gradient(180deg, #ff6666 0%, #ff4d4d 100%);
            color: #ffffff;
            border-color: rgba(255, 77, 77, 0.35);
        }
        section[data-testid="stMain"] .stButton > button[kind="primary"]:hover {
            background: linear-gradient(180deg, #ff7777 0%, #ff5f5f 100%);
            color: #ffffff;
        }
        .lotoia-table-wrap {
            padding-top: 0.15rem;
            padding-bottom: 0.15rem;
        }
        section[data-testid="stSidebar"] .stButton > button {
            min-height: 36px;
            padding-top: 0.4rem;
            padding-bottom: 0.4rem;
            border-radius: 10px;
            font-size: 1.02rem;
        }
        .lotoia-sidebar-group {
            font-size: 0.88rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #6f8195;
            margin: 0.55rem 0 0.30rem 0;
            font-weight: 900;
        }
        .lotoia-sidebar-subgroup {
            font-size: 0.80rem;
            letter-spacing: 0.10em;
            text-transform: uppercase;
            color: #8b97a8;
            margin: 0.55rem 0 0.25rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar_logo() -> None:
    if LOGO_PATH.exists():
        st.sidebar.image(str(LOGO_PATH), width=220)
    else:
        st.sidebar.empty()


def _sidebar_nav_button(label: str, target_page: str, current_page: str) -> None:
    if st.sidebar.button(label, key=f"nav_{target_page}"):
        page_id = _canonical_page_id(target_page)
        st.session_state["institutional_page_id"] = page_id
        st.rerun()


@st.cache_resource(show_spinner=False)
def _get_engine_cached():
    return get_engine(DB_PATH)


def _database_snapshot() -> dict[str, Any]:
    adapter = InstitutionalDatabaseAdapter(DB_PATH)
    engine = _get_engine_cached()
    preferred_tables = [
        "generation_events",
        "generated_games",
        "reconciliation_runs",
        "reconciliation_games",
        "reconciliation_events",
        "imported_contests",
        "lotofacil_official_history",
        "institutional_output_signatures",
        "scientific_calibration_decisions",
        "scientific_institutional_memory",
        "expansion_events",
        "operational_logs",
    ]
    latest_fields = {
        "generation_events": "created_at",
        "generated_games": "created_at",
        "reconciliation_runs": "created_at",
        "reconciliation_games": "created_at",
        "reconciliation_events": "created_at",
        "imported_contests": "contest_number",
        "lotofacil_official_history": "contest_number",
        "institutional_output_signatures": "created_at",
        "scientific_calibration_decisions": "created_at",
        "scientific_institutional_memory": "created_at",
        "expansion_events": "created_at",
        "operational_logs": "created_at",
    }
    counts: dict[str, int] = {}
    latest: dict[str, Any] = {}
    errors: dict[str, str] = {}
    query_logs: list[dict[str, Any]] = []
    table_diagnostics: dict[str, dict[str, Any]] = {}
    for table in preferred_tables:
        count_query = f'SELECT COUNT(*) FROM "{table}"'
        count_status = "ok"
        count_error = ""
        count_value = 0
        try:
            with engine.connect() as connection:
                value = connection.execute(text(count_query)).scalar()
            count_value = int(value or 0)
        except Exception as exc:
            count_status = "error"
            count_error = str(exc)
            errors[table] = count_error
        counts[table] = count_value

        latest_field = latest_fields.get(table, "created_at")
        latest_status = "ok"
        latest_error = ""
        latest_value: Any = "-"
        if latest_field in {"created_at", "contest_number"}:
            latest_query = f'SELECT MAX("{latest_field}") FROM "{table}"'
            try:
                with engine.connect() as connection:
                    value = connection.execute(text(latest_query)).scalar()
                latest_value = value if value is not None else "-"
            except Exception as exc:
                latest_status = "error"
                latest_error = str(exc)
                latest_value = "-"
        latest[table] = latest_value
        table_diagnostics[table] = {
            "table": table,
            "count_query": count_query,
            "count_status": count_status,
            "count": count_value,
            "count_error": count_error,
            "latest_field": latest_field,
            "latest_query": f'SELECT MAX("{latest_field}") FROM "{table}"' if latest_field in {"created_at", "contest_number"} else "",
            "latest_status": latest_status,
            "latest_error": latest_error,
        }
        query_logs.append(
            {
                "table": table,
                "query": count_query,
                "status": count_status,
                "count": count_value,
                "error": count_error,
            }
        )
    return {
        "backend": adapter.backend,
        "engine_url": str(engine.url),
        "database_url": adapter.database_url,
        "database_source": adapter.database_source,
        "counts": counts,
        "latest": latest,
        "tables": preferred_tables,
        "errors": errors,
        "query_logs": query_logs,
        "table_diagnostics": table_diagnostics,
    }


def _live_institutional_snapshot(snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        live_snapshot = _database_snapshot()
    except Exception:
        return snapshot or {
            "backend": "unknown",
            "engine_url": "",
            "database_url": "",
            "database_source": "",
            "counts": {},
            "latest": {},
            "tables": [],
        }
    if snapshot:
        snapshot = dict(snapshot)
        snapshot.update(live_snapshot)
        return snapshot
    return live_snapshot


def _institutional_source_map(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    latest_contest = _get_latest_contest() or _load_latest_contest_summary() or {}
    latest_generation = _load_latest_generated_games() or {}
    latest_reconciliation = _load_latest_reconciliation_summary() or {}
    return [
        {
            "camada": "GERADOR",
            "origem": "PostgreSQL",
            "tabelas": "generation_events / generated_games",
            "uso": f"última geração={latest_generation.get('generation_event_id', '-')}",
        },
        {
            "camada": "CONFERÊNCIA",
            "origem": "PostgreSQL",
            "tabelas": "imported_contests / reconciliation_runs / reconciliation_games",
            "uso": f"último concurso={latest_contest.get('contest_number', '-')} | última reconciliação={latest_reconciliation.get('id', '-')}",
        },
        {
            "camada": "MEMÓRIA",
            "origem": "PostgreSQL",
            "tabelas": "generated_games / reconciliation_* / operational_logs",
            "uso": "timeline e resumos institucionais",
        },
        {
            "camada": "PAINEL",
            "origem": "PostgreSQL + session_state",
            "tabelas": "snapshot institucional",
            "uso": f"build={BUILD_MARKER}",
        },
    ]


def _render_runtime_audit_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    audit = _runtime_audit_payload(snapshot)
    st.subheader("Auditoria do Runtime")
    st.write("Auditoria temporária da instância publicada no runtime institucional ativo.")
    if audit["backend"] != "postgresql":
        st.warning(f"Backend atual resolvido: {audit['backend']}. Esta instância não está apontando para PostgreSQL.")
    top_cols = st.columns(5)
    top_cols[0].metric("build ativo", audit["build_active"])
    top_cols[1].metric("commit ativo", audit["commit_active"])
    top_cols[2].metric("backend", audit["backend"])
    top_cols[3].metric("database_source", audit["database_source"])
    top_cols[4].metric("schema", audit["schema"])
    conn_cols = st.columns(3)
    conn_cols[0].caption(f"DATABASE_URL: {audit['database_url']}")
    conn_cols[1].caption(f"engine_url: {audit['engine_url']}")
    conn_cols[2].caption(f"host: {audit['host']} | database: {audit['database']}")
    st.markdown("##### SELECT COUNT(*) no runtime")
    audit_rows: list[dict[str, Any]] = []
    with _get_engine_cached().begin() as connection:
        for query in (
            "SELECT COUNT(*) FROM generation_events;",
            "SELECT COUNT(*) FROM generated_games;",
            "SELECT COUNT(*) FROM reconciliation_runs;",
            "SELECT COUNT(*) FROM reconciliation_games;",
            "SELECT COUNT(*) FROM imported_contests;",
            "SELECT COUNT(*) FROM institutional_output_signatures;",
        ):
            row: dict[str, Any] = {"query": query, "count": None, "status": "ok", "error": ""}
            try:
                value = connection.execute(text(query)).scalar()
                row["count"] = int(value or 0)
            except Exception as exc:
                row["status"] = "error"
                row["error"] = str(exc)
                row["count"] = None
            audit_rows.append(row)
    audit_df = pd.DataFrame(audit_rows)
    st.dataframe(audit_df, hide_index=True, use_container_width=True)
    error_rows = [row for row in audit_rows if row.get("status") == "error"]
    if error_rows:
        with st.expander("Erros SQL da auditoria", expanded=True):
            st.dataframe(
                pd.DataFrame(error_rows)[["query", "error"]],
                hide_index=True,
                use_container_width=True,
            )
    st.markdown("##### Diferenças entre módulos")
    source_map = _institutional_source_map(snapshot)
    st.dataframe(pd.DataFrame(source_map), hide_index=True, use_container_width=True)
    _render_scientific_memory_block()
    st.markdown("##### Papel do session_state")
    st.info(
        "session_state é apenas estado temporário de interface: página ativa, seleção de botões, "
        "diagnósticos e resultados recentes. A verdade operacional vem do PostgreSQL Institucional; "
        "session_state não deve ser usado como fonte de dados persistente nem como origem de conferência."
    )
    st.caption(f"build={BUILD_MARKER} | commit={audit['commit_active']}")


def _runtime_audit_payload(snapshot: dict[str, Any]) -> dict[str, Any]:
    engine_url = str(snapshot.get("engine_url") or snapshot.get("database_url") or "")
    parsed = urlparse(engine_url)
    database_name = "-"
    if parsed.scheme.startswith("sqlite"):
        database_name = parsed.path or engine_url
    elif parsed.path:
        database_name = parsed.path.lstrip("/") or "-"
    return {
        "backend": snapshot.get("backend", "-"),
        "host": parsed.hostname or "-",
        "database": database_name,
        "schema": "public" if str(snapshot.get("backend", "")).lower() == "postgresql" else "main",
        "engine_url": _mask_database_url(engine_url),
        "database_url": _mask_database_url(str(snapshot.get("database_url") or engine_url)),
        "database_source": snapshot.get("database_source", "-"),
        "build_active": BUILD_MARKER,
        "commit_active": _resolve_active_commit(),
        "counts": dict(snapshot.get("counts") or {}),
    }


def _hb_geometry_state() -> dict[str, Any]:
    with _JOB_LOCK:
        state = dict(_JOB_STATE)
    progress = _safe_json_load(HB_GEOMETRY_PROGRESS_FILE)
    report = _safe_json_load(HB_GEOMETRY_JSON_FILE)
    csv_frame = _safe_csv_load(HB_GEOMETRY_CSV_FILE)
    summary = report.get("summary") or progress.get("summary") or {}
    return {
        "job": state,
        "progress": progress,
        "report": report,
        "summary": summary,
        "csv_frame": csv_frame,
    }


def _load_imported_contest(contest_number: int | None = None) -> dict[str, Any] | None:
    with get_session(DB_PATH) as session:
        query = session.query(ImportedContest)
        if contest_number is None:
            row = query.order_by(ImportedContest.contest_number.desc()).first()
        else:
            row = query.filter(ImportedContest.contest_number == int(contest_number)).first()
        if row is None:
            return None
        dezenas = _extract_int_numbers(str(row.dezenas or ""))
        return {
            "contest_number": int(row.contest_number),
            "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else "",
            "data": str(row.data or ""),
            "dezenas": dezenas,
            "metadata_json": str(row.metadata_json or "{}"),
        }


def _normalize_contest_record(record: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(record, dict):
        return None
    contest_number = record.get("contest_number", record.get("concurso"))
    if not str(contest_number or "").isdigit():
        return None
    dezenas = _extract_int_numbers(record.get("dezenas", []) or [])
    return {
        "contest_number": int(contest_number),
        "created_at": str(record.get("created_at", "") or ""),
        "data": str(record.get("data", "") or ""),
        "dezenas": dezenas,
        "metadata_json": str(record.get("metadata_json", "{}") or "{}"),
    }


def _load_imported_contest_numbers() -> list[int]:
    with get_session(DB_PATH) as session:
        rows = session.query(ImportedContest.contest_number).order_by(ImportedContest.contest_number.asc()).all()
        return [int(row[0]) for row in rows if row and row[0] is not None]


def _load_latest_generated_games() -> dict[str, Any] | None:
    seed = 0
    created_at = ""
    target_contest = None
    with get_session(DB_PATH) as session:
        generation_event = (
            session.query(GenerationEvent)
            .order_by(GenerationEvent.created_at.desc(), GenerationEvent.id.desc())
            .first()
        )
        if generation_event is None:
            return None

        generation_event_id = int(generation_event.id or 0)
        seed = int(getattr(generation_event, "seed", 0) or 0)
        created_at = generation_event.created_at.isoformat() if getattr(generation_event, "created_at", None) else ""
        games_query = (
            session.query(GeneratedGame)
            .filter(GeneratedGame.generation_event_id == generation_event_id)
            .order_by(GeneratedGame.game_index)
            .all()
        )
        games: list[dict[str, Any]] = []
        for game in games_query:
            if getattr(game, "target_contest", None) is not None:
                target_contest = int(game.target_contest)
            games.append(
                {
                    "game_index": int(game.game_index or 0),
                    "numbers": [int(number) for number in (game.numbers or [])],
                    "profile_type": str(game.profile_type or ""),
                    "final_score": dict(game.final_score or {}),
                    "quadra_score": dict(game.quadra_score or {}),
                    "origin": str(game.origin or "institutional"),
                    "context_json": dict(game.context_json or {}),
                }
            )

    if not games:
        return None

    return {
        "generation_event_id": generation_event_id,
        "seed": seed,
        "games": games,
        "total_games": len(games),
        "target_contest": target_contest,
        "created_at": created_at,
        "runtime_status": "loaded_from_database",
    }


def _load_latest_contest_summary() -> dict[str, Any] | None:
    latest_contest = _load_imported_contest()
    if latest_contest:
        return {
            "contest_number": int(latest_contest.get("contest_number", 0) or 0),
            "data": str(latest_contest.get("data") or ""),
            "dezenas": [int(number) for number in latest_contest.get("dezenas", [])],
            "source": "banco oficial",
        }
    latest_generation = _load_latest_generated_games() or {}
    target_contest = latest_generation.get("target_contest")
    if str(target_contest or "").isdigit():
        return {
            "contest_number": int(target_contest or 0),
            "data": str(latest_generation.get("created_at") or ""),
            "dezenas": [],
            "source": "última geração persistida",
        }
    return None


def _get_latest_contest() -> dict[str, Any] | None:
    sync_summary = st.session_state.get("institutional_last_official_sync_summary", {}) or {}
    sync_record = _normalize_contest_record(sync_summary.get("latest_contest_record"))
    if sync_record:
        return sync_record
    sync_contest = sync_summary.get("latest_contest")
    if str(sync_contest or "").isdigit():
        synced_contest = _load_imported_contest(int(sync_contest))
        if synced_contest and int(synced_contest.get("contest_number", 0) or 0) > 0:
            return synced_contest
    latest_contest = _load_imported_contest()
    if latest_contest and int(latest_contest.get("contest_number", 0) or 0) > 0:
        return latest_contest
    contest_numbers = _load_imported_contest_numbers()
    if contest_numbers:
        return _load_imported_contest(contest_numbers[-1])
    latest_generation = _load_latest_generated_games() or {}
    target_contest = latest_generation.get("target_contest")
    if str(target_contest or "").isdigit():
        return _load_imported_contest(int(target_contest))
    if str(sync_contest or "").isdigit():
        return {
            "contest_number": int(sync_contest),
            "created_at": str(sync_summary.get("sync_timestamp", "") or ""),
            "data": "",
            "dezenas": list(sync_summary.get("imported_numbers", []) or []),
            "metadata_json": "{}",
        }
    return None


def _load_latest_scientific_calibration_decision(limit: int = 1) -> list[dict[str, Any]]:
    resolved_limit = max(1, int(limit or 1))
    with get_session(DB_PATH) as session:
        rows = (
            session.query(ScientificCalibrationDecision)
            .order_by(
                ScientificCalibrationDecision.created_at.desc(),
                ScientificCalibrationDecision.id.desc(),
            )
            .limit(resolved_limit)
            .all()
        )
    decisions: list[dict[str, Any]] = []
    for row in rows:
        decisions.append(
            {
                "id": int(getattr(row, "id", 0) or 0),
                "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else "",
                "strategy": str(getattr(row, "strategy", "") or ""),
                "game_size": int(getattr(row, "game_size", 0) or 0),
                "source_batch_id": str(getattr(row, "source_batch_id", "") or ""),
                "source_generation_range": dict(getattr(row, "source_generation_range", {}) or {}),
                "structural_status": str(getattr(row, "structural_status", "") or ""),
                "scientific_status": str(getattr(row, "scientific_status", "") or ""),
                "classification": str(getattr(row, "classification", "") or ""),
                "main_reason": str(getattr(row, "main_reason", "") or ""),
                "recommended_action": str(getattr(row, "recommended_action", "") or ""),
                "policy_before": dict(getattr(row, "policy_before", {}) or {}),
                "policy_after": dict(getattr(row, "policy_after", {}) or {}),
                "mode": str(getattr(row, "mode", "") or "OBSERVACAO"),
                "applied": bool(getattr(row, "applied", 0) or 0),
                "approved_by": str(getattr(row, "approved_by", "") or ""),
                "notes": str(getattr(row, "notes", "") or ""),
            }
        )
    return decisions


def _load_latest_scientific_memory(limit: int = 5) -> list[dict[str, Any]]:
    resolved_limit = max(1, int(limit or 1))
    with get_session(DB_PATH) as session:
        rows = (
            session.query(ScientificInstitutionalMemory)
            .order_by(
                ScientificInstitutionalMemory.created_at.desc(),
                ScientificInstitutionalMemory.id.desc(),
            )
            .limit(resolved_limit)
            .all()
        )
    memories: list[dict[str, Any]] = []
    for row in rows:
        memories.append(
            {
                "id": int(getattr(row, "id", 0) or 0),
                "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else "",
                "memory_kind": str(getattr(row, "memory_kind", "") or ""),
                "strategy_name": str(getattr(row, "strategy_name", "") or ""),
                "game_size": int(getattr(row, "game_size", 0) or 0),
                "batch_id": str(getattr(row, "batch_id", "") or ""),
                "generation_range": dict(getattr(row, "generation_range", {}) or {}),
                "total_games": int(getattr(row, "total_games", 0) or 0),
                "unique_games": int(getattr(row, "unique_games", 0) or 0),
                "duplicate_games": int(getattr(row, "duplicate_games", 0) or 0),
                "structural_status": str(getattr(row, "structural_status", "") or ""),
                "scientific_status": str(getattr(row, "scientific_status", "") or ""),
                "scientific_classification": str(getattr(row, "scientific_classification", "") or ""),
                "main_reason": str(getattr(row, "main_reason", "") or ""),
                "recommended_action": str(getattr(row, "recommended_action", "") or ""),
                "best_hit": int(getattr(row, "best_hit", 0) or 0),
                "average_hits": float(getattr(row, "average_hits", 0.0) or 0.0),
                "count_11_plus": int(getattr(row, "count_11_plus", 0) or 0),
                "count_12_plus": int(getattr(row, "count_12_plus", 0) or 0),
                "count_13_plus": int(getattr(row, "count_13_plus", 0) or 0),
                "count_14_plus": int(getattr(row, "count_14_plus", 0) or 0),
                "count_15": int(getattr(row, "count_15", 0) or 0),
                "decision_mode": str(getattr(row, "decision_mode", "OBSERVACAO") or "OBSERVACAO"),
                "approved_for_use": bool(getattr(row, "approved_for_use", 0) or 0),
                "official_history_count": int(getattr(row, "official_history_count", 0) or 0),
                "official_history_first_contest": getattr(row, "official_history_first_contest", None),
                "official_history_last_contest": getattr(row, "official_history_last_contest", None),
                "official_history_window": list(getattr(row, "official_history_window", []) or []),
                "source": str(getattr(row, "source", "") or ""),
            }
        )
    return memories


def _load_official_history_summary() -> dict[str, Any]:
    with get_session(DB_PATH) as session:
        rows = (
            session.query(LotofacilOfficialHistory)
            .order_by(LotofacilOfficialHistory.contest_number.asc())
            .all()
        )
    contest_numbers = [int(getattr(row, "contest_number", 0) or 0) for row in rows if int(getattr(row, "contest_number", 0) or 0) > 0]
    latest = rows[-1] if rows else None
    return {
        "count": len(rows),
        "first_contest": contest_numbers[0] if contest_numbers else None,
        "last_contest": contest_numbers[-1] if contest_numbers else None,
        "latest_contest": {
            "contest_number": int(getattr(latest, "contest_number", 0) or 0) if latest is not None else 0,
            "draw_date": str(getattr(latest, "draw_date", "") or "") if latest is not None else "",
            "numbers": [int(value) for value in str(getattr(latest, "numbers", "") or "").replace(",", " ").split() if str(value).isdigit()] if latest is not None else [],
            "source": str(getattr(latest, "source", "") or "") if latest is not None else "",
        }
        if latest is not None
        else {},
        "window": contest_numbers[-10:],
        "rows": [
            {
                "contest_number": int(getattr(row, "contest_number", 0) or 0),
                "draw_date": str(getattr(row, "draw_date", "") or ""),
                "numbers": [int(value) for value in str(getattr(row, "numbers", "") or "").replace(",", " ").split() if str(value).isdigit()],
                "source": str(getattr(row, "source", "") or ""),
            }
            for row in rows[-10:]
        ],
        "source": "lotofacil_official_history",
    }


def _load_imported_contests_summary() -> dict[str, Any]:
    with get_session(DB_PATH) as session:
        rows = (
            session.query(ImportedContest)
            .order_by(ImportedContest.contest_number.asc())
            .all()
        )
    contest_numbers = [int(getattr(row, "contest_number", 0) or 0) for row in rows if int(getattr(row, "contest_number", 0) or 0) > 0]
    latest = rows[-1] if rows else None
    return {
        "count": len(rows),
        "first_contest": contest_numbers[0] if contest_numbers else None,
        "last_contest": contest_numbers[-1] if contest_numbers else None,
        "latest_contest": {
            "contest_number": int(getattr(latest, "contest_number", 0) or 0) if latest is not None else 0,
            "draw_date": str(getattr(latest, "data", "") or "") if latest is not None else "",
            "numbers": [int(value) for value in str(getattr(latest, "dezenas", "") or "").replace(",", " ").split() if str(value).isdigit()] if latest is not None else [],
            "source": "imported_contests" if latest is not None else "",
        }
        if latest is not None
        else {},
        "window": contest_numbers[-10:],
        "rows": [
            {
                "contest_number": int(getattr(row, "contest_number", 0) or 0),
                "draw_date": str(getattr(row, "data", "") or ""),
                "numbers": [int(value) for value in str(getattr(row, "dezenas", "") or "").replace(",", " ").split() if str(value).isdigit()],
                "source": "imported_contests",
            }
            for row in rows[-10:]
        ],
        "source": "imported_contests",
    }


def _load_official_history_diagnostics() -> dict[str, Any]:
    official_summary = _load_official_history_summary()
    imported_summary = _load_imported_contests_summary()
    with get_session(DB_PATH) as session:
        official_numbers = [
            int(row[0] or 0)
            for row in session.query(LotofacilOfficialHistory.contest_number)
            .order_by(LotofacilOfficialHistory.contest_number.asc())
            .all()
            if int(row[0] or 0) > 0
        ]
    official_set = set(official_numbers)
    if official_numbers:
        min_contest = official_numbers[0]
        max_contest = official_numbers[-1]
        missing = [contest for contest in range(min_contest, max_contest + 1) if contest not in official_set]
    else:
        min_contest = None
        max_contest = None
        missing = []
    imported_last = imported_summary.get("last_contest")
    status = "OK"
    if not official_numbers:
        status = "INCOMPLETA"
    elif missing:
        status = "INCOMPLETA"
    elif imported_last is not None and max_contest is not None and int(imported_last) > int(max_contest):
        status = "INCOMPLETA"
    return {
        "total_lotofacil_official_history": int(official_summary.get("count", 0) or 0),
        "contest_number_min": min_contest,
        "contest_number_max": max_contest,
        "concursos_faltantes": missing,
        "total_concursos_faltantes": len(missing),
        "ultimo_concurso_imported_contests": imported_last,
        "ultimo_concurso_lotofacil_official_history": max_contest,
        "status_base_oficial": status,
        "imported_contests_count": int(imported_summary.get("count", 0) or 0),
        "imported_contests_window": list(imported_summary.get("window") or []),
    }


def _ensure_official_history_seeded() -> dict[str, Any]:
    diagnostics = _load_official_history_diagnostics()
    if int(diagnostics.get("total_lotofacil_official_history", 0) or 0) > 0 and int(diagnostics.get("total_concursos_faltantes", 0) or 0) == 0:
        return {"status": "ok", "seeded": 0, **diagnostics}
    try:
        repository = ContestRepository(DB_PATH)
        inserted = 0
        if int(diagnostics.get("total_lotofacil_official_history", 0) or 0) <= 0:
            inserted += int(repository.bootstrap_official_history_from_csv())
        inserted += int(repository.sync_official_history_from_imported_contests())
        diagnostics = _load_official_history_diagnostics()
        return {
            "status": "ok" if int(diagnostics.get("total_lotofacil_official_history", 0) or 0) > 0 and int(diagnostics.get("total_concursos_faltantes", 0) or 0) == 0 else "partial",
            "seeded": inserted,
            **diagnostics,
        }
    except Exception as exc:
        return {"status": "error", "seeded": 0, "error": str(exc), **diagnostics}


def _render_scientific_memory_block() -> None:
    seed_report = _ensure_official_history_seeded()
    official_diagnostics = _load_official_history_diagnostics()
    scientific_memory = _load_latest_scientific_memory(limit=5)
    latest_memory = scientific_memory[0] if scientific_memory else {}
    st.markdown("##### Mem?ria Cient?fica da LotoIA")
    memory_cols = st.columns(6)
    memory_cols[0].metric("lotofacil_official_history_total", int(official_diagnostics.get("total_lotofacil_official_history", 0) or 0))
    memory_cols[1].metric("primeiro_concurso", official_diagnostics.get("contest_number_min", "-") or "-")
    memory_cols[2].metric("ultimo_concurso", official_diagnostics.get("contest_number_max", "-") or "-")
    memory_cols[3].metric("concursos_faltantes", int(official_diagnostics.get("total_concursos_faltantes", 0) or 0))
    memory_cols[4].metric("status_base_oficial", official_diagnostics.get("status_base_oficial", "-") or "-")
    memory_cols[5].metric("imported_ult", official_diagnostics.get("ultimo_concurso_imported_contests", "-") or "-")
    st.caption(
        " | ".join(
            [
                f"seed_status={seed_report.get('status', '-')}",
                f"seeded={seed_report.get('seeded', 0)}",
                f"faltantes={official_diagnostics.get('concursos_faltantes', [])}",
            ]
        )
    )
    scientific_cols = st.columns(3)
    scientific_cols[0].metric("memoria_cientifica", len(scientific_memory))
    scientific_cols[1].metric("classificacao", latest_memory.get("scientific_classification", "-") or "-")
    scientific_cols[2].metric("acao", latest_memory.get("recommended_action", "-") or "-")
    st.caption(
        " | ".join(
            [
                f"memory_kind={latest_memory.get('memory_kind', '-')} ",
                f"strategy={latest_memory.get('strategy_name', '-')} ",
                f"batch_id={latest_memory.get('batch_id', '-')} ",
                f"decision_mode={latest_memory.get('decision_mode', '-')} ",
                f"approved_for_use={latest_memory.get('approved_for_use', False)}",
            ]
        )
    )
    if scientific_memory:
        with st.expander("Mem?ria cient?fica completa", expanded=False):
            st.dataframe(pd.DataFrame(scientific_memory), hide_index=True, use_container_width=True)


@st.cache_data(show_spinner=False)
def _history_number_frequency() -> dict[int, int]:
    try:
        draws = load_draws_csv()
    except Exception:
        return {}
    frequencies = number_frequency(draws)
    return {int(number): int(amount) for number, amount in frequencies.items()}


def _sequence_metrics(numbers: list[int]) -> dict[str, int]:
    ordered = sorted(int(number) for number in numbers)
    if not ordered:
        return {"sequence_count": 0, "largest_sequence": 0}
    longest = 1
    current = 1
    count = 0
    for index in range(1, len(ordered)):
        if ordered[index] == ordered[index - 1] + 1:
            current += 1
        else:
            if current > 1:
                count += 1
            longest = max(longest, current)
            current = 1
    if current > 1:
        count += 1
    longest = max(longest, current)
    return {"sequence_count": count, "largest_sequence": longest}


def _coverage_metrics(numbers: list[int]) -> dict[str, Any]:
    blocks = Counter(((int(number) - 1) // 5) for number in numbers)
    block_distribution = [int(blocks.get(index, 0)) for index in range(5)]
    active_blocks = sum(1 for amount in block_distribution if amount > 0)
    coverage_score = round(active_blocks / 5.0, 4)
    return {
        "coverage_score": coverage_score,
        "block_distribution": block_distribution,
        "active_blocks": active_blocks,
    }


def _entropy_score(numbers: list[int]) -> float:
    coverage = _coverage_metrics(numbers)["block_distribution"]
    total = sum(coverage) or 1
    entropy = 0.0
    for amount in coverage:
        if amount <= 0:
            continue
        share = amount / total
        entropy -= share * math.log2(share)
    non_zero_blocks = sum(1 for amount in coverage if amount > 0)
    max_entropy = math.log2(non_zero_blocks) if non_zero_blocks > 1 else 1.0
    return round((entropy / max_entropy) if max_entropy else 0.0, 4)


def _hb_geometry_profile_for_size(size: int) -> dict[str, float | int]:
    size = max(2, min(15, int(size or 15)))
    if size <= 2:
        odd_even_max = 2
        sequence_max = 2
        coverage_min = 0.20
        entropy_min = 0.15
    elif size <= 4:
        odd_even_max = 4
        sequence_max = 3
        coverage_min = 0.25
        entropy_min = 0.20
    elif size <= 8:
        odd_even_max = 5
        sequence_max = 4
        coverage_min = 0.30
        entropy_min = 0.30
    elif size <= 12:
        odd_even_max = 7
        sequence_max = 5
        coverage_min = 0.35
        entropy_min = 0.40
    else:
        odd_even_max = 9
        sequence_max = 6
        coverage_min = 0.40
        entropy_min = 0.45
    return {
        "odd_min": 0,
        "odd_max": min(size, odd_even_max),
        "even_min": 0,
        "even_max": min(size, odd_even_max),
        "sequence_max": min(size, sequence_max),
        "coverage_min": coverage_min,
        "entropy_min": entropy_min,
    }


def _institutional_generation_policy(size: int) -> dict[str, Any]:
    size = max(2, min(25, int(size or 15)))
    if size == 15:
        return {
            "repeat_min": 7,
            "repeat_max": 10,
            "preferred_parity_pairs": [(7, 8), (8, 7)],
            "allowed_parity_pairs": [(7, 8), (8, 7), (6, 9), (9, 6)],
            "sequence_max": 6,
            "coverage_min": 0.40,
            "entropy_min": 0.45,
            "core_numbers": [7, 12, 16, 23],
            "discouraged_numbers": [2, 4, 11, 15, 24, 25],
            "max_frequency_ratio": 0.70,
            "min_frequency_ratio": 0.20,
            "preferred_profile_ratios": {(7, 8): 0.52, (8, 7): 0.48},
        }
    profile = _hb_geometry_profile_for_size(size)
    return {
        "repeat_min": 0,
        "repeat_max": min(size, 8),
        "preferred_parity_pairs": [],
        "allowed_parity_pairs": [],
        "sequence_max": int(profile["sequence_max"]),
        "coverage_min": float(profile["coverage_min"]),
        "entropy_min": float(profile["entropy_min"]),
        "core_numbers": [],
        "discouraged_numbers": [],
        "max_frequency_ratio": 1.0,
        "min_frequency_ratio": 0.0,
        "preferred_profile_ratios": {},
    }


def _load_scientific_batch_games(batch_id: str | None) -> list[dict[str, Any]]:
    resolved_batch_id = str(batch_id or "").strip()
    if not resolved_batch_id:
        return []
    with get_session(DB_PATH) as session:
        rows = (
            session.query(InstitutionalOutputSignature)
            .filter(InstitutionalOutputSignature.batch_id == resolved_batch_id)
            .order_by(InstitutionalOutputSignature.created_at.asc(), InstitutionalOutputSignature.id.asc())
            .all()
        )
    games: list[dict[str, Any]] = []
    for row in rows:
        payload = dict(getattr(row, "payload", {}) or {})
        numbers = _extract_int_numbers(payload.get("numbers", []))
        games.append(
            {
                "game_index": int(payload.get("game_index", len(games) + 1) or len(games) + 1),
                "numbers": numbers,
                "game_signature": str(getattr(row, "game_signature", "") or ""),
                "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else "",
                "source": str(payload.get("source", "institutional_app") or "institutional_app"),
                "batch_id": resolved_batch_id,
            }
        )
    return games


def _scientific_batch_diagnostics(
    *,
    batch_id: str | None,
    games: list[dict[str, Any]],
    game_size: int,
) -> dict[str, Any]:
    resolved_batch_id = str(batch_id or "").strip()
    if not resolved_batch_id:
        return {}
    scientific_games = games or _load_scientific_batch_games(resolved_batch_id)
    if not scientific_games:
        return {}
    resolved_game_size = int(game_size or 0)
    if resolved_game_size <= 0:
        first_game_numbers = scientific_games[0].get("numbers", []) if scientific_games else []
        resolved_game_size = len(first_game_numbers) if first_game_numbers else 15
    core = LotofacilScientificCore()
    reference_contests = core.contests[-10:] if core.contests else []
    policy = (
        get_scientific_generation_policy(resolved_game_size, contests=core.contests)
        if core.contests
        else get_scientific_generation_policy(resolved_game_size)
    )
    report = validate_scientific_batch(
        scientific_games,
        reference_contests,
        resolved_game_size,
        policy,
        batch_id=resolved_batch_id,
    )
    report["reference_window"] = [int(item.get("contest_number", 0) or 0) for item in reference_contests]
    report["game_size"] = resolved_game_size
    report["status_comandante_cientifico"] = str(report.get("status_comandante_cientifico", "REPROVADO") or "REPROVADO")
    report["classificacao_cientifica"] = str(report.get("classificacao_cientifica", "REPROVADA") or "REPROVADA")
    report["status_visual"] = (
        "APROVADO"
        if str(report["status_comandante_cientifico"]).upper() == "APROVADO"
        else "REPROVADO"
    )
    return report


def _sync_hb_geometry_controls(size: int) -> dict[str, float | int]:
    profile = _hb_geometry_profile_for_size(size)
    size_key = int(size)
    if int(st.session_state.get("institutional_geometry_size", 0) or 0) != size_key:
        st.session_state["institutional_geometry_size"] = size_key
        st.session_state["institutional_odd_min"] = int(profile["odd_min"])
        st.session_state["institutional_odd_max"] = int(profile["odd_max"])
        st.session_state["institutional_even_min"] = int(profile["even_min"])
        st.session_state["institutional_even_max"] = int(profile["even_max"])
        st.session_state["institutional_sequence_max"] = int(profile["sequence_max"])
        st.session_state["institutional_coverage_min"] = float(profile["coverage_min"])
        st.session_state["institutional_entropy_min"] = float(profile["entropy_min"])
    else:
        st.session_state["institutional_odd_min"] = max(
            0,
            min(int(st.session_state.get("institutional_odd_min", profile["odd_min"]) or profile["odd_min"]), int(profile["odd_max"])),
        )
        st.session_state["institutional_odd_max"] = max(
            st.session_state["institutional_odd_min"],
            min(int(st.session_state.get("institutional_odd_max", profile["odd_max"]) or profile["odd_max"]), int(profile["odd_max"])),
        )
        st.session_state["institutional_even_min"] = max(
            0,
            min(int(st.session_state.get("institutional_even_min", profile["even_min"]) or profile["even_min"]), int(profile["even_max"])),
        )
        st.session_state["institutional_even_max"] = max(
            st.session_state["institutional_even_min"],
            min(int(st.session_state.get("institutional_even_max", profile["even_max"]) or profile["even_max"]), int(profile["even_max"])),
        )
        st.session_state["institutional_sequence_max"] = max(
            1,
            min(int(st.session_state.get("institutional_sequence_max", profile["sequence_max"]) or profile["sequence_max"]), int(profile["sequence_max"])),
        )
        st.session_state["institutional_coverage_min"] = max(
            0.0,
            min(float(st.session_state.get("institutional_coverage_min", profile["coverage_min"]) or profile["coverage_min"]), float(profile["coverage_min"]) + 0.2),
        )
        st.session_state["institutional_entropy_min"] = max(
            0.0,
            min(float(st.session_state.get("institutional_entropy_min", profile["entropy_min"]) or profile["entropy_min"]), float(profile["entropy_min"]) + 0.2),
        )
    return profile


def _parity_pair_is_allowed(
    odd_count: int,
    even_count: int,
    *,
    target_size: int,
    allowed_parity_pairs: Sequence[tuple[int, int]] | None = None,
) -> bool:
    if odd_count + even_count != target_size:
        return False
    if not allowed_parity_pairs:
        return True
    return (odd_count, even_count) in set(tuple(pair) for pair in allowed_parity_pairs)


def _order_parity_pairs_for_batch(
    pairs: Sequence[tuple[int, int]] | None,
    *,
    batch_profile_usage: dict[tuple[int, int], int] | None = None,
    preferred_profile_ratios: dict[tuple[int, int], float] | None = None,
) -> list[tuple[int, int]]:
    ordered_pairs: list[tuple[int, int]] = []
    for pair in pairs or []:
        normalized_pair = (int(pair[0]), int(pair[1]))
        if normalized_pair not in ordered_pairs:
            ordered_pairs.append(normalized_pair)
    if not ordered_pairs:
        return []
    if not batch_profile_usage:
        return ordered_pairs
    total_usage = sum(int(amount or 0) for amount in batch_profile_usage.values()) or 1
    preferred_profile_ratios = preferred_profile_ratios or {}
    return sorted(
        ordered_pairs,
        key=lambda pair: (
            float(batch_profile_usage.get(pair, 0)) / max(1.0, float(preferred_profile_ratios.get(pair, 0.0) or 0.0) * total_usage)
            if preferred_profile_ratios.get(pair, 0.0)
            else float(batch_profile_usage.get(pair, 0)),
            int(pair[0]),
            int(pair[1]),
        ),
    )


def _select_subset_from_candidate(
    numbers: list[int],
    *,
    target_size: int,
    frequency_map: dict[int, int],
    latest_numbers: set[int],
    batch_number_usage: dict[int, int] | None = None,
    batch_total_games: int | None = None,
    batch_profile_usage: dict[tuple[int, int], int] | None = None,
    core_numbers: Sequence[int] | None = None,
    discouraged_numbers: Sequence[int] | None = None,
    max_frequency_ratio: float = 1.0,
    min_frequency_ratio: float = 0.0,
    preferred_profile_ratios: dict[tuple[int, int], float] | None = None,
    odd_min: int,
    odd_max: int,
    even_min: int,
    even_max: int,
    sequence_max: int,
    coverage_min: float,
    entropy_min: float,
    repeat_min: int,
    repeat_max: int,
    preferred_parity_pairs: Sequence[tuple[int, int]] | None = None,
    allowed_parity_pairs: Sequence[tuple[int, int]] | None = None,
) -> list[int] | None:
    candidate_numbers = sorted({int(number) for number in numbers})
    if target_size < 1:
        return None
    if target_size > 25:
        return None
    universe = list(range(1, 26))
    candidate_set = set(candidate_numbers)
    batch_number_usage = dict(batch_number_usage or {})
    batch_total_games = max(1, int(batch_total_games or 1))
    core_numbers_set = {int(number) for number in (core_numbers or [])}
    discouraged_numbers_set = {int(number) for number in (discouraged_numbers or [])}
    max_count = max(1, int(math.ceil(batch_total_games * float(max_frequency_ratio or 1.0))))
    min_count = max(0, int(math.ceil(batch_total_games * float(min_frequency_ratio or 0.0))))
    preferred_profile_ratios = {
        (int(pair[0]), int(pair[1])): float(ratio)
        for pair, ratio in (preferred_profile_ratios or {}).items()
    }
    scoring = sorted(
        universe,
        key=lambda number: (
            -int(number in candidate_set),
            -int(frequency_map.get(int(number), 0)),
            int(batch_number_usage.get(int(number), 0)),
            -int(number in core_numbers_set and int(batch_number_usage.get(int(number), 0)) < min_count),
            int(number in latest_numbers),
            int(number in discouraged_numbers_set),
            int(number),
        ),
    )

    candidate_pairs: list[tuple[int, int]] = []
    for pair in preferred_parity_pairs or []:
        normalized_pair = (int(pair[0]), int(pair[1]))
        if sum(normalized_pair) == target_size and normalized_pair not in candidate_pairs:
            candidate_pairs.append(normalized_pair)
    for pair in allowed_parity_pairs or []:
        normalized_pair = (int(pair[0]), int(pair[1]))
        if sum(normalized_pair) == target_size and normalized_pair not in candidate_pairs:
            candidate_pairs.append(normalized_pair)
    if not candidate_pairs:
        odd_target = min(max((target_size + 1) // 2, odd_min), odd_max)
        even_target = target_size - odd_target
        candidate_pairs = [(odd_target, even_target)]
    if batch_profile_usage and preferred_profile_ratios:
        candidate_pairs = _order_parity_pairs_for_batch(
            candidate_pairs,
            batch_profile_usage=batch_profile_usage,
            preferred_profile_ratios=preferred_profile_ratios,
        )

    for odd_target, even_target in candidate_pairs:
        if odd_target < odd_min or odd_target > odd_max:
            continue
        if even_target < even_min or even_target > even_max:
            continue
        if odd_target + even_target != target_size:
            continue
        selected: list[int] = []
        for pool, quota in (
            ([number for number in scoring if number % 2 != 0], odd_target),
            ([number for number in scoring if number % 2 == 0], even_target),
        ):
            for number in pool:
                if number not in selected:
                    selected.append(number)
                if sum(1 for item in selected if item % 2 == pool[0] % 2) >= quota:
                    break

        if len(selected) < target_size:
            for number in scoring:
                if number not in selected:
                    selected.append(number)
                if len(selected) >= target_size:
                    break

        selected = sorted(selected[:target_size])
        if not selected:
            continue

        odd_count = sum(1 for number in selected if number % 2 != 0)
        even_count = len(selected) - odd_count
        if not (odd_min <= odd_count <= odd_max and even_min <= even_count <= even_max):
            continue
        if _sequence_metrics(selected)["largest_sequence"] > sequence_max:
            continue
        repeat_count = len(set(selected).intersection(latest_numbers))
        if repeat_count < repeat_min or repeat_count > repeat_max:
            continue
        if _coverage_metrics(selected)["coverage_score"] < coverage_min:
            continue
        if _entropy_score(selected) < entropy_min:
            continue
        if batch_number_usage:
            projected = dict(batch_number_usage)
            for number in selected:
                projected[int(number)] = int(projected.get(int(number), 0) or 0) + 1
            if any(int(projected.get(number, 0) or 0) > max_count for number in selected):
                continue
            if core_numbers_set:
                if any(int(projected.get(number, 0) or 0) < min_count for number in core_numbers_set if number in selected):
                    # do not reject here; just prefer candidates that keep core numbers growing
                    pass
        if not _parity_pair_is_allowed(
            odd_count,
            even_count,
            target_size=target_size,
            allowed_parity_pairs=allowed_parity_pairs or candidate_pairs,
        ):
            continue
        return selected
    return None


def _force_subset_from_universe(
    *,
    target_size: int,
    frequency_map: dict[int, int],
    latest_numbers: set[int],
    batch_number_usage: dict[int, int] | None = None,
    batch_total_games: int | None = None,
    batch_profile_usage: dict[tuple[int, int], int] | None = None,
    core_numbers: Sequence[int] | None = None,
    discouraged_numbers: Sequence[int] | None = None,
    max_frequency_ratio: float = 1.0,
    min_frequency_ratio: float = 0.0,
    odd_min: int,
    odd_max: int,
    even_min: int,
    even_max: int,
    preferred_parity_pairs: Sequence[tuple[int, int]] | None = None,
    preferred_profile_ratios: dict[tuple[int, int], float] | None = None,
    repeat_min: int = 0,
    repeat_max: int | None = None,
    sequence_max: int | None = None,
    coverage_min: float | None = None,
    entropy_min: float | None = None,
    allowed_parity_pairs: Sequence[tuple[int, int]] | None = None,
    offset: int = 0,
) -> list[int]:
    target_size = max(1, min(int(target_size or 1), 25))
    universe = list(range(1, 26))
    batch_number_usage = dict(batch_number_usage or {})
    batch_total_games = max(1, int(batch_total_games or 1))
    batch_profile_usage = dict(batch_profile_usage or {})
    core_numbers_set = {int(number) for number in (core_numbers or [])}
    discouraged_numbers_set = {int(number) for number in (discouraged_numbers or [])}
    max_count = max(1, int(math.ceil(batch_total_games * float(max_frequency_ratio or 1.0))))
    min_count = max(0, int(math.ceil(batch_total_games * float(min_frequency_ratio or 0.0))))
    preferred_profile_ratios = {
        (int(pair[0]), int(pair[1])): float(ratio)
        for pair, ratio in (preferred_profile_ratios or {}).items()
    }
    scoring = sorted(
        universe,
        key=lambda number: (
            -int(frequency_map.get(int(number), 0)),
            int(batch_number_usage.get(int(number), 0)),
            -int(number in core_numbers_set and int(batch_number_usage.get(int(number), 0)) < min_count),
            int(number in discouraged_numbers_set),
            int(number in latest_numbers),
            int(number),
        ),
    )
    if scoring:
        offset = int(offset or 0) % len(scoring)
        scoring = scoring[offset:] + scoring[:offset]
    odd_target = min(max((target_size + 1) // 2, odd_min), odd_max)
    even_target = target_size - odd_target
    if even_target < even_min:
        even_target = even_min
        odd_target = target_size - even_target
    if odd_target < odd_min:
        odd_target = odd_min
        even_target = target_size - odd_target
    if odd_target > odd_max:
        odd_target = odd_max
        even_target = target_size - odd_target
    if even_target > even_max:
        even_target = even_max
        odd_target = target_size - even_target
    if odd_target < 0 or even_target < 0 or odd_target + even_target != target_size:
        odd_target = min(max(odd_target, 0), target_size)
        even_target = target_size - odd_target
    parity_pairs = [(odd_target, even_target)]
    ordered_pairs: list[tuple[int, int]] = []
    for pair in preferred_parity_pairs or []:
        normalized_pair = (int(pair[0]), int(pair[1]))
        if sum(normalized_pair) == target_size and normalized_pair not in ordered_pairs:
            ordered_pairs.append(normalized_pair)
    for pair in allowed_parity_pairs or []:
        normalized_pair = (int(pair[0]), int(pair[1]))
        if sum(normalized_pair) == target_size and normalized_pair not in ordered_pairs:
            ordered_pairs.append(normalized_pair)
    if ordered_pairs:
        parity_pairs = ordered_pairs
    if batch_profile_usage and preferred_profile_ratios:
        parity_pairs = _order_parity_pairs_for_batch(
            parity_pairs,
            batch_profile_usage=batch_profile_usage,
            preferred_profile_ratios=preferred_profile_ratios,
        )
    latest_numbers = set(latest_numbers or set())
    repeat_max = target_size if repeat_max is None else max(0, min(int(repeat_max), target_size))
    repeat_min = max(0, min(int(repeat_min), repeat_max))

    for odd_target, even_target in parity_pairs:
        selected: list[int] = []
        odd_pool = [number for number in scoring if number % 2 != 0]
        even_pool = [number for number in scoring if number % 2 == 0]
        for pool, quota in ((odd_pool, odd_target), (even_pool, even_target)):
            for number in pool:
                if number not in selected:
                    selected.append(number)
                if sum(1 for item in selected if item % 2 == pool[0] % 2) >= quota:
                    break
        if len(selected) < target_size:
            for number in scoring:
                if number not in selected:
                    selected.append(number)
                if len(selected) >= target_size:
                    break
        selected = sorted(selected[:target_size])
        if not selected:
            continue
        odd_count = sum(1 for number in selected if number % 2 != 0)
        even_count = len(selected) - odd_count
        if not _parity_pair_is_allowed(
            odd_count,
            even_count,
            target_size=target_size,
            allowed_parity_pairs=allowed_parity_pairs,
        ):
            continue
        if repeat_min or repeat_max is not None:
            repeat_count = len(set(selected).intersection(latest_numbers))
            if repeat_count < repeat_min or repeat_count > repeat_max:
                continue
        if sequence_max is not None and _sequence_metrics(selected)["largest_sequence"] > sequence_max:
            continue
        if coverage_min is not None and _coverage_metrics(selected)["coverage_score"] < coverage_min:
            continue
        if entropy_min is not None and _entropy_score(selected) < entropy_min:
            continue
        if batch_number_usage:
            projected = dict(batch_number_usage)
            for number in selected:
                projected[int(number)] = int(projected.get(int(number), 0) or 0) + 1
            if any(int(projected.get(number, 0) or 0) > max_count for number in selected):
                continue
            if core_numbers_set and any(int(projected.get(number, 0) or 0) < min_count for number in core_numbers_set if number in selected):
                continue
        return selected
    return []


def _build_institutional_game_record(
    *,
    selected_numbers: list[int],
    candidate: dict[str, Any] | None = None,
    history_frequency: dict[int, int] | None = None,
    dezenas_per_game: int,
) -> dict[str, Any]:
    candidate = candidate or {}
    history_frequency = history_frequency or {}
    sequence_stats = _sequence_metrics(selected_numbers)
    coverage_stats = _coverage_metrics(selected_numbers)
    entropy_value = _entropy_score(selected_numbers)
    odd_count = sum(1 for number in selected_numbers if number % 2 != 0)
    even_count = len(selected_numbers) - odd_count
    structural_score = round(
        max(
            0.0,
            min(
                100.0,
                float(candidate.get("historical_intelligence", {}).get("profile_score", 0.0) or 0.0)
                * 0.45
                + float(candidate.get("final_score", {}).get("final_score", 0.0) or 0.0) * 0.30
                + coverage_stats["coverage_score"] * 25.0
                + entropy_value * 20.0
                - abs(odd_count - even_count) * 1.5,
            ),
        ),
        2,
    )
    return {
        "numbers": selected_numbers,
        "odd": odd_count,
        "even": even_count,
        "sum": sum(selected_numbers),
        "frame": len({((number - 1) // 5) for number in selected_numbers}),
        "center": sum(1 for number in selected_numbers if 8 <= number <= 18),
        "quadra_score": {
            "found_quadras": int(candidate.get("quadra_score", {}).get("found_quadras", 0) or 0),
            "average_rank": float(candidate.get("quadra_score", {}).get("average_rank", 0.0) or 0.0),
        },
        "final_score": {
            "final_score": structural_score,
            "components": {
                "structural_score": structural_score,
                "coverage_score": coverage_stats["coverage_score"],
                "entropy_score": entropy_value,
                "sequence_score": max(0.0, 1.0 - (sequence_stats["largest_sequence"] / max(1, dezenas_per_game))),
            },
        },
        "historical_intelligence": {
            "profile_type": str(candidate.get("profile_type", "")),
            "profile_score": float(candidate.get("historical_intelligence", {}).get("profile_score", 0.0) or 0.0),
            "coverage_score": coverage_stats["coverage_score"],
            "entropy_score": entropy_value,
            "sequence_max": sequence_stats["largest_sequence"],
            "dominant_numbers": [
                {"number": int(number), "frequency": int(history_frequency.get(int(number), 0))}
                for number in selected_numbers
            ],
        },
        "profile_type": str(candidate.get("profile_type", "")),
        "profile_score": float(candidate.get("historical_intelligence", {}).get("profile_score", 0.0) or 0.0),
        "ml_enabled": False,
        "structural_metrics": {
            "coverage_score": coverage_stats["coverage_score"],
            "entropy_score": entropy_value,
            "sequence_max": sequence_stats["largest_sequence"],
            "block_distribution": coverage_stats["block_distribution"],
        },
    }


def _build_simulated_draw(size: int = 15) -> list[int]:
    return sorted(random.sample(range(1, 26), k=max(1, min(size, 25))))


def _extract_int_numbers(raw_text: str) -> list[int]:
    numbers: list[int] = []
    for token in re.findall(r"\d+", str(raw_text or "")):
        number = int(token)
        if 1 <= number <= 25 and number not in numbers:
            numbers.append(number)
    return sorted(numbers)


def _parse_draw_numbers(raw_text: str) -> list[int]:
    values: list[int] = []
    for token in str(raw_text or "").replace(",", " ").split():
        if token.isdigit():
            number = int(token)
            if 1 <= number <= 25 and number not in values:
                values.append(number)
    return sorted(values)


def _format_simulation_numbers(numbers: list[int], matched_numbers: list[int]) -> str:
    matched_set = set(int(number) for number in matched_numbers)
    fragments: list[str] = []
    for number in numbers:
        if int(number) in matched_set:
            fragments.append(
                f'<span style="color:#1b7f2a;font-weight:700;">{int(number):02d}</span>'
            )
        else:
            fragments.append(
                f'<span style="color:#9aa4b2;text-decoration:line-through;">{int(number):02d}</span>'
            )
    return " ".join(fragments)


def _run_institutional_generation(
    *,
    total_games: int,
    dezenas_per_game: int,
    use_top50: bool,
    odd_min: int,
    odd_max: int,
    even_min: int,
    even_max: int,
    sequence_max: int,
    coverage_min: float,
    entropy_min: float,
    repeat_limit: int,
    snapshot: dict[str, Any],
) -> None:
    st.session_state["institutional_last_ui_event"] = "operacional:gerar_jogos"
    st.session_state.pop("institutional_generation_batch_result", None)
    started = time.monotonic()
    seed = int(time.time()) % 1_000_000
    batch_id = _institutional_output_batch_id()
    policy = _institutional_generation_policy(dezenas_per_game)
    repeat_min = int(policy.get("repeat_min", 0) or 0)
    repeat_max = int(policy.get("repeat_max", repeat_limit) or repeat_limit)
    preferred_parity_pairs = list(policy.get("preferred_parity_pairs", []) or [])
    allowed_parity_pairs = list(policy.get("allowed_parity_pairs", []) or [])
    preferred_profile_ratios = dict(policy.get("preferred_profile_ratios", {}) or {})
    core_numbers = [int(number) for number in (policy.get("core_numbers", []) or [])]
    discouraged_numbers = [int(number) for number in (policy.get("discouraged_numbers", []) or [])]
    max_frequency_ratio = float(policy.get("max_frequency_ratio", 1.0) or 1.0)
    min_frequency_ratio = float(policy.get("min_frequency_ratio", 0.0) or 0.0)
    effective_sequence_max = int(min(sequence_max, int(policy.get("sequence_max", sequence_max) or sequence_max)))
    effective_coverage_min = max(float(coverage_min), float(policy.get("coverage_min", coverage_min) or coverage_min))
    effective_entropy_min = max(float(entropy_min), float(policy.get("entropy_min", entropy_min) or entropy_min))
    latest_contest = _load_latest_contest_summary()
    target_contest = int(latest_contest["contest_number"]) if latest_contest else None
    history_frequency = _history_number_frequency()
    latest_numbers = set(int(number) for number in (latest_contest or {}).get("dezenas", []))
    candidate_count = max(total_games * 5, 50 if use_top50 else 30)
    ranked_candidates = generate_ranked_games(total_games=candidate_count, seed=seed, ml_enabled=False, pool_size=max(candidate_count, 30))
    games: list[dict[str, Any]] = []
    used_signatures: set[str] = set(load_batch_output_signatures(batch_id))
    batch_number_usage = batch_number_usage if batch_number_usage is not None else {}
    batch_profile_usage = batch_profile_usage if batch_profile_usage is not None else {}
    batch_total_games = max(1, int(batch_total_games or total_games))
    for candidate in ranked_candidates:
        selected_numbers = _select_subset_from_candidate(
            list(candidate.get("numbers", [])),
            target_size=dezenas_per_game,
            frequency_map=history_frequency,
            latest_numbers=latest_numbers,
            batch_number_usage=batch_number_usage,
            batch_total_games=batch_total_games,
            batch_profile_usage=batch_profile_usage,
            core_numbers=core_numbers,
            discouraged_numbers=discouraged_numbers,
            max_frequency_ratio=max_frequency_ratio,
            min_frequency_ratio=min_frequency_ratio,
            preferred_profile_ratios=preferred_profile_ratios,
            odd_min=odd_min,
            odd_max=odd_max,
            even_min=even_min,
            even_max=even_max,
            sequence_max=effective_sequence_max,
            coverage_min=effective_coverage_min,
            entropy_min=effective_entropy_min,
            repeat_min=repeat_min,
            repeat_max=repeat_max,
            preferred_parity_pairs=preferred_parity_pairs,
            allowed_parity_pairs=allowed_parity_pairs,
        )
        if not selected_numbers:
            selected_numbers = _force_subset_from_universe(
                target_size=dezenas_per_game,
                frequency_map=history_frequency,
                latest_numbers=latest_numbers,
                batch_number_usage=batch_number_usage,
                batch_total_games=batch_total_games,
                batch_profile_usage=batch_profile_usage,
                core_numbers=core_numbers,
                discouraged_numbers=discouraged_numbers,
                max_frequency_ratio=max_frequency_ratio,
                min_frequency_ratio=min_frequency_ratio,
                preferred_profile_ratios=preferred_profile_ratios,
                odd_min=odd_min,
                odd_max=odd_max,
                even_min=even_min,
                even_max=even_max,
                preferred_parity_pairs=preferred_parity_pairs,
                repeat_min=repeat_min,
                repeat_max=repeat_max,
                sequence_max=effective_sequence_max,
                coverage_min=effective_coverage_min,
                entropy_min=effective_entropy_min,
                allowed_parity_pairs=allowed_parity_pairs,
                offset=len(games),
            )
        if not selected_numbers:
            continue
        signature = _game_signature(selected_numbers)
        if signature in used_signatures:
            continue
        games.append(
            _build_institutional_game_record(
                selected_numbers=selected_numbers,
                candidate=dict(candidate),
                history_frequency=history_frequency,
                dezenas_per_game=dezenas_per_game,
            )
        )
        profile_pair = (
            sum(1 for number in selected_numbers if number % 2 != 0),
            sum(1 for number in selected_numbers if number % 2 == 0),
        )
        batch_profile_usage[profile_pair] = int(batch_profile_usage.get(profile_pair, 0) or 0) + 1
        for number in selected_numbers:
            batch_number_usage[int(number)] = int(batch_number_usage.get(int(number), 0) or 0) + 1
        used_signatures.add(signature)
        if len(games) >= total_games:
            break

    fallback_attempt = 0
    while len(games) < total_games and fallback_attempt < max(total_games * 25, 50):
        candidate = ranked_candidates[fallback_attempt % len(ranked_candidates)] if ranked_candidates else {}
        fallback_numbers = _force_subset_from_universe(
            target_size=dezenas_per_game,
            frequency_map=history_frequency,
            latest_numbers=latest_numbers,
            batch_number_usage=batch_number_usage,
            batch_total_games=batch_total_games,
            batch_profile_usage=batch_profile_usage,
            core_numbers=core_numbers,
            discouraged_numbers=discouraged_numbers,
            max_frequency_ratio=max_frequency_ratio,
            min_frequency_ratio=min_frequency_ratio,
            preferred_profile_ratios=preferred_profile_ratios,
            odd_min=odd_min,
            odd_max=odd_max,
            even_min=even_min,
            even_max=even_max,
            preferred_parity_pairs=preferred_parity_pairs,
            repeat_min=repeat_min,
            repeat_max=repeat_max,
            sequence_max=effective_sequence_max,
            coverage_min=effective_coverage_min,
            entropy_min=effective_entropy_min,
            allowed_parity_pairs=allowed_parity_pairs,
            offset=seed + fallback_attempt,
        )
        fallback_attempt += 1
        if not fallback_numbers:
            continue
        signature = _game_signature(fallback_numbers)
        if signature in used_signatures:
            continue
        games.append(
            _build_institutional_game_record(
                selected_numbers=fallback_numbers,
                candidate=dict(candidate),
                history_frequency=history_frequency,
                dezenas_per_game=dezenas_per_game,
            )
        )
        profile_pair = (
            sum(1 for number in fallback_numbers if number % 2 != 0),
            sum(1 for number in fallback_numbers if number % 2 == 0),
        )
        batch_profile_usage[profile_pair] = int(batch_profile_usage.get(profile_pair, 0) or 0) + 1
        for number in fallback_numbers:
            batch_number_usage[int(number)] = int(batch_number_usage.get(int(number), 0) or 0) + 1
        used_signatures.add(signature)
    commander_report = output_commander_validate_games(
        games,
        batch_id=batch_id,
        generation_event_id=None,
        target_size=dezenas_per_game,
        required_total=total_games,
        candidate_total=total_games,
        persisted_signatures=set(load_batch_output_signatures(batch_id)),
    )
    if commander_report.get("status_comandante_saida") != "APROVADO" or int(commander_report.get("quantidade_jogos_unicos", 0) or 0) != int(total_games):
        approved_total = int(commander_report.get("quantidade_jogos_aprovados", len(games)) or len(games))
        rejected_total = int(commander_report.get("quantidade_jogos_rejeitados", max(0, total_games - approved_total)) or max(0, total_games - approved_total))
        blocked_reason = str(
            commander_report.get("motivo_bloqueio")
            or commander_report.get("error_message")
            or "nao foi possivel gerar a quantidade solicitada de jogos unicos"
        )
        st.session_state["institutional_generation"] = {
            "seed": seed,
            "games": [],
            "total_games": total_games,
            "dezenas_per_game": dezenas_per_game,
            "use_top50": use_top50,
            "core_numbers": core_numbers,
            "discouraged_numbers": discouraged_numbers,
            "max_frequency_ratio": max_frequency_ratio,
            "min_frequency_ratio": min_frequency_ratio,
            "repeticao_ultimo_concurso_min": repeat_min,
            "repeticao_ultimo_concurso_max": repeat_max,
            "perfis_paridade_preferenciais": preferred_parity_pairs,
            "perfis_paridade_permitidos": allowed_parity_pairs,
            "limite_sequencia_max": effective_sequence_max,
            "generation_event_id": None,
            "created_at": datetime.now(UTC).isoformat(),
            "runtime_status": "critical_error",
            "elapsed_time": round(time.monotonic() - started, 3),
            "batch_id": batch_id,
            "output_commander": commander_report,
        }
        st.session_state["institutional_generation_result"] = {
            "generation_event_id": None,
            "seed": seed,
            "jogos": [],
            "quantidade_jogos_solicitada": total_games,
            "quantidade_dezenas_solicitada": dezenas_per_game,
            "total_esperado_jogos": int(total_games) * int(1 if total_games else 0),
            "repeticao_ultimo_concurso_min": repeat_min,
            "repeticao_ultimo_concurso_max": repeat_max,
            "perfis_paridade_preferenciais": preferred_parity_pairs,
            "perfis_paridade_permitidos": allowed_parity_pairs,
            "limite_sequencia_max": effective_sequence_max,
            "quantidade_jogos_candidatos": int(commander_report.get("quantidade_jogos_candidatos", total_games) or total_games),
            "quantidade_jogos_aprovados": approved_total,
            "quantidade_jogos_real_gerada": approved_total,
            "quantidade_jogos_persistida": 0,
            "len_todos_os_jogos": [],
            "primeiro_jogo": [],
            "len_primeiro_jogo": 0,
            "batch_id": batch_id,
            "status_comandante_saida": "BLOQUEADO",
            "total_jogos_unicos": int(commander_report.get("quantidade_jogos_unicos", 0) or 0),
            "total_jogos_duplicados": int(commander_report.get("quantidade_jogos_duplicados", 0) or 0),
            "total_jogos_rejeitados": rejected_total,
            "motivo_bloqueio": blocked_reason,
            "taxa_duplicidade": float(commander_report.get("taxa_duplicidade", 0.0) or 0.0),
            "error_message": blocked_reason,
            "duplicate_hashes": list(commander_report.get("duplicate_hashes", []) or []),
            "invalid_games": list(commander_report.get("invalid_games", []) or []),
        }
        return
    generation_snapshot = _persist_generation_snapshot(
        games=games,
        seed=seed,
        target_contest=target_contest,
        batch_id=batch_id,
        generation_context={
            "dezenas_per_game": dezenas_per_game,
            "total_games": total_games,
            "use_top50": use_top50,
            "core_numbers": core_numbers,
            "discouraged_numbers": discouraged_numbers,
            "max_frequency_ratio": max_frequency_ratio,
            "min_frequency_ratio": min_frequency_ratio,
            "odd_min": odd_min,
            "odd_max": odd_max,
            "even_min": even_min,
            "even_max": even_max,
            "sequence_max": effective_sequence_max,
            "coverage_min": effective_coverage_min,
            "entropy_min": effective_entropy_min,
            "repeat_limit": repeat_limit,
            "repeticao_ultimo_concurso_min": repeat_min,
            "repeticao_ultimo_concurso_max": repeat_max,
            "perfis_paridade_preferenciais": preferred_parity_pairs,
            "perfis_paridade_permitidos": allowed_parity_pairs,
            "limite_sequencia_max": effective_sequence_max,
            "batch_id": batch_id,
            "game_signatures": [game.get("game_signature", "") for game in commander_report.get("accepted_games", [])],
            "total_jogos_unicos": int(commander_report.get("quantidade_jogos_unicos", len(games)) or len(games)),
            "total_jogos_duplicados": int(commander_report.get("quantidade_jogos_duplicados", 0) or 0),
            "taxa_duplicidade": float(commander_report.get("taxa_duplicidade", 0.0) or 0.0),
            "status_comandante_saida": str(commander_report.get("status_comandante_saida", "APROVADO") or "APROVADO"),
        },
    )
    st.session_state["institutional_generation"] = {
        "seed": seed,
        "games": games,
        "total_games": total_games,
        "dezenas_per_game": dezenas_per_game,
        "use_top50": use_top50,
        "core_numbers": core_numbers,
        "discouraged_numbers": discouraged_numbers,
        "max_frequency_ratio": max_frequency_ratio,
        "min_frequency_ratio": min_frequency_ratio,
        "repeticao_ultimo_concurso_min": repeat_min,
        "repeticao_ultimo_concurso_max": repeat_max,
        "perfis_paridade_preferenciais": preferred_parity_pairs,
        "perfis_paridade_permitidos": allowed_parity_pairs,
        "limite_sequencia_max": effective_sequence_max,
        "generation_event_id": generation_snapshot["generation_event_id"],
        "created_at": datetime.now(UTC).isoformat(),
        "runtime_status": "generated",
        "elapsed_time": round(time.monotonic() - started, 3),
        "batch_id": batch_id,
        "output_commander": commander_report,
    }
    st.session_state["institutional_generation_result"] = {
        "generation_event_id": generation_snapshot["generation_event_id"],
        "seed": seed,
        "jogos": games,
        "quantidade_jogos_solicitada": total_games,
        "quantidade_dezenas_solicitada": dezenas_per_game,
        "total_esperado_jogos": int(total_games) * 1,
        "repeticao_ultimo_concurso_min": repeat_min,
        "repeticao_ultimo_concurso_max": repeat_max,
        "perfis_paridade_preferenciais": preferred_parity_pairs,
        "perfis_paridade_permitidos": allowed_parity_pairs,
        "limite_sequencia_max": effective_sequence_max,
        "quantidade_jogos_candidatos": int(commander_report.get("quantidade_jogos_candidatos", total_games) or total_games),
        "quantidade_jogos_aprovados": int(commander_report.get("quantidade_jogos_aprovados", len(games)) or len(games)),
        "quantidade_jogos_real_gerada": len(games),
        "quantidade_jogos_persistida": int(generation_snapshot.get("games_count", 0) or 0),
        "len_todos_os_jogos": [len(game.get("numbers", [])) for game in games],
        "primeiro_jogo": games[0]["numbers"] if games else [],
        "len_primeiro_jogo": len(games[0]["numbers"]) if games else 0,
        "batch_id": batch_id,
        "status_comandante_saida": commander_report.get("status_comandante_saida", "APROVADO"),
        "total_jogos_unicos": int(commander_report.get("quantidade_jogos_unicos", len(games)) or len(games)),
        "total_jogos_duplicados": int(commander_report.get("quantidade_jogos_duplicados", 0) or 0),
        "total_jogos_rejeitados": int(commander_report.get("quantidade_jogos_rejeitados", 0) or 0),
        "motivo_bloqueio": str(commander_report.get("motivo_bloqueio", "") or ""),
        "taxa_duplicidade": float(commander_report.get("taxa_duplicidade", 0.0) or 0.0),
        "duplicate_hashes": list(commander_report.get("duplicate_hashes", []) or []),
        "invalid_games": list(commander_report.get("invalid_games", []) or []),
    }


def _run_institutional_generation_batch(
    *,
    generation_runs: int,
    total_games: int,
    dezenas_per_game: int,
    use_top50: bool,
    odd_min: int,
    odd_max: int,
    even_min: int,
    even_max: int,
    sequence_max: int,
    coverage_min: float,
    entropy_min: float,
    repeat_limit: int,
    snapshot: dict[str, Any],
    batch_number_usage: dict[int, int] | None = None,
    batch_profile_usage: dict[tuple[int, int], int] | None = None,
    batch_total_games: int | None = None,
) -> None:
    batch_runs = max(1, int(generation_runs))
    batch_id = _institutional_output_batch_id()
    policy = _institutional_generation_policy(dezenas_per_game)
    repeat_min = int(policy.get("repeat_min", 0) or 0)
    repeat_max = int(policy.get("repeat_max", repeat_limit) or repeat_limit)
    preferred_parity_pairs = list(policy.get("preferred_parity_pairs", []) or [])
    allowed_parity_pairs = list(policy.get("allowed_parity_pairs", []) or [])
    preferred_profile_ratios = dict(policy.get("preferred_profile_ratios", {}) or {})
    core_numbers = [int(number) for number in (policy.get("core_numbers", []) or [])]
    discouraged_numbers = [int(number) for number in (policy.get("discouraged_numbers", []) or [])]
    max_frequency_ratio = float(policy.get("max_frequency_ratio", 1.0) or 1.0)
    min_frequency_ratio = float(policy.get("min_frequency_ratio", 0.0) or 0.0)
    effective_sequence_max = int(min(sequence_max, int(policy.get("sequence_max", sequence_max) or sequence_max)))
    st.session_state["institutional_generation_batch_result"] = {}
    batch_number_usage: dict[int, int] = {}
    batch_profile_usage: dict[tuple[int, int], int] = {}
    batch_total_games = int(total_games) * batch_runs
    run_summaries: list[dict[str, Any]] = []
    for run_index in range(batch_runs):
        _run_institutional_generation(
            total_games=total_games,
            dezenas_per_game=dezenas_per_game,
            use_top50=use_top50,
            odd_min=odd_min,
            odd_max=odd_max,
            even_min=even_min,
            even_max=even_max,
            sequence_max=sequence_max,
            coverage_min=coverage_min,
            entropy_min=entropy_min,
            repeat_limit=repeat_limit,
            snapshot=snapshot,
            batch_number_usage=batch_number_usage,
            batch_profile_usage=batch_profile_usage,
            batch_total_games=batch_total_games,
        )
        generation_result = dict(st.session_state.get("institutional_generation_result") or {})
        run_summaries.append(generation_result)
        if str(generation_result.get("status_comandante_saida", "APROVADO") or "APROVADO") != "APROVADO":
            break
        if run_index + 1 < batch_runs:
            continue

    batch_signatures = load_batch_output_signatures(batch_id)
    batch_total_requested = sum(int(item.get("quantidade_jogos_solicitada", 0) or 0) for item in run_summaries)
    batch_total_candidates = sum(int(item.get("quantidade_jogos_candidatos", 0) or 0) for item in run_summaries)
    batch_total_approved = sum(int(item.get("quantidade_jogos_aprovados", 0) or 0) for item in run_summaries)
    batch_total_generated = sum(int(item.get("quantidade_jogos_real_gerada", 0) or 0) for item in run_summaries)
    batch_total_unique = len(batch_signatures)
    batch_total_duplicates = max(0, batch_total_generated - batch_total_unique)
    batch_total_rejected = max(0, batch_total_requested - batch_total_approved)
    batch_status = "APROVADO" if batch_total_requested == batch_total_approved == batch_total_generated == batch_total_unique and batch_total_duplicates == 0 else "BLOQUEADO"
    batch_reason = "OK" if batch_status == "APROVADO" else "não foi possível gerar a quantidade solicitada de jogos únicos"
    st.session_state["institutional_generation_batch_result"] = {
        "batch_id": batch_id,
        "quantidade_jogos_por_geracao": int(total_games),
        "quantidade_geracoes_na_bateria": batch_runs,
        "quantidade_dezenas_por_jogo": int(dezenas_per_game),
        "total_jogos_esperados": int(total_games) * batch_runs,
        "total_esperado_jogos": int(total_games) * batch_runs,
        "repeticao_ultimo_concurso_min": repeat_min,
        "repeticao_ultimo_concurso_max": repeat_max,
        "perfis_paridade_preferenciais": preferred_parity_pairs,
        "perfis_paridade_permitidos": allowed_parity_pairs,
        "limite_sequencia_max": effective_sequence_max,
        "core_numbers": core_numbers,
        "discouraged_numbers": discouraged_numbers,
        "max_frequency_ratio": max_frequency_ratio,
        "min_frequency_ratio": min_frequency_ratio,
        "total_gens_solicitadas": batch_runs,
        "total_jogos_solicitados": batch_total_requested,
        "total_jogos_candidatos": batch_total_candidates,
        "total_jogos_aprovados": batch_total_approved,
        "total_jogos_gerados": batch_total_generated,
        "total_jogos_unicos": batch_total_unique,
        "total_jogos_duplicados": batch_total_duplicates,
        "total_jogos_rejeitados": batch_total_rejected,
        "taxa_duplicidade": round(batch_total_duplicates / max(1, batch_total_generated), 4),
        "status_comandante_saida": batch_status,
        "motivo_bloqueio": batch_reason,
        "institutional_output_signatures": batch_total_unique,
    }


def _load_persisted_generation_event_groups() -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    with get_session(DB_PATH) as session:
        events = (
            session.query(GenerationEvent)
            .order_by(GenerationEvent.created_at.desc(), GenerationEvent.id.desc())
            .all()
        )
        for event in events:
            rows = (
                session.query(GeneratedGame)
                .filter(GeneratedGame.generation_event_id == event.id)
                .order_by(GeneratedGame.game_index.asc())
                .all()
            )
            games: list[dict[str, Any]] = []
            for row in rows:
                numbers = [int(number) for number in (row.numbers or [])]
                context_json = dict(row.context_json or {})
                structural_metrics = dict(context_json.get("structural_metrics") or {})
                games.append(
                    {
                        "game_index": int(row.game_index or 0),
                        "numbers": numbers,
                        "profile_type": str(row.profile_type or ""),
                        "score": round(float((row.final_score or {}).get("final_score", 0.0) or 0.0), 4),
                        "coverage": round(float(structural_metrics.get("coverage_score", 0.0) or 0.0), 4),
                        "entropy": round(float(structural_metrics.get("entropy_score", 0.0) or 0.0), 4),
                        "odd": sum(1 for number in numbers if number % 2 != 0),
                        "even": sum(1 for number in numbers if number % 2 == 0),
                        "frame": len({((number - 1) // 5) for number in numbers}),
                        "center": sum(1 for number in numbers if 8 <= number <= 18),
                    }
                )
            target_contests: list[int] = []
            for row in rows:
                value = _safe_int(_safe_get(row, "target_contest"), default=None)
                if value is not None and value > 0:
                    target_contests.append(value)
            groups.append(
                {
                    "generation_event_id": int(event.id or 0),
                    "created_at": event.created_at.isoformat() if getattr(event, "created_at", None) else "",
                    "seed": int(getattr(event, "seed", 0) or 0),
                    "strategy": str(getattr(event, "strategy", "") or ""),
                    "total_games": len(games),
                    "target_contest": max(target_contests) if target_contests else None,
                    "games": games,
                    "structural_summary": _summarize_games_structurally([game["numbers"] for game in games]),
                }
            )
    return groups


def _run_institutional_conference(contest_number: int | None = None) -> None:
    selected_contest = _safe_int(contest_number, default=None)
    latest_contest = _load_imported_contest(selected_contest) or _get_latest_contest()
    if latest_contest is None:
        st.session_state["institutional_check_result"] = {
            "status": "waiting_contest",
            "warning": "imported_contests ainda est? vazio. Sincronize o resultado oficial para habilitar a confer?ncia autom?tica.",
        }
        return
    grouped_generations = _load_persisted_generation_event_groups()
    if not grouped_generations:
        st.session_state["institutional_check_result"] = {"warning": "Gere jogos antes de conferir."}
        return
    generation_results: list[dict[str, Any]] = []
    total_prizes = 0
    total_hits = 0
    best_hits_global = 0
    latest_imported_contest_number = _safe_int(_safe_get(latest_contest, "contest_number"), default=None)
    for group in grouped_generations:
        group_target_contest = _safe_int(_safe_get(group, "target_contest"), default=None)
        contest_to_use = selected_contest or group_target_contest or latest_imported_contest_number
        contest_payload = _load_imported_contest(contest_to_use) if contest_to_use else latest_contest
        if contest_payload is None:
            contest_payload = latest_contest
        comparison = _compare_games_against_contest(
            generation_event_id=int(group.get("generation_event_id") or 0),
            games=list(group.get("games") or []),
            contest=contest_payload,
        )
        hit_counts = Counter(int(row.get("hits", 0) or 0) for row in comparison.get("results", []))
        generation_results.append(
            {
                "generation_event_id": int(group.get("generation_event_id") or 0),
                "created_at": group.get("created_at", ""),
                "seed": int(group.get("seed") or 0),
                "total_games": int(group.get("total_games") or 0),
                "target_contest": contest_to_use,
                "best_hits": int(comparison.get("best_hits", 0) or 0),
                "total_hits": int(comparison.get("total_hits", 0) or 0),
                "prize_count": int(comparison.get("prize_count", 0) or 0),
                "hit_distribution": dict(sorted(hit_counts.items(), key=lambda item: (-item[0], item[1]))),
                "results": list(comparison.get("results", [])),
                "games": list(group.get("games") or []),
                "contest_number": int(comparison.get("contest_number", contest_to_use or 0) or 0),
                "contest_date": str(comparison.get("contest_date", _safe_get(contest_payload, "data", "")) or ""),
            }
        )
        total_prizes += int(comparison.get("prize_count", 0) or 0)
        total_hits += int(comparison.get("total_hits", 0) or 0)
        best_hits_global = max(best_hits_global, int(comparison.get("best_hits", 0) or 0))
    st.session_state["institutional_check"] = {
        "runtime_status": "checked",
        "timestamp": datetime.now(UTC).isoformat(),
        "contest_number": int(latest_contest.get("contest_number", 0) or 0),
        "best_hits": best_hits_global,
        "total_hits": total_hits,
    }
    st.session_state["institutional_check_result"] = {
        "status": "checked",
        "contest_number": int(latest_contest.get("contest_number", 0) or 0),
        "contest_date": str(latest_contest.get("data", "") or ""),
        "dezenas": list(latest_contest.get("dezenas", []) or []),
        "generation_results": generation_results,
        "best_hits": best_hits_global,
        "total_hits": total_hits,
        "prize_count": total_prizes,
    }


def _run_institutional_simulation(*, drawn_numbers: list[int] | None = None) -> None:
    st.session_state["institutional_last_ui_event"] = "operacional:simular_resultado"
    try:
        simulated_numbers = sorted(drawn_numbers or _build_simulated_draw(15))
        source = "session_generation"
        generation_state = st.session_state.get("institutional_generation") or {}
        games = list(generation_state.get("games") or [])
        if not games:
            source = "session_generation_result"
            generation_result = st.session_state.get("institutional_generation_result") or {}
            games = list(generation_result.get("jogos") or [])
        if not games:
            source = "latest_persisted_generation"
            games = _institutional_generation_games()
        if not games:
            source = "all_persisted_games"
            games = [game for group in _load_persisted_generation_event_groups() for game in list(group.get("games") or [])]
        simulation_rows: list[dict[str, Any]] = []
        for index, game in enumerate(games, start=1):
            numbers = sorted(int(number) for number in game.get("numbers", []))
            matched = sorted(set(numbers) & set(simulated_numbers))
            simulation_rows.append(
                {
                    "jogo": index,
                    "dezenas": " ".join(f"{number:02d}" for number in numbers),
                    "resultado": _format_simulation_numbers(numbers, matched),
                    "hits": len(matched),
                    "premiado": "sim" if len(matched) >= 11 else "nao",
                    "matched_numbers": matched,
                    "generation_event_id": int(game.get("generation_event_id", 0) or 0),
                    "profile_type": str(game.get("profile_type", "") or ""),
                    "score": float(game.get("score", game.get("final_score", {}).get("final_score", 0.0)) or 0.0),
                    "odd": int(game.get("odd", 0) or 0),
                    "even": int(game.get("even", 0) or 0),
                    "entropy": float(game.get("entropy", 0.0) or 0.0),
                    "coverage": float(game.get("coverage", 0.0) or 0.0),
                }
            )
        premium_rows = [row for row in simulation_rows if int(row.get("hits", 0) or 0) >= 11]
        st.session_state["institutional_simulation"] = {
            "runtime_status": "simulated",
            "timestamp": datetime.now(UTC).isoformat(),
            "contest_numbers": simulated_numbers,
            "source": source,
            "loaded_games": len(games),
            "compared_games": len(simulation_rows),
            "premium_games": len(premium_rows),
            "results": simulation_rows,
            "summary": {
                "source": source,
                "loaded_games": len(games),
                "compared_games": len(simulation_rows),
                "premium_games": len(premium_rows),
                "contest_numbers": simulated_numbers,
            },
        }
        st.session_state["institutional_simulation_result"] = simulation_rows
        st.session_state["institutional_simulation_error"] = None
    except Exception as exc:  # pragma: no cover - diagnostic path
        st.session_state["institutional_simulation"] = {
            "runtime_status": "error",
            "timestamp": datetime.now(UTC).isoformat(),
            "contest_numbers": sorted(drawn_numbers or []),
            "results": [],
            "source": "error",
            "loaded_games": 0,
            "compared_games": 0,
            "premium_games": 0,
            "summary": {
                "source": "error",
                "loaded_games": 0,
                "compared_games": 0,
                "premium_games": 0,
            },
        }
        st.session_state["institutional_simulation_result"] = []
        st.session_state["institutional_simulation_error"] = {
            "error": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        }
        st.exception(exc)


def _institutional_generation_games() -> list[dict[str, Any]]:
    generation_state = st.session_state.get("institutional_generation") or {}
    if generation_state.get("games"):
        return list(generation_state.get("games") or [])
    persisted_generation = _load_latest_generated_games()
    if persisted_generation and persisted_generation.get("games"):
        return list(persisted_generation.get("games") or [])
    return []


def _summarize_games_structurally(games: list[Any]) -> dict[str, Any]:
    normalized_games: list[list[int]] = []
    for game in games:
        if isinstance(game, dict):
            raw_numbers = game.get("numbers", [])
        else:
            raw_numbers = game
        numbers = [int(number) for number in raw_numbers or [] if str(number).isdigit() or isinstance(number, int)]
        if numbers:
            normalized_games.append(sorted(numbers))
    if not normalized_games:
        return {
            "games": 0,
            "average_overlap": 0.0,
            "average_unique_numbers": 0.0,
            "dominant_numbers": [],
            "number_frequency": {},
        }
    frequencies: dict[int, int] = {}
    total_unique = 0
    pairwise_overlap = 0
    pair_count = 0
    for numbers in normalized_games:
        total_unique += len(set(numbers))
        for number in numbers:
            frequencies[number] = frequencies.get(number, 0) + 1
    for index, left in enumerate(normalized_games):
        left_set = set(left)
        for right in normalized_games[index + 1 :]:
            pairwise_overlap += len(left_set & set(right))
            pair_count += 1
    dominant_numbers = [
        {"number": number, "frequency": frequency}
        for number, frequency in sorted(frequencies.items(), key=lambda item: (-item[1], item[0]))[:10]
    ]
    return {
        "games": len(normalized_games),
        "average_overlap": round(pairwise_overlap / pair_count, 4) if pair_count else 0.0,
        "average_unique_numbers": round(total_unique / len(normalized_games), 4),
        "dominant_numbers": dominant_numbers,
        "number_frequency": {str(number): frequency for number, frequency in sorted(frequencies.items())},
    }


def _load_latest_reconciliation_summary() -> dict[str, Any] | None:
    with get_session(DB_PATH) as session:
        run = session.query(ReconciliationRun).order_by(ReconciliationRun.id.desc()).first()
        if run is None:
            return None
        games_rows = (
            session.query(ReconciliationGame)
            .filter(ReconciliationGame.reconciliation_run_id == run.id)
            .order_by(ReconciliationGame.game_index.asc())
            .all()
        )
        matched_numbers: set[int] = set()
        hit_counts: Counter[int] = Counter()
        for row in games_rows:
            hits = int(getattr(row, "hits", 0) or 0)
            hit_counts[hits] += 1
            matched_numbers.update(int(number) for number in (row.matched_numbers or []))
        return {
            "id": int(run.id or 0),
            "contest_id": int(getattr(run, "contest_id", 0) or 0),
            "generation_event_id": int(getattr(run, "generation_event_id", 0) or 0),
            "status": str(getattr(run, "status", "") or ""),
            "prize_count": int(getattr(run, "prize_count", 0) or 0),
            "total_hits": int(getattr(run, "total_hits", 0) or 0),
            "best_hits": int(getattr(run, "best_hits", 0) or 0),
            "games_count": len(games_rows),
            "matched_numbers": sorted(matched_numbers),
            "hit_distribution": dict(sorted(hit_counts.items(), key=lambda item: (-item[0], item[1]))),
            "created_at": run.created_at.isoformat() if getattr(run, "created_at", None) else "",
        }


def _mean_or_zero(values: list[float]) -> float:
    values = [float(value) for value in values if value is not None]
    return round(sum(values) / len(values), 4) if values else 0.0


def _load_latest_reconciliation_for_generation(session: Any, generation_event_id: int) -> dict[str, Any] | None:
    run = (
        session.query(ReconciliationRun)
        .filter(ReconciliationRun.generation_event_id == int(generation_event_id))
        .order_by(ReconciliationRun.created_at.desc(), ReconciliationRun.id.desc())
        .first()
    )
    if run is None:
        return None
    games_rows = (
        session.query(ReconciliationGame)
        .filter(ReconciliationGame.reconciliation_run_id == run.id)
        .order_by(ReconciliationGame.game_index.asc())
        .all()
    )
    matched_numbers: set[int] = set()
    hit_counts: Counter[int] = Counter()
    games_by_index: dict[int, dict[str, Any]] = {}
    for row in games_rows:
        hits = int(getattr(row, "hits", 0) or 0)
        matched = [int(number) for number in (row.matched_numbers or [])]
        hit_counts[hits] += 1
        matched_numbers.update(matched)
        games_by_index[int(getattr(row, "game_index", 0) or 0)] = {
            "reconciliation_id": int(run.id or 0),
            "contest_id": int(getattr(row, "contest_id", 0) or 0),
            "hits": hits,
            "matched_numbers": matched,
            "prize_status": str(getattr(row, "prize_status", "") or ""),
            "prize_tier": str(getattr(row, "prize_tier", "") or ""),
            "status": str(getattr(run, "status", "") or ""),
            "reconciled_at": run.created_at.isoformat() if getattr(run, "created_at", None) else "",
        }
    return {
        "id": int(run.id or 0),
        "contest_id": int(getattr(run, "contest_id", 0) or 0),
        "generation_event_id": int(getattr(run, "generation_event_id", 0) or 0),
        "status": str(getattr(run, "status", "") or ""),
        "prize_count": int(getattr(run, "prize_count", 0) or 0),
        "total_hits": int(getattr(run, "total_hits", 0) or 0),
        "best_hits": int(getattr(run, "best_hits", 0) or 0),
        "games_count": len(games_rows),
        "matched_numbers": sorted(matched_numbers),
        "hit_distribution": dict(sorted(hit_counts.items(), key=lambda item: (-item[0], item[1]))),
        "created_at": run.created_at.isoformat() if getattr(run, "created_at", None) else "",
        "games_by_index": games_by_index,
    }


def _load_generation_history(limit: int | None = 12) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    with get_session(DB_PATH) as session:
        events_query = session.query(GenerationEvent).order_by(GenerationEvent.created_at.desc(), GenerationEvent.id.desc())
        if limit is not None and int(limit) > 0:
            events_query = events_query.limit(int(limit))
        events = events_query.all()
        for event in events:
            games_rows = (
                session.query(GeneratedGame)
                .filter(GeneratedGame.generation_event_id == event.id)
                .order_by(GeneratedGame.game_index.asc())
                .all()
            )
            reconciliation_summary = _load_latest_reconciliation_for_generation(session, int(event.id or 0))
            reconciliation_games = dict((reconciliation_summary or {}).get("games_by_index", {}))
            games: list[dict[str, Any]] = []
            scores: list[float] = []
            entropies: list[float] = []
            coverages: list[float] = []
            target_contests: list[int] = []
            for row in games_rows:
                numbers = [int(number) for number in (row.numbers or [])]
                final_score = dict(row.final_score or {})
                quadra_score = dict(row.quadra_score or {})
                context_json = dict(row.context_json or {})
                structural_metrics = dict(context_json.get("structural_metrics") or {})
                historical_intelligence = dict(context_json.get("historical_intelligence") or {})
                score_value = float(final_score.get("final_score", 0.0) or 0.0)
                entropy_value = float(
                    structural_metrics.get("entropy_score", historical_intelligence.get("entropy_score", 0.0)) or 0.0
                )
                coverage_value = float(
                    structural_metrics.get("coverage_score", historical_intelligence.get("coverage_score", 0.0)) or 0.0
                )
                odd_count = sum(1 for number in numbers if number % 2 != 0)
                even_count = len(numbers) - odd_count
                reconciliation_row = reconciliation_games.get(int(row.game_index or 0), {})
                games.append(
                    {
                        "game_index": int(row.game_index or 0),
                        "numbers": numbers,
                        "profile_type": str(row.profile_type or ""),
                        "origin": str(getattr(row, "origin", "") or "institutional"),
                        "generation_mode": str(getattr(row, "generation_mode", "") or ""),
                        "generation_context": dict(context_json),
                        "score": score_value,
                        "final_score": final_score,
                        "quadra_score": quadra_score,
                        "target_contest": int(row.target_contest) if getattr(row, "target_contest", None) is not None else None,
                        "coverage": round(coverage_value, 4),
                        "entropy": round(entropy_value, 4),
                        "sequence_max": int(structural_metrics.get("sequence_max", historical_intelligence.get("sequence_max", 0)) or 0),
                        "odd": odd_count,
                        "even": even_count,
                        "center": sum(1 for number in numbers if 8 <= number <= 18),
                        "frame": len({((number - 1) // 5) for number in numbers}),
                        "contest_id": int(reconciliation_row.get("contest_id", 0) or 0) if reconciliation_row else None,
                        "hits": int(reconciliation_row.get("hits", 0) or 0) if reconciliation_row else None,
                        "matched_numbers": list(reconciliation_row.get("matched_numbers", []) or []) if reconciliation_row else [],
                        "prize_status": str(reconciliation_row.get("prize_status", "") or "") if reconciliation_row else "",
                        "prize_tier": str(reconciliation_row.get("prize_tier", "") or "") if reconciliation_row else "",
                        "conference_status": "Conferido" if reconciliation_row else "Nao conferido",
                        "reconciliation_id": int(reconciliation_row.get("reconciliation_id", 0) or 0) if reconciliation_row else None,
                        "reconciled_at": str(reconciliation_row.get("reconciled_at", "") or "") if reconciliation_row else "",
                    }
                )
                scores.append(score_value)
                entropies.append(entropy_value)
                coverages.append(coverage_value)
                if getattr(row, "target_contest", None) is not None:
                    target_contests.append(int(row.target_contest))
            structural_summary = _summarize_games_structurally([game["numbers"] for game in games]) if games else {}
            top_games = sorted(games, key=lambda item: (-float(item["score"]), item["game_index"]))
            first_context = dict(games[0].get("generation_context") or {}) if games and isinstance(games[0], dict) else {}
            history.append(
                {
                    "generation_event_id": int(event.id or 0),
                    "created_at": event.created_at.isoformat() if getattr(event, "created_at", None) else "",
                    "seed": int(getattr(event, "seed", 0) or 0),
                    "strategy": str(getattr(event, "strategy", "") or ""),
                    "ml_enabled": bool(getattr(event, "ml_enabled", 0) or 0),
                    "total_games": len(games),
                    "target_contest": max(target_contests) if target_contests else None,
                    "first_name": str(getattr(event, "first_name", "") or ""),
                    "whatsapp": str(getattr(event, "whatsapp", "") or ""),
                    "avg_score": _mean_or_zero(scores),
                    "avg_entropy": _mean_or_zero(entropies),
                    "avg_coverage": _mean_or_zero(coverages),
                    "average_overlap": float(structural_summary.get("average_overlap", 0.0) or 0.0),
                    "dominant_numbers": list(structural_summary.get("dominant_numbers", [])),
                    "batch_id": str(first_context.get("batch_id", "") or ""),
                    "status_comandante_saida": str(first_context.get("status_comandante_saida", "APROVADO") or "APROVADO"),
                    "total_jogos_unicos": int(first_context.get("total_jogos_unicos", len(games)) or len(games)),
                    "total_jogos_duplicados": int(first_context.get("total_jogos_duplicados", 0) or 0),
                    "taxa_duplicidade": float(first_context.get("taxa_duplicidade", 0.0) or 0.0),
                    "reconciliation": reconciliation_summary or {},
                    "games": games,
                    "top_games": sorted(
                        games,
                        key=lambda item: (
                            -float(item["score"]),
                            -(int(item.get("hits") or -1) if item.get("hits") is not None else -1),
                            int(item["game_index"]),
                        ),
                    ),
                }
            )
    return history


def _load_reconciliation_history(limit: int = 12) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    with get_session(DB_PATH) as session:
        runs = (
            session.query(ReconciliationRun)
            .order_by(ReconciliationRun.created_at.desc(), ReconciliationRun.id.desc())
            .limit(limit)
            .all()
        )
        for run in runs:
            games_rows = (
                session.query(ReconciliationGame)
                .filter(ReconciliationGame.reconciliation_run_id == run.id)
                .order_by(ReconciliationGame.game_index.asc())
                .all()
            )
            matched_numbers: set[int] = set()
            for row in games_rows:
                matched_numbers.update(int(number) for number in (row.matched_numbers or []))
            history.append(
                {
                    "id": int(run.id or 0),
                    "generation_event_id": int(getattr(run, "generation_event_id", 0) or 0),
                    "contest_id": int(getattr(run, "contest_id", 0) or 0),
                    "status": str(getattr(run, "status", "") or ""),
                    "prize_count": int(getattr(run, "prize_count", 0) or 0),
                    "total_hits": int(getattr(run, "total_hits", 0) or 0),
                    "best_hits": int(getattr(run, "best_hits", 0) or 0),
                    "created_at": run.created_at.isoformat() if getattr(run, "created_at", None) else "",
                    "matched_numbers": sorted(matched_numbers),
                    "games_count": len(games_rows),
                }
            )
    return history


def _load_operational_logs_history(limit: int = 20) -> list[dict[str, Any]]:
    with get_session(DB_PATH) as session:
        inspector = inspect(session.get_bind())
        if "operational_logs" not in set(inspector.get_table_names()):
            return []
        try:
            rows = session.execute(
                text(
                    """
                    SELECT id, event_type, status, duration_ms, context_json, created_at
                    FROM operational_logs
                    ORDER BY created_at DESC, id DESC
                    LIMIT :limit
                    """
                ),
                {"limit": int(limit)},
            ).mappings().all()
        except Exception:
            return []
        history: list[dict[str, Any]] = []
        for row in rows:
            context_json = row.get("context_json", {})
            if isinstance(context_json, str):
                try:
                    context_json = json.loads(context_json or "{}")
                except Exception:
                    context_json = {}
            history.append(
                {
                    "id": int(row.get("id") or 0),
                    "event_type": str(row.get("event_type") or ""),
                    "status": str(row.get("status") or ""),
                    "duration_ms": float(row.get("duration_ms") or 0.0),
                    "created_at": row.get("created_at").isoformat() if getattr(row.get("created_at"), "isoformat", None) else str(row.get("created_at") or ""),
                    "context_json": context_json if isinstance(context_json, dict) else {},
                }
            )
        return history


def _load_institutional_timeline(limit: int = 30) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for entry in _load_generation_history(limit=limit):
        items.append(
            {
                "kind": "generation",
                "created_at": entry["created_at"],
                "title": f"Geração #{entry['generation_event_id']}",
                "details": (
                    f"concurso={entry.get('target_contest', '-') or '-'} | jogos={entry['total_games']} | "
                    f"seed={entry['seed']} | status=persistido"
                ),
            }
        )
    for entry in _load_reconciliation_history(limit=limit):
        items.append(
            {
                "kind": "reconciliation",
                "created_at": entry["created_at"],
                "title": f"Conferência #{entry['id']}",
                "details": (
                    f"concurso={entry['contest_id']} | jogos_conferidos={entry['games_count']} | "
                    f"status={entry['status']} | generation_event_id={entry['generation_event_id']}"
                ),
            }
        )
    sync_summary = _load_official_sync_diagnostics()
    if sync_summary:
        items.append(
            {
                "kind": "sync",
                "created_at": str(sync_summary.get("sync_timestamp", "") or ""),
                "title": "Sync Caixa",
                "details": (
                    f"concurso={sync_summary.get('imported_contest', '-')} | status={sync_summary.get('sync_status', '-')} | "
                    f"http={sync_summary.get('http_status', '-')} | persisted={len(sync_summary.get('imported_numbers', []) or [])} | "
                    f"dezenas={' '.join(f'{int(number):02d}' for number in sync_summary.get('imported_numbers', []) or []) or '-'}"
                ),
            }
        )
    items.append(
        {
            "kind": "audit",
            "created_at": "",
            "title": "Auditoria Runtime",
            "details": "PostgreSQL Institucional validado como fonte oficial",
        }
    )
    items.append(
        {
            "kind": "governance",
            "created_at": "",
            "title": "Lei Nº 001",
            "details": "PostgreSQL Institucional como Fonte Única da Verdade",
        }
    )
    hb_state = _hb_geometry_state()
    progress = hb_state.get("progress") or {}
    if progress:
        items.append(
            {
                "kind": "hb_geometry",
                "created_at": str(progress.get("created_at", "") or ""),
                "title": "HB Geometry",
                "details": f"batch={progress.get('current_batch', '-')} | contests={progress.get('contests_processed', '-')} | completed={'sim' if progress.get('completed') else 'não'}",
            }
        )
    items.append(
        {
            "kind": "whatsapp",
            "created_at": "",
            "title": "WhatsApp",
            "details": "Futura integração operacional da plataforma",
        }
    )
    for entry in _load_operational_logs_history(limit=limit):
        items.append(
            {
                "kind": "log",
                "created_at": entry["created_at"],
                "title": f"Log operacional #{entry['id']}",
                "details": f"evento={entry['event_type']} | status={entry['status']} | duration_ms={entry['duration_ms']:.1f}",
            }
        )
    return sorted(
        items,
        key=lambda item: item.get("created_at", ""),
        reverse=True,
    )[:limit]


def _load_analytical_timeline(limit: int = 30) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for entry in _load_generation_history(limit=limit):
        top_game = (entry.get("top_games") or [{}])[0] if entry.get("top_games") else {}
        top_numbers = " ".join(f"{number:02d}" for number in top_game.get("numbers", [])[:15]) if top_game else "-"
        items.append(
            {
                "kind": "generation",
                "created_at": entry.get("created_at", ""),
                "title": f"Geração #{entry['generation_event_id']} | concurso={entry.get('target_contest', '-') or '-'}",
                "details": (
                    f"jogos={entry['total_games']} | seed={entry['seed']} | perfil_medio={entry.get('avg_score', 0.0):.4f} | "
                    f"entropy={entry.get('avg_entropy', 0.0):.4f} | coverage={entry.get('avg_coverage', 0.0):.4f} | "
                    f"overlap={entry.get('average_overlap', 0.0):.4f} | top_jogo={top_numbers}"
                ),
            }
        )
        for game in (entry.get("games") or []):
            items.append(
                {
                    "kind": "game",
                    "created_at": entry.get("created_at", ""),
                    "title": f"Jogo {game.get('game_index', '-')}",
                    "details": (
                        f"dezenas={' '.join(f'{number:02d}' for number in game.get('numbers', []))} | "
                        f"perfil={game.get('profile_type', '-')} | score={float(game.get('score', 0.0) or 0.0):.4f} | "
                        f"pares={game.get('even', 0)} | impares={game.get('odd', 0)} | "
                        f"cobertura={float(game.get('coverage', 0.0) or 0.0):.4f} | entropia={float(game.get('entropy', 0.0) or 0.0):.4f}"
                    ),
                }
            )
    for entry in _load_reconciliation_history(limit=limit):
        items.append(
            {
                "kind": "reconciliation",
                "created_at": entry.get("created_at", ""),
                "title": f"Conferência #{entry['id']} | concurso={entry.get('contest_id', '-')}",
                "details": (
                    f"jogos_conferidos={entry.get('games_count', 0)} | melhor_acerto={entry.get('best_hits', 0)} | "
                    f"premios={entry.get('prize_count', 0)} | total_hits={entry.get('total_hits', 0)} | "
                    f"matched_numbers={' '.join(f'{number:02d}' for number in entry.get('matched_numbers', [])) or '-'}"
                ),
            }
        )
    return sorted(items, key=lambda item: item.get("created_at", ""), reverse=True)[:limit]


def _load_accumulated_analytical_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for generation in _load_generation_history(limit=None):
        generation_label = f"Geração {generation.get('generation_event_id', '-')}"
        created_at = str(generation.get("created_at", "") or "")
        strategy = str(generation.get("strategy", "") or "")
        for game in generation.get("games", []) or []:
            hits_value = game.get("hits")
            rows.append(
                {
                    "geração": generation_label,
                    "generation_event_id": int(generation.get("generation_event_id", 0) or 0),
                    "data/hora": created_at,
                    "jogo n°": int(game.get("game_index", 0) or 0),
                    "dezenas": " ".join(f"{number:02d}" for number in game.get("numbers", [])),
                    "estratégia": strategy or "-",
                    "score": round(float(game.get("score", 0.0) or 0.0), 4),
                    "origem/modelo": str(game.get("origin", "") or "institutional"),
                    "status de conferência": str(game.get("conference_status", "Nao conferido") or "Nao conferido"),
                    "concurso conferido": int(game.get("contest_id", 0) or 0) if game.get("contest_id") else None,
                    "acertos": int(hits_value) if hits_value is not None else None,
                    "premiação": str(game.get("prize_status", "") or "") or "—",
                    "observações": str(game.get("prize_tier", "") or "") or "-",
                    "generation_mode": str(game.get("generation_mode", "") or ""),
                    "reconciliation_id": int(game.get("reconciliation_id", 0) or 0) if game.get("reconciliation_id") else None,
                    "reconciled_at": str(game.get("reconciled_at", "") or ""),
                }
            )
    return rows


def _load_accumulated_institutional_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for generation in _load_generation_history(limit=None):
        games = list(generation.get("games", []) or [])
        reconciliation = dict(generation.get("reconciliation") or {})
        generated_count = int(generation.get("total_games", 0) or 0)
        persisted_count = _count_generated_games_for_event(int(generation.get("generation_event_id", 0) or 0))
        recovered_count = len(games)
        first_context = dict((games[0] or {}).get("generation_context") or {}) if games and isinstance(games[0], dict) else {}
        requested_count = int(first_context.get("total_games", generated_count) or generated_count)
        generated_requested = generated_count
        strategy = str(generation.get("strategy", "") or "")
        latest_game = max(games, key=lambda item: float(item.get("score", 0.0) or 0.0), default={})
        top_score = float(latest_game.get("score", 0.0) or 0.0) if latest_game else 0.0
        highest_hits = max((int(game.get("hits", 0) or 0) for game in games), default=0)
        average_hits = round(sum(int(game.get("hits", 0) or 0) for game in games) / len(games), 4) if games and any(game.get("hits") is not None for game in games) else 0.0
        conference_status = "Conferido" if reconciliation.get("id") else "Nao conferido"
        persistence_status = "OK" if persisted_count >= recovered_count and recovered_count >= generated_count else "ALERTA"
        generation_status = "OK" if requested_count == generated_count else "ALERTA"
        integrity_alerts: list[str] = []
        if requested_count != generated_count:
            integrity_alerts.append("solicitado_!=_gerado")
        if generated_count != persisted_count:
            integrity_alerts.append("gerado_!=_persistido")
        if persisted_count != recovered_count:
            integrity_alerts.append("persistido_!=_recuperado")
        if not games:
            integrity_alerts.append("sem_jogos_associados")
        if not reconciliation.get("contest_id"):
            integrity_alerts.append("sem_conferencia")
        commander_status = str(first_context.get("status_comandante_saida", "APROVADO") or "APROVADO")
        total_unique = int(first_context.get("total_jogos_unicos", recovered_count) or recovered_count)
        total_duplicates = int(first_context.get("total_jogos_duplicados", 0) or 0)
        rows.append(
            {
                "geração": f"Geração {generation.get('generation_event_id', '-')}",
                "generation_event_id": int(generation.get("generation_event_id", 0) or 0),
                "data/hora": str(generation.get("created_at", "") or ""),
                "usuário/session_id": str(generation.get("first_name", "") or "-"),
                "estratégia/modelo": strategy or "-",
                "quantidade solicitada": requested_count,
                "quantidade real gerada": generated_requested,
                "quantidade persistida": persisted_count,
                "total de jogos recuperados": recovered_count,
                "status da geração": generation_status,
                "status de persistência": persistence_status,
                "status de conferência": conference_status,
                "status comandante saída": commander_status,
                "concurso conferido": int(reconciliation.get("contest_id", 0) or 0) if reconciliation.get("contest_id") else None,
                "maior acerto": highest_hits,
                "média de acertos": average_hits,
                "melhor score": round(top_score, 4),
                "score médio": round(float(generation.get("avg_score", 0.0) or 0.0), 4),
                "origem da geração": str(generation.get("strategy", "") or "institutional"),
                "observações/alertas": ", ".join(integrity_alerts) if integrity_alerts else "OK",
                "total_games": generated_count,
                "batch_id": str(first_context.get("batch_id", "") or ""),
                "total jogos únicos": total_unique,
                "total jogos duplicados": total_duplicates,
                "taxa duplicidade": float(first_context.get("taxa_duplicidade", 0.0) or 0.0),
                "reconciliation_id": reconciliation.get("id"),
                "reconciliation_best_hits": reconciliation.get("best_hits"),
                "reconciliation_prize_count": reconciliation.get("prize_count"),
                "reconciliation_total_hits": reconciliation.get("total_hits"),
                "generated_games": games,
            }
        )
    return rows

def _clear_institutional_history_state() -> None:
    for key in (
        "institutional_generation",
        "institutional_generation_result",
        "institutional_generation_batch_result",
        "institutional_check",
        "institutional_check_result",
        "institutional_simulation",
        "institutional_simulation_result",
        "institutional_last_official_sync_summary",
        "institutional_output_batch_id",
    ):
        st.session_state.pop(key, None)


def _align_institutional_runtime_with_database(snapshot: dict[str, Any]) -> None:
    history_counts = (
        int(snapshot["counts"].get("generation_events", 0) or 0),
        int(snapshot["counts"].get("generated_games", 0) or 0),
        int(snapshot["counts"].get("reconciliation_runs", 0) or 0),
        int(snapshot["counts"].get("reconciliation_games", 0) or 0),
        int(snapshot["counts"].get("reconciliation_events", 0) or 0),
    )
    if any(history_counts):
        return
    _clear_institutional_history_state()
    for key in (
        "institutional_contest_nav",
        "institutional_draw_input",
        "institutional_sync_last_payload",
        "institutional_sync_status",
        "institutional_sync_error",
        "institutional_sync_timestamp",
        "institutional_sync_http_status",
        "institutional_sync_request_url",
        "institutional_imported_contest",
        "institutional_imported_numbers",
        "institutional_generation_batch_result",
        "institutional_simulation",
        "institutional_simulation_result",
        "institutional_simulation_error",
        "institutional_check_result",
        "institutional_check",
        "institutional_output_batch_id",
    ):
        st.session_state.pop(key, None)


def _purge_institutional_history_tables() -> dict[str, Any]:
    before_snapshot = _database_snapshot()
    deleted: dict[str, int] = {}
    errors: dict[str, str] = {}
    engine = get_engine(DB_PATH)
    tables_to_purge = list(HISTORICAL_TEST_TABLES) + list(PURGE_ONLY_TABLES)
    for table in tables_to_purge:
        try:
            with engine.begin() as connection:
                result = connection.execute(text(f'DELETE FROM "{table}"'))
            deleted[table] = int(result.rowcount or 0)
        except Exception as exc:
            deleted[table] = 0
            errors[table] = str(exc)
    try:
        st.cache_data.clear()
    except Exception:
        pass
    _clear_institutional_history_state()
    after_snapshot = _database_snapshot()
    return {
        "status": "partial" if errors else "ok",
        "deleted": deleted,
        "errors": errors,
        "before": {
            "counts": {table: int(before_snapshot["counts"].get(table, 0) or 0) for table in HISTORICAL_TEST_TABLES},
            "latest": {table: before_snapshot["latest"].get(table, "-") for table in HISTORICAL_TEST_TABLES},
        },
        "after": {
            "counts": {table: int(after_snapshot["counts"].get(table, 0) or 0) for table in HISTORICAL_TEST_TABLES},
            "latest": {table: after_snapshot["latest"].get(table, "-") for table in HISTORICAL_TEST_TABLES},
        },
        "preserved": {
            "imported_contests": int(after_snapshot["counts"].get("imported_contests", 0) or 0),
            "latest_imported_contest": after_snapshot["latest"].get("imported_contests", "-"),
        },
    }


def _render_history_institutional_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    live_counts = _database_snapshot()["counts"]
    st.subheader("Hist?rico Institucional")
    st.write("Visão macro acumulativa de gerações, conferências e integridade operacional.")

    source_map = _institutional_source_map(snapshot)
    latest_sync = st.session_state.get("institutional_last_official_sync_summary", {})
    latest_contest = _load_latest_contest_summary() or {}
    latest_reconciliation = _load_latest_reconciliation_summary() or {}
    generation_rows = _load_accumulated_institutional_rows()
    generation_df = pd.DataFrame(generation_rows)
    source_cols = st.columns(8)
    source_cols[0].metric("backend", snapshot["backend"])
    source_cols[1].metric("database_source", snapshot["database_source"])
    source_cols[2].metric("schema", "public" if str(snapshot.get("backend", "")).lower() == "postgresql" else "main")
    source_cols[3].metric("operational_logs", int(live_counts.get("operational_logs", 0)))
    source_cols[4].metric("institutional_output_signatures", int(live_counts.get("institutional_output_signatures", 0)))
    source_cols[5].metric("scientific_calibration_decisions", int(live_counts.get("scientific_calibration_decisions", 0)))
    source_cols[6].metric("lotofacil_official_history", int(live_counts.get("lotofacil_official_history", 0)))
    source_cols[7].metric("scientific_institutional_memory", int(live_counts.get("scientific_institutional_memory", 0)))
    st.caption(
        " | ".join(
            [
                f"build={BUILD_MARKER}",
                f"commit={_resolve_active_commit()}",
                f"last_imported_contest={latest_contest.get('contest_number', '-')}",
                f"last_sync={latest_sync.get('sync_timestamp', '-')}",
            ]
        )
    )
    st.markdown("##### Resumo institucional")
    summary_cols = st.columns(10)
    total_generation_events = len(generation_df)
    total_requested = int(generation_df["quantidade solicitada"].fillna(0).astype(int).sum()) if not generation_df.empty else 0
    total_generated = int(generation_df["quantidade real gerada"].fillna(0).astype(int).sum()) if not generation_df.empty else 0
    total_persisted = int(generation_df["quantidade persistida"].fillna(0).astype(int).sum()) if not generation_df.empty else 0
    total_recovered = int(generation_df["total de jogos recuperados"].fillna(0).astype(int).sum()) if not generation_df.empty else 0
    total_contests_reconciled = int(generation_df["concurso conferido"].fillna(0).astype(int).ne(0).sum()) if not generation_df.empty else 0
    highest_hits = int(generation_df["maior acerto"].fillna(0).astype(int).max()) if not generation_df.empty else 0
    best_score = float(generation_df["melhor score"].fillna(0.0).astype(float).max()) if not generation_df.empty else 0.0
    latest_generation_label = generation_df.iloc[0]["geração"] if not generation_df.empty else "-"
    first_generation_label = generation_df.iloc[-1]["geração"] if not generation_df.empty else "-"
    summary_cols[0].metric("total gerações", total_generation_events)
    summary_cols[1].metric("jogos solicitados", total_requested)
    summary_cols[2].metric("jogos gerados", total_generated)
    summary_cols[3].metric("jogos persistidos", total_persisted)
    summary_cols[4].metric("jogos recuperados", total_recovered)
    summary_cols[5].metric("concursos conferidos", total_contests_reconciled)
    summary_cols[6].metric("maior acerto", highest_hits)
    summary_cols[7].metric("melhor score", f"{best_score:.4f}")
    summary_cols[8].metric("última geração", latest_generation_label)
    summary_cols[9].metric("primeira geração", first_generation_label)
    _render_scientific_memory_block()

    if not generation_df.empty:
        latest_commander = generation_df.iloc[0]
        st.markdown("##### Comandante de Saída")
        commander_cols = st.columns(6)
        commander_cols[0].metric("total_jogos_solicitados", int(latest_commander.get("quantidade solicitada", 0) or 0))
        commander_cols[1].metric("total_jogos_gerados", int(latest_commander.get("quantidade real gerada", 0) or 0))
        commander_cols[2].metric("total_jogos_unicos", int(latest_commander.get("total jogos únicos", 0) or 0))
        commander_cols[3].metric("total_jogos_duplicados", int(latest_commander.get("total jogos duplicados", 0) or 0))
        commander_cols[4].metric("taxa_duplicidade", f"{float(latest_commander.get('taxa duplicidade', 0.0) or 0.0):.4f}")
        commander_cols[5].metric("status_comandante_saida", str(latest_commander.get("status comandante saída", "APROVADO") or "APROVADO"))
        st.caption(
            f"institutional_output_signatures={int(live_counts.get('institutional_output_signatures', 0))} | "
            f"generation_event_id={int(latest_commander.get('generation_event_id', 0) or 0)}"
        )

        scientific_batch_id = str(latest_commander.get("batch_id", "") or "").strip()
        scientific_batch = _scientific_batch_diagnostics(batch_id=scientific_batch_id, games=[], game_size=0) if scientific_batch_id else {}
        if scientific_batch:
            st.markdown("##### Núcleo Científico Lotofácil")
            sci_cols = st.columns(6)
            sci_cols[0].metric("status_cientifico", scientific_batch.get("status_comandante_cientifico", "-"))
            sci_cols[1].metric("classificacao_cientifica", scientific_batch.get("classificacao_cientifica", "-"))
            sci_cols[2].metric("maior_acerto", int(scientific_batch.get("best_hits", 0) or 0))
            sci_cols[3].metric("11+", int(scientific_batch.get("count_11_plus", 0) or 0))
            sci_cols[4].metric("12+", int(scientific_batch.get("count_12_plus", 0) or 0))
            sci_cols[5].metric("13+", int(scientific_batch.get("count_13_plus", 0) or 0))
            sci_cols_2 = st.columns(4)
            sci_cols_2[0].metric("media_best_hits", f"{float(scientific_batch.get('average_best_hits', 0.0) or 0.0):.4f}")
            sci_cols_2[1].metric("media_hits", f"{float(scientific_batch.get('average_hits', 0.0) or 0.0):.4f}")
            sci_cols_2[2].metric("freq_max", f"{float(scientific_batch.get('frequency_maxima_dezena_percentual', 0.0) or 0.0):.2f}%")
            sci_cols_2[3].metric("freq_min_nucleo", f"{float(scientific_batch.get('frequency_minima_dezena_candidata_percentual', 0.0) or 0.0):.2f}%")
            st.caption(
                " | ".join(
                    [
                        f"status_estrutural={latest_commander.get('status comandante saída', 'APROVADO')}",
                        f"status_cientifico={scientific_batch.get('status_comandante_cientifico', '-')}",
                        f"classificacao_cientifica={scientific_batch.get('classificacao_cientifica', '-')}",
                        f"reference_window={scientific_batch.get('reference_window', [])}",
                        f"repeticao_media={scientific_batch.get('average_repetition', '-')}",
                        f"sequencia_media={scientific_batch.get('average_sequence_max', '-')}",
                    ]
                )
            )
            if scientific_batch.get("motivo_cientifico"):
                if scientific_batch.get("status_comandante_cientifico") == "APROVADO":
                    st.success(
                        f"Núcleo Científico Lotofácil aprovou a bateria. motivo={scientific_batch.get('motivo_cientifico', '-')}"
                    )
                else:
                    st.warning(
                        f"Núcleo Científico Lotofácil reprovou a bateria. motivo={scientific_batch.get('motivo_cientifico', '-')}"
                    )
            with st.expander("Diagnóstico científico completo", expanded=False):
                st.json(scientific_batch)
            latest_scientific_decisions = _load_latest_scientific_calibration_decision(limit=5)
            if latest_scientific_decisions:
                st.markdown("##### Memória científica de calibração")
                st.dataframe(pd.DataFrame(latest_scientific_decisions), hide_index=True, use_container_width=True)


    if not generation_df.empty:
        filter_row_1 = st.columns([1, 1, 1, 1, 1])
        generation_options = sorted(int(value) for value in generation_df["generation_event_id"].dropna().astype(int).unique().tolist())
        strategy_options = sorted(str(value) for value in generation_df["estratégia/modelo"].dropna().astype(str).unique().tolist())
        status_generation_options = sorted(str(value) for value in generation_df["status da geração"].dropna().astype(str).unique().tolist())
        status_persistence_options = sorted(str(value) for value in generation_df["status de persistência"].dropna().astype(str).unique().tolist())
        status_conference_options = sorted(str(value) for value in generation_df["status de conferência"].dropna().astype(str).unique().tolist())
        selected_generations = filter_row_1[0].multiselect("geração", generation_options, default=generation_options)
        selected_strategies = filter_row_1[1].multiselect("estratégia/modelo", strategy_options, default=strategy_options)
        selected_generation_status = filter_row_1[2].multiselect("status da geração", status_generation_options, default=status_generation_options)
        selected_persistence_status = filter_row_1[3].multiselect("status de persistência", status_persistence_options, default=status_persistence_options)
        selected_conference_status = filter_row_1[4].multiselect("status de conferência", status_conference_options, default=status_conference_options)

        filter_row_2 = st.columns([1, 1, 1, 1, 1])
        contest_options = sorted(int(value) for value in generation_df["concurso conferido"].dropna().astype(int).unique().tolist() if int(value) > 0)
        alert_only = filter_row_2[0].checkbox("somente gerações com alerta", value=False)
        conference_only = filter_row_2[1].checkbox("somente gerações conferidas", value=False)
        not_conference_only = filter_row_2[2].checkbox("somente gerações não conferidas", value=False)
        min_score = filter_row_2[3].number_input("score mínimo", min_value=0.0, value=0.0, step=0.1)
        min_hits = filter_row_2[4].number_input("maior acerto mínimo", min_value=0, value=0, step=1)

        date_values = pd.to_datetime(generation_df["data/hora"], errors="coerce").dropna()
        if not date_values.empty:
            start_date = date_values.min().date()
            end_date = date_values.max().date()
            date_range = st.date_input("data inicial/final", value=(start_date, end_date))
        else:
            date_range = ()

        filtered_df = generation_df.copy()
        filtered_df["data/hora_dt"] = pd.to_datetime(filtered_df["data/hora"], errors="coerce")
        filtered_df["score_medio_num"] = pd.to_numeric(filtered_df["score médio"], errors="coerce").fillna(0.0)
        if selected_generations:
            filtered_df = filtered_df[filtered_df["generation_event_id"].isin(selected_generations)]
        if selected_strategies:
            filtered_df = filtered_df[filtered_df["estratégia/modelo"].isin(selected_strategies)]
        if selected_generation_status:
            filtered_df = filtered_df[filtered_df["status da geração"].isin(selected_generation_status)]
        if selected_persistence_status:
            filtered_df = filtered_df[filtered_df["status de persistência"].isin(selected_persistence_status)]
        if selected_conference_status:
            filtered_df = filtered_df[filtered_df["status de conferência"].isin(selected_conference_status)]
        if contest_options:
            filtered_df = filtered_df[filtered_df["concurso conferido"].fillna(0).astype(int).isin(contest_options)]
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            filtered_df = filtered_df[filtered_df["data/hora_dt"].dt.date.between(start_date, end_date)]
        if alert_only:
            filtered_df = filtered_df[filtered_df["observações/alertas"].astype(str) != "OK"]
        if conference_only:
            filtered_df = filtered_df[filtered_df["status de conferência"].astype(str) == "Conferido"]
        if not_conference_only:
            filtered_df = filtered_df[filtered_df["status de conferência"].astype(str) != "Conferido"]
        filtered_df = filtered_df[filtered_df["score médio"].astype(float) >= float(min_score)]
        filtered_df = filtered_df[filtered_df["maior acerto"].astype(int) >= int(min_hits)]

        order_by = st.selectbox("ordenar por", ["data", "maior acerto", "score"], index=0)
        if order_by == "maior acerto":
            filtered_df = filtered_df.sort_values(
                by=["maior acerto", "melhor score", "data/hora_dt", "generation_event_id"],
                ascending=[False, False, False, False],
            )
        elif order_by == "score":
            filtered_df = filtered_df.sort_values(
                by=["score médio", "melhor score", "data/hora_dt", "generation_event_id"],
                ascending=[False, False, False, False],
            )
        else:
            filtered_df = filtered_df.sort_values(
                by=["data/hora_dt", "generation_event_id"],
                ascending=[False, False],
            )

        display_df = filtered_df.copy()
        display_df["concurso conferido"] = display_df["concurso conferido"].apply(lambda value: f"{int(value)}" if pd.notna(value) and int(value) > 0 else "—")
        display_df["quantidade solicitada"] = display_df["quantidade solicitada"].fillna(0).astype(int)
        display_df["quantidade real gerada"] = display_df["quantidade real gerada"].fillna(0).astype(int)
        display_df["quantidade persistida"] = display_df["quantidade persistida"].fillna(0).astype(int)
        display_df["total de jogos recuperados"] = display_df["total de jogos recuperados"].fillna(0).astype(int)
        display_df["maior acerto"] = display_df["maior acerto"].fillna(0).astype(int)
        display_df["média de acertos"] = display_df["média de acertos"].fillna(0.0).astype(float).map(lambda value: f"{value:.4f}")
        display_df["melhor score"] = display_df["melhor score"].fillna(0.0).astype(float).map(lambda value: f"{value:.4f}")
        display_df["score médio"] = display_df["score médio"].fillna(0.0).astype(float).map(lambda value: f"{value:.4f}")
        display_df["observações/alertas"] = display_df["observações/alertas"].astype(str)
        display_df["data/hora"] = display_df["data/hora"].fillna("—")
        for column, default in (
            ("status comandante saída", "APROVADO"),
            ("batch_id", "-"),
            ("total jogos únicos", 0),
            ("total jogos duplicados", 0),
            ("taxa duplicidade", 0.0),
        ):
            if column not in display_df.columns:
                display_df[column] = default
        display_df["status comandante saída"] = display_df["status comandante saída"].astype(str)
        display_df["batch_id"] = display_df["batch_id"].astype(str)
        display_df["total jogos únicos"] = display_df["total jogos únicos"].fillna(0).astype(int)
        display_df["total jogos duplicados"] = display_df["total jogos duplicados"].fillna(0).astype(int)
        display_df["taxa duplicidade"] = display_df["taxa duplicidade"].fillna(0.0).astype(float).map(lambda value: f"{value:.4f}")
        display_df = display_df[
            [
                "geração",
                "generation_event_id",
                "data/hora",
                "usuário/session_id",
                "estratégia/modelo",
                "quantidade solicitada",
                "quantidade real gerada",
                "quantidade persistida",
                "total de jogos recuperados",
                "status da geração",
                "status de persistência",
                "status de conferência",
                "status comandante saída",
                "concurso conferido",
                "maior acerto",
                "média de acertos",
                "melhor score",
                "score médio",
                "origem da geração",
                "batch_id",
                "total jogos únicos",
                "total jogos duplicados",
                "taxa duplicidade",
                "observações/alertas",
            ]
        ]
        st.markdown("##### Gerações institucionais")
        st.dataframe(display_df, hide_index=True, use_container_width=True, height=540)

        if filtered_df.empty:
            st.info("Nenhuma geração encontrada com os filtros atuais.")
        else:
            selected_generation_label = st.selectbox(
                "Detalhe da geração selecionada",
                list(display_df["generation_event_id"].astype(int).tolist()),
                index=0,
            )
            selected_generation_id = int(selected_generation_label)
            selected_generation = next((item for item in generation_rows if int(item.get("generation_event_id", 0) or 0) == selected_generation_id), {})
            detail_cols = st.columns(6)
            detail_cols[0].metric("generation_event_id", selected_generation.get("generation_event_id", "-"))
            detail_cols[1].metric("data/hora", selected_generation.get("data/hora", "-"))
            detail_cols[2].metric("solicitados", selected_generation.get("quantidade solicitada", 0))
            detail_cols[3].metric("gerados", selected_generation.get("quantidade real gerada", 0))
            detail_cols[4].metric("persistidos", selected_generation.get("quantidade persistida", 0))
            detail_cols[5].metric("recuperados", selected_generation.get("total de jogos recuperados", 0))
            st.caption(
                " | ".join(
                    [
                        f"estratégia/modelo={selected_generation.get('estratégia/modelo', '-')}",
                        f"status_conferência={selected_generation.get('status de conferência', '-')}",
                        f"concurso={selected_generation.get('concurso conferido', '-') or '-'}",
                        f"maior_acerto={selected_generation.get('maior acerto', '-')}",
                        f"melhor_score={selected_generation.get('melhor score', '-')}",
                    ]
                )
            )
            if selected_generation.get("observações/alertas") and selected_generation.get("observações/alertas") != "OK":
                st.warning(f"Alerta: {selected_generation.get('observações/alertas')}")
            selected_history = next((item for item in _load_generation_history(limit=None) if int(item.get("generation_event_id", 0) or 0) == selected_generation_id), {})
            if selected_history:
                st.markdown("###### Top jogos da geração selecionada")
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "jogo": game.get("game_index", "-"),
                                "dezenas": " ".join(f"{number:02d}" for number in game.get("numbers", [])),
                                "perfil": game.get("profile_type", "-"),
                                "score": round(float(game.get("score", 0.0) or 0.0), 4),
                                "pares": int(game.get("even", 0) or 0),
                                "?mpares": int(game.get("odd", 0) or 0),
                                "cobertura": round(float(game.get("coverage", 0.0) or 0.0), 4),
                                "entropia": round(float(game.get("entropy", 0.0) or 0.0), 4),
                                "concurso conferido": game.get("contest_id", "-") or "-",
                                "acertos": game.get("hits", "-") if game.get("hits") is not None else "-",
                                "status": game.get("prize_status", "nao_premiado") or "nao_premiado",
                            }
                            for game in (selected_history.get("top_games") or [])
                        ]
                    ),
                    hide_index=True,
                    use_container_width=True,
                )

        st.markdown("##### Auditoria de integridade")
        issues = display_df[display_df["observações/alertas"].astype(str) != "OK"]
        if issues.empty:
            st.success("Nenhuma inconsistência detectada na visão institucional atual.")
        else:
            st.dataframe(
                issues[
                    [
                        "geração",
                        "generation_event_id",
                        "quantidade solicitada",
                        "quantidade real gerada",
                        "quantidade persistida",
                        "total de jogos recuperados",
                        "status da geração",
                        "status de persistência",
                        "status de conferência",
                        "observações/alertas",
                    ]
                ],
                hide_index=True,
                use_container_width=True,
            )
        diag_cols = st.columns(10)
        diag_cols[0].metric("total_generation_events_carregados", len(generation_rows))
        diag_cols[1].metric("total_generation_events_exibidos", len(display_df))
        diag_cols[2].metric("total_jogos_solicitados", total_requested)
        diag_cols[3].metric("total_jogos_gerados", total_generated)
        diag_cols[4].metric("total_jogos_persistidos", total_persisted)
        diag_cols[5].metric("total_jogos_recuperados", total_recovered)
        diag_cols[6].metric("generation_event_id_mais_antigo", int(generation_df["generation_event_id"].min()) if not generation_df.empty else "-")
        diag_cols[7].metric("generation_event_id_mais_recente", int(generation_df["generation_event_id"].max()) if not generation_df.empty else "-")
        diag_cols[8].metric("total_eventos_com_alerta", int((generation_df["observações/alertas"].astype(str) != "OK").sum()) if not generation_df.empty else 0)
        diag_cols[9].metric("total_eventos_ok", int((generation_df["observações/alertas"].astype(str) == "OK").sum()) if not generation_df.empty else 0)
        st.caption(f"institutional_output_signatures={int(live_counts.get('institutional_output_signatures', 0))}")
    else:
        st.info("Ainda não há gerações persistidas para reconstrução institucional.")

    st.divider()
    st.markdown("##### Tabelas Institucionais")
    table_rows = []
    for table, count in live_counts.items():
        table_rows.append(
            {
                "tabela": table,
                "contagem": int(count),
                "ultima_persistencia": snapshot["latest"].get(table, "-"),
            }
        )
    st.dataframe(pd.DataFrame(table_rows), hide_index=True, use_container_width=True)

    with st.expander("Timeline secundária", expanded=False):
        timeline = _load_institutional_timeline(limit=30)
        if timeline:
            st.dataframe(pd.DataFrame(timeline), hide_index=True, use_container_width=True)
        else:
            st.info("Ainda não há eventos suficientes para montar a timeline institucional.")

def _render_clear_histories_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    st.subheader("Limpar Histories")
    st.write("Limpa apenas os estados visuais e operacionais desta sessao. Nao apaga o banco.")
    state_keys = sorted([key for key in st.session_state.keys() if str(key).startswith("institutional_")])
    st.caption(f"Chaves institucionais ativas: {len(state_keys)}")
    st.code("\n".join(state_keys) if state_keys else "-", language="text")
    if st.button("Limpar historicos desta sessao", type="primary"):
        _clear_institutional_history_state()
        st.success("Historicos visuais limpos desta sessao.")
        st.rerun()



def _render_delete_history_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    st.subheader("Apagar Historico")
    st.write("Remove os registros operacionais institucionais persistidos no banco atual.")
    st.warning(
        "Esta acao remove geracoes, reconciliacoes, logs e eventos de reset do runtime. "
        "Nao afeta imported_contests."
    )
    st.caption("Acao irreversivel no runtime atual. Preserva imported_contests.")
    before_rows = [
        {
            "tabela": table,
            "contagem": int(snapshot["counts"].get(table, 0) or 0),
            "ultima_persistencia": snapshot["latest"].get(table, "-"),
        }
        for table in HISTORICAL_TEST_TABLES
    ]
    st.markdown("##### Diagnostico antes da limpeza")
    st.dataframe(pd.DataFrame(before_rows), hide_index=True, use_container_width=True)
    if st.button("Apagar historico persistido", type="primary"):
        result = _purge_institutional_history_tables()
        refreshed_snapshot = _database_snapshot()
        after_rows = [
            {
                "tabela": table,
                "contagem": int(refreshed_snapshot["counts"].get(table, 0) or 0),
                "ultima_persistencia": refreshed_snapshot["latest"].get(table, "-"),
            }
            for table in HISTORICAL_TEST_TABLES
        ]
        preserved_row = {
            "tabela": "imported_contests",
            "contagem": int(refreshed_snapshot["counts"].get("imported_contests", 0) or 0),
            "ultima_persistencia": refreshed_snapshot["latest"].get("imported_contests", "-"),
        }
        st.success("Historico institucional apagado.")
        st.markdown("##### Resultado da limpeza")
        st.json(result)
        st.markdown("##### Diagnostico depois da limpeza")
        st.dataframe(pd.DataFrame(after_rows + [preserved_row]), hide_index=True, use_container_width=True)



def _render_comparative_history_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    st.subheader("Comparativos histórico")
    st.write("Comparação resumida entre geração, reconciliação e base oficial.")
    latest_generation = _load_latest_generated_games() or {}
    latest_contest = _load_imported_contest()
    structural_stats = _summarize_games_structurally(list(latest_generation.get("games") or []))
    cols = st.columns(4)
    cols[0].metric("generated_games", int(snapshot["counts"].get("generated_games", 0)))
    cols[1].metric("reconciliation_runs", int(snapshot["counts"].get("reconciliation_runs", 0)))
    cols[2].metric("imported_contests", int(snapshot["counts"].get("imported_contests", 0)))
    cols[3].metric("average_overlap", f"{structural_stats.get('average_overlap', 0.0):.4f}")
    comp_cols = st.columns([1, 1])
    with comp_cols[0]:
        st.markdown("##### Geração atual")
        if latest_generation.get("games"):
            st.json(
                {
                    "generation_event_id": latest_generation.get("generation_event_id", "-"),
                    "seed": latest_generation.get("seed", "-"),
                    "total_games": latest_generation.get("total_games", 0),
                    "target_contest": latest_generation.get("target_contest", "-"),
                }
            )
        else:
            st.info("Nenhuma geração persistida encontrada.")
    with comp_cols[1]:
        st.markdown("##### Concurso oficial")
        if latest_contest:
            st.json(
                {
                    "contest_number": latest_contest.get("contest_number", "-"),
                    "data": latest_contest.get("data", "-"),
                    "dezenas": latest_contest.get("dezenas", []),
                }
            )
        else:
            st.info("Nenhum concurso oficial importado ainda.")
    if structural_stats.get("dominant_numbers"):
        st.markdown("##### Números dominantes")
        st.dataframe(pd.DataFrame(structural_stats.get("dominant_numbers") or []), hide_index=True, use_container_width=True)


def _render_strategies_page(page_title: str, snapshot: dict[str, Any]) -> None:
    st.subheader(page_title)
    st.write("Ações analíticas desacopladas do fluxo operacional principal.")
    latest_generation = _load_latest_generated_games() or {}
    games = list(latest_generation.get("games") or [])
    structural_stats = _summarize_games_structurally(games)
    action_cols = st.columns(3)
    if action_cols[0].button("Análises Estratégicas", type="primary"):
        st.session_state["institutional_strategy_action"] = "análises_estratégicas"
    if action_cols[1].button("Testar Estratégias", type="primary"):
        st.session_state["institutional_strategy_action"] = "testar_estratégias"
    if action_cols[2].button("Simular Estratégias", type="primary"):
        st.session_state["institutional_strategy_action"] = "simular_estratégias"
    st.caption(f"last_ui_event: {st.session_state.get('institutional_last_ui_event', '-')}")
    st.caption(f"strategy_action: {st.session_state.get('institutional_strategy_action', '-')}")
    stats_cols = st.columns(4)
    stats_cols[0].metric("games", structural_stats.get("games", 0))
    stats_cols[1].metric("average_overlap", f"{structural_stats.get('average_overlap', 0.0):.4f}")
    stats_cols[2].metric("average_unique_numbers", f"{structural_stats.get('average_unique_numbers', 0.0):.4f}")
    stats_cols[3].metric("dominant_numbers", len(structural_stats.get("dominant_numbers") or []))
    if structural_stats.get("dominant_numbers"):
        st.dataframe(pd.DataFrame(structural_stats["dominant_numbers"]), hide_index=True, use_container_width=True)
    latest_contest = _load_imported_contest()
    if latest_generation.get("games") and latest_contest:
        comparison = _compare_games_against_contest(
            generation_event_id=int(latest_generation.get("generation_event_id") or 0),
            games=list(latest_generation.get("games") or []),
            contest=latest_contest,
        )
        st.markdown("##### Replay institucional")
        st.caption(
            f"concurso={comparison['contest_number']} | best_hits={comparison['best_hits']} | "
            f"prizes={comparison['prize_count']} | total_hits={comparison['total_hits']}"
        )
        replay_df = pd.DataFrame(
            [
                {
                    "jogo": row["game_index"],
                    "hits": row["hits"],
                    "premiado": row["prize_status"],
                    "matched_numbers": " ".join(f"{number:02d}" for number in row["matched_numbers"]),
                }
                for row in comparison["results"]
            ]
        )
        st.dataframe(replay_df, hide_index=True, use_container_width=True)


def _render_metrics_hb_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    st.subheader("Métricas HB")
    st.write("Resumo HB do replay estrutural incremental.")
    state = _hb_geometry_state()
    summary = state["summary"] or {}
    baseline = summary.get("hb_baseline", {})
    cols = st.columns(4)
    cols[0].metric("avg_hits", round(float(baseline.get("average_hits", 0.0)), 4))
    cols[1].metric("11+", int(baseline.get("hits_11_plus", 0)))
    cols[2].metric("12+", int(baseline.get("hits_12_plus", 0)))
    cols[3].metric("entropy", round(float(baseline.get("entropy", 0.0)), 4))
    metrics_df = pd.DataFrame(
        [
            {"métrica": "average_overlap", "valor": round(float(baseline.get("average_overlap", 0.0)), 4)},
            {"métrica": "dominant_numbers", "valor": ", ".join(f"{item['number']}:{item['frequency']}" for item in baseline.get("dominant_numbers", [])[:5]) or "-"},
            {"métrica": "contests_analyzed", "valor": int(summary.get("contests_analyzed", 0) or 0)},
            {"métrica": "games_count", "valor": int(summary.get("games_count", 0) or 0)},
            {"métrica": "pool_size", "valor": int(summary.get("pool_size", 0) or 0)},
        ]
    )
    st.dataframe(metrics_df, hide_index=True, use_container_width=True)


def _render_cobertura_estrutural_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    st.subheader("Cobertura estrutural")
    st.write("Geometria e concentração do lote institucional persistido.")
    games = _institutional_generation_games()
    stats = _summarize_games_structurally(games)
    cols = st.columns(4)
    cols[0].metric("games", stats.get("games", 0))
    cols[1].metric("average_overlap", f"{stats.get('average_overlap', 0.0):.4f}")
    cols[2].metric("average_unique_numbers", f"{stats.get('average_unique_numbers', 0.0):.4f}")
    cols[3].metric("dominant_numbers", len(stats.get("dominant_numbers") or []))
    if stats.get("dominant_numbers"):
        st.dataframe(pd.DataFrame(stats["dominant_numbers"]), hide_index=True, use_container_width=True)


def _render_replay_institutional_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    st.subheader("Replay institucional")
    st.write("Reexecuta a leitura do último lote persistido contra o concurso oficial corrente.")
    latest_generation = _load_latest_generated_games() or {}
    latest_contest = _load_imported_contest()
    if st.button("Executar replay institucional", type="primary"):
        if latest_generation.get("games") and latest_contest:
            replay = _compare_games_against_contest(
                generation_event_id=int(latest_generation.get("generation_event_id") or 0),
                games=list(latest_generation.get("games") or []),
                contest=latest_contest,
            )
            st.session_state["institutional_replay"] = replay
            st.success("Replay institucional executado.")
            st.rerun()
        else:
            st.warning("É preciso ter geração persistida e concurso oficial importado.")
    replay = st.session_state.get("institutional_replay")
    if replay:
        st.caption(
            f"concurso={replay.get('contest_number', '-')}"
            f" | best_hits={replay.get('best_hits', '-')}"
            f" | prizes={replay.get('prize_count', '-')}"
        )
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "jogo": row["game_index"],
                        "hits": row["hits"],
                        "premiado": row["prize_status"],
                    }
                    for row in replay.get("results", [])
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )


def _render_benchmark_resumido_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    st.subheader("Benchmark resumido")
    st.write("Snapshot curto dos indicadores institucionais atuais.")
    latest_generation = _load_latest_generated_games() or {}
    latest_reconciliation = _load_latest_reconciliation_summary() or {}
    cols = st.columns(4)
    cols[0].metric("generated_games", int(snapshot["counts"].get("generated_games", 0)))
    cols[1].metric("reconciliation_runs", int(snapshot["counts"].get("reconciliation_runs", 0)))
    cols[2].metric("imported_contests", int(snapshot["counts"].get("imported_contests", 0)))
    cols[3].metric("latest_generation", latest_generation.get("generation_event_id", "-"))
    summary_cols = st.columns(2)
    with summary_cols[0]:
        st.markdown("##### Última geração")
        st.json(
            {
                "generation_event_id": latest_generation.get("generation_event_id", "-"),
                "seed": latest_generation.get("seed", "-"),
                "total_games": latest_generation.get("total_games", 0),
                "target_contest": latest_generation.get("target_contest", "-"),
            }
        )
    with summary_cols[1]:
        st.markdown("##### Última reconciliação")
        st.json(latest_reconciliation or {"status": "sem_reconciliação"})


def _render_estatisticas_operacionais_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    st.subheader("Estatísticas operacionais")
    st.write("Fluxo operacional persistido e sessão corrente.")
    latest_generation = _load_latest_generated_games() or {}
    latest_reconciliation = _load_latest_reconciliation_summary() or {}
    cols = st.columns(4)
    cols[0].metric("generation_events", int(snapshot["counts"].get("generation_events", 0)))
    cols[1].metric("generated_games", int(snapshot["counts"].get("generated_games", 0)))
    cols[2].metric("reconciliation_runs", int(snapshot["counts"].get("reconciliation_runs", 0)))
    cols[3].metric("session_keys", len([key for key in st.session_state.keys() if str(key).startswith("institutional_")]))
    st.caption(f"last_ui_event: {st.session_state.get('institutional_last_ui_event', '-')}")
    st.caption(f"latest_generation_event_id: {latest_generation.get('generation_event_id', '-')}")
    st.caption(f"latest_reconciliation_id: {latest_reconciliation.get('id', '-') if latest_reconciliation else '-'}")
def _sync_latest_official_result_now() -> dict[str, Any]:
    try:
        repository = ContestRepository(DB_PATH)
        service = ResultSyncService(repository=repository)
        summary = service.sync_latest()
        payload = summary.to_dict()
        payload["status"] = "ok"
        payload["http_status"] = getattr(service.client, "last_http_status", None)
        payload["request_url"] = getattr(service.client, "last_request_url", "")
        payload["request_headers"] = getattr(service.client, "last_request_headers", {})
        payload["response_headers"] = getattr(service.client, "last_response_headers", {})
        payload["response_preview"] = getattr(service.client, "last_response_preview", "")
        payload["sync_error"] = ""
        payload["sync_timestamp"] = datetime.now(UTC).isoformat()
        latest_record = repository.get_latest_contest_record()
        payload["latest_contest_record"] = latest_record
        payload["imported_numbers"] = list(latest_record.get("dezenas", []) if latest_record else [])
        try:
            export_historical_csv(repository.get_all_contests())
            payload["history_export_status"] = "ok"
        except Exception as export_exc:  # pragma: no cover - surfaced in UI
            payload["history_export_status"] = "failed"
            payload["history_export_error"] = str(export_exc)
        return payload
    except Exception as exc:  # pragma: no cover - surfaced in UI
        client = None
        return {
            "status": "error",
            "error_message": str(exc),
            "sync_error": str(exc),
            "sync_timestamp": datetime.now(UTC).isoformat(),
            "latest_contest": None,
            "synced_contests": [],
            "synced_contests_count": 0,
            "persisted_contests": 0,
            "provider_payload_count": 0,
            "contest_ids": [],
            "db_backend": "unknown",
            "engine_url": "",
            "commit_state": "failed",
            "source": "",
            "fallback_used": True,
            "rollback": True,
            "http_status": None,
            "request_url": "",
            "request_headers": {},
            "response_headers": {},
            "response_preview": "",
            "latest_contest_record": None,
            "imported_numbers": [],
        }


def _persist_generation_snapshot(
    *,
    games: list[dict[str, Any]],
    seed: int,
    target_contest: int | None,
    batch_id: str | None = None,
    generation_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started_at = time.monotonic()
    context_payload = {
        "source": "institutional_app",
        "target_contest": target_contest,
        "build_marker": BUILD_MARKER,
        "batch_id": batch_id,
    }
    if generation_context:
        context_payload.update({str(key): value for key, value in generation_context.items()})
    with get_session(DB_PATH) as session:
        event = GenerationEvent(
            lead_id=None,
            first_name="institutional",
            whatsapp="",
            generated_games=games,
            ml_enabled=0,
            seed=seed,
            strategy="institutional_clean_hb",
            ranking_score=0.0,
            execution_time_ms=0.0,
        )
        session.add(event)
        session.flush()
        generation_event_id = int(event.id)
        for index, game in enumerate(games, start=1):
            numbers = list(game.get("numbers", []))
            signature = _game_signature(numbers)
            session.add(
                GeneratedGame(
                    generation_event_id=generation_event_id,
                    lead_id=None,
                    target_contest=target_contest,
                    origin="institutional",
                    generation_mode="hb_baseline",
                    game_index=index,
                    numbers=numbers,
                    profile_type=str(game.get("profile_type", "")),
                    final_score=dict(game.get("final_score", {})) if isinstance(game.get("final_score"), dict) else {},
                    quadra_score=dict(game.get("quadra_score", {})) if isinstance(game.get("quadra_score"), dict) else {},
                    context_json={
                        **context_payload,
                        "game_signature": signature,
                        "game_index": index,
                    },
                )
            )
            session.add(
                InstitutionalOutputSignature(
                    batch_id=str(batch_id or "").strip() or "global",
                    generation_event_id=generation_event_id,
                    game_signature=signature,
                    payload={
                        "game_index": index,
                        "numbers": numbers,
                        "source": "institutional_app",
                        "build_marker": BUILD_MARKER,
                    },
                )
            )
        event.execution_time_ms = round((time.monotonic() - started_at) * 1000, 2)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise RuntimeError(
                f"Comandante de Saída bloqueou a persistência por assinatura duplicada na bateria {batch_id or 'global'}."
            ) from exc
        return {
            "generation_event_id": generation_event_id,
            "seed": seed,
            "games_count": len(games),
            "target_contest": target_contest,
            "batch_id": batch_id,
        }


def _count_generated_games_for_event(generation_event_id: int) -> int:
    with get_session(DB_PATH) as session:
        return int(
            session.query(GeneratedGame)
            .filter(GeneratedGame.generation_event_id == int(generation_event_id))
            .count()
        )


def _generated_games_count_sql(generation_event_id: int) -> str:
    return f"SELECT COUNT(*) FROM generated_games WHERE generation_event_id = {int(generation_event_id)};"


def _safe_get(row: Any, key: str, default: Any = None) -> Any:
    if row is None:
        return default
    if isinstance(row, dict):
        return row.get(key, default)
    getter = getattr(row, "get", None)
    if callable(getter):
        try:
            return getter(key, default)
        except Exception:
            pass
    return getattr(row, key, default)


def _safe_int(value: Any, default: int | None = None) -> int | None:
    if value is None:
        return default
    try:
        if isinstance(value, str):
            value = value.strip()
            if value in {"", "-", "None", "nan", "NaN"}:
                return default
        if value != value:  # NaN guard
            return default
        return int(float(value))
    except Exception:
        return default


def _institutional_output_batch_id() -> str:
    batch_id = str(st.session_state.get("institutional_output_batch_id", "") or "").strip()
    if not batch_id:
        batch_id = f"calibration-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
        st.session_state["institutional_output_batch_id"] = batch_id
    return batch_id


def _compare_games_against_contest(*, generation_event_id: int, games: list[dict[str, Any]], contest: dict[str, Any]) -> dict[str, Any]:
    official_numbers = _extract_int_numbers(contest.get("dezenas", []))
    results: list[dict[str, Any]] = []
    for index, game in enumerate(games, start=1):
        numbers = _extract_int_numbers(game.get("numbers", []))
        matched = sorted(set(numbers) & set(official_numbers))
        results.append(
            {
                "game_index": index,
                "numbers": numbers,
                "hits": len(matched),
                "matched_numbers": matched,
                "prize_status": "premiado" if len(matched) >= 11 else "nao_premiado",
                "prize_tier": f"faixa_{len(matched)}" if len(matched) >= 11 else "",
            }
        )
    best_hits = max((int(row["hits"]) for row in results), default=0)
    total_hits = sum(int(row["hits"]) for row in results)
    prize_count = sum(1 for row in results if int(row["hits"]) >= 11)
    diagnostics = {
        "official_numbers": official_numbers,
        "official_numbers_count": len(official_numbers),
        "first_game": results[0]["numbers"] if results else [],
        "first_game_hits": int(results[0]["hits"]) if results else 0,
        "first_intersection": results[0]["matched_numbers"] if results else [],
        "total_games": len(results),
        "total_hits": total_hits,
        "best_hits": best_hits,
        "prize_count": prize_count,
    }
    with get_session(DB_PATH) as session:
        run = ReconciliationRun(
            generation_event_id=generation_event_id,
            lead_id=None,
            contest_id=int(contest["contest_number"]),
            source="institutional",
            status="reconciled" if results else "sem_jogos",
            prize_count=prize_count,
            total_hits=total_hits,
            best_hits=best_hits,
            payload={
                "source": "institutional",
                "contest_id": int(contest["contest_number"]),
                "best_hits": best_hits,
                "total_hits": total_hits,
                "prize_count": prize_count,
            },
        )
        session.add(run)
        session.flush()
        for game in results:
            session.add(
                ReconciliationGame(
                    reconciliation_run_id=run.id,
                    generation_event_id=generation_event_id,
                    lead_id=None,
                    contest_id=int(contest["contest_number"]),
                    game_index=int(game["game_index"]),
                    numbers=list(game["numbers"]),
                    hits=int(game["hits"]),
                    matched_numbers=list(game["matched_numbers"]),
                    prize_status=str(game["prize_status"]),
                    prize_tier=str(game["prize_tier"]),
                    context_json={"source": "institutional", "build_marker": BUILD_MARKER},
                )
            )
        session.commit()
    return {
        "contest_number": int(contest["contest_number"]),
        "contest_date": str(contest.get("data", "")),
        "official_numbers": official_numbers,
        "results": results,
        "best_hits": best_hits,
        "total_hits": total_hits,
        "prize_count": prize_count,
        "reconciliation": {"id": int(run.id), "contest_id": int(contest["contest_number"])},
        "diagnostics": diagnostics,
    }


def _start_hb_geometry_job(*, resume: bool) -> None:
    def _runner() -> None:
        started_at = time.monotonic()
        with _JOB_LOCK:
            _JOB_STATE.update(
                {
                    "running": True,
                    "completed": False,
                    "error": "",
                    "started_at": started_at,
                }
            )
        try:
            result = run_hb_geometry_audit(
                contests_analyzed=30,
                games_count=5,
                pool_size=18,
                history_window=200,
                batch_size=5,
                lightweight=True,
                resume=resume,
                max_batches_per_run=1,
                output_dir=HB_GEOMETRY_DIR,
            )
            with _JOB_LOCK:
                _JOB_STATE.update(
                    {
                        "running": False,
                        "completed": bool(result.completed),
                        "current_scenario": str(result.scenarios[0]["scenario"]) if result.scenarios else "-",
                        "processed_batches": int(result.processed_batches),
                        "contests_processed": int(result.contests_analyzed),
                        "elapsed_time": float(time.monotonic() - started_at),
                        "error": "",
                        "result": result.to_dict(),
                    }
                )
        except Exception as exc:  # pragma: no cover
            with _JOB_LOCK:
                _JOB_STATE.update(
                    {
                        "running": False,
                        "completed": False,
                        "error": str(exc),
                        "elapsed_time": float(time.monotonic() - started_at),
                    }
                )

    thread = threading.Thread(target=_runner, daemon=True, name="hb-geometry-audit")
    thread.start()


def _reset_hb_geometry_job() -> None:
    for path in (HB_GEOMETRY_JSON_FILE, HB_GEOMETRY_CSV_FILE, HB_GEOMETRY_PROGRESS_FILE):
        if path.exists():
            try:
                path.unlink()
            except Exception:
                pass
    with _JOB_LOCK:
        _JOB_STATE.update(
            {
                "running": False,
                "completed": False,
                "current_scenario": "-",
                "processed_batches": 0,
                "contests_processed": 0,
                "elapsed_time": 0.0,
                "error": "",
                "result": None,
                "started_at": None,
            }
        )


def _render_sidebar(page: str, snapshot: dict[str, Any]) -> str:
    _apply_institutional_styles()
    _render_sidebar_logo()
    st.sidebar.markdown('<div class="lotoia-sidebar-divider"></div>', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="lotoia-nav-hint">Navegação</div>', unsafe_allow_html=True)
    st.sidebar.caption(f"build={APP_BUILD}")
    st.sidebar.caption("Painel institucional limpo")
    st.sidebar.markdown('<div class="lotoia-sidebar-group">Auditoria</div>', unsafe_allow_html=True)
    _sidebar_nav_button("Auditoria Runtime", "Auditoria Runtime", page)
    pages = list(PAGE_TARGETS.values())
    st.sidebar.markdown('<div class="lotoia-sidebar-group">Operações</div>', unsafe_allow_html=True)
    _sidebar_nav_button("Gerar Jogos", "Gerar Jogos", page)
    _sidebar_nav_button("Conferir Resultados", "Conferir Resultados", page)
    _sidebar_nav_button("Simular Resultados", "Simular Resultados", page)
    st.sidebar.markdown('<div class="lotoia-sidebar-group">Históricos</div>', unsafe_allow_html=True)
    _sidebar_nav_button("Histórico Analítico", "Histórico Analítico", page)
    _sidebar_nav_button("Histórico Institucional", "Histórico Institucional", page)
    _sidebar_nav_button("Limpar Históricos", "Limpar Históricos", page)
    _sidebar_nav_button("Apagar Histórico", "Apagar Histórico", page)
    _sidebar_nav_button("Comparativos histórico", "Comparativos histórico", page)
    st.sidebar.markdown('<div class="lotoia-sidebar-group">Estratégias</div>', unsafe_allow_html=True)
    _sidebar_nav_button("Análises Estratégicas", "Análises Estratégicas", page)
    _sidebar_nav_button("Testar Estratégias", "Testar Estratégias", page)
    _sidebar_nav_button("Simular Estratégias", "Simular Estratégias", page)
    st.sidebar.markdown('<div class="lotoia-sidebar-group">Analítico</div>', unsafe_allow_html=True)
    _sidebar_nav_button("Métricas HB", "Métricas HB", page)
    _sidebar_nav_button("Cobertura estrutural", "Cobertura estrutural", page)
    _sidebar_nav_button("Replay institucional", "Replay institucional", page)
    _sidebar_nav_button("Benchmark resumido", "Benchmark resumido", page)
    _sidebar_nav_button("Estatísticas operacionais", "Estatísticas operacionais", page)
    _sidebar_nav_button("HB Geometry", "HB Geometry", page)
    choice = _canonical_page_id(st.session_state.get("institutional_page_id") or page)
    if choice not in pages:
        choice = _canonical_page_id(page)
    st.session_state["institutional_page_id"] = choice
    st.sidebar.divider()
    st.sidebar.caption("DATABASE_URL conectada")
    return choice


def _ensure_institutional_schema() -> None:
    create_database(DB_PATH)


def _render_generation_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    _ensure_official_history_seeded()
    live_counts = _database_snapshot()["counts"]
    st.subheader("Gerar Jogos")
    st.write("Fluxo principal limpo, sem legado visual ou CRM.")
    status_cols = st.columns([1, 1, 1, 1, 1])
    status_cols[0].metric("build", BUILD_MARKER)
    status_cols[1].metric("backend", snapshot["backend"])
    status_cols[2].metric("imported_contests", int(live_counts.get("imported_contests", 0)))
    status_cols[3].metric("generated_games", int(live_counts.get("generated_games", 0)))
    status_cols[4].metric("reconciliation_runs", int(live_counts.get("reconciliation_runs", 0)))

    contest_summary = _get_latest_contest() or _load_latest_contest_summary()
    top_cols = st.columns([1.1, 1.3, 1.6])
    if contest_summary:
        top_cols[0].metric("Último concurso", int(contest_summary["contest_number"]))
        top_cols[1].caption(f"Fonte: {contest_summary.get('source', 'banco oficial')}")
        top_cols[2].caption(
            f"dezenas: {' '.join(f'{number:02d}' for number in contest_summary.get('dezenas', [])) or '-'}"
        )
    else:
        top_cols[0].caption("Último concurso: -")
        top_cols[1].caption("Fonte: banco vazio")

    official_generation_policy = _institutional_generation_policy(int(st.session_state.get("institutional_dezenas_per_game", 15) or 15))
    current_dezenas_size = int(st.session_state.get("institutional_dezenas_per_game", 15) or 15)
    if current_dezenas_size == 15:
        st.session_state["institutional_total_games"] = 10
        st.session_state["institutional_generation_runs"] = 10
        st.session_state["institutional_repeat_limit"] = int(official_generation_policy.get("repeat_max", 10) or 10)
    controls_cols = st.columns([1.0, 1.0, 1.0, 1.0])
    total_games = int(
        controls_cols[0].number_input(
            "Quantidade de jogos por geração",
            min_value=1,
            max_value=100,
            value=int(st.session_state.get("institutional_total_games", 10 if current_dezenas_size == 15 else 15) or (10 if current_dezenas_size == 15 else 15)),
            step=1,
            key="institutional_total_games",
        )
    )
    generation_runs = int(
        controls_cols[1].number_input(
            "Quantidade de gerações na bateria",
            min_value=1,
            max_value=60,
            value=int(st.session_state.get("institutional_generation_runs", 10 if current_dezenas_size == 15 else 1) or (10 if current_dezenas_size == 15 else 1)),
            step=1,
            key="institutional_generation_runs",
        )
    )
    dezenas_per_game = int(
        controls_cols[2].number_input(
            "Quantidade de dezenas por jogo",
            min_value=2,
            max_value=MAX_INSTITUTIONAL_DEZENAS_PER_GAME,
            value=int(
                min(
                    MAX_INSTITUTIONAL_DEZENAS_PER_GAME,
                    max(2, int(st.session_state.get("institutional_dezenas_per_game", 15) or 15)),
                )
            ),
            step=1,
            key="institutional_dezenas_per_game",
        )
    )
    geometry_profile = _sync_hb_geometry_controls(dezenas_per_game)
    use_top50 = bool(
        controls_cols[3].checkbox(
            "Usar TOP50 estrutural HB",
            value=bool(st.session_state.get("institutional_use_top50", True)),
            key="institutional_use_top50",
        )
    )
    repeat_limit = int(
        controls_cols[3].number_input(
            "Máx. repetição do último concurso",
            min_value=0,
            max_value=15,
            value=int(st.session_state.get("institutional_repeat_limit", 10 if current_dezenas_size == 15 else 8) or (10 if current_dezenas_size == 15 else 8)),
            step=1,
            key="institutional_repeat_limit",
        )
    )

    parity_cols = st.columns([1.0, 1.0, 1.0, 1.0])
    odd_min = int(
        parity_cols[0].slider(
            "Ímpares mínimo",
            min_value=0,
            max_value=dezenas_per_game,
            value=int(st.session_state.get("institutional_odd_min", geometry_profile["odd_min"]) or geometry_profile["odd_min"]),
            key="institutional_odd_min",
        )
    )
    odd_max = int(
        parity_cols[1].slider(
            "Ímpares máximo",
            min_value=0,
            max_value=dezenas_per_game,
            value=int(st.session_state.get("institutional_odd_max", geometry_profile["odd_max"]) or geometry_profile["odd_max"]),
            key="institutional_odd_max",
        )
    )
    even_min = int(
        parity_cols[2].slider(
            "Pares mínimo",
            min_value=0,
            max_value=dezenas_per_game,
            value=int(st.session_state.get("institutional_even_min", geometry_profile["even_min"]) or geometry_profile["even_min"]),
            key="institutional_even_min",
        )
    )
    even_max = int(
        parity_cols[3].slider(
            "Pares máximo",
            min_value=0,
            max_value=dezenas_per_game,
            value=int(st.session_state.get("institutional_even_max", geometry_profile["even_max"]) or geometry_profile["even_max"]),
            key="institutional_even_max",
        )
    )

    structural_cols = st.columns([1.0, 1.0, 1.0, 1.0])
    sequence_max = int(
        structural_cols[0].slider(
            "Limite de sequência",
            min_value=1,
            max_value=dezenas_per_game,
            value=int(st.session_state.get("institutional_sequence_max", geometry_profile["sequence_max"]) or geometry_profile["sequence_max"]),
            key="institutional_sequence_max",
        )
    )
    coverage_min = float(
        structural_cols[1].slider(
            "Cobertura mínima",
            min_value=0.0,
            max_value=1.0,
            value=float(st.session_state.get("institutional_coverage_min", geometry_profile["coverage_min"]) or geometry_profile["coverage_min"]),
            step=0.05,
            key="institutional_coverage_min",
        )
    )
    entropy_min = float(
    structural_cols[2].slider(
            "Entropia mínima",
            min_value=0.0,
            max_value=1.0,
            value=float(st.session_state.get("institutional_entropy_min", geometry_profile["entropy_min"]) or geometry_profile["entropy_min"]),
            step=0.05,
            key="institutional_entropy_min",
        )
    )
    structural_cols[3].caption("Perfil geométrico adaptado automaticamente ao tamanho do jogo.")

    total_jogos_esperados = int(total_games) * int(generation_runs)
    st.markdown("##### Resumo da bateria")
    resume_cols = st.columns(4)
    resume_cols[0].metric("jogos por geração", int(total_games))
    resume_cols[1].metric("gerações na bateria", int(generation_runs))
    resume_cols[2].metric("dezenas por jogo", int(dezenas_per_game))
    resume_cols[3].metric("total esperado de jogos", total_jogos_esperados)
    if generation_runs > 1 and dezenas_per_game != 15:
        st.error("Nesta fase, a bateria oficial precisa usar 15 dezenas por jogo para manter a calibração institucional.")
    if dezenas_per_game == 15:
        st.info(
            " | ".join(
                [
                    f"repeticao_ultimo_concurso_min={official_generation_policy.get('repeat_min', 7)}",
                    f"repeticao_ultimo_concurso_max={official_generation_policy.get('repeat_max', 10)}",
                    f"perfis_paridade_preferenciais={official_generation_policy.get('preferred_parity_pairs', [])}",
                    f"perfis_paridade_permitidos={official_generation_policy.get('allowed_parity_pairs', [])}",
                    f"limite_sequencia_max={official_generation_policy.get('sequence_max', 6)}",
                    f"core_numbers={official_generation_policy.get('core_numbers', [])}",
                    f"discouraged_numbers={official_generation_policy.get('discouraged_numbers', [])}",
                    f"max_frequency_ratio={official_generation_policy.get('max_frequency_ratio', 1.0)}",
                    f"min_frequency_ratio={official_generation_policy.get('min_frequency_ratio', 0.0)}",
                ]
            )
        )

    button_cols = st.columns([0.28, 1.72])
    if button_cols[0].button("LotoIA", type="primary"):
        if generation_runs > 1 and dezenas_per_game != 15:
            st.error("A bateria institucional oficial exige 15 dezenas por jogo nesta fase.")
        else:
            if generation_runs > 1:
                _run_institutional_generation_batch(
                    generation_runs=generation_runs,
                    total_games=total_games,
                    dezenas_per_game=dezenas_per_game,
                    use_top50=use_top50,
                    odd_min=odd_min,
                    odd_max=odd_max,
                    even_min=even_min,
                    even_max=even_max,
                    sequence_max=sequence_max,
                    coverage_min=coverage_min,
                    entropy_min=entropy_min,
                    repeat_limit=repeat_limit,
                    snapshot=snapshot,
                )
            else:
                _run_institutional_generation(
                    total_games=total_games,
                    dezenas_per_game=dezenas_per_game,
                    use_top50=use_top50,
                    odd_min=odd_min,
                    odd_max=odd_max,
                    even_min=even_min,
                    even_max=even_max,
                    sequence_max=sequence_max,
                    coverage_min=coverage_min,
                    entropy_min=entropy_min,
                    repeat_limit=repeat_limit,
                    snapshot=snapshot,
                )
            st.rerun()
    st.caption("Escolha a quantidade antes de gerar.")

    batch_result = st.session_state.get("institutional_generation_batch_result") or {}
    generation_state = st.session_state.get("institutional_generation") or {}
    generation_result = st.session_state.get("institutional_generation_result") or {}
    if batch_result:
        st.info(
            " | ".join(
                [
                    f"quantidade_jogos_por_geracao={batch_result.get('quantidade_jogos_por_geracao', '-')}",
                    f"quantidade_geracoes_na_bateria={batch_result.get('quantidade_geracoes_na_bateria', '-')}",
                    f"quantidade_dezenas_por_jogo={batch_result.get('quantidade_dezenas_por_jogo', '-')}",
                    f"total_jogos_esperados={batch_result.get('total_jogos_esperados', '-')}",
                    f"repeticao_ultimo_concurso_min={batch_result.get('repeticao_ultimo_concurso_min', '-')}",
                    f"repeticao_ultimo_concurso_max={batch_result.get('repeticao_ultimo_concurso_max', '-')}",
                    f"perfis_paridade_preferenciais={batch_result.get('perfis_paridade_preferenciais', '-')}",
                    f"perfis_paridade_permitidos={batch_result.get('perfis_paridade_permitidos', '-')}",
                    f"limite_sequencia_max={batch_result.get('limite_sequencia_max', '-')}",
                    f"core_numbers={batch_result.get('core_numbers', '-')}",
                    f"discouraged_numbers={batch_result.get('discouraged_numbers', '-')}",
                    f"max_frequency_ratio={batch_result.get('max_frequency_ratio', '-')}",
                    f"min_frequency_ratio={batch_result.get('min_frequency_ratio', '-')}",
                    f"total_gens_solicitadas={batch_result.get('total_gens_solicitadas', '-')}",
                    f"total_jogos_solicitados={batch_result.get('total_jogos_solicitados', '-')}",
                    f"total_jogos_gerados={batch_result.get('total_jogos_gerados', '-')}",
                    f"total_jogos_unicos={batch_result.get('total_jogos_unicos', '-')}",
                    f"total_jogos_duplicados={batch_result.get('total_jogos_duplicados', '-')}",
                    f"taxa_duplicidade={batch_result.get('taxa_duplicidade', '-')}",
                    f"status_comandante_saida={batch_result.get('status_comandante_saida', '-')}",
                ]
            )
        )
        st.caption(f"institutional_output_signatures={batch_result.get('institutional_output_signatures', '-')}")
    summary_result = batch_result or generation_result
    if batch_result:
        batch_status = str(summary_result.get("status_comandante_saida", "BLOQUEADO") or "BLOQUEADO")
        batch_solicitados = int(summary_result.get("total_jogos_solicitados", 0) or 0)
        batch_aprovados = int(summary_result.get("total_jogos_aprovados", summary_result.get("total_jogos_unicos", 0)) or 0)
        batch_gerados = int(summary_result.get("total_jogos_gerados", batch_aprovados) or batch_aprovados)
        batch_unicos = int(summary_result.get("total_jogos_unicos", batch_aprovados) or batch_aprovados)
        batch_rejeitados = int(summary_result.get("total_jogos_rejeitados", max(0, batch_solicitados - batch_aprovados)) or 0)
        batch_motivo = str(summary_result.get("motivo_bloqueio", "não foi possível gerar a quantidade solicitada de jogos únicos") or "não foi possível gerar a quantidade solicitada de jogos únicos")
        if batch_status != "APROVADO":
            st.error(
                "Comandante de Saída bloqueou a bateria. "
                f"status = {batch_status} | "
                f"motivo = {batch_motivo} | "
                f"solicitados = {batch_solicitados} | "
                f"aprovados = {batch_aprovados} | "
                f"faltantes = {max(0, batch_solicitados - batch_aprovados)}"
            )
        else:
            st.success(
                "Bateria aprovada. "
                f"jogos por geração={summary_result.get('quantidade_jogos_por_geracao', '-')} | "
                f"gerações na bateria={summary_result.get('quantidade_geracoes_na_bateria', '-')} | "
                f"jogos gerados={batch_gerados}"
            )
        st.caption(
            " | ".join(
                [
                    f"quantidade_jogos_por_geracao={summary_result.get('quantidade_jogos_por_geracao', '-')}",
                    f"quantidade_geracoes_na_bateria={summary_result.get('quantidade_geracoes_na_bateria', '-')}",
                    f"quantidade_dezenas_por_jogo={summary_result.get('quantidade_dezenas_por_jogo', '-')}",
                    f"total_jogos_esperados={summary_result.get('total_jogos_esperados', '-')}",
                    f"repeticao_ultimo_concurso_min={summary_result.get('repeticao_ultimo_concurso_min', '-')}",
                    f"repeticao_ultimo_concurso_max={summary_result.get('repeticao_ultimo_concurso_max', '-')}",
                    f"perfis_paridade_preferenciais={summary_result.get('perfis_paridade_preferenciais', '-')}",
                    f"perfis_paridade_permitidos={summary_result.get('perfis_paridade_permitidos', '-')}",
                    f"limite_sequencia_max={summary_result.get('limite_sequencia_max', '-')}",
                    f"core_numbers={summary_result.get('core_numbers', '-')}",
                    f"discouraged_numbers={summary_result.get('discouraged_numbers', '-')}",
                    f"max_frequency_ratio={summary_result.get('max_frequency_ratio', '-')}",
                    f"min_frequency_ratio={summary_result.get('min_frequency_ratio', '-')}",
                    f"total_jogos_solicitados={batch_solicitados}",
                    f"total_jogos_candidatos={summary_result.get('total_jogos_candidatos', '-')}",
                    f"total_jogos_aprovados={batch_aprovados}",
                    f"total_jogos_gerados={batch_gerados}",
                    f"total_jogos_persistidos={int(summary_result.get('institutional_output_signatures', 0) or 0)}",
                    f"total_jogos_unicos={batch_unicos}",
                    f"total_jogos_duplicados={int(summary_result.get('total_jogos_duplicados', 0) or 0)}",
                    f"total_jogos_rejeitados={batch_rejeitados}",
                    f"motivo_bloqueio={batch_motivo}",
                    f"status_comandante_saida={batch_status}",
                    f"institutional_output_signatures={int(live_counts.get('institutional_output_signatures', 0))}",
                ]
            )
        )
    scientific_batch = {}
    scientific_batch_id = str(
        summary_result.get("batch_id")
        or generation_result.get("batch_id")
        or generation_state.get("batch_id")
        or ""
    ).strip()
    scientific_game_size = int(
        summary_result.get("quantidade_dezenas_por_jogo")
        or generation_result.get("quantidade_dezenas_solicitada")
        or generation_state.get("dezenas_per_game")
        or dezenas_per_game
    )
    if scientific_batch_id:
        scientific_batch = _scientific_batch_diagnostics(
            batch_id=scientific_batch_id,
            games=[] if batch_result else list(generation_result.get("jogos") or generation_state.get("games") or []),
            game_size=scientific_game_size,
        )
    if scientific_batch:
        st.markdown("##### Núcleo Científico Lotofácil")
        sci_cols = st.columns(6)
        sci_cols[0].metric("status_cientifico", scientific_batch.get("status_comandante_cientifico", "-"))
        sci_cols[1].metric("classificacao_cientifica", scientific_batch.get("classificacao_cientifica", "-"))
        sci_cols[2].metric("maior_acerto", int(scientific_batch.get("best_hits", 0) or 0))
        sci_cols[3].metric("11+", int(scientific_batch.get("count_11_plus", 0) or 0))
        sci_cols[4].metric("12+", int(scientific_batch.get("count_12_plus", 0) or 0))
        sci_cols[5].metric("13+", int(scientific_batch.get("count_13_plus", 0) or 0))
        sci_cols_2 = st.columns(4)
        sci_cols_2[0].metric("media_best_hits", f"{float(scientific_batch.get('average_best_hits', 0.0) or 0.0):.4f}")
        sci_cols_2[1].metric("media_hits", f"{float(scientific_batch.get('average_hits', 0.0) or 0.0):.4f}")
        sci_cols_2[2].metric(
            "freq_max",
            f"{float(scientific_batch.get('frequency_maxima_dezena_percentual', 0.0) or 0.0):.2f}%",
        )
        sci_cols_2[3].metric(
            "freq_min_nucleo",
            f"{float(scientific_batch.get('frequency_minima_dezena_candidata_percentual', 0.0) or 0.0):.2f}%",
        )
        st.caption(
            " | ".join(
                [
                    f"status_estrutural={batch_status if batch_result else generation_result.get('status_comandante_saida', '-') if generation_result else '-'}",
                    f"status_cientifico={scientific_batch.get('status_comandante_cientifico', '-')}",
                    f"classificacao_cientifica={scientific_batch.get('classificacao_cientifica', '-')}",
                    f"reference_window={scientific_batch.get('reference_window', [])}",
                    f"repeticao_media={scientific_batch.get('average_repetition', '-')} ",
                    f"sequencia_media={scientific_batch.get('average_sequence_max', '-')}",
                ]
            )
        )
        if scientific_batch.get("motivo_cientifico"):
            if scientific_batch.get("status_comandante_cientifico") == "APROVADO":
                st.success(
                    f"Núcleo Científico Lotofácil aprovou a bateria. motivo={scientific_batch.get('motivo_cientifico', '-')}"
                )
            else:
                st.warning(
                    f"Núcleo Científico Lotofácil reprovou a bateria. motivo={scientific_batch.get('motivo_cientifico', '-')}"
                )
        with st.expander("Diagnóstico científico completo", expanded=False):
            st.json(scientific_batch)
    if scientific_batch_id:
        scientific_calibration_games = _load_scientific_batch_games(scientific_batch_id)
        scientific_calibration_mode = st.selectbox(
            "modo de calibração",
            ["OBSERVAÇÃO", "AUTONOMIA SUPERVISIONADA"],
            index=0 if str(scientific_batch.get("status_comandante_cientifico", "")).upper() != "APROVADO" else 1,
            key=f"scientific_calibration_mode_{scientific_batch_id}",
        )
        scientific_calibration_context = evaluate_last_batch(
            game_size=scientific_game_size,
            batch_id=scientific_batch_id,
            mode=scientific_calibration_mode,
            games=scientific_calibration_games,
            db_path=DB_PATH,
        )
        scientific_calibration_policy = generate_recalibration_policy(scientific_calibration_context)
        scientific_calibration_recommendation = recommend_next_strategy(scientific_calibration_context)
        st.markdown("##### Motor Científico de Calibração")
        calibration_cols = st.columns(6)
        calibration_cols[0].metric("modo", scientific_calibration_context.get("mode", "-"))
        calibration_cols[1].metric("status_estrutural", scientific_calibration_context.get("structural_status", "-"))
        calibration_cols[2].metric("status_cientifico", scientific_calibration_context.get("scientific_status", "-"))
        calibration_cols[3].metric("classificacao", scientific_calibration_context.get("classification", "-"))
        calibration_cols[4].metric("acao_sugerida", scientific_calibration_recommendation.get("action_suggested", "-"))
        calibration_cols[5].metric("status_visual", scientific_calibration_recommendation.get("status_visual", "-"))
        st.caption(
            " | ".join(
                [
                    f"source_batch_id={scientific_calibration_context.get('source_batch_id', '-')}",
                    f"main_reason={scientific_calibration_context.get('main_reason', '-') or '-'}",
                    f"policy_before={scientific_calibration_context.get('policy_before', {})}",
                    f"policy_after={scientific_calibration_policy}",
                ]
            )
        )
        if st.button(
            "Registrar decisão científica",
            key=f"register_scientific_calibration_{scientific_batch_id}",
            use_container_width=False,
        ):
            calibration_decision = apply_supervised_calibration(
                scientific_calibration_context,
                auto_apply=str(scientific_calibration_mode).upper() == "AUTONOMIA SUPERVISIONADA",
            )
            registered_decision = register_calibration_decision(
                scientific_calibration_context,
                decision=calibration_decision,
                db_path=DB_PATH,
            )
            st.success(
                f"Decisão científica registrada. classification={registered_decision.get('classification', '-')} | "
                f"mode={registered_decision.get('mode', '-')} | applied={registered_decision.get('applied', False)}"
            )
            with st.expander("Memória científica registrada", expanded=False):
                st.json(registered_decision)
        latest_scientific_decisions = _load_latest_scientific_calibration_decision(limit=5)
        if latest_scientific_decisions:
            st.markdown("###### Últimas decisões científicas")
            st.dataframe(pd.DataFrame(latest_scientific_decisions), hide_index=True, use_container_width=True)
    if generation_result and not batch_result:
        generation_event_id = int(generation_result.get("generation_event_id") or 0)
        persisted_count = _count_generated_games_for_event(generation_event_id) if generation_event_id else 0
        generation_runtime_status = str(generation_result.get("status_comandante_saida") or generation_state.get("runtime_status") or "")
        if generation_runtime_status == "ERRO_CRITICO" or not generation_result.get("jogos"):
            st.error(
                f"Comandante de Saída bloqueou a bateria. status={generation_runtime_status or '-'} | "
                f"erro={generation_result.get('error_message', 'diversidade insuficiente')}"
            )
        else:
            st.success(
                f"Geração concluída. generation_event_id={generation_result.get('generation_event_id', '-')} | jogos={len(generation_result.get('jogos') or [])} | seed={generation_result.get('seed', '-')}"
            )
            if generation_event_id:
                st.code(_generated_games_count_sql(generation_event_id), language="sql")
                st.caption(f"SQL_COUNT_RESULT={persisted_count}")
        st.caption(
            " | ".join(
                [
                    f"quantidade_jogos_solicitada={generation_result.get('quantidade_jogos_solicitada', '-')}",
                    f"quantidade_dezenas_solicitada={generation_result.get('quantidade_dezenas_solicitada', '-')}",
                    f"quantidade_jogos_real_gerada={generation_result.get('quantidade_jogos_real_gerada', '-')}",
                    f"quantidade_jogos_persistida={persisted_count}",
                    f"generation_event_id={generation_event_id or '-'}",
                    f"len(generated_games)={len(generation_result.get('jogos') or [])}",
                    f"len_todos_os_jogos={generation_result.get('len_todos_os_jogos', [])}",
                    f"len_primeiro_jogo={generation_result.get('len_primeiro_jogo', '-')}",
                    f"primeiro_jogo={' '.join(f'{number:02d}' for number in generation_result.get('primeiro_jogo', [])) or '-'}",
                ]
            )
        )
        st.caption(
            " | ".join(
                [
                    f"status_comandante_saida={generation_result.get('status_comandante_saida', '-')}",
                    f"total_jogos_unicos={generation_result.get('total_jogos_unicos', '-')}",
                    f"total_jogos_duplicados={generation_result.get('total_jogos_duplicados', '-')}",
                    f"taxa_duplicidade={generation_result.get('taxa_duplicidade', 0.0):.4f}" if isinstance(generation_result.get("taxa_duplicidade"), (int, float)) else f"taxa_duplicidade={generation_result.get('taxa_duplicidade', '-')}",
                    f"batch_id={generation_result.get('batch_id', '-')}",
                ]
            )
        )
        commander_cols = st.columns(6)
        commander_cols[0].metric("total_jogos_solicitados", int(generation_result.get("quantidade_jogos_solicitada", 0) or 0))
        commander_cols[1].metric("total_jogos_gerados", int(generation_result.get("quantidade_jogos_real_gerada", 0) or 0))
        commander_cols[2].metric("total_jogos_unicos", int(generation_result.get("total_jogos_unicos", 0) or 0))
        commander_cols[3].metric("total_jogos_duplicados", int(generation_result.get("total_jogos_duplicados", 0) or 0))
        commander_cols[4].metric(
            "taxa_duplicidade",
            f"{float(generation_result.get('taxa_duplicidade', 0.0) or 0.0):.4f}"
            if isinstance(generation_result.get("taxa_duplicidade"), (int, float))
            else generation_result.get("taxa_duplicidade", "-"),
        )
        commander_cols[5].metric(
            "status_comandante_saida",
            str(generation_result.get("status_comandante_saida", "APROVADO") or "APROVADO"),
        )
        st.caption(
            f"institutional_output_signatures={int(live_counts.get('institutional_output_signatures', 0))} | "
            f"batch_id={generation_result.get('batch_id', '-')}"
        )
        with st.expander("Diagnóstico do Comandante de Saída", expanded=True):
            commander_diag = pd.DataFrame(
                [
                    {
                        "total_jogos_solicitados": int(generation_result.get("quantidade_jogos_solicitada", 0) or 0),
                        "total_jogos_gerados": int(generation_result.get("quantidade_jogos_real_gerada", 0) or 0),
                        "total_jogos_unicos": int(generation_result.get("total_jogos_unicos", 0) or 0),
                        "total_jogos_duplicados": int(generation_result.get("total_jogos_duplicados", 0) or 0),
                        "taxa_duplicidade": float(generation_result.get("taxa_duplicidade", 0.0) or 0.0),
                        "status_comandante_saida": str(generation_result.get("status_comandante_saida", "APROVADO") or "APROVADO"),
                        "institutional_output_signatures": int(live_counts.get("institutional_output_signatures", 0)),
                    }
                ]
            )
            st.dataframe(commander_diag, hide_index=True, use_container_width=True)
        if generation_result.get("jogos"):
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "rank": index + 1,
                            "dezenas": " ".join(f"{number:02d}" for number in game.get("numbers", [])),
                            "perfil": game.get("profile_type", "-"),
                            "pares": int(game.get("even", 0) or 0),
                            "ímpares": int(game.get("odd", 0) or 0),
                            "seq_max": int(game.get("structural_metrics", {}).get("sequence_max", 0) or 0),
                            "cobertura": round(float(game.get("structural_metrics", {}).get("coverage_score", 0.0) or 0.0), 4),
                            "entropia": round(float(game.get("structural_metrics", {}).get("entropy_score", 0.0) or 0.0), 4),
                            "score": round(float(game.get("final_score", {}).get("final_score", 0.0)), 4),
                        }
                        for index, game in enumerate(generation_result.get("jogos") or [])
                    ]
                ),
                hide_index=True,
                use_container_width=True,
            )
    elif generation_state.get("games"):
        st.info("Última geração carregada. Use o menu lateral para conferir ou simular novamente.")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "rank": index + 1,
                        "dezenas": " ".join(f"{number:02d}" for number in game.get("numbers", [])),
                        "perfil": game.get("profile_type", "-"),
                        "pares": int(game.get("even", 0) or 0),
                        "ímpares": int(game.get("odd", 0) or 0),
                        "seq_max": int(game.get("structural_metrics", {}).get("sequence_max", 0) or 0),
                        "cobertura": round(float(game.get("structural_metrics", {}).get("coverage_score", 0.0) or 0.0), 4),
                        "entropia": round(float(game.get("structural_metrics", {}).get("entropy_score", 0.0) or 0.0), 4),
                        "score": round(float(game.get("final_score", {}).get("final_score", 0.0)), 4),
                    }
                    for index, game in enumerate(generation_state.get("games") or [])
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.caption("Use a barra lateral para acionar geração, conferência e simulação.")

    latest_contest = _load_imported_contest()
    latest_generation = _load_latest_generated_games() or {}
    contest_number = None
    contest_numbers_text = "-"
    contest_source = "banco oficial"
    if latest_contest:
        contest_number = int(latest_contest.get("contest_number", 0) or 0)
        contest_numbers_text = " ".join(f"{number:02d}" for number in latest_contest.get("dezenas", [])) or "-"
    elif str(latest_generation.get("target_contest") or "").isdigit():
        contest_number = int(latest_generation.get("target_contest") or 0)
        contest_source = "última geração persistida"
    if contest_number:
        contest_cols = st.columns([0.65, 1.6])
        contest_cols[0].metric("Último concurso", contest_number)
        contest_cols[1].caption(f"Fonte: {contest_source} | dezenas: {contest_numbers_text}")
    else:
        st.caption("Último concurso: -")


def _render_conference_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    live_counts = _database_snapshot()["counts"]
    st.subheader("Conferir Resultados")
    st.write("Compare os jogos gerados com o concurso selecionado no banco.")
    status_cols = st.columns([1, 1, 1, 1])
    status_cols[0].metric("imported_contests", int(live_counts.get("imported_contests", 0)))
    status_cols[1].metric("generated_games", int(live_counts.get("generated_games", 0)))
    status_cols[2].metric("reconciliation_runs", int(live_counts.get("reconciliation_runs", 0)))

    live_counts_imported_contests = int(live_counts.get("imported_contests", 0))
    try:
        with _get_engine_cached().begin() as connection:
            runtime_query_imported_contests = int(
                connection.execute(text('SELECT COUNT(*) FROM "imported_contests"')).scalar() or 0
            )
        runtime_query_error = ""
    except Exception as exc:  # pragma: no cover - surfaced in UI
        runtime_query_imported_contests = None
        runtime_query_error = str(exc)

    latest_contest = _get_latest_contest()
    latest_generation = _load_latest_generated_games() or {}
    current_contest = (
        int(latest_contest["contest_number"])
        if latest_contest
        else int(latest_generation.get("target_contest") or 0)
        if str(latest_generation.get("target_contest") or "").isdigit()
        else 0
    )
    if "institutional_contest_nav" not in st.session_state:
        st.session_state["institutional_contest_nav"] = current_contest or 0
    if current_contest and int(st.session_state.get("institutional_contest_nav", 0) or 0) != current_contest:
        st.session_state["institutional_contest_nav"] = current_contest
    nav_cols = st.columns([0.35, 1.0, 0.35, 1.35])
    if nav_cols[0].button("−", use_container_width=True, disabled=not bool(current_contest)):
        st.session_state["institutional_contest_nav"] = max(0, int(st.session_state.get("institutional_contest_nav", current_contest or 0)) - 1)
    nav_cols[1].markdown(
        f"<div style='padding-top:0.2rem;font-size:0.78rem;letter-spacing:0.08em;color:#6b7280;text-transform:uppercase;'>Último concurso</div>",
        unsafe_allow_html=True,
    )
    if nav_cols[2].button("+", disabled=not bool(current_contest)):
        st.session_state["institutional_contest_nav"] = int(st.session_state.get("institutional_contest_nav", current_contest or 0)) + 1
    selected_contest = int(st.session_state.get("institutional_contest_nav", current_contest or 0) or 0) if current_contest else 0
    if selected_contest:
        nav_cols[3].metric("Último concurso", selected_contest)
    else:
        nav_cols[3].caption("Último concurso: -")
    contest_buttons = st.columns([0.48, 0.62, 0.66])
    if contest_buttons[0].button("Conferir Resultados", type="primary", disabled=not bool(selected_contest)):
        _run_institutional_conference(contest_number=selected_contest if selected_contest else None)
        st.rerun()
    if contest_buttons[1].button("Sincronizar resultado oficial agora", type="primary"):
        with st.status("Importando resultado oficial da Caixa...", expanded=True) as sync_status:
            sync_payload = _sync_latest_official_result_now()
            st.session_state["institutional_last_official_sync_summary"] = dict(sync_payload)
            st.session_state["institutional_sync_status"] = str(sync_payload.get("status", "unknown"))
            st.session_state["institutional_sync_error"] = str(sync_payload.get("sync_error") or sync_payload.get("error_message") or "")
            st.session_state["institutional_sync_timestamp"] = str(sync_payload.get("sync_timestamp") or datetime.now(UTC).isoformat())
            st.session_state["institutional_sync_http_status"] = sync_payload.get("http_status")
            st.session_state["institutional_sync_request_url"] = str(sync_payload.get("request_url") or "")
            st.session_state["institutional_imported_contest"] = sync_payload.get("latest_contest")
            latest_contest_record = _normalize_contest_record(sync_payload.get("latest_contest_record"))
            st.session_state["institutional_imported_numbers"] = list(latest_contest_record.get("dezenas", [])) if latest_contest_record else list(sync_payload.get("imported_numbers", []) or [])
            _persist_official_sync_diagnostics(
                {
                    "sync_status": st.session_state.get("institutional_sync_status", "-"),
                    "sync_error": st.session_state.get("institutional_sync_error", ""),
                    "sync_timestamp": st.session_state.get("institutional_sync_timestamp", ""),
                    "http_status": st.session_state.get("institutional_sync_http_status", None),
                    "request_url": st.session_state.get("institutional_sync_request_url", ""),
                    "imported_contest": st.session_state.get("institutional_imported_contest", None),
                    "imported_numbers": st.session_state.get("institutional_imported_numbers", []),
                    "payload": sync_payload,
                }
            )
            if sync_payload.get("status") == "ok":
                sync_status.update(label=f"Resultado oficial importado: {sync_payload.get('latest_contest', '-')}", state="complete")
            else:
                sync_status.update(label="Falha ao importar resultado oficial", state="error")
        try:
            st.cache_data.clear()
        except Exception:
            pass
        if sync_payload.get("status") == "ok":
            st.success(f"Resultado oficial importado: {sync_payload.get('latest_contest', '-')}")
        else:
            st.error(f"Falha ao importar resultado oficial: {sync_payload.get('error_message', '-')}")
            if sync_payload.get("traceback"):
                st.exception(RuntimeError(sync_payload.get("error_message", "Falha na sincronização")))
        st.json(sync_payload)
        st.session_state["institutional_sync_last_payload"] = dict(sync_payload)
        time.sleep(1.3)
        st.rerun()
    if contest_buttons[2].button("Importar último resultado oficial", type="primary"):
        with st.status("Sincronizando o último resultado oficial...", expanded=True) as sync_status:
            sync_payload = _sync_latest_official_result_now()
            st.session_state["institutional_last_official_sync_summary"] = dict(sync_payload)
            st.session_state["institutional_sync_status"] = str(sync_payload.get("status", "unknown"))
            st.session_state["institutional_sync_error"] = str(sync_payload.get("sync_error") or sync_payload.get("error_message") or "")
            st.session_state["institutional_sync_timestamp"] = str(sync_payload.get("sync_timestamp") or datetime.now(UTC).isoformat())
            st.session_state["institutional_sync_http_status"] = sync_payload.get("http_status")
            st.session_state["institutional_sync_request_url"] = str(sync_payload.get("request_url") or "")
            st.session_state["institutional_imported_contest"] = sync_payload.get("latest_contest")
            latest_contest_record = _normalize_contest_record(sync_payload.get("latest_contest_record"))
            st.session_state["institutional_imported_numbers"] = list(latest_contest_record.get("dezenas", [])) if latest_contest_record else list(sync_payload.get("imported_numbers", []) or [])
            _persist_official_sync_diagnostics(
                {
                    "sync_status": st.session_state.get("institutional_sync_status", "-"),
                    "sync_error": st.session_state.get("institutional_sync_error", ""),
                    "sync_timestamp": st.session_state.get("institutional_sync_timestamp", ""),
                    "http_status": st.session_state.get("institutional_sync_http_status", None),
                    "request_url": st.session_state.get("institutional_sync_request_url", ""),
                    "imported_contest": st.session_state.get("institutional_imported_contest", None),
                    "imported_numbers": st.session_state.get("institutional_imported_numbers", []),
                    "payload": sync_payload,
                }
            )
            if sync_payload.get("status") == "ok":
                sync_status.update(label=f"Resultado oficial importado: {sync_payload.get('latest_contest', '-')}", state="complete")
            else:
                sync_status.update(label="Falha ao importar resultado oficial", state="error")
        try:
            st.cache_data.clear()
        except Exception:
            pass
        if sync_payload.get("status") == "ok":
            st.success(f"Resultado oficial importado: {sync_payload.get('latest_contest', '-')}")
        else:
            st.error(f"Falha ao importar resultado oficial: {sync_payload.get('error_message', '-')}")
            if sync_payload.get("traceback"):
                st.exception(RuntimeError(sync_payload.get("error_message", "Falha na sincronização")))
        st.json(sync_payload)
        st.session_state["institutional_sync_last_payload"] = dict(sync_payload)
        time.sleep(1.3)
        st.rerun()
    if latest_contest:
        contest_buttons[0].caption(
            f"Último concurso: {int(latest_contest['contest_number'])} | dezenas: {' '.join(f'{number:02d}' for number in latest_contest.get('dezenas', [])) or '-'}"
        )
    elif latest_generation.get("target_contest"):
        contest_buttons[0].caption(f"Último concurso: {latest_generation.get('target_contest')}")
    else:
        contest_buttons[0].caption("Último concurso: -")

    diagnostic_state = _load_official_sync_diagnostics()
    if diagnostic_state:
        st.markdown("#### Diagnóstico da sincronização")
        diag_cols = st.columns(4)
        diag_cols[0].metric("sync_status", diagnostic_state.get("sync_status", "-"))
        diag_cols[1].metric("http_status", diagnostic_state.get("http_status", "-"))
        diag_cols[2].metric("imported_contest", diagnostic_state.get("imported_contest", "-"))
        diag_cols[3].metric("timestamp", diagnostic_state.get("sync_timestamp", "-"))
        st.caption(f"request_url: {diagnostic_state.get('request_url', '-')}")
        st.caption(f"request_headers: {json.dumps(diagnostic_state.get('request_headers', {}), ensure_ascii=False)}")
        st.caption(f"response_headers: {json.dumps(diagnostic_state.get('response_headers', {}), ensure_ascii=False)}")
        preview = str(diagnostic_state.get("response_preview") or "")
        if preview:
            st.text_area("response_preview", preview[:500], height=160)
        if diagnostic_state.get("sync_error"):
            st.error(diagnostic_state.get("sync_error"))
        imported_numbers = diagnostic_state.get("imported_numbers") or []
        if imported_numbers:
            st.caption("dezenas importadas: " + " ".join(f"{int(number):02d}" for number in imported_numbers))

    check_result = st.session_state.get("institutional_check_result")
    if isinstance(check_result, dict) and check_result.get("warning"):
        st.warning(check_result["warning"])
    if isinstance(check_result, dict):
        generation_results = list(check_result.get("generation_results") or [])
        if generation_results:
            st.markdown("#### Resumo geral")
            total_games_reconciled = sum(int(item.get("total_games", 0) or 0) for item in generation_results)
            total_runs = len(generation_results)
            best_hits = max((int(item.get("best_hits", 0) or 0) for item in generation_results), default=0)
            total_hits = int(check_result.get("total_hits", 0) or 0)
            prize_count = int(check_result.get("prize_count", 0) or 0)
            st.write(total_runs)
            st.write(total_games_reconciled)
            st.write(best_hits)
            st.write(f"total_runs={total_runs}")
            st.write(f"total_games_reconciled={total_games_reconciled}")
            st.write(f"best_hits={best_hits}")
            summary_cols = st.columns(5)
            summary_cols[0].metric("Concurso", check_result.get("contest_number", "-"))
            summary_cols[1].metric("Total jogos conferidos", total_games_reconciled)
            summary_cols[2].metric("Melhor acerto", best_hits)
            summary_cols[3].metric("Prêmios", prize_count)
            summary_cols[4].metric("Total hits", total_hits)
            hit_totals: Counter[int] = Counter()
            for item in generation_results:
                for row in item.get("results", []) or []:
                    hit_totals[int(row.get("hits", 0) or 0)] += 1
            hit_counts_df = pd.DataFrame(
                [
                    {"faixa": f"{hits} acertos", "quantidade": count}
                    for hits, count in sorted(hit_totals.items(), key=lambda item: (-item[0], item[1]))
                    if hits >= 10
                ]
            )
            if not hit_counts_df.empty:
                st.dataframe(hit_counts_df, hide_index=True, use_container_width=True)
            st.markdown("#### Por geração")
            for item in generation_results:
                title = f"Geração #{item.get('generation_event_id', '-')}"
                with st.expander(
                    f"{title} | jogos={item.get('total_games', '-') } | best_hits={item.get('best_hits', '-')}",
                    expanded=False,
                ):
                    gen_cols = st.columns(4)
                    gen_cols[0].metric("seed", item.get("seed", "-"))
                    gen_cols[1].metric("contest", item.get("contest_number", "-"))
                    gen_cols[2].metric("best_hits", item.get("best_hits", "-"))
                    gen_cols[3].metric("prize_count", item.get("prize_count", "-"))
                    generation_df = pd.DataFrame(
                        [
                            {
                                "jogo": row["game_index"],
                                "dezenas": " ".join(f"{number:02d}" for number in row["numbers"]),
                                "hits": row["hits"],
                                "premiado": row["prize_status"],
                                "matched_numbers": " ".join(f"{number:02d}" for number in row.get("matched_numbers", [])),
                            }
                            for row in item.get("results", []) or []
                        ]
                    )
                    if not generation_df.empty:
                        st.dataframe(generation_df, hide_index=True, use_container_width=True)
                    else:
                        st.info("Nenhum jogo encontrado para esta geração.")
            diagnostics = check_result.get("diagnostics") or {}
            if diagnostics:
                st.markdown("#### Diagnóstico temporário")
                st.write(f"Resultado oficial: {diagnostics.get('official_numbers', [])}")
                st.write(f"Tipo resultado: {type(diagnostics.get('official_numbers', []))}")
                st.write(f"Primeiro jogo: {diagnostics.get('first_game', [])}")
                st.write(f"Tipo jogo: {type(diagnostics.get('first_game', []))}")
                st.write(f"Interseção: {set(int(number) for number in diagnostics.get('first_intersection', []) or [])}")
                st.write(f"Hits: {diagnostics.get('first_game_hits', 0)}")
            st.markdown("#### Últimas reconciliações")
            reconciliations = _load_reconciliation_history(limit=10)
            if reconciliations:
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "concurso": row.get("contest_id", "-"),
                                "data": row.get("created_at", "-"),
                                "jogos conferidos": row.get("games_count", "-"),
                                "melhor acerto": row.get("best_hits", "-"),
                                "prêmios": row.get("prize_count", "-"),
                            }
                            for row in reconciliations
                        ]
                    ),
                    hide_index=True,
                    use_container_width=True,
                )
            else:
                st.info("Ainda não há reconciliações persistidas nesta instância.")
            st.markdown("#### Conferência")
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "jogo": row["game_index"],
                            "dezenas": " ".join(f"{number:02d}" for number in row["numbers"]),
                            "hits": row["hits"],
                            "premiado": row["prize_status"],
                        }
                        for generation in generation_results
                        for row in generation.get("results", []) or []
                    ]
                ),
                hide_index=True,
                use_container_width=True,
            )
        elif check_result.get("status") == "waiting_contest":
            st.info("A conferência está pronta, mas ainda falta o concurso oficial em imported_contests.")
        elif check_result.get("status") == "checked":
            st.info("Conferência executada, mas nenhum resultado foi renderizado.")
    elif not latest_contest:
        st.info("Último concurso ainda não veio do banco. Use a sincronização oficial quando disponível.")


def _render_simulation_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    st.subheader("Simular Resultados")
    st.write("Digite as dezenas sorteadas para comparar com os jogos persistidos.")
    status_cols = st.columns([1, 1, 1, 1])
    status_cols[0].metric("generated_games", int(snapshot["counts"].get("generated_games", 0)))
    status_cols[1].metric("imported_contests", int(snapshot["counts"].get("imported_contests", 0)))
    status_cols[2].metric("last_event", st.session_state.get("institutional_last_ui_event", "-"))
    status_cols[3].metric("runtime", st.session_state.get("institutional_simulation", {}).get("runtime_status", "idle"))

    draw_input = st.text_input(
        "Dezenas sorteadas",
        value=st.session_state.get("institutional_draw_input", ""),
        placeholder="01 02 04 05 07 08 09 13 14 17 18 19 20 22 24",
    )
    st.session_state["institutional_draw_input"] = draw_input
    if st.button("Simular Resultados", type="primary"):
        parsed_draw = _parse_draw_numbers(draw_input)
        if len(parsed_draw) != 15:
            st.warning("Informe exatamente 15 dezenas válidas entre 1 e 25.")
        else:
            _run_institutional_simulation(drawn_numbers=parsed_draw)
            st.session_state["institutional_last_ui_event"] = "operacional:simular_resultado"
            st.rerun()
    st.caption("Cole as 15 dezenas sorteadas para conferir com os jogos gerados e persistidos.")

    simulation_state = st.session_state.get("institutional_simulation") or {}
    if simulation_state:
        sim_diag_cols = st.columns([1, 1, 1, 1])
        sim_diag_cols[0].metric("source", str(simulation_state.get("source", "-") or "-"))
        sim_diag_cols[1].metric("loaded_games", int(simulation_state.get("loaded_games", 0) or 0))
        sim_diag_cols[2].metric("compared_games", int(simulation_state.get("compared_games", 0) or 0))
        sim_diag_cols[3].metric("premium_games", int(simulation_state.get("premium_games", 0) or 0))
        with st.expander("Diagnóstico da simulação", expanded=False):
            st.json(simulation_state.get("summary") or {})
            st.write("Jogos carregados:", int(simulation_state.get("loaded_games", 0) or 0))
            st.write("Jogos comparados:", int(simulation_state.get("compared_games", 0) or 0))
            error_payload = st.session_state.get("institutional_simulation_error")
            if error_payload:
                st.error(error_payload.get("error", "Erro desconhecido"))

    cover_result = st.session_state.get("institutional_simulation_result")
    if cover_result:
        st.markdown("#### Resultado da simulação")
        st.caption("Apenas os jogos premiados com 11 pontos ou mais aparecem abaixo.")
        rows_html = []
        premium_rows = [row for row in cover_result if int(row.get("hits", 0)) >= 11]
        for row in premium_rows:
            rows_html.append(
                "<tr>"
                f"<td>{row.get('jogo', '-')}</td>"
                f"<td>{row.get('resultado', '-')}</td>"
                f"<td>{row.get('hits', '-')}</td>"
                f"<td>{row.get('premiado', '-')}</td>"
                "</tr>"
            )
        if premium_rows:
            st.markdown(
                """
                <table class="lotoia-sim-table">
                    <thead>
                        <tr>
                            <th>jogo</th>
                            <th>resultado</th>
                            <th>hits</th>
                            <th>premiado</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                + "".join(rows_html)
                + """
                    </tbody>
                </table>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("Nenhum jogo premiado com 11 pontos ou mais nesta simulação.")
            st.dataframe(
                pd.DataFrame(cover_result)[
                    ["jogo", "dezenas", "hits", "premiado"]
                ]
                if cover_result
                else pd.DataFrame(columns=["jogo", "dezenas", "hits", "premiado"]),
                hide_index=True,
                use_container_width=True,
            )
    elif simulation_state.get("runtime_status") == "error":
        st.error("A simulação encontrou um erro. Veja o diagnóstico acima.")
    else:
        st.info("Nenhum jogo encontrado para simulação.")


def _render_history_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    _render_analytical_page(snapshot)


def _render_operational_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    st.subheader("Operacional")
    st.write("Fluxo principal limpo, sem legado visual ou CRM.")
    status_cols = st.columns([1, 1, 1, 1, 1])
    status_cols[0].metric("build", BUILD_MARKER)
    status_cols[1].metric("backend", snapshot["backend"])
    status_cols[2].metric("imported_contests", int(snapshot["counts"].get("imported_contests", 0)))
    status_cols[3].metric("generated_games", int(snapshot["counts"].get("generated_games", 0)))
    status_cols[4].metric("reconciliation_runs", int(snapshot["counts"].get("reconciliation_runs", 0)))

    contest_numbers = _load_imported_contest_numbers()
    latest_contest = _load_imported_contest()
    selected_contest = int(contest_numbers[-1]) if contest_numbers else int(snapshot["latest"].get("imported_contests") or 0) if str(snapshot["latest"].get("imported_contests", "")).isdigit() else 0
    latest_contest_number = latest_contest["contest_number"] if latest_contest else snapshot["latest"].get("imported_contests", "-")
    latest_contest_numbers = " ".join(f"{number:02d}" for number in (latest_contest.get("dezenas", []) if latest_contest else [])) or "-"

    top_cols = st.columns([1.3, 1.3, 1.8])
    top_cols[0].caption(f"Concurso alvo: {snapshot['latest'].get('imported_contests', '-')}")
    top_cols[1].caption("Cada jogo respeita a quantidade selecionada.")
    top_cols[2].caption(f"last_ui_event: {st.session_state.get('institutional_last_ui_event', '-')}")

    st.markdown("#### Motor de gera??o")
    gen_cols = st.columns([1.1, 0.75, 0.95, 0.8, 0.95])
    total_games = int(
        gen_cols[0].number_input(
            "Quantidade de jogos",
            min_value=1,
            max_value=100,
            value=15,
            step=1,
            key="institutional_total_games",
        )
    )
    if gen_cols[1].button("LotoIA", type="primary"):
        _run_institutional_generation(total_games=total_games, snapshot=snapshot)
        st.rerun()
    if gen_cols[2].button("Conferir Jogos", type="primary"):
        _run_institutional_conference(contest_number=selected_contest if selected_contest else None)
        st.rerun()
    gen_cols[3].number_input("?ltimo concurso", min_value=max(1, contest_numbers[0]) if contest_numbers else 1, max_value=max(contest_numbers) if contest_numbers else 999999, value=selected_contest if selected_contest else 1, step=1, key="institutional_contest_nav")
    if gen_cols[4].button("Simular Resultado", type="primary"):
        parsed_draw = _parse_draw_numbers(st.session_state.get("institutional_draw_input", ""))
        if len(parsed_draw) != 15:
            st.warning("Informe exatamente 15 dezenas v?lidas entre 1 e 25.")
        else:
            _run_institutional_simulation(drawn_numbers=parsed_draw)
            st.session_state["institutional_last_ui_event"] = "operacional:simular_resultado"
            st.rerun()
    st.caption("Escolha a quantidade antes de gerar.")

    generation_state = st.session_state.get("institutional_generation") or {}
    generation_result = st.session_state.get("institutional_generation_result") or {}
    if generation_result:
        st.success(
            f"Gera??o conclu?da. generation_event_id={generation_result.get('generation_event_id', '-')} | jogos={len(generation_result.get('jogos') or [])} | seed={generation_result.get('seed', '-')}"
        )
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "rank": index + 1,
                        "dezenas": " ".join(f"{number:02d}" for number in game.get("numbers", [])),
                        "perfil": game.get("profile_type", "-"),
                        "score": round(float(game.get("final_score", {}).get("final_score", 0.0)), 4),
                    }
                    for index, game in enumerate(generation_result.get("jogos") or [])
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )
    elif generation_state.get("games"):
        st.info("?ltima gera??o carregada. Use a barra lateral para gerar, conferir ou simular novamente.")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "rank": index + 1,
                        "dezenas": " ".join(f"{number:02d}" for number in game.get("numbers", [])),
                        "perfil": game.get("profile_type", "-"),
                        "score": round(float(game.get("final_score", {}).get("final_score", 0.0)), 4),
                    }
                    for index, game in enumerate(generation_state.get("games") or [])
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.caption("Use a barra lateral para acionar gera??o, confer?ncia e simula??o.")

    st.markdown("#### Simular Resultado")
    draw_input = st.text_input(
        "Dezenas sorteadas",
        value=st.session_state.get("institutional_draw_input", ""),
        placeholder="01 02 04 05 07 08 09 13 14 17 18 19 20 22 24",
    )
    st.session_state["institutional_draw_input"] = draw_input
    st.caption("Cole as 15 dezenas sorteadas para conferir com os jogos gerados e persistidos.")

    cover_result = st.session_state.get("institutional_simulation_result")
    if cover_result:
        st.markdown("#### Resultado da simula??o")
        st.caption("Confer?ncia dos jogos gerados contra as dezenas sorteadas informadas acima.")
        st.markdown(
            """
            <style>
            .lotoia-sim-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 0.95rem;
            }
            .lotoia-sim-table th,
            .lotoia-sim-table td {
                border-bottom: 1px solid rgba(0,0,0,0.08);
                padding: 0.55rem 0.6rem;
                vertical-align: top;
                text-align: left;
            }
            .lotoia-sim-table th {
                color: #6b7280;
                font-weight: 600;
            }
            .lotoia-sim-meta {
                color: #6b7280;
                font-size: 0.88rem;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        rows_html = []
        premium_rows = [row for row in cover_result if int(row.get("hits", 0)) >= 11]
        for row in premium_rows:
            rows_html.append(
                "<tr>"
                f"<td>{row.get('jogo', '-')}</td>"
                f"<td>{row.get('resultado', '-')}</td>"
                f"<td>{row.get('hits', '-')}</td>"
                f"<td>{row.get('premiado', '-')}</td>"
                "</tr>"
            )
        if premium_rows:
            st.markdown(
                """
                <table class="lotoia-sim-table">
                    <thead>
                        <tr>
                            <th>jogo</th>
                            <th>resultado</th>
                            <th>hits</th>
                            <th>premiado</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                + "".join(rows_html)
                + """
                    </tbody>
                </table>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("Nenhum jogo premiado com 11 pontos ou mais nesta simulação.")

    st.markdown("#### Cobertura estrutural")

    check_result = st.session_state.get("institutional_check_result")
    if isinstance(check_result, dict) and check_result.get("warning"):
        st.warning(check_result["warning"])
    if isinstance(check_result, dict) and check_result.get("results"):
        st.markdown("#### Confer?ncia")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "jogo": row["game_index"],
                        "dezenas": " ".join(f"{number:02d}" for number in row["numbers"]),
                        "hits": row["hits"],
                        "premiado": row["prize_status"],
                    }
                    for row in check_result["results"]
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )
        check_summary_cols = st.columns(4)
        check_summary_cols[0].metric("concurso", check_result.get("contest_number", "-"))
        check_summary_cols[1].metric("best_hits", check_result.get("best_hits", "-"))
        check_summary_cols[2].metric("prizes", check_result.get("prize_count", "-"))
        check_summary_cols[3].metric("total_hits", check_result.get("total_hits", "-"))
    elif isinstance(check_result, dict) and check_result.get("status") == "waiting_contest":
        st.info("A confer?ncia est? pronta, mas ainda falta o concurso oficial em imported_contests.")
def _render_analytical_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    st.subheader("Hist?rico Anal?tico")
    st.write("Visao acumulativa de desempenho dos jogos persistidos no PostgreSQL Institucional.")

    generation_history = _load_generation_history(limit=None)
    historical_rows = _load_accumulated_analytical_rows()
    if not generation_history or not historical_rows:
        st.info("Ainda nao ha geracoes persistidas para reconstruir o historico analitico.")
        return

    games_df = pd.DataFrame(historical_rows)
    if games_df.empty:
        st.info("Ainda nao ha jogos persistidos para reconstruir o historico analitico.")
        return

    games_df["data/hora_dt"] = pd.to_datetime(games_df["data/hora"], errors="coerce")
    games_df["acertos_num"] = pd.to_numeric(games_df["acertos"], errors="coerce")
    games_df["score_num"] = pd.to_numeric(games_df["score"], errors="coerce").fillna(0.0)

    filter_row_1 = st.columns([1.2, 1.2, 1.2, 1.2, 1.0])
    generation_options = sorted(int(value) for value in games_df["generation_event_id"].dropna().unique().tolist())
    strategy_options = sorted(str(value) for value in games_df["estratégia"].dropna().astype(str).unique().tolist())
    status_options = sorted(str(value) for value in games_df["status de conferência"].dropna().astype(str).unique().tolist())
    contest_options = sorted(
        int(value)
        for value in games_df["concurso conferido"].dropna().astype(int).unique().tolist()
        if int(value) > 0
    )

    selected_generation_ids = filter_row_1[0].multiselect("filtrar por geração", generation_options, default=generation_options)
    selected_strategies = filter_row_1[1].multiselect("filtrar por estratégia", strategy_options, default=strategy_options)
    selected_statuses = filter_row_1[2].multiselect("filtrar por status de conferência", status_options, default=status_options)
    selected_contests = filter_row_1[3].multiselect("filtrar por concurso", contest_options, default=contest_options)
    order_by = filter_row_1[4].selectbox("ordenar por", ["score", "data", "acertos"], index=0)

    date_values = games_df["data/hora_dt"].dropna()
    if not date_values.empty:
        min_date = date_values.min().date()
        max_date = date_values.max().date()
        date_range = st.date_input("filtrar por data", value=(min_date, max_date))
    else:
        date_range = ()

    filtered_df = games_df.copy()
    if selected_generation_ids:
        filtered_df = filtered_df[filtered_df["generation_event_id"].isin(selected_generation_ids)]
    if selected_strategies:
        filtered_df = filtered_df[filtered_df["estratégia"].isin(selected_strategies)]
    if selected_statuses:
        filtered_df = filtered_df[filtered_df["status de conferência"].isin(selected_statuses)]
    if selected_contests:
        filtered_df = filtered_df[
            filtered_df["concurso conferido"].fillna(0).astype(int).isin(selected_contests)
        ]
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        filtered_df = filtered_df[
            filtered_df["data/hora_dt"].dt.date.between(start_date, end_date)
        ]

    if order_by == "score":
        filtered_df = filtered_df.sort_values(
            by=["score_num", "data/hora_dt", "generation_event_id", "jogo n°"],
            ascending=[False, False, False, True],
        )
    elif order_by == "acertos":
        filtered_df = filtered_df.sort_values(
            by=["acertos_num", "score_num", "data/hora_dt", "generation_event_id", "jogo n°"],
            ascending=[False, False, False, False, True],
            na_position="last",
        )
    else:
        filtered_df = filtered_df.sort_values(
            by=["data/hora_dt", "generation_event_id", "jogo n°"],
            ascending=[False, False, True],
        )

    display_games = filtered_df.copy()
    display_games["concurso conferido"] = display_games["concurso conferido"].apply(
        lambda value: f"{int(value)}" if pd.notna(value) and int(value) > 0 else "—"
    )
    display_games["acertos"] = display_games["acertos"].apply(
        lambda value: f"{int(value)}" if pd.notna(value) and int(value) >= 0 else "—"
    )
    display_games["score"] = display_games["score"].apply(lambda value: f"{float(value):.4f}")
    display_games["data/hora"] = display_games["data/hora"].fillna("—")
    display_games = display_games[
        [
            "geração",
            "generation_event_id",
            "data/hora",
            "jogo n°",
            "dezenas",
            "estratégia",
            "score",
            "origem/modelo",
            "status de conferência",
            "concurso conferido",
            "acertos",
            "premiação",
            "observações",
        ]
    ]

    top_df = filtered_df.sort_values(
        by=["score_num", "acertos_num", "data/hora_dt", "generation_event_id", "jogo n°"],
        ascending=[False, False, False, False, True],
        na_position="last",
    ).copy()
    if not top_df.empty:
        top_df.insert(0, "rank", range(1, len(top_df) + 1))
    top_df["concurso conferido"] = top_df["concurso conferido"].apply(
        lambda value: f"{int(value)}" if pd.notna(value) and int(value) > 0 else "—"
    )
    top_df["acertos"] = top_df["acertos"].apply(
        lambda value: f"{int(value)}" if pd.notna(value) and int(value) >= 0 else "—"
    )
    top_df["score"] = top_df["score"].apply(lambda value: f"{float(value):.4f}")
    top_df["data/hora"] = top_df["data/hora"].fillna("—")
    top_df = top_df[
        [
            "rank",
            "geração",
            "generation_event_id",
            "data/hora",
            "jogo n°",
            "dezenas",
            "estratégia",
            "score",
            "origem/modelo",
            "status de conferência",
            "concurso conferido",
            "acertos",
            "premiação",
            "observações",
        ]
    ]

    diag_cols = st.columns(6)
    diag_cols[0].metric("total_generation_events_carregados", len(generation_history))
    diag_cols[1].metric("total_jogos_historicos_carregados", len(games_df))
    diag_cols[2].metric("total_linhas_exibidas_jogos_completos_historicos", len(display_games))
    diag_cols[3].metric("total_linhas_exibidas_top_jogos_historicos", len(top_df))
    diag_cols[4].metric("generation_event_id_mais_antigo", min(generation_options) if generation_options else "-")
    diag_cols[5].metric("generation_event_id_mais_recente", max(generation_options) if generation_options else "-")

    st.markdown("##### Jogos completos historicos")
    if not display_games.empty:
        st.dataframe(display_games, hide_index=True, use_container_width=True, height=560)
    else:
        st.info("Nenhum jogo historico encontrado com os filtros atuais.")

    st.markdown("##### Top jogos historicos")
    if not top_df.empty:
        st.dataframe(top_df, hide_index=True, use_container_width=True, height=520)
    else:
        st.info("Nenhum top jogo historico encontrado com os filtros atuais.")

    with st.expander("Linha do tempo secundaria", expanded=False):
        timeline = _load_analytical_timeline(limit=30)
        if timeline:
            st.dataframe(pd.DataFrame(timeline), hide_index=True, use_container_width=True)
        else:
            st.info("Ainda nao ha eventos suficientes para montar a timeline analitica.")

def _render_hb_geometry_page(state: dict[str, Any]) -> None:
    st.subheader("HB Geometry")
    st.write("Auditoria incremental isolada do motor oficial.")
    job = state["job"]
    progress = state["progress"]
    summary = state["summary"]
    csv_frame = state["csv_frame"]
    button_cols = st.columns(3)
    if button_cols[0].button("Iniciar Auditoria", type="primary", use_container_width=True, disabled=bool(job.get("running"))):
        st.session_state["institutional_last_ui_event"] = "hb_geometry:iniciar"
        _start_hb_geometry_job(resume=bool(progress) and not bool(progress.get("completed", False)))
        st.rerun()
    if button_cols[1].button("Continuar Auditoria", use_container_width=True, disabled=bool(job.get("running")) or not bool(progress) or bool(progress.get("completed", False))):
        st.session_state["institutional_last_ui_event"] = "hb_geometry:continuar"
        _start_hb_geometry_job(resume=True)
        st.rerun()
    if button_cols[2].button("Resetar Auditoria", use_container_width=True, disabled=bool(job.get("running"))):
        st.session_state["institutional_last_ui_event"] = "hb_geometry:resetar"
        _reset_hb_geometry_job()
        st.rerun()
    status_cols = st.columns(4)
    status_cols[0].metric("contests_processed", int(job.get("contests_processed", 0)))
    status_cols[1].metric("processed_batches", int(job.get("processed_batches", 0)))
    status_cols[2].metric("completed", "sim" if bool(job.get("completed")) else "não")
    status_cols[3].metric("elapsed_time", f"{float(job.get('elapsed_time', 0.0)):.1f}s")
    st.caption(f"current_scenario: {job.get('current_scenario', '-')}")
    if job.get("error"):
        st.error(f"HB Geometry error: {job['error']}")
    if progress:
        st.info(
            " | ".join(
                [
                    f"checkpoint={HB_GEOMETRY_PROGRESS_FILE.name}",
                    f"resume={'true' if bool(progress) and not bool(progress.get('completed', False)) else 'false'}",
                    f"last_contest={progress.get('last_contest', '-')}",
                    f"current_batch={progress.get('current_batch', '-')}",
                ]
            )
        )
    if summary:
        st.dataframe(
            pd.DataFrame(
                [
                    {"Métrica": "avg_hits", "Valor": round(float(summary.get("hb_baseline", {}).get("average_hits", 0.0)), 4)},
                    {"Métrica": "11+", "Valor": int(summary.get("hb_baseline", {}).get("hits_11_plus", 0))},
                    {"Métrica": "12+", "Valor": int(summary.get("hb_baseline", {}).get("hits_12_plus", 0))},
                    {"Métrica": "overlap", "Valor": round(float(summary.get("hb_baseline", {}).get("average_overlap", 0.0)), 4)},
                    {"Métrica": "entropy", "Valor": round(float(summary.get("hb_baseline", {}).get("entropy", 0.0)), 4)},
                    {
                        "Métrica": "dominant_numbers",
                        "Valor": ", ".join(
                            f"{item['number']}:{item['frequency']}" for item in summary.get("hb_baseline", {}).get("dominant_numbers", [])[:5]
                        )
                        or "-",
                    },
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )
    if not csv_frame.empty:
        with st.expander("CSV consolidado", expanded=False):
            st.dataframe(csv_frame.tail(20), hide_index=True, use_container_width=True)
    st.caption(f"json: {HB_GEOMETRY_JSON_FILE} | csv: {HB_GEOMETRY_CSV_FILE} | progress: {HB_GEOMETRY_PROGRESS_FILE}")


def main() -> None:
    st.set_page_config(page_title="LotoIA Institucional", page_icon="🧭", layout="wide")
    _ensure_institutional_schema()
    snapshot = _database_snapshot()
    _align_institutional_runtime_with_database(snapshot)
    page = _render_sidebar(
        st.session_state.get("institutional_page_id", "generation"),
        snapshot,
    )
    st.session_state["institutional_page_id"] = page
    st.success(BUILD_MARKER)
    st.caption("Painel mínimo, isolado e pronto para o runtime novo.")
    if page == "audit":
        _render_runtime_audit_page(snapshot)
    elif page == "generation":
        _render_generation_page(snapshot)
    elif page == "conference":
        _render_conference_page(snapshot)
    elif page == "simulation":
        _render_simulation_page(snapshot)
    elif page == "history_analytical":
        _render_analytical_page(snapshot)
    elif page == "history_institutional":
        _render_history_institutional_page(snapshot)
    elif page == "clear_histories":
        _render_clear_histories_page(snapshot)
    elif page == "delete_history":
        _render_delete_history_page(snapshot)
    elif page == "comparative_history":
        _render_comparative_history_page(snapshot)
    elif page == "strategies_analysis":
        _render_strategies_page("Análises Estratégicas", snapshot)
    elif page == "strategies_test":
        _render_strategies_page("Testar Estratégias", snapshot)
    elif page == "strategies_simulation":
        _render_strategies_page("Simular Estratégias", snapshot)
    elif page == "hb_metrics":
        _render_metrics_hb_page(snapshot)
    elif page == "structural_coverage":
        _render_cobertura_estrutural_page(snapshot)
    elif page == "institutional_replay":
        _render_replay_institutional_page(snapshot)
    elif page == "summary_benchmark":
        _render_benchmark_resumido_page(snapshot)
    elif page == "operational_statistics":
        _render_estatisticas_operacionais_page(snapshot)
    else:
        _render_hb_geometry_page(_hb_geometry_state())


if __name__ == "__main__":
    main()
