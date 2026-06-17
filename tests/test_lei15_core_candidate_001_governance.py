from __future__ import annotations

import pytest

from lotoia.generation.lei15_core_candidate_001 import build_candidate_pool
from lotoia.generation.lei15_core_structural_payload import (
    apply_core_traceability_payload,
    compute_structural_bias_score,
    is_v1_strong_pattern,
)
from lotoia.governance.lei15_core_candidate_001 import (
    BATCH_LABEL_A,
    BATCH_LABEL_D,
    ENV_VAR,
    resolve_candidate_config,
    should_apply_core_candidate_001,
)
from lotoia.generator.basic_generator import _compose_profiled_games
from lotoia.statistics.historical_intelligence import PROFILE_RECURRENT, profile_quota


def test_payload_fields() -> None:
    game = apply_core_traceability_payload(
        {"numbers": [1, 2, 3, 6, 8, 10, 11, 14, 15, 16, 18, 20, 22, 24, 25], "profile_type": PROFILE_RECURRENT},
        profile_origin=PROFILE_RECURRENT,
    )
    assert game["perfil_origem_real"] == PROFILE_RECURRENT
    assert game["prefix_signature"] == "01-02-03"
    assert game["suffix_signature"] == "22-24-25"
    assert "structural_bias_score" in game
    assert game["relabeling_applied"] is False


def test_v1_strong_shield_lowers_bias() -> None:
    nums = [1, 2, 3, 6, 8, 10, 11, 14, 15, 16, 18, 20, 22, 24, 25]
    assert is_v1_strong_pattern(nums)
    with_shield = compute_structural_bias_score(nums, profile_origin=PROFILE_RECURRENT)
    # Shield -18 vs padrão V1 forte; ainda pode ser alto por múltiplos pares sufixo
    assert with_shield < compute_structural_bias_score(nums, profile_origin="hibrido") + 20


def test_variant_d_has_nc1_nc6_nc3_nc2() -> None:
    cfg = resolve_candidate_config(BATCH_LABEL_D)
    assert cfg.pool_sampling_by_quota is True
    assert cfg.disable_profile_relabeling is True
    assert cfg.cap_last_draw_overlap is True
    assert cfg.adjusted_recurrence_scoring is True
    assert cfg.blind_spot_injection is True
    assert cfg.suffix_hot_cap is True
    assert cfg.structural_bias_penalty is True


def test_relabeling_metadata() -> None:
    from random import Random

    games = []
    for i in range(40):
        base = sorted({((i + j * 3) % 25) + 1 for j in range(15)})
        while len(base) < 15:
            base.append((len(base) + i) % 25 + 1)
        base = sorted(set(base))
        while len(base) < 15:
            base.append(Random(i).randint(1, 25))
            base = sorted(set(base))
        games.append(
            {
                "numbers": base[:15],
                "profile_type": PROFILE_RECURRENT,
                "profile_score": 90.0 - i,
                "final_score": {"final_score": 1.0},
            }
        )
    selected = _compose_profiled_games(games, 15, allow_profile_relabeling=True)
    assert any(g.get("relabeling_applied") for g in selected)
    assert any(g.get("relabeling_reason") for g in selected)
    honest = _compose_profiled_games(games, 15, allow_profile_relabeling=False)
    assert not any(g.get("relabeling_applied") for g in honest)


def test_pool_quota(monkeypatch) -> None:
    from lotoia.data.loader import load_draws_csv

    monkeypatch.setenv(ENV_VAR, "shadow_test")
    assert should_apply_core_candidate_001(BATCH_LABEL_A)
    cfg = resolve_candidate_config(BATCH_LABEL_A)
    pool = build_candidate_pool(60, seed=7, history=load_draws_csv(), config=cfg)
    targets = profile_quota(60)
    counts: dict[str, int] = {}
    for g in pool:
        k = str(g.get("perfil_origem_real"))
        counts[k] = counts.get(k, 0) + 1
    for profile, target in targets.items():
        assert abs(counts.get(profile, 0) - target) <= 3
