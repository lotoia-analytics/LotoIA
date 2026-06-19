"""M-STAT-002 — seleção estatística diversa do top slice pré-GP."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any
from unittest.mock import patch

import pytest

from dashboard.institutional_build import BUILD_MARKER
from lotoia.governance.institutional_agent_routing_matrix import AGENT_ESTATISTICO, AGENT_GERACAO
from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL
from lotoia.ml.ml_operational_hierarchy import (
    STAGE_DIVERSITY,
    execute_ml_operational_hierarchy,
)
from lotoia.ml.overlap_format_thresholds import DIVERSITY_LOW_THRESHOLD
from lotoia.ml.supervised_output_calibration import DOMINANCE_CALIBRATION_THRESHOLD
from lotoia.statistics.diverse_top_slice_selection import (
    DOMINANT_STRUCTURAL_TRIPLE_LABEL,
    MISSION_ID,
    MIN_MATERIAL_DIVERSITY_GAIN,
    _prefix_key,
    _suffix_key,
    apply_diverse_top_slice_pre_gp,
    build_diverse_top_slice_trace,
    evaluate_top_slice_criteria,
    is_diverse_top_slice_enabled,
    run_mstat_002_swap_engine,
    select_diverse_pre_gp_top_slice,
    slice_limit,
)
from lotoia.generator.basic_generator import _attach_scores, _build_game

STRUCTURAL_TRIPLE = (1, 2, 3)
DOMINANT_SUFFIX = (20, 21, 22, 23, 24)
RESERVE_HEAD = (4, 5, 6)


def _unique_cards_with_fixed_numbers(
    count: int,
    *,
    fixed: tuple[int, ...],
    exclude: frozenset[int] | None = None,
) -> list[list[int]]:
    fixed_set = set(fixed)
    excluded = set(exclude or ())
    available = sorted(value for value in range(1, 26) if value not in fixed_set and value not in excluded)
    head_needed = 15 - len(fixed_set)
    cards: list[list[int]] = []
    for combo in combinations(available, head_needed):
        cards.append(sorted(list(combo) + list(fixed)))
        if len(cards) >= count:
            break
    return cards


def _diverse_cards_without_structural_triple(count: int) -> list[list[int]]:
    cards: list[list[int]] = []
    for combo in combinations(range(1, 26), 15):
        ordered = sorted(combo)
        if tuple(ordered[:3]) == STRUCTURAL_TRIPLE:
            continue
        cards.append(ordered)
        if len(cards) >= count:
            break
    return cards


def _reserve_cards_non_triplet_varied_suffix(count: int) -> list[list[int]]:
    """Reserva útil: sem trinca 01-02-03 e com sufixos alternativos."""
    cards: list[list[int]] = []
    suffix_options = ((13, 14, 15), (16, 17, 18), (9, 10, 11))
    index = 0
    for combo in combinations(range(7, 20), 9):
        suffix = suffix_options[index % len(suffix_options)]
        head = RESERVE_HEAD + tuple(combo)
        if len(set(head) | set(suffix)) != len(head) + len(suffix):
            continue
        ordered = sorted(set(head) | set(suffix))
        if len(ordered) != 15:
            continue
        if tuple(ordered[:3]) == STRUCTURAL_TRIPLE:
            continue
        cards.append(ordered)
        index += 1
        if len(cards) >= count:
            break
    if len(cards) < count:
        cards.extend(_diverse_cards_without_structural_triple(count - len(cards)))
    return cards[:count]


def _pool_from_card_groups(
    *,
    dominant_cards: list[list[int]],
    reserve_cards: list[list[int]],
) -> list[dict[str, Any]]:
    pool: list[dict[str, Any]] = []
    for index, numbers in enumerate(dominant_cards):
        game = _build_game(numbers)
        game["profile_score"] = 1000 - index
        _attach_scores(game, profile_type="recorrente")
        pool.append(game)
    for index, numbers in enumerate(reserve_cards):
        game = _build_game(numbers)
        game["profile_score"] = 300 - index
        _attach_scores(game, profile_type="recorrente")
        pool.append(game)
    pool.sort(key=lambda row: float(row.get("profile_score", 0.0) or 0.0), reverse=True)
    return pool


def _build_suffix_isolated_pool(*, pool_size: int = 100) -> list[dict[str, Any]]:
    """Sufixo dominante no top; trinca 01-02-03 ausente (dentro do teto)."""
    dominant_count = max(40, pool_size // 2)
    reserve_count = pool_size - dominant_count
    dominant_cards = _unique_cards_with_fixed_numbers(
        dominant_count,
        fixed=DOMINANT_SUFFIX,
        exclude=frozenset(STRUCTURAL_TRIPLE),
    )
    reserve_cards = _reserve_cards_non_triplet_varied_suffix(reserve_count)
    return _pool_from_card_groups(dominant_cards=dominant_cards, reserve_cards=reserve_cards)


def _build_triple_isolated_pool(*, pool_size: int = 100) -> list[dict[str, Any]]:
    """Trinca 01-02-03 dominante no top; sufixos variados (dentro do teto)."""
    dominant_count = max(40, pool_size // 2)
    reserve_count = pool_size - dominant_count
    dominant_cards = _unique_cards_with_fixed_numbers(dominant_count, fixed=STRUCTURAL_TRIPLE)
    reserve_cards = _reserve_cards_non_triplet_varied_suffix(reserve_count)
    return _pool_from_card_groups(dominant_cards=dominant_cards, reserve_cards=reserve_cards)


def _build_combined_conflict_pool(*, pool_size: int = 100) -> list[dict[str, Any]]:
    """Trinca + sufixo dominantes no top; reserva não-trinca com sufixos alternativos."""
    dominant_count = max(40, pool_size // 2)
    reserve_count = pool_size - dominant_count
    dominant_cards = _unique_cards_with_fixed_numbers(
        dominant_count,
        fixed=STRUCTURAL_TRIPLE + DOMINANT_SUFFIX,
    )
    reserve_cards = _reserve_cards_non_triplet_varied_suffix(reserve_count)
    return _pool_from_card_groups(dominant_cards=dominant_cards, reserve_cards=reserve_cards)


def _build_insufficient_non_triplet_reserve_pool(*, pool_size: int = 100) -> list[dict[str, Any]]:
    """Pouca reserva não-trinca: agent_estatistico esgota swaps úteis."""
    dominant_count = max(40, pool_size // 2)
    reserve_count = pool_size - dominant_count
    dominant_cards = _unique_cards_with_fixed_numbers(dominant_count, fixed=STRUCTURAL_TRIPLE)
    reserve_cards = _reserve_cards_non_triplet_varied_suffix(reserve_count)
    return _pool_from_card_groups(dominant_cards=dominant_cards, reserve_cards=reserve_cards)


def _build_all_triple_contaminated_pool(*, pool_size: int = 100) -> list[dict[str, Any]]:
    """Cenário artificial 100% trinca — bloqueia swaps de sufixo por regra estrutural."""
    dominant_count = max(40, pool_size // 2)
    reserve_count = pool_size - dominant_count
    dominant_cards = _unique_cards_with_fixed_numbers(
        dominant_count,
        fixed=STRUCTURAL_TRIPLE + DOMINANT_SUFFIX,
    )
    reserve_cards = _unique_cards_with_fixed_numbers(
        reserve_count,
        fixed=STRUCTURAL_TRIPLE,
    )
    return _pool_from_card_groups(dominant_cards=dominant_cards, reserve_cards=reserve_cards)


def _build_mixed_score_dominant_prefix_pool(*, pool_size: int = 100, requested_count: int = 20) -> list[dict[str, Any]]:
    return _build_insufficient_non_triplet_reserve_pool(pool_size=pool_size)


def _build_mixed_score_dominant_pool(*, pool_size: int = 100, requested_count: int = 20) -> list[dict[str, Any]]:
    return _build_suffix_isolated_pool(pool_size=pool_size)


def _count_triple(games: list[dict[str, Any]]) -> int:
    return sum(1 for game in games if _prefix_key(game) == DOMINANT_STRUCTURAL_TRIPLE_LABEL)


def _max_suffix_share(games: list[dict[str, Any]]) -> int:
    counts: dict[str, int] = {}
    for game in games:
        suffix = _suffix_key(game)
        if suffix:
            counts[suffix] = counts.get(suffix, 0) + 1
    return max(counts.values()) if counts else 0


@dataclass
class _Draw:
    numbers: list[int]


def _history() -> list[_Draw]:
    return [_Draw(sorted(range(1, 16)))] + [
        _Draw(sorted({((offset * 3 + index * 2) % 25) + 1 for index in range(15)}))
        for offset in range(12)
    ]


@pytest.fixture(autouse=True)
def _enable_stack(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOTOIA_DIVERSE_TOP_SLICE_ENABLED", "1")
    monkeypatch.setenv("LOTOIA_ML_OPERATIONAL_HIERARCHY_ENABLED", "1")
    monkeypatch.setenv("LOTOIA_ML_STRUCTURAL_15D_POOL_ENABLED", "0")
    monkeypatch.setenv("LOTOIA_ML_PRE_FINAL_POOL_ENABLED", "0")
    policy: dict[str, Any] = {
        "policy_version": "M-ML-070-v1",
        "core_numbers": [7, 12, 16, 23],
        "discouraged_numbers": [2, 4, 11, 15, 24, 25],
    }
    monkeypatch.setattr(
        "lotoia.ml.supervised_output_calibration.ensure_structural_policy_15d_memory",
        lambda db_path=None: policy,
    )
    monkeypatch.setattr(
        "lotoia.ml.supervised_output_calibration.build_structural_policy_15d_calibration_plan",
        lambda bundle, policy_payload: {"has_plan": False, "parametros_sugeridos": {}},
    )


def test_slice_limit_gp20_is_60() -> None:
    assert slice_limit(requested_count=20) == 60


def test_suffix_swap_isolated_when_triple_within_cap() -> None:
    """agent_estatistico: swap de sufixo com trinca fora do caminho."""
    pool = _build_suffix_isolated_pool(pool_size=100)
    limit = slice_limit(requested_count=20)
    selected, stats = run_mstat_002_swap_engine(pool, limit=limit, game_size=15)
    cap = DOMINANCE_CALIBRATION_THRESHOLD

    assert len(selected) == limit
    assert _count_triple(selected) <= cap
    assert int(stats.get("suffix_swaps", 0) or 0) > 0
    assert int(stats.get("structural_triplet_010203_swaps", 0) or 0) == 0
    assert _max_suffix_share(selected) <= cap
    assert not bool(stats.get("pool_insufficient_non_triplet_reserve"))


def test_triple_swap_isolated_when_suffix_within_cap() -> None:
    """agent_estatistico: swap de trinca com sufixo dentro do teto."""
    pool = _build_triple_isolated_pool(pool_size=200)
    limit = slice_limit(requested_count=20)
    selected, stats = run_mstat_002_swap_engine(pool, limit=limit, game_size=15)
    cap = DOMINANCE_CALIBRATION_THRESHOLD

    assert len(selected) == limit
    assert int(stats.get("structural_triplet_010203_swaps", 0) or 0) > 0
    assert _count_triple(selected) <= cap
    assert _max_suffix_share(selected) <= cap
    assert not bool(stats.get("pool_insufficient_non_triplet_reserve"))


def test_combined_suffix_and_triple_conflict_with_valid_reserve() -> None:
    """Conflito combinado: ambos reduzidos quando há reserva não-trinca útil."""
    pool = _build_combined_conflict_pool(pool_size=200)
    limit = slice_limit(requested_count=20)
    selected, stats = run_mstat_002_swap_engine(pool, limit=limit, game_size=15)
    cap = DOMINANCE_CALIBRATION_THRESHOLD

    assert len(selected) == limit
    assert int(stats.get("structural_swaps", 0) or 0) > 0
    assert _count_triple(selected) <= cap
    assert _max_suffix_share(selected) <= cap
    assert not bool(stats.get("pool_insufficient_non_triplet_reserve"))


def test_all_triple_pool_blocks_suffix_swap_without_failing_suffix_logic() -> None:
    """Reserva 100% trinca: sufixo não troca porque todo candidato viola a trinca."""
    pool = _build_all_triple_contaminated_pool(pool_size=100)
    limit = slice_limit(requested_count=20)
    selected, stats = run_mstat_002_swap_engine(pool, limit=limit, game_size=15)
    cap = DOMINANCE_CALIBRATION_THRESHOLD

    assert len(selected) == limit
    assert _count_triple(selected) == limit
    assert int(stats.get("non_triplet_pool_count", 0) or 0) == 0
    assert int(stats.get("suffix_swaps", 0) or 0) == 0
    assert _max_suffix_share(selected) > cap


def test_insufficient_non_triplet_reserve_escalates_to_agent_geracao() -> None:
    """agent_geracao: reserva não-trinca menor que o necessário para o teto."""
    pool = _build_insufficient_non_triplet_reserve_pool(pool_size=100)
    limit = slice_limit(requested_count=20)
    selected, stats = run_mstat_002_swap_engine(pool, limit=limit, game_size=15)
    cap = DOMINANCE_CALIBRATION_THRESHOLD

    assert len(selected) == limit
    assert int(stats.get("structural_triplet_010203_swaps", 0) or 0) > 0
    assert bool(stats.get("pool_insufficient_non_triplet_reserve"))
    assert stats.get("responsible_agent") == AGENT_GERACAO
    assert stats.get("next_mission_hint") == "M-ML-072"
    assert _count_triple(selected) > cap
    assert int(stats.get("non_triplet_pool_count", 0) or 0) < int(
        stats.get("non_triplet_required_count", 0) or 0
    )


def test_low_diversity_pool_applies_structural_swaps() -> None:
    pool = _build_suffix_isolated_pool(pool_size=100)
    reordered, bundle = apply_diverse_top_slice_pre_gp(
        pool,
        game_size=15,
        requested_count=20,
        batch_label=BATCH_LABEL,
    )
    swap_stats = dict(bundle.get("swap_stats") or {})
    assert bundle["diverse_top_slice_applied"] is True
    assert int(swap_stats.get("structural_swaps", 0) or 0) > 0
    assert int(bundle.get("candidates_replaced", 0) or 0) > 0
    assert len(reordered) == len(pool)


def test_swap_engine_reports_structural_and_overlap_layers() -> None:
    pool = _build_suffix_isolated_pool(pool_size=100)
    limit = slice_limit(requested_count=20)
    selected, stats = run_mstat_002_swap_engine(pool, limit=limit, game_size=15)
    assert len(selected) == limit
    assert int(stats.get("structural_swaps", 0) or 0) > 0
    assert int(stats.get("suffix_cap", 0) or 0) == DOMINANCE_CALIBRATION_THRESHOLD
    assert int(stats.get("max_overlap_permitted", 0) or 0) == 12


def test_criteria_threshold_or_material_gain() -> None:
    criteria = evaluate_top_slice_criteria(diversity_before=0.32, diversity_after=0.55)
    assert criteria["diversity_target_met"] is True
    assert criteria["criteria_met"] is True
    criteria_gain = evaluate_top_slice_criteria(diversity_before=0.30, diversity_after=0.50)
    assert criteria_gain["material_gain_met"] is True
    assert criteria_gain["criteria_met"] is True
    criteria_fail = evaluate_top_slice_criteria(diversity_before=0.34, diversity_after=0.36)
    assert criteria_fail["criteria_met"] is False


def test_build_diverse_top_slice_trace_includes_triplet_reserve_diagnostics() -> None:
    trace = build_diverse_top_slice_trace(
        {
            "diverse_top_slice_applied": True,
            "requested_count": 20,
            "candidate_pool_size": 60,
            "swap_stats": {
                "structural_triplet_010203_count": 10,
                "structural_triplet_010203_cap": 6,
                "structural_triplet_010203_excess": 4,
                "structural_triplet_010203_swaps": 10,
                "pool_insufficient_non_triplet_reserve": True,
                "responsible_agent": AGENT_GERACAO,
                "next_mission_hint": "M-ML-072",
                "non_triplet_pool_count": 10,
                "non_triplet_reserve_count": 0,
            },
            "non_triplet_required_count_gp": 15,
            "non_triplet_ideal_count_gp": 30,
            "metrics_before": {"diversity_score": 0.34},
            "metrics_after": {"diversity_score": 0.57},
            "criteria": {
                "diversity_gain_absolute": 0.23,
                "diversity_target_met": True,
                "material_gain_met": True,
                "criteria_met": True,
            },
            "top_slice_changed": True,
            "candidates_replaced": 18,
        }
    )
    assert trace["structural_triplet_010203_count"] == 10
    assert trace["pool_insufficient_non_triplet_reserve"] is True
    assert trace["responsible_agent"] == AGENT_GERACAO
    assert trace["non_triplet_required_count_gp"] == 15


def test_build_diverse_top_slice_trace() -> None:
    trace = build_diverse_top_slice_trace(
        {
            "diverse_top_slice_applied": True,
            "requested_count": 20,
            "candidate_pool_size": 60,
            "metrics_before": {"diversity_score": 0.34},
            "metrics_after": {"diversity_score": 0.57},
            "criteria": {
                "diversity_gain_absolute": 0.23,
                "diversity_target_met": True,
                "material_gain_met": True,
                "criteria_met": True,
            },
            "top_slice_changed": True,
            "candidates_replaced": 18,
        }
    )
    assert trace["mission_id"] == MISSION_ID
    assert trace["diversity_score_after"] == 0.57
    assert trace["criteria_met"] is True


def test_hierarchy_applies_diverse_top_slice_before_diversity_stage() -> None:
    pool = _build_suffix_isolated_pool(pool_size=100)
    result_pool, bundle, mission_bundles = execute_ml_operational_hierarchy(
        pool,
        game_size=15,
        requested_count=20,
        history=_history(),
        seed=11,
        batch_label=BATCH_LABEL,
    )
    diverse_bundle = dict(mission_bundles.get("diverse_top_slice") or {})
    swap_stats = dict(diverse_bundle.get("swap_stats") or {})
    assert diverse_bundle.get("diverse_top_slice_applied") is True
    assert int(diverse_bundle.get("selected_count", 0) or 0) > 0
    assert int(swap_stats.get("structural_swaps", 0) or 0) > 0
    assert int(diverse_bundle.get("candidates_replaced", 0) or 0) > 0
    assert len(result_pool) == len(pool)


def test_material_gain_constant() -> None:
    assert MIN_MATERIAL_DIVERSITY_GAIN == 0.20
    assert DIVERSITY_LOW_THRESHOLD == 0.55


def test_is_enabled_by_default() -> None:
    assert is_diverse_top_slice_enabled() is True


def test_build_marker_updated() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v76"


def test_agent_estatistico_scope_is_swap_not_pool_generation() -> None:
    _ = AGENT_ESTATISTICO
    pool = _build_insufficient_non_triplet_reserve_pool(pool_size=100)
    _, stats = run_mstat_002_swap_engine(pool, limit=slice_limit(requested_count=20), game_size=15)
    assert int(stats.get("structural_triplet_010203_swaps", 0) or 0) > 0
    assert stats.get("responsible_agent") == AGENT_GERACAO
