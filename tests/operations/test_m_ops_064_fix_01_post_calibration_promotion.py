"""M-OPS-064-FIX-01 — promoção conferível do lote calibrado N+1."""

from __future__ import annotations

from typing import Any

import pytest

import dashboard.institutional_app as institutional_app
from dashboard.institutional_build import BUILD_MARKER
from lotoia.ml.ml_operational_verdict import (
    VERDICT_APROVADO,
    VERDICT_APROVADO_COM_ALERTA,
    VERDICT_REPROVADO,
)
from lotoia.operations.lot_operational_status import (
    POST_CALIBRATION_PROMOTION_MISSION_ID,
    STATUS_APPROVED_WITH_WARNING,
    STATUS_NEEDS_CALIBRATION,
    STATUS_OFFICIALIZED,
    STATUS_PENDING_STRUCTURAL_REVIEW,
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


def test_build_marker_v72() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v72"


def test_n1_aprovado_promoted_to_officialized() -> None:
    promoted = promote_post_calibration_consumer_lot_visibility(
        {
            "lot_operational_status": STATUS_PENDING_STRUCTURAL_REVIEW,
            "official_release_allowed": True,
            "ml_verdict": VERDICT_APROVADO,
        },
        authorized_plan=_consumer_plan(),
        promotion_context=_promo_context(
            gp_quality_tier="APROVADO",
            ml_verdict=VERDICT_APROVADO,
            official_release_allowed=True,
        ),
    )
    assert promoted["lot_operational_status"] == STATUS_OFFICIALIZED
    assert promoted["post_calibration_promotion_evaluated"] is True
    assert promoted["promoted_to_analytical_history"] is True
    assert promoted["promoted_to_official_conference"] is True
    assert promoted["promotion_block_reason"] == ""
    assert is_analytical_history_eligible(promoted)
    assert is_official_conference_eligible(promoted)


def test_n1_atencao_promoted_to_approved_with_warning() -> None:
    promoted = promote_post_calibration_consumer_lot_visibility(
        {
            "lot_operational_status": STATUS_NEEDS_CALIBRATION,
            "ml_verdict": VERDICT_APROVADO_COM_ALERTA,
        },
        authorized_plan=_consumer_plan(),
        promotion_context=_promo_context(
            gp_quality_tier="ATENÇÃO",
            ml_verdict=VERDICT_APROVADO_COM_ALERTA,
            official_release_allowed=True,
        ),
    )
    assert promoted["lot_operational_status"] == STATUS_APPROVED_WITH_WARNING
    assert promoted["promoted_to_analytical_history"] is True
    assert promoted["promoted_to_official_conference"] is True
    assert is_analytical_history_eligible(promoted)
    assert is_official_conference_eligible(promoted)


def test_n1_reprovado_not_promoted_with_reason() -> None:
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
    assert promoted["lot_operational_status"] != STATUS_PENDING_STRUCTURAL_REVIEW
    assert promoted["promoted_to_analytical_history"] is False
    assert promoted["promoted_to_official_conference"] is False
    assert promoted["promotion_block_reason"]
    assert promoted["post_calibration_consumer_not_released"] is True
    assert not is_analytical_history_eligible(promoted)
    assert not is_official_conference_eligible(promoted)


def test_initial_lot_without_calibration_plan_unchanged() -> None:
    original = {
        "lot_operational_status": STATUS_NEEDS_CALIBRATION,
        "ml_verdict": VERDICT_REPROVADO,
    }
    result = promote_post_calibration_consumer_lot_visibility(
        dict(original),
        authorized_plan={"calibration_plan_loaded_from_db": False},
        promotion_context=_promo_context(gp_quality_tier="REPROVADO"),
    )
    assert result == original


def test_promote_does_not_overwrite_existing_conferivel_status() -> None:
    promoted = promote_post_calibration_consumer_lot_visibility(
        {
            "lot_operational_status": STATUS_OFFICIALIZED,
            "official_release_allowed": True,
            "ml_verdict": VERDICT_APROVADO,
        },
        authorized_plan=_consumer_plan(),
        promotion_context=_promo_context(
            gp_quality_tier="APROVADO",
            ml_verdict=VERDICT_APROVADO,
            official_release_allowed=True,
        ),
    )
    assert promoted["lot_operational_status"] == STATUS_OFFICIALIZED
    assert promoted["promoted_to_analytical_history"] is True


def test_context_json_promotion_trace_fields() -> None:
    promoted = promote_post_calibration_consumer_lot_visibility(
        {"lot_operational_status": STATUS_PENDING_STRUCTURAL_REVIEW},
        authorized_plan=_consumer_plan(),
        promotion_context=_promo_context(gp_quality_tier="APROVADO", ml_verdict=VERDICT_APROVADO),
    )
    assert promoted["post_calibration_consumer_lot"] is True
    assert promoted["calibration_plan_loaded_from_db"] is True
    assert promoted["calibration_plan_applied_to_generation"] is True
    assert promoted["post_calibration_promotion_evaluated"] is True
    assert promoted["post_calibration_promotion_status"] == STATUS_OFFICIALIZED
    assert promoted["post_calibration_promotion_mission_id"] == POST_CALIBRATION_PROMOTION_MISSION_ID


def test_prerequisites_block_promotion_games_mismatch() -> None:
    promoted = promote_post_calibration_consumer_lot_visibility(
        {"lot_operational_status": STATUS_PENDING_STRUCTURAL_REVIEW},
        authorized_plan=_consumer_plan(),
        promotion_context=_promo_context(
            generated_games_count=15,
            requested_count=20,
            gp_quality_tier="APROVADO",
        ),
    )
    assert promoted["promoted_to_analytical_history"] is False
    assert promoted["promotion_block_reason"] == "generated_games_count_mismatch"


def test_n1_aprovado_in_analytical_history_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    n1_generation: dict[str, Any] = {
        "generation_event_id": 201,
        "lot_operational_status": STATUS_OFFICIALIZED,
        "official_release_allowed": True,
        "is_active_reading": True,
        "seed": 1,
        "strategy": "institutional_clean_hb",
        "created_at": "2026-06-18T12:00:00",
        "batch_id": "n1-calibrated",
        "post_calibration_consumer_lot": True,
        "games": [{"game_index": 1, "numbers": list(range(1, 16)), "generation_context": {}}],
    }
    initial_generation: dict[str, Any] = {
        "generation_event_id": 200,
        "lot_operational_status": STATUS_NEEDS_CALIBRATION,
        "official_release_allowed": False,
        "is_active_reading": True,
        "games": [{"game_index": 1, "numbers": list(range(1, 16)), "generation_context": {}}],
    }
    monkeypatch.setattr(
        institutional_app,
        "_load_generation_history_light",
        lambda limit=25: [n1_generation, initial_generation],
    )
    monkeypatch.setattr(institutional_app, "_load_sovereign_generation_event_rows", lambda: [])
    rows = institutional_app._load_accumulated_analytical_rows_light(limit=10)
    generation_ids = {int(row.get("generation_event_id", 0) or 0) for row in rows}
    assert 201 in generation_ids
    assert 200 not in generation_ids


def test_n1_aprovado_in_official_conference_groups(monkeypatch: pytest.MonkeyPatch) -> None:
    groups = [
        {
            "generation_event_id": 301,
            "lot_operational_status": STATUS_OFFICIALIZED,
            "is_official_conference_eligible": True,
            "official_release_allowed": True,
            "post_calibration_consumer_lot": True,
            "games": [],
        },
        {
            "generation_event_id": 300,
            "lot_operational_status": STATUS_NEEDS_CALIBRATION,
            "is_official_conference_eligible": False,
            "official_release_allowed": False,
            "games": [],
        },
    ]
    monkeypatch.setattr(institutional_app, "_load_persisted_generation_event_groups", lambda **_: groups)
    eligible = institutional_app._load_official_conference_generation_groups()
    ids = {int(group.get("generation_event_id", 0) or 0) for group in eligible}
    assert 301 in ids
    assert 300 not in ids
