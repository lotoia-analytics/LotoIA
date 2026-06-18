from __future__ import annotations

from dashboard.institutional_build import BUILD_MARKER
from lotoia.ml.ml_operational_verdict import VERDICT_APROVADO, VERDICT_BLOQUEADO, VERDICT_PRECISA_CALIBRAR
from lotoia.operations.lot_operational_status import (
    GENERATION_ORIGIN_GENERATOR,
    GENERATION_ORIGIN_SIMULATION,
    MISSION_ID,
    STATUS_BLOCKED_FOR_OFFICIALIZATION,
    STATUS_NOT_OFFICIALIZED,
    STATUS_OFFICIALIZED,
    build_lot_status_context,
    is_active_structural_reading_status,
    is_analytical_history_eligible,
    is_official_conference_eligible,
    resolve_lot_operational_status,
)


def test_build_marker_v44() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v45"


def test_mission_id() -> None:
    assert MISSION_ID == "M-OPS-062"


def test_pending_then_blocked_from_verdict() -> None:
    status = resolve_lot_operational_status(
        ml_verdict=VERDICT_BLOQUEADO,
        official_release_allowed=False,
        generation_origin=GENERATION_ORIGIN_GENERATOR,
    )
    assert status == STATUS_BLOCKED_FOR_OFFICIALIZATION


def test_approved_officialized() -> None:
    status = resolve_lot_operational_status(
        ml_verdict=VERDICT_APROVADO,
        official_release_allowed=True,
        generation_origin=GENERATION_ORIGIN_GENERATOR,
    )
    assert status == STATUS_OFFICIALIZED
    assert is_official_conference_eligible({"lot_operational_status": status})
    assert is_analytical_history_eligible({"lot_operational_status": status})


def test_simulation_not_officialized() -> None:
    status = resolve_lot_operational_status(
        ml_verdict=VERDICT_APROVADO,
        official_release_allowed=True,
        generation_origin=GENERATION_ORIGIN_SIMULATION,
        simulation_mode=True,
    )
    assert status == STATUS_NOT_OFFICIALIZED
    assert not is_official_conference_eligible({"lot_operational_status": status})
    assert not is_analytical_history_eligible({"lot_operational_status": status})


def test_needs_calibration_not_in_active_structural_after_blocked() -> None:
    status = resolve_lot_operational_status(
        ml_verdict=VERDICT_PRECISA_CALIBRAR,
        official_release_allowed=False,
    )
    assert not is_active_structural_reading_status(status)


def test_build_lot_status_context_persist_fields() -> None:
    payload = build_lot_status_context(
        ml_verdict_payload={
            "ml_verdict": VERDICT_BLOQUEADO,
            "official_release_allowed": False,
        },
        generation_origin=GENERATION_ORIGIN_GENERATOR,
    )
    assert payload["lot_operational_status"] == STATUS_BLOCKED_FOR_OFFICIALIZATION
    assert payload["lot_status_trace"]["mission_id"] == MISSION_ID
    assert payload["is_active_structural_reading"] is False
