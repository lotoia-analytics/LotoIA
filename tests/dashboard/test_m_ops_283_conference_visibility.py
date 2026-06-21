from __future__ import annotations

from dashboard import conference_visibility_hotfix  # noqa: F401
from lotoia.operations.lot_operational_status import (
    STATUS_APPROVED_WITH_WARNING,
    STATUS_PENDING_STRUCTURAL_REVIEW,
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

    assert is_official_conference_eligible(group) is True
    assert is_analytical_history_eligible(group) is True


def test_pending_structural_review_remains_blocked() -> None:
    group = {
        "context_json": {
            "lot_operational_status": STATUS_PENDING_STRUCTURAL_REVIEW,
            "official_release_allowed": False,
        }
    }

    assert is_official_conference_eligible(group) is False
    assert is_analytical_history_eligible(group) is False


def test_status_field_without_context_json_is_supported() -> None:
    assert is_official_conference_eligible({"lot_operational_status": STATUS_APPROVED_WITH_WARNING}) is True
    assert is_official_conference_eligible({"post_calibration_promotion_status": STATUS_APPROVED_WITH_WARNING}) is True
