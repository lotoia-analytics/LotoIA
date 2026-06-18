from __future__ import annotations

from datetime import UTC, datetime

from lotoia.analytics.scientific_calibration_engine import register_calibration_decision
from lotoia.database.database import (
    GeneratedGame,
    GenerationEvent,
    ReconciliationGame,
    ReconciliationRun,
    create_database,
    get_session,
)
from lotoia.governance.batch_operational_scope import (
    OPERATIONAL_STATUS_CALIBRATION_SOURCE,
    OPERATIONAL_STATUS_PENDING,
    OPERATIONAL_STATUS_SUPERSEDED,
    is_active_reading_scope,
    is_conference_eligible_scope,
    list_excluded_batches_audit,
    mark_batch_superseded_by_calibration,
    summarize_active_reading_exclusions,
)
from lotoia.observability.card_structure_diagnostics import load_card_structure_diagnostics_from_db
from lotoia.observability.ml_diagnostic_panels import (
    build_central_ml_diagnostics_payload,
    load_distinct_generation_event_count,
    load_recent_reconciliation_runs_context,
)



def _seed_generation_with_reconciliation(
    db_path,
    *,
    batch_id: str,
    operational_status: str = OPERATIONAL_STATUS_PENDING,
) -> int:
    numbers = list(range(1, 16))
    with get_session(db_path) as session:
        event = GenerationEvent(
            lead_id=None,
            first_name="institutional",
            whatsapp="",
            generated_games=[{"numbers": numbers}],
            context_json={
                "batch_id": batch_id,
                "operational_status": operational_status,
                "officialization_status": "not_officialized",
                "calibration_state": "none",
                "active_reading_scope": operational_status == OPERATIONAL_STATUS_PENDING,
            },
            ml_enabled=0,
            seed=42,
            strategy="institutional_clean_hb",
            ranking_score=0.0,
            execution_time_ms=0.0,
            analysis_batch_label="STRUCT_TEST_15D_001",
        )
        session.add(event)
        session.flush()
        event_id = int(event.id or 0)
        session.add(
            GeneratedGame(
                generation_event_id=event_id,
                lead_id=None,
                target_contest=3700,
                origin="institutional",
                generation_mode="hb_baseline",
                game_index=1,
                numbers=numbers,
                profile_type="recorrente",
                final_score={"final_score": 0.5},
                quadra_score={},
                context_json={"batch_id": batch_id, "operational_status": operational_status},
            )
        )
        run = ReconciliationRun(
            generation_event_id=event_id,
            contest_id=3700,
            prize_count=0,
            total_hits=14,
            best_hits=14,
            created_at=datetime.now(UTC),
            payload={},
        )
        session.add(run)
        session.flush()
        session.add(
            ReconciliationGame(
                reconciliation_run_id=run.id,
                generation_event_id=event_id,
                contest_id=3700,
                game_index=1,
                numbers=numbers,
                hits=14,
                matched_numbers=numbers,
                prize_status="nao_premiado",
                prize_tier="",
                context_json={},
            )
        )
        session.commit()
        return event_id


def test_mark_batch_superseded_persists_context_json_without_purge(tmp_path) -> None:
    db_path = tmp_path / "scope.db"
    create_database(db_path)
    batch_id = "batch-m061-superseded"
    _seed_generation_with_reconciliation(db_path, batch_id=batch_id)

    result = mark_batch_superseded_by_calibration(
        batch_id,
        db_path=db_path,
        reason="calibração aplicada",
        evidence={"classification": "REPROVADA"},
        authorized_plan={"policy_mode": "hybrid_15_towards_12_plus"},
        operator="operator@test",
    )

    assert result["active_reading_scope"] is False
    assert result["updated_generation_event_ids"]
    assert result["updated_game_rows"] == 1

    with get_session(db_path) as session:
        event = session.query(GenerationEvent).one()
        game = session.query(GeneratedGame).one()
        assert event.context_json["operational_status"] == OPERATIONAL_STATUS_SUPERSEDED
        assert game.context_json["operational_status"] == OPERATIONAL_STATUS_SUPERSEDED
        assert event.context_json["batch_operational_trace"]
        assert session.query(ReconciliationRun).count() == 1
        assert session.query(ReconciliationGame).count() == 1


def test_superseded_batch_excluded_from_active_reading_helpers(tmp_path) -> None:
    db_path = tmp_path / "scope2.db"
    create_database(db_path)
    batch_id = "batch-m061-inactive"
    _seed_generation_with_reconciliation(db_path, batch_id=batch_id)
    mark_batch_superseded_by_calibration(
        batch_id,
        db_path=db_path,
        reason="base de calibração",
        operator="operator@test",
        calibration_source_only=True,
    )

    with get_session(db_path) as session:
        event = session.query(GenerationEvent).one()
        context = dict(event.context_json or {})

    assert context["operational_status"] == OPERATIONAL_STATUS_CALIBRATION_SOURCE
    assert is_active_reading_scope(context) is False
    assert is_conference_eligible_scope(context) is False
    assert summarize_active_reading_exclusions(db_path)["excluded_batches_count"] == 1
    assert list_excluded_batches_audit(db_path)[0]["batch_id"] == batch_id


def test_central_ml_and_cobertura_ignore_superseded_batch(tmp_path) -> None:
    db_path = tmp_path / "scope3.db"
    create_database(db_path)
    active_batch = "batch-m061-active"
    inactive_batch = "batch-m061-inactive"
    _seed_generation_with_reconciliation(db_path, batch_id=active_batch)
    _seed_generation_with_reconciliation(db_path, batch_id=inactive_batch)
    mark_batch_superseded_by_calibration(
        inactive_batch,
        db_path=db_path,
        reason="calibração",
        operator="operator@test",
    )

    contexts = load_recent_reconciliation_runs_context(limit=5, db_path=db_path)
    assert len(contexts) == 1

    assert load_distinct_generation_event_count(db_path=db_path) == 1

    central = build_central_ml_diagnostics_payload(db_path=db_path)
    assert central["excluded_batches_count"] == 1
    assert "removido" in central["excluded_batches_message"]

    cobertura = load_card_structure_diagnostics_from_db(db_path)
    assert cobertura["excluded_batches_count"] == 1
    assert cobertura["available"] is True
    assert cobertura["summary"]["total_geracoes"] == 1


def test_register_calibration_decision_marks_source_batch(tmp_path) -> None:
    db_path = tmp_path / "scope4.db"
    create_database(db_path)
    batch_id = "batch-scientific-calibration"
    _seed_generation_with_reconciliation(db_path, batch_id=batch_id)

    context = {
        "source_batch_id": batch_id,
        "game_size": 15,
        "mode": "OBSERVAÇÃO",
        "scientific_report": {"total_jogos_solicitados": 20},
        "structural_report": {"quantidade_jogos_solicitados": 20},
        "official_history": {"count": 0, "window": []},
        "scientific_memory": {"latest": {}},
        "reference_contests": [],
        "policy_before": {},
        "policy_after": {"policy_mode": "hybrid_15_towards_12_plus"},
    }
    decision = {
        "strategy": "15_dezenas",
        "game_size": 15,
        "source_batch_id": batch_id,
        "source_generation_range": {},
        "structural_status": "REPROVADO",
        "scientific_status": "REPROVADO",
        "classification": "REPROVADA",
        "main_reason": "calibração aplicada",
        "recommended_action": "recalibrate_frequency_distribution",
        "policy_before": {},
        "policy_after": {"policy_mode": "hybrid_15_towards_12_plus"},
        "mode": "OBSERVAÇÃO",
        "applied": False,
        "approved_by": "operator@test",
        "notes": "registro supervisionado",
        "status_visual": "REPROVADO",
    }
    saved = register_calibration_decision(context, decision=decision, db_path=db_path)

    assert saved["batch_operational_scope"]["active_reading_scope"] is False
    with get_session(db_path) as session:
        event = session.query(GenerationEvent).one()
        assert event.context_json["operational_status"] in {
            OPERATIONAL_STATUS_SUPERSEDED,
            OPERATIONAL_STATUS_CALIBRATION_SOURCE,
        }
