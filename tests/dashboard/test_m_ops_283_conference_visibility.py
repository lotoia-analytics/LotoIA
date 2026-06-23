from __future__ import annotations

from lotoia.operations.lot_operational_status import (
    STATUS_APPROVED_WITH_WARNING,
    STATUS_PENDING_STRUCTURAL_REVIEW,
    extract_lot_operational_status,
    is_analytical_history_eligible,
    is_official_conference_eligible,
)


def test_approved_with_warning_is_conference_eligible_from_context_json_group() -> None:
    group = {
        "is_official_conference_eligible": False,
        "games_promoted_to_conference": 0,
        "context_json": {
            "lot_operational_status": STATUS_APPROVED_WITH_WARNING,
            "official_release_allowed": True,
        },
    }

    assert extract_lot_operational_status(group) == STATUS_APPROVED_WITH_WARNING
    assert is_official_conference_eligible(group) is True
    assert is_analytical_history_eligible(group) is True


def test_pending_structural_review_is_conference_eligible_observational() -> None:
    """M-SENSOR-001: pending_structural_review agora é conferível como observacional.

    A conferência observacional permite medir a performance real dos jogos antes
    da aprovação formal do ML. Isso quebra o loop fechado onde o ML bloqueava a
    conferência e sem conferência não havia dados para calibrar o ML.
    """
    group = {
        "context_json": {
            "lot_operational_status": STATUS_PENDING_STRUCTURAL_REVIEW,
            "official_release_allowed": False,
        }
    }

    assert extract_lot_operational_status(group) == STATUS_PENDING_STRUCTURAL_REVIEW
    assert (
        is_official_conference_eligible(group) is True
    )  # M-SENSOR-001: agora conferível
    assert (
        is_analytical_history_eligible(group) is False
    )  # histórico analítico permanece bloqueado


def test_status_resolution_accepts_derived_status_fields() -> None:
    assert (
        is_official_conference_eligible(
            {"lot_operational_status": STATUS_APPROVED_WITH_WARNING}
        )
        is True
    )
    assert (
        is_official_conference_eligible(
            {"post_calibration_promotion_status": STATUS_APPROVED_WITH_WARNING}
        )
        is True
    )
    assert (
        is_official_conference_eligible(
            {"officialization_status": STATUS_APPROVED_WITH_WARNING}
        )
        is True
    )
