from __future__ import annotations

from datetime import UTC, datetime

from lotoia.database.database import GeneratedGame, GenerationEvent, create_database, get_session
from lotoia.governance.batch_operational_scope import (
    OPERATIONAL_STATUS_CALIBRATION_SOURCE,
    OPERATIONAL_STATUS_PENDING,
    OPERATIONAL_STATUS_SUPERSEDED,
    is_active_reading_scope,
    is_generation_event_active_reading,
    merge_supersede_operational_fields,
    mark_generation_events_superseded_by_calibration,
    resolve_operational_status_from_context,
)
from lotoia.governance.lei15_core_002_sovereign import resolve_core_002_batch_label
from dashboard.institutional_operational_structural_coverage import (
    OPERATIONAL_GENERATION_ALL_LABEL,
    load_operational_core_002_generations,
)
from dashboard.institutional_supervised_ml import load_supervised_ml_operational_events_from_db


def _seed_core_event(
    db_path,
    *,
    ge_id_label: str,
    lot_operational_status: str = "",
    operational_status: str = OPERATIONAL_STATUS_PENDING,
    ml_enabled: int = 1,
) -> int:
    numbers = list(range(1, 16))
    context = {
        "batch_id": ge_id_label,
        "operational_status": operational_status,
        "selected_card_format": 15,
    }
    if lot_operational_status:
        context["lot_operational_status"] = lot_operational_status
    with get_session(db_path) as session:
        event = GenerationEvent(
            lead_id=None,
            first_name="institutional",
            whatsapp="",
            generated_games=[{"numbers": numbers}],
            context_json=context,
            ml_enabled=ml_enabled,
            seed=42,
            strategy="institutional_clean_hb",
            ranking_score=0.0,
            execution_time_ms=0.0,
            analysis_batch_label=resolve_core_002_batch_label(15),
            created_at=datetime.now(UTC),
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
                context_json=dict(context),
            )
        )
        session.commit()
        return event_id


def test_lot_operational_status_maps_to_inactive_scope(tmp_path) -> None:
    context = {"lot_operational_status": "superseded_by_calibration"}
    assert resolve_operational_status_from_context(context) == OPERATIONAL_STATUS_SUPERSEDED
    assert is_active_reading_scope(context) is False


def test_merge_supersede_syncs_both_status_fields() -> None:
    merged = merge_supersede_operational_fields(
        {"batch_id": "batch-1", "operational_status": OPERATIONAL_STATUS_PENDING},
        superseded_by_event_id=99,
        reason="test",
        calibration_source_only=True,
    )
    assert merged["operational_status"] == OPERATIONAL_STATUS_CALIBRATION_SOURCE
    assert merged["lot_operational_status"] == "calibration_source_only"
    assert merged["active_reading_scope"] is False


def test_operational_dropdown_excludes_superseded_lots(tmp_path) -> None:
    db_path = tmp_path / "dropdown.db"
    create_database(db_path)
    active_id = _seed_core_event(db_path, ge_id_label="batch-active")
    inactive_id = _seed_core_event(
        db_path,
        ge_id_label="batch-inactive",
        lot_operational_status="superseded_by_calibration",
    )
    assert active_id > 0 and inactive_id > 0

    active_generations = load_operational_core_002_generations(db_path, active_reading_only=True)
    active_ids = {int(row["generation_event_id"]) for row in active_generations}
    assert active_id in active_ids
    assert inactive_id not in active_ids
    assert OPERATIONAL_GENERATION_ALL_LABEL == "Todos — gerações ativas CORE_002"


def test_ml_loader_excludes_superseded_events(tmp_path) -> None:
    db_path = tmp_path / "ml.db"
    create_database(db_path)
    _seed_core_event(db_path, ge_id_label="batch-active-ml")
    inactive_id = _seed_core_event(
        db_path,
        ge_id_label="batch-inactive-ml",
        lot_operational_status="superseded_by_calibration",
    )

    events = load_supervised_ml_operational_events_from_db(db_path, limit=10)
    event_ids = {int(row["generation_event_id"]) for row in events}
    assert inactive_id not in event_ids


def test_mark_generation_events_superseded_persists_postgresql(tmp_path) -> None:
    db_path = tmp_path / "mark.db"
    create_database(db_path)
    event_id = _seed_core_event(db_path, ge_id_label="batch-mark")

    result = mark_generation_events_superseded_by_calibration(
        [event_id],
        db_path=db_path,
        reason="cockpit apply",
        operator="test",
        calibration_source_only=True,
    )
    assert result["active_reading_scope"] is False
    assert event_id in result["updated_generation_event_ids"]

    with get_session(db_path) as session:
        event = session.query(GenerationEvent).filter(GenerationEvent.id == event_id).one()
        assert not is_generation_event_active_reading(event)
        assert event.context_json["operational_status"] == OPERATIONAL_STATUS_CALIBRATION_SOURCE
