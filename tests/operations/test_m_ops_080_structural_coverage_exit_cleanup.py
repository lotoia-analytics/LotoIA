"""M-OPS-080 — limpeza de gerações CORE_002 auditadas ao sair da Cobertura Estrutural."""

from __future__ import annotations

import inspect

from lotoia.database.database import GeneratedGame, GenerationEvent, ReconciliationRun, create_database, get_session
from lotoia.governance.lei15_core_002_sovereign import resolve_core_002_batch_label
from lotoia.operations.lot_operational_status import (
    GENERATION_ORIGIN_GENERATOR,
    build_lot_status_context,
)
from lotoia.operations.structural_coverage_exit_cleanup import (
    MISSION_ID,
    all_active_generations_review_completed,
    delete_reviewed_operational_generations,
    execute_structural_coverage_exit_cleanup,
    is_generation_eligible_for_post_coverage_deletion,
    is_structural_coverage_review_completed,
    list_active_core_002_generation_event_ids,
    persist_structural_coverage_review_completed,
    resolve_post_coverage_deletion_targets,
)
from lotoia.ml.ml_operational_verdict import VERDICT_PRECISA_CALIBRAR


def _seed_sovereign_event(
    db_path,
    *,
    context_json: dict,
    games_count: int = 10,
    card_format: int = 15,
) -> int:
    batch_label = resolve_core_002_batch_label(card_format)
    numbers = list(range(1, card_format + 1))
    with get_session(db_path) as session:
        event = GenerationEvent(
            lead_id=None,
            first_name="institutional",
            whatsapp="",
            generated_games=[{"numbers": numbers}],
            context_json=context_json,
            ml_enabled=0,
            seed=42,
            strategy="institutional_clean_hb",
            ranking_score=0.0,
            execution_time_ms=0.0,
            analysis_batch_label=batch_label,
        )
        session.add(event)
        session.flush()
        event_id = int(event.id or 0)
        for index in range(games_count):
            session.add(
                GeneratedGame(
                    generation_event_id=event_id,
                    lead_id=None,
                    target_contest=3700,
                    origin="institutional",
                    generation_mode="hb_baseline",
                    game_index=index + 1,
                    numbers=numbers,
                    profile_type="recorrente",
                    final_score={"final_score": 0.5},
                    quadra_score={},
                    context_json={
                        **context_json,
                        "selected_card_format": card_format,
                        "final_card_numbers": numbers,
                    },
                )
            )
        session.commit()
        return event_id


def test_persist_structural_coverage_review_completed_marks_context(tmp_path) -> None:
    db_path = tmp_path / "review.db"
    create_database(db_path)
    lot_context = build_lot_status_context(
        ml_verdict_payload={
            "ml_verdict": VERDICT_PRECISA_CALIBRAR,
            "official_release_allowed": False,
        },
        generation_origin=GENERATION_ORIGIN_GENERATOR,
    )
    ge_id = _seed_sovereign_event(
        db_path,
        context_json={**lot_context, "selected_card_format": 15},
        games_count=10,
    )
    result = persist_structural_coverage_review_completed(db_path, [ge_id])
    assert ge_id in result["updated_generation_event_ids"]
    with get_session(db_path) as session:
        event = session.query(GenerationEvent).filter(GenerationEvent.id == ge_id).first()
        assert event is not None
        context = dict(event.context_json or {})
        assert is_structural_coverage_review_completed(context)
        assert context["structural_coverage_review_mission_id"] == MISSION_ID


def test_all_active_generations_review_completed_requires_all_ids(tmp_path) -> None:
    db_path = tmp_path / "all-reviewed.db"
    create_database(db_path)
    lot_context = build_lot_status_context(
        ml_verdict_payload={
            "ml_verdict": VERDICT_PRECISA_CALIBRAR,
            "official_release_allowed": False,
        },
        generation_origin=GENERATION_ORIGIN_GENERATOR,
    )
    ge_one = _seed_sovereign_event(db_path, context_json=lot_context, games_count=5)
    ge_two = _seed_sovereign_event(db_path, context_json=lot_context, games_count=5)
    persist_structural_coverage_review_completed(db_path, [ge_one])
    assert all_active_generations_review_completed(db_path, [ge_one, ge_two]) is False
    persist_structural_coverage_review_completed(db_path, [ge_two])
    assert all_active_generations_review_completed(db_path, [ge_one, ge_two]) is True


def test_delete_reviewed_operational_generations_removes_active_core_002(tmp_path) -> None:
    db_path = tmp_path / "delete.db"
    create_database(db_path)
    lot_context = build_lot_status_context(
        ml_verdict_payload={
            "ml_verdict": VERDICT_PRECISA_CALIBRAR,
            "official_release_allowed": False,
        },
        generation_origin=GENERATION_ORIGIN_GENERATOR,
    )
    ge_id = _seed_sovereign_event(db_path, context_json=lot_context, games_count=8)
    persist_structural_coverage_review_completed(db_path, [ge_id])
    result = delete_reviewed_operational_generations(db_path, [ge_id])
    assert ge_id in result["deleted_generation_event_ids"]
    with get_session(db_path) as session:
        assert session.query(GenerationEvent).filter(GenerationEvent.id == ge_id).count() == 0
        assert (
            session.query(GeneratedGame)
            .filter(GeneratedGame.generation_event_id == ge_id)
            .count()
            == 0
        )


def test_conferred_generation_is_not_deleted(tmp_path) -> None:
    db_path = tmp_path / "conferred.db"
    create_database(db_path)
    lot_context = build_lot_status_context(
        ml_verdict_payload={
            "ml_verdict": VERDICT_PRECISA_CALIBRAR,
            "official_release_allowed": False,
        },
        generation_origin=GENERATION_ORIGIN_GENERATOR,
    )
    ge_id = _seed_sovereign_event(db_path, context_json=lot_context, games_count=8)
    persist_structural_coverage_review_completed(db_path, [ge_id])
    with get_session(db_path) as session:
        session.add(
            ReconciliationRun(
                generation_event_id=ge_id,
                lead_id=None,
                contest_id=3700,
                source="official_result",
                status="reconciliado",
                prize_count=0,
                total_hits=10,
                best_hits=10,
                payload={},
            )
        )
        session.commit()
    dry_run = resolve_post_coverage_deletion_targets(db_path, [ge_id])
    assert dry_run["eligible_generation_event_ids"] == []
    with get_session(db_path) as session:
        event = session.query(GenerationEvent).filter(GenerationEvent.id == ge_id).first()
        assert event is not None
        allowed, reason = is_generation_eligible_for_post_coverage_deletion(
            event,
            reconciliation_exists=True,
        )
        assert allowed is False
        assert reason == "lot_already_conferred"


def test_conference_status_checked_without_reconciliation_is_eligible(tmp_path) -> None:
    db_path = tmp_path / "checked-context.db"
    create_database(db_path)
    lot_context = build_lot_status_context(
        ml_verdict_payload={
            "ml_verdict": VERDICT_PRECISA_CALIBRAR,
            "official_release_allowed": False,
        },
        generation_origin=GENERATION_ORIGIN_GENERATOR,
    )
    ge_id = _seed_sovereign_event(
        db_path,
        context_json={**lot_context, "conference_status": "checked"},
        games_count=8,
    )
    persist_structural_coverage_review_completed(db_path, [ge_id])
    dry_run = resolve_post_coverage_deletion_targets(db_path, [ge_id])
    assert ge_id in dry_run["eligible_generation_event_ids"]


def test_approved_operational_scope_is_eligible_after_structural_review(tmp_path) -> None:
    db_path = tmp_path / "approved.db"
    create_database(db_path)
    lot_context = build_lot_status_context(
        ml_verdict_payload={
            "ml_verdict": VERDICT_PRECISA_CALIBRAR,
            "official_release_allowed": False,
        },
        generation_origin=GENERATION_ORIGIN_GENERATOR,
    )
    ge_id = _seed_sovereign_event(
        db_path,
        context_json={**lot_context, "operational_status": "approved_for_officialization"},
        games_count=8,
    )
    persist_structural_coverage_review_completed(db_path, [ge_id])
    dry_run = resolve_post_coverage_deletion_targets(db_path, [ge_id])
    assert ge_id in dry_run["eligible_generation_event_ids"]


def test_execute_exit_cleanup_requires_all_reviewed(tmp_path) -> None:
    db_path = tmp_path / "exit.db"
    create_database(db_path)
    lot_context = build_lot_status_context(
        ml_verdict_payload={
            "ml_verdict": VERDICT_PRECISA_CALIBRAR,
            "official_release_allowed": False,
        },
        generation_origin=GENERATION_ORIGIN_GENERATOR,
    )
    ge_one = _seed_sovereign_event(db_path, context_json=lot_context, games_count=4)
    ge_two = _seed_sovereign_event(db_path, context_json=lot_context, games_count=4)
    active_ids = list_active_core_002_generation_event_ids(db_path)
    assert ge_one in active_ids and ge_two in active_ids
    pending = execute_structural_coverage_exit_cleanup(db_path, active_generation_event_ids=active_ids)
    assert pending["executed"] is False
    assert pending["reason"] == "pending_structural_coverage_review"
    persist_structural_coverage_review_completed(db_path, active_ids)
    executed = execute_structural_coverage_exit_cleanup(db_path, active_generation_event_ids=active_ids)
    assert executed["executed"] is True
    assert sorted(executed["deleted_generation_event_ids"]) == sorted(active_ids)
    assert list_active_core_002_generation_event_ids(db_path) == []


def test_institutional_app_wires_structural_coverage_exit_cleanup() -> None:
    import dashboard.institutional_app as institutional_app

    source = inspect.getsource(institutional_app.main)
    assert "_handle_structural_coverage_page_exit" in source
    assert "INSTITUTIONAL_PREVIOUS_PAGE_ID_KEY" in source
    coverage_source = inspect.getsource(institutional_app._render_cobertura_estrutural_page)
    assert "_mark_structural_coverage_aggregate_reviewed" in coverage_source
    assert "is_all_operational_generations_selection" in coverage_source
    assert "_maybe_bust_operational_coverage_cache" in inspect.getsource(institutional_app.main)
