# -*- coding: utf-8 -*-
from __future__ import annotations

try:
    from . import _bootstrap  # type: ignore[import-not-found]  # noqa: F401
except ImportError:
    import _bootstrap  # type: ignore[no-redef]  # noqa: F401

import json
import os
import threading
import time
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy import inspect, text

from lotoia.database.adapter import InstitutionalDatabaseAdapter
from lotoia.database.database import DEFAULT_DATABASE_PATH, get_engine
from lotoia.experiments.hb_geometry_audit import DEFAULT_HB_GEOMETRY_DIR, run_hb_geometry_audit


BUILD_MARKER = "institutional-clean-runtime-v1"
APP_BUILD = BUILD_MARKER
PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
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


def _render_sidebar(page: str) -> str:
    st.sidebar.title("LotoIA")
    st.sidebar.caption(f"build={APP_BUILD}")
    st.sidebar.caption("Painel institucional limpo")
    choice = st.sidebar.radio("Navegação", ["Operacional", "Analítico", "HB Geometry"], index=["Operacional", "Analítico", "HB Geometry"].index(page))
    st.sidebar.divider()
    st.sidebar.caption("DATABASE_URL conectada")
    return choice


def _render_operational_page(snapshot: dict[str, Any]) -> None:
    st.subheader("Operacional")
    st.write("Fluxo principal limpo, sem legado visual ou CRM.")
    cols = st.columns(2)
    if cols[0].button("Gerar Jogos", use_container_width=True):
        st.session_state["institutional_last_ui_event"] = "operacional:gerar_jogos"
        st.success("Ação registrada. O fluxo de geração está pronto para o serviço oficial.")
    if cols[1].button("Conferir Jogos", use_container_width=True):
        st.session_state["institutional_last_ui_event"] = "operacional:conferir_jogos"
        latest_contest = snapshot["latest"].get("imported_contests", "-")
        count = snapshot["counts"].get("imported_contests", 0)
        if int(count) > 0:
            st.success(f"Conferência pronta. imported_contests={count}, latest_contest={latest_contest}.")
        else:
            st.warning("imported_contests ainda está vazio. Sincronize o resultado oficial para habilitar a conferência automática.")
    st.caption(f"last_ui_event: {st.session_state.get('institutional_last_ui_event', '-')}")


def _render_analytical_page(snapshot: dict[str, Any]) -> None:
    st.subheader("Analítico")
    st.write("Snapshot institucional do banco atual via DATABASE_URL.")
    diag_cols = st.columns(3)
    diag_cols[0].metric("backend", snapshot["backend"])
    diag_cols[1].metric("database_source", snapshot["database_source"])
    diag_cols[2].metric("imported_contests", int(snapshot["counts"].get("imported_contests", 0)))
    st.caption(f"database_url: {_mask_database_url(snapshot['database_url'])}")
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
    job = state["job"]
    progress = state["progress"]
    summary = state["summary"]
    csv_frame = state["csv_frame"]
    button_cols = st.columns(3)
    if button_cols[0].button("Iniciar Auditoria", type="primary", disabled=bool(job.get("running"))):
        st.session_state["institutional_last_ui_event"] = "hb_geometry:iniciar"
        _start_hb_geometry_job(resume=bool(progress) and not bool(progress.get("completed", False)))
        st.rerun()
    if button_cols[1].button("Continuar Auditoria", disabled=bool(job.get("running")) or not bool(progress) or bool(progress.get("completed", False))):
        st.session_state["institutional_last_ui_event"] = "hb_geometry:continuar"
        _start_hb_geometry_job(resume=True)
        st.rerun()
    if button_cols[2].button("Resetar Auditoria", disabled=bool(job.get("running"))):
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
    snapshot = _database_snapshot()
    page = _render_sidebar(st.session_state.get("institutional_page", "Operacional"))
    st.session_state["institutional_page"] = page
    st.title("LotoIA Institucional")
    st.success(BUILD_MARKER)
    st.caption("Painel mínimo, isolado e pronto para o runtime novo.")
    if page == "Operacional":
        _render_operational_page(snapshot)
    elif page == "Analítico":
        _render_analytical_page(snapshot)
    else:
        _render_hb_geometry_page(_hb_geometry_state())


if __name__ == "__main__":
    main()
