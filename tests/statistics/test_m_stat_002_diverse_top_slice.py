"""M-STAT-002 — seleção estatística diversa do top slice pré-GP."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any
from unittest.mock import patch

import pytest

from dashboard.institutional_build import BUILD_MARKER
from lotoia.governance.institutional_agent_routing_matrix import AGENT_ESTATISTICO
from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL
from lotoia.ml.ml_operational_hierarchy import (
    STAGE_DIVERSITY,
    execute_ml_operational_hierarchy,
)
from lotoia.ml.overlap_format_thresholds import DIVERSITY_LOW_THRESHOLD
from lotoia.ml.supervised_output_calibration import DOMINANCE_CALIBRATION_THRESHOLD
from lotoia.statistics.diverse_top_slice_selection import (
    MISSION_ID,
    MIN_MATERIAL_DIVERSITY_GAIN,
    apply_diverse_top_slice_pre_gp,
    build_diverse_top_slice_trace,
    evaluate_top_slice_criteria,
    is_diverse_top_slice_enabled,
    run_mstat_002_swap_engine,
    select_diverse_pre_gp_top_slice,
    slice_limit,
)
from lotoia.generator.basic_generator import _attach_scores, _build_game


def _unique_cards_with_fixed_numbers(
    count: int,
    *,
    fixed: tuple[int, ...],
    exclude: frozenset[int] | None = None,
) -> list[list[int]]:
    """Gera cartões 15D únicos contendo os números fixos (ex.: sufixo dominante)."""
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


def _unique_diverse_cards(count: int) -> list[list[int]]:
    """Cartões 15D estruturalmente distintos (evita clusters com overlap 14)."""
    cards: list[list[int]] = []
    for index, combo in enumerate(combinations(range(1, 26), 15)):
        if index % 11 != 0:
            continue
        cards.append(list(combo))
        if len(cards) >= count:
            break
    return cards


def _build_mixed_score_dominant_pool(*, pool_size: int = 100, requested_count: int = 20) -> list[dict[str, Any]]:
    """Pool com top score dominado por sufixo e cauda estruturalmente diversa (cartões únicos)."""
    dominant_suffix = (20, 21, 22, 23, 24)
    dominant_count = max(40, pool_size // 2)
    diverse_count = pool_size - dominant_count
    dominant_cards = _unique_cards_with_fixed_numbers(
        dominant_count,
        fixed=dominant_suffix,
    )
    diverse_cards = _unique_diverse_cards(diverse_count)
    pool: list[dict[str, Any]] = []
    for index, numbers in enumerate(dominant_cards):
        game = _build_game(numbers)
        game["profile_score"] = 1000 - index
        _attach_scores(game, profile_type="recorrente")
        pool.append(game)
    for index, numbers in enumerate(diverse_cards):
        game = _build_game(numbers)
        game["profile_score"] = 300 - index
        _attach_scores(game, profile_type="recorrente")
        pool.append(game)
    pool.sort(key=lambda row: float(row.get("profile_score", 0.0) or 0.0), reverse=True)
    _ = requested_count
    return pool


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


def test_low_diversity_pool_improves_with_diverse_selection() -> None:
    pool = _build_mixed_score_dominant_pool(pool_size=100, requested_count=20)
    reordered, bundle = apply_diverse_top_slice_pre_gp(
        pool,
        game_size=15,
        requested_count=20,
        batch_label=BATCH_LABEL,
    )
    assert bundle["diverse_top_slice_applied"] is True
    before = float(bundle["metrics_before"]["diversity_score"])
    after = float(bundle["metrics_after"]["diversity_score"])
    assert after > before
    assert bundle["criteria"]["diversity_gain_absolute"] > 0
    assert bundle["selected_count"] > 0
    assert len(reordered) == len(pool)


def test_dominant_family_capped_in_top_slice() -> None:
    pool = _build_mixed_score_dominant_pool(pool_size=100, requested_count=20)
    limit = slice_limit(requested_count=20)
    selected = select_diverse_pre_gp_top_slice(
        pool,
        limit=limit,
        game_size=15,
        requested_count=20,
        batch_label=BATCH_LABEL,
    )
    suffix_counts: dict[str, int] = {}
    for game in selected:
        from lotoia.statistics.diverse_top_slice_selection import _suffix_key

        suffix = _suffix_key(game)
        suffix_counts[suffix] = suffix_counts.get(suffix, 0) + 1
    suffix_cap = DOMINANCE_CALIBRATION_THRESHOLD
    assert len(selected) == limit
    assert selected
    assert max(suffix_counts.values()) <= suffix_cap


def test_swap_engine_reports_structural_and_overlap_layers() -> None:
    pool = _build_mixed_score_dominant_pool(pool_size=100, requested_count=20)
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
    pool = _build_mixed_score_dominant_pool(pool_size=100, requested_count=20)
    result_pool, bundle, mission_bundles = execute_ml_operational_hierarchy(
        pool,
        game_size=15,
        requested_count=20,
        history=_history(),
        seed=11,
        batch_label=BATCH_LABEL,
    )
    diverse_bundle = dict(mission_bundles.get("diverse_top_slice") or {})
    assert diverse_bundle.get("diverse_top_slice_applied") is True
    assert int(diverse_bundle.get("selected_count", 0) or 0) > 0
    assert float(
        dict(diverse_bundle.get("criteria") or {}).get("diversity_gain_absolute", 0.0) or 0.0
    ) >= 0.0
    diversity_stage = dict(bundle.get("stage_results", {}).get(STAGE_DIVERSITY) or {})
    if diversity_stage:
        metrics = dict(diversity_stage.get("metrics") or {})
        assert float(metrics.get("diversity_score", 0.0) or 0.0) >= float(
            diverse_bundle.get("metrics_before", {}).get("diversity_score", 0.0) or 0.0
        )
    assert len(result_pool) == len(pool)


def test_material_gain_constant() -> None:
    assert MIN_MATERIAL_DIVERSITY_GAIN == 0.20
    assert DIVERSITY_LOW_THRESHOLD == 0.55


def test_is_enabled_by_default() -> None:
    assert is_diverse_top_slice_enabled() is True


def test_build_marker_updated() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v67"
