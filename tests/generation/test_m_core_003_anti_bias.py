"""M-CORE-003 — calibração anti-viés prefixo/sufixo."""

from __future__ import annotations

from lotoia.generation.lei15_core_structural_payload import (
    PREFIX_BIAS_GROUP_B,
    compute_structural_bias_score,
)
from lotoia.generation.m_core_003_prefix_suffix_policy import (
    enforce_gp_diversity_cap,
    historical_pattern_cap,
    pre_filter_pool_diversity,
    resolve_pattern_cap,
)
from lotoia.governance.lei15_core_candidate_001 import resolve_candidate_config, BATCH_LABEL_D
from lotoia.governance.law15_structural_realignment_v1 import StructuralRealignmentConfig


def test_structural_bias_weight_is_60_for_variant_d() -> None:
    cfg = resolve_candidate_config(BATCH_LABEL_D)
    assert cfg.structural_bias_weight == 60.0
    assert cfg.structural_bias_penalty is True


def test_historical_pattern_cap_proportional() -> None:
    assert historical_pattern_cap(1.40, gp_size=10) == 0
    assert historical_pattern_cap(1.40, gp_size=100) == 1
    assert historical_pattern_cap(3.50, gp_size=10) == 1
    assert historical_pattern_cap(20.09, gp_size=10) == 3
    assert historical_pattern_cap(20.09, gp_size=50) == 11
    assert resolve_pattern_cap("01-04-06", kind="prefix", gp_size=10) == 0


def test_prefix_group_b_increases_bias_score() -> None:
    numbers = [1, 4, 6, 8, 9, 10, 11, 12, 13, 14, 16, 17, 20, 22, 25]
    sig_prefix = "01-04-06"
    assert sig_prefix in PREFIX_BIAS_GROUP_B
    biased = compute_structural_bias_score(numbers, profile_origin="hibrido")
    neutral = compute_structural_bias_score(
        [2, 5, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 20, 22, 25],
        profile_origin="hibrido",
    )
    assert biased > neutral


def test_pre_filter_pool_respects_allowlist() -> None:
    pool = [
        {
            "numbers": [1, 4, 6, 8, 9, 10, 11, 12, 13, 14, 16, 17, 20, 22, 25],
            "prefix_signature": "01-04-06",
            "suffix_signature": "20-22-25",
            "profile_score": 80.0,
        },
        {
            "numbers": [2, 5, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 20, 22, 25],
            "prefix_signature": "99-88-77",
            "suffix_signature": "20-22-25",
            "profile_score": 90.0,
        },
    ]
    filtered = pre_filter_pool_diversity(pool)
    prefixes = {str(game.get("prefix_signature")) for game in filtered}
    assert "99-88-77" not in prefixes
    assert "01-04-06" in prefixes


def test_enforce_gp_diversity_cap_limits_rare_prefix() -> None:
    base_numbers = [1, 4, 6, 8, 9, 10, 11, 12, 13, 14, 16, 17, 20, 22, 25]
    games = []
    pool = []
    for index in range(12):
        numbers = base_numbers.copy()
        numbers[1] = 4 + (index % 3)
        game = {
            "numbers": numbers,
            "prefix_signature": "01-04-06",
            "suffix_signature": f"2{index % 3}-22-25",
            "profile_score": 90.0 - index,
        }
        games.append(game)
        pool.append(dict(game))
    capped = enforce_gp_diversity_cap(games, pool, 10)
    prefix_count = sum(1 for game in capped if game.get("prefix_signature") == "01-04-06")
    assert prefix_count == 0


def test_compose_sovereign_gp_delivers_large_batch_counts() -> None:
    import os

    os.environ.setdefault("LOTOIA_LEI15_CORE_002", "sovereign")
    from lotoia.data.loader import DEFAULT_HISTORY_PATH, load_draws_csv
    from lotoia.generation.lei15_core_002 import build_sovereign_pool, compose_sovereign_gp
    from lotoia.governance.lei15_core_002_sovereign import get_core_002_config

    label = "STRUCT_LEI15_CORE_CANDIDATE_002_15D_001"
    cfg = get_core_002_config(label)
    history = load_draws_csv(DEFAULT_HISTORY_PATH)
    pool = build_sovereign_pool(150, seed=42, history=history, config=cfg)
    gp = compose_sovereign_gp(pool, 50, cfg, game_size=15)
    assert len(gp) == 50
    assert sum(1 for game in gp if game.get("prefix_signature") == "01-04-06") == 0


def test_realignment_defaults_m_core_003() -> None:
    cfg = StructuralRealignmentConfig()
    assert cfg.max_prefix3_ratio == 0.10
    assert cfg.max_suffix3_ratio == 0.10
    assert cfg.concentration_penalty_weight == 200.0
    assert cfg.evidence_epoch == "EPOCH_002_M_CORE_003"
