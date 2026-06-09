from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from lotoia.database.database import (
    BacktestRun,
    BenchmarkRun,
    CalibrationRun,
    Lead,
    GeneratedGame,
    ReconciliationGame,
    ReconciliationRun,
    WorkflowEvent,
    WorkflowRun,
    WorkflowStep,
    create_database,
    get_session,
)
from lotoia.database.public_repository import (
    save_check_event,
    save_expansion_event,
    save_generation_event,
    save_lead,
    save_reconciliation_event,
    save_report_event,
)
from lotoia.public.reset_service import InstitutionalResetService, ResetScope


def _seed_scientific_rows(db_path: Path) -> None:
    with get_session(db_path) as session:
        session.add(
            BenchmarkRun(
                contests=10,
                games_per_contest=5,
                pool_size=15,
                history_window=50,
                seed=42,
                lotoia_average_hits=7.0,
                filtered_average_hits=6.0,
                random_average_hits=5.0,
                superiority_rate=0.5,
                average_advantage=1.0,
                standard_deviation=0.2,
                report_path="benchmark/report.json",
                payload={"kind": "benchmark"},
            )
        )
        session.add(
            BacktestRun(
                contests=10,
                games_per_contest=5,
                average_hits=7.2,
                hit_distribution={"7": 3},
                correlation=0.3,
                stability={"standard_deviation": 0.2},
                best_game={"hits": 9},
                worst_game={"hits": 3},
                report_path="backtest/report.json",
                payload={"kind": "backtest"},
            )
        )
        session.add(
            CalibrationRun(
                weight_configuration={"configuration": "baseline", "weights": {"a": 1}},
                average_hits=7.1,
                correlation=0.25,
                stability={"standard_deviation": 0.15},
                report_path="calibration/report.json",
                payload={"kind": "calibration"},
            )
        )
        session.commit()


def _seed_operational_rows(db_path: Path) -> dict[str, int]:
    lead = save_lead(
        first_name="Maria",
        whatsapp="11999990000",
        source="dashboard",
        ip_hash="hash",
        user_agent="agent",
        db_path=db_path,
    )
    generation = save_generation_event(
        lead_id=int(lead["id"]),
        generated_games=[{"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]}],
        ml_enabled=True,
        seed=123,
        strategy="historical",
        ranking_score=78.9,
        execution_time_ms=12.5,
        first_name="Maria",
        whatsapp="11999990000",
        db_path=db_path,
    )
    save_check_event(
        lead_id=int(lead["id"]),
        contest_id=3692,
        selected_numbers=[1, 2, 3, 4, 5],
        hits=5,
        result_payload={"contest_id": 3692},
        db_path=db_path,
    )
    save_report_event(
        lead_id=int(lead["id"]),
        generation_event_id=int(generation["id"]),
        report_type="user_report",
        generation_origin="dashboard",
        runtime_origin="dashboard",
        strategy_profile="historical",
        payload={"kind": "report"},
        db_path=db_path,
    )
    save_expansion_event(
        lead_id=int(lead["id"]),
        generation_event_id=int(generation["id"]),
        expansion_type="expanded",
        expansion_size=10,
        runtime_origin="dashboard",
        strategy_profile="historical",
        payload={"kind": "expansion"},
        db_path=db_path,
    )
    save_reconciliation_event(
        lead_id=int(lead["id"]),
        generation_event_id=int(generation["id"]),
        reconciliation_type="operational",
        hits=5,
        matched_numbers=[1, 2, 3, 4, 5],
        runtime_origin="dashboard",
        payload={"kind": "reconciliation"},
        db_path=db_path,
    )

    with get_session(db_path) as session:
        session.add(
            GeneratedGame(
                generation_event_id=int(generation["id"]),
                lead_id=int(lead["id"]),
                target_contest=3692,
                origin="dashboard",
                generation_mode="public_hybrid_statistical_v1",
                game_index=1,
                numbers=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
                profile_type="recorrente",
                final_score={"score": 78.9},
                quadra_score={"score": 9.0},
                context_json={"source": "test"},
            )
        )
        session.add(
            ReconciliationRun(
                generation_event_id=int(generation["id"]),
                lead_id=int(lead["id"]),
                contest_id=3692,
                source="official_result",
                status="reconciled",
                prize_count=1,
                total_hits=5,
                best_hits=5,
                payload={"kind": "reconciliation_run"},
            )
        )
        session.flush()
        reconciliation_run_id = session.query(ReconciliationRun.id).order_by(ReconciliationRun.id.desc()).first()[0]
        session.add(
            ReconciliationGame(
                reconciliation_run_id=int(reconciliation_run_id),
                generation_event_id=int(generation["id"]),
                lead_id=int(lead["id"]),
                contest_id=3692,
                game_index=1,
                numbers=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
                hits=5,
                matched_numbers=[1, 2, 3, 4, 5],
                prize_status="premiado",
                prize_tier="quadra",
                context_json={"source": "test"},
            )
        )
        session.add(
            WorkflowEvent(
                workflow_id="workflow-1",
                workflow_name="reset-test",
                correlation_id="corr-1",
                stage="running",
                source="test",
                status="running",
                payload={"kind": "workflow_event"},
                error_message="",
            )
        )
        session.add(
            WorkflowRun(
                workflow_id="workflow-1",
                workflow_name="reset-test",
                trigger="manual",
                status="running",
                retries=0,
                context_json={"kind": "workflow_run"},
                telemetry_json={"kind": "telemetry"},
                error_message="",
            )
        )
        session.add(
            WorkflowStep(
                workflow_id="workflow-1",
                step_name="step-1",
                status="running",
                attempt=1,
                payload_json={"kind": "workflow_step"},
                error_message="",
            )
        )
        session.commit()

    return {"lead_id": int(lead["id"]), "generation_event_id": int(generation["id"])}


def test_governed_operational_reset_preserves_scientific_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "reset.db"
    create_database(db_path)
    _seed_scientific_rows(db_path)
    _seed_operational_rows(db_path)

    service = InstitutionalResetService(db_path)
    result = service.reset_operational_history(
        scope=ResetScope.operational,
        triggered_by="admin",
        confirm_token="confirmar",
        payload={"reason": "cleanup"},
    )

    assert result.status == "completed"
    assert result.reset_type == ResetScope.operational.value
    assert "generation_events" in result.affected_tables
    assert "check_events" in result.affected_tables
    assert "benchmark_runs" not in result.affected_tables

    with get_session(db_path) as session:
        assert session.query(BenchmarkRun).count() == 1
        assert session.query(BacktestRun).count() == 1
        assert session.query(CalibrationRun).count() == 1
        assert session.query(Lead).count() == 1
        assert session.query(GeneratedGame).count() == 0
        assert session.query(ReconciliationRun).count() == 0
        assert session.query(ReconciliationGame).count() == 0
        assert session.query(WorkflowEvent).count() == 0
        assert session.query(WorkflowRun).count() == 0
        assert session.query(WorkflowStep).count() == 0
        reset_rows = session.execute(text("SELECT COUNT(*) FROM reset_events")).scalar_one()
        assert reset_rows == 1


def test_governed_full_reset_can_clear_leads(tmp_path: Path) -> None:
    db_path = tmp_path / "reset_full.db"
    create_database(db_path)
    _seed_scientific_rows(db_path)
    _seed_operational_rows(db_path)

    service = InstitutionalResetService(db_path)
    result = service.reset_operational_history(
        scope=ResetScope.full_operational,
        triggered_by="admin",
        confirm_token="confirmar",
        payload={"reason": "cleanup"},
    )

    assert result.status == "completed"
    assert "leads" in result.affected_tables
    with get_session(db_path) as session:
        assert session.query(BenchmarkRun).count() == 1
        assert session.query(BacktestRun).count() == 1
        assert session.query(CalibrationRun).count() == 1
        assert session.query(Lead).count() == 0


def test_governed_reset_requires_confirmation(tmp_path: Path) -> None:
    db_path = tmp_path / "reset_confirm.db"
    create_database(db_path)
    service = InstitutionalResetService(db_path)

    try:
        service.reset_operational_history(
            scope=ResetScope.visual,
            triggered_by="admin",
            confirm_token="nao",
        )
    except ValueError as exc:
        assert "confirm_token" in str(exc)
    else:
        raise AssertionError("expected reset confirmation failure")
