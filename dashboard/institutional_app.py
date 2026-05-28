# -*- coding: utf-8 -*-
from __future__ import annotations

try:
    from . import _bootstrap  # type: ignore[import-not-found]  # noqa: F401
except ImportError:
    import _bootstrap  # type: ignore[no-redef]  # noqa: F401

import json
import os
import random
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy import inspect, text

from lotoia.database.adapter import InstitutionalDatabaseAdapter
from lotoia.database.database import DEFAULT_DATABASE_PATH, GeneratedGame, GenerationEvent, ImportedContest, ReconciliationGame, ReconciliationRun, create_database, get_engine, get_session
from lotoia.ingestion.result_sync_service import ResultSyncService
from lotoia.experiments.hb_geometry_audit import DEFAULT_HB_GEOMETRY_DIR, run_hb_geometry_audit
from lotoia.generator.engine import generate_ranked_games


BUILD_MARKER = "institutional-clean-runtime-v1"
APP_BUILD = BUILD_MARKER
PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
LOGO_PATH = PROJECT_ROOT / "assets" / "logo.png"
HB_GEOMETRY_DIR = Path(os.fspath(DEFAULT_HB_GEOMETRY_DIR))
HB_GEOMETRY_PROGRESS_FILE = HB_GEOMETRY_DIR / "hb_geometry_audit.progress.json"
HB_GEOMETRY_JSON_FILE = HB_GEOMETRY_DIR / "hb_geometry_audit.json"
HB_GEOMETRY_CSV_FILE = HB_GEOMETRY_DIR / "hb_geometry_audit.csv"
DB_PATH = DEFAULT_DATABASE_PATH

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
            width: 88% !important;
            max-width: 300px !important;
            display: block;
            margin: 0 auto 0.4rem auto;
        }
        .lotoia-sidebar-divider {
            border-top: 1px solid rgba(18, 52, 86, 0.14);
            margin: 0.6rem 0;
        }
        .lotoia-nav-hint {
            font-size: 0.70rem;
            letter-spacing: 0.07em;
            text-transform: uppercase;
            color: #7a8795;
            margin-bottom: 0.45rem;
        }
        .lotoia-sidebar-title {
            color: #123456;
            font-size: 1.02rem;
            font-weight: 800;
            letter-spacing: 0.01em;
            margin: 0.1rem 0 0.15rem 0;
        }
        .lotoia-section-title {
            font-size: 1.7rem;
            font-weight: 800;
            color: #123456;
            margin-bottom: 0.2rem;
            letter-spacing: 0.01em;
        }
        .lotoia-section-subtitle {
            font-size: 0.92rem;
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
            min-height: 34px;
            padding-top: 0.35rem;
            padding-bottom: 0.35rem;
            border-radius: 10px;
            font-size: 0.93rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar_logo() -> None:
    try:
        if LOGO_PATH.exists():
            st.sidebar.image(str(LOGO_PATH), use_container_width=True)
    except Exception:
        st.sidebar.markdown(
            '<div style="font-weight:900;color:#123456;text-align:center;font-size:1.1rem;letter-spacing:0.12em;margin-bottom:0.4rem;">LotoIA</div>',
            unsafe_allow_html=True,
        )


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
        "database_url": adapter.database_url,
        "database_source": adapter.database_source,
        "counts": counts,
        "latest": latest,
        "tables": sorted(table_names),
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
        dezenas = [int(number) for number in str(row.dezenas or "").replace(",", " ").split() if str(number).isdigit()]
        return {
            "contest_number": int(row.contest_number),
            "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else "",
            "data": str(row.data or ""),
            "dezenas": dezenas,
            "metadata_json": str(row.metadata_json or "{}"),
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


def _build_simulated_draw(size: int = 15) -> list[int]:
    return sorted(random.sample(range(1, 26), k=max(1, min(size, 25))))


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


def _run_institutional_generation(*, total_games: int, snapshot: dict[str, Any]) -> None:
    st.session_state["institutional_last_ui_event"] = "operacional:gerar_jogos"
    started = time.monotonic()
    seed = int(time.time()) % 1_000_000
    target_contest = snapshot["latest"].get("imported_contests", "-")
    games = generate_ranked_games(total_games=total_games, seed=seed, ml_enabled=False)
    generation_snapshot = _persist_generation_snapshot(
        games=games,
        seed=seed,
        target_contest=int(target_contest) if str(target_contest).isdigit() else None,
    )
    st.session_state["institutional_generation"] = {
        "seed": seed,
        "games": games,
        "total_games": total_games,
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


def _run_institutional_conference(contest_number: int | None = None) -> None:
    st.session_state["institutional_last_ui_event"] = "operacional:conferir_jogos"
    latest_contest = _load_imported_contest(contest_number)
    generation_state = st.session_state.get("institutional_generation") or {}
    if not generation_state.get("games"):
        persisted_generation = _load_latest_generated_games()
        if persisted_generation and persisted_generation.get("games"):
            generation_state = dict(persisted_generation)
            st.session_state["institutional_generation"] = {
                "seed": int(persisted_generation.get("seed") or 0),
                "games": list(persisted_generation.get("games") or []),
                "total_games": int(persisted_generation.get("total_games") or len(persisted_generation.get("games") or [])),
                "generation_event_id": int(persisted_generation.get("generation_event_id") or 0),
                "created_at": str(persisted_generation.get("created_at") or ""),
                "runtime_status": "loaded_from_database",
                "elapsed_time": 0.0,
            }
            st.session_state["institutional_generation_result"] = {
                "generation_event_id": int(persisted_generation.get("generation_event_id") or 0),
                "seed": int(persisted_generation.get("seed") or 0),
                "jogos": list(persisted_generation.get("games") or []),
            }
        else:
            st.session_state["institutional_check_result"] = {"warning": "Gere jogos antes de conferir."}
            return
    if latest_contest is None:
        st.session_state["institutional_check_result"] = {
            "status": "waiting_contest",
            "warning": "imported_contests ainda está vazio. Sincronize o resultado oficial para habilitar a conferência automática."
        }
        return
    comparison = _compare_games_against_contest(
        generation_event_id=int(generation_state.get("generation_event_id") or 0),
        games=list(generation_state.get("games") or []),
        contest=latest_contest,
    )
    st.session_state["institutional_check"] = {
        "runtime_status": "checked",
        "timestamp": datetime.now(UTC).isoformat(),
        "contest_number": comparison["contest_number"],
        "best_hits": comparison["best_hits"],
        "total_hits": comparison["total_hits"],
    }
    st.session_state["institutional_check_result"] = {
        **comparison,
        "status": "checked",
    }


def _run_institutional_simulation(*, drawn_numbers: list[int] | None = None) -> None:
    st.session_state["institutional_last_ui_event"] = "operacional:simular_resultado"
    generation_state = st.session_state.get("institutional_generation") or {}
    simulated_numbers = sorted(drawn_numbers or _build_simulated_draw(15))
    games = list(generation_state.get("games") or [])
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
            }
        )
    st.session_state["institutional_simulation"] = {
        "runtime_status": "simulated",
        "timestamp": datetime.now(UTC).isoformat(),
        "contest_numbers": simulated_numbers,
        "results": simulation_rows,
    }
    st.session_state["institutional_simulation_result"] = simulation_rows


def _institutional_generation_games() -> list[dict[str, Any]]:
    generation_state = st.session_state.get("institutional_generation") or {}
    if generation_state.get("games"):
        return list(generation_state.get("games") or [])
    persisted_generation = _load_latest_generated_games()
    if persisted_generation and persisted_generation.get("games"):
        return list(persisted_generation.get("games") or [])
    return []


def _summarize_games_structurally(games: list[dict[str, Any]]) -> dict[str, Any]:
    normalized_games = [sorted(int(number) for number in game.get("numbers", [])) for game in games if game.get("numbers")]
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
        return {
            "id": int(run.id or 0),
            "contest_id": int(getattr(run, "contest_id", 0) or 0),
            "generation_event_id": int(getattr(run, "generation_event_id", 0) or 0),
            "status": str(getattr(run, "status", "") or ""),
            "prize_count": int(getattr(run, "prize_count", 0) or 0),
            "total_hits": int(getattr(run, "total_hits", 0) or 0),
            "best_hits": int(getattr(run, "best_hits", 0) or 0),
            "created_at": run.created_at.isoformat() if getattr(run, "created_at", None) else "",
        }


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


def _purge_institutional_history_tables() -> dict[str, Any]:
    tables = [
        "reconciliation_games",
        "reconciliation_runs",
        "generated_games",
        "generation_events",
        "operational_logs",
        "expansion_events",
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
    st.subheader("Histórico Institucional")
    st.write("Visão consolidada do runtime institucional limpo.")
    diag_cols = st.columns(4)
    diag_cols[0].metric("backend", snapshot["backend"])
    diag_cols[1].metric("database_source", snapshot["database_source"])
    diag_cols[2].metric("generated_games", int(snapshot["counts"].get("generated_games", 0)))
    diag_cols[3].metric("reconciliation_runs", int(snapshot["counts"].get("reconciliation_runs", 0)))
    latest_sync = st.session_state.get("institutional_last_official_sync_summary", {})
    if latest_sync:
        sync_cols = st.columns(4)
        sync_cols[0].metric("latest_contest", latest_sync.get("latest_contest", "-"))
        sync_cols[1].metric("synced_contests", len(latest_sync.get("synced_contests", []) or []))
        sync_cols[2].metric("commit_state", latest_sync.get("commit_state", "-"))
        sync_cols[3].metric("fallback", "sim" if latest_sync.get("fallback_used") else "não")
    latest_generation = _load_latest_generated_games() or {}
    latest_reconciliation = _load_latest_reconciliation_summary() or {}
    info_cols = st.columns([1, 1])
    with info_cols[0]:
        st.markdown("##### Última geração persistida")
        if latest_generation.get("games"):
            st.caption(
                f"generation_event_id={latest_generation.get('generation_event_id', '-')}"
                f" | seed={latest_generation.get('seed', '-')}"
                f" | total_games={latest_generation.get('total_games', '-')}"
                f" | target_contest={latest_generation.get('target_contest', '-')}"
            )
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "rank": game.get("game_index", "-"),
                            "dezenas": " ".join(f"{number:02d}" for number in game.get("numbers", [])),
                            "perfil": game.get("profile_type", "-"),
                            "score": round(float(game.get("final_score", {}).get("final_score", 0.0)), 4),
                        }
                        for game in latest_generation.get("games") or []
                    ]
                ),
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("Ainda não há jogos persistidos nesta instância.")
    with info_cols[1]:
        st.markdown("##### Última reconciliação persistida")
        if latest_reconciliation:
            st.caption(
                f"reconciliation_id={latest_reconciliation.get('id', '-')}"
                f" | contest_id={latest_reconciliation.get('contest_id', '-')}"
                f" | status={latest_reconciliation.get('status', '-')}"
            )
            recon_cols = st.columns(3)
            recon_cols[0].metric("best_hits", latest_reconciliation.get("best_hits", "-"))
            recon_cols[1].metric("prize_count", latest_reconciliation.get("prize_count", "-"))
            recon_cols[2].metric("total_hits", latest_reconciliation.get("total_hits", "-"))
        else:
            st.info("Ainda não há reconciliação persistida nesta instância.")
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


def _render_clear_histories_page(snapshot: dict[str, Any]) -> None:
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
    st.subheader("Apagar Histórico")
    st.write("Remove os registros operacionais institucionais persistidos no banco atual.")
    st.warning("Esta ação remove gerações, reconciliações e logs institucionais do runtime. Não afeta imported_contests.")
    confirm = st.checkbox("Confirmo que desejo apagar o histórico institucional persistido.")
    if st.button("Apagar histórico persistido", type="primary", disabled=not confirm):
        result = _purge_institutional_history_tables()
        st.success("Histórico institucional apagado.")
        st.json(result)
        st.rerun()


def _render_comparative_history_page(snapshot: dict[str, Any]) -> None:
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
        service = ResultSyncService(db_path=DB_PATH)
        summary = service.sync_latest()
        payload = summary.to_dict()
        payload["status"] = "ok"
        return payload
    except Exception as exc:  # pragma: no cover - surfaced in UI
        return {
            "status": "error",
            "error_message": str(exc),
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
        }


def _persist_generation_snapshot(*, games: list[dict[str, Any]], seed: int, target_contest: int | None) -> dict[str, Any]:
    started_at = time.monotonic()
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
                        "source": "institutional_app",
                        "target_contest": target_contest,
                        "build_marker": BUILD_MARKER,
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
    official_numbers = sorted(int(number) for number in contest.get("dezenas", []))
    results: list[dict[str, Any]] = []
    for index, game in enumerate(games, start=1):
        numbers = sorted(int(number) for number in game.get("numbers", []))
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
    st.sidebar.markdown('<div class="lotoia-sidebar-title">LotoIA</div>', unsafe_allow_html=True)
    st.sidebar.caption(f"build={APP_BUILD}")
    st.sidebar.caption("Painel institucional limpo")
    pages = [
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
    choice = st.sidebar.radio("Navegação", pages, index=pages.index(page) if page in pages else 0)
    st.sidebar.divider()
    st.sidebar.caption("DATABASE_URL conectada")
    return choice


def _ensure_institutional_schema() -> None:
    create_database(DB_PATH)


def _render_generation_page(snapshot: dict[str, Any]) -> None:
    st.subheader("Gerar Jogos")
    st.write("Fluxo principal limpo, sem legado visual ou CRM.")
    status_cols = st.columns([1, 1, 1, 1, 1])
    status_cols[0].metric("build", BUILD_MARKER)
    status_cols[1].metric("backend", snapshot["backend"])
    status_cols[2].metric("imported_contests", int(snapshot["counts"].get("imported_contests", 0)))
    status_cols[3].metric("generated_games", int(snapshot["counts"].get("generated_games", 0)))
    status_cols[4].metric("reconciliation_runs", int(snapshot["counts"].get("reconciliation_runs", 0)))

    top_cols = st.columns([1.3, 1.3, 1.8])
    top_cols[0].caption(f"Concurso alvo: {snapshot['latest'].get('imported_contests', '-')}")
    top_cols[1].caption("Cada jogo mantém 15 dezenas da Lotofácil.")
    top_cols[2].caption(f"last_ui_event: {st.session_state.get('institutional_last_ui_event', '-')}")

    gen_cols = st.columns([1.0, 0.25])
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
    gen_cols[1].caption("")
    button_cols = st.columns([0.28, 1.72])
    if button_cols[0].button("LotoIA", type="primary"):
        _run_institutional_generation(total_games=total_games, snapshot=snapshot)
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


def _render_conference_page(snapshot: dict[str, Any]) -> None:
    st.subheader("Conferir Resultados")
    st.write("Compare os jogos gerados com o concurso selecionado no banco.")
    status_cols = st.columns([1, 1, 1, 1])
    status_cols[0].metric("imported_contests", int(snapshot["counts"].get("imported_contests", 0)))
    status_cols[1].metric("generated_games", int(snapshot["counts"].get("generated_games", 0)))
    status_cols[2].metric("reconciliation_runs", int(snapshot["counts"].get("reconciliation_runs", 0)))
    status_cols[3].metric("last_event", st.session_state.get("institutional_last_ui_event", "-"))

    contest_numbers = _load_imported_contest_numbers()
    latest_contest = _load_imported_contest()
    current_contest = int(contest_numbers[-1]) if contest_numbers else int(snapshot["latest"].get("imported_contests") or 0) if str(snapshot["latest"].get("imported_contests", "")).isdigit() else 0
    if "institutional_contest_nav" not in st.session_state:
        st.session_state["institutional_contest_nav"] = current_contest or 0
    if current_contest and st.session_state["institutional_contest_nav"] < current_contest:
        st.session_state["institutional_contest_nav"] = current_contest
    nav_cols = st.columns([0.35, 0.8, 0.35, 1.05, 1.35])
    if nav_cols[0].button("−", use_container_width=True):
        st.session_state["institutional_contest_nav"] = max(1, int(st.session_state.get("institutional_contest_nav", current_contest or 1)) - 1)
    nav_cols[1].markdown(
        f"<div style='padding-top:0.2rem;font-size:0.78rem;letter-spacing:0.08em;color:#6b7280;text-transform:uppercase;'>Último concurso</div>",
        unsafe_allow_html=True,
    )
    if nav_cols[2].button("+"):
        st.session_state["institutional_contest_nav"] = int(st.session_state.get("institutional_contest_nav", current_contest or 1)) + 1
    selected_contest = int(st.session_state.get("institutional_contest_nav", current_contest or 1) or 1)
    nav_cols[3].markdown(
        f"<div style='font-size:1.4rem;font-weight:800;color:#123456;line-height:1.1;'>{selected_contest}</div>",
        unsafe_allow_html=True,
    )
    nav_cols[4].markdown(
        f"<div style='padding-top:0.15rem;font-size:0.82rem;color:#6b7280;'>{len(contest_numbers)} concursos no banco</div>",
        unsafe_allow_html=True,
    )
    contest_buttons = st.columns([0.55, 0.7, 0.85])
    if contest_buttons[0].button("Conferir Resultados", type="primary"):
        _run_institutional_conference(contest_number=selected_contest if selected_contest else None)
        st.rerun()
    if contest_buttons[1].button("Sincronizar resultado oficial agora"):
        with st.spinner("Importando resultado oficial da Caixa..."):
            sync_payload = _sync_latest_official_result_now()
        st.session_state["institutional_last_official_sync_summary"] = dict(sync_payload)
        try:
            st.cache_data.clear()
        except Exception:
            pass
        if sync_payload.get("status") == "ok":
            st.success(f"Resultado oficial importado: {sync_payload.get('latest_contest', '-')}")
        else:
            st.error(f"Falha ao importar resultado oficial: {sync_payload.get('error_message', '-')}")
        st.json(sync_payload)
        st.rerun()
    if contest_buttons[2].button("Importar último resultado oficial"):
        with st.spinner("Sincronizando o último resultado oficial..."):
            sync_payload = _sync_latest_official_result_now()
        st.session_state["institutional_last_official_sync_summary"] = dict(sync_payload)
        try:
            st.cache_data.clear()
        except Exception:
            pass
        if sync_payload.get("status") == "ok":
            st.success(f"Resultado oficial importado: {sync_payload.get('latest_contest', '-')}")
        else:
            st.error(f"Falha ao importar resultado oficial: {sync_payload.get('error_message', '-')}")
        st.json(sync_payload)
        st.rerun()

    check_result = st.session_state.get("institutional_check_result")
    if isinstance(check_result, dict) and check_result.get("warning"):
        st.warning(check_result["warning"])
    if isinstance(check_result, dict) and check_result.get("results"):
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
        st.info("A conferência está pronta, mas ainda falta o concurso oficial em imported_contests.")


def _render_simulation_page(snapshot: dict[str, Any]) -> None:
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


def _render_history_page(snapshot: dict[str, Any]) -> None:
    _render_analytical_page(snapshot)


def _render_operational_page(snapshot: dict[str, Any]) -> None:
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
    st.subheader("Histórico Analítico")
    st.write("Snapshot institucional do banco atual via DATABASE_URL.")
    diag_cols = st.columns(3)
    diag_cols[0].metric("backend", snapshot["backend"])
    diag_cols[1].metric("database_source", snapshot["database_source"])
    diag_cols[2].metric("imported_contests", int(snapshot["counts"].get("imported_contests", 0)))
    st.caption(f"database_url: {_mask_database_url(snapshot['database_url'])}")
    last_sync_summary = st.session_state.get("institutional_last_official_sync_summary", {})
    if last_sync_summary:
        sync_cols = st.columns(4)
        sync_cols[0].metric("latest_contest", last_sync_summary.get("latest_contest", "-"))
        sync_cols[1].metric("synced_contests", len(last_sync_summary.get("synced_contests", []) or []))
        sync_cols[2].metric("commit_state", last_sync_summary.get("commit_state", "-"))
        sync_cols[3].metric("fallback", "sim" if last_sync_summary.get("fallback_used") else "não")
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
    page = _render_sidebar(st.session_state.get("institutional_page", "Gerar Jogos"), snapshot)
    st.session_state["institutional_page"] = page
    st.title("LotoIA Institucional")
    st.success(BUILD_MARKER)
    st.caption("Painel mínimo, isolado e pronto para o runtime novo.")
    if page == "Gerar Jogos":
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
