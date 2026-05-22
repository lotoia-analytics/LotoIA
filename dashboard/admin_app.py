from __future__ import annotations

try:
    from . import _bootstrap  # type: ignore[import-not-found]  # noqa: F401
    from .labels import LABELS, PAGES
except ImportError:
    import _bootstrap  # type: ignore[no-redef]  # noqa: F401
    from labels import LABELS, PAGES  # type: ignore[no-redef]

import json
import sqlite3
import shutil
import time
import tempfile
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lotoia.calibration.weight_calibrator import (
    WeightConfiguration,
    compare_weight_configurations,
)
from lotoia.combinatorics import (
    DEFAULT_STAKE_PRICE,
    ExpansionConfig,
    expand_lotofacil_numbers,
    estimate_expansion,
)
from lotoia.data.loader import DEFAULT_HISTORY_PATH, load_draws_csv
from lotoia.database import list_runs
from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.experiments.temporal_governance import build_walk_forward_splits
from lotoia.governance.adaptive_governance_report import (
    ADAPTIVE_GOVERNANCE_REPORT_CREATED_INDEX_SQL,
    ADAPTIVE_GOVERNANCE_REPORT_EXPERIMENT_INDEX_SQL,
    ADAPTIVE_GOVERNANCE_REPORT_TABLE_SQL,
)
from lotoia.models.draw import Draw
from lotoia.standards import (
    ArtifactKind,
    EventCategory,
    Severity,
    artifact_path,
    institutional_timestamp,
    metadata_envelope,
    ml_governance_payload,
    operational_event,
    report_payload,
)
from lotoia.ml import (
    InterpretableLinearScoreML,
    attach_score_ml,
    calibrate_linear_score_ml,
    ml_heartbeat,
    extract_score_ml_features,
    migrate_score_ml_snapshot,
    ensure_calibration,
    supervised_rerank_games,
)
from lotoia.reports import generate_backtest_report
from lotoia.analytics import (
    build_analytical_intelligence,
    build_executive_analytical_report,
    build_institutional_analytical_timeline,
    build_institutional_historical_intelligence,
    load_adaptive_institutional_insights,
    load_adaptive_institutional_intelligence,
    load_adaptive_institutional_timeline,
    ensure_institutional_analytical_timeline,
    load_institutional_analytics_snapshot,
    load_institutional_analytical_timeline,
    publish_institutional_analytics,
    publish_adaptive_institutional_intelligence,
)
from lotoia.assistance import build_executive_assistance
from lotoia.assistance import build_contextual_recommendations
from lotoia.assistance import build_explainable_analytics
from lotoia.assistance import build_operational_guidance
from lotoia.assistance import build_executive_summary
from lotoia.assistance import build_adaptive_assistance_memory
from lotoia.assistance import build_human_analytical_language
from lotoia.assistance import build_institutional_support_experience
from lotoia.assistance import build_assistance_governance
from lotoia.assistance import build_full_executive_assistance_presence
from lotoia.workflows import build_workflow_dashboard, WorkflowEngine
from lotoia.orchestration import (
    build_intelligent_operational_orchestration,
    load_intelligent_operational_orchestration,
    persist_intelligent_operational_orchestration,
)
from lotoia.public import OperationalLifecycleEngine
from lotoia.memory import build_adaptive_evolution_tracking
from lotoia.observability import (
    build_institutional_observability_dashboard,
    build_operational_experience,
    build_live_institutional_presence,
    build_live_operational_memory,
    build_live_telemetry_snapshot,
    build_operational_health_snapshot,
    build_real_time_governance,
    build_runtime_storytelling,
    build_memory_timeline,
    build_observational_stabilization_report,
    load_observational_stabilization_report,
    persist_observational_stabilization_report,
)
from lotoia.public.services import LeadCaptureRequest, LeadCaptureService
from dashboard.components import (
    render_adaptive_institutional_intelligence,
    render_analytical_cards,
    render_executive_dashboard,
    render_generation_context,
    render_live_analytical_intelligence,
    render_hero_banner,
    render_executive_panel,
    render_executive_summary,
    render_institutional_timeline,
    render_operational_orchestration,
    render_secondary_operational_metrics,
    render_structural_health,
)
from lotoia.statistics.advanced import (
    FINAL_SCORE_WEIGHTS,
    calculate_hot_cold_numbers,
    load_delay_stats,
    load_duos_stats,
    load_frequency_stats,
    load_quadras_stats,
    load_quinas_stats,
    load_senas_stats,
    load_ternos_stats,
)
from lotoia.statistics.historical_intelligence import (
    GENERATION_PROFILE_RATIOS,
    classify_profile,
    profile_score,
)
from lotoia.statistics.generation_trace import diversity_collapse_report, pressure_heatmap, survival_summary
from lotoia.statistics.generation_trace import destructive_filters_report, executive_behavioral_report, filter_profile_damage_report, normalization_comparison_report, pipeline_divergence_score, replay_snapshot
from lotoia.statistics.generation_trace import behavior_recovery_timeline, behavior_drift_report, experiment_baseline_report, experiment_comparison_report, false_recovery_report, golden_baselines, historical_adherence_score, pressure_sensitivity_report, profile_stability_score, recovery_decision_protocol, recovery_plateau_detection, safe_recovery_zone
from lotoia.statistics.generation_trace import experiment_01_report, marginal_recovery_gain
from lotoia.statistics.basic import summarize_draws

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / DEFAULT_DATABASE_PATH
LOGO_PATH = PROJECT_ROOT / "assets" / "logo.png"
LOGO_DIRECTORY = PROJECT_ROOT / "assets" / "logo"
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_SNAPSHOTS_DIR = REPORTS_DIR / "snapshots"
ML_REPORTS_DIR = REPORTS_DIR / "ml"
ML_SNAPSHOTS_DIR = ML_REPORTS_DIR / "snapshots"
SQLITE_BUSY_TIMEOUT_MS = 5000
ADMIN_EVENT_LIMIT = 200
LEAD_HISTORY_LIMIT = 5000
STREAMLIT_CACHE_TTL_SECONDS = 300
STREAMLIT_CACHE_MAX_ENTRIES = 16
ADMIN_EXPANSION_ALLOWED_SIZES = (16, 17)
ADMIN_EXPANSION_PREVIEW_LIMIT = 136
ADMIN_EXPANSION_PAGE_SIZE = 50
ALLOWED_ADMIN_EVENT_TABLES = frozenset({"generation_events", "generated_games", "check_events", "operational_logs", "audit_trail", "leads"})
ALERT_GENERATION_MS = 5_000.0
ALERT_CHECK_MS = 3_000.0
ALERT_REPORT_MS = 15_000.0
ALERT_DASHBOARD_LOAD_MS = 8_000.0
ALERT_REPEATED_FAILURES = 3
ALERT_SQLITE_SIZE_BYTES = 256 * 1024 * 1024
ALERT_LOG_GROWTH_EVENTS = 1_000
SQLITE_BOOTSTRAP_DIAGNOSTICS: list[dict[str, Any]] = []
SQLITE_MEMORY_LOGS: list[dict[str, Any]] = []
SQLITE_RECOVERY_STATE = {"attempted": False, "active": False, "last_backup": "", "last_error": ""}
SQLITE_BOOTSTRAP_STATE = {"fallback_used": False, "requested_path": "", "active_path": ""}

conn: sqlite3.Connection | None = None
cursor: sqlite3.Cursor | None = None


def _sqlite_open_connection(path: Path = DB_PATH) -> sqlite3.Connection:
    candidates = [path, Path(tempfile.gettempdir()) / "lotoia" / "lotoia.db"]
    last_error: Exception | None = None

    for candidate in candidates:
        try:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(candidate, check_same_thread=False)
            try:
                connection.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
                connection.execute("PRAGMA journal_mode = WAL")
                connection.execute("PRAGMA synchronous = NORMAL")
            except sqlite3.Error:
                pass
            global DB_PATH
            DB_PATH = candidate
            if candidate != path:
                fallback_context = {
                    "requested_path": str(path),
                    "active_path": str(candidate),
                    "reason": "sqlite bootstrap fallback path selected",
                }
                SQLITE_BOOTSTRAP_STATE.update(
                    {
                        "fallback_used": True,
                        "requested_path": str(path),
                        "active_path": str(candidate),
                    }
                )
                SQLITE_MEMORY_LOGS.append(
                    {
                        "event_type": "sqlite_bootstrap",
                        "status": "fallback",
                        "context": fallback_context,
                    }
                )
                _record_operational_log("sqlite_bootstrap", "fallback", 0.0, fallback_context)
            return connection
        except Exception as exc:
            last_error = exc

    raise sqlite3.OperationalError(f"sqlite bootstrap failed for all candidates: {last_error}")


def _sqlite_bootstrap_state() -> dict[str, Any]:
    return dict(SQLITE_BOOTSTRAP_STATE)


def _sqlite_bind_connection(connection: sqlite3.Connection) -> None:
    global conn, cursor
    conn = connection
    cursor = connection.cursor()


def _sqlite_ensure_runtime_connection() -> tuple[sqlite3.Connection | None, sqlite3.Cursor | None]:
    if conn is None or cursor is None:
        try:
            _sqlite_bind_connection(_sqlite_open_connection())
        except Exception as exc:
            _sqlite_memory_logs.append({"event_type": "sqlite", "status": "failed", "error": str(exc)})
            return None, None
    return conn, cursor


def _sqlite_backup_corrupted_database(error_text: str) -> Path | None:
    if not DB_PATH.exists():
        return None
    backup_dir = DB_PATH.parent / "data" / "corrupted"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{DB_PATH.stem}_{time.strftime('%Y%m%dT%H%M%S')}.db"
    try:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        shutil.move(str(DB_PATH), str(backup_path))
        SQLITE_RECOVERY_STATE["last_backup"] = str(backup_path)
        SQLITE_RECOVERY_STATE["last_error"] = error_text
        return backup_path
    except Exception as exc:
        SQLITE_MEMORY_LOGS.append(
            {
                "event_type": "sqlite_recovery",
                "status": "failed",
                "error": str(exc),
                "source_error": error_text,
            }
        )
        return None


def _sqlite_maybe_recover_connection(error: Exception) -> bool:
    message = str(error).lower()
    if not isinstance(error, sqlite3.DatabaseError) and "malformed" not in message:
        return False
    if SQLITE_RECOVERY_STATE["attempted"]:
        return False
    SQLITE_RECOVERY_STATE["attempted"] = True
    backup_path = _sqlite_backup_corrupted_database(str(error))
    try:
        new_conn = _sqlite_open_connection()
        _sqlite_bind_connection(new_conn)
        _sqlite_ensure_admin_schema()
        if cursor is not None:
            try:
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()
                if not (result and str(result[0]).lower() == "ok"):
                    raise sqlite3.DatabaseError("integrity_check failed after recovery")
            except Exception:
                pass
        if conn is not None:
            conn.commit()
        SQLITE_RECOVERY_STATE["active"] = True
        _record_operational_log(
            "sqlite_recovery",
            "success",
            0.0,
            {"backup_path": str(backup_path) if backup_path else "", "source_error": str(error)},
        )
        return True
    except Exception as exc:
        SQLITE_MEMORY_LOGS.append(
            {
                "event_type": "sqlite_recovery",
                "status": "failed",
                "error": str(exc),
                "source_error": str(error),
                "backup_path": str(backup_path) if backup_path else "",
            }
        )
        return False


def _sqlite_classify_error(statement: str, exc: Exception, table_name: str | None = None) -> dict[str, str]:
    message = str(exc)
    lowered = message.lower()
    if "no such table" in lowered:
        issue = "table ausente"
    elif "no such column" in lowered:
        issue = "coluna ausente"
    elif "syntax error" in lowered:
        issue = "schema inválido"
    elif "constraint" in lowered:
        issue = "migration pendente"
    else:
        issue = "erro sqlite"
    return {
        "issue": issue,
        "table": table_name or "",
        "sql": statement.strip().replace("\n", " "),
        "error": message,
    }


def _sqlite_execute_bootstrap(statement: str, *, table_name: str | None = None) -> bool:
    connection, current_cursor = _sqlite_ensure_runtime_connection()
    if connection is None or current_cursor is None:
        SQLITE_BOOTSTRAP_DIAGNOSTICS.append(
            {
                "issue": "runtime indisponível",
                "table": table_name or "",
                "sql": statement.strip().replace("\n", " "),
                "error": "No SQLite connection available",
            }
        )
        return False
    try:
        current_cursor.execute(statement)
        return True
    except sqlite3.Error as exc:
        if _sqlite_maybe_recover_connection(exc):
            recovered = _sqlite_ensure_runtime_connection()[1]
            if recovered is not None:
                try:
                    recovered.execute(statement)
                    return True
                except sqlite3.Error as retry_exc:
                    exc = retry_exc
        diagnostic = _sqlite_classify_error(statement, exc, table_name)
        SQLITE_BOOTSTRAP_DIAGNOSTICS.append(diagnostic)
        try:
            SQLITE_MEMORY_LOGS.append({"event_type": "sqlite", "status": "failed", **diagnostic})
            _record_operational_log("sqlite", "failed", 0.0, diagnostic)
        except Exception:
            pass
        return False


def _sqlite_table_columns(table_name: str) -> set[str]:
    _, current_cursor = _sqlite_ensure_runtime_connection()
    if current_cursor is None:
        return set()
    try:
        rows = current_cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
    except sqlite3.Error:
        return set()
    return {str(row[1]) for row in rows}


def _sqlite_ensure_column(table_name: str, column_name: str, ddl_type: str, default_sql: str | None = None) -> None:
    columns = _sqlite_table_columns(table_name)
    if column_name in columns:
        return
    statement = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl_type}"
    if default_sql is not None:
        statement = f"{statement} DEFAULT {default_sql}"
    _sqlite_execute_bootstrap(statement, table_name=table_name)


def _sqlite_ensure_admin_schema() -> None:
    schema_statements = (
        """
        CREATE TABLE IF NOT EXISTS generation_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            whatsapp TEXT NOT NULL,
            seed INTEGER,
            strategy TEXT,
            ranking_score REAL,
            execution_time_ms REAL,
            ml_enabled INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS check_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            whatsapp TEXT NOT NULL,
            contest_id INTEGER,
            hits INTEGER,
            execution_time_ms REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS generated_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generation_event_id INTEGER,
            lead_id INTEGER,
            target_contest INTEGER,
            origin TEXT NOT NULL DEFAULT 'dashboard',
            generation_mode TEXT NOT NULL DEFAULT '',
            game_index INTEGER,
            numbers TEXT,
            profile_type TEXT,
            final_score TEXT,
            quadra_score TEXT,
            context_json TEXT NOT NULL DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS imported_contests (
            contest_number INTEGER PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data TEXT,
            dezenas TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}'
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            whatsapp TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS operational_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            status TEXT NOT NULL,
            duration_ms REAL,
            context_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS audit_trail (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT NOT NULL,
            actor TEXT,
            artifact_path TEXT,
            context_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_type TEXT NOT NULL,
            artifact_path TEXT NOT NULL,
            metadata_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        ADAPTIVE_GOVERNANCE_REPORT_TABLE_SQL,
    )
    for statement in schema_statements:
        table_name = None
        for candidate in ("generation_events", "check_events", "generated_games", "imported_contests", "leads", "operational_logs", "audit_trail", "snapshots", "adaptive_governance_reports"):
            if candidate in statement:
                table_name = candidate
                break
        _sqlite_execute_bootstrap(statement, table_name=table_name)

    _sqlite_ensure_column("generation_events", "first_name", "TEXT", "''")
    _sqlite_ensure_column("generation_events", "whatsapp", "TEXT", "''")
    _sqlite_ensure_column("generation_events", "seed", "INTEGER")
    _sqlite_ensure_column("generation_events", "strategy", "TEXT")
    _sqlite_ensure_column("generation_events", "ranking_score", "REAL")
    _sqlite_ensure_column("generation_events", "execution_time_ms", "REAL")
    _sqlite_ensure_column("generation_events", "ml_enabled", "INTEGER", "0")
    _sqlite_ensure_column("check_events", "first_name", "TEXT", "''")
    _sqlite_ensure_column("check_events", "whatsapp", "TEXT", "''")
    _sqlite_ensure_column("check_events", "contest_id", "INTEGER")
    _sqlite_ensure_column("check_events", "hits", "INTEGER")
    _sqlite_ensure_column("check_events", "execution_time_ms", "REAL")
    _sqlite_ensure_column("generated_games", "target_contest", "INTEGER")
    _sqlite_ensure_column("generated_games", "origin", "TEXT", "'dashboard'")
    _sqlite_ensure_column("generated_games", "generation_mode", "TEXT", "''")
    _sqlite_ensure_column("generated_games", "context_json", "TEXT", "'{}'")
    _sqlite_ensure_column("imported_contests", "metadata_json", "TEXT", "'{}'")
    _sqlite_ensure_column("leads", "first_name", "TEXT", "''")
    _sqlite_ensure_column("leads", "whatsapp", "TEXT", "''")
    _sqlite_ensure_column("leads", "created_at", "TIMESTAMP", "CURRENT_TIMESTAMP")
    _sqlite_ensure_column("operational_logs", "event_type", "TEXT", "''")
    _sqlite_ensure_column("operational_logs", "status", "TEXT", "''")
    _sqlite_ensure_column("operational_logs", "duration_ms", "REAL")
    _sqlite_ensure_column("operational_logs", "context_json", "TEXT")
    _sqlite_ensure_column("audit_trail", "action_type", "TEXT", "''")
    _sqlite_ensure_column("audit_trail", "actor", "TEXT")
    _sqlite_ensure_column("audit_trail", "artifact_path", "TEXT")
    _sqlite_ensure_column("audit_trail", "context_json", "TEXT")
    _sqlite_ensure_column("snapshots", "snapshot_type", "TEXT", "''")
    _sqlite_ensure_column("snapshots", "artifact_path", "TEXT", "''")
    _sqlite_ensure_column("snapshots", "metadata_json", "TEXT")
    _sqlite_ensure_column("snapshots", "created_at", "TIMESTAMP", "CURRENT_TIMESTAMP")
    _sqlite_ensure_column("adaptive_governance_reports", "governance_id", "TEXT")
    _sqlite_ensure_column("adaptive_governance_reports", "created_at", "TEXT")
    _sqlite_ensure_column("adaptive_governance_reports", "source_intelligence_id", "TEXT")
    _sqlite_ensure_column("adaptive_governance_reports", "experiment_id", "TEXT")
    _sqlite_ensure_column("adaptive_governance_reports", "model_name", "TEXT")
    _sqlite_ensure_column("adaptive_governance_reports", "model_version", "TEXT")
    _sqlite_ensure_column("adaptive_governance_reports", "benchmark_id", "TEXT")
    _sqlite_ensure_column("adaptive_governance_reports", "risk_score", "REAL", "0")
    _sqlite_ensure_column("adaptive_governance_reports", "approval_status", "TEXT", "''")
    _sqlite_ensure_column("adaptive_governance_reports", "change_action", "TEXT", "''")
    _sqlite_ensure_column("adaptive_governance_reports", "summary_metrics_json", "TEXT", "'{}'")
    _sqlite_ensure_column("adaptive_governance_reports", "report_json", "TEXT", "'{}'")

    for index_sql in (
        "CREATE INDEX IF NOT EXISTS idx_snapshots_created_at ON snapshots(created_at DESC, id DESC)",
        "CREATE INDEX IF NOT EXISTS idx_snapshots_type ON snapshots(snapshot_type, created_at DESC)",
        ADAPTIVE_GOVERNANCE_REPORT_EXPERIMENT_INDEX_SQL,
        ADAPTIVE_GOVERNANCE_REPORT_CREATED_INDEX_SQL,
    ):
        _sqlite_execute_bootstrap(index_sql)


def _render_sqlite_bootstrap_diagnostics() -> None:
    if not SQLITE_BOOTSTRAP_DIAGNOSTICS:
        return
    last = SQLITE_BOOTSTRAP_DIAGNOSTICS[-1]
    st.error(f"SQLite bootstrap {last['issue']}: {last['error']}")
    st.caption(f"Tabela: {last['table'] or 'n/a'}")
    st.code(last["sql"], language="sql")


def _render_sidebar_logo() -> None:
    logo_candidates = (
        LOGO_DIRECTORY / "logo.png",
        LOGO_DIRECTORY / "logo.webp",
        LOGO_PATH,
    )
    for logo_path in logo_candidates:
        try:
            if logo_path.exists() and logo_path.is_file():
                st.sidebar.image(str(logo_path), width=260)
                return
        except Exception:
            continue
    st.sidebar.markdown('<div class="lotoia-sidebar-fallback">LotoIA</div>', unsafe_allow_html=True)


_sqlite_bind_connection(_sqlite_open_connection())
_sqlite_ensure_admin_schema()
if conn is not None:
    conn.commit()

def _format_numbers(numbers: list[int]) -> str:
    return " ".join(f"{number:02d}" for number in numbers)


def _parse_admin_expansion_numbers(text: str) -> list[int]:
    tokens = [token for token in text.replace(",", " ").split() if token]
    numbers = sorted(int(token) for token in tokens)
    if len(numbers) not in ADMIN_EXPANSION_ALLOWED_SIZES:
        raise ValueError("Modo experimental interno permite apenas 16 ou 17 dezenas.")
    if len(set(numbers)) != len(numbers):
        raise ValueError("As dezenas nao podem se repetir no jogo expandido.")
    if any(number < 1 or number > 25 for number in numbers):
        raise ValueError("As dezenas devem estar entre 1 e 25.")
    return numbers


def _default_admin_expansion_numbers(selected_count: int) -> str:
    size = selected_count if selected_count in ADMIN_EXPANSION_ALLOWED_SIZES else ADMIN_EXPANSION_ALLOWED_SIZES[0]
    return _format_numbers(list(range(1, size + 1)))


def _admin_expansion_dataframe(combinations: list[list[int]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "aposta": index + 1,
                "dezenas": _format_numbers(game),
            }
            for index, game in enumerate(combinations)
        ]
    )


def _run_admin_expansion(numbers: list[int], preview_limit: int = ADMIN_EXPANSION_PREVIEW_LIMIT) -> dict[str, Any]:
    start_time = time.monotonic()
    result = expand_lotofacil_numbers(
        numbers,
        config=ExpansionConfig(
            preview_limit=min(preview_limit, ADMIN_EXPANSION_PREVIEW_LIMIT),
            max_runtime_seconds=1.5,
            stake_price=DEFAULT_STAKE_PRICE,
        ),
    )
    payload = result.as_dict()
    payload["metrics"] = {
        "engine": "combinatorial_expansion_v1_admin_experimental",
        "allowed_sizes": list(ADMIN_EXPANSION_ALLOWED_SIZES),
        "memory_policy": "preview_paginated_no_full_ui_dump",
        "runtime_guard_seconds": 1.5,
    }
    _record_operational_log(
        "admin_expansion_experimental",
        "success",
        (time.monotonic() - start_time) * 1000.0,
        {
            "selected_count": len(numbers),
            "total_combinations": payload["total_combinations"],
            "generated_count": payload["generated_count"],
            "complete": payload["complete"],
            "stopped_reason": payload["stopped_reason"],
        },
    )
    return payload


def _safe_int(value: Any, default: int, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        candidate = int(value)
    except Exception:
        candidate = default
    if minimum is not None:
        candidate = max(minimum, candidate)
    if maximum is not None:
        candidate = min(maximum, candidate)
    return candidate


def _safe_float(value: Any, default: float, minimum: float | None = None, maximum: float | None = None) -> float:
    try:
        candidate = float(value)
    except Exception:
        candidate = default
    if minimum is not None:
        candidate = max(minimum, candidate)
    if maximum is not None:
        candidate = min(maximum, candidate)
    return candidate


def _safe_text(value: Any, default: str = "", max_length: int = 120) -> str:
    text = default if value is None else str(value)
    text = text.strip()
    return text[:max_length]


def _safe_dataframe(dataframe: pd.DataFrame | None, columns: list[str] | None = None) -> pd.DataFrame:
    if dataframe is None:
        return pd.DataFrame(columns=columns or [])
    if columns is not None and dataframe.empty:
        return pd.DataFrame(columns=columns)
    return dataframe


def _normalize_numbers(numbers: list[int]) -> tuple[int, ...]:
    return tuple(sorted(int(number) for number in numbers))


def _draw_numbers(draw: Any) -> list[int]:
    if isinstance(draw, Draw):
        return [int(item) for item in draw.numbers]
    if isinstance(draw, dict):
        numbers = draw.get("numbers")
        if isinstance(numbers, list):
            return [int(item) for item in numbers]
        dezenas = draw.get("dezenas")
        if isinstance(dezenas, list):
            return [int(item) for item in dezenas]
        values = []
        for key in sorted(draw):
            if str(key).startswith("d"):
                try:
                    values.append(int(draw[key]))
                except Exception:
                    continue
        return values
    return []


def _draw_contest(draw: Any) -> int:
    if isinstance(draw, Draw):
        return int(draw.contest)
    if isinstance(draw, dict):
        for key in ("concurso", "contest", "id"):
            value = draw.get(key)
            if value is not None:
                try:
                    return int(value)
                except Exception:
                    continue
    return 0


@st.cache_data(show_spinner=False, ttl=STREAMLIT_CACHE_TTL_SECONDS, max_entries=STREAMLIT_CACHE_MAX_ENTRIES)
def _historical_dataset() -> dict[str, Any]:
    draws = _load_draws()
    historical_map: dict[tuple[int, ...], list[int]] = {}
    all_numbers: list[int] = []
    for draw in draws:
        numbers = _normalize_numbers(_draw_numbers(draw))
        if not numbers:
            continue
        all_numbers.extend(numbers)
        contest = _draw_contest(draw)
        historical_map.setdefault(numbers, []).append(contest)
    frequency = pd.Series(all_numbers).value_counts().sort_index().to_dict() if all_numbers else {}
    return {
        "draws": draws,
        "historical_map": historical_map,
        "frequency": frequency,
        "total_draws": len(draws),
    }


def _historical_match_engine(numbers: list[int]) -> dict[str, Any]:
    dataset = _historical_dataset()
    historical_map = dataset["historical_map"]
    normalized = _normalize_numbers(numbers)
    total_draws = int(dataset["total_draws"])
    occurrences = historical_map.get(normalized, [])
    history = dataset["draws"]
    similar_contests: list[dict[str, Any]] = []
    for historical_numbers, contests in historical_map.items():
        overlap = len(set(normalized).intersection(historical_numbers))
        if overlap >= 9:
            similar_contests.append(
                {
                    "combo": _format_numbers(list(historical_numbers)),
                    "contests": contests[-3:],
                    "overlap": overlap,
                    "occurrences": len(contests),
                }
            )
    similar_contests = sorted(similar_contests, key=lambda item: (item["overlap"], item["occurrences"]), reverse=True)[:10]
    profile_type = classify_profile(list(normalized), history)
    intelligence = profile_score(list(normalized), history, profile_type)
    rarity = float(intelligence["structural_rarity"]) / 100
    proximity = max((item["overlap"] / len(normalized) for item in similar_contests), default=0.0)
    score = float(intelligence["profile_score"])
    return {
        "numbers": normalized,
        "is_unique": int(intelligence["partial_match_max"]) == 0,
        "occurrences": len(occurrences),
        "last_contest": occurrences[-1] if occurrences else None,
        "similar_contests": similar_contests,
        "rarity": round(rarity, 4),
        "proximity": round(proximity, 4),
        "historical_score": score,
        **intelligence,
    }


def _historical_intelligence_dataframe(games: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for index, game in enumerate(games, start=1):
        match = _historical_match_engine(game["numbers"])
        rows.append(
            {
                "rank": index,
                "dezenas": _format_numbers(game["numbers"]),
                "historical_score": match["historical_score"],
                "profile_type": match["profile_type"],
                "recurrence_score": match["recurrence_score"],
                "partial_match_max": match["partial_match_max"],
                "partial_match_avg": match["partial_match_avg"],
                "jaccard_similarity": match["jaccard_similarity"],
                "structural_rarity": match["structural_rarity"],
                "entropy_score": match["entropy_score"],
                "block_density": match["block_density"],
                "max_sequence_length": match["max_sequence_length"],
                "recent_repetition_count": match["recent_repetition_count"],
                "cluster_type": match["cluster_type"],
                "ranking_reason": match["ranking_reason"],
                "rarity": match["rarity"],
                "repeat_count": match["occurrences"],
                "partial_repeat_count": match["partial_match_max"],
                "is_unique": match["is_unique"],
                "last_contest": match["last_contest"],
                "proximity": match["proximity"],
                "similar_contests": ", ".join(
                    str(item["contests"][-1]) for item in match["similar_contests"][:3] if item["contests"]
                ),
            }
        )
    return pd.DataFrame(rows)


def _presentational_historical_intelligence_dataframe(games: list[dict[str, Any]]) -> pd.DataFrame:
    dataframe = _historical_intelligence_dataframe(games)
    if dataframe.empty:
        return dataframe
    return dataframe.rename(
        columns={
            "historical_score": "Forca Historica",
            "profile_type": "Perfil Estrategico",
            "recurrence_score": "Tendencia",
            "partial_match_max": "Pico de Acertos",
            "partial_match_avg": "Media de Acertos",
            "jaccard_similarity": "Compatibilidade",
            "structural_rarity": "Exclusividade",
            "entropy_score": "Balanceamento",
            "block_density": "Distribuicao Estrutural",
        }
    )


def _presentational_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    if dataframe.empty:
        return dataframe
    presentational = dataframe.rename(
        columns={
            "historical_score": "Forca Historica",
            "profile_type": "Perfil Estrategico",
            "recurrence_score": "Tendencia",
            "partial_match_max": "Pico de Acertos",
            "partial_match_avg": "Media de Acertos",
            "jaccard_similarity": "Compatibilidade",
            "structural_rarity": "Exclusividade",
            "entropy_score": "Balanceamento",
            "block_density": "Distribuicao Estrutural",
            "first_name": "Nome",
            "whatsapp": "WhatsApp",
            "created_at": "Criado em",
            "origin": "Origem",
            "generations": "Geracoes",
            "checks": "Conferencias",
            "ml_activations": "ML",
            "last_generation_at": "Ultima geracao",
            "last_check_at": "Ultima conferencia",
            "lead": "Lead",
            "event_type": "Evento",
            "count": "Quantidade",
            "avg_duration_ms": "Tempo medio ms",
            "failures": "Falhas",
            "metric": "Metrica",
            "value": "Valor",
            "stage": "Etapa",
            "status": "Status",
            "source": "Fonte",
            "model_version": "Versao do modelo",
            "report_path": "Caminho do relatorio",
            "type": "Tipo",
            "path": "Caminho",
            "generated_by": "Gerado por",
            "interpretation": "Interpretacao",
            "confidence": "Confianca",
            "response_time_ms": "Tempo resposta ms",
            "ml_events": "Eventos ML",
            "report_events": "Eventos de relatorio",
            "snapshot_events": "Snapshots",
            "sqlite_size_bytes": "SQLite bytes",
            "total_runs": "Execucoes",
            "total_games": "Jogos totais",
            "prize_count": "Premios",
            "best_hits": "Melhor acerto",
            "latest_contest": "Ultimo concurso",
            "prize_tier": "Faixa",
            "prize_status": "Status premio",
            "hits": "Acertos",
            "matched_numbers": "Dezenas acertadas",
            "numbers": "Dezenas",
            "game_index": "Jogo",
            "contest_id": "Concurso",
            "total_hits": "Acertos totais",
            "best_hits": "Melhor acerto",
            "retention_rate": "Retencao",
            "average_hits": "Acertos medios",
            "historical_average_hits": "Media historica acertos",
            "historical_average_prizes": "Media historica premios",
            "prize_tiers": "Faixas premio",
            "prize_count": "Premios",
            "note": "Observacao",
            "layer": "Camada",
            "headline": "Titulo",
            "recommendation": "Recomendacao",
            "confidence": "Confianca",
            "trend": "Tendencia",
            "verdict_count": "Vereditos",
            "latest_status": "Status recente",
            "homepage_priority": "Prioridade homepage",
            "stability_note": "Nota de estabilidade",
            "runtime_profile": "Perfil runtime",
            "memory_depth": "Memoria",
            "timeline_depth": "Linha do tempo",
            "orchestration_state": "Orquestracao",
            "priority": "Prioridade",
            "context": "Contexto",
            "state": "Estado",
            "pattern": "Padrao",
            "persistent_changes": "Mudancas",
            "recurring_statuses": "Recorrencia",
            "runtime_perception": "Percepcao runtime",
            "presence_state": "Presenca",
            "coordinate_depth": "Profundidade de coordenacao",
        }
    )
    presentational = presentational.rename(
        columns={
            "status_transition": "Transicao",
            "average_hits": "Acertos medios",
            "stability_window_sd": "Estabilidade janela",
            "final_score_hit_correlation": "Correlacao score x acertos",
            "contests_analyzed": "Concursos analisados",
            "memory_state": "Estado memoria",
        }
    )
    value_maps: dict[str, dict[Any, Any]] = {
        "layer": {"executive": "Executiva", "historical": "Historica", "observability": "Observabilidade", "adaptive": "Adaptativa"},
        "component": {
            "executive_dashboard": "Visao geral",
            "executive_panel": "Painel executivo",
            "executive_summary": "Resumo",
            "live_status_header": "Estado atual",
            "institutional_timeline": "Linha do tempo",
            "live_analytical_intelligence": "Inteligencia viva",
            "operational_orchestration": "Orquestracao operacional",
            "adaptive_intelligence": "Inteligencia adaptativa",
            "historical_intelligence": "Historico analitico",
            "analytics_intelligence": "Analise inteligente",
            "observability": "Monitoramento",
        },
        "flow_name": {
            "generation": "Geracao",
            "check": "Conferencia",
            "benchmark": "Benchmark",
            "backtest": "Backtest",
            "calibration": "Calibracao",
            "report": "Relatorio",
            "observability": "Monitoramento",
        },
        "entity_type": {
            "generation_event": "Evento de geracao",
            "check_event": "Evento de conferencia",
            "runtime_execution": "Execucao runtime",
            "runtime_span": "Span runtime",
            "runtime_metric": "Metrica runtime",
            "runtime_lineage": "Lineage runtime",
            "runtime_snapshot": "Snapshot runtime",
        },
        "event_type": {
            "generation": "Geracao",
            "check": "Conferencia",
            "dashboard": "Dashboard",
            "load_draws": "Carga de acervo",
            "export": "Exportacao",
            "sqlite": "SQLite",
            "ml": "ML",
            "observability_boot": "Inicializacao observability",
            "sqlite_bootstrap": "Bootstrap SQLite",
            "snapshot::baseline": "Snapshot baseline",
            "snapshot::adaptive": "Snapshot adaptativo",
            "snapshot::runtime": "Snapshot runtime",
            "snapshot::drift": "Snapshot drift",
            "snapshot::confidence": "Snapshot confianca",
            "snapshot::health": "Snapshot saude",
            "state::baseline_state": "Estado baseline",
            "state::drift_state": "Estado drift",
            "state::confidence_state": "Estado confianca",
            "state::adaptive_state": "Estado adaptativo",
            "state::runtime_health": "Estado de saude",
            "replay::chronological": "Replay cronologico",
        },
        "source": {
            "observability": "Monitoramento",
            "adaptive_intelligence": "Inteligencia adaptativa",
            "historical_intelligence": "Historico analitico",
            "executive_dashboard": "Visao geral",
            "operational_monitoring": "Monitoramento operacional",
            "operational_orchestration": "Orquestracao operacional",
            "public_api": "API publica",
            "dashboard": "Dashboard",
            "generation": "Geracao",
            "check": "Conferencia",
            "sqlite": "SQLite",
            "ml": "ML",
        },
        "metric_type": {
            "gauge": "Indicador",
            "counter": "Contador",
            "timer": "Tempo",
        },
        "status": {"atencao": "atencao", "critical": "critico", "monitoring": "monitorando", "insuficiente": "insuficiente", "mixed": "mista", "saudavel": "saudavel", "running": "executando", "success": "sucesso", "failed": "falha", "ok": "ok", "active": "ativo", "idle": "inativo", "degraded": "degradado"},
        "trend": {"insuficiente": "insuficiente", "stable": "estavel", "observation": "observacao", "mixed": "mista"},
        "latest_status": {"mixed": "misto", "homepage em observacao": "homepage em observacao"},
        "homepage_priority": {"mixed": "mista", "homepage em observacao": "homepage em observacao"},
        "state": {"monitoring": "monitorando", "observation": "observacao"},
        "state_type": {
            "baseline_state": "Estado baseline",
            "drift_state": "Estado drift",
            "confidence_state": "Estado confianca",
            "adaptive_state": "Estado adaptativo",
            "runtime_health": "Estado de saude",
            "replay": "Replay",
        },
        "pattern": {"observacao governada": "observacao governada"},
        "runtime_perception": {"percepcao operacional em atencao": "percepcao operacional em atencao"},
        "presence_state": {"adaptativa": "adaptativa"},
        "snapshot_type": {
            "runtime": "Runtime",
            "generation": "Geracao",
            "check": "Conferencia",
            "observability": "Monitoramento",
        },
        "name": {
            "runtime_latency_ms": "Latencia runtime ms",
            "dashboard_load_ms": "Carga do dashboard ms",
            "generation_ms": "Tempo geracao ms",
            "check_ms": "Tempo conferencia ms",
            "ml_inference_ms": "Tempo ML ms",
            "report_ms": "Tempo relatorio ms",
            "avg_generation_ms": "Media geracao ms",
            "avg_check_ms": "Media conferencia ms",
            "avg_duration_ms": "Tempo medio ms",
        },
        "metric": {
            "avg_generation_ms": "Tempo medio geracao",
            "avg_check_ms": "Tempo medio conferencia",
            "ml_usage": "Uso ML",
            "generated_games": "Jogos gerados",
            "imported_contests": "Concursos importados",
            "snapshot_volume": "Volume de snapshots",
            "log_growth_today": "Crescimento de logs hoje",
            "sqlite_size_bytes": "Tamanho SQLite bytes",
        },
    }
    for column, replacements in value_maps.items():
        if column in presentational.columns:
            presentational[column] = presentational[column].replace(replacements)
    return presentational


def _historical_analytics(games: list[dict[str, Any]]) -> dict[str, Any]:
    matches = [_historical_match_engine(game["numbers"]) for game in games]
    return {
        "total_draws": int(_historical_dataset()["total_draws"]),
        "unique_games": sum(1 for match in matches if match["is_unique"]),
        "recurring_games": sum(1 for match in matches if not match["is_unique"]),
        "repeated_hits": sum(match["occurrences"] for match in matches),
        "avg_rarity": round(sum(match["rarity"] for match in matches) / len(matches), 4) if matches else 0.0,
        "avg_proximity": round(sum(match["proximity"] for match in matches) / len(matches), 4) if matches else 0.0,
        "profile_counts": {
            profile: sum(1 for match in matches if match["profile_type"] == profile)
            for profile in GENERATION_PROFILE_RATIOS
        },
        "profile_percentages": {
            profile: round(
                (sum(1 for match in matches if match["profile_type"] == profile) / len(matches)) * 100,
                2,
            )
            if matches
            else 0.0
            for profile in GENERATION_PROFILE_RATIOS
        },
    }


@st.cache_data(show_spinner=False, ttl=STREAMLIT_CACHE_TTL_SECONDS, max_entries=STREAMLIT_CACHE_MAX_ENTRIES)
def _analytics_base_tables() -> dict[str, pd.DataFrame]:
    dataset = _historical_dataset()
    frequency = pd.DataFrame(
        sorted(
            [
                {"dezena": number, "frequencia": count}
                for number, count in dataset["frequency"].items()
            ],
            key=lambda row: row["frequencia"],
            reverse=True,
        )
    )
    history_rows = []
    for draw in dataset["draws"]:
        numbers = _draw_numbers(draw)
        normalized = _normalize_numbers(numbers)
        history_rows.append(
            {
                "concurso": _draw_contest(draw),
                "dezenas": _format_numbers(numbers),
                "soma": sum(numbers),
                "pares": sum(1 for value in numbers if value % 2 == 0),
                "impares": sum(1 for value in numbers if value % 2 == 1),
                "repeticao": len(dataset["historical_map"].get(normalized, [])),
            }
        )
    history = pd.DataFrame(history_rows)
    if history.empty:
        history = pd.DataFrame(columns=["concurso", "dezenas", "soma", "pares", "impares", "repeticao"])
    return {
        "frequency": frequency,
        "history": history,
    }


def _frequency_chart() -> go.Figure:
    dataframe = _analytics_base_tables()["frequency"]
    figure = go.Figure(
        data=[go.Bar(x=dataframe["dezena"], y=dataframe["frequencia"], marker_color="#173b63")]
    )
    figure.update_layout(
        title="Frequência das dezenas",
        xaxis_title="Dezena",
        yaxis_title="Frequência",
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    return figure


def _delay_chart() -> go.Figure:
    stats = _cached_stats()["delay"]
    dataframe = _stats_table(stats, "dezena", limit=20)
    figure = go.Figure(
        data=[go.Bar(x=dataframe["dezena"], y=[float(v) for v in dataframe.iloc[:, 1]], marker_color="#1f5f8b")]
    )
    figure.update_layout(
        title="Atraso das dezenas",
        xaxis_title="Dezena",
        yaxis_title="Atraso",
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    return figure


def _sum_chart() -> go.Figure:
    history = _analytics_base_tables()["history"]
    figure = go.Figure(
        data=[go.Histogram(x=history["soma"], nbinsx=15, marker_color="#0f766e")]
    )
    figure.update_layout(
        title="Distribuição da soma",
        xaxis_title="Soma",
        yaxis_title="Quantidade",
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    return figure


def _odd_even_chart() -> go.Figure:
    history = _analytics_base_tables()["history"]
    figure = go.Figure()
    figure.add_trace(go.Bar(x=history["concurso"], y=history["pares"], name="Pares", marker_color="#173b63"))
    figure.add_trace(go.Bar(x=history["concurso"], y=history["impares"], name="Ímpares", marker_color="#9bbad1"))
    figure.update_layout(
        title="Pares e ímpares por concurso",
        barmode="group",
        xaxis_title="Concurso",
        yaxis_title="Quantidade",
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    return figure


def _recurrence_heatmap() -> go.Figure:
    history = _analytics_base_tables()["history"]
    if history.empty:
        return go.Figure()
    pivot = pd.pivot_table(
        history.assign(bucket=(history["concurso"] // 25) * 25),
        index="bucket",
        values="repeticao",
        aggfunc="mean",
    )
    figure = go.Figure(
        data=go.Heatmap(
            z=[pivot["repeticao"].tolist()],
            x=[str(value) for value in pivot.index.tolist()],
            y=["Recorrência"],
            colorscale="Blues",
        )
    )
    figure.update_layout(
        title="Heatmap de recorrência histórica",
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    return figure


def _pattern_heatmap() -> go.Figure:
    history = _analytics_base_tables()["history"]
    if history.empty:
        return go.Figure()
    rows = []
    for _, row in history.head(40).iterrows():
        numbers = [int(item) for item in str(row["dezenas"]).split()]
        rows.append(numbers[:10])
    matrix = rows if rows else [[0]]
    figure = go.Figure(
        data=go.Heatmap(z=matrix, colorscale="Viridis")
    )
    figure.update_layout(
        title="Heatmap de padrões",
        xaxis_title="Posição",
        yaxis_title="Linha",
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    return figure


def _temporal_heatmap() -> go.Figure:
    history = _analytics_base_tables()["history"]
    if history.empty:
        return go.Figure()
    history = history.copy()
    history["periodo"] = (history["concurso"] // 50) * 50
    pivot = pd.pivot_table(history, index="periodo", values="soma", aggfunc="mean")
    figure = go.Figure(
        data=go.Heatmap(z=[pivot["soma"].tolist()], x=[str(v) for v in pivot.index.tolist()], y=["Soma média"], colorscale="Cividis")
    )
    figure.update_layout(
        title="Heatmap temporal",
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    return figure


def _distribution_chart_advanced() -> go.Figure:
    history = _analytics_base_tables()["history"]
    figure = go.Figure(
        data=[go.Scatter(x=history["concurso"], y=history["soma"], mode="lines+markers", marker={"size": 6, "color": "#355c7d"})]
    )
    figure.update_layout(
        title="Distribuição histórica da soma",
        xaxis_title="Concurso",
        yaxis_title="Soma",
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    return figure



@st.cache_data(show_spinner=False, ttl=STREAMLIT_CACHE_TTL_SECONDS, max_entries=STREAMLIT_CACHE_MAX_ENTRIES)
def _ml_training_result(contests: int = 5, games_count: int = 8, pool_size: int = 24, history_window: int = 180, seed: int = 42) -> dict[str, Any]:
    start_time = time.monotonic()
    result = _safe_backtest(contests=contests, games_count=games_count, pool_size=pool_size, history_window=history_window, seed=seed)
    rows: list[dict[str, Any]] = []
    all_contests = [item["contest"] for item in result.contest_results]
    if not all_contests:
        empty_model = InterpretableLinearScoreML()
        empty_model = ensure_calibration(empty_model)
        validation_metrics = {
            "rows": 0,
            "splits": 0,
            "temporal_valid": True,
            "model_version": empty_model.model_version,
            "feature_schema_version": empty_model.feature_schema_version,
            "status": "degraded_no_backtest_candidates",
            "ml_runtime_status": "degraded",
            "fallback_used": True,
            "calibration_loaded": bool(getattr(empty_model, "calibration", None)),
        }
        payload = {
            "timestamp": _report_timestamp(),
            "model_version": empty_model.model_version,
            "feature_schema_version": empty_model.feature_schema_version,
            "engine_version": empty_model.model_version,
            "calibration_version": empty_model.calibration.get("version") if isinstance(empty_model.calibration, dict) else empty_model.model_version,
            "ml_runtime_status": "degraded",
            "fallback_used": True,
            "experiment_rows": 0,
            "walk_forward_splits": 0,
            "temporal_valid": True,
            "validation_metrics": validation_metrics,
            "training_summary": {},
            "calibration": {},
            "attribution": [],
            "profile_distribution": {},
            "ranking_strategy": "historical_recalibrated",
        }
        ml_report_paths = _save_ml_report(payload, pd.DataFrame(columns=["feature", "weight"]))
        ml_snapshot = _write_ml_snapshot("ml_model_snapshot", payload)
        return {
            "model": empty_model,
            "validation_metrics": validation_metrics,
            "scored_games": [],
            "reranked_games": [],
            "sample_row": {},
            "splits": [],
            "feature_rows": [],
            "ml_report_paths": ml_report_paths,
            "ml_snapshot": ml_snapshot,
            "payload": payload,
        }
    for contest_result in result.contest_results:
        contest = int(contest_result["contest"])
        for game in contest_result["games"]:
            rows.append(
                {
                    "sample_id": f"c{contest}_{'_'.join(map(str, game['numbers']))}",
                    "feature_cutoff_contest": max(1, contest - 1),
                    "label_contest": contest,
                    "target_hits": int(game["hits"]),
                    "features": extract_score_ml_features(game),
                }
            )

    calibration_report = calibrate_linear_score_ml(rows, target_field="target_hits")
    calibration_report = ensure_calibration(calibration_report)
    validated_rows = [row for row in rows if int(row["feature_cutoff_contest"]) < int(row["label_contest"])]
    unique_contests = sorted(set(all_contests))
    min_train_size = max(2, len(unique_contests) // 2) if len(unique_contests) > 2 else 2
    try:
        splits = build_walk_forward_splits(unique_contests, min_train_size=min_train_size, test_size=1, step_size=1)
    except Exception:
        splits = []
    scored_games = []
    for contest_result in result.contest_results:
        contest = int(contest_result["contest"])
        for game in contest_result["games"]:
            scored_games.append(attach_score_ml(dict(game), model=calibration_report))
    reranked = supervised_rerank_games(scored_games, model=calibration_report)
    sample_row = rows[0] if rows else {}
    feature_rows = []
    for feature_name, weight in calibration_report._weights().items():
        feature_values = [row["features"][feature_name] for row in rows] if rows else [0.0]
        feature_rows.append(
            {
                "feature": feature_name,
                "weight": round(weight, 4),
                "mean_value": round(sum(feature_values) / len(feature_values), 4),
                "importance": round(weight * (sum(feature_values) / len(feature_values)), 4),
                "contribution": round(weight * 100.0 * (sum(feature_values) / len(feature_values)), 4),
            }
        )
    validation_metrics = {
        "splits": len(splits),
        "rows": len(validated_rows),
        "temporal_valid": len(splits) > 0,
        "feature_schema_version": calibration_report.feature_schema_version,
        "model_version": calibration_report.model_version,
        "ml_runtime_status": "active",
        "fallback_used": False,
        "calibration_loaded": bool(getattr(calibration_report, "calibration", None)),
    }
    payload = {
        "timestamp": _report_timestamp(),
        "model_version": calibration_report.model_version,
        "feature_schema_version": calibration_report.feature_schema_version,
        "engine_version": calibration_report.model_version,
        "calibration_version": calibration_report.calibration.get("version") if isinstance(calibration_report.calibration, dict) else calibration_report.model_version,
        "ml_runtime_status": "active",
        "fallback_used": False,
        "experiment_rows": len(rows),
        "walk_forward_splits": len(splits),
        "temporal_valid": validation_metrics["temporal_valid"],
        "validation_metrics": validation_metrics,
        "training_summary": dict(calibration_report.training_summary or {}),
        "features": feature_rows,
        "profile_distribution": {},
        "ranking_strategy": "historical_recalibrated",
    }
    duration_ms = (time.monotonic() - start_time) * 1000.0
    ml_report_paths = _save_ml_report(payload, pd.DataFrame(feature_rows))
    ml_snapshot = _write_ml_snapshot(
        "ml_model_snapshot",
        {
            **payload,
            "calibration": dict(calibration_report.calibration or {}),
            "attribution": [item.as_dict() for item in calibration_report.attribution],
            "sample_row": sample_row,
        },
    )
    _record_operational_log("ml", "success", duration_ms, {"rows": len(rows), "splits": len(splits), "model_version": calibration_report.model_version})
    _record_performance_metric("ml_inference_ms", duration_ms, {"rows": len(rows), "splits": len(splits)})
    _record_audit_trail("ml_snapshot", artifact_path=str(ml_snapshot), context={"model_version": calibration_report.model_version})
    _invalidate_runtime_cache()
    return {
        "result": result,
        "rows": rows,
        "model": calibration_report,
        "scored_games": scored_games,
        "reranked_games": reranked,
        "validation_metrics": validation_metrics,
        "sample_row": sample_row,
        "splits": [split.as_dict() for split in splits],
        "feature_rows": feature_rows,
        "ml_report_paths": ml_report_paths,
        "ml_snapshot": ml_snapshot,
        "payload": payload,
        "runtime": {
            "engine_version": calibration_report.model_version,
            "ml_runtime_status": "active",
            "fallback_used": False,
            "calibration_loaded": True,
        },
    }


def _ml_features_table(model: InterpretableLinearScoreML) -> pd.DataFrame:
    weights = model._weights()
    return pd.DataFrame(
        [
            {"feature": name, "weight": round(weight, 4)}
            for name, weight in weights.items()
        ]
    )


def _recurrence_table() -> pd.DataFrame:
    dataset = _historical_dataset()
    rows = [
        {
            "dezenas": _format_numbers(list(combo)),
            "ocorrencias": len(contests),
            "ultimo_concurso": contests[-1] if contests else None,
            "raridade": round(1.0 - (len(contests) / dataset["total_draws"]), 4) if dataset["total_draws"] else 1.0,
        }
        for combo, contests in sorted(
            dataset["historical_map"].items(),
            key=lambda item: len(item[1]),
            reverse=True,
        )[:20]
    ]
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False, ttl=STREAMLIT_CACHE_TTL_SECONDS, max_entries=STREAMLIT_CACHE_MAX_ENTRIES)
def _observability_tables() -> dict[str, pd.DataFrame]:
    try:
        logs = pd.read_sql_query(
            """
            SELECT * FROM operational_logs
            ORDER BY created_at DESC, id DESC
            LIMIT 200
            """,
            conn,
        )
    except Exception:
        logs = pd.DataFrame(columns=["id", "event_type", "status", "duration_ms", "context_json", "created_at"])

    try:
        audit = pd.read_sql_query(
            """
            SELECT * FROM audit_trail
            ORDER BY created_at DESC, id DESC
            LIMIT 200
            """,
            conn,
        )
    except Exception:
        audit = pd.DataFrame(columns=["id", "action_type", "actor", "artifact_path", "context_json", "created_at"])

    return {"logs": logs, "audit": audit}


def _runtime_health() -> dict[str, Any]:
    logs = _observability_tables()["logs"]
    generation_logs = logs[logs["event_type"] == "generation"] if not logs.empty else pd.DataFrame()
    check_logs = logs[logs["event_type"] == "check"] if not logs.empty else pd.DataFrame()
    ml_logs = logs[logs["event_type"] == "ml"] if not logs.empty else pd.DataFrame()
    report_logs = logs[logs["event_type"] == "report"] if not logs.empty else pd.DataFrame()
    snapshot_logs = logs[logs["event_type"].str.contains("snapshot", na=False)] if not logs.empty else pd.DataFrame()
    sqlite_ok = _sqlite_health_check()
    ml_failures = int((ml_logs["status"] == "failed").sum()) if not ml_logs.empty else 0
    generation_avg = round(float(generation_logs["duration_ms"].dropna().mean()), 2) if not generation_logs.empty and generation_logs["duration_ms"].notna().any() else _table_average_ms("generation_events")
    check_avg = round(float(check_logs["duration_ms"].dropna().mean()), 2) if not check_logs.empty and check_logs["duration_ms"].notna().any() else _table_average_ms("check_events")
    ml_state = ml_heartbeat()
    engine_version = str(ml_state.get("engine_version") or "historical_recalibrated_v2")
    model_version = str(ml_state.get("model_version") or "historical_recalibrated_v2")
    return {
        "response_time_ms": round(float(logs["duration_ms"].dropna().mean()), 2) if not logs.empty and logs["duration_ms"].notna().any() else 0.0,
        "total_runs": int(len(logs)),
        "failures": int((logs["status"] == "failed").sum()) if not logs.empty else 0,
        "avg_generation_ms": generation_avg,
        "avg_check_ms": check_avg,
        "ml_events": int(len(ml_logs)),
        "report_events": int(len(report_logs)),
        "snapshot_events": int(len(snapshot_logs)),
        "snapshot_files": _snapshot_count(),
        "sqlite_status": "ok" if sqlite_ok else "failed",
        "runtime_status": "degraded" if not logs.empty and (logs["status"] == "failed").any() else "ok",
        "ml_status": "failed" if ml_failures else str(ml_state.get("status") or ("active" if not ml_logs.empty else "idle")),
        "engine_version": engine_version,
        "model_version": model_version,
        "fallback_used": bool(ml_state.get("fallback_used", False)),
        "snapshot_version": "v2" if _snapshot_count() else "v1_legacy",
        "cache_status": "fresh" if logs.empty or logs["created_at"].notna().any() else "stale",
        "cache_hit": 0,
        "cache_miss": 0,
        "cache_stale": 0,
        "cache_regenerated": 0,
        "sqlite_size_bytes": _sqlite_size_bytes(),
        "calibration_loaded": bool(ml_state.get("calibration_loaded", True)),
        "last_runtime_update": str(ml_state.get("last_update") or (logs["created_at"].max() if not logs.empty else "")),
    }


def _table_average_ms(table_name: str) -> float:
    if table_name not in {"generation_events", "check_events"}:
        return 0.0
    value = _query_scalar(f"SELECT AVG(execution_time_ms) FROM {table_name}", default=0.0)
    try:
        return round(float(value or 0.0), 2)
    except Exception:
        return 0.0


def _snapshot_count() -> int:
    try:
        _ensure_reports_dirs()
        return len(list(REPORTS_SNAPSHOTS_DIR.glob("*.json"))) + len(list(ML_SNAPSHOTS_DIR.glob("*.json")))
    except Exception:
        return 0


def _generation_pipeline_snapshot_dir() -> Path:
    return REPORTS_DIR / "snapshots" / "generation_pipeline"


def _generation_pipeline_trace_table() -> pd.DataFrame:
    trace_dir = _generation_pipeline_snapshot_dir()
    if not trace_dir.exists():
        return pd.DataFrame(columns=["stage", "timestamp", "games", "rarity_std", "recurrence_density", "sequence_pressure", "normalization_pressure"])

    rows = []
    for path in sorted(trace_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)[:20]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        metrics = payload.get("metrics") or {}
        rows.append(
            {
                "stage": payload.get("stage", path.stem),
                "timestamp": payload.get("timestamp", ""),
                "games": payload.get("games", 0),
                "rarity_std": metrics.get("rarity_std", 0.0),
                "recurrence_density": metrics.get("recurrence_density", 0.0),
                "sequence_pressure": metrics.get("sequence_pressure", 0.0),
                "normalization_pressure": metrics.get("normalization_pressure", 0.0),
            }
        )
    return pd.DataFrame(rows)


def _pressure_heatmap_table() -> pd.DataFrame:
    rows = pressure_heatmap()
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["filter", "discarded", "reason"])


def _survival_summary_table() -> pd.DataFrame:
    rows = survival_summary()
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["stage", "recorrente", "hibrido", "caotico", "total"])


def _diversity_collapse_table() -> pd.DataFrame:
    rows = diversity_collapse_report()
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["stage", "diversity_score", "rarity_std", "recurrence_density", "structural_entropy", "normalization_pressure"])


def _normalization_comparison_table() -> pd.DataFrame:
    rows = normalization_comparison_report()
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["mode", "stage", "rarity_std", "recurrence_density", "structural_entropy", "cluster_aggressiveness", "normalization_pressure"])


def _pipeline_divergence_table() -> pd.DataFrame:
    rows = pipeline_divergence_score()
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["mode", "stage", "divergence_score"])


def _destructive_filters_table() -> pd.DataFrame:
    rows = destructive_filters_report()
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["filter", "discarded", "diversity_collapse", "recurrence_kill", "chaos_kill", "divergence_contribution", "classification", "reference_stage"])


def _executive_behavioral_table() -> pd.DataFrame:
    rows = executive_behavioral_report()
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["filter", "classification", "impact", "diversity_collapse", "recurrence_kill", "chaos_kill", "divergence_contribution"])


def _filter_profile_damage_table() -> pd.DataFrame:
    rows = filter_profile_damage_report()
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["filter", "recorrente", "hibrido", "caotico"])


def _behavior_recovery_table() -> pd.DataFrame:
    rows = behavior_recovery_timeline()
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["mode", "stage", "recurrence_recovery", "chaos_recovery", "variance_recovery", "recovery_score"])


def _safe_recovery_zone_table() -> pd.DataFrame:
    return pd.DataFrame(safe_recovery_zone())


def _historical_adherence_table() -> pd.DataFrame:
    rows = historical_adherence_score()
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["mode", "stage", "historical_adherence_score"])


def _profile_stability_table() -> pd.DataFrame:
    rows = profile_stability_score()
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["stage", "recorrente", "hibrido", "caotico", "profile_stability_score"])


def _pressure_sensitivity_table() -> pd.DataFrame:
    rows = pressure_sensitivity_report()
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["filter", "pressure_sensitivity", "classification"])


def _recovery_decision_protocol_table() -> pd.DataFrame:
    return pd.DataFrame(recovery_decision_protocol())


def _behavior_drift_table() -> pd.DataFrame:
    rows = behavior_drift_report()
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["mode", "stage", "behavior_drift_score"])


def _golden_baselines_table() -> pd.DataFrame:
    return pd.DataFrame(golden_baselines())


def _false_recovery_table() -> pd.DataFrame:
    rows = false_recovery_report()
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["mode", "stage", "false_recovery"])


def _experiment_baseline_table() -> pd.DataFrame:
    return pd.DataFrame(experiment_baseline_report())


def _experiment_comparison_table() -> pd.DataFrame:
    rows = experiment_comparison_report()
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["mode", "stage", "behavior_integrity_recovery"])


def _recovery_plateau_table() -> pd.DataFrame:
    rows = recovery_plateau_detection()
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["mode", "stage", "plateau_detected"])


def _experiment_01_table() -> pd.DataFrame:
    rows = experiment_01_report()
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["experiment", "mode", "stage", "recovery", "adherence", "drift", "false_recovery", "profile_stability"])


def _marginal_recovery_gain_table() -> pd.DataFrame:
    rows = marginal_recovery_gain()
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["from_stage", "to_stage", "marginal_recovery_gain", "adherence_delta", "drift_delta"])


def _analytical_intelligence_summary() -> pd.DataFrame:
    report = build_analytical_intelligence()
    summary = report.get("analytical_summary", {})
    rows = [
        {"metric": "structural_health", "value": summary.get("structural_health", 0.0), "interpretation": summary.get("interpretation", ""), "confidence": summary.get("confidence", "")},
        {"metric": "coverage_10", "value": summary.get("coverage_10", 0.0), "interpretation": "cobertura longitudinal em 10+", "confidence": summary.get("confidence", "")},
        {"metric": "coverage_11", "value": summary.get("coverage_11", 0.0), "interpretation": "cobertura longitudinal em 11+", "confidence": summary.get("confidence", "")},
        {"metric": "average_hits", "value": summary.get("average_hits", 0.0), "interpretation": "média operacional longitudinal", "confidence": summary.get("confidence", "")},
        {"metric": "drift", "value": summary.get("drift", 0.0), "interpretation": "interpretação de drift longitudinal", "confidence": summary.get("confidence", "")},
        {"metric": "runtime_profile", "value": summary.get("runtime_profile", ""), "interpretation": "perfil de execução", "confidence": summary.get("confidence", "")},
    ]
    return pd.DataFrame(rows)


def _analytical_intelligence_insights() -> pd.DataFrame:
    report = build_analytical_intelligence()
    rows = report.get("insights", [])
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["metric", "value", "interpretation", "confidence"])


def _analytical_intelligence_comparisons() -> pd.DataFrame:
    report = build_analytical_intelligence()
    rows = report.get("comparisons", [])
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["label", "baseline", "compared", "delta", "interpretation"])


def _analytical_intelligence_timeline() -> pd.DataFrame:
    report = build_analytical_intelligence()
    rows = report.get("comparisons", [])
    summary = report.get("analytical_summary", {})
    if not rows:
        return pd.DataFrame(
            [
                {
                    "checkpoint": "-",
                    "structural_health": summary.get("structural_health", 0.0),
                    "coverage_10": summary.get("coverage_10", 0.0),
                    "coverage_11": summary.get("coverage_11", 0.0),
                    "drift": summary.get("drift", 0.0),
                    "interpretation": summary.get("interpretation", ""),
                }
            ]
        )
    timeline = []
    for index, comparison in enumerate(rows, start=1):
        timeline.append(
            {
                "checkpoint": f"comparativo_{index:02d}",
                "structural_health": summary.get("structural_health", 0.0),
                "coverage_10": summary.get("coverage_10", 0.0),
                "coverage_11": summary.get("coverage_11", 0.0),
                "drift": summary.get("drift", 0.0),
                "interpretation": comparison.get("interpretation", ""),
            }
        )
    return pd.DataFrame(timeline)


def _institutional_analytical_timeline() -> pd.DataFrame:
    report = load_institutional_analytical_timeline()
    if not report:
        report = ensure_institutional_analytical_timeline(report_dir=REPORTS_DIR / "analytics")
    rows = report.get("timeline", [])
    if not rows:
        summary = report.get("summary", {})
        return pd.DataFrame(
            [
                {
                    "created_at": "-",
                    "status": summary.get("latest_status", ""),
                    "previous_status": "",
                    "status_transition": summary.get("latest_transition", ""),
                    "headline": summary.get("latest_headline", ""),
                    "recommendation": summary.get("latest_recommendation", ""),
                    "trend": summary.get("trend", ""),
                    "verdict_count": summary.get("verdict_count", 0),
                    "confidence": "",
                    "source": report.get("source", ""),
                }
            ]
        )
    timeline = []
    for row in rows:
        timeline.append(
            {
                "created_at": row.get("created_at", ""),
                "status": row.get("status", ""),
                "previous_status": row.get("previous_status", ""),
                "status_transition": row.get("status_transition", ""),
                "headline": row.get("headline", ""),
                "recommendation": row.get("recommendation", ""),
                "trend": row.get("trend", ""),
                "verdict_count": row.get("verdict_count", 0),
                "confidence": row.get("confidence", ""),
                "source": row.get("source", ""),
            }
        )
    return pd.DataFrame(timeline)


def _executive_analytical_summary() -> pd.DataFrame:
    report = build_executive_analytical_report()
    rows = [
        {"field": "status", "value": report.get("status", "")},
        {"field": "headline", "value": report.get("headline", "")},
        {"field": "recommendation", "value": report.get("recommendation", "")},
        {"field": "confidence", "value": report.get("confidence", "")},
        {"field": "structural_health", "value": report.get("structural_health", 0.0)},
        {"field": "drift", "value": report.get("drift", 0.0)},
        {"field": "coverage_11", "value": report.get("coverage_11", 0.0)},
        {"field": "baseline_mode", "value": report.get("baseline_mode", "")},
    ]
    return pd.DataFrame(rows)


def _analytical_insight_cards() -> dict[str, Any]:
    report = build_executive_analytical_report()
    return {
        "status": report.get("status", ""),
        "headline": report.get("headline", ""),
        "recommendation": report.get("recommendation", ""),
        "confidence": report.get("confidence", ""),
        "structural_health": report.get("structural_health", 0.0),
        "drift": report.get("drift", 0.0),
        "coverage_11": report.get("coverage_11", 0.0),
    }


def _executive_header_block() -> None:
    cards = _analytical_insight_cards()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Saúde", f"{float(cards.get('structural_health', 0.0)):.2f}")
    col2.metric("Cobertura 11+", f"{float(cards.get('coverage_11', 0.0)):.2f}")
    col3.metric("Status", str(cards.get("status", "-")))
    col4.metric("Confiança", str(cards.get("confidence", "-")))
    st.info(
        f"{cards.get('headline', '-')} | {cards.get('recommendation', '-')} | drift={float(cards.get('drift', 0.0)):.2f}"
    )


def _institutional_historical_table() -> pd.DataFrame:
    report = build_institutional_historical_intelligence()
    summary = report.get("summary", {})
    timeline = report.get("timeline", [])
    rows = [
        {"metric": "trend", "value": summary.get("trend", "")},
        {"metric": "verdict_count", "value": summary.get("verdict_count", 0)},
        {"metric": "latest_status", "value": summary.get("latest_status", "")},
        {"metric": "latest_headline", "value": summary.get("latest_headline", "")},
        {"metric": "latest_recommendation", "value": summary.get("latest_recommendation", "")},
        {"metric": "stability_trend", "value": summary.get("stability_trend", 0.0)},
        {"metric": "drift_trend", "value": summary.get("drift_trend", 0.0)},
        {"metric": "confidence_trend", "value": summary.get("confidence_trend", 0.0)},
        {"metric": "source", "value": report.get("source", "")},
        {"metric": "timeline_preview", "value": len(timeline)},
    ]
    return pd.DataFrame(rows)


def _institutional_analytics_snapshot_table() -> pd.DataFrame:
    snapshot_path = REPORTS_DIR / "analytics" / "institutional_analytics_snapshot.json"
    payload = load_institutional_analytics_snapshot(snapshot_path)
    if not payload:
        payload = publish_institutional_analytics(report_dir=REPORTS_DIR / "analytics")
    executive = payload.get("executive_report", build_executive_analytical_report())
    historical = payload.get("historical_report", build_institutional_historical_intelligence())
    rows = [
        {"metric": "executive_status", "value": executive.get("status", "")},
        {"metric": "executive_headline", "value": executive.get("headline", "")},
        {"metric": "executive_recommendation", "value": executive.get("recommendation", "")},
        {"metric": "historical_trend", "value": historical.get("summary", {}).get("trend", "")},
        {"metric": "historical_verdict_count", "value": historical.get("summary", {}).get("verdict_count", 0)},
        {"metric": "latest_status", "value": historical.get("summary", {}).get("latest_status", "")},
        {"metric": "latest_recommendation", "value": historical.get("summary", {}).get("latest_recommendation", "")},
    ]
    return pd.DataFrame(rows)


def _sqlite_size_bytes() -> int:
    try:
        return DB_PATH.stat().st_size if DB_PATH.exists() else 0
    except Exception:
        return 0


def _query_scalar(query: str, params: tuple[Any, ...] = (), default: Any = 0) -> Any:
    try:
        row = _sqlite_execute_safe(query, params)
        value = row.fetchone()[0] if row else default
        return default if value is None else value
    except Exception:
        return default


def _operational_metrics() -> dict[str, Any]:
    generation_total = int(_query_scalar("SELECT COUNT(*) FROM generation_events"))
    generation_days = int(_query_scalar("SELECT COUNT(DISTINCT DATE(created_at)) FROM generation_events"))
    check_total = int(_query_scalar("SELECT COUNT(*) FROM check_events"))
    ml_usage = int(_query_scalar("SELECT COUNT(*) FROM generation_events WHERE ml_enabled = 1"))
    imported_total = int(_query_scalar("SELECT COUNT(*) FROM imported_contests"))
    generated_games_total = int(_query_scalar("SELECT COUNT(*) FROM generated_games"))
    logs_total = int(_query_scalar("SELECT COUNT(*) FROM operational_logs"))
    logs_today = int(_query_scalar("SELECT COUNT(*) FROM operational_logs WHERE DATE(created_at) = DATE('now')"))
    return {
        "daily_generation_average": round(generation_total / generation_days, 2) if generation_days else 0.0,
        "check_volume": check_total,
        "ml_usage": ml_usage,
        "imported_contests": imported_total,
        "generated_games": generated_games_total,
        "snapshot_volume": _snapshot_count(),
        "log_growth_today": logs_today,
        "log_total": logs_total,
        "sqlite_size_bytes": _sqlite_size_bytes(),
    }


def _source_of_truth_map() -> pd.DataFrame:
    rows = [
        {"component": "Dashboard.generation_count", "source": "generation_events", "notes": "live COUNT(*)"},
        {"component": "Dashboard.check_count", "source": "check_events", "notes": "live COUNT(*)"},
        {"component": "Dashboard.total_games", "source": "generated_games", "notes": "live COUNT(*) generated_games rows"},
        {"component": "Dashboard.last_contest", "source": "check_events -> imported_contests -> historical CSV", "notes": "MAX(contest_id) with imported contest fallback"},
        {"component": "Historico analitico", "source": "generation_events + check_events + historical draws", "notes": "no stale snapshot dependency"},
        {"component": "Analise inteligente", "source": "generation_events + generated_games + imported_contests", "notes": "live tables and draw history"},
        {"component": "Auditoria tecnica", "source": "ml_runtime_state + operational_logs", "notes": "latest runtime state"},
        {"component": "Monitoramento", "source": "operational_logs + audit_trail", "notes": "live runtime signals"},
        {"component": "PerformanceTracking", "source": "operational_logs", "notes": "durations per event"},
        {"component": "CloudMonitoring", "source": "operational_logs + sqlite file", "notes": "runtime health and size"},
    ]
    return pd.DataFrame(rows)


def _performance_metrics_table() -> pd.DataFrame:
    rows = []
    logs = _observability_tables()["logs"]
    families = {
        "generation": "tempo geração",
        "check": "tempo conferência",
        "analytics": "tempo analytics",
        "report": "tempo relatórios",
        "ml": "tempo inferência ML",
        "dashboard": "tempo carregamento dashboard",
    }
    for event_type, label in families.items():
        subset = logs[logs["event_type"] == event_type] if not logs.empty else pd.DataFrame()
        rows.append(
            {
                "metric": label,
                "avg_ms": round(float(subset["duration_ms"].dropna().mean()), 2) if not subset.empty and subset["duration_ms"].notna().any() else 0.0,
                "events": int(len(subset)),
                "failures": int((subset["status"] == "failed").sum()) if not subset.empty else 0,
            }
        )
    return pd.DataFrame(rows)


def _alert_contracts() -> pd.DataFrame:
    health = _runtime_health()
    health = {
        "avg_generation_ms": 0.0,
        "avg_check_ms": 0.0,
        "sqlite_size_bytes": 0,
        "failures": 0,
        "ml_status": "idle",
        "runtime_status": "unknown",
        **health,
    }
    metrics = _operational_metrics()
    checks = [
        ("tempo excessivo geração", health["avg_generation_ms"] <= ALERT_GENERATION_MS, health["avg_generation_ms"], ALERT_GENERATION_MS),
        ("tempo excessivo conferência", health["avg_check_ms"] <= ALERT_CHECK_MS, health["avg_check_ms"], ALERT_CHECK_MS),
        ("crescimento anormal logs", metrics["log_growth_today"] <= ALERT_LOG_GROWTH_EVENTS, metrics["log_growth_today"], ALERT_LOG_GROWTH_EVENTS),
        ("crescimento SQLite", health["sqlite_size_bytes"] <= ALERT_SQLITE_SIZE_BYTES, health["sqlite_size_bytes"], ALERT_SQLITE_SIZE_BYTES),
        ("falhas repetidas", health["failures"] < ALERT_REPEATED_FAILURES, health["failures"], ALERT_REPEATED_FAILURES),
        ("falhas ML", health["ml_status"] != "failed", health["ml_status"], "ok/idle"),
        ("falhas runtime", health["runtime_status"] != "degraded", health["runtime_status"], "ok"),
    ]
    return pd.DataFrame(
        [
            {
                "contract": name,
                "status": "ok" if ok else "alert",
                "value": value,
                "threshold": threshold,
            }
            for name, ok, value, threshold in checks
        ]
    )


def _cloud_failure_table() -> pd.DataFrame:
    logs = _observability_tables()["logs"]
    event_types = ("dashboard", "load_draws", "export", "sqlite", "ml")
    if logs.empty:
        return pd.DataFrame([{"event_type": event_type, "failures": 0} for event_type in event_types])
    failed = logs[logs["status"] == "failed"]
    rows = []
    for event_type in event_types:
        rows.append(
            {
                "event_type": event_type,
                "failures": int((failed["event_type"] == event_type).sum()) if not failed.empty else 0,
            }
        )
    return pd.DataFrame(rows)


def _observability_metrics_table() -> pd.DataFrame:
    logs = _observability_tables()["logs"]
    if logs.empty:
        return pd.DataFrame(columns=["event_type", "count", "avg_duration_ms"])
    grouped = logs.groupby("event_type", dropna=False)
    return pd.DataFrame(
        [
            {
                "event_type": event_type,
                "count": len(group),
                "avg_duration_ms": round(float(group["duration_ms"].dropna().mean()), 2) if group["duration_ms"].notna().any() else 0.0,
            }
            for event_type, group in grouped
        ]
    ).sort_values("count", ascending=False)


def render_observability_page() -> None:
    with st.container(border=True):
        _section_header("Monitoramento", "Logs institucionais, saúde cloud, auditoria e eventos operacionais recentes.")
        stabilization = load_observational_stabilization_report()
        if not stabilization:
            stabilization = persist_observational_stabilization_report()
        stabilization_report = stabilization.get("report", {})
        summary = stabilization_report.get("summary", {})
        counts = stabilization_report.get("counts", {})
        st.subheader("Observational stabilization")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Homepage", summary.get("homepage_priority", "-"))
        col2.metric("Estabilidade", summary.get("stability_note", "-"))
        col3.metric("Snapshot", "ok" if summary.get("institutional_snapshot_ready") else "pending")
        col4.metric("Linha do tempo", "ok" if summary.get("institutional_timeline_ready") else "pending")
        st.caption(
            f"Gerações={counts.get('generation_events', 0)}"
            f" | Conferências={counts.get('check_events', 0)}"
            f" | Jogos={counts.get('generated_games', 0)}"
            f" | Concursos={counts.get('imported_contests', 0)}"
        )
        observability_dashboard = build_institutional_observability_dashboard()
        observability_summary = observability_dashboard.get("summary", {})
        observability_health = observability_dashboard.get("runtime_health", {})
        live_telemetry = build_live_telemetry_snapshot()
        st.subheader("Painel executivo de observabilidade")
        dash_col1, dash_col2, dash_col3, dash_col4 = st.columns(4)
        dash_col1.metric("Execuções", observability_summary.get("execution_count", 0))
        dash_col2.metric("Spans", observability_summary.get("span_count", 0))
        dash_col3.metric("Metricas", observability_summary.get("metric_count", 0))
        dash_col4.metric("Snapshots", observability_summary.get("snapshot_count", 0))
        st.caption(
            f"Fluxo recente: {observability_summary.get('latest_flow', '-')}"
            f" | Status: {observability_summary.get('latest_status', '-')}"
            f" | Duração média: {observability_summary.get('average_execution_duration_ms', 0.0):.2f} ms"
        )
        st.dataframe(
            _presentational_dataframe(
                pd.DataFrame(
                    [
                        {
                            "metric": "confidence_drift",
                            "value": len(observability_dashboard.get("drift_evolution", [])),
                            "interpretation": "Eventos de drift rastreados",
                            "confidence": observability_health.get("latest_status", "-"),
                        },
                        {
                            "metric": "confidence_stability",
                            "value": len(observability_dashboard.get("confidence_stability", [])),
                            "interpretation": "Eventos de estabilidade rastreados",
                            "confidence": observability_health.get("latest_status", "-"),
                        },
                        {
                            "metric": "structural_integrity",
                            "value": 1.0 if observability_dashboard.get("structural_integrity", {}).get("ok") else 0.0,
                            "interpretation": "Integridade estrutural persistida",
                            "confidence": "ok" if observability_dashboard.get("structural_integrity", {}).get("ok") else "alerta",
                        },
                    ]
            )
            ),
            hide_index=True,
            use_container_width=True,
        )
        st.subheader("Telemetria viva")
        live_cols = st.columns(4)
        live_cols[0].metric("Estado", live_telemetry.get("summary", {}).get("telemetry_status", "-"))
        live_cols[1].metric("Runtime", live_telemetry.get("summary", {}).get("runtime_awareness", "-"))
        live_cols[2].metric("Atividade", live_telemetry.get("summary", {}).get("activity_level", "-"))
        live_cols[3].metric("Execucao", live_telemetry.get("summary", {}).get("latest_execution_id", "-"))
        st.dataframe(
            _presentational_dataframe(
                pd.DataFrame(live_telemetry.get("live_signals", [])),
            ),
            hide_index=True,
            use_container_width=True,
        )
        live_alerts = live_telemetry.get("alerts", [])
        if live_alerts:
            st.caption("Alertas executivos")
            alert_rows = pd.DataFrame(live_alerts)
            st.dataframe(
                _presentational_dataframe(alert_rows),
                hide_index=True,
                use_container_width=True,
            )
        operational_health = build_operational_health_snapshot()
        st.subheader("Saude operacional")
        health_cols = st.columns(4)
        health_cols[0].metric("Status", operational_health.get("status", "-"))
        health_cols[1].metric("Score", f"{float(operational_health.get('score', 0.0)):.2f}")
        health_cols[2].metric("Sinais", operational_health.get("active_signals", 0))
        health_cols[3].metric("Alertas", len(operational_health.get("alerts", [])))
        st.caption(
            f"Runtime: {operational_health.get('runtime_awareness', '-')}"
            f" | Telemetria: {operational_health.get('telemetry_status', '-')}"
            f" | Execucao: {operational_health.get('summary', {}).get('latest_execution_id', '-')}"
        )
        if operational_health.get("alerts"):
            st.dataframe(
                _presentational_dataframe(pd.DataFrame(operational_health.get("alerts", []))),
                hide_index=True,
                use_container_width=True,
            )
        runtime_story = build_runtime_storytelling()
        st.subheader("Narrativa operacional viva")
        story_cols = st.columns(3)
        story_cols[0].metric("Headline", runtime_story.get("headline", "-"))
        story_cols[1].metric("Saude", runtime_story.get("summary", {}).get("health_status", "-"))
        story_cols[2].metric("Sinais", runtime_story.get("summary", {}).get("active_signals", 0))
        st.caption(
            f"Telemetria: {runtime_story.get('summary', {}).get('telemetry_status', '-')}"
            f" | Runtime: {runtime_story.get('summary', {}).get('runtime_awareness', '-')}"
        )
        st.write(" | ".join(runtime_story.get("narrative", [])))
        if runtime_story.get("timeline"):
            st.dataframe(
                _presentational_dataframe(pd.DataFrame(runtime_story.get("timeline", []))),
                hide_index=True,
                use_container_width=True,
            )
        live_memory = build_live_operational_memory()
        st.subheader("Memoria operacional viva")
        memory_cols = st.columns(4)
        memory_cols[0].metric("Estado", live_memory.get("summary", {}).get("memory_status", "-"))
        memory_cols[1].metric("Snapshots", live_memory.get("summary", {}).get("snapshot_count", 0))
        memory_cols[2].metric("Estados", live_memory.get("summary", {}).get("state_count", 0))
        memory_cols[3].metric("Replay", "sim" if live_memory.get("summary", {}).get("replay_ready") else "nao")
        st.caption(
            f"Execucao: {live_memory.get('execution_id', '-')}"
            f" | Headline: {live_memory.get('headline', '-')}"
        )
        memory_story = live_memory.get("story", {})
        if memory_story.get("narrative"):
            st.write(" | ".join(memory_story.get("narrative", [])))
        governance = build_real_time_governance()
        st.subheader("Governanca em tempo real")
        gov_cols = st.columns(4)
        gov_cols[0].metric("Status", governance.get("status", "-"))
        gov_cols[1].metric("Score", f"{float(governance.get('score', 0.0)):.2f}")
        gov_cols[2].metric("Policy", "ok" if governance.get("policy_allowed") else "review")
        gov_cols[3].metric("Alertas", len(governance.get("alerts", [])))
        st.caption(
            f"Saude: {governance.get('summary', {}).get('health_status', '-')}"
            f" | Bloqueios: {governance.get('summary', {}).get('blocking_count', 0)}"
        )
        if governance.get("alerts"):
            st.dataframe(
                _presentational_dataframe(pd.DataFrame(governance.get("alerts", []))),
                hide_index=True,
                use_container_width=True,
            )
        operational_experience = build_operational_experience()
        st.subheader("Experiencia operacional")
        exp_cols = st.columns(4)
        exp_cols[0].metric("Estado", operational_experience.get("state", "-"))
        exp_cols[1].metric("Memoria", operational_experience.get("summary", {}).get("memory_status", "-"))
        exp_cols[2].metric("Governanca", operational_experience.get("summary", {}).get("health_status", "-"))
        exp_cols[3].metric("Telemetria", operational_experience.get("summary", {}).get("telemetry_status", "-"))
        st.caption(" | ".join(operational_experience.get("narrative", [])))
        live_presence = build_live_institutional_presence()
        st.subheader("Presenca institucional viva")
        presence_cols = st.columns(4)
        presence_cols[0].metric("Presenca", live_presence.get("presence", "-"))
        presence_cols[1].metric("Estado", live_presence.get("summary", {}).get("state", "-"))
        presence_cols[2].metric("Memoria", live_presence.get("summary", {}).get("memory_status", "-"))
        presence_cols[3].metric("Governanca", live_presence.get("summary", {}).get("health_status", "-"))
        st.caption(" | ".join(live_presence.get("narrative", [])))
        assistance = build_executive_assistance()
        st.subheader("Assistencia executiva")
        assist_cols = st.columns(4)
        assist_cols[0].metric("Estado", assistance.get("state", "-"))
        assist_cols[1].metric("Presenca", assistance.get("summary", {}).get("presence", "-"))
        assist_cols[2].metric("Saude", assistance.get("summary", {}).get("health_status", "-"))
        assist_cols[3].metric("Historico", assistance.get("summary", {}).get("historical_trend", "-"))
        st.caption(" | ".join(assistance.get("explanation", [])))
        if assistance.get("recommendations"):
            st.dataframe(
                _presentational_dataframe(pd.DataFrame(assistance.get("recommendations", []))),
                hide_index=True,
                use_container_width=True,
            )
        if assistance.get("guidance"):
            st.write(" | ".join(assistance.get("guidance", [])))
        recommendations = build_contextual_recommendations()
        st.subheader("Recomendacoes contextuais")
        rec_cols = st.columns(4)
        rec_cols[0].metric("Estado", recommendations.get("state", "-"))
        rec_cols[1].metric("Presenca", recommendations.get("summary", {}).get("presence", "-"))
        rec_cols[2].metric("Historico", recommendations.get("summary", {}).get("historical_trend", "-"))
        rec_cols[3].metric("Saude", recommendations.get("summary", {}).get("health_status", "-"))
        st.caption(" | ".join(recommendations.get("explanation", [])))
        if recommendations.get("recommendations"):
            st.dataframe(
                _presentational_dataframe(pd.DataFrame(recommendations.get("recommendations", []))),
                hide_index=True,
                use_container_width=True,
            )
        explainable = build_explainable_analytics()
        st.subheader("Analitica explicavel")
        explain_cols = st.columns(4)
        explain_cols[0].metric("Estado", explainable.get("state", "-"))
        explain_cols[1].metric("Presenca", explainable.get("summary", {}).get("presence", "-"))
        explain_cols[2].metric("Saude", explainable.get("summary", {}).get("health_status", "-"))
        explain_cols[3].metric("Drift", explainable.get("summary", {}).get("drift", 0.0))
        st.caption(" | ".join(explainable.get("narrative", [])))
        if explainable.get("explanation"):
            st.dataframe(
                _presentational_dataframe(pd.DataFrame(explainable.get("explanation", []))),
                hide_index=True,
                use_container_width=True,
            )
        guidance = build_operational_guidance()
        st.subheader("Orientacao operacional")
        guidance_cols = st.columns(4)
        guidance_cols[0].metric("Estado", guidance.get("state", "-"))
        guidance_cols[1].metric("Presenca", guidance.get("summary", {}).get("presence", "-"))
        guidance_cols[2].metric("Saude", guidance.get("summary", {}).get("health_status", "-"))
        guidance_cols[3].metric("Drift", guidance.get("summary", {}).get("drift", 0.0))
        st.caption(" | ".join(guidance.get("narrative", [])))
        if guidance.get("guidance"):
            st.dataframe(
                _presentational_dataframe(pd.DataFrame(guidance.get("guidance", []))),
                hide_index=True,
                use_container_width=True,
            )
        executive_summary = build_executive_summary()
        st.subheader("Resumo executivo")
        summary_cols = st.columns(4)
        summary_cols[0].metric("Estado", executive_summary.get("state", "-"))
        summary_cols[1].metric("Presenca", executive_summary.get("summary", {}).get("presence", "-"))
        summary_cols[2].metric("Saude", executive_summary.get("summary", {}).get("health_status", "-"))
        summary_cols[3].metric("Historico", executive_summary.get("summary", {}).get("historical_trend", "-"))
        st.caption(" | ".join(executive_summary.get("bullets", [])))
        if executive_summary.get("highlights"):
            st.dataframe(
                _presentational_dataframe(pd.DataFrame(executive_summary.get("highlights", []))),
                hide_index=True,
                use_container_width=True,
            )
        adaptive_memory = build_adaptive_assistance_memory()
        st.subheader("Memoria assistiva adaptativa")
        memory_cols = st.columns(4)
        memory_cols[0].metric("Estado", adaptive_memory.get("state", "-"))
        memory_cols[1].metric("Execucao", adaptive_memory.get("summary", {}).get("execution_id", "-"))
        memory_cols[2].metric("Snapshots", adaptive_memory.get("summary", {}).get("snapshot_count", 0))
        memory_cols[3].metric("Replay", "sim" if adaptive_memory.get("memory", {}).get("replay_available") else "nao")
        st.caption(
            f"Memoria: {adaptive_memory.get('summary', {}).get('state', '-')}"
            f" | Linha de memoria: {adaptive_memory.get('metadata', {}).get('layer', '-')}"
        )
        if adaptive_memory.get("memory_items"):
            st.dataframe(
                _presentational_dataframe(pd.DataFrame(adaptive_memory.get("memory_items", []))),
                hide_index=True,
                use_container_width=True,
            )
        human_language = build_human_analytical_language()
        st.subheader("Linguagem analitica humana")
        human_cols = st.columns(4)
        human_cols[0].metric("Estado", human_language.get("state", "-"))
        human_cols[1].metric("Guia", human_language.get("summary", {}).get("guidance_state", "-"))
        human_cols[2].metric("Saude", human_language.get("summary", {}).get("health_status", "-"))
        human_cols[3].metric("Memoria", human_language.get("summary", {}).get("memory_state", "-"))
        st.caption(" | ".join(human_language.get("phrases", [])))
        if human_language.get("highlights"):
            st.dataframe(
                _presentational_dataframe(pd.DataFrame(human_language.get("highlights", []))),
                hide_index=True,
                use_container_width=True,
            )
        support_experience = build_institutional_support_experience()
        st.subheader("Experiencia de suporte institucional")
        support_cols = st.columns(4)
        support_cols[0].metric("Estado", support_experience.get("state", "-"))
        support_cols[1].metric("Presenca", support_experience.get("summary", {}).get("presence", "-"))
        support_cols[2].metric("Saude", support_experience.get("summary", {}).get("health_status", "-"))
        support_cols[3].metric("Memoria", support_experience.get("summary", {}).get("memory_state", "-"))
        st.caption(" | ".join(support_experience.get("narrative", [])))
        if support_experience.get("experience"):
            st.dataframe(
                _presentational_dataframe(pd.DataFrame(support_experience.get("experience", []))),
                hide_index=True,
                use_container_width=True,
            )
        assistance_governance = build_assistance_governance()
        st.subheader("Governanca da assistencia")
        gov_support_cols = st.columns(4)
        gov_support_cols[0].metric("Estado", assistance_governance.get("state", "-"))
        gov_support_cols[1].metric("Presenca", assistance_governance.get("summary", {}).get("presence", "-"))
        gov_support_cols[2].metric("Saude", assistance_governance.get("summary", {}).get("health_status", "-"))
        gov_support_cols[3].metric("Memoria", assistance_governance.get("summary", {}).get("memory_state", "-"))
        st.caption(" | ".join(assistance_governance.get("narrative", [])))
        if assistance_governance.get("rules"):
            st.dataframe(
                _presentational_dataframe(pd.DataFrame(assistance_governance.get("rules", []))),
                hide_index=True,
                use_container_width=True,
            )
        full_presence = build_full_executive_assistance_presence()
        st.subheader("Presenca executiva final")
        full_cols = st.columns(4)
        full_cols[0].metric("Estado", full_presence.get("state", "-"))
        full_cols[1].metric("Suporte", full_presence.get("summary", {}).get("support_state", "-"))
        full_cols[2].metric("Governanca", full_presence.get("summary", {}).get("governance_state", "-"))
        full_cols[3].metric("Linguagem", full_presence.get("summary", {}).get("language_state", "-"))
        st.caption(" | ".join(full_presence.get("narrative", [])))
        if full_presence.get("presence"):
            st.dataframe(
                _presentational_dataframe(pd.DataFrame(full_presence.get("presence", []))),
                hide_index=True,
                use_container_width=True,
            )
        timeline_execution_id = str(observability_summary.get("latest_execution_id", "-"))
        memory_timeline = build_memory_timeline(timeline_execution_id) if timeline_execution_id not in {"", "-"} else {"summary": {"marker_count": 0, "snapshot_count": 0, "state_count": 0, "replay_ready": False, "latest_event": "-"}, "execution_id": timeline_execution_id, "entries": []}
        st.subheader("Linha temporal executiva da memória")
        timeline_summary = memory_timeline.get("summary", {})
        timeline_col1, timeline_col2, timeline_col3, timeline_col4 = st.columns(4)
        timeline_col1.metric("Marcadores", timeline_summary.get("marker_count", 0))
        timeline_col2.metric("Snapshots", timeline_summary.get("snapshot_count", 0))
        timeline_col3.metric("Estados", timeline_summary.get("state_count", 0))
        timeline_col4.metric("Replay", "sim" if timeline_summary.get("replay_ready") else "nao")
        st.caption(
            f"Execução: {memory_timeline.get('execution_id', '-')}"
            f" | Ultimo evento: {timeline_summary.get('latest_event', '-')}"
        )
        timeline_entries = memory_timeline.get("entries", [])
        if timeline_entries:
            st.dataframe(
                _presentational_dataframe(
                    pd.DataFrame(
                        [
                            {
                                "metric": entry.get("label", ""),
                                "value": entry.get("timestamp", ""),
                                "interpretation": entry.get("event_type", ""),
                                "confidence": entry.get("state_type", ""),
                                "path": entry.get("memory_id", ""),
                            }
                            for entry in timeline_entries[:20]
                        ]
                    )
                ),
                hide_index=True,
                use_container_width=True,
            )
        evolution = build_adaptive_evolution_tracking(timeline_execution_id) if timeline_execution_id not in {"", "-"} else {
            "summary": {
                "snapshot_count": 0,
                "state_count": 0,
                "step_count": 0,
                "change_count": 0,
                "stable_count": 0,
                "latest_label": "-",
            },
            "execution_id": timeline_execution_id,
            "steps": [],
        }
        st.subheader("Evolucao adaptativa")
        evolution_summary = evolution.get("summary", {})
        evo_col1, evo_col2, evo_col3, evo_col4 = st.columns(4)
        evo_col1.metric("Snapshots", evolution_summary.get("snapshot_count", 0))
        evo_col2.metric("Estados", evolution_summary.get("state_count", 0))
        evo_col3.metric("Mudancas", evolution_summary.get("change_count", 0))
        evo_col4.metric("Estabilidade", evolution_summary.get("stable_count", 0))
        st.caption(
            f"Execucao: {evolution.get('execution_id', '-')}"
            f" | Ultima evolucao: {evolution_summary.get('latest_label', '-')}"
        )
        evolution_steps = evolution.get("steps", [])
        if evolution_steps:
            st.dataframe(
                _presentational_dataframe(
                    pd.DataFrame(
                        [
                            {
                                "metric": step.get("label", ""),
                                "value": step.get("timestamp", ""),
                                "interpretation": step.get("event_type", ""),
                                "confidence": step.get("drift_ratio", 0.0),
                                "stage": step.get("memory_id", ""),
                            }
                            for step in evolution_steps[:20]
                        ]
                    )
                ),
                hide_index=True,
                use_container_width=True,
            )
        health = _runtime_health()
        operational = _operational_metrics()
        st.subheader("Saude operacional")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Tempo geracao", f"{health['avg_generation_ms']:.2f} ms")
        col2.metric("Tempo conferencia", f"{health['avg_check_ms']:.2f} ms")
        col3.metric("Snapshots", health.get("snapshot_files", health.get("snapshot_events", 0)))
        col4.metric("Eventos", health.get("total_runs", 0))
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("SQLite", health.get("sqlite_status", "unknown"))
        col2.metric("Runtime", health.get("runtime_status", "unknown"))
        col3.metric("ML", health.get("ml_status", "idle"))
        col4.metric("Cache", health.get("cache_status", "bounded"))
        bootstrap_state = _sqlite_bootstrap_state()
        if bootstrap_state.get("fallback_used"):
            st.info(
                "SQLite bootstrap em fallback temporário "
                f"({bootstrap_state.get('requested_path', '-') } -> {bootstrap_state.get('active_path', '-')})."
            )
        st.caption(
            f"Engine ativa: {health.get('engine_version', '-')}"
            f" | Modelo: {health.get('model_version', '-')}"
            f" | Fallback: {health.get('fallback_used', False)}"
            f" | Snapshot: {health.get('snapshot_version', '-')}"
        )
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Desempenho")
            st.dataframe(_presentational_dataframe(_performance_metrics_table()), hide_index=True, use_container_width=True)
        with col2:
            st.subheader("Metricas operacionais")
            st.dataframe(
                _presentational_dataframe(
                    pd.DataFrame(
                        [
                            {"metric": "daily_generation_average", "value": operational["daily_generation_average"]},
                            {"metric": "check_volume", "value": operational["check_volume"]},
                            {"metric": "ml_usage", "value": operational["ml_usage"]},
                            {"metric": "generated_games", "value": operational["generated_games"]},
                            {"metric": "imported_contests", "value": operational["imported_contests"]},
                            {"metric": "snapshot_volume", "value": operational["snapshot_volume"]},
                            {"metric": "log_growth_today", "value": operational["log_growth_today"]},
                            {"metric": "sqlite_size_bytes", "value": operational["sqlite_size_bytes"]},
                        ]
                    )
                ),
                hide_index=True,
                use_container_width=True,
            )
        st.subheader("Alertas")
        st.dataframe(_presentational_dataframe(_alert_contracts()), hide_index=True, use_container_width=True)
        st.subheader("Fonte de verdade")
        st.dataframe(_presentational_dataframe(_source_of_truth_map()), hide_index=True, use_container_width=True)
        st.subheader("Monitoramento cloud")
        st.dataframe(_presentational_dataframe(_cloud_failure_table()), hide_index=True, use_container_width=True)
        st.subheader("Rastro de geracao")
        trace_table = _generation_pipeline_trace_table()
        if trace_table.empty:
            st.info("Nenhum snapshot comportamental ainda.")
        else:
            st.dataframe(_presentational_dataframe(trace_table), hide_index=True, use_container_width=True)
            latest_trace = trace_table.iloc[0].to_dict()
            st.caption(
                "Último estágio: "
                f"{latest_trace.get('stage', '-')}"
                f" | rarity_std={latest_trace.get('rarity_std', 0.0)}"
                f" | recurrence_density={latest_trace.get('recurrence_density', 0.0)}"
                f" | normalization_pressure={latest_trace.get('normalization_pressure', 0.0)}"
            )
        col_trace_1, col_trace_2 = st.columns(2)
        with col_trace_1:
            st.subheader("Mapa de pressao")
            st.dataframe(_presentational_dataframe(_pressure_heatmap_table()), hide_index=True, use_container_width=True)
        with col_trace_2:
            st.subheader("Resumo de estabilidade")
            st.dataframe(_presentational_dataframe(_survival_summary_table()), hide_index=True, use_container_width=True)
        st.subheader("Colapso de diversidade")
        st.dataframe(_presentational_dataframe(_diversity_collapse_table()), hide_index=True, use_container_width=True)
        st.subheader("Comparativo de normalizacao")
        st.dataframe(_presentational_dataframe(_normalization_comparison_table()), hide_index=True, use_container_width=True)
        st.subheader("Divergencia de pipeline")
        st.dataframe(_presentational_dataframe(_pipeline_divergence_table()), hide_index=True, use_container_width=True)
        st.subheader("Relatorio dos filtros destrutivos")
        st.dataframe(_presentational_dataframe(_destructive_filters_table()), hide_index=True, use_container_width=True)
        st.subheader("Comportamento executivo")
        st.dataframe(_presentational_dataframe(_executive_behavioral_table()), hide_index=True, use_container_width=True)
        st.subheader("Filter profile damage")
        st.dataframe(_presentational_dataframe(_filter_profile_damage_table()), hide_index=True, use_container_width=True)
        st.subheader("Recuperacao")
        st.dataframe(_presentational_dataframe(_behavior_recovery_table()), hide_index=True, use_container_width=True)
        st.subheader("Zona segura")
        st.dataframe(_presentational_dataframe(_safe_recovery_zone_table()), hide_index=True, use_container_width=True)
        st.subheader("Aderencia historica")
        st.dataframe(_presentational_dataframe(_historical_adherence_table()), hide_index=True, use_container_width=True)
        st.subheader("Estabilidade do perfil")
        st.dataframe(_presentational_dataframe(_profile_stability_table()), hide_index=True, use_container_width=True)
        st.subheader("Sensibilidade a pressao")
        st.dataframe(_presentational_dataframe(_pressure_sensitivity_table()), hide_index=True, use_container_width=True)
        st.subheader("Protocolo de recuperacao")
        st.dataframe(_presentational_dataframe(_recovery_decision_protocol_table()), hide_index=True, use_container_width=True)
        st.subheader("Drift de comportamento")
        st.dataframe(_presentational_dataframe(_behavior_drift_table()), hide_index=True, use_container_width=True)
        st.subheader("Bases ouro")
        st.dataframe(_presentational_dataframe(_golden_baselines_table()), hide_index=True, use_container_width=True)
        st.subheader("Recuperacao falsa")
        st.dataframe(_presentational_dataframe(_false_recovery_table()), hide_index=True, use_container_width=True)
        st.subheader("Base experimental")
        st.dataframe(_presentational_dataframe(_experiment_baseline_table()), hide_index=True, use_container_width=True)
        st.subheader("Comparativo experimental")
        st.dataframe(_presentational_dataframe(_experiment_comparison_table()), hide_index=True, use_container_width=True)
        st.subheader("Plat? de recuperacao")
        st.dataframe(_presentational_dataframe(_recovery_plateau_table()), hide_index=True, use_container_width=True)
        st.subheader("Experimento 01")
        st.dataframe(_presentational_dataframe(_experiment_01_table()), hide_index=True, use_container_width=True)
        st.subheader("Ganho marginal")
        st.dataframe(_presentational_dataframe(_marginal_recovery_gain_table()), hide_index=True, use_container_width=True)
        ai_report = build_analytical_intelligence()
        ai_summary = ai_report.get("analytical_summary", {})
        ai_insights = ai_report.get("insights", [])
        ai_comparisons = ai_report.get("comparisons", [])
        executive_report = build_executive_analytical_report()
        ai_top_insights = {item.get("metric"): item for item in ai_insights if isinstance(item, dict)}
        col_ai_1, col_ai_2, col_ai_3, col_ai_4 = st.columns(4)
        col_ai_1.metric("Saúde estrutural", f"{float(ai_summary.get('structural_health', 0.0)):.2f}")
        col_ai_2.metric("Cobertura 10+", f"{float(ai_summary.get('coverage_10', 0.0)):.2f}")
        col_ai_3.metric("Cobertura 11+", f"{float(ai_summary.get('coverage_11', 0.0)):.2f}")
        col_ai_4.metric("Confiança", str(ai_summary.get("confidence", "-")))
        st.caption(
            f"Leitura institucional: {ai_summary.get('interpretation', '-')}"
            f" | baseline={ai_report.get('baseline_mode', '-')}"
            f" | fonte={ai_report.get('source', '-')}"
        )
        st.info(
            f"Veredito executivo: {executive_report.get('headline', '-')}"
            f" | status={executive_report.get('status', '-')}"
            f" | recomendacao={executive_report.get('recommendation', '-')}"
        )
        render_live_analytical_intelligence(
            ai_report,
            executive_report,
            build_institutional_historical_intelligence(),
            load_institutional_analytics_snapshot(),
            _institutional_analytical_timeline(),
            load_observational_stabilization_report(),
        )
        adaptive_report = load_adaptive_institutional_intelligence()
        if not adaptive_report:
            adaptive_payload = publish_adaptive_institutional_intelligence()
            adaptive_report = adaptive_payload.get("adaptive_memory", {})
        adaptive_timeline_report = load_adaptive_institutional_timeline()
        adaptive_insights_report = load_adaptive_institutional_insights()
        st.subheader("Inteligencia adaptativa")
        render_adaptive_institutional_intelligence(
            {
                **adaptive_report,
                "strategic_timeline": adaptive_timeline_report.get("report", adaptive_report.get("strategic_timeline", {})),
                "adaptive_insights": adaptive_insights_report.get("report", adaptive_report.get("adaptive_insights", {})),
            }
        )
        st.subheader("Historico analitico")
        st.dataframe(_institutional_historical_table(), hide_index=True, use_container_width=True)
        st.subheader("Snapshot analitico")
        st.dataframe(_institutional_analytics_snapshot_table(), hide_index=True, use_container_width=True)
        st.subheader("Linha do tempo")
        st.dataframe(_institutional_analytical_timeline(), hide_index=True, use_container_width=True)
        if ai_top_insights:
            st.dataframe(
                _presentational_dataframe(pd.DataFrame(
                    [
                        {
                            "metric": item.get("metric", ""),
                            "value": item.get("value", 0.0),
                            "interpretation": item.get("interpretation", ""),
                            "confidence": item.get("confidence", ""),
                        }
                        for item in ai_top_insights.values()
                    ]
                )),
                hide_index=True,
                use_container_width=True,
            )
        st.subheader("Insights")
        st.dataframe(_presentational_dataframe(_analytical_intelligence_insights()), hide_index=True, use_container_width=True)
        st.subheader("Comparativos analiticos")
        st.dataframe(_presentational_dataframe(_analytical_intelligence_comparisons()), hide_index=True, use_container_width=True)
        st.subheader("Linha do tempo")
        st.dataframe(_presentational_dataframe(_analytical_intelligence_timeline()), hide_index=True, use_container_width=True)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Tempo médio", f"{health['response_time_ms']:.2f} ms")
        col2.metric("Execuções", health["total_runs"])
        col3.metric("Falhas", health["failures"])
        col4.metric("Snapshots", health["snapshot_events"])

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Metricas runtime")
            st.dataframe(_presentational_dataframe(_observability_metrics_table()), hide_index=True, use_container_width=True)
        with col2:
            st.subheader("Saúde operacional")
            st.dataframe(
                _presentational_dataframe(pd.DataFrame(
                    [
                        {"metric": "avg_generation_ms", "value": health["avg_generation_ms"]},
                        {"metric": "avg_check_ms", "value": health["avg_check_ms"]},
                        {"metric": "ml_events", "value": health["ml_events"]},
                        {"metric": "report_events", "value": health["report_events"]},
                    ]
                )),
                hide_index=True,
                use_container_width=True,
            )

        tables = _observability_tables()
        st.subheader("Logs recentes")
        st.dataframe(_presentational_dataframe(tables["logs"].head(50)), hide_index=True, use_container_width=True)
        st.subheader("Auditoria institucional")
        st.dataframe(_presentational_dataframe(tables["audit"].head(50)), hide_index=True, use_container_width=True)


def _report_timestamp() -> str:
    return institutional_timestamp()


def _record_operational_log(event_type: str, status: str, duration_ms: float | None = None, context: dict[str, Any] | None = None) -> None:
    standardized_context = operational_event(
        category=event_type if event_type in set(item.value for item in EventCategory) else EventCategory.RUNTIME,
        event=event_type,
        status=status,
        severity=Severity.ERROR if status == "failed" else Severity.INFO,
        context=context or {},
    )
    connection, current_cursor = _sqlite_ensure_runtime_connection()
    payload = (
        event_type,
        status,
        duration_ms,
        json.dumps(standardized_context, ensure_ascii=False),
    )
    if connection is None or current_cursor is None:
        SQLITE_MEMORY_LOGS.append({"event_type": event_type, "status": status, "context": standardized_context})
        return
    try:
        current_cursor.execute(
            """
            INSERT INTO operational_logs (
                event_type,
                status,
                duration_ms,
                context_json
            )
            VALUES (?, ?, ?, ?)
            """,
            payload,
        )
        connection.commit()
    except sqlite3.Error as exc:
        SQLITE_MEMORY_LOGS.append({"event_type": event_type, "status": status, "error": str(exc), "context": standardized_context})
        if _sqlite_maybe_recover_connection(exc):
            recovered_conn, recovered_cursor = _sqlite_ensure_runtime_connection()
            if recovered_conn is not None and recovered_cursor is not None:
                try:
                    recovered_cursor.execute(
                        """
                        INSERT INTO operational_logs (
                            event_type,
                            status,
                            duration_ms,
                            context_json
                        )
                        VALUES (?, ?, ?, ?)
                        """,
                        payload,
                    )
                    recovered_conn.commit()
                    return
                except sqlite3.Error as retry_exc:
                    SQLITE_MEMORY_LOGS.append({"event_type": event_type, "status": status, "error": str(retry_exc), "context": standardized_context})


def _record_performance_metric(metric_name: str, duration_ms: float, context: dict[str, Any] | None = None) -> None:
    _record_operational_log(
        "performance",
        "success",
        duration_ms,
        {"metric": metric_name, **(context or {})},
    )


def _record_audit_trail(action_type: str, actor: str = "dashboard", artifact_path: str = "", context: dict[str, Any] | None = None) -> None:
    standardized_context = operational_event(
        category=EventCategory.AUDIT,
        event=action_type,
        status="recorded",
        context={"actor": actor, "artifact_path": artifact_path, **(context or {})},
    )
    connection, current_cursor = _sqlite_ensure_runtime_connection()
    if connection is None or current_cursor is None:
        SQLITE_MEMORY_LOGS.append({"action_type": action_type, "actor": actor, "artifact_path": artifact_path, "context": standardized_context})
        return
    try:
        current_cursor.execute(
            """
            INSERT INTO audit_trail (
                action_type,
                actor,
                artifact_path,
                context_json
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                action_type,
                actor,
                artifact_path,
                json.dumps(standardized_context, ensure_ascii=False),
            ),
        )
        connection.commit()
    except sqlite3.Error as exc:
        SQLITE_MEMORY_LOGS.append({"action_type": action_type, "actor": actor, "artifact_path": artifact_path, "error": str(exc), "context": standardized_context})
        if _sqlite_maybe_recover_connection(exc):
            recovered_conn, recovered_cursor = _sqlite_ensure_runtime_connection()
            if recovered_conn is not None and recovered_cursor is not None:
                try:
                    recovered_cursor.execute(
                        """
                        INSERT INTO audit_trail (
                            action_type,
                            actor,
                            artifact_path,
                            context_json
                        )
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            action_type,
                            actor,
                            artifact_path,
                            json.dumps(standardized_context, ensure_ascii=False),
                        ),
                    )
                    recovered_conn.commit()
                except sqlite3.Error:
                    pass


def _ensure_log_tables() -> None:
    _record_operational_log("observability_boot", "ok", 0.0, {"source": "admin_app"})


def _ensure_reports_dirs() -> None:
    REPORTS_DIR.mkdir(exist_ok=True)
    REPORTS_SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    ML_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ML_SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def _sqlite_health_check() -> bool:
    try:
        connection, current_cursor = _sqlite_ensure_runtime_connection()
        if connection is None or current_cursor is None:
            return False
        current_cursor.execute("PRAGMA integrity_check")
        result = current_cursor.fetchone()
        if not (result and str(result[0]).lower() == "ok"):
            raise sqlite3.DatabaseError("integrity_check failed")
        return bool(result and str(result[0]).lower() == "ok")
    except sqlite3.DatabaseError as exc:
        SQLITE_MEMORY_LOGS.append({"event_type": "sqlite_integrity", "status": "failed", "error": str(exc)})
        if _sqlite_maybe_recover_connection(exc):
            return _sqlite_health_check()
        return False
    except Exception:
        return False


def _sqlite_execute_safe(query: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor | None:
    try:
        connection, current_cursor = _sqlite_ensure_runtime_connection()
        if connection is None or current_cursor is None:
            return None
        connection.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
        return current_cursor.execute(query, params)
    except sqlite3.DatabaseError as exc:
        SQLITE_MEMORY_LOGS.append({"event_type": "sqlite", "status": "failed", "query": query[:80], "error": str(exc)})
        if _sqlite_maybe_recover_connection(exc):
            connection, current_cursor = _sqlite_ensure_runtime_connection()
            if connection is not None and current_cursor is not None:
                try:
                    connection.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
                    return current_cursor.execute(query, params)
                except sqlite3.Error:
                    pass
        _record_operational_log("sqlite", "failed", 0.0, {"query": query[:80], "error": str(exc)})
        return None


def _invalidate_runtime_cache() -> None:
    try:
        st.cache_data.clear()
    except Exception:
        pass
    except Exception as exc:
        _record_operational_log("sqlite", "failed", 0.0, {"query": query[:80], "error": str(exc)})
        return None


def _write_snapshot(name: str, payload: dict[str, Any]) -> Path:
    _ensure_reports_dirs()
    path = artifact_path(REPORTS_SNAPSHOTS_DIR, ArtifactKind.SNAPSHOT, name, "json")
    standardized_payload = {
        "metadata": metadata_envelope(artifact_type=ArtifactKind.SNAPSHOT, name=name, context={"source": "admin_app"}),
        "payload": payload,
    }
    path.write_text(json.dumps(standardized_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _record_operational_log("snapshot", "success", 0.0, {"name": name, "path": str(path)})
    _record_audit_trail("snapshot", artifact_path=str(path), context={"name": name})
    return path


def _write_ml_snapshot(name: str, payload: dict[str, Any]) -> Path:
    _ensure_reports_dirs()
    path = artifact_path(ML_SNAPSHOTS_DIR, ArtifactKind.ML_SNAPSHOT, name, "json")
    standardized_payload = {
        "metadata": metadata_envelope(
            artifact_type=ArtifactKind.ML_SNAPSHOT,
            name=name,
            context={
                "model_version": payload.get("model_version"),
                "feature_schema_version": payload.get("feature_schema_version"),
            },
        ),
        "payload": payload,
    }
    path.write_text(json.dumps(standardized_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _record_operational_log("ml", "success", 0.0, {"event": "ml_snapshot", "name": name, "path": str(path)})
    return path


def _export_csv(path: Path, dataframe: pd.DataFrame) -> Path:
    _ensure_reports_dirs()
    dataframe.to_csv(path, index=False, encoding="utf-8")
    _record_operational_log("export", "success", 0.0, {"path": str(path), "format": "csv"})
    return path


def _save_pdf_report(path: Path, title: str, lines: list[str], table: pd.DataFrame | None = None) -> Path:
    _ensure_reports_dirs()
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    ax.axis("off")
    ax.text(0.02, 0.98, title, fontsize=18, fontweight="bold", va="top")
    ax.text(0.02, 0.955, "LotoIA | Statistical Structural Platform | UTC", fontsize=8, va="top")
    y = 0.91
    for line in lines[:24]:
        ax.text(0.02, y, line, fontsize=10, va="top")
        y -= 0.035
    if table is not None and not table.empty:
        preview = table.head(12)
        table_ax = fig.add_axes([0.02, 0.08, 0.96, 0.30])
        table_ax.axis("off")
        mpl_table = table_ax.table(cellText=preview.values, colLabels=preview.columns, loc="center")
        mpl_table.auto_set_font_size(False)
        mpl_table.set_fontsize(7)
        mpl_table.scale(1, 1.3)
    fig.savefig(path, format="pdf", bbox_inches="tight")
    plt.close(fig)
    _record_operational_log("report", "success", 0.0, {"path": str(path), "format": "pdf", "title": title})
    return path


def _safe_download_bytes(path: Path) -> bytes | None:
    try:
        if not path.exists() or not path.is_file():
            return None
        return path.read_bytes()
    except Exception as exc:
        _record_operational_log("export", "failed", 0.0, {"path": str(path), "error": str(exc)})
        return None


def _save_ml_report(payload: dict[str, Any], summary: pd.DataFrame) -> dict[str, Path]:
    _ensure_reports_dirs()
    timestamp = _report_timestamp()
    json_path = ML_REPORTS_DIR / f"lotoia_ml_governance_{timestamp}.json"
    csv_path = ML_REPORTS_DIR / f"lotoia_ml_governance_{timestamp}.csv"
    pdf_path = ML_REPORTS_DIR / f"lotoia_ml_governance_{timestamp}.pdf"
    governed_payload = ml_governance_payload(payload=payload, experiment_name="ml_governance")
    json_path.write_text(json.dumps(governed_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    summary.to_csv(csv_path, index=False, encoding="utf-8")
    _record_audit_trail("ml_report", artifact_path=str(json_path), context={"model_version": payload.get("model_version")})
    _save_pdf_report(
        pdf_path,
        "LotoIA - Governanca ML Report",
        [
            f"Model version: {payload.get('model_version')}",
            f"Feature schema: {payload.get('feature_schema_version')}",
            f"Experiment rows: {payload.get('experiment_rows')}",
            f"Walk-forward splits: {payload.get('walk_forward_splits')}",
            f"Temporal valid: {payload.get('temporal_valid')}",
        ],
        summary,
    )
    return {"json": json_path, "csv": csv_path, "pdf": pdf_path}


def _build_generation_report_payload(games: list[dict[str, Any]]) -> tuple[pd.DataFrame, dict[str, Any]]:
    dataframe = _historical_intelligence_dataframe(games)
    analytics = _historical_analytics(games)
    payload = report_payload(
        report_type="generation",
        payload={
            "analytics": analytics,
            "games": dataframe.to_dict(orient="records"),
        },
        context={"records": len(games), "source": "admin_app"},
    )
    return dataframe, payload


def _build_check_report_payload(result: dict[str, Any], contest_id: int, numbers: list[int]) -> tuple[pd.DataFrame, dict[str, Any]]:
    row = pd.DataFrame(
        [
            {
                "contest_id": contest_id,
                "hits": result.get("hits"),
                "numbers": _format_numbers(numbers),
                "correct_numbers": _format_numbers(result.get("correct_numbers", [])),
            }
        ]
    )
    payload = report_payload(
        report_type="check",
        payload={
            "contest_id": contest_id,
            "result": result,
        },
        context={"contest_id": contest_id, "source": "admin_app"},
    )
    return row, payload


def _parse_check_numbers(numbers_text: str) -> list[int]:
    try:
        numbers = [int(item) for item in numbers_text.replace(",", " ").replace(";", " ").split()]
    except Exception as exc:
        raise ValueError("Digite apenas dezenas numericas separadas por espaco ou virgula.") from exc
    if len(numbers) != 15:
        raise ValueError("Informe exatamente 15 dezenas para conferencia.")
    if len(set(numbers)) != 15:
        raise ValueError("As dezenas da conferencia nao podem se repetir.")
    invalid = [number for number in numbers if number < 1 or number > 25]
    if invalid:
        raise ValueError("As dezenas devem estar entre 01 e 25.")
    return sorted(numbers)


def _parse_check_games(games_text: str) -> list[list[int]]:
    lines = [line.strip() for line in games_text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("Informe ao menos 1 jogo para conferencia.")
    if len(lines) > 10:
        raise ValueError("O maximo permitido e de 10 jogos por conferencia.")
    return [_parse_check_numbers(line) for line in lines]


def _find_draw_for_check(contest_id: int) -> Draw:
    row = _sqlite_execute_safe(
        """
        SELECT contest_number, data, dezenas
        FROM imported_contests
        WHERE contest_number = ?
        """,
        (contest_id,),
    )
    if row:
        contest = row.fetchone()
        if contest:
            numbers = [int(number) for number in str(contest[2]).split(",") if str(number).strip()]
            if len(numbers) == 15:
                return Draw(contest=int(contest[0]), date=str(contest[1]), numbers=numbers)

    draws = load_draws_csv(DEFAULT_HISTORY_PATH)
    if not draws:
        raise ValueError("Nenhum concurso historico disponivel para conferencia.")
    latest_contest = max(draw.contest for draw in draws)
    if contest_id > latest_contest:
        raise ValueError(f"Concurso {contest_id} ainda nao disponivel. Ultimo concurso carregado: {latest_contest}.")
    for draw in draws:
        if draw.contest == contest_id:
            return draw
    raise ValueError(f"Concurso {contest_id} nao encontrado na base historica.")


def _check_game_against_contest(contest_id: int, numbers: list[int]) -> dict[str, Any]:
    draw = _find_draw_for_check(contest_id)
    correct_numbers = sorted(set(numbers) & set(draw.numbers))
    return {
        "contest_id": contest_id,
        "numbers": numbers,
        "draw_numbers": sorted(draw.numbers),
        "hits": len(correct_numbers),
        "correct_numbers": correct_numbers,
        "execution_time_ms": 0.0,
    }



def _score_value(game: dict[str, Any]) -> float:
    final_score = game.get("final_score", {})
    return float(final_score.get("final_score", 0))


def _games_dataframe(games: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for index, game in enumerate(games, start=1):
        quadra_score = game.get("quadra_score", {})
        rows.append(
            {
                "rank": index,
                "dezenas": _format_numbers(game["numbers"]),
                "perfil": game.get("profile_type", ""),
                "profile_score": game.get("profile_score", 0),
                "motivo": game.get("historical_intelligence", {}).get("ranking_reason", ""),
                "final_score": _score_value(game),
                "quadras": quadra_score.get("found_quadras", 0),
                "rank_medio_quadra": round(float(quadra_score.get("average_rank", 0)), 2),
                "soma": game.get("sum", sum(game["numbers"])),
                "pares": game.get("even", 0),
                "impares": game.get("odd", 0),
            }
        )
    return pd.DataFrame(rows)


def _stats_table(stats: dict[str, dict[str, Any]], key_name: str, limit: int = 25) -> pd.DataFrame:
    rows = []
    for key, values in list(stats.items())[:limit]:
        row = {key_name: key}
        row.update(values)
        rows.append(row)
    return pd.DataFrame(rows)


def _all_backtest_games(result: BacktestResult) -> list[dict[str, Any]]:
    return [game for contest_result in result.contest_results for game in contest_result["games"]]


def _backtest_games_dataframe(result: BacktestResult) -> pd.DataFrame:
    rows = []
    for contest_result in result.contest_results:
        for game in contest_result["games"]:
            rows.append(
                {
                    "concurso": contest_result["contest"],
                    "dezenas": _format_numbers(game["numbers"]),
                    "acertos": game["hits"],
                    "final_score": _score_value(game),
                    "quadras": game["quadra_score"]["found_quadras"],
                    "rank_medio_quadra": round(float(game["quadra_score"]["average_rank"]), 2),
                }
            )
    return pd.DataFrame(rows)


def _distribution_chart(hit_distribution: dict[str, int]) -> go.Figure:
    figure = go.Figure(data=[go.Bar(x=list(hit_distribution.keys()), y=list(hit_distribution.values()), marker_color="#173b63")])
    figure.update_layout(title="Distribuição de acertos", xaxis_title="Pontos", yaxis_title="Quantidade", margin={"l": 20, "r": 20, "t": 50, "b": 20})
    return figure


def _score_correlation_chart(result: BacktestResult) -> go.Figure:
    games = _all_backtest_games(result)
    figure = go.Figure(data=[go.Scatter(x=[_score_value(game) for game in games], y=[game["hits"] for game in games], mode="markers", marker={"color": "#355c7d", "size": 9})])
    figure.update_layout(title="final_score x acertos", xaxis_title="final_score", yaxis_title="Acertos", margin={"l": 20, "r": 20, "t": 50, "b": 20})
    return figure


def _hits_by_contest_chart(result: BacktestResult) -> go.Figure:
    contests = [item["contest"] for item in result.contest_results]
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=contests, y=[item["best_hits"] for item in result.contest_results], mode="lines+markers", name="Melhor jogo"))
    figure.add_trace(go.Scatter(x=contests, y=[item["average_hits"] for item in result.contest_results], mode="lines+markers", name="Média"))
    figure.update_layout(title="Acertos por concurso", xaxis_title="Concurso", yaxis_title="Acertos", margin={"l": 20, "r": 20, "t": 50, "b": 20})
    return figure


def _configuration_chart(calibration_result: dict[str, Any]) -> go.Figure:
    evaluations = calibration_result.get("evaluations", [])
    figure = go.Figure(data=[go.Bar(x=[evaluation["configuration"] for evaluation in evaluations], y=[evaluation["average_hits"] for evaluation in evaluations], marker_color="#1f5f8b")])
    figure.update_layout(title="Média de acertos por configuração", xaxis_title="Configuração", yaxis_title="Média de acertos", margin={"l": 20, "r": 20, "t": 50, "b": 20})
    return figure


def _benchmark_summary_dataframe(result: BenchmarkResult) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "estrategia": strategy,
                "media_acertos": metrics["average_hits"],
                "desvio_padrao": metrics["standard_deviation"],
                "correlacao": metrics["final_score_hit_correlation"],
                "total_jogos": metrics["total_games"],
                "melhor": metrics["stability"]["max_hits"],
                "pior": metrics["stability"]["min_hits"],
            }
            for strategy, metrics in result.strategies.items()
        ]
    )


def _benchmark_comparison_dataframe(result: BenchmarkResult) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "comparacao": name,
                "diferenca_media": metrics["average_hit_difference"],
                "taxa_superioridade": metrics["superiority_rate"],
                "ranking_medio_lotoia": metrics["lotoia_average_rank"],
                "ranking_medio_competidor": metrics["competitor_average_rank"],
            }
            for name, metrics in result.comparisons.items()
        ]
    )


def _benchmark_average_chart(result: BenchmarkResult) -> go.Figure:
    dataframe = _benchmark_summary_dataframe(result)
    figure = go.Figure(data=[go.Bar(x=dataframe["estrategia"], y=dataframe["media_acertos"], marker_color=["#173b63", "#1f5f8b", "#9bbad1"])])
    figure.update_layout(title="Média de acertos por estratégia", xaxis_title="Estratégia", yaxis_title="Média de acertos", margin={"l": 20, "r": 20, "t": 50, "b": 20})
    return figure


def _benchmark_evolution_chart(result: BenchmarkResult) -> go.Figure:
    figure = go.Figure()
    contests = [contest_result["contest"] for contest_result in result.contest_results]
    for strategy in result.strategies:
        figure.add_trace(
            go.Scatter(
                x=contests,
                y=[contest_result["strategy_results"][strategy]["average_hits"] for contest_result in result.contest_results],
                mode="lines+markers",
                name=strategy,
            )
        )
    figure.update_layout(title="Evolução histórica do benchmark", xaxis_title="Concurso", yaxis_title="Média de acertos", margin={"l": 20, "r": 20, "t": 50, "b": 20})
    return figure


def _runs_dataframe(runs: list[dict[str, Any]], columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame([{column: run.get(column) for column in columns} for run in runs])


def _historical_metric_chart(runs: list[dict[str, Any]], metric: str, title: str) -> go.Figure:
    figure = go.Figure(data=[go.Scatter(x=[run["created_at"] for run in runs], y=[run.get(metric, 0) for run in runs], mode="lines+markers")])
    figure.update_layout(title=title, xaxis_title="Execução", yaxis_title=metric, margin={"l": 20, "r": 20, "t": 50, "b": 20})
    return figure


@st.cache_data(show_spinner=False, ttl=STREAMLIT_CACHE_TTL_SECONDS, max_entries=STREAMLIT_CACHE_MAX_ENTRIES)
def _load_draws():
    try:
        return load_draws_csv(DEFAULT_HISTORY_PATH)
    except Exception as exc:
        _record_operational_log("load_draws", "failed", 0.0, {"error": str(exc), "path": str(DEFAULT_HISTORY_PATH)})
        raise


@st.cache_data(show_spinner=False, ttl=STREAMLIT_CACHE_TTL_SECONDS, max_entries=STREAMLIT_CACHE_MAX_ENTRIES)
def _cached_generate_best_games(count: int, pool_size: int) -> dict[str, Any]:
    from lotoia.generator.basic_generator import generate_best_games

    return generate_best_games(count=count, pool_size=pool_size)


@st.cache_data(show_spinner=False, ttl=STREAMLIT_CACHE_TTL_SECONDS, max_entries=STREAMLIT_CACHE_MAX_ENTRIES)
def _cached_generate_multiple_games(count: int, max_repeated: int) -> list[dict[str, Any]]:
    from lotoia.generator.basic_generator import generate_multiple_games

    return generate_multiple_games(count=count, max_repeated=max_repeated)


@st.cache_data(show_spinner=False, ttl=STREAMLIT_CACHE_TTL_SECONDS, max_entries=STREAMLIT_CACHE_MAX_ENTRIES)
def _cached_backtest(contests: int, games_count: int, pool_size: int, history_window: int, seed: int) -> BacktestResult:
    from lotoia.backtesting import run_backtest

    return run_backtest(contests_analyzed=contests, games_count=games_count, pool_size=pool_size, history_window=history_window, seed=seed)


@st.cache_data(show_spinner=False, ttl=STREAMLIT_CACHE_TTL_SECONDS, max_entries=STREAMLIT_CACHE_MAX_ENTRIES)
def _cached_calibration(weights: dict[str, float], contests: int, games_count: int, pool_size: int, history_window: int, seed: int) -> dict[str, Any]:
    official = WeightConfiguration(
        name="oficial",
        duo=FINAL_SCORE_WEIGHTS["duo_score"],
        terno=FINAL_SCORE_WEIGHTS["terno_score"],
        quadra=FINAL_SCORE_WEIGHTS["quadra_score"],
        quina=FINAL_SCORE_WEIGHTS["quina_score"],
        delay=FINAL_SCORE_WEIGHTS["delay_score"],
        frequency=FINAL_SCORE_WEIGHTS["frequency_score"],
        sum=FINAL_SCORE_WEIGHTS["sum_score"],
        sequence=FINAL_SCORE_WEIGHTS["sequence_score"],
    )
    custom = WeightConfiguration(name="experimental", **weights)
    return compare_weight_configurations([official, custom], contests_analyzed=contests, games_count=games_count, pool_size=pool_size, history_window=history_window, seed=seed)


@st.cache_data(show_spinner=False, ttl=STREAMLIT_CACHE_TTL_SECONDS, max_entries=STREAMLIT_CACHE_MAX_ENTRIES)
def _cached_stats() -> dict[str, dict[str, Any]]:
    return {
        "frequency": load_frequency_stats(),
        "delay": load_delay_stats(),
        "duos": load_duos_stats(),
        "ternos": load_ternos_stats(),
        "quadras": load_quadras_stats(),
        "quinas": load_quinas_stats(),
        "senas": load_senas_stats(),
    }


@st.cache_data(show_spinner=False, ttl=STREAMLIT_CACHE_TTL_SECONDS, max_entries=STREAMLIT_CACHE_MAX_ENTRIES)
def _cached_benchmark(contests: int, games_count: int, pool_size: int, history_window: int, seed: int) -> BenchmarkResult:
    from lotoia.benchmark import run_benchmark

    return run_benchmark(contests_analyzed=contests, games_count=games_count, pool_size=pool_size, history_window=history_window, seed=seed)


@st.cache_data(show_spinner=False, ttl=STREAMLIT_CACHE_TTL_SECONDS, max_entries=STREAMLIT_CACHE_MAX_ENTRIES)
def _cached_runs() -> dict[str, list[dict[str, Any]]]:
    return list_runs()


@st.cache_data(show_spinner=False, ttl=STREAMLIT_CACHE_TTL_SECONDS, max_entries=STREAMLIT_CACHE_MAX_ENTRIES)
def _load_admin_events(table_name: str) -> pd.DataFrame:
    if table_name not in ALLOWED_ADMIN_EVENT_TABLES:
        return pd.DataFrame()
    query = f"SELECT * FROM {table_name} ORDER BY created_at DESC, id DESC LIMIT {ADMIN_EVENT_LIMIT}"
    connection, _ = _sqlite_ensure_runtime_connection()
    if connection is None:
        return pd.DataFrame()
    return pd.read_sql_query(query, connection)


def _lead_identifier(first_name: str, whatsapp: str) -> str:
    return f"{first_name.strip()} | {whatsapp.strip()}"


def _read_sql_query_safe(query: str, columns: list[str], params: tuple[Any, ...] = ()) -> pd.DataFrame:
    try:
        connection, _ = _sqlite_ensure_runtime_connection()
        if connection is None:
            return pd.DataFrame(columns=columns)
        return pd.read_sql_query(query, connection, params=params)
    except Exception as exc:
        _record_operational_log("sqlite", "failed", 0.0, {"query": query[:80], "error": str(exc)})
        return pd.DataFrame(columns=columns)


def _persist_lead(first_name: str, whatsapp: str) -> int | None:
    if not first_name.strip() or not whatsapp.strip():
        return None
    connection, current_cursor = _sqlite_ensure_runtime_connection()
    if connection is None or current_cursor is None:
        SQLITE_MEMORY_LOGS.append({"event_type": "leads", "status": "failed", "first_name": first_name, "whatsapp": whatsapp})
        return None
    try:
        current_cursor.execute(
            """
            INSERT INTO leads (
                first_name,
                whatsapp
            )
            VALUES (?, ?)
            """,
            (first_name.strip(), whatsapp.strip()),
        )
        connection.commit()
        return int(current_cursor.lastrowid or 0) or None
    except sqlite3.Error as exc:
        SQLITE_MEMORY_LOGS.append({"event_type": "leads", "status": "failed", "error": str(exc), "first_name": first_name, "whatsapp": whatsapp})
        if _sqlite_maybe_recover_connection(exc):
            recovered_conn, recovered_cursor = _sqlite_ensure_runtime_connection()
            if recovered_conn is not None and recovered_cursor is not None:
                try:
                    recovered_cursor.execute(
                        """
                        INSERT INTO leads (
                            first_name,
                            whatsapp
                        )
                        VALUES (?, ?)
                        """,
                        (first_name.strip(), whatsapp.strip()),
                    )
                    recovered_conn.commit()
                    return int(recovered_cursor.lastrowid or 0) or None
                except sqlite3.Error:
                    pass
    _invalidate_runtime_cache()
    return None


def _persist_generation_events(
    *,
    first_name: str,
    whatsapp: str,
    games: list[dict[str, Any]],
    duration_ms: float,
    strategy: str,
    lead_id: int | None,
) -> int | None:
    connection, current_cursor = _sqlite_ensure_runtime_connection()
    if connection is None or current_cursor is None:
        SQLITE_MEMORY_LOGS.append({"event_type": "generation", "status": "failed", "games": len(games), "strategy": strategy})
        return None

    average_rank = 0.0
    target_contest = None
    try:
        target_contest = int(_safe_last_contest()) if _safe_last_contest().isdigit() else None
    except Exception:
        target_contest = None
    if games:
        scores = [float(game.get("final_score", {}).get("final_score", 0.0)) for game in games if isinstance(game.get("final_score"), dict)]
        average_rank = round(sum(scores) / len(scores), 4) if scores else 0.0

    try:
        current_cursor.execute(
            """
            INSERT INTO generation_events (
                first_name,
                whatsapp,
                seed,
                strategy,
                ranking_score,
                execution_time_ms,
                ml_enabled
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (first_name.strip(), whatsapp.strip(), None, strategy, average_rank, duration_ms, 0),
        )
        generation_event_id = int(current_cursor.lastrowid or 0) or None
        for index, game in enumerate(games, start=1):
            current_cursor.execute(
                """
                INSERT INTO generated_games (
                    generation_event_id,
                    lead_id,
                    target_contest,
                    origin,
                    generation_mode,
                    game_index,
                    numbers,
                    profile_type,
                    final_score,
                    quadra_score,
                    context_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    generation_event_id,
                    lead_id,
                    target_contest,
                    "dashboard_admin",
                    strategy,
                    index,
                    json.dumps(game.get("numbers", []), ensure_ascii=False),
                    str(game.get("profile_type", "")),
                    json.dumps(game.get("final_score", {}), ensure_ascii=False),
                    json.dumps(game.get("quadra_score", {}), ensure_ascii=False),
                    json.dumps(
                        {
                            "first_name": first_name.strip(),
                            "whatsapp": whatsapp.strip(),
                            "duration_ms": round(duration_ms, 2),
                            "strategy": strategy,
                            "lead_id": lead_id,
                            "target_contest": target_contest,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                ),
            )
        connection.commit()
        _invalidate_runtime_cache()
        return generation_event_id
    except sqlite3.Error as exc:
        SQLITE_MEMORY_LOGS.append({"event_type": "generation", "status": "failed", "error": str(exc), "games": len(games), "strategy": strategy})
        if _sqlite_maybe_recover_connection(exc):
            recovered_conn, recovered_cursor = _sqlite_ensure_runtime_connection()
            if recovered_conn is not None and recovered_cursor is not None:
                try:
                    recovered_cursor.execute(
                        """
                        INSERT INTO generation_events (
                            first_name,
                            whatsapp,
                            seed,
                            strategy,
                            ranking_score,
                            execution_time_ms,
                            ml_enabled
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (first_name.strip(), whatsapp.strip(), None, strategy, average_rank, duration_ms, 0),
                    )
                    generation_event_id = int(recovered_cursor.lastrowid or 0) or None
                    for index, game in enumerate(games, start=1):
                        recovered_cursor.execute(
                            """
                        INSERT INTO generated_games (
                            generation_event_id,
                            lead_id,
                            target_contest,
                            origin,
                            generation_mode,
                            game_index,
                            numbers,
                            profile_type,
                            final_score,
                            quadra_score,
                            context_json
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            generation_event_id,
                            lead_id,
                            target_contest,
                            "dashboard_admin",
                            strategy,
                            index,
                            json.dumps(game.get("numbers", []), ensure_ascii=False),
                            str(game.get("profile_type", "")),
                            json.dumps(game.get("final_score", {}), ensure_ascii=False),
                            json.dumps(game.get("quadra_score", {}), ensure_ascii=False),
                            json.dumps(
                                {
                                    "first_name": first_name.strip(),
                                    "whatsapp": whatsapp.strip(),
                                    "duration_ms": round(duration_ms, 2),
                                    "strategy": strategy,
                                    "lead_id": lead_id,
                                    "target_contest": target_contest,
                                },
                                ensure_ascii=False,
                                sort_keys=True,
                            ),
                        ),
                    )
                    recovered_conn.commit()
                    _invalidate_runtime_cache()
                    return generation_event_id
                except sqlite3.Error:
                    pass
        return None


def _capture_generation_lead(first_name: str, whatsapp: str) -> tuple[int, str, str]:
    lead_service = LeadCaptureService(DEFAULT_DATABASE_PATH)
    lead_payload = LeadCaptureRequest(
        first_name=first_name,
        whatsapp=whatsapp,
        source="dashboard_user_panel",
    )
    lead_capture = lead_service.capture(
        lead_payload,
        ip_address="",
        user_agent="dashboard_user_panel",
    )
    return int(lead_capture.lead["id"]), str(lead_capture.lead["first_name"]), str(lead_capture.normalized_whatsapp)


@st.cache_data(show_spinner=False, ttl=STREAMLIT_CACHE_TTL_SECONDS, max_entries=STREAMLIT_CACHE_MAX_ENTRIES)
def _lead_history_dataframe() -> pd.DataFrame:
    leads_df = _read_sql_query_safe(
        """
        SELECT
            id,
            first_name,
            whatsapp,
            created_at
        FROM leads
        ORDER BY created_at DESC, id DESC
        LIMIT 
        """,
        ["id", "first_name", "whatsapp", "created_at"],
        params=(LEAD_HISTORY_LIMIT,),
    )
    gen_df = _read_sql_query_safe(
        """
        SELECT
            first_name,
            whatsapp,
            created_at,
            ml_enabled,
            strategy
        FROM generation_events
        ORDER BY created_at DESC, id DESC
        LIMIT 
        """,
        ["first_name", "whatsapp", "created_at", "ml_enabled", "strategy"],
        params=(LEAD_HISTORY_LIMIT,),
    )
    check_df = _read_sql_query_safe(
        """
        SELECT
            first_name,
            whatsapp,
            created_at,
            contest_id,
            hits
        FROM check_events
        ORDER BY created_at DESC, id DESC
        LIMIT 
        """,
        ["first_name", "whatsapp", "created_at", "contest_id", "hits"],
        params=(LEAD_HISTORY_LIMIT,),
    )
    if leads_df.empty:
        return pd.DataFrame(
            columns=[
                "lead",
                "first_name",
                "whatsapp",
                "created_at",
                "origin",
                "generations",
                "checks",
                "ml_activations",
                "last_generation_at",
                "last_check_at",
                "recurrence_score",
            ]
        )

    base = leads_df.drop_duplicates(subset=["first_name", "whatsapp"], keep="first").copy()
    if gen_df.empty:
        gen_summary = pd.DataFrame(columns=["first_name", "whatsapp", "generations", "ml_activations", "last_generation_at"])
    else:
        gen_summary = (
            gen_df.assign(ml_enabled=gen_df["ml_enabled"].fillna(0).astype(int))
            .groupby(["first_name", "whatsapp"], as_index=False)
            .agg(generations=("created_at", "size"), ml_activations=("ml_enabled", "sum"), last_generation_at=("created_at", "max"))
        )
    if check_df.empty:
        check_summary = pd.DataFrame(columns=["first_name", "whatsapp", "checks", "last_check_at"])
    else:
        check_summary = check_df.groupby(["first_name", "whatsapp"], as_index=False).agg(checks=("created_at", "size"), last_check_at=("created_at", "max"))

    dataframe = base.merge(gen_summary, on=["first_name", "whatsapp"], how="left").merge(check_summary, on=["first_name", "whatsapp"], how="left")
    for column in ("generations", "checks", "ml_activations"):
        dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce").fillna(0).astype(int)
    dataframe["lead"] = dataframe.apply(lambda row: _lead_identifier(str(row["first_name"]), str(row["whatsapp"])), axis=1)
    dataframe["origin"] = "dashboard_admin"
    dataframe["recurrence_score"] = dataframe["generations"] + dataframe["checks"]
    dataframe = dataframe[
        [
            "lead",
            "first_name",
            "whatsapp",
            "created_at",
            "origin",
            "generations",
            "checks",
            "ml_activations",
            "last_generation_at",
            "last_check_at",
            "recurrence_score",
        ]
    ]
    if not dataframe.empty:
        dataframe = dataframe.sort_values(
            by=["recurrence_score", "created_at"],
            ascending=[False, False],
        )
    return dataframe


def _lead_analytics() -> dict[str, Any]:
    history = _lead_history_dataframe()
    total_leads = int(len(history))
    recurring_leads = int((history["recurrence_score"] > 1).sum()) if not history.empty else 0
    ml_activations = int(history["ml_activations"].sum()) if not history.empty else 0
    volume_generations = int(history["generations"].sum()) if not history.empty else 0
    volume_checks = int(history["checks"].sum()) if not history.empty else 0
    return {
        "total_leads": total_leads,
        "recurring_leads": recurring_leads,
        "ml_activations": ml_activations,
        "volume_generations": volume_generations,
        "volume_checks": volume_checks,
    }


def _empty_backtest_result(
    *,
    contests: int,
    games_count: int,
    pool_size: int,
    history_window: int,
) -> BacktestResult:
    return BacktestResult(
        contests_analyzed=0,
        games_per_contest=games_count,
        pool_size=pool_size,
        history_window=history_window,
        total_games=0,
        average_hits=0.0,
        hit_distribution={str(points): 0 for points in range(11, 16)},
        best_game=None,
        worst_game=None,
        average_winner_final_score=0.0,
        final_score_hit_correlation=0.0,
        contest_results=[],
    )


def _safe_backtest(
    *,
    contests: int,
    games_count: int,
    pool_size: int,
    history_window: int,
    seed: int,
) -> BacktestResult:
    attempts = [
        (contests, games_count, max(pool_size, games_count), history_window),
        (max(1, contests), max(1, min(games_count, 5)), max(max(1, min(games_count, 5)), min(pool_size, 50)), history_window),
        (max(1, min(contests, 3)), 1, 1, max(1, min(history_window, 120))),
    ]
    last_error = ""
    for attempt_contests, attempt_games, attempt_pool, attempt_window in attempts:
        try:
            return _cached_backtest(attempt_contests, attempt_games, attempt_pool, attempt_window, seed)
        except Exception as exc:
            last_error = str(exc)
            _record_operational_log(
                "backtest",
                "failed",
                0.0,
                {
                    "contests": attempt_contests,
                    "games_count": attempt_games,
                    "pool_size": attempt_pool,
                    "history_window": attempt_window,
                    "error": last_error,
                },
            )
    _record_operational_log("backtest", "degraded", 0.0, {"error": last_error})
    return _empty_backtest_result(
        contests=contests,
        games_count=games_count,
        pool_size=pool_size,
        history_window=history_window,
    )


def _safe_count(table_name: str) -> int:
    try:
        if table_name not in ALLOWED_ADMIN_EVENT_TABLES:
            return 0
        row = _sqlite_execute_safe(f"SELECT COUNT(*) FROM {table_name}")
        row = row.fetchone() if row else None
        return int(row[0]) if row else 0
    except Exception:
        return 0


def _safe_last_contest() -> str:
    try:
        row = _sqlite_execute_safe("SELECT MAX(contest_id) FROM check_events")
        row = row.fetchone() if row else None
        value = row[0] if row else None
        if value is not None:
            return str(value)
        row = _sqlite_execute_safe("SELECT MAX(contest_number) FROM imported_contests")
        row = row.fetchone() if row else None
        value = row[0] if row else None
        if value is not None:
            return str(value)
        draws = _load_draws()
        if draws:
            return str(max(draw.contest for draw in draws))
        return "-"
    except Exception:
        return "-"


def _safe_total_games() -> str:
    try:
        gen_row = _sqlite_execute_safe("SELECT COUNT(*) FROM generated_games")
        gen_row = gen_row.fetchone() if gen_row else None
        return str(int(gen_row[0]) if gen_row else 0)
    except Exception:
        return "-"


def _metric_row(result: BacktestResult) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Concursos", result.contests_analyzed)
    col2.metric("Jogos avaliados", result.total_games)
    col3.metric("Média de acertos", f"{result.average_hits:.2f}")
    col4.metric("Correlação", f"{result.final_score_hit_correlation:.3f}")


def _section_header(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="lotoia-section-title">{title}</div>
        <div class="lotoia-section-subtitle">{subtitle}</div>
        """,
        unsafe_allow_html=True,
    )


def _render_kpi_cards() -> None:
    gen_count = _safe_count("generation_events")
    check_count = _safe_count("check_events")
    ml_count = int(_query_scalar("SELECT COUNT(*) FROM generation_events WHERE ml_enabled = 1"))
    last_contest = _safe_last_contest()
    total_games = _safe_total_games()
    render_secondary_operational_metrics(gen_count, check_count, ml_count, last_contest, total_games)


def _render_institutional_cockpit() -> None:
    ai_report = build_analytical_intelligence()
    executive_report = build_executive_analytical_report()
    historical_report = build_institutional_historical_intelligence()
    snapshot = load_institutional_analytics_snapshot()
    observability_report = load_observational_stabilization_report()
    timeline = load_institutional_analytical_timeline()
    if not timeline:
        timeline = ensure_institutional_analytical_timeline(report_dir=REPORTS_DIR / "analytics")
    orchestration_report = load_intelligent_operational_orchestration()
    if not orchestration_report:
        orchestration_report = persist_intelligent_operational_orchestration(report_dir=REPORTS_DIR / "orchestration")

    historical_summary = historical_report.get("summary", {})
    analytical_summary = ai_report.get("analytical_summary", {})
    snapshot_summary = snapshot.get("summary", {}) if isinstance(snapshot, dict) else {}

    with st.container(border=True):
        _section_header(
            "Visao geral",
            "Leitura executiva da saúde estrutural, baseline, confiança, drift e linha do tempo institucional.",
        )
        render_executive_dashboard(
            executive_report,
            analytical_summary,
            historical_summary,
            snapshot_summary,
            observability_report,
            pd.DataFrame(timeline.get("timeline", [])),
        )
        render_operational_orchestration(orchestration_report)


def _render_lead_intelligence() -> None:
    analytics = _lead_analytics()
    history = _lead_history_dataframe()
    st.markdown("---")
    _section_header("Leitura de uso", "Uso institucional por usuario, recorrencia e padrao de uso.")
    a, b, c, d, e = st.columns(5)
    a.metric("Total leads", analytics["total_leads"])
    b.metric("Leads recorrentes", analytics["recurring_leads"])
    c.metric("Ativações ML", analytics["ml_activations"])
    d.metric("Gerações", analytics["volume_generations"])
    e.metric("Conferências", analytics["volume_checks"])
    st.subheader("Historico")
    st.dataframe(
        _presentational_dataframe(history),
        hide_index=True,
        use_container_width=True,
    )
    if not history.empty:
        st.subheader("Ranking de uso")
        ranking = (
            history[["lead", "recurrence_score", "generations", "checks", "ml_activations"]]
            .head(20)
            .reset_index(drop=True)
        )
        st.dataframe(_presentational_dataframe(ranking), hide_index=True, use_container_width=True)


def _sidebar_navigation() -> str:
    st.sidebar.markdown(
        """
        <style>
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #f7fbff 0%, #eef4fa 100%);
            border-right: 1px solid rgba(18, 52, 86, 0.10);
        }
        section[data-testid="stSidebar"] .block-container {
            padding-top: 0.9rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        .lotoia-sidebar-fallback {
            font-weight: 900;
            color: #123456;
            margin-bottom: 0.6rem;
            line-height: 1;
            text-align: center;
            font-size: 1.15rem;
            letter-spacing: 0.12em;
        }
        section[data-testid="stSidebar"] img {
            width: 92% !important;
            max-width: 340px !important;
            display: block;
            margin: 0 auto 0.4rem auto;
        }
        .lotoia-sidebar-divider {
            border-top: 1px solid rgba(18, 52, 86, 0.14);
            margin: 0.85rem 0;
        }
        .lotoia-nav-hint {
            font-size: 0.74rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #7a8795;
            margin-bottom: 0.65rem;
        }
        section[data-testid="stSidebar"] div[data-baseweb="radio"] {
            margin-top: -0.2rem;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )
    _render_sidebar_logo()
    st.sidebar.markdown('<div class="lotoia-sidebar-divider"></div>', unsafe_allow_html=True)
    return st.sidebar.radio(
        "Navegacao",
        options=PAGES,
        format_func=lambda key: LABELS.get(key, key),
        label_visibility="collapsed",
    )


def _render_sidebar_dispatch(page: str, draws) -> None:
    st.write(f"DEBUG PAGE => {page}")

    routes: dict[str, Any] = {
        "geracao_jogos": render_generation_page,
        "conferir_jogos": render_check_page,
        "estatisticas_historicas": lambda: render_statistics_page(draws),
        "backtesting": render_backtesting_page,
        "calibracao_experimental": render_calibration_page,
        "benchmark_cientifico": render_benchmark_page,
        "historico_experimental": render_history_page,
        "relatorios": render_reports_page,
        "historical_intelligence": lambda: render_historical_intelligence_page(draws),
        "analytics_intelligence": render_analytics_intelligence_page,
        "ml_intelligence": render_ml_intelligence_page,
        "jogo_expandido_experimental": render_expansion_experimental_page,
        "ml_governance": render_ml_governance_page,
        "observability": render_observability_page,
        "workflows": render_workflows_page,
        "reports_engine": render_reports_engine_page,
    }
    handler = routes.get(page)
    if handler is not None:
        try:
            handler()
        except Exception as exc:
            _record_operational_log("dashboard_route", "failed", 0.0, {"page": page, "error": str(exc)})
            st.error(f"Falha controlada na rota {page}.")
            st.caption(f"Contexto técnico: {exc}")
            raise
    else:
        st.warning(f"Rota sem handler: {page}")


def render_historical_intelligence_page(draws) -> None:
    with st.container(border=True):
        _section_header("Historico Analitico", "Leitura historica para combinacoes, recorrencia e proximidade estatistica.")
        if st.session_state.get("last_generation_games"):
            games = st.session_state["last_generation_games"]
        else:
            summary = summarize_draws(draws)
            top_numbers = [int(number) for number, _ in list(summary["frequencies"].items())[:15]]
            games = [{"numbers": top_numbers}]

        analytics = _historical_analytics(games)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Jogos inditos", analytics["unique_games"])
        c2.metric("Jogos recorrentes", analytics["recurring_games"])
        c3.metric("Raridade estrutural mdia", f"{analytics['avg_rarity']:.4f}")
        c4.metric("Proximidade mdia", f"{analytics['avg_proximity']:.4f}")
        st.caption(
            "Perfis gerados: "
            + ", ".join(
                f"{profile}: {analytics['profile_percentages'].get(profile, 0):.1f}%"
                for profile in GENERATION_PROFILE_RATIOS
            )
        )

        match_raw_df = _historical_intelligence_dataframe(games)
        match_df = _presentational_historical_intelligence_dataframe(games)
        st.subheader("Tabela histrica")
        st.dataframe(match_df, hide_index=True, use_container_width=True)

        tabs = st.tabs(["Recorrentes", "Hibridos", "Caoticos"])
        for tab, profile in zip(tabs, GENERATION_PROFILE_RATIOS, strict=True):
            with tab:
                st.dataframe(
                    _presentational_historical_intelligence_dataframe(
                        [
                            game
                            for game in games
                            if _historical_intelligence_dataframe([game]).iloc[0]["profile_type"] == profile
                        ]
                    ),
                    hide_index=True,
                    use_container_width=True,
                )

        st.subheader("Concursos similares")
        similar_rows = []
        for _, row in match_df.iterrows():
            similar_rows.append(
                {
                    "dezenas": row["dezenas"],
                    "Forca Historica": row["Forca Historica"],
                    "Ultimo concurso": row["last_contest"],
                    "Concursos similares": row["similar_contests"],
                }
            )
        st.dataframe(pd.DataFrame(similar_rows), hide_index=True, use_container_width=True)


def render_analytics_intelligence_page() -> None:
    with st.container(border=True):
        start_time = time.monotonic()
        _section_header("Analise Inteligente", "Leitura analitica com graficos, heatmaps e padroes historicos.")
        c1, c2, c3, c4 = st.columns(4)
        analytics_history = _analytics_base_tables()["history"]
        c1.metric("Concursos", len(analytics_history))
        c2.metric("Padrões", len(_recurrence_table()))
        c3.metric("Média soma", f"{analytics_history['soma'].mean():.2f}" if not analytics_history.empty else "0.00")
        c4.metric("Recorrência média", f"{analytics_history['repeticao'].mean():.2f}" if not analytics_history.empty else "0.00")

        st.plotly_chart(_frequency_chart(), use_container_width=True)
        st.plotly_chart(_delay_chart(), use_container_width=True)
        st.plotly_chart(_odd_even_chart(), use_container_width=True)
        st.plotly_chart(_sum_chart(), use_container_width=True)
        st.plotly_chart(_distribution_chart_advanced(), use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(_recurrence_heatmap(), use_container_width=True)
            st.plotly_chart(_pattern_heatmap(), use_container_width=True)
        with col2:
            st.plotly_chart(_temporal_heatmap(), use_container_width=True)
            st.subheader("Padrões recorrentes")
            st.dataframe(_presentational_dataframe(_recurrence_table()), hide_index=True, use_container_width=True)
        duration_ms = (time.monotonic() - start_time) * 1000.0
        _record_operational_log("analytics", "success", duration_ms, {"source": "analytics_intelligence"})
        _record_performance_metric("analytics_ms", duration_ms, {"source": "analytics_intelligence"})


def render_ml_intelligence_page() -> None:
    with st.container(border=True):
        _section_header("Aprendizado Estatistico", "Score ML com validacao temporal e reranking interpretavel.")
        training = _ml_training_result()
        model = training["model"]
        validation = training["validation_metrics"]
        scored_games = training["scored_games"]
        reranked_games = training["reranked_games"]
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Model version", model.model_version)
        col2.metric("Score schema", model.feature_schema_version)
        col3.metric("Walk-forward", validation["splits"])
        col4.metric("Rows válidas", validation["rows"])

        st.subheader("Metricas do modelo")
        st.dataframe(_presentational_dataframe(_ml_features_table(model)), hide_index=True, use_container_width=True)

        scored_df = pd.DataFrame(
            [
                {
                    "contest": item["contest"] if isinstance(item, dict) else None,
                    "numbers": _format_numbers(item["numbers"]),
                    "score_ml": item.get("score_ml", 0),
                    "final_score": _score_value(item),
                    "hits": item.get("hits", 0),
                }
                for item in reranked_games
            ]
        )
        if not scored_df.empty:
            scored_df = scored_df.head(40)
        st.subheader("Ranking ML")
        st.dataframe(_presentational_dataframe(scored_df), hide_index=True, use_container_width=True)

        score_fig = go.Figure(
            data=[
                go.Bar(
                    x=scored_df["numbers"] if not scored_df.empty else [],
                    y=scored_df["score_ml"] if not scored_df.empty else [],
                    marker_color="#173b63",
                )
            ]
        )
        score_fig.update_layout(
            title="Score ML por jogo",
            xaxis_title="Jogo",
            yaxis_title="score_ml",
            margin={"l": 20, "r": 20, "t": 50, "b": 20},
        )
        st.plotly_chart(score_fig, use_container_width=True)

        val_df = pd.DataFrame(training["splits"])
        st.subheader("Validação walk-forward")
        st.dataframe(_presentational_dataframe(val_df), hide_index=True, use_container_width=True)
        st.info(
            f"Governança: temporal={validation['temporal_valid']} | linhas={validation['rows']} | modelo={validation['model_version']}"
        )


def render_ml_governance_page() -> None:
    with st.container(border=True):
        _section_header("Auditoria Tecnica", "Governanca de modelos, experimentos, versoes e snapshots.")
        training = _ml_training_result()
        payload = training["payload"]
        feature_rows = training["feature_rows"]
        paths = training["ml_report_paths"]
        snapshot_path = training["ml_snapshot"]
        model = training["model"]

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Modelo ativo", model.model_version)
        col2.metric("Experimentos", 1)
        col3.metric("Snapshots", len(list(ML_SNAPSHOTS_DIR.glob("*.json"))))
        col4.metric("Arquivos ML", len(list(ML_REPORTS_DIR.glob("*"))))

        st.subheader("Histórico de calibração")
        history_df = pd.DataFrame(
            [
                {
                    "timestamp": payload["timestamp"],
                    "model_version": payload["model_version"],
                    "feature_schema_version": payload["feature_schema_version"],
                    "experiment_rows": payload["experiment_rows"],
                    "walk_forward_splits": payload["walk_forward_splits"],
                    "temporal_valid": payload["temporal_valid"],
                }
            ]
        )
        st.dataframe(_presentational_dataframe(history_df), hide_index=True, use_container_width=True)

        st.subheader("Governança de features")
        st.dataframe(_presentational_dataframe(pd.DataFrame(feature_rows)), hide_index=True, use_container_width=True)

        st.subheader("Artefatos institucionais")
        artifacts = pd.DataFrame(
            [
                {"type": "json", "path": str(paths["json"])},
                {"type": "csv", "path": str(paths["csv"])},
                {"type": "pdf", "path": str(paths["pdf"])},
                {"type": "snapshot", "path": str(snapshot_path)},
            ]
        )
        st.dataframe(_presentational_dataframe(artifacts), hide_index=True, use_container_width=True)
        for _, row in artifacts.iterrows():
            artifact_path = Path(row["path"])
            if artifact_path.exists():
                st.download_button(
                    f"Baixar {artifact_path.suffix.upper().lstrip('.')}",
                    data=artifact_path.read_bytes(),
                    file_name=artifact_path.name,
                    key=f"ml_{artifact_path.name}",
                )


def render_generation_page() -> None:
    with st.container(border=True):
        _section_header("Gerar Jogos", "Geracao institucional com o fluxo operacional atual preservado.")
        executive_report = build_executive_analytical_report()
        historical_report = build_institutional_historical_intelligence()
        observability_report = load_observational_stabilization_report()
        render_generation_context(executive_report, historical_report, observability_report)
        lead_col1, lead_col2 = st.columns(2)
        first_name = lead_col1.text_input("Primeiro nome do lead", key="admin_first_name")
        whatsapp = lead_col2.text_input("WhatsApp do lead", key="admin_whatsapp")
        first_name = _safe_text(first_name, max_length=80)
        whatsapp = _safe_text(whatsapp, max_length=40)
        lead_ready = bool(first_name.strip() and whatsapp.strip())
        if not lead_ready:
            st.info("Informe primeiro nome e WhatsApp para habilitar a geracao.")
        st.markdown('<div class="lotoia-lead-hint">Lead institucional obrigatorio para rastreabilidade analitica.</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        count = col1.number_input("Quantidade", min_value=1, max_value=50, value=10)
        pool_size = col2.number_input("Pool do ranking", min_value=count, max_value=500, value=max(30, count))
        max_repeated = col3.number_input("Repeticao maxima", min_value=0, max_value=15, value=9)
        mode = st.radio("Modo", ["Ranking hibrido", "Multiplos jogos"], horizontal=True)
        if st.button("Gerar jogos", type="primary"):
            if not lead_ready:
                st.warning("Informe primeiro nome e WhatsApp para seguir com a geracao.")
                return
            start_time = time.monotonic()
            with st.spinner("Gerando jogos e anexando scores..."):
                try:
                    lead_id, first_name, whatsapp = _capture_generation_lead(first_name, whatsapp)
                except Exception as exc:
                    st.warning(str(exc))
                    return
                if mode == "Ranking hibrido":
                    payload = _cached_generate_best_games(int(count), int(pool_size))
                    games = payload["games"]
                else:
                    games = _cached_generate_multiple_games(int(count), int(max_repeated))
                    payload = {
                        "games": games,
                        "profile_counts": {
                            profile: sum(1 for game in games if game.get("profile_type") == profile)
                            for profile in GENERATION_PROFILE_RATIOS
                        },
                    }
                st.session_state["last_generation_games"] = games
            duration_ms = (time.monotonic() - start_time) * 1000.0
            generation_event_id = _persist_generation_events(
                first_name=first_name,
                whatsapp=whatsapp,
                games=games,
                duration_ms=duration_ms,
                strategy=mode,
                lead_id=lead_id,
            )
            dataframe = _games_dataframe(games)
            st.dataframe(dataframe, hide_index=True, use_container_width=True)
            st.plotly_chart(go.Figure(data=[go.Bar(x=dataframe["rank"], y=dataframe["final_score"], marker_color="#173b63")]).update_layout(title="Ranking por final_score", xaxis_title="Rank", yaxis_title="final_score"), use_container_width=True)
            st.session_state["last_generation_games"] = games
            st.session_state["last_generation_context"] = {
                "first_name": first_name.strip(),
                "whatsapp": whatsapp.strip(),
                "timestamp": _report_timestamp(),
            }
            generation_snapshot = _write_snapshot(
                "generation_snapshot",
                {
                    "context": st.session_state["last_generation_context"],
                    "games": games,
                    "historical": _historical_analytics(games),
                    "engine_version": "historical_recalibrated_v2",
                    "fallback_used": False,
                    "profile_distribution": payload.get("profile_counts", {}),
                },
            )
            _record_operational_log("generation", "success", duration_ms, {"games": len(games), "ml_enabled": False, "generation_event_id": generation_event_id})
            _record_performance_metric("generation_ms", duration_ms, {"games": len(games), "ml_enabled": False})
            _record_audit_trail("generation_snapshot", artifact_path=str(generation_snapshot), context={"games": len(games), "generation_event_id": generation_event_id})
            _invalidate_runtime_cache()
def render_check_page() -> None:
    with st.container(border=True):
        _section_header("Conferir Jogos", "Conferencia operacional contra concursos historicos carregados.")
        lead_col1, lead_col2 = st.columns(2)
        first_name = _safe_text(lead_col1.text_input("Primeiro nome do lead", key="check_first_name"), max_length=80)
        whatsapp = _safe_text(lead_col2.text_input("WhatsApp do lead", key="check_whatsapp"), max_length=40)
        col1, col2 = st.columns([1, 3])
        contest_id = col1.number_input("Concurso", min_value=1, step=1, value=max(1, int(_safe_last_contest()) if _safe_last_contest().isdigit() else 1))
        numbers_text = col2.text_area("Jogos", placeholder="01 02 03 04 05 06 07 08 09 10 11 12 13 14 15", height=220)
        if st.button("Conferir jogo", type="primary"):
            start_time = time.monotonic()
            try:
                games = _parse_check_games(numbers_text)
                contest_id_int = int(contest_id)
                _persist_lead(first_name, whatsapp)
                results = []
                for index, numbers in enumerate(games, start=1):
                    game_start = time.monotonic()
                    result = _check_game_against_contest(contest_id_int, numbers)
                    duration_ms = (time.monotonic() - game_start) * 1000.0
                    result["execution_time_ms"] = round(duration_ms, 2)
                    results.append({
                        "jogo": index,
                        "contest_id": contest_id_int,
                        "acertos": int(result["hits"]),
                        "dezenas": _format_numbers(numbers),
                        "dezenas_sorteadas": _format_numbers(result["draw_numbers"]),
                        "dezenas_acertadas": _format_numbers(result["correct_numbers"]) if result["correct_numbers"] else "-",
                        "execution_time_ms": round(duration_ms, 2),
                    })
                    connection, current_cursor = _sqlite_ensure_runtime_connection()
                    if connection is not None and current_cursor is not None:
                        current_cursor.execute(
                            """
                            INSERT INTO check_events (
                                first_name,
                                whatsapp,
                                contest_id,
                                hits,
                                execution_time_ms
                            )
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (first_name.strip(), whatsapp.strip(), contest_id_int, int(result["hits"]), duration_ms),
                        )
                        connection.commit()
                    check_row, check_payload = _build_check_report_payload(result, contest_id_int, numbers)
                    snapshot = _write_snapshot(
                        f"check_snapshot_{index}",
                        {
                            "context": {"first_name": first_name.strip(), "whatsapp": whatsapp.strip(), "timestamp": _report_timestamp(), "game_index": index},
                            "check": check_payload,
                        },
                    )
                    _record_operational_log("check", "success", duration_ms, {"contest_id": contest_id_int, "hits": int(result["hits"]), "game_index": index})
                    _record_performance_metric("check_ms", duration_ms, {"contest_id": contest_id_int, "hits": int(result["hits"]), "game_index": index})
                    _record_audit_trail("check_snapshot", artifact_path=str(snapshot), context={"contest_id": contest_id_int, "hits": int(result["hits"]), "game_index": index})
                    _invalidate_runtime_cache()
                summary = pd.DataFrame(results).sort_values(["acertos", "jogo"], ascending=[False, True]).reset_index(drop=True)
                st.session_state["last_check_context"] = {
                    "timestamp": _report_timestamp(),
                    "contest_id": contest_id_int,
                    "games": results,
                }
                st.metric("Jogos conferidos", len(results))
                st.metric("Maior acerto", int(summary["acertos"].max()) if not summary.empty else 0)
                st.dataframe(summary, hide_index=True, use_container_width=True)
                st.subheader("Ranking por acertos")
                st.dataframe(summary[["jogo", "acertos", "contest_id"]], hide_index=True, use_container_width=True)
            except Exception as exc:
                duration_ms = (time.monotonic() - start_time) * 1000.0
                _record_operational_log("check", "failed", duration_ms, {"contest_id": int(contest_id), "error": str(exc)})
                st.warning(str(exc))



def render_statistics_page(draws) -> None:
    with st.container(border=True):
        _section_header("Resultados Passados", "Base histórica, frequências, atrasos e leituras estruturais do acervo.")
        summary = summarize_draws(draws)
        hot_cold = calculate_hot_cold_numbers(draws, window=20)
        stats = _cached_stats()
        col1, col2, col3 = st.columns(3)
        col1.metric("Concursos carregados", summary["total_draws"])
        col2.metric("Último concurso", summary["last_contest"]["contest"])
        col3.metric("Dezenas rastreadas", summary["numbers_tracked"])
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Dezenas quentes")
            st.dataframe(pd.DataFrame(hot_cold["hot"]), hide_index=True, use_container_width=True)
        with col2:
            st.subheader("Dezenas frias")
            st.dataframe(pd.DataFrame(hot_cold["cold"]), hide_index=True, use_container_width=True)
        frequency = sorted(summary["frequencies"].items(), key=lambda item: item[1], reverse=True)
        st.plotly_chart(go.Figure(data=[go.Bar(x=[number for number, _ in frequency], y=[count for _, count in frequency], marker_color="#1f5f8b")]).update_layout(title="Frequência histórica", xaxis_title="Dezena", yaxis_title="Quantidade"), use_container_width=True)
        tabs = st.tabs(["Frequência", "Atrasos", "Duos", "Ternos", "Quadras", "Quinas", "Senas"])
        tables = [("dezena", stats["frequency"]), ("dezena", stats["delay"]), ("duo", stats["duos"]), ("terno", stats["ternos"]), ("quadra", stats["quadras"]), ("quina", stats["quinas"]), ("sena", stats["senas"])]
        for tab, (key_name, table_stats) in zip(tabs, tables, strict=True):
            with tab:
                if table_stats:
                    st.dataframe(_stats_table(table_stats, key_name), hide_index=True, use_container_width=True)
                else:
                    st.info("Arquivo estatístico ainda não encontrado.")


def render_backtesting_page() -> BacktestResult | None:
    with st.container(border=True):
        _section_header("Testar Estratégia", "Backtesting temporal e avaliação histórica com leitura analítica.")
        col1, col2, col3, col4, col5 = st.columns(5)
        contests = col1.number_input("Concursos", min_value=1, max_value=100, value=5)
        pool_size = col2.number_input("Pool", min_value=1, max_value=500, value=30)
        games_count = col3.number_input("Jogos", min_value=1, max_value=100, value=10)
        history_window = col4.number_input("Histórico", min_value=1, max_value=1000, value=200)
        seed = col5.number_input("Seed", min_value=0, max_value=999_999, value=42)
        if games_count > pool_size:
            st.warning("O pool precisa ser maior ou igual à quantidade de jogos.")
            return None
        if st.button("Executar backtest", type="primary"):
            with st.spinner("Executando backtest histórico..."):
                result = _safe_backtest(contests=int(contests), games_count=int(games_count), pool_size=int(pool_size), history_window=int(history_window), seed=int(seed))
            _metric_row(result)
            if result.total_games == 0:
                st.warning("Backtest em modo degradado: não foi possível gerar candidatos suficientes nesta configuração.")
                return result
            st.plotly_chart(_distribution_chart(result.hit_distribution), use_container_width=True)
            st.plotly_chart(_score_correlation_chart(result), use_container_width=True)
            st.plotly_chart(_hits_by_contest_chart(result), use_container_width=True)
            st.subheader("Jogos avaliados")
            st.dataframe(_backtest_games_dataframe(result), hide_index=True, use_container_width=True)
            return result
    return None


def render_workflows_page() -> None:
    with st.container(border=True):
        _section_header("Fluxos Operacionais", "Orquestração governada de sincronização, reconciliação, telemetria e fechamento diário.")
        workflow_dashboard = build_workflow_dashboard()
        workflow_summary = workflow_dashboard.get("summary", {})
        workflow_health = workflow_dashboard.get("health", {})
        dash_col1, dash_col2, dash_col3, dash_col4 = st.columns(4)
        dash_col1.metric("Workflows", workflow_summary.get("workflow_count", 0))
        dash_col2.metric("Etapas", workflow_summary.get("step_count", 0))
        dash_col3.metric("Falhas", workflow_summary.get("failure_count", 0))
        dash_col4.metric("Retries", workflow_summary.get("retry_count", 0))
        st.caption(
            f"Status: {workflow_summary.get('workflow_status', '-')}"
            f" | Saúde: {workflow_health.get('status', '-')}"
            f" | Estabilidade runtime: {workflow_health.get('stability_score', 0.0):.2f}"
        )
        if workflow_dashboard.get("alerts"):
            st.dataframe(
                _presentational_dataframe(pd.DataFrame(workflow_dashboard.get("alerts", []))),
                hide_index=True,
                use_container_width=True,
            )
        action_engine = WorkflowEngine()
        action_cols = st.columns(3)
        if action_cols[0].button("Sincronizar agora", use_container_width=True):
            sync_snapshot = action_engine.run_sync_workflow(trigger="dashboard")
            st.success(f"Sincronizacao concluida: {sync_snapshot.state}")
            st.json(sync_snapshot.to_dict())
        if action_cols[1].button("Executar ciclo agendado", use_container_width=True):
            cycle_snapshot = action_engine.run_schedule_cycle()
            st.success(f"Ciclo executado: {cycle_snapshot.get('status', 'idle')}")
            st.json(cycle_snapshot)
        if action_cols[2].button("Atualizar telemetria", use_container_width=True):
            st.rerun()
        st.subheader("Workflows ativos")
        if workflow_dashboard.get("live_workflows"):
            st.dataframe(
                _presentational_dataframe(pd.DataFrame(workflow_dashboard.get("live_workflows", []))),
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("Nenhum workflow ativo no momento.")


def render_calibration_page() -> None:
    with st.container(border=True):
        _section_header("Estrategias Operacionais", "Calibracao experimental com pesos temporarios e avaliacao restauravel.")
        col1, col2, col3, col4, col5 = st.columns(5)
        contests = col1.number_input("Concursos", min_value=1, max_value=50, value=3, key="cal_contests")
        games_count = col2.number_input("Jogos", min_value=1, max_value=50, value=5, key="cal_games")
        pool_size = col3.number_input("Pool", min_value=1, max_value=200, value=15, key="cal_pool")
        history_window = col4.number_input("Histórico", min_value=1, max_value=1000, value=150, key="cal_hist")
        seed = col5.number_input("Seed", min_value=0, max_value=999_999, value=42, key="cal_seed")
        weight_cols = st.columns(4)
        weights = {
            "duo": weight_cols[0].number_input("Duo", min_value=0.0, value=15.0),
            "terno": weight_cols[1].number_input("Terno", min_value=0.0, value=20.0),
            "quadra": weight_cols[2].number_input("Quadra", min_value=0.0, value=25.0),
            "quina": weight_cols[3].number_input("Quina", min_value=0.0, value=20.0),
            "delay": weight_cols[0].number_input("Delay", min_value=0.0, value=10.0),
            "frequency": weight_cols[1].number_input("Frequência", min_value=0.0, value=5.0),
            "sum": weight_cols[2].number_input("Soma", min_value=0.0, value=3.0),
            "sequence": weight_cols[3].number_input("Sequência", min_value=0.0, value=2.0),
        }
        st.metric("Soma dos pesos", sum(weights.values()))
        if games_count > pool_size:
            st.warning("O pool precisa ser maior ou igual à quantidade de jogos.")
            return
        if st.button("Comparar configurações", type="primary"):
            with st.spinner("Executando calibração experimental..."):
                result = _cached_calibration(weights, int(contests), int(games_count), int(pool_size), int(history_window), int(seed))
            if not result.get("evaluations"):
                st.warning("Calibração sem avaliações disponíveis nesta configuração.")
                return
            evaluations = result["evaluations"]
            st.plotly_chart(_configuration_chart(result), use_container_width=True)
            st.dataframe(pd.DataFrame([{"configuracao": evaluation["configuration"], "media_acertos": evaluation["average_hits"], "correlacao": evaluation["final_score_hit_correlation"], "desvio_padrao": evaluation["hit_standard_deviation"], "peso_total": evaluation["total_weight"]} for evaluation in evaluations]), hide_index=True, use_container_width=True)
            st.info(f"Melhor configuração nesta amostra: {result['best_configuration']}")


def render_benchmark_page() -> None:
    with st.container(border=True):
        _section_header("Comparativos Operacionais", "Benchmark cientifico para leitura comparativa entre estrategias.")
        col1, col2, col3, col4, col5 = st.columns(5)
        contests = col1.number_input("Concursos", min_value=1, max_value=100, value=5, key="bench_contests")
        games_count = col2.number_input("Jogos", min_value=1, max_value=100, value=5, key="bench_games")
        pool_size = col3.number_input("Pool LotoIA", min_value=1, max_value=500, value=20, key="bench_pool")
        history_window = col4.number_input("Histórico", min_value=1, max_value=1000, value=200, key="bench_hist")
        seed = col5.number_input("Seed", min_value=0, max_value=999_999, value=42, key="bench_seed")
        if games_count > pool_size:
            st.warning("O pool do LotoIA precisa ser maior ou igual à quantidade de jogos.")
            return
        if st.button("Executar benchmark", type="primary"):
            with st.spinner("Executando comparação controlada..."):
                result = _cached_benchmark(int(contests), int(games_count), int(pool_size), int(history_window), int(seed))
            summary = _benchmark_summary_dataframe(result)
            comparisons = _benchmark_comparison_dataframe(result)
            lotoia = result.strategies["lotoia_engine"]
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Concursos", result.contests_analyzed)
            col2.metric("Jogos por estratégia", result.games_per_contest)
            col3.metric("Média LotoIA", f"{lotoia['average_hits']:.2f}")
            col4.metric("Desvio LotoIA", f"{lotoia['standard_deviation']:.2f}")
            st.plotly_chart(_benchmark_average_chart(result), use_container_width=True)
            st.plotly_chart(_benchmark_evolution_chart(result), use_container_width=True)
            st.subheader("Ranking das estratégias")
            st.dataframe(summary, hide_index=True, use_container_width=True)
            st.subheader("Comparações estatísticas")
            st.dataframe(comparisons, hide_index=True, use_container_width=True)
            st.info(f"Relatorios salvos em: {result.report_paths.get('json', 'reports/benchmark')}")


def render_expansion_experimental_page() -> None:
    with st.container(border=True):
        _section_header(
            "Jogo Expandido",
            "Validacao operacional interna do motor combinatorio, restrita a 16 e 17 dezenas.",
        )
        st.warning("Modo interno: 18, 19 e 20 dezenas permanecem desabilitadas no ADMIN.")
        selected_count = st.selectbox(
            "Quantidade de dezenas",
            options=list(ADMIN_EXPANSION_ALLOWED_SIZES),
            index=0,
            key="admin_expansion_selected_count",
        )
        default_numbers = _default_admin_expansion_numbers(int(selected_count))
        numbers_text = st.text_input("Dezenas", value=default_numbers, key=f"admin_expansion_numbers_{selected_count}")
        preview_limit = st.slider(
            "Limite de preview",
            min_value=16,
            max_value=ADMIN_EXPANSION_PREVIEW_LIMIT,
            value=ADMIN_EXPANSION_PREVIEW_LIMIT,
            step=10,
            key="admin_expansion_preview_limit",
        )

        try:
            numbers = _parse_admin_expansion_numbers(numbers_text)
            estimate = estimate_expansion(numbers)
        except Exception as exc:
            st.error(str(exc))
            _record_operational_log("admin_expansion_experimental", "blocked", 0.0, {"error": str(exc)})
            return

        col1, col2, col3 = st.columns(3)
        col1.metric("Dezenas", len(numbers))
        col2.metric("Apostas internas", f"{estimate['total_combinations']:,}".replace(",", "."))
        col3.metric("Custo estimado", f"R$ {float(estimate['estimated_cost']):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        if st.button("Gerar preview experimental", type="primary"):
            try:
                with st.spinner("Gerando preview com guardrails operacionais..."):
                    st.session_state["admin_last_expansion_experimental"] = _run_admin_expansion(
                        numbers,
                        preview_limit=int(preview_limit),
                    )
            except Exception as exc:
                st.error("Falha controlada no motor combinatorio experimental.")
                st.caption(str(exc))
                _record_operational_log("admin_expansion_experimental", "failed", 0.0, {"error": str(exc)})
                return

        result = st.session_state.get("admin_last_expansion_experimental")
        if not result:
            return

        st.success(f"Preview disponivel: {result['generated_count']} de {result['total_combinations']} apostas.")
        if result.get("stopped_reason"):
            st.info("Preview limitado de forma controlada para preservar runtime e memoria.")

        combinations = result["combinations"]
        page_count = max(1, (len(combinations) + ADMIN_EXPANSION_PAGE_SIZE - 1) // ADMIN_EXPANSION_PAGE_SIZE)
        page = st.number_input("Pagina", min_value=1, max_value=page_count, value=1, key="admin_expansion_page")
        start = (int(page) - 1) * ADMIN_EXPANSION_PAGE_SIZE
        end = start + ADMIN_EXPANSION_PAGE_SIZE
        dataframe = _admin_expansion_dataframe(combinations[start:end])
        st.dataframe(dataframe, hide_index=True, use_container_width=True)

        export_dataframe = _admin_expansion_dataframe(combinations)
        csv_path = _export_csv(
            artifact_path(REPORTS_DIR, ArtifactKind.REPORT, "admin_expansion_experimental", "csv"),
            export_dataframe,
        )
        pdf_path = _save_pdf_report(
            artifact_path(REPORTS_DIR, ArtifactKind.REPORT, "admin_expansion_experimental", "pdf"),
            "LotoIA - Jogo Expandido",
            [
                f"Dezenas selecionadas: {_format_numbers(result['selected_numbers'])}",
                f"Apostas internas: {result['total_combinations']}",
                f"Custo estimado: R$ {float(result['estimated_cost']):.2f}",
                f"Preview gerado: {result['generated_count']}",
                f"Runtime ms: {result['runtime_ms']}",
                "Restricao ADMIN: apenas 16 e 17 dezenas.",
            ],
            export_dataframe,
        )
        csv_bytes = _safe_download_bytes(csv_path)
        pdf_bytes = _safe_download_bytes(pdf_path)
        if csv_bytes is not None:
            st.download_button("Exportar CSV", data=csv_bytes, file_name=csv_path.name, mime="text/csv")
        if pdf_bytes is not None:
            st.download_button("Exportar PDF", data=pdf_bytes, file_name=pdf_path.name, mime="application/pdf")


def render_history_page() -> None:
    with st.container(border=True):
        _section_header("Testes Operacionais", "Historico operacional, eventos persistidos e analises atuais.")
        runs = _cached_runs()
        benchmark_runs = runs["benchmark"]
        backtest_runs = runs["backtest"]
        calibration_runs = runs["calibration"]
        gen_df = _load_admin_events("generation_events")
        check_df = _load_admin_events("check_events")
        col1, col2, col3 = st.columns(3)
        col1.metric("Benchmarks", len(benchmark_runs))
        col2.metric("Backtests", len(backtest_runs))
        col3.metric("Calibrações", len(calibration_runs))
        st.markdown("---")
        st.subheader("generation_events")
        st.dataframe(gen_df, use_container_width=True, hide_index=True)
        st.subheader("check_events")
        st.dataframe(check_df, use_container_width=True, hide_index=True)
        tabs = st.tabs(["Benchmarks", "Backtests", "Calibrações"])
        with tabs[0]:
            if benchmark_runs:
                st.plotly_chart(_historical_metric_chart(benchmark_runs, "lotoia_average_hits", "Média LotoIA por benchmark"), use_container_width=True)
                st.dataframe(_runs_dataframe(benchmark_runs, ["id", "created_at", "contests", "games_per_contest", "lotoia_average_hits", "filtered_average_hits", "random_average_hits", "superiority_rate", "average_advantage", "report_path"]), hide_index=True, use_container_width=True)
            else:
                st.info("Nenhum benchmark persistido ainda.")
        with tabs[1]:
            if backtest_runs:
                st.plotly_chart(_historical_metric_chart(backtest_runs, "average_hits", "Média por backtest"), use_container_width=True)
                st.dataframe(_runs_dataframe(backtest_runs, ["id", "created_at", "contests", "games_per_contest", "average_hits", "correlation", "report_path"]), hide_index=True, use_container_width=True)
            else:
                st.info("Nenhum backtest persistido ainda.")
        with tabs[2]:
            if calibration_runs:
                st.plotly_chart(_historical_metric_chart(calibration_runs, "average_hits", "Média por calibração"), use_container_width=True)
                st.dataframe(_runs_dataframe(calibration_runs, ["id", "created_at", "average_hits", "correlation", "report_path"]), hide_index=True, use_container_width=True)
            else:
                st.info("Nenhuma calibração persistida ainda.")


def render_reports_page() -> None:
    with st.container(border=True):
        _section_header("Analiticas Persistidas", "Saidas analiticas persistidas e artefatos gerados pela operacao.")
        _ensure_reports_dirs()
        col1, col2, col3, col4, col5 = st.columns(5)
        contests = col1.number_input("Concursos", min_value=1, max_value=50, value=3, key="rep_contests")
        games_count = col2.number_input("Jogos", min_value=1, max_value=50, value=5, key="rep_games")
        pool_size = col3.number_input("Pool", min_value=1, max_value=200, value=15, key="rep_pool")
        history_window = col4.number_input("Histórico", min_value=1, max_value=1000, value=150, key="rep_hist")
        seed = col5.number_input("Seed", min_value=0, max_value=999_999, value=42, key="rep_seed")
        if st.button("Gerar relatório", type="primary"):
            start_time = time.monotonic()
            with st.spinner("Gerando relatório analítico..."):
                result = _safe_backtest(contests=int(contests), games_count=int(games_count), pool_size=int(pool_size), history_window=int(history_window), seed=int(seed))
                if result.total_games == 0:
                    st.warning("Relatório em modo degradado: backtest sem candidatos suficientes.")
                    return
                report = generate_backtest_report(result=result, output_dir=REPORTS_DIR)
                snapshot = _write_snapshot(
                    "backtest_snapshot",
                    {
                        "timestamp": _report_timestamp(),
                        "type": "backtest",
                        "report": report.to_dict(),
                        "backtest": result.to_dict(),
                    },
                )
                st.session_state["last_report_paths"] = {
                    "json": report.json_path,
                    "snapshot": snapshot,
                }
                duration_ms = (time.monotonic() - start_time) * 1000.0
                _record_operational_log("report", "success", duration_ms, {"output_dir": str(report.output_dir)})
                _record_performance_metric("report_ms", duration_ms, {"output_dir": str(report.output_dir)})
                _record_audit_trail("report_export", artifact_path=str(report.json_path), context={"output_dir": str(report.output_dir)})
            st.success(f"Relatório gerado em {report.output_dir}")
        files = sorted(path for path in REPORTS_DIR.glob("*") if path.is_file())
        if not files:
            st.info("Nenhum relatório gerado ainda.")
            return
        st.subheader("Arquivos disponíveis")
        for path in files:
            col1, col2 = st.columns([3, 1])
            col1.write(str(path))
            download_bytes = _safe_download_bytes(path)
            if download_bytes is not None:
                col2.download_button("Baixar", data=download_bytes, file_name=path.name, key=f"download_{path.name}")
        html_files = [path for path in files if path.suffix.lower() == ".html"]
        if html_files:
            selected = st.selectbox("Gráfico HTML", html_files, format_func=lambda path: path.name)
            st.components.v1.html(selected.read_text(encoding="utf-8"), height=520, scrolling=True)
        json_files = [path for path in files if path.suffix.lower() == ".json"]
        if json_files:
            selected_json = st.selectbox("JSON", json_files, format_func=lambda path: path.name)
            st.json(json.loads(selected_json.read_text(encoding="utf-8")))


def _latest_generation_games() -> list[dict[str, Any]]:
    return st.session_state.get("last_generation_games", [])


def _latest_check_context() -> dict[str, Any]:
    return st.session_state.get("last_check_context", {})


def render_reports_engine_page() -> None:
    with st.container(border=True):
        _section_header("Relatorios Gerais", "Exportacoes institucionais, relatorios recentes e snapshots operacionais.")
        latest_games = _latest_generation_games()
        latest_check = _latest_check_context()
        lifecycle_engine = OperationalLifecycleEngine(DEFAULT_DATABASE_PATH)
        lifecycle_dashboard = lifecycle_engine.build_dashboard()
        lifecycle_telemetry = lifecycle_engine.build_telemetry()
        lifecycle_analytics = lifecycle_engine.build_post_draw_analytics()
        col1, col2, col3 = st.columns(3)
        col1.metric("Snapshots", len(list(REPORTS_SNAPSHOTS_DIR.glob("*.json"))))
        col2.metric("Última geração", "sim" if latest_games else "não")
        col3.metric("Última conferência", "sim" if latest_check else "não")

        if latest_games:
            gen_df, gen_payload = _build_generation_report_payload(latest_games)
            generation_pdf = _save_pdf_report(
                artifact_path(REPORTS_DIR, ArtifactKind.REPORT, "generation", "pdf"),
                "LotoIA - Generation Report",
                [
                    f"Timestamp: {gen_payload['timestamp']}",
                    f"Total de jogos: {len(latest_games)}",
                    f"Jogos inéditos: {gen_payload['analytics']['unique_games']}",
                    f"Jogos recorrentes: {gen_payload['analytics']['recurring_games']}",
                    f"Raridade média: {gen_payload['analytics']['avg_rarity']}",
                    f"Proximidade média: {gen_payload['analytics']['avg_proximity']}",
                ],
                gen_df,
            )
            gen_csv = _export_csv(artifact_path(REPORTS_DIR, ArtifactKind.REPORT, "generation", "csv"), gen_df)
            pdf_bytes = _safe_download_bytes(generation_pdf)
            csv_bytes = _safe_download_bytes(gen_csv)
            if pdf_bytes is not None:
                st.download_button("Baixar PDF da geração", data=pdf_bytes, file_name=generation_pdf.name)
            if csv_bytes is not None:
                st.download_button("Baixar CSV da geração", data=csv_bytes, file_name=gen_csv.name)

        if latest_check:
            check_row = pd.DataFrame([latest_check])
            check_pdf = _save_pdf_report(
                artifact_path(REPORTS_DIR, ArtifactKind.REPORT, "check", "pdf"),
                "LotoIA - Check Report",
                [
                    f"Timestamp: {latest_check.get('timestamp', _report_timestamp())}",
                    f"Concurso: {latest_check.get('contest_id', '-')}",
                    f"Acertos: {latest_check.get('hits', '-')}",
                ],
                check_row,
            )
            check_csv = _export_csv(artifact_path(REPORTS_DIR, ArtifactKind.REPORT, "check", "csv"), check_row)
            pdf_bytes = _safe_download_bytes(check_pdf)
            csv_bytes = _safe_download_bytes(check_csv)
            if pdf_bytes is not None:
                st.download_button("Baixar PDF da conferência", data=pdf_bytes, file_name=check_pdf.name)
            if csv_bytes is not None:
                st.download_button("Baixar CSV da conferência", data=csv_bytes, file_name=check_csv.name)

        st.subheader("Snapshots")
        snapshots = sorted(REPORTS_SNAPSHOTS_DIR.glob("*.json"), reverse=True)
        if snapshots:
            for path in snapshots[:10]:
                st.write(str(path))
                snapshot_bytes = _safe_download_bytes(path)
                if snapshot_bytes is not None:
                    st.download_button("Baixar snapshot", data=snapshot_bytes, file_name=path.name, key=f"snap_{path.name}")
        else:
            st.info("Nenhum snapshot institucional disponível ainda.")

        st.subheader("Dashboard operacional pós-sorteio")
        dash_col1, dash_col2, dash_col3, dash_col4 = st.columns(4)
        dash_col1.metric("Execuções", lifecycle_dashboard.total_runs)
        dash_col2.metric("Jogos reconciliados", lifecycle_dashboard.total_games)
        dash_col3.metric("Premiados", lifecycle_dashboard.prize_count)
        dash_col4.metric("Melhor acerto", lifecycle_dashboard.best_hits)
        st.caption(
            f"Último concurso reconciliado: {lifecycle_dashboard.latest_contest or '-'} | "
            f"Status: {lifecycle_dashboard.status}"
        )
        st.caption(
            f"Telemetria: sync={lifecycle_telemetry['sync_runs']} | gerações={lifecycle_telemetry['generated_games']} | "
            f"reconciliações={lifecycle_telemetry['reconciliation_runs']} | fechamento={lifecycle_telemetry['operational_status']}"
        )
        if lifecycle_dashboard.post_draw_notes:
            st.write(" | ".join(lifecycle_dashboard.post_draw_notes))
        if lifecycle_analytics is not None:
            st.subheader("Analiticas pos-sorteio")
            analytics_col1, analytics_col2, analytics_col3, analytics_col4 = st.columns(4)
            analytics_col1.metric("Acertos medios", f"{lifecycle_analytics.average_hits:.2f}")
            analytics_col2.metric("Retencao", f"{lifecycle_analytics.retention_rate:.0%}")
            analytics_col3.metric("Prêmios", lifecycle_analytics.prize_count)
            analytics_col4.metric("Melhor acerto", max((int(key) for key in lifecycle_analytics.hit_distribution.keys()), default=0))
            st.caption(
                f"Concursos: {lifecycle_analytics.contest_id} | "
                f"Historico medio de acertos: {lifecycle_analytics.historical_average_hits:.2f} | "
                f"Historico medio de premios: {lifecycle_analytics.historical_average_prizes:.2f}"
            )
            if lifecycle_analytics.notes:
                st.write(" | ".join(lifecycle_analytics.notes))


def main() -> None:
    dashboard_start_time = time.monotonic()
    try:
        icon = Path("assets/favicon.ico")
        st.set_page_config(page_title="LotoIA", page_icon=str(icon) if icon.exists() else "L", layout="wide")
    except Exception:
        st.set_page_config(page_title="LotoIA", layout="wide")

    st.success("INSTITUTIONAL DASHBOARD ACTIVE")
    _render_sqlite_bootstrap_diagnostics()

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
        .stDataFrame, .stPlotlyChart { border-radius: 14px; }
        section[data-testid="stMain"] .stDataFrame {
            border: 1px solid rgba(18, 52, 86, 0.08);
            border-radius: 14px;
            overflow: hidden;
            background: #ffffff;
        }
        section[data-testid="stMain"] .stPlotlyChart {
            border: 1px solid rgba(18, 52, 86, 0.08);
            border-radius: 14px;
            overflow: hidden;
            background: #ffffff;
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
        .lotoia-kpi-marker {
            width: 22px;
            height: 22px;
            border-radius: 999px;
            background: rgba(18, 52, 86, 0.08);
            color: #123456;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.8rem;
            margin-bottom: 0.45rem;
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
        .lotoia-lead-hint {
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
        .lotoia-table-wrap {
            padding-top: 0.15rem;
            padding-bottom: 0.15rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    try:
        if LOGO_PATH.exists():
            st.sidebar.image(str(LOGO_PATH), use_container_width=True)
    except Exception:
        pass

    try:
        draws = _load_draws()
    except FileNotFoundError:
        st.warning(
            "Arquivo historico da LOTOFACIL nao encontrado. "
            f"Coloque o CSV em `{DEFAULT_HISTORY_PATH}` usando as colunas "
            "`concurso,data,d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14,d15`."
        )
        st.stop()
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    except Exception as exc:
        _record_operational_log("load_draws", "failed", 0.0, {"error": str(exc), "path": str(DEFAULT_HISTORY_PATH)})
        st.warning("O carregamento do acervo histórico encontrou uma falha controlada. O dashboard seguirá em modo seguro parcial.")
        draws = []

    try:
        page = _sidebar_navigation()
        _render_institutional_cockpit()
        _render_kpi_cards()
        st.markdown("---")
        _render_sidebar_dispatch(page, draws)
        st.markdown("---")
        _render_lead_intelligence()
        dashboard_duration_ms = (time.monotonic() - dashboard_start_time) * 1000.0
        _record_operational_log("dashboard", "success", dashboard_duration_ms, {"page": page})
        _record_performance_metric("dashboard_load_ms", dashboard_duration_ms, {"page": page})
    except Exception as exc:
        _record_operational_log("dashboard", "failed", 0.0, {"page": locals().get("page", "unknown"), "error": str(exc)})
        st.error("Falha operacional controlada no dashboard. O runtime permaneceu ativo.")
        st.caption(f"Contexto técnico: {exc}")
        st.markdown("---")
        _render_lead_intelligence()


if __name__ == "__main__":
    main()
