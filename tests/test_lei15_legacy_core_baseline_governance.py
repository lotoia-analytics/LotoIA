from __future__ import annotations

import pytest

from lotoia.governance.lei15_legacy_core_baseline import (
    CDX_CANDIDATE_LABEL_D,
    LEGACY_CORE_BASELINE_LABEL,
    assert_no_new_legacy_extensive_lot,
    is_cdx_candidate_label,
    is_legacy_core_frozen_label,
)


def test_legacy_baseline_frozen() -> None:
    assert is_legacy_core_frozen_label(LEGACY_CORE_BASELINE_LABEL)
    assert is_legacy_core_frozen_label("STRUCT_CORE_REALIGN_V2_15D_001")
    assert not is_legacy_core_frozen_label(CDX_CANDIDATE_LABEL_D)


def test_cdx_not_legacy() -> None:
    assert is_cdx_candidate_label(CDX_CANDIDATE_LABEL_D)
    assert not is_legacy_core_frozen_label(CDX_CANDIDATE_LABEL_D)


def test_blocks_new_legacy_lot() -> None:
    with pytest.raises(RuntimeError, match="congelado"):
        assert_no_new_legacy_extensive_lot(
            batch_label=LEGACY_CORE_BASELINE_LABEL,
            new_events=1,
        )


def test_allows_cdx_lot() -> None:
    assert_no_new_legacy_extensive_lot(batch_label=CDX_CANDIDATE_LABEL_D, new_events=1)
