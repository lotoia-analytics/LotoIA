from __future__ import annotations

import inspect

from lotoia.database.database import GeneratedGame, GenerationEvent, create_database, get_session
from lotoia.governance.batch_operational_scope import (
    OPERATIONAL_STATUS_NEEDS_CALIBRATION,
    OPERATIONAL_STATUS_PENDING,
    dry_run_active_coverage_cleanup,
    is_generation_event_active_reading,
    resolve_operational_status_from_context,
)
from lotoia.governance.lei15_core_002_sovereign import resolve_core_002_batch_label
from lotoia.observability.card_structure_diagnostics import _event_eligible_for_active_structural_reading
from lotoia.operations.lot_operational_status import (
    GENERATION_ORIGIN_GENERATOR,
    GENERATION_ORIGIN_SIMULATION,
    STATUS_BLOCKED_FOR_OFFICIALIZATION,
    STATUS_CALIBRATION_AUTHORIZED,
    STATUS_NEEDS_CALIBRATION,
    STATUS_PENDING_STRUCTURAL_REVIEW,
    build_lot_status_context,
    defer_lot_status_for_structural_coverage,
    is_active_structural_reading_status,
    resolve_lot_operational_status,
    should_defer_generator_persist_verdict_for_coverage,
)
from lotoia.ml.ml_operational_verdict import VERDICT_APROVADO, VERDICT_BLOQUEADO, VERDICT_PRECISA_CALIBRAR

from dashboard.institutional_operational_structural_coverage import (
    build_active_coverage_scope_summary,
    diagnose_operational_coverage_gap,
    load_operational_core_002_generations,
    sync_persisted_event_operational_status,
)


def _seed_sovereign_event(
    db_path,
    *,
    batch_label: str,
    context_json: dict,
    games_count: int = 20,
) -> int:
    numbers = list(range(1, 18))
    with get_session(db_path) as session:
        event = GenerationEvent(
            lead_id=None,
            first_name="institutional",
            whatsapp="",
            generated_games=[{"numbers": numbers}],
            context_json=context_json,
            ml_enabled=1,
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
                        "selected_card_format": 17,
                        "final_card_numbers": numbers,
                    },
                )
            )
        session.commit()
        return event_id


def test_defer_lot_status_promotes_rejected_generator_to_pending() -> None:
    lot_context = build_lot_status_context(
        ml_verdict_payload={
            "ml_verdict": VERDICT_BLOQUEADO,
            "official_release_allowed": False,
        },
        generation_origin=GENERATION_ORIGIN_GENERATOR,
    )
    assert lot_context["lot_operational_status"] == STATUS_BLOCKED_FOR_OFFICIALIZATION
    deferred = defer_lot_status_for_structural_coverage(
        lot_context,
        generation_origin=GENERATION_ORIGIN_GENERATOR,
        simulation_mode=False,
        ml_verdict_payload={"ml_verdict": VERDICT_BLOQUEADO, "ml_verdict_reason": "overlap"},
    )
    assert deferred["lot_operational_status"] == STATUS_PENDING_STRUCTURAL_REVIEW
    assert deferred["ml_persist_verdict_deferred_for_coverage"] is True


def test_should_defer_generator_persist_verdict_for_legacy_rejected_rows() -> None:
    context = {
        "generation_origin": GENERATION_ORIGIN_GENERATOR,
        "simulation_mode": False,
        "lot_operational_status": STATUS_BLOCKED_FOR_OFFICIALIZATION,
        "ml_verdict": VERDICT_BLOQUEADO,
        "lot_operational_status_mission_id": "M-OPS-062",
    }
    assert should_defer_generator_persist_verdict_for_coverage(context)


def test_rejected_generator_17d_visible_in_operational_coverage_loader(tmp_path) -> None:
    db_path = tmp_path / "rejected-visible.db"
    create_database(db_path)
    batch_label = resolve_core_002_batch_label(17)
    lot_context = build_lot_status_context(
        ml_verdict_payload={
            "ml_verdict": VERDICT_BLOQUEADO,
            "official_release_allowed": False,
        },
        generation_origin=GENERATION_ORIGIN_GENERATOR,
    )
    ge_id = _seed_sovereign_event(
        db_path,
        batch_label=batch_label,
        context_json={
            **lot_context,
            "generation_origin": GENERATION_ORIGIN_GENERATOR,
            "ml_verdict": VERDICT_BLOQUEADO,
            "selected_card_format": 17,
            "card_format": 17,
        },
        games_count=20,
    )
    generations = load_operational_core_002_generations(db_path)
    assert any(int(row["generation_event_id"]) == ge_id for row in generations)
    diagnosis = diagnose_operational_coverage_gap(db_path)
    assert diagnosis["visible_in_coverage_loader"] is True
    assert diagnosis["persisted_games"] == 20


def test_sync_persisted_event_operational_status_aligns_needs_calibration() -> None:
    synced = sync_persisted_event_operational_status(
        {
            "operational_status": "pending_structural_review",
            "lot_operational_status": "needs_calibration",
        }
    )
    assert synced["operational_status"] == OPERATIONAL_STATUS_NEEDS_CALIBRATION
    assert synced["active_reading_scope"] is True


def test_sync_persisted_event_operational_status_marks_inactive_rejected() -> None:
    synced = sync_persisted_event_operational_status(
        {
            "operational_status": "pending_structural_review",
            "lot_operational_status": "blocked_for_officialization",
        }
    )
    assert synced["operational_status"] == "rejected"
    assert synced["active_reading_scope"] is False


def test_cobertura_page_loads_without_generation_list_cache() -> None:
    import dashboard.institutional_app as institutional_app

    source = inspect.getsource(institutional_app._render_cobertura_estrutural_page)
    assert "_load_operational_generations_cached" in source
    assert "diagnose_operational_coverage_gap" in source


def test_persist_clean_law15_defers_inactive_generator_status() -> None:
    import dashboard.institutional_app as institutional_app

    source = inspect.getsource(institutional_app._persist_clean_law15_generation_history)
    assert "defer_lot_status_for_structural_coverage" in source


def test_persist_clean_law15_invalidates_operational_cache() -> None:
    import dashboard.institutional_app as institutional_app

    source = inspect.getsource(institutional_app._persist_clean_law15_generation_history)
    assert "_invalidate_operational_structural_cache" in source
    assert "_bust_operational_coverage_cache" in source


def test_needs_calibration_is_active_structural_reading() -> None:
    from lotoia.operations.lot_operational_status import (
        is_active_structural_reading_status,
        resolve_lot_operational_status,
    )

    status = resolve_lot_operational_status(
        ml_verdict=VERDICT_PRECISA_CALIBRAR,
        official_release_allowed=False,
    )
    assert status == STATUS_NEEDS_CALIBRATION
    assert is_active_structural_reading_status(status)


def test_simulation_lab_lot_pending_structural_review() -> None:
    status = resolve_lot_operational_status(
        ml_verdict=VERDICT_APROVADO,
        official_release_allowed=True,
        generation_origin=GENERATION_ORIGIN_SIMULATION,
        simulation_mode=True,
    )
    assert status == STATUS_PENDING_STRUCTURAL_REVIEW
    assert is_active_structural_reading_status(status)


def test_simulation_calibration_authorized_active() -> None:
    from lotoia.operations.lot_operational_status import (
        STATUS_CALIBRATION_AUTHORIZED,
        is_active_structural_reading_status,
        resolve_lot_operational_status,
    )

    status = resolve_lot_operational_status(
        ml_verdict=VERDICT_APROVADO,
        official_release_allowed=False,
        generation_origin=GENERATION_ORIGIN_SIMULATION,
        simulation_mode=True,
        calibration_authorized=True,
    )
    assert status == STATUS_CALIBRATION_AUTHORIZED
    assert is_active_structural_reading_status(status)


def test_17d_needs_calibration_appears_in_operational_coverage_loader(tmp_path) -> None:
    db_path = tmp_path / "coverage.db"
    create_database(db_path)
    batch_label = resolve_core_002_batch_label(17)
    lot_context = build_lot_status_context(
        ml_verdict_payload={
            "ml_verdict": VERDICT_PRECISA_CALIBRAR,
            "official_release_allowed": False,
        },
        generation_origin="generator",
    )
    ge_id = _seed_sovereign_event(
        db_path,
        batch_label=batch_label,
        context_json={
            **lot_context,
            "selected_card_format": 17,
            "card_format": 17,
        },
        games_count=20,
    )
    generations = load_operational_core_002_generations(db_path)
    assert any(int(row["generation_event_id"]) == ge_id for row in generations)
    row = next(row for row in generations if int(row["generation_event_id"]) == ge_id)
    assert row["card_format"] == 17
    assert row["games_count"] == 20
    assert row["operational_status"] == OPERATIONAL_STATUS_NEEDS_CALIBRATION


def test_simulation_17d_pending_appears_in_card_structure_eligibility(tmp_path) -> None:
    db_path = tmp_path / "sim.db"
    create_database(db_path)
    batch_label = resolve_core_002_batch_label(17)
    lot_context = build_lot_status_context(
        ml_verdict_payload={"ml_verdict": VERDICT_APROVADO, "official_release_allowed": False},
        generation_origin=GENERATION_ORIGIN_SIMULATION,
        simulation_mode=True,
    )
    ge_id = _seed_sovereign_event(
        db_path,
        batch_label=batch_label,
        context_json={
            **lot_context,
            "generation_origin": GENERATION_ORIGIN_SIMULATION,
            "simulation_mode": True,
            "selected_card_format": 17,
        },
        games_count=20,
    )
    with get_session(db_path) as session:
        event = session.query(GenerationEvent).filter(GenerationEvent.id == ge_id).first()
        assert event is not None
        context = dict(event.context_json or {})
        assert is_generation_event_active_reading(event)
        assert _event_eligible_for_active_structural_reading(context)
        assert resolve_operational_status_from_context(context) == OPERATIONAL_STATUS_PENDING


def test_legacy_without_status_flagged_by_dry_run(tmp_path) -> None:
    db_path = tmp_path / "legacy.db"
    create_database(db_path)
    batch_label = resolve_core_002_batch_label(15)
    _seed_sovereign_event(
        db_path,
        batch_label=batch_label,
        context_json={"operational_status": OPERATIONAL_STATUS_PENDING},
        games_count=3,
    )
    report = dry_run_active_coverage_cleanup(db_path)
    assert report["candidates_count"] >= 1
    assert any(
        row.get("exclusion_reason") == "legacy_without_operational_status"
        for row in report.get("candidates") or []
    )


def test_active_coverage_scope_summary_latest_lot(tmp_path) -> None:
    db_path = tmp_path / "summary.db"
    create_database(db_path)
    batch_label = resolve_core_002_batch_label(17)
    lot_context = build_lot_status_context(
        ml_verdict_payload={"ml_verdict": VERDICT_PRECISA_CALIBRAR, "official_release_allowed": False},
    )
    _seed_sovereign_event(
        db_path,
        batch_label=batch_label,
        context_json={**lot_context, "selected_card_format": 17},
        games_count=20,
    )
    generations = load_operational_core_002_generations(db_path)
    summary = build_active_coverage_scope_summary(generations, exclusions_summary={"excluded_batches_count": 0})
    assert summary["active_lots_count"] == 1
    assert summary["latest_card_format"] == 17
    assert summary["latest_games_count"] == 20
    assert "GE" in summary["latest_summary"]
    assert STATUS_NEEDS_CALIBRATION in summary["latest_summary"]
