from pathlib import Path
import sqlite3

from sqlalchemy import inspect

from lotoia.backtesting import BacktestResult
from lotoia.benchmark.benchmark_engine import BenchmarkResult
from lotoia.database import (
    create_database,
    get_run_by_id,
    list_runs,
    save_backtest_run,
    save_benchmark_run,
    save_calibration_run,
)
from lotoia.database.database import get_engine


def make_backtest_result() -> BacktestResult:
    game = {
        "contest": 100,
        "numbers": list(range(1, 16)),
        "hits": 11,
        "final_score": {"final_score": 70, "components": {}},
        "quadra_score": {"found_quadras": 10, "average_rank": 200},
    }
    return BacktestResult(
        contests_analyzed=1,
        games_per_contest=1,
        pool_size=2,
        history_window=20,
        total_games=1,
        average_hits=11,
        hit_distribution={"11": 1, "12": 0, "13": 0, "14": 0, "15": 0},
        best_game=game,
        worst_game=game,
        average_winner_final_score=70,
        final_score_hit_correlation=0,
        contest_results=[
            {
                "contest": 100,
                "target_numbers": list(range(1, 16)),
                "games": [game],
                "best_hits": 11,
                "average_hits": 11,
            }
        ],
    )


def make_benchmark_result() -> BenchmarkResult:
    metrics = {
        "total_games": 1,
        "average_hits": 10,
        "hit_distribution": {"11": 0, "12": 0, "13": 0, "14": 0, "15": 0},
        "standard_deviation": 0,
        "stability": {"min_hits": 10, "max_hits": 10, "windows": []},
        "final_score_hit_correlation": 0,
        "best_game": None,
        "worst_game": None,
    }
    return BenchmarkResult(
        contests_analyzed=1,
        games_per_contest=1,
        pool_size=2,
        history_window=20,
        strategies={
            "lotoia_engine": metrics,
            "filtered_random": {**metrics, "average_hits": 9},
            "pure_random": {**metrics, "average_hits": 8},
        },
        comparisons={
            "lotoia_engine_vs_filtered_random": {
                "average_hit_difference": 1,
                "superiority_rate": 1,
                "lotoia_average_rank": 1,
                "competitor_average_rank": 2,
            },
            "lotoia_engine_vs_pure_random": {
                "average_hit_difference": 2,
                "superiority_rate": 1,
                "lotoia_average_rank": 1,
                "competitor_average_rank": 3,
            },
        },
        contest_results=[],
        report_paths={"json": "reports/benchmark/benchmark_result.json"},
    )


def test_create_database_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "lotoia.db"

    create_database(db_path)

    inspector = inspect(get_engine(db_path))
    assert {
        "benchmark_runs",
        "backtest_runs",
        "calibration_runs",
        "check_events",
        "generated_games",
        "generation_events",
        "imported_contests",
        "leads",
        "reconciliation_games",
        "reconciliation_runs",
    } <= set(inspector.get_table_names())
    imported_columns = {column["name"] for column in inspector.get_columns("imported_contests")}
    assert {"contest_number", "created_at", "data", "dezenas", "metadata_json"} <= imported_columns
    generated_columns = {column["name"] for column in inspector.get_columns("generated_games")}
    assert {"generation_event_id", "lead_id", "target_contest", "origin", "generation_mode", "context_json"} <= generated_columns
    check_fks = inspector.get_foreign_keys("check_events")
    generation_fks = inspector.get_foreign_keys("generation_events")
    assert any(fk["referred_table"] == "leads" for fk in check_fks)
    assert any(fk["referred_table"] == "leads" for fk in generation_fks)

    lead_indexes = {item["name"] for item in inspector.get_indexes("leads")}
    generation_indexes = {item["name"] for item in inspector.get_indexes("generation_events")}
    check_indexes = {item["name"] for item in inspector.get_indexes("check_events")}
    assert {"ix_leads_created_at", "ix_leads_whatsapp", "ix_leads_source"} <= lead_indexes
    assert {"ix_generation_events_created_at", "ix_generation_events_lead_id"} <= generation_indexes
    assert {"ix_check_events_created_at", "ix_check_events_lead_id"} <= check_indexes


def test_get_engine_reuses_engine_for_same_database_url(tmp_path: Path) -> None:
    db_path = tmp_path / "lotoia.db"

    assert get_engine(db_path) is get_engine(db_path)


def test_create_database_migrates_lead_runtime_columns(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy_lotoia.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                whatsapp TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()

    create_database(db_path)

    inspector = inspect(get_engine(db_path))
    lead_columns = {column["name"] for column in inspector.get_columns("leads")}
    assert {"source", "ip_hash", "user_agent"} <= lead_columns


def test_create_database_migrates_generation_event_payload_columns(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy_generation_events.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE generation_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER,
                first_name TEXT NOT NULL DEFAULT '',
                whatsapp TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                context_json JSON NOT NULL DEFAULT '{}',
                ml_enabled INTEGER NOT NULL,
                seed INTEGER NOT NULL,
                strategy TEXT NOT NULL,
                ranking_score REAL NOT NULL,
                execution_time_ms REAL NOT NULL
            )
            """
        )
        connection.commit()

    create_database(db_path)

    inspector = inspect(get_engine(db_path))
    generation_columns = {column["name"] for column in inspector.get_columns("generation_events")}
    assert {"lead_id", "first_name", "whatsapp", "generated_games", "context_json"} <= generation_columns


def test_save_and_read_backtest_run(tmp_path: Path) -> None:
    db_path = tmp_path / "lotoia.db"

    run_id = save_backtest_run(make_backtest_result(), report_path="reports/a.json", db_path=db_path)
    run = get_run_by_id("backtest", run_id, db_path=db_path)

    assert run is not None
    assert run["average_hits"] == 11
    assert run["hit_distribution"]["11"] == 1
    assert run["report_path"] == "reports/a.json"


def test_save_and_read_benchmark_run(tmp_path: Path) -> None:
    db_path = tmp_path / "lotoia.db"

    run_id = save_benchmark_run(make_benchmark_result(), seed=42, db_path=db_path)
    run = get_run_by_id("benchmark", run_id, db_path=db_path)

    assert run is not None
    assert run["seed"] == 42
    assert run["lotoia_average_hits"] == 10
    assert run["average_advantage"] == 1.5


def test_save_and_read_calibration_run(tmp_path: Path) -> None:
    db_path = tmp_path / "lotoia.db"
    evaluation = {
        "configuration": "experimental",
        "weights": {"duo_score": 15},
        "total_weight": 100,
        "average_hits": 9.5,
        "final_score_hit_correlation": 0.2,
        "hit_standard_deviation": 1.1,
    }

    run_id = save_calibration_run(evaluation, report_path="reports/c.json", db_path=db_path)
    run = get_run_by_id("calibration", run_id, db_path=db_path)

    assert run is not None
    assert run["weight_configuration"]["configuration"] == "experimental"
    assert run["stability"]["standard_deviation"] == 1.1


def test_list_runs_with_multiple_executions(tmp_path: Path) -> None:
    db_path = tmp_path / "lotoia.db"
    save_backtest_run(make_backtest_result(), db_path=db_path)
    save_backtest_run(make_backtest_result(), db_path=db_path)
    save_benchmark_run(make_benchmark_result(), db_path=db_path)

    all_runs = list_runs(db_path=db_path)
    backtests = list_runs("backtest", db_path=db_path)

    assert len(all_runs["backtest"]) == 2
    assert len(all_runs["benchmark"]) == 1
    assert len(backtests) == 2
