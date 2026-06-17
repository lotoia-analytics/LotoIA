from __future__ import annotations

import pytest

from lotoia.governance.history_preservation_policy import (
    PROTECTED_GENERATION_EVENT_IDS,
    PreservationClass,
    assert_generic_institutional_purge_blocked,
    assert_generation_event_deletion_allowed,
    classify_batch_label,
    evaluate_generation_events_for_cleanup,
    get_protected_batch_labels,
    institutional_preservation_summary,
)
from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL as SOVEREIGN_LABEL
from lotoia.governance.lei15_legacy_core_baseline import (
    CDX_CANDIDATE_LABEL_A,
    CDX_CANDIDATE_LABEL_D,
    LEGACY_CORE_BASELINE_LABEL,
    V1_EVIDENCE_LABEL,
)


def test_protected_labels_include_mandatory() -> None:
    labels = get_protected_batch_labels()
    for required in (
        SOVEREIGN_LABEL,
        LEGACY_CORE_BASELINE_LABEL,
        V1_EVIDENCE_LABEL,
        CDX_CANDIDATE_LABEL_A,
        CDX_CANDIDATE_LABEL_D,
        "STRUCT_CORE_REALIGN_V2_15D_001",
        "STRUCT_LEI15_CORE_CANDIDATE_001_D_15D_001",
    ):
        assert required in labels


def test_classify_sovereign_and_legacy() -> None:
    sovereign = classify_batch_label(SOVEREIGN_LABEL)
    assert sovereign.preservation_class == PreservationClass.SOVEREIGN
    assert sovereign.protected is True

    legacy = classify_batch_label(LEGACY_CORE_BASELINE_LABEL)
    assert legacy.preservation_class == PreservationClass.FROZEN_LEGACY
    assert legacy.protected is True


def test_unknown_label_fail_closed() -> None:
    unknown = classify_batch_label("CUSTOM_UNKNOWN_BATCH_X")
    assert unknown.protected is True
    assert unknown.preservation_class == PreservationClass.INSTITUTIONAL_UNKNOWN

    empty = classify_batch_label(None)
    assert empty.protected is True


def test_protected_ge_ids() -> None:
    assert 114 in PROTECTED_GENERATION_EVENT_IDS
    assert 115 in PROTECTED_GENERATION_EVENT_IDS


def test_generic_purge_blocked() -> None:
    with pytest.raises(RuntimeError, match="Purge"):
        assert_generic_institutional_purge_blocked(source="test")


def test_ge_deletion_blocked_for_evidence() -> None:
    with pytest.raises(RuntimeError, match="DELETE bloqueado"):
        assert_generation_event_deletion_allowed(
            generation_event_id=114,
            batch_label=CDX_CANDIDATE_LABEL_A,
            source="test",
        )
    with pytest.raises(RuntimeError, match="DELETE bloqueado"):
        assert_generation_event_deletion_allowed(
            generation_event_id=51,
            batch_label="STRUCT_CORE_REALIGN_V2_15D_001",
            source="test",
        )


def test_dry_run_evaluation() -> None:
    rows = [
        {"id": 114, "analysis_batch_label": CDX_CANDIDATE_LABEL_A},
        {"id": 115, "analysis_batch_label": CDX_CANDIDATE_LABEL_D},
        {"id": 999, "analysis_batch_label": None},
    ]
    result = evaluate_generation_events_for_cleanup(rows)
    assert result["protected_count"] == 3
    assert result["potentially_disposable_count"] == 0
    assert result["generic_purge_allowed"] is False


def test_institutional_summary() -> None:
    summary = institutional_preservation_summary()
    assert summary["generic_purge_blocked"] is True
    assert summary["mandatory_preservation"]["ge_114"]
