from __future__ import annotations

import pytest

from lotoia.generation.core_realignment_v3_1 import compose_gp_v3_1
from lotoia.governance.analysis_batch_labels import (
    LEI15_CORE_REALIGNMENT_V3_1_PROTECTED_TEST,
    build_batch_metadata,
    infer_batch_type,
)
from lotoia.governance.lei15_core_realignment_v3_1 import (
    ENV_VAR,
    P15_BATCH_LABEL,
    REALIGNMENT_NAME,
    get_v3_1_config,
    is_p15_label,
    is_v3_1_label,
    resolve_v3_1_config,
    should_apply_v3_1,
)


def _game(numbers: list[int], *, profile_score: float, final_score: float) -> dict:
    return {
        "numbers": numbers,
        "profile_score": profile_score,
        "final_score": {"final_score": final_score},
    }


def test_v3_1_label_recognized() -> None:
    assert is_v3_1_label("STRUCT_LEI15_CORE_V3_1_PROTECTED_15D_001")
    assert not is_v3_1_label("STRUCT_CORE_REALIGN_V3_BALANCED_15D_001")


def test_should_apply_v3_1_shadow_only(monkeypatch) -> None:
    monkeypatch.setenv(ENV_VAR, "shadow_test")
    assert should_apply_v3_1("STRUCT_LEI15_CORE_V3_1_PROTECTED_15D_001")
    monkeypatch.setenv(ENV_VAR, "active")
    assert not should_apply_v3_1("STRUCT_LEI15_CORE_V3_1_PROTECTED_15D_001")


def test_v3_1_batch_metadata() -> None:
    meta = build_batch_metadata(
        "STRUCT_LEI15_CORE_V3_1_PROTECTED_15D_001",
        game_size=15,
        created_by="test",
    )
    assert meta["analysis_batch_label"] == "STRUCT_LEI15_CORE_V3_1_PROTECTED_15D_001"
    assert meta["analysis_batch_type"] == LEI15_CORE_REALIGNMENT_V3_1_PROTECTED_TEST


def test_compose_gp_v3_1_protects_top_score_slots() -> None:
    cfg = get_v3_1_config()
    pool = [
        _game(
            sorted([(i + j) % 25 + 1 for j in range(15)]),
            profile_score=0.9 - i * 0.01,
            final_score=0.5,
        )
        for i in range(20)
    ]
    selected, _ = compose_gp_v3_1(pool, 15, cfg, game_size=15)
    assert len(selected) == 15
    protected = [g for g in selected if (g.get("realignment_metadata") or {}).get("protected_top_score")]
    assert len(protected) == cfg.protected_top_score_slots
    assert all(g.get("core_realignment_v3_1_applied") for g in selected)


def test_v3_1_config_tag() -> None:
    cfg = get_v3_1_config()
    assert cfg.realignment_tag == REALIGNMENT_NAME


def test_p15_label_and_config() -> None:
    assert is_p15_label(P15_BATCH_LABEL)
    assert is_v3_1_label(P15_BATCH_LABEL)
    assert not is_p15_label("STRUCT_LEI15_CORE_V3_1_PROTECTED_15D_001")
    cfg = resolve_v3_1_config(P15_BATCH_LABEL)
    assert cfg.protected_top_score_slots == 15
    assert cfg.max_suffix3_ratio == 0.35
    assert cfg.realignment_tag == "LEI15_CORE_REALIGNMENT_V3_1_P15_PROTECTED"


def test_infer_batch_type_p15() -> None:
    from lotoia.governance.analysis_batch_labels import LEI15_CORE_REALIGNMENT_V3_1_P15_PROTECTED_TEST

    assert infer_batch_type(P15_BATCH_LABEL) == LEI15_CORE_REALIGNMENT_V3_1_P15_PROTECTED_TEST
