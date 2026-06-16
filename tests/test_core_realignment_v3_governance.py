from __future__ import annotations

import pytest

from lotoia.governance.analysis_batch_labels import (
    STRUCTURAL_CORE_REALIGNMENT_V3_BALANCED_TEST,
    build_batch_metadata,
    infer_batch_type,
)
from lotoia.governance.lei15_15a_core_realignment_v3 import (
    get_v3_config,
    is_v3_label,
    should_apply_v3,
)


def test_v3_label_recognized() -> None:
    assert is_v3_label("STRUCT_CORE_REALIGN_V3_BALANCED_15D_001")
    assert not is_v3_label("STRUCT_CORE_REALIGN_V2_15D_001")


def test_v3_batch_metadata() -> None:
    meta = build_batch_metadata(
        "STRUCT_CORE_REALIGN_V3_BALANCED_15D_001",
        game_size=15,
        created_by="test",
    )
    assert meta["analysis_batch_label"] == "STRUCT_CORE_REALIGN_V3_BALANCED_15D_001"
    assert meta["analysis_batch_type"] == STRUCTURAL_CORE_REALIGNMENT_V3_BALANCED_TEST


def test_should_apply_v3_shadow_test_only_for_label(monkeypatch) -> None:
    monkeypatch.setenv("LOTOIA_LEI15_15A_CORE_REALIGNMENT_V3", "shadow_test")
    assert should_apply_v3("STRUCT_CORE_REALIGN_V3_BALANCED_15D_001")
    assert not should_apply_v3("STRUCT_REALIGN_V1_15D_001")
    monkeypatch.setenv("LOTOIA_LEI15_15A_CORE_REALIGNMENT_V3", "off")
    assert not should_apply_v3("STRUCT_CORE_REALIGN_V3_BALANCED_15D_001")


def test_v3_config_balanced_thresholds() -> None:
    cfg = get_v3_config()
    assert cfg.max_prefix3_ratio >= 0.30
    assert cfg.max_pool_prefix3_ratio >= 0.40
    assert cfg.realignment_tag == "CORE_REALIGNMENT_V3_BALANCED"


def test_infer_batch_type_v3() -> None:
    assert infer_batch_type("STRUCT_CORE_REALIGN_V3_BALANCED_15D_001") == (
        STRUCTURAL_CORE_REALIGNMENT_V3_BALANCED_TEST
    )
