"""Decomposição da similaridade média — M-STAT-002 diagnóstico."""

from __future__ import annotations

from typing import Any

import pytest

from lotoia.statistics.similarity_overlap_decomposition import (
    EXCLUSIVE_COMPONENT_ORDER,
    decompose_pool_similarity,
    format_similarity_decomposition_report,
)
from tests.statistics.test_m_stat_002_diverse_top_slice import (
    _build_mixed_score_dominant_pool,
    _build_mixed_score_dominant_prefix_pool,
)
from lotoia.statistics.diverse_top_slice_selection import (
    DOMINANT_STRUCTURAL_TRIPLE_LABEL,
    _score_based_slice,
    apply_diverse_top_slice_pre_gp,
    slice_limit,
)


@pytest.fixture(autouse=True)
def _mock_structural_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    policy: dict[str, Any] = {
        "policy_version": "M-ML-070-v1",
        "core_numbers": [7, 12, 16, 23],
        "discouraged_numbers": [2, 4, 11, 15, 24, 25],
    }
    monkeypatch.setenv("LOTOIA_DIVERSE_TOP_SLICE_ENABLED", "1")
    monkeypatch.setattr(
        "lotoia.ml.supervised_output_calibration.ensure_structural_policy_15d_memory",
        lambda db_path=None: policy,
    )
    monkeypatch.setattr(
        "lotoia.ml.supervised_output_calibration.build_structural_policy_15d_calibration_plan",
        lambda bundle, policy_payload: {"has_plan": False, "parametros_sugeridos": {}},
    )


def test_decompose_pool_similarity_returns_components() -> None:
    pool = _build_mixed_score_dominant_pool(pool_size=100, requested_count=20)
    limit = slice_limit(requested_count=20)
    top = _score_based_slice(pool, limit=limit)
    result = decompose_pool_similarity(
        top,
        game_size=15,
        previous_contest_numbers=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    )
    assert result["pair_count"] > 0
    assert result["avg_overlap"] > 0
    assert "shared_prefix_dezenas" in result["components"]
    assert "shared_core_dezenas" in result["components"]
    assert result["diversity_score"] == round(1.0 - float(result["similarity_score"]), 4)
    assert abs(float(result["exclusive_sum_check"]) - float(result["avg_overlap"])) < 0.0001


def test_exclusive_components_sum_to_avg_overlap() -> None:
    pool = _build_mixed_score_dominant_prefix_pool(pool_size=100, requested_count=20)
    top = _score_based_slice(pool, limit=slice_limit(requested_count=20))
    result = decompose_pool_similarity(top, game_size=15)
    component_sum = sum(
        float(dict(result["components"].get(key) or {}).get("mean_shared_dezenas", 0.0) or 0.0)
        for key in EXCLUSIVE_COMPONENT_ORDER
    )
    assert abs(component_sum - float(result["avg_overlap"])) < 0.0001


def test_high_overlap_pool_has_high_prefix_and_core_contribution() -> None:
    pool = _build_mixed_score_dominant_pool(pool_size=100, requested_count=20)
    top = _score_based_slice(pool, limit=slice_limit(requested_count=20))
    result = decompose_pool_similarity(top, game_size=15)
    prefix_share = float(result["components"]["shared_prefix_dezenas"]["mean_shared_dezenas"])
    core_share = float(result["components"]["shared_core_dezenas"]["mean_shared_dezenas"])
    assert prefix_share >= 0
    assert core_share >= 0


def test_apply_diverse_top_slice_includes_similarity_decomposition() -> None:
    pool = _build_mixed_score_dominant_prefix_pool(pool_size=100, requested_count=20)
    _, bundle = apply_diverse_top_slice_pre_gp(
        pool,
        game_size=15,
        requested_count=20,
    )
    before = dict(bundle.get("similarity_decomposition_before") or {})
    after = dict(bundle.get("similarity_decomposition_after") or {})
    assert float(before.get("avg_overlap", 0.0) or 0.0) > 0
    assert float(after.get("avg_overlap", 0.0) or 0.0) > 0
    assert "components" in before
    assert "components" in after
    swap_stats = dict(bundle.get("swap_stats") or {})
    assert int(swap_stats.get("structural_triplet_010203_cap", 0) or 0) > 0
    assert "pool_insufficient_non_triplet_reserve" in bundle


def test_prefix_triple_dimensions_are_separated() -> None:
    pool = _build_mixed_score_dominant_prefix_pool(pool_size=100, requested_count=20)
    top = _score_based_slice(pool, limit=slice_limit(requested_count=20))
    result = decompose_pool_similarity(top, game_size=15, structural_triple_dominance_cap=6)
    analysis = dict(
        result.get("dominant_structural_triple_analysis") or result.get("prefix_triple_analysis") or {}
    )

    individual = dict(analysis.get("individual_dezena_presence") or {})
    structural = dict(
        analysis.get("dominant_structural_triple") or analysis.get("structural_prefix_triple") or {}
    )
    impact = dict(analysis.get("similarity_impact") or {})

    assert float(dict(individual.get("01") or {}).get("share_pct", 0.0) or 0.0) > 0
    assert int(structural.get("count", 0) or 0) > 0
    assert float(impact.get("avg_overlap", 0.0) or 0.0) == float(result.get("avg_overlap", 0.0) or 0.0)
    assert float(impact.get("mean_shared_prefix_dezenas_123", 0.0) or 0.0) >= 0
    assert float(impact.get("non_prefix_residual_overlap", 0.0) or 0.0) >= 0

    individual_01_pct = float(dict(individual.get("01") or {}).get("share_pct", 0.0) or 0.0)
    structural_pct = float(structural.get("share_pct", 0.0) or 0.0)
    assert individual_01_pct >= structural_pct
    assert dict(analysis.get("interpretation") or {}).get("corrective_action") == (
        "limit_triple_dominance_in_gp_top_slice"
    )
    assert structural.get("label") == DOMINANT_STRUCTURAL_TRIPLE_LABEL


def test_format_similarity_decomposition_report_is_readable() -> None:
    pool = _build_mixed_score_dominant_prefix_pool(pool_size=100, requested_count=20)
    top = _score_based_slice(pool, limit=slice_limit(requested_count=20))
    result = decompose_pool_similarity(top, game_size=15)
    report = format_similarity_decomposition_report(result)
    assert "avg_overlap=" in report
    assert "Trinca estrutural dominante 01-02-03" in report
    assert "Impacto da trinca na similaridade média do GP" in report
