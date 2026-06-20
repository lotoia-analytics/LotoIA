"""M-OPS-065 — promoção cautelosa N+1 com plano autorizado consumido."""

from __future__ import annotations

from typing import Any

import pytest

from dashboard.institutional_build import BUILD_MARKER
from lotoia.ml.ml_operational_verdict import VERDICT_PRECISA_CALIBRAR, VERDICT_REPROVADO
from lotoia.operations.lot_operational_status import (
    AUTHORIZED_PLAN_PROMOTION_BYPASS_MISSION_ID,
    PROMOTION_BYPASS_REASON_AUTHORIZED_PLAN_CONSUMED,
    STATUS_APPROVED_WITH_WARNING,
    STATUS_NEEDS_CALIBRATION,
    STATUS_REJECTED,
    is_analytical_history_eligible,
    is_official_conference_eligible,
    promote_post_calibration_consumer_lot_visibility,
)


def _consumer_plan() -> dict[str, Any]:
    return {
        "calibration_plan_loaded_from_db": True,
        "calibration_plan_applied_to_generation": True,
        "calibration_plan_source_generation_event_id": 10,
        "calibration_trace_id": "trace-n1",
    }


def _promo_context(**overrides: Any) -> dict[str, Any]:
    base = {
        "generated_games_count": 20,
        "requested_count": 20,
        "persistence_supported": True,
        "persistence_blocked": False,
        "runtime_contract_broken": False,
        "hierarchy_delivery_blocked": False,
    }
    base.update(overrides)
    return base


def test_n1_precisa_calibrar_with_authorized_plan_promoted_with_caution() -> None:
    promoted = promote_post_calibration_consumer_lot_visibility(
        {
            "lot_operational_status": STATUS_NEEDS_CALIBRATION,
            "ml_verdict": VERDICT_PRECISA_CALIBRAR,
            "official_release_allowed": False,
        },
        authorized_plan=_consumer_plan(),
        promotion_context=_promo_context(
            ml_verdict=VERDICT_PRECISA_CALIBRAR,
            official_release_allowed=False,
        ),
    )
    assert promoted["lot_operational_status"] == STATUS_APPROVED_WITH_WARNING
    assert promoted["ml_verdict_after_authorized_plan"] == VERDICT_PRECISA_CALIBRAR
    assert promoted["ml_verdict"] == VERDICT_PRECISA_CALIBRAR
    assert promoted["promotion_bypass_reason"] == PROMOTION_BYPASS_REASON_AUTHORIZED_PLAN_CONSUMED
    assert promoted["authorized_plan_promotion_bypass_mission_id"] == AUTHORIZED_PLAN_PROMOTION_BYPASS_MISSION_ID
    assert promoted["authorized_plan_applied_to_generation"] is True
    assert promoted["promoted_to_analytical_history"] is True
    assert promoted["promoted_to_official_conference"] is True
    assert promoted["promotion_block_reason"] == ""
    assert is_analytical_history_eligible(promoted)
    assert is_official_conference_eligible(promoted)


def test_n1_precisa_calibrar_without_plan_not_bypassed() -> None:
    promoted = promote_post_calibration_consumer_lot_visibility(
        {
            "lot_operational_status": STATUS_NEEDS_CALIBRATION,
            "ml_verdict": VERDICT_PRECISA_CALIBRAR,
        },
        authorized_plan={"calibration_plan_loaded_from_db": False},
        promotion_context=_promo_context(ml_verdict=VERDICT_PRECISA_CALIBRAR),
    )
    assert promoted.get("promotion_bypass_reason") is None
    assert promoted["lot_operational_status"] == STATUS_NEEDS_CALIBRATION
    assert not is_analytical_history_eligible(promoted)


def test_n1_reprovado_with_authorized_plan_still_blocked() -> None:
    promoted = promote_post_calibration_consumer_lot_visibility(
        {
            "lot_operational_status": STATUS_REJECTED,
            "ml_verdict": VERDICT_REPROVADO,
        },
        authorized_plan=_consumer_plan(),
        promotion_context=_promo_context(
            gp_quality_tier="REPROVADO",
            ml_verdict=VERDICT_REPROVADO,
            official_release_allowed=False,
        ),
    )
    assert promoted["lot_operational_status"] == STATUS_REJECTED
    assert promoted.get("promotion_bypass_reason") is None
    assert promoted["promoted_to_analytical_history"] is False
    assert not is_analytical_history_eligible(promoted)


def test_build_marker_v75() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v83"
