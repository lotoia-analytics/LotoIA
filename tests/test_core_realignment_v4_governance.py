from __future__ import annotations

import pytest

from lotoia.generation.core_realignment_v4 import compose_gp_v4, compute_pattern_score
from lotoia.governance.analysis_batch_labels import (
    LEI15_CORE_REALIGNMENT_V4_PATTERN_PROTECTED_TEST,
    build_batch_metadata,
    infer_batch_type,
)
from lotoia.governance.lei15_core_realignment_v4 import (
    BATCH_LABEL,
    ENV_VAR,
    REALIGNMENT_NAME,
    get_v4_config,
    is_v4_label,
    should_apply_v4,
)
from lotoia.statistics.historical_intelligence import PROFILE_HYBRID, PROFILE_RECURRENT


def _game(
    numbers: list[int],
    *,
    profile_score: float = 0.8,
    final_score: float = 0.5,
    profile_type: str = PROFILE_RECURRENT,
) -> dict:
    return {
        "numbers": numbers,
        "profile_score": profile_score,
        "final_score": {"final_score": final_score},
        "profile_type": profile_type,
    }


def test_v4_label_recognized() -> None:
    assert is_v4_label(BATCH_LABEL)
    assert not is_v4_label("STRUCT_LEI15_CORE_V3_1_PROTECTED_15D_001")


def test_should_apply_v4_shadow_only(monkeypatch) -> None:
    monkeypatch.setenv(ENV_VAR, "shadow_test")
    assert should_apply_v4(BATCH_LABEL)
    monkeypatch.setenv(ENV_VAR, "active")
    assert not should_apply_v4(BATCH_LABEL)
    monkeypatch.setenv(ENV_VAR, "off")
    assert not should_apply_v4(BATCH_LABEL)


def test_v4_batch_metadata() -> None:
    meta = build_batch_metadata(BATCH_LABEL, game_size=15, created_by="test")
    assert meta["analysis_batch_label"] == BATCH_LABEL
    assert meta["analysis_batch_type"] == LEI15_CORE_REALIGNMENT_V4_PATTERN_PROTECTED_TEST
    assert infer_batch_type(BATCH_LABEL) == LEI15_CORE_REALIGNMENT_V4_PATTERN_PROTECTED_TEST


def test_v4_config_tag() -> None:
    cfg = get_v4_config()
    assert cfg.realignment_tag == REALIGNMENT_NAME
    assert cfg.pattern_protected_ratio == 0.30


def test_pattern_score_strong_suffix() -> None:
    cfg = get_v4_config()
    game = _game([1, 2, 3, 6, 8, 10, 11, 14, 15, 16, 18, 20, 22, 24, 25])
    score, signals = compute_pattern_score(game, config=cfg)
    assert signals["strong_suffix"] is True
    assert signals["strong_prefix"] is True
    assert signals["high_close_24_25"] is True
    assert score >= cfg.min_pattern_score_faixa_a


def test_compose_gp_v4_faixa_a_ratio() -> None:
    from random import Random

    cfg = get_v4_config()
    rng = Random(42)
    pool: list[dict] = []
    universe = list(range(1, 26))
    for i in range(70):
        nums = sorted(rng.sample(universe, 15))
        pool.append(
            _game(
                nums,
                profile_score=0.9 - i * 0.005,
                profile_type=PROFILE_RECURRENT if i % 2 == 0 else PROFILE_HYBRID,
            )
        )
    pool.append(_game([1, 2, 3, 6, 8, 10, 11, 14, 15, 16, 18, 20, 22, 24, 25], profile_score=0.95))
    pool.append(_game([1, 3, 4, 6, 8, 9, 14, 15, 16, 17, 18, 21, 23, 24, 25], profile_score=0.94))

    gp_size = 15
    selected, _ = compose_gp_v4(pool, gp_size, cfg, game_size=15)
    assert len(selected) == gp_size
    faixa_a = [g for g in selected if (g.get("realignment_metadata") or {}).get("protected_v1_pattern")]
    expected_a = max(1, int(round(gp_size * cfg.pattern_protected_ratio)))
    assert len(faixa_a) == expected_a
    assert all(g.get("core_realignment_v4_applied") for g in selected)
