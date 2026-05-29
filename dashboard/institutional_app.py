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
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd
import streamlit as st
from sqlalchemy import inspect, text

from lotoia.database.adapter import InstitutionalDatabaseAdapter
from lotoia.database.contest_repository import ContestRepository
from lotoia.database.database import DEFAULT_DATABASE_PATH, GeneratedGame, GenerationEvent, ImportedContest, ReconciliationGame, ReconciliationRun, create_database, get_engine, get_session
from lotoia.data.history_export import export_historical_csv
from lotoia.data.loader import load_draws_csv
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
        st.session_state["institutional_page"] = target_page
        st.rerun()


@st.cache_resource(show_spinner=False)
def _get_engine_cached():
    return get_engine(DB_PATH)


def _database_snapshot() -> dict[str, Any]:
    adapter = InstitutionalDatabaseAdapter(DB_PATH)
    engine = _get_engine_cached()
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    preferred_tables = [
        "generation_events",
        "generated_games",
        "reconciliation_runs",
        "reconciliation_games",
        "reconciliation_events",
        "imported_contests",
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
        "expansion_events": "created_at",
        "operational_logs": "created_at",
    }
    counts: dict[str, int] = {}
    latest: dict[str, Any] = {}
    with engine.begin() as connection:
        for table in preferred_tables:
            if table not in table_names:
                counts[table] = 0
                latest[table] = "-"
                continue
            try:
                counts[table] = int(connection.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar() or 0)
            except Exception:
                counts[table] = 0
            latest_field = latest_fields.get(table, "created_at")
            if latest_field in {"created_at", "contest_number"}:
                try:
                    value = connection.execute(text(f'SELECT MAX("{latest_field}") FROM "{table}"')).scalar()
                    latest[table] = value if value is not None else "-"
                except Exception:
                    latest[table] = "-"
            else:
                latest[table] = "-"
    return {
        "backend": adapter.backend,
        "engine_url": str(engine.url),
        "database_url": adapter.database_url,
        "database_source": adapter.database_source,
        "counts": counts,
        "latest": latest,
        "tables": sorted(table_names),
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


def _select_subset_from_candidate(
    numbers: list[int],
    *,
    target_size: int,
    frequency_map: dict[int, int],
    latest_numbers: set[int],
    odd_min: int,
    odd_max: int,
    even_min: int,
    even_max: int,
    sequence_max: int,
    coverage_min: float,
    entropy_min: float,
    repeat_limit: int,
) -> list[int] | None:
    unique_numbers = sorted({int(number) for number in numbers})
    if not unique_numbers or target_size < 1:
        return None
    if target_size > len(unique_numbers):
        target_size = len(unique_numbers)

    scoring = sorted(
        unique_numbers,
        key=lambda number: (
            -int(frequency_map.get(int(number), 0)),
            int(number in latest_numbers),
            int(number),
        ),
    )

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
        return None

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
        return None

    odd_count = sum(1 for number in selected if number % 2 != 0)
    even_count = len(selected) - odd_count
    if not (odd_min <= odd_count <= odd_max and even_min <= even_count <= even_max):
        return None
    if _sequence_metrics(selected)["largest_sequence"] > sequence_max:
        return None
    if len(set(selected).intersection(latest_numbers)) > repeat_limit:
        return None
    if _coverage_metrics(selected)["coverage_score"] < coverage_min:
        return None
    if _entropy_score(selected) < entropy_min:
        return None
    return selected


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
    started = time.monotonic()
    seed = int(time.time()) % 1_000_000
    latest_contest = _load_latest_contest_summary()
    target_contest = int(latest_contest["contest_number"]) if latest_contest else None
    history_frequency = _history_number_frequency()
    latest_numbers = set(int(number) for number in (latest_contest or {}).get("dezenas", []))
    candidate_count = max(total_games * 5, 50 if use_top50 else 30)
    ranked_candidates = generate_ranked_games(total_games=candidate_count, seed=seed, ml_enabled=False, pool_size=max(candidate_count, 30))
    games: list[dict[str, Any]] = []
    used_signatures: set[tuple[int, ...]] = set()
    repeat_limit = max(0, min(repeat_limit, dezenas_per_game))
    for candidate in ranked_candidates:
        selected_numbers = _select_subset_from_candidate(
            list(candidate.get("numbers", [])),
            target_size=dezenas_per_game,
            frequency_map=history_frequency,
            latest_numbers=latest_numbers,
            odd_min=odd_min,
            odd_max=odd_max,
            even_min=even_min,
            even_max=even_max,
            sequence_max=sequence_max,
            coverage_min=coverage_min,
            entropy_min=entropy_min,
            repeat_limit=repeat_limit,
        )
        if not selected_numbers:
            continue
        signature = tuple(selected_numbers)
        if signature in used_signatures:
            continue
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
        games.append(
            {
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
        )
        used_signatures.add(signature)
        if len(games) >= total_games:
            break

    if not games:
        games = [
            {
                "numbers": list(candidate.get("numbers", []))[:dezenas_per_game],
                "odd": sum(1 for number in candidate.get("numbers", [])[:dezenas_per_game] if int(number) % 2 != 0),
                "even": sum(1 for number in candidate.get("numbers", [])[:dezenas_per_game] if int(number) % 2 == 0),
                "sum": sum(int(number) for number in candidate.get("numbers", [])[:dezenas_per_game]),
                "frame": 0,
                "center": 0,
                "quadra_score": dict(candidate.get("quadra_score", {})),
                "final_score": dict(candidate.get("final_score", {})),
                "historical_intelligence": dict(candidate.get("historical_intelligence", {})),
                "profile_type": str(candidate.get("profile_type", "")),
                "profile_score": float(candidate.get("profile_score", 0.0) or 0.0),
                "ml_enabled": False,
                "structural_metrics": {},
            }
            for candidate in ranked_candidates[:total_games]
        ]
    generation_snapshot = _persist_generation_snapshot(
        games=games,
        seed=seed,
        target_contest=target_contest,
        generation_context={
            "dezenas_per_game": dezenas_per_game,
            "total_games": total_games,
            "use_top50": use_top50,
            "odd_min": odd_min,
            "odd_max": odd_max,
            "even_min": even_min,
            "even_max": even_max,
            "sequence_max": sequence_max,
            "coverage_min": coverage_min,
            "entropy_min": entropy_min,
            "repeat_limit": repeat_limit,
        },
    )
    st.session_state["institutional_generation"] = {
        "seed": seed,
        "games": games,
        "total_games": total_games,
        "dezenas_per_game": dezenas_per_game,
        "use_top50": use_top50,
        "generation_event_id": generation_snapshot["generation_event_id"],
        "created_at": datetime.now(UTC).isoformat(),
        "runtime_status": "generated",
        "elapsed_time": round(time.monotonic() - started, 3),
    }
    st.session_state["institutional_generation_result"] = {
        "generation_event_id": generation_snapshot["generation_event_id"],
        "seed": seed,
        "jogos": games,
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
            groups.append(
                {
                    "generation_event_id": int(event.id or 0),
                    "created_at": event.created_at.isoformat() if getattr(event, "created_at", None) else "",
                    "seed": int(getattr(event, "seed", 0) or 0),
                    "strategy": str(getattr(event, "strategy", "") or ""),
                    "total_games": len(games),
                    "target_contest": max((int(game.get("target_contest") or 0) for game in rows if getattr(game, "target_contest", None) is not None), default=None),
                    "games": games,
                    "structural_summary": _summarize_games_structurally([game["numbers"] for game in games]),
                }
            )
    return groups


def _run_institutional_conference(contest_number: int | None = None) -> None:
    latest_contest = _load_imported_contest(contest_number) or _get_latest_contest()
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
    for group in grouped_generations:
        comparison = _compare_games_against_contest(
            generation_event_id=int(group.get("generation_event_id") or 0),
            games=list(group.get("games") or []),
            contest=latest_contest,
        )
        hit_counts = Counter(int(row.get("hits", 0) or 0) for row in comparison.get("results", []))
        generation_results.append(
            {
                "generation_event_id": int(group.get("generation_event_id") or 0),
                "created_at": group.get("created_at", ""),
                "seed": int(group.get("seed") or 0),
                "total_games": int(group.get("total_games") or 0),
                "target_contest": group.get("target_contest"),
                "best_hits": int(comparison.get("best_hits", 0) or 0),
                "total_hits": int(comparison.get("total_hits", 0) or 0),
                "prize_count": int(comparison.get("prize_count", 0) or 0),
                "hit_distribution": dict(sorted(hit_counts.items(), key=lambda item: (-item[0], item[1]))),
                "results": list(comparison.get("results", [])),
                "games": list(group.get("games") or []),
                "contest_number": int(comparison.get("contest_number", latest_contest.get("contest_number", 0)) or 0),
                "contest_date": str(comparison.get("contest_date", latest_contest.get("data", "")) or ""),
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


def _load_generation_history(limit: int = 12) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    with get_session(DB_PATH) as session:
        events = (
            session.query(GenerationEvent)
            .order_by(GenerationEvent.created_at.desc(), GenerationEvent.id.desc())
            .limit(limit)
            .all()
        )
        for event in events:
            games_rows = (
                session.query(GeneratedGame)
                .filter(GeneratedGame.generation_event_id == event.id)
                .order_by(GeneratedGame.game_index.asc())
                .all()
            )
            games: list[dict[str, Any]] = []
            scores: list[float] = []
            entropies: list[float] = []
            coverages: list[float] = []
            overlaps: list[float] = []
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
                games.append(
                    {
                        "game_index": int(row.game_index or 0),
                        "numbers": numbers,
                        "profile_type": str(row.profile_type or ""),
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
                    }
                )
                scores.append(score_value)
                entropies.append(entropy_value)
                coverages.append(coverage_value)
                if getattr(row, "target_contest", None) is not None:
                    target_contests.append(int(row.target_contest))
            structural_summary = _summarize_games_structurally([game["numbers"] for game in games]) if games else {}
            top_games = sorted(games, key=lambda item: (-float(item["score"]), item["game_index"]))[:5]
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
                    "games": games,
                    "top_games": top_games,
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
                "details": f"jogos={entry['total_games']} | seed={entry['seed']} | target_contest={entry.get('target_contest', '-') or '-'}",
            }
        )
    for entry in _load_reconciliation_history(limit=limit):
        items.append(
            {
                "kind": "reconciliation",
                "created_at": entry["created_at"],
                "title": f"Reconciliação #{entry['id']}",
                "details": f"contest_id={entry['contest_id']} | best_hits={entry['best_hits']} | prizes={entry['prize_count']} | total_hits={entry['total_hits']}",
            }
        )
    sync_summary = _load_official_sync_diagnostics()
    if sync_summary:
        items.append(
            {
                "kind": "sync",
                "created_at": str(sync_summary.get("sync_timestamp", "") or ""),
                "title": "Sincronização Caixa",
                "details": f"status={sync_summary.get('sync_status', '-')} | contest={sync_summary.get('imported_contest', '-')} | http={sync_summary.get('http_status', '-')}",
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
    for entry in _load_operational_logs_history(limit=limit):
        items.append(
            {
                "kind": "log",
                "created_at": entry["created_at"],
                "title": f"Log operacional #{entry['id']}",
                "details": f"{entry['event_type']} | status={entry['status']} | duration_ms={entry['duration_ms']:.1f}",
            }
        )
    return sorted(
        items,
        key=lambda item: item.get("created_at", ""),
        reverse=True,
    )[:limit]


def _clear_institutional_history_state() -> None:
    for key in (
        "institutional_generation",
        "institutional_generation_result",
        "institutional_check",
        "institutional_check_result",
        "institutional_simulation",
        "institutional_simulation_result",
        "institutional_last_official_sync_summary",
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
        "institutional_simulation",
        "institutional_simulation_result",
        "institutional_simulation_error",
        "institutional_check_result",
        "institutional_check",
    ):
        st.session_state.pop(key, None)


def _purge_institutional_history_tables() -> dict[str, Any]:
    tables = [
        "reconciliation_games",
        "reconciliation_runs",
        "reconciliation_events",
        "operational_logs",
        "reset_events",
    ]
    deleted: dict[str, int] = {}
    with get_session(DB_PATH) as session:
        for table in tables:
            try:
                deleted[table] = int(session.execute(text(f'DELETE FROM "{table}"')).rowcount or 0)
            except Exception:
                deleted[table] = 0
        session.commit()
    try:
        st.cache_data.clear()
    except Exception:
        pass
    _clear_institutional_history_state()
    return {"status": "ok", "deleted": deleted}


def _render_history_institutional_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    st.subheader("Hist?rico Institucional")
    st.write("Vis?o consolidada do runtime institucional limpo.")
    source_map = _institutional_source_map(snapshot)
    st.markdown("##### Fontes institucionais")
    st.dataframe(pd.DataFrame(source_map), hide_index=True, use_container_width=True)
    latest_sync = st.session_state.get("institutional_last_official_sync_summary", {})
    latest_reconciliation = _load_latest_reconciliation_summary() or {}
    latest_contest = _load_latest_contest_summary() or {}
    top_cols = st.columns(5)
    top_cols[0].metric("total_execucoes", int(snapshot["counts"].get("generation_events", 0)))
    top_cols[1].metric("total_jogos", int(snapshot["counts"].get("generated_games", 0)))
    top_cols[2].metric("ultimo_concurso", latest_contest.get("contest_number", "-"))
    top_cols[3].metric("ultimo_sync", latest_sync.get("latest_contest", latest_contest.get("contest_number", "-")))
    top_cols[4].metric("status_postgresql", snapshot["backend"])
    sync_cols = st.columns(4)
    sync_cols[0].metric("imported_contests", int(snapshot["counts"].get("imported_contests", 0)))
    sync_cols[1].metric("reconciliation_runs", int(snapshot["counts"].get("reconciliation_runs", 0)))
    sync_cols[2].metric("operational_logs", int(snapshot["counts"].get("operational_logs", 0)))
    sync_cols[3].metric("database_source", snapshot["database_source"])
    if latest_sync:
        st.caption(
            " | ".join(
                [
                    f"latest_contest={latest_sync.get('latest_contest', '-')}",
                    f"synced_contests={len(latest_sync.get('synced_contests', []) or [])}",
                    f"commit_state={latest_sync.get('commit_state', '-')}",
                    f"fallback={'sim' if latest_sync.get('fallback_used') else 'n?o'}",
                ]
            )
        )
    st.markdown("##### ?ltima reconcilia??o persistida")
    if latest_reconciliation:
        st.caption(
            f"reconciliation_id={latest_reconciliation.get('id', '-')}"
            f" | generation_event_id={latest_reconciliation.get('generation_event_id', '-')}"
            f" | contest_id={latest_reconciliation.get('contest_id', '-')}"
            f" | status={latest_reconciliation.get('status', '-')}"
        )
        recon_cols = st.columns(5)
        recon_cols[0].metric("Concurso", latest_reconciliation.get("contest_id", "-"))
        recon_cols[1].metric("Total jogos conferidos", latest_reconciliation.get("games_count", 0))
        recon_cols[2].metric("Melhor acerto", latest_reconciliation.get("best_hits", "-"))
        recon_cols[3].metric("Premiações", latest_reconciliation.get("prize_count", "-"))
        recon_cols[4].metric("Total hits", latest_reconciliation.get("total_hits", "-"))
        distribution = latest_reconciliation.get("hit_distribution") or {}
        if distribution:
            st.markdown("###### Distribui??o de acertos")
            st.dataframe(
                pd.DataFrame(
                    [
                        {"acertos": hits, "quantidade": count}
                        for hits, count in sorted(distribution.items(), key=lambda item: (-int(item[0]), int(item[1])))
                    ]
                ),
                hide_index=True,
                use_container_width=True,
            )
    else:
        st.info("Ainda n?o h? reconcilia??o persistida nesta inst?ncia.")
    st.divider()
    st.markdown("##### Timeline Institucional")
    timeline = _load_institutional_timeline(limit=30)
    if timeline:
        st.dataframe(pd.DataFrame(timeline), hide_index=True, use_container_width=True)
    else:
        st.info("Ainda n?o h? eventos suficientes para montar a timeline institucional.")
    st.divider()
    st.markdown("##### Tabelas Institucionais")
    table_rows = []
    for table, count in snapshot["counts"].items():
        table_rows.append(
            {
                "tabela": table,
                "contagem": int(count),
                "ultima_persistencia": snapshot["latest"].get(table, "-"),
            }
        )
    st.dataframe(pd.DataFrame(table_rows), hide_index=True, use_container_width=True)


def _render_clear_histories_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    st.subheader("Limpar Históricos")
    st.write("Limpa apenas os estados visuais e operacionais desta sessão.")
    state_keys = sorted([key for key in st.session_state.keys() if str(key).startswith("institutional_")])
    st.caption(f"Chaves institucionais ativas: {len(state_keys)}")
    st.code("\n".join(state_keys) if state_keys else "-", language="text")
    if st.button("Limpar históricos desta sessão", type="primary"):
        _clear_institutional_history_state()
        st.success("Históricos visuais limpos desta sessão.")
        st.rerun()


def _render_delete_history_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    st.subheader("Apagar Histórico")
    st.write("Remove os registros operacionais institucionais persistidos no banco atual.")
    st.warning("Esta ação remove gerações, reconciliações e logs institucionais do runtime. Não afeta imported_contests.")
    st.caption("Ação irreversível no runtime atual. Preserva imported_contests.")
    if st.button("Apagar histórico persistido", type="primary"):
        result = _purge_institutional_history_tables()
        st.success("Histórico institucional apagado.")
        st.json(result)
        st.rerun()


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
    generation_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started_at = time.monotonic()
    context_payload = {
        "source": "institutional_app",
        "target_contest": target_contest,
        "build_marker": BUILD_MARKER,
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
            session.add(
                GeneratedGame(
                    generation_event_id=generation_event_id,
                    lead_id=None,
                    target_contest=target_contest,
                    origin="institutional",
                    generation_mode="hb_baseline",
                    game_index=index,
                    numbers=list(game.get("numbers", [])),
                    profile_type=str(game.get("profile_type", "")),
                    final_score=dict(game.get("final_score", {})) if isinstance(game.get("final_score"), dict) else {},
                    quadra_score=dict(game.get("quadra_score", {})) if isinstance(game.get("quadra_score"), dict) else {},
                    context_json={
                        **context_payload,
                    },
                )
            )
        event.execution_time_ms = round((time.monotonic() - started_at) * 1000, 2)
        session.commit()
        return {
            "generation_event_id": generation_event_id,
            "seed": seed,
            "games_count": len(games),
            "target_contest": target_contest,
        }


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
    pages = [
        "Auditoria Runtime",
        "Gerar Jogos",
        "Conferir Resultados",
        "Simular Resultados",
        "Histórico Analítico",
        "Histórico Institucional",
        "Limpar Históricos",
        "Apagar Histórico",
        "Comparativos histórico",
        "Análises Estratégicas",
        "Testar Estratégias",
        "Simular Estratégias",
        "Métricas HB",
        "Cobertura estrutural",
        "Replay institucional",
        "Benchmark resumido",
        "Estatísticas operacionais",
        "HB Geometry",
    ]
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
    choice = st.session_state.get("institutional_page", page)
    if choice not in pages:
        choice = page if page in pages else "Gerar Jogos"
    st.sidebar.divider()
    st.sidebar.caption("DATABASE_URL conectada")
    return choice


def _ensure_institutional_schema() -> None:
    create_database(DB_PATH)


def _render_generation_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    st.subheader("Gerar Jogos")
    st.write("Fluxo principal limpo, sem legado visual ou CRM.")
    status_cols = st.columns([1, 1, 1, 1, 1])
    status_cols[0].metric("build", BUILD_MARKER)
    status_cols[1].metric("backend", snapshot["backend"])
    status_cols[2].metric("imported_contests", int(snapshot["counts"].get("imported_contests", 0)))
    status_cols[3].metric("generated_games", int(snapshot["counts"].get("generated_games", 0)))
    status_cols[4].metric("reconciliation_runs", int(snapshot["counts"].get("reconciliation_runs", 0)))

    contest_summary = _get_latest_contest() or _load_latest_contest_summary()
    top_cols = st.columns([1.1, 1.3, 1.6])
    if contest_summary:
        top_cols[0].metric("Último concurso", int(contest_summary["contest_number"]))
        top_cols[1].caption(f"Fonte: {contest_summary['source']}")
        top_cols[2].caption(
            f"dezenas: {' '.join(f'{number:02d}' for number in contest_summary.get('dezenas', [])) or '-'}"
        )
    else:
        top_cols[0].caption("Último concurso: -")
        top_cols[1].caption("Fonte: banco vazio")

    controls_cols = st.columns([1.0, 1.0, 1.0, 1.0])
    total_games = int(
        controls_cols[0].number_input(
            "Quantidade de jogos",
            min_value=1,
            max_value=100,
            value=int(st.session_state.get("institutional_total_games", 15) or 15),
            step=1,
            key="institutional_total_games",
        )
    )
    dezenas_per_game = int(
        controls_cols[1].number_input(
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
        controls_cols[2].checkbox(
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
            value=int(st.session_state.get("institutional_repeat_limit", 8) or 8),
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

    button_cols = st.columns([0.28, 1.72])
    if button_cols[0].button("LotoIA", type="primary"):
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

    generation_state = st.session_state.get("institutional_generation") or {}
    generation_result = st.session_state.get("institutional_generation_result") or {}
    if generation_result:
        st.success(
            f"Geração concluída. generation_event_id={generation_result.get('generation_event_id', '-')} | jogos={len(generation_result.get('jogos') or [])} | seed={generation_result.get('seed', '-')}"
        )
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
    st.subheader("Conferir Resultados")
    st.write("Compare os jogos gerados com o concurso selecionado no banco.")
    status_cols = st.columns([1, 1, 1, 1])
    status_cols[0].metric("imported_contests", int(snapshot["counts"].get("imported_contests", 0)))
    status_cols[1].metric("generated_games", int(snapshot["counts"].get("generated_games", 0)))
    status_cols[2].metric("reconciliation_runs", int(snapshot["counts"].get("reconciliation_runs", 0)))

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
    top_cols[1].caption("Cada jogo mant?m 15 dezenas da Lotof?cil.")
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
    st.write("Snapshot institucional do banco atual via DATABASE_URL.")
    st.markdown("##### Fontes institucionais")
    st.dataframe(pd.DataFrame(_institutional_source_map(snapshot)), hide_index=True, use_container_width=True)
    diag_cols = st.columns(4)
    diag_cols[0].metric("backend", snapshot["backend"])
    diag_cols[1].metric("database_source", snapshot["database_source"])
    diag_cols[2].metric("imported_contests", int(snapshot["counts"].get("imported_contests", 0)))
    diag_cols[3].metric("generation_events", int(snapshot["counts"].get("generation_events", 0)))
    st.caption(f"database_url: {_mask_database_url(snapshot['database_url'])}")
    last_sync_summary = st.session_state.get("institutional_last_official_sync_summary", {})
    if last_sync_summary:
        sync_cols = st.columns(4)
        sync_cols[0].metric("latest_contest", last_sync_summary.get("latest_contest", "-"))
        sync_cols[1].metric("synced_contests", len(last_sync_summary.get("synced_contests", []) or []))
        sync_cols[2].metric("commit_state", last_sync_summary.get("commit_state", "-"))
        sync_cols[3].metric("fallback", "sim" if last_sync_summary.get("fallback_used") else "n?o")

    generations = _load_generation_history(limit=12)
    if generations:
        st.markdown("##### Gera??es persistidas")
        generation_options = {
            f"Gera??o #{item['generation_event_id']} | jogos={item['total_games']} | seed={item['seed']} | concurso={item.get('target_contest', '-') or '-'} | score_medio={item['avg_score']:.4f}": item
            for item in generations
        }
        selected_label = st.selectbox("Escolha uma gera??o", list(generation_options.keys()), index=0)
        selected_generation = generation_options[selected_label]
        selected_cols = st.columns(5)
        selected_cols[0].metric("timestamp", selected_generation.get("created_at", "-"))
        selected_cols[1].metric("seed", selected_generation.get("seed", "-"))
        selected_cols[2].metric("target_contest", selected_generation.get("target_contest", "-"))
        selected_cols[3].metric("total_games", selected_generation.get("total_games", 0))
        selected_cols[4].metric("perfil HB", selected_generation.get("strategy", "-") or "-")
        summary_cols = st.columns(4)
        summary_cols[0].metric("score m?dio", f"{selected_generation.get('avg_score', 0.0):.4f}")
        summary_cols[1].metric("entropia m?dia", f"{selected_generation.get('avg_entropy', 0.0):.4f}")
        summary_cols[2].metric("cobertura m?dia", f"{selected_generation.get('avg_coverage', 0.0):.4f}")
        summary_cols[3].metric("overlap m?dio", f"{selected_generation.get('average_overlap', 0.0):.4f}")
        if selected_generation.get("dominant_numbers"):
            st.caption(
                "dominantes: "
                + ", ".join(
                    f"{item.get('number', '-')}: {item.get('frequency', '-')}"
                    for item in selected_generation.get("dominant_numbers", [])[:8]
                )
            )
        st.markdown("###### Jogos completos da gera??o selecionada")
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
                        "seq_max": int(game.get("sequence_max", 0) or 0),
                        "frame": int(game.get("frame", 0) or 0),
                        "center": int(game.get("center", 0) or 0),
                    }
                    for game in selected_generation.get("games", [])
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )
        st.markdown("###### Top jogos da gera??o")
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
                    }
                    for game in selected_generation.get("top_games", [])
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("Ainda n?o h? gera??es persistidas para reconstru??o anal?tica.")
    st.divider()
    st.markdown("##### Timeline operacional")
    timeline = _load_institutional_timeline(limit=30)
    if timeline:
        st.dataframe(pd.DataFrame(timeline), hide_index=True, use_container_width=True)
    else:
        st.info("Ainda n?o h? eventos suficientes para montar a timeline institucional.")
    st.divider()
    st.markdown("##### Tabelas institucionais")
    table_rows = []
    for table, count in snapshot["counts"].items():
        table_rows.append(
            {
                "tabela": table,
                "contagem": int(count),
                "ultima_persistencia": snapshot["latest"].get(table, "-"),
            }
        )
    st.dataframe(pd.DataFrame(table_rows), hide_index=True, use_container_width=True)


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
    page = _render_sidebar(st.session_state.get("institutional_page", "Gerar Jogos"), snapshot)
    st.session_state["institutional_page"] = page
    st.success(BUILD_MARKER)
    st.caption("Painel mínimo, isolado e pronto para o runtime novo.")
    if page == "Auditoria Runtime":
        _render_runtime_audit_page(snapshot)
    elif page == "Gerar Jogos":
        _render_generation_page(snapshot)
    elif page == "Conferir Resultados":
        _render_conference_page(snapshot)
    elif page == "Simular Resultados":
        _render_simulation_page(snapshot)
    elif page == "Histórico Analítico":
        _render_analytical_page(snapshot)
    elif page == "Histórico Institucional":
        _render_history_institutional_page(snapshot)
    elif page == "Limpar Históricos":
        _render_clear_histories_page(snapshot)
    elif page == "Apagar Histórico":
        _render_delete_history_page(snapshot)
    elif page == "Comparativos histórico":
        _render_comparative_history_page(snapshot)
    elif page == "Análises Estratégicas":
        _render_strategies_page("Análises Estratégicas", snapshot)
    elif page == "Testar Estratégias":
        _render_strategies_page("Testar Estratégias", snapshot)
    elif page == "Simular Estratégias":
        _render_strategies_page("Simular Estratégias", snapshot)
    elif page == "Métricas HB":
        _render_metrics_hb_page(snapshot)
    elif page == "Cobertura estrutural":
        _render_cobertura_estrutural_page(snapshot)
    elif page == "Replay institucional":
        _render_replay_institutional_page(snapshot)
    elif page == "Benchmark resumido":
        _render_benchmark_resumido_page(snapshot)
    elif page == "Estatísticas operacionais":
        _render_estatisticas_operacionais_page(snapshot)
    else:
        _render_hb_geometry_page(_hb_geometry_state())


if __name__ == "__main__":
    main()
