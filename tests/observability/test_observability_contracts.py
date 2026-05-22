from __future__ import annotations

import sys
import types
import sqlite3

import pandas as pd
from lotoia.database import create_database
from lotoia.database.database import get_session, Lead, GenerationEvent, CheckEvent, ImportedContest, GeneratedGame
from lotoia.observability import MetricSample, MetricType, ObservabilityRepository, build_institutional_observability_dashboard, build_observational_stabilization_report

if "matplotlib" not in sys.modules:
    matplotlib = types.ModuleType("matplotlib")
    pyplot = types.ModuleType("matplotlib.pyplot")
    pyplot.subplots = lambda *args, **kwargs: (type("Fig", (), {"add_axes": lambda *a, **k: type("Ax", (), {"axis": lambda *a, **k: None, "text": lambda *a, **k: None, "table": lambda *a, **k: type("Tbl", (), {"auto_set_font_size": lambda *a, **k: None, "set_fontsize": lambda *a, **k: None, "scale": lambda *a, **k: None})()})(), "savefig": lambda *a, **k: None})(), type("Ax", (), {"axis": lambda *a, **k: None, "text": lambda *a, **k: None, "table": lambda *a, **k: None})())
    pyplot.close = lambda *args, **kwargs: None
    matplotlib.pyplot = pyplot  # type: ignore[attr-defined]
    sys.modules["matplotlib"] = matplotlib
    sys.modules["matplotlib.pyplot"] = pyplot


def _install_admin_app_stubs() -> None:
    stubs: dict[str, dict[str, object]] = {
        "lotoia.reports": {
            "generate_backtest_report": lambda *args, **kwargs: None,
        },
        "lotoia.backtesting": {
            "BacktestResult": type("BacktestResult", (), {}),
            "run_backtest": lambda *args, **kwargs: None,
        },
        "lotoia.benchmark": {
            "BenchmarkResult": type("BenchmarkResult", (), {}),
            "run_benchmark": lambda *args, **kwargs: None,
        },
        "lotoia.calibration.weight_calibrator": {
            "WeightConfiguration": type("WeightConfiguration", (), {}),
            "compare_weight_configurations": lambda *args, **kwargs: None,
        },
        "lotoia.generator.basic_generator": {
            "_build_game": lambda *args, **kwargs: {},
            "_is_valid_game": lambda *args, **kwargs: True,
            "generate_best_games": lambda *args, **kwargs: [],
            "generate_multiple_games": lambda *args, **kwargs: [],
        },
        "lotoia.experiments.temporal_governance": {
            "build_walk_forward_splits": lambda *args, **kwargs: [],
        },
        "lotoia.ml": {
            "InterpretableLinearScoreML": type("InterpretableLinearScoreML", (), {}),
            "attach_score_ml": lambda *args, **kwargs: None,
            "calibrate_linear_score_ml": lambda *args, **kwargs: None,
            "activate_score_ml_runtime": lambda *args, **kwargs: {},
            "ml_heartbeat": lambda *args, **kwargs: {"engine_version": "historical_recalibrated_v2", "model_version": "historical_recalibrated_v2", "status": "active", "fallback_used": False},
            "extract_score_ml_features": lambda *args, **kwargs: [],
            "migrate_score_ml_snapshot": lambda *args, **kwargs: None,
            "ensure_calibration": lambda *args, **kwargs: None,
            "supervised_rerank_games": lambda *args, **kwargs: [],
        },
        "lotoia.generator.engine": {
            "generate_ranked_games": lambda *args, **kwargs: [],
        },
    }
    for module_name, attributes in stubs.items():
        if module_name in sys.modules:
            continue
        module = types.ModuleType(module_name)
        for attribute_name, attribute_value in attributes.items():
            setattr(module, attribute_name, attribute_value)
        sys.modules[module_name] = module


def test_runtime_health_and_metrics_table_are_safe(monkeypatch, tmp_path) -> None:
    _install_admin_app_stubs()
    import dashboard.admin_app as admin_app

    conn = sqlite3.connect(tmp_path / "observability.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE operational_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            status TEXT NOT NULL,
            duration_ms REAL,
            context_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.executemany(
        "INSERT INTO operational_logs (event_type, status, duration_ms, context_json) VALUES (?, ?, ?, ?)",
        [
            ("generation", "success", 10.0, "{}"),
            ("check", "failed", 20.0, "{}"),
        ],
    )
    conn.commit()
    monkeypatch.setattr(admin_app, "conn", conn)
    monkeypatch.setattr(admin_app, "cursor", cursor)
    monkeypatch.setattr(admin_app, "_observability_tables", lambda: {"logs": pd.read_sql_query("SELECT * FROM operational_logs", conn), "audit": pd.DataFrame()})

    health = admin_app._runtime_health()
    metrics = admin_app._observability_metrics_table()

    assert health["total_runs"] == 2
    assert health["failures"] == 1
    assert not metrics.empty
    assert set(metrics["event_type"]) == {"generation", "check"}


def test_observational_stabilization_report_reads_live_database(tmp_path) -> None:
    db_path = tmp_path / "observability.db"
    create_database(db_path)
    with get_session(db_path) as session:
        lead = Lead(first_name="Ana", whatsapp="11999999999", source="public", ip_hash="", user_agent="")
        session.add(lead)
        session.commit()
        session.add(
            GenerationEvent(
                lead_id=lead.id,
                generated_games=[{"numbers": list(range(1, 16))}],
                ml_enabled=0,
                seed=7,
                strategy="historical_recalibrated_v2",
                ranking_score=1.0,
                execution_time_ms=10.0,
            )
        )
        session.add(
            CheckEvent(
                lead_id=lead.id,
                contest_id=5000,
                selected_numbers=list(range(1, 16)),
                hits=12,
                result_payload={"hits": 12},
            )
        )
        session.add(
            ImportedContest(
                contest_number=5000,
                data="{}",
                dezenas="1,2,3,4,5,6,7,8,9,10,11,12,13,14,15",
            )
        )
        session.add(
            GeneratedGame(
                generation_event_id=1,
                lead_id=lead.id,
                game_index=1,
                numbers=list(range(1, 16)),
                profile_type="recorrente",
                final_score={"score": 1.0},
                quadra_score={"quadra": 0},
            )
        )
        session.commit()

    report = build_observational_stabilization_report(db_path)

    assert report["schema_version"] == "observational-stabilization-v1.0.0"
    assert report["generated_by"] == "build_observational_stabilization_report"
    assert report["summary"]["homepage_priority"] in {"institutional_first", "mixed"}
    assert report["counts"]["generation_events"] == 1
    assert report["counts"]["check_events"] == 1


def test_institutional_observability_dashboard_aggregates_runtime_history(tmp_path) -> None:
    db_path = tmp_path / "observability.db"
    create_database(db_path)
    repository = ObservabilityRepository(db_path)
    execution_id = repository.start_execution(flow_name="generation", stage="runtime", context={"source": "test"})
    repository.record_metric(
        execution_id,
        MetricSample(name="confidence_drift", value=0.4, metric_type=MetricType.GAUGE, labels={}, metadata={}),
        stage="runtime",
    )
    repository.record_lineage(
        execution_id,
        entity_type="runtime_execution",
        entity_id=execution_id,
        event_type="generator_started",
        payload={"source": "test"},
    )
    repository.record_snapshot(
        execution_id,
        snapshot_type="runtime",
        payload={"state": "ok"},
        metadata={"source": "test"},
    )
    repository.finish_execution(execution_id, status="ok", stage="done", duration_ms=42.0)

    dashboard = build_institutional_observability_dashboard(db_path)

    assert dashboard["summary"]["execution_count"] == 1
    assert dashboard["summary"]["metric_count"] == 1
    assert dashboard["summary"]["lineage_count"] == 1
    assert dashboard["summary"]["snapshot_count"] == 1
    assert dashboard["summary"]["latest_execution_id"] == execution_id
    assert dashboard["structural_integrity"]["ok"] is True
