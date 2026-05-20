from __future__ import annotations

try:
    from . import _bootstrap  # type: ignore[import-not-found]  # noqa: F401
except ImportError:
    import _bootstrap  # type: ignore[no-redef]  # noqa: F401

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lotoia.backtesting import BacktestResult, run_backtest
from lotoia.benchmark import BenchmarkResult, run_benchmark
from lotoia.calibration.weight_calibrator import (
    WeightConfiguration,
    compare_weight_configurations,
)
from lotoia.data.loader import DEFAULT_HISTORY_PATH, load_draws_csv
from lotoia.database import list_runs
from lotoia.generator.basic_generator import generate_best_games, generate_multiple_games
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
    extract_score_ml_features,
    supervised_rerank_games,
)
from lotoia.reports import generate_backtest_report
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
from lotoia.statistics.basic import summarize_draws

DB_PATH = Path("lotoia.db")
LOGO_PATH = Path("assets/logo.png")
REPORTS_DIR = Path("reports")
REPORTS_SNAPSHOTS_DIR = REPORTS_DIR / "snapshots"
ML_REPORTS_DIR = REPORTS_DIR / "ml"
ML_SNAPSHOTS_DIR = ML_REPORTS_DIR / "snapshots"
SQLITE_BUSY_TIMEOUT_MS = 5000
ADMIN_EVENT_LIMIT = 200
LEAD_HISTORY_LIMIT = 5000
STREAMLIT_CACHE_TTL_SECONDS = 300
STREAMLIT_CACHE_MAX_ENTRIES = 16
ALLOWED_ADMIN_EVENT_TABLES = frozenset({"generation_events", "check_events", "operational_logs", "audit_trail", "leads"})
ALERT_GENERATION_MS = 5_000.0
ALERT_CHECK_MS = 3_000.0
ALERT_REPORT_MS = 15_000.0
ALERT_DASHBOARD_LOAD_MS = 8_000.0
ALERT_REPEATED_FAILURES = 3
ALERT_SQLITE_SIZE_BYTES = 256 * 1024 * 1024
ALERT_LOG_GROWTH_EVENTS = 1_000
SQLITE_BOOTSTRAP_DIAGNOSTICS: list[dict[str, Any]] = []

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()


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
    try:
        cursor.execute(statement)
        return True
    except sqlite3.Error as exc:
        diagnostic = _sqlite_classify_error(statement, exc, table_name)
        SQLITE_BOOTSTRAP_DIAGNOSTICS.append(diagnostic)
        try:
            _record_operational_log("sqlite", "failed", 0.0, diagnostic)
        except Exception:
            pass
        return False


def _sqlite_table_columns(table_name: str) -> set[str]:
    try:
        rows = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
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
        for candidate in ("generation_events", "check_events", "leads", "operational_logs", "audit_trail", "snapshots", "adaptive_governance_reports"):
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


_sqlite_execute_bootstrap(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
_sqlite_execute_bootstrap("PRAGMA journal_mode = WAL")
_sqlite_execute_bootstrap("PRAGMA synchronous = NORMAL")
_sqlite_ensure_admin_schema()
conn.commit()

PAGES = [
    "geracao_jogos",
    "estatisticas_historicas",
    "backtesting",
    "calibracao_experimental",
    "benchmark_cientifico",
    "historico_experimental",
    "relatorios",
]

LABELS = {
    "geracao_jogos": "Criar Jogos",
    "conferir_jogos": "Conferir Jogos",
    "estatisticas_historicas": "Resultados Passados",
    "backtesting": "Testar Estratégia",
    "calibracao_experimental": "Ajustar Estratégia",
    "benchmark_cientifico": "Comparar Métodos",
    "historico_experimental": "Meus Testes",
    "relatorios": "Relatórios",
}


def _format_numbers(numbers: list[int]) -> str:
    return " ".join(f"{number:02d}" for number in numbers)


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
        if isinstance(draw.get("numbers"), list):
            return [int(item) for item in draw["numbers"]]
        if isinstance(draw.get("dezenas"), list):
            return [int(item) for item in draw["dezenas"]]
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
    rarity = 1.0 - (len(occurrences) / total_draws) if total_draws else 1.0
    proximity = max((item["overlap"] / len(normalized) for item in similar_contests), default=0.0)
    score = round((rarity * 100) + (proximity * 25), 2)
    return {
        "numbers": normalized,
        "is_unique": len(occurrences) == 0,
        "occurrences": len(occurrences),
        "last_contest": occurrences[-1] if occurrences else None,
        "similar_contests": similar_contests,
        "rarity": round(rarity, 4),
        "proximity": round(proximity, 4),
        "historical_score": score,
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
                "rarity": match["rarity"],
                "repeat_count": match["occurrences"],
                "is_unique": match["is_unique"],
                "last_contest": match["last_contest"],
                "proximity": match["proximity"],
                "similar_contests": ", ".join(
                    str(item["contests"][-1]) for item in match["similar_contests"][:3] if item["contests"]
                ),
            }
        )
    return pd.DataFrame(rows)


def _historical_analytics(games: list[dict[str, Any]]) -> dict[str, Any]:
    matches = [_historical_match_engine(game["numbers"]) for game in games]
    return {
        "total_draws": int(_historical_dataset()["total_draws"]),
        "unique_games": sum(1 for match in matches if match["is_unique"]),
        "recurring_games": sum(1 for match in matches if not match["is_unique"]),
        "repeated_hits": sum(match["occurrences"] for match in matches),
        "avg_rarity": round(sum(match["rarity"] for match in matches) / len(matches), 4) if matches else 0.0,
        "avg_proximity": round(sum(match["proximity"] for match in matches) / len(matches), 4) if matches else 0.0,
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
        validation_metrics = {
            "rows": 0,
            "splits": 0,
            "temporal_valid": True,
            "model_version": empty_model.model_version,
            "feature_schema_version": empty_model.feature_schema_version,
            "status": "degraded_no_backtest_candidates",
        }
        payload = {
            "timestamp": _report_timestamp(),
            "model_version": empty_model.model_version,
            "feature_schema_version": empty_model.feature_schema_version,
            "experiment_rows": 0,
            "walk_forward_splits": 0,
            "temporal_valid": True,
            "validation_metrics": validation_metrics,
            "training_summary": {},
            "calibration": {},
            "attribution": [],
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
    }
    payload = {
        "timestamp": _report_timestamp(),
        "model_version": calibration_report.model_version,
        "feature_schema_version": calibration_report.feature_schema_version,
        "experiment_rows": len(rows),
        "walk_forward_splits": len(splits),
        "temporal_valid": validation_metrics["temporal_valid"],
        "validation_metrics": validation_metrics,
        "training_summary": dict(calibration_report.training_summary or {}),
        "features": feature_rows,
    }
    duration_ms = (time.monotonic() - start_time) * 1000.0
    ml_report_paths = _save_ml_report(payload, pd.DataFrame(feature_rows))
    ml_snapshot = _write_ml_snapshot(
        "ml_model_snapshot",
        {
            **payload,
            "calibration": calibration_report.calibration,
            "attribution": [item.as_dict() for item in calibration_report.attribution],
            "sample_row": sample_row,
        },
    )
    _record_operational_log("ml", "success", duration_ms, {"rows": len(rows), "splits": len(splits), "model_version": calibration_report.model_version})
    _record_performance_metric("ml_inference_ms", duration_ms, {"rows": len(rows), "splits": len(splits)})
    _record_audit_trail("ml_snapshot", artifact_path=str(ml_snapshot), context={"model_version": calibration_report.model_version})
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
        "ml_status": "failed" if ml_failures else ("ok" if not ml_logs.empty else "idle"),
        "cache_status": f"ttl={STREAMLIT_CACHE_TTL_SECONDS}s; max_entries={STREAMLIT_CACHE_MAX_ENTRIES}",
        "sqlite_size_bytes": _sqlite_size_bytes(),
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
    logs_total = int(_query_scalar("SELECT COUNT(*) FROM operational_logs"))
    logs_today = int(_query_scalar("SELECT COUNT(*) FROM operational_logs WHERE DATE(created_at) = DATE('now')"))
    return {
        "daily_generation_average": round(generation_total / generation_days, 2) if generation_days else 0.0,
        "check_volume": check_total,
        "ml_usage": ml_usage,
        "snapshot_volume": _snapshot_count(),
        "log_growth_today": logs_today,
        "log_total": logs_total,
        "sqlite_size_bytes": _sqlite_size_bytes(),
    }


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
        _section_header("Observability", "Logs institucionais, saúde cloud, auditoria e eventos operacionais recentes.")
        health = _runtime_health()
        operational = _operational_metrics()
        st.subheader("Operational Health Panel")
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
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Performance tracking")
            st.dataframe(_performance_metrics_table(), hide_index=True, use_container_width=True)
        with col2:
            st.subheader("Metricas operacionais")
            st.dataframe(
                pd.DataFrame(
                    [
                        {"metric": "daily_generation_average", "value": operational["daily_generation_average"]},
                        {"metric": "check_volume", "value": operational["check_volume"]},
                        {"metric": "ml_usage", "value": operational["ml_usage"]},
                        {"metric": "snapshot_volume", "value": operational["snapshot_volume"]},
                        {"metric": "log_growth_today", "value": operational["log_growth_today"]},
                        {"metric": "sqlite_size_bytes", "value": operational["sqlite_size_bytes"]},
                    ]
                ),
                hide_index=True,
                use_container_width=True,
            )
        st.subheader("Contratos de alerta")
        st.dataframe(_alert_contracts(), hide_index=True, use_container_width=True)
        st.subheader("Cloud monitoring")
        st.dataframe(_cloud_failure_table(), hide_index=True, use_container_width=True)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Tempo médio", f"{health['response_time_ms']:.2f} ms")
        col2.metric("Execuções", health["total_runs"])
        col3.metric("Falhas", health["failures"])
        col4.metric("Snapshots", health["snapshot_events"])

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Métricas runtime")
            st.dataframe(_observability_metrics_table(), hide_index=True, use_container_width=True)
        with col2:
            st.subheader("Saúde operacional")
            st.dataframe(
                pd.DataFrame(
                    [
                        {"metric": "avg_generation_ms", "value": health["avg_generation_ms"]},
                        {"metric": "avg_check_ms", "value": health["avg_check_ms"]},
                        {"metric": "ml_events", "value": health["ml_events"]},
                        {"metric": "report_events", "value": health["report_events"]},
                    ]
                ),
                hide_index=True,
                use_container_width=True,
            )

        tables = _observability_tables()
        st.subheader("Logs recentes")
        st.dataframe(tables["logs"].head(50), hide_index=True, use_container_width=True)
        st.subheader("Auditoria institucional")
        st.dataframe(tables["audit"].head(50), hide_index=True, use_container_width=True)


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
    cursor.execute(
        """
        INSERT INTO operational_logs (
            event_type,
            status,
            duration_ms,
            context_json
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            event_type,
            status,
            duration_ms,
            json.dumps(standardized_context, ensure_ascii=False),
        ),
    )
    conn.commit()


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
    cursor.execute(
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
    conn.commit()


def _ensure_log_tables() -> None:
    _record_operational_log("observability_boot", "ok", 0.0, {"source": "admin_app"})


def _ensure_reports_dirs() -> None:
    REPORTS_DIR.mkdir(exist_ok=True)
    REPORTS_SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    ML_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ML_SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def _sqlite_health_check() -> bool:
    try:
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        return bool(result and str(result[0]).lower() == "ok")
    except Exception:
        return False


def _sqlite_execute_safe(query: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor | None:
    try:
        conn.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
        return cursor.execute(query, params)
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
        "LotoIA - ML Governance Report",
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
        raise ValueError("Digite apenas dezenas numéricas separadas por espaço ou vírgula.") from exc
    if len(numbers) != 15:
        raise ValueError("Informe exatamente 15 dezenas para conferência.")
    if len(set(numbers)) != 15:
        raise ValueError("As dezenas da conferência não podem se repetir.")
    invalid = [number for number in numbers if number < 1 or number > 25]
    if invalid:
        raise ValueError("As dezenas devem estar entre 01 e 25.")
    return sorted(numbers)


def _find_draw_for_check(contest_id: int) -> Draw:
    draws = load_draws_csv(DEFAULT_HISTORY_PATH)
    if not draws:
        raise ValueError("Nenhum concurso histórico disponível para conferência.")
    latest_contest = max(draw.contest for draw in draws)
    if contest_id > latest_contest:
        raise ValueError(f"Concurso {contest_id} ainda não disponível. Último concurso carregado: {latest_contest}.")
    for draw in draws:
        if draw.contest == contest_id:
            return draw
    raise ValueError(f"Concurso {contest_id} não encontrado na base histórica.")


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
    return generate_best_games(count=count, pool_size=pool_size)


@st.cache_data(show_spinner=False, ttl=STREAMLIT_CACHE_TTL_SECONDS, max_entries=STREAMLIT_CACHE_MAX_ENTRIES)
def _cached_generate_multiple_games(count: int, max_repeated: int) -> list[dict[str, Any]]:
    return generate_multiple_games(count=count, max_repeated=max_repeated)


@st.cache_data(show_spinner=False, ttl=STREAMLIT_CACHE_TTL_SECONDS, max_entries=STREAMLIT_CACHE_MAX_ENTRIES)
def _cached_backtest(contests: int, games_count: int, pool_size: int, history_window: int, seed: int) -> BacktestResult:
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
    return run_benchmark(contests_analyzed=contests, games_count=games_count, pool_size=pool_size, history_window=history_window, seed=seed)


@st.cache_data(show_spinner=False, ttl=STREAMLIT_CACHE_TTL_SECONDS, max_entries=STREAMLIT_CACHE_MAX_ENTRIES)
def _cached_runs() -> dict[str, list[dict[str, Any]]]:
    return list_runs()


@st.cache_data(show_spinner=False, ttl=STREAMLIT_CACHE_TTL_SECONDS, max_entries=STREAMLIT_CACHE_MAX_ENTRIES)
def _load_admin_events(table_name: str) -> pd.DataFrame:
    if table_name not in ALLOWED_ADMIN_EVENT_TABLES:
        return pd.DataFrame()
    query = f"SELECT * FROM {table_name} ORDER BY created_at DESC, id DESC LIMIT {ADMIN_EVENT_LIMIT}"
    return pd.read_sql_query(query, conn)


def _lead_identifier(first_name: str, whatsapp: str) -> str:
    return f"{first_name.strip()} | {whatsapp.strip()}"


def _read_sql_query_safe(query: str, columns: list[str], params: tuple[Any, ...] = ()) -> pd.DataFrame:
    try:
        return pd.read_sql_query(query, conn, params=params)
    except Exception as exc:
        _record_operational_log("sqlite", "failed", 0.0, {"query": query[:80], "error": str(exc)})
        return pd.DataFrame(columns=columns)


def _persist_lead(first_name: str, whatsapp: str) -> None:
    if not first_name.strip() or not whatsapp.strip():
        return
    cursor.execute(
        """
        INSERT INTO leads (
            first_name,
            whatsapp
        )
        VALUES (?, ?)
        """,
        (first_name.strip(), whatsapp.strip()),
    )
    conn.commit()


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
        LIMIT ?
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
        LIMIT ?
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
        LIMIT ?
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
        return str(value) if value is not None else "-"
    except Exception:
        return "-"


def _safe_total_games() -> str:
    try:
        gen_cur = _sqlite_execute_safe("SELECT COUNT(*) FROM generation_events")
        check_cur = _sqlite_execute_safe("SELECT COUNT(*) FROM check_events")
        gen_row = gen_cur.fetchone() if gen_cur else None
        check_row = check_cur.fetchone() if check_cur else None
        total = int(gen_row[0] if gen_row else 0) + int(check_row[0] if check_row else 0)
        return str(total)
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
    last_contest = _safe_last_contest()
    total_games = _safe_total_games()
    col1, col2, col3, col4 = st.columns(4)
    cards = [
        (col1, "Gerações", gen_count, "Eventos persistidos em generation_events"),
        (col2, "Conferências", check_count, "Eventos persistidos em check_events"),
        (col3, "Último concurso", last_contest, "Maior concurso conferido"),
        (col4, "Jogos totais", total_games, "Total operacional registrado"),
    ]
    markers = ["▸", "▸", "▸", "▸"]
    for (column, label, value, caption), marker in zip(cards, markers, strict=True):
        with column:
            st.markdown(
                f"""
                <div class="lotoia-kpi-card">
                    <div class="lotoia-kpi-marker">{marker}</div>
                    <div class="lotoia-kpi-label">{label}</div>
                    <div class="lotoia-kpi-value">{value}</div>
                    <div class="lotoia-kpi-caption">{caption}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_lead_intelligence() -> None:
    analytics = _lead_analytics()
    history = _lead_history_dataframe()
    st.markdown("---")
    _section_header("Lead Intelligence", "Inteligência institucional por usuário, recorrência e padrão de uso.")
    a, b, c, d, e = st.columns(5)
    a.metric("Total leads", analytics["total_leads"])
    b.metric("Leads recorrentes", analytics["recurring_leads"])
    c.metric("Ativações ML", analytics["ml_activations"])
    d.metric("Gerações", analytics["volume_generations"])
    e.metric("Conferências", analytics["volume_checks"])
    st.subheader("Histórico institucional")
    st.dataframe(
        history,
        hide_index=True,
        use_container_width=True,
        column_config={
            "lead": "Lead",
            "first_name": "Nome",
            "whatsapp": "WhatsApp",
            "created_at": "Criado em",
            "origin": "Origem",
            "generations": "Gerações",
            "checks": "Conferências",
            "ml_activations": "ML",
            "last_generation_at": "Última geração",
            "last_check_at": "Última conferência",
            "recurrence_score": "Recorrência",
        },
    )
    if not history.empty:
        st.subheader("Ranking de uso")
        ranking = (
            history[["lead", "recurrence_score", "generations", "checks", "ml_activations"]]
            .head(20)
            .reset_index(drop=True)
        )
        st.dataframe(ranking, hide_index=True, use_container_width=True)


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
        .lotoia-sidebar-title {
            font-size: 1.55rem;
            font-weight: 900;
            letter-spacing: 0.10em;
            color: #123456;
            margin-bottom: 0.1rem;
            line-height: 1;
        }
        .lotoia-sidebar-subtitle {
            color: #5a6b7e;
            font-size: 0.82rem;
            margin-bottom: 0.95rem;
            line-height: 1.45;
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
    st.sidebar.markdown('<div class="lotoia-sidebar-title">LotoIA</div>', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="lotoia-sidebar-subtitle">Dashboard institucional anal?tico<br/>Leitura operacional, benchmarking e hist?rico</div>', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="lotoia-sidebar-divider"></div>', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="lotoia-nav-hint">Navega??o institucional</div>', unsafe_allow_html=True)
    return st.sidebar.radio(
        "Navega??o",
        options=[
            "geracao_jogos",
            "conferir_jogos",
            "estatisticas_historicas",
            "historical_intelligence",
            "analytics_intelligence",
            "ml_intelligence",
            "backtesting",
            "calibracao_experimental",
            "benchmark_cientifico",
            "historico_experimental",
            "relatorios",
            "ml_governance",
            "observability",
            "reports_engine",
        ],
        format_func=lambda key: {**LABELS, "historical_intelligence": "Historical Intelligence", "analytics_intelligence": "Analytics Intelligence", "ml_intelligence": "ML Intelligence", "ml_governance": "ML Governance", "observability": "Observability", "reports_engine": "Reports Engine"}.get(key, key),
        label_visibility="collapsed",
    )


def render_historical_intelligence_page(draws) -> None:
    with st.container(border=True):
        _section_header("Historical Intelligence", "Intelig?ncia hist?rica operacional para combina??es, recorr?ncia e proximidade estat?stica.")
        if st.session_state.get("last_generation_games"):
            games = st.session_state["last_generation_games"]
        else:
            summary = summarize_draws(draws)
            top_numbers = [int(number) for number, _ in list(summary["frequencies"].items())[:15]]
            games = [{"numbers": top_numbers}]

        analytics = _historical_analytics(games)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Jogos in?ditos", analytics["unique_games"])
        c2.metric("Jogos recorrentes", analytics["recurring_games"])
        c3.metric("Raridade m?dia", f"{analytics['avg_rarity']:.4f}")
        c4.metric("Proximidade m?dia", f"{analytics['avg_proximity']:.4f}")

        match_df = _historical_intelligence_dataframe(games)
        st.subheader("Tabela hist?rica")
        st.dataframe(match_df, hide_index=True, use_container_width=True)

        unique_df = match_df[match_df["is_unique"] == True]
        recurring_df = match_df[match_df["is_unique"] == False]

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Jogos in?ditos")
            st.dataframe(unique_df, hide_index=True, use_container_width=True)
        with col2:
            st.subheader("Jogos recorrentes")
            st.dataframe(recurring_df, hide_index=True, use_container_width=True)

        st.subheader("Concursos similares")
        similar_rows = []
        for _, row in match_df.iterrows():
            similar_rows.append(
                {
                    "dezenas": row["dezenas"],
                    "historical_score": row["historical_score"],
                    "last_contest": row["last_contest"],
                    "similar_contests": row["similar_contests"],
                }
            )
        st.dataframe(pd.DataFrame(similar_rows), hide_index=True, use_container_width=True)


def render_analytics_intelligence_page() -> None:
    with st.container(border=True):
        start_time = time.monotonic()
        _section_header("Analytics Intelligence", "Visual analytics institucional com gráficos, heatmaps e padrões históricos.")
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
            st.dataframe(_recurrence_table(), hide_index=True, use_container_width=True)
        duration_ms = (time.monotonic() - start_time) * 1000.0
        _record_operational_log("analytics", "success", duration_ms, {"source": "analytics_intelligence"})
        _record_performance_metric("analytics_ms", duration_ms, {"source": "analytics_intelligence"})


def render_ml_intelligence_page() -> None:
    with st.container(border=True):
        _section_header("ML Intelligence", "Score ML operacional com validação temporal e reranking interpretable.")
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

        st.subheader("Métricas do modelo")
        st.dataframe(_ml_features_table(model), hide_index=True, use_container_width=True)

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
        st.dataframe(scored_df, hide_index=True, use_container_width=True)

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
        st.dataframe(val_df, hide_index=True, use_container_width=True)
        st.info(
            f"Governança: temporal={validation['temporal_valid']} | linhas={validation['rows']} | modelo={validation['model_version']}"
        )


def render_ml_governance_page() -> None:
    with st.container(border=True):
        _section_header("ML Governance", "Governança institucional de modelos, experimentos, versões e snapshots.")
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
        st.dataframe(history_df, hide_index=True, use_container_width=True)

        st.subheader("Governança de features")
        st.dataframe(pd.DataFrame(feature_rows), hide_index=True, use_container_width=True)

        st.subheader("Artefatos institucionais")
        artifacts = pd.DataFrame(
            [
                {"type": "json", "path": str(paths["json"])},
                {"type": "csv", "path": str(paths["csv"])},
                {"type": "pdf", "path": str(paths["pdf"])},
                {"type": "snapshot", "path": str(snapshot_path)},
            ]
        )
        st.dataframe(artifacts, hide_index=True, use_container_width=True)
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
        _section_header("Criar Jogos", "Geração institucional com o fluxo operacional atual preservado.")
        lead_col1, lead_col2 = st.columns(2)
        first_name = lead_col1.text_input("Primeiro nome do lead", key="admin_first_name")
        whatsapp = lead_col2.text_input("WhatsApp do lead", key="admin_whatsapp")
        first_name = _safe_text(first_name, max_length=80)
        whatsapp = _safe_text(whatsapp, max_length=40)
        st.markdown('<div class="lotoia-lead-hint">Lead institucional opcional para rastreabilidade analítica.</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        count = col1.number_input("Quantidade", min_value=1, max_value=50, value=10)
        pool_size = col2.number_input("Pool do ranking", min_value=count, max_value=500, value=max(30, count))
        max_repeated = col3.number_input("Repetição máxima", min_value=0, max_value=15, value=9)
        mode = st.radio("Modo", ["Ranking híbrido", "Múltiplos jogos"], horizontal=True)
        if st.button("Gerar jogos", type="primary"):
            start_time = time.monotonic()
            with st.spinner("Gerando jogos e anexando scores..."):
                if mode == "Ranking híbrido":
                    payload = _cached_generate_best_games(int(count), int(pool_size))
                    games = payload["games"]
                else:
                    games = _cached_generate_multiple_games(int(count), int(max_repeated))
                st.session_state["last_generation_games"] = games
                _persist_lead(first_name, whatsapp)
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
                },
            )
            duration_ms = (time.monotonic() - start_time) * 1000.0
            _record_operational_log("generation", "success", duration_ms, {"games": len(games), "ml_enabled": False})
            _record_performance_metric("generation_ms", duration_ms, {"games": len(games), "ml_enabled": False})
            _record_audit_trail("generation_snapshot", artifact_path=str(generation_snapshot), context={"games": len(games)})


def render_check_page() -> None:
    with st.container(border=True):
        _section_header("Conferir Jogos", "Conferência operacional contra concursos históricos carregados.")
        lead_col1, lead_col2 = st.columns(2)
        first_name = _safe_text(lead_col1.text_input("Primeiro nome do lead", key="check_first_name"), max_length=80)
        whatsapp = _safe_text(lead_col2.text_input("WhatsApp do lead", key="check_whatsapp"), max_length=40)
        col1, col2 = st.columns([1, 3])
        contest_id = col1.number_input("Concurso", min_value=1, step=1, value=max(1, int(_safe_last_contest()) if _safe_last_contest().isdigit() else 1))
        numbers_text = col2.text_input("Dezenas", placeholder="01 02 03 04 05 06 07 08 09 10 11 12 13 14 15")
        if st.button("Conferir jogo", type="primary"):
            start_time = time.monotonic()
            try:
                numbers = _parse_check_numbers(numbers_text)
                result = _check_game_against_contest(int(contest_id), numbers)
                duration_ms = (time.monotonic() - start_time) * 1000.0
                result["execution_time_ms"] = round(duration_ms, 2)
                _persist_lead(first_name, whatsapp)
                cursor.execute(
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
                    (first_name.strip(), whatsapp.strip(), int(contest_id), int(result["hits"]), duration_ms),
                )
                conn.commit()
                check_row, check_payload = _build_check_report_payload(result, int(contest_id), numbers)
                snapshot = _write_snapshot(
                    "check_snapshot",
                    {
                        "context": {"first_name": first_name.strip(), "whatsapp": whatsapp.strip(), "timestamp": _report_timestamp()},
                        "check": check_payload,
                    },
                )
                st.session_state["last_check_context"] = {
                    "timestamp": _report_timestamp(),
                    "contest_id": int(contest_id),
                    "numbers": _format_numbers(numbers),
                    "draw_numbers": _format_numbers(result["draw_numbers"]),
                    "hits": int(result["hits"]),
                    "correct_numbers": _format_numbers(result["correct_numbers"]),
                }
                _record_operational_log("check", "success", duration_ms, {"contest_id": int(contest_id), "hits": int(result["hits"])})
                _record_performance_metric("check_ms", duration_ms, {"contest_id": int(contest_id), "hits": int(result["hits"])})
                _record_audit_trail("check_snapshot", artifact_path=str(snapshot), context={"contest_id": int(contest_id), "hits": int(result["hits"])})
                st.metric("Acertos", int(result["hits"]))
                st.dataframe(check_row, hide_index=True, use_container_width=True)
                st.subheader("Dezenas sorteadas")
                st.write(_format_numbers(result["draw_numbers"]))
                st.subheader("Dezenas acertadas")
                st.write(_format_numbers(result["correct_numbers"]) if result["correct_numbers"] else "-")
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


def render_calibration_page() -> None:
    with st.container(border=True):
        _section_header("Ajustar Estratégia", "Calibração experimental com pesos temporários e avaliação restaurável.")
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
        _section_header("Comparar Métodos", "Benchmark científico para leitura comparativa entre estratégias.")
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
            st.info(f"Relatórios salvos em: {result.report_paths.get('json', 'reports/benchmark')}")


def render_history_page() -> None:
    with st.container(border=True):
        _section_header("Meus Testes", "Histórico operacional, eventos persistidos e analytics atuais.")
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
        _section_header("Relatórios", "Saídas analíticas persistidas e artefatos gerados pela operação.")
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
        _section_header("Reports Engine", "Exportações institucionais, relatórios recentes e snapshots operacionais.")
        latest_games = _latest_generation_games()
        latest_check = _latest_check_context()
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

        st.subheader("Snapshots disponíveis")
        snapshots = sorted(REPORTS_SNAPSHOTS_DIR.glob("*.json"), reverse=True)
        if snapshots:
            for path in snapshots[:10]:
                st.write(str(path))
                snapshot_bytes = _safe_download_bytes(path)
                if snapshot_bytes is not None:
                    st.download_button("Baixar snapshot", data=snapshot_bytes, file_name=path.name, key=f"snap_{path.name}")
        else:
            st.info("Nenhum snapshot institucional disponível ainda.")


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
        .block-container { padding-top: 1.0rem; padding-bottom: 2rem; max-width: 1280px; }
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

    st.sidebar.caption("Plataforma analítica para LOTOFÁCIL")

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
        _render_kpi_cards()
        st.markdown("---")
        if page == "geracao_jogos":
            render_generation_page()
        elif page == "conferir_jogos":
            render_check_page()
        elif page == "estatisticas_historicas":
            render_statistics_page(draws)
        elif page == "backtesting":
            render_backtesting_page()
        elif page == "calibracao_experimental":
            render_calibration_page()
        elif page == "benchmark_cientifico":
            render_benchmark_page()
        elif page == "historico_experimental":
            render_history_page()
        elif page == "relatorios":
            render_reports_page()
        elif page == "historical_intelligence":
            render_historical_intelligence_page(draws)
        elif page == "analytics_intelligence":
            render_analytics_intelligence_page()
        elif page == "ml_intelligence":
            render_ml_intelligence_page()
        elif page == "ml_governance":
            render_ml_governance_page()
        elif page == "observability":
            render_observability_page()
        elif page == "reports_engine":
            render_reports_engine_page()
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
