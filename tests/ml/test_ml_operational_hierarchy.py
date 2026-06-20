"""Testes de hierarquia operacional ML — limiares adaptativos M-ML-080."""

from __future__ import annotations

from typing import Any

import pytest

from lotoia.ml.ml_operational_hierarchy import (
    QUALITY_TIER_ATENCAO,
    STAGE_CONFORMITY,
    STAGE_COVERAGE,
    STAGE_DIVERSITY,
    _evaluate_conformity_stage,
    _evaluate_diversity_stage,
    _pool_candidate_slice,
    execute_ml_operational_hierarchy,
    resolve_gp_closure_allowed,
    resolve_min_coverage_for_count,
    resolve_min_pool_compliance_rate,
)
from lotoia.ml.agent_operador_ml_executor import GP_ENTREGUE_COM_ALERTA


@pytest.fixture(autouse=True)
def _mock_structural_policy(monkeypatch: pytest.MonkeyPatch) -> None:
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
    monkeypatch.setenv("LOTOIA_ML_PRE_FINAL_POOL_ENABLED", "0")


def _simple_pool(size: int) -> list[dict[str, Any]]:
    games: list[dict[str, Any]] = []
    for index in range(size):
        numbers = sorted({((index + offset * 3) % 25) + 1 for offset in range(15)})
        games.append({"numbers": numbers, "profile_score": float(size - index)})
    return games


@pytest.mark.parametrize("requested_count", [1, 5, 10, 20, 50, 100])
def test_hierarchy_accepts_adaptive_lot_sizes(
    monkeypatch: pytest.MonkeyPatch,
    requested_count: int,
) -> None:
    monkeypatch.setenv("LOTOIA_ML_OPERATIONAL_HIERARCHY_ENABLED", "1")
    monkeypatch.setenv("LOTOIA_ML_STRUCTURAL_15D_POOL_ENABLED", "0")
    pool, bundle, _mission = execute_ml_operational_hierarchy(
        _simple_pool(max(requested_count * 3, 30)),
        game_size=15,
        requested_count=requested_count,
        batch_label="STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
    )
    assert bundle["hierarchy_applied"] is True
    assert STAGE_CONFORMITY in bundle["stage_results"]
    assert STAGE_DIVERSITY in bundle["stage_results"]
    assert len(pool) >= 1


def test_diversity_stage_uses_adaptive_threshold_for_small_lot() -> None:
    pool = _simple_pool(30)
    result = _evaluate_diversity_stage(
        pool,
        game_size=15,
        batch_label=None,
        requested_count=5,
    )
    metrics = dict(result.get("metrics") or {})
    assert metrics.get("diversity_threshold") == pytest.approx(0.35)
    assert metrics.get("near_dup_limit") == pytest.approx(0.60)
    assert metrics.get("requested_count") == 5


def test_conformity_stage_uses_adaptive_compliance_for_small_lot() -> None:
    pool = _simple_pool(12)
    result = _evaluate_conformity_stage(
        pool,
        game_size=16,
        history=None,
        structural_pool_bundle=None,
        batch_label=None,
        requested_count=5,
    )
    metrics = dict(result.get("metrics") or {})
    assert metrics.get("min_compliance_rate") == pytest.approx(0.70)
    assert metrics.get("requested_count") == 5


def test_adaptive_helpers_match_mission_tables() -> None:
    assert resolve_min_coverage_for_count(1) == 18
    assert resolve_min_pool_compliance_rate(1) == 0.70
    assert len(_pool_candidate_slice(_simple_pool(100), requested_count=1)) >= 30


def test_diversity_attention_allows_gp_closure_for_small_lot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GP 10 com diversidade baixa: ATENÇÃO + fechamento permitido."""
    monkeypatch.setenv("LOTOIA_ML_OPERATIONAL_HIERARCHY_ENABLED", "1")
    monkeypatch.setenv("LOTOIA_ML_STRUCTURAL_15D_POOL_ENABLED", "0")
    monkeypatch.setenv("LOTOIA_ML_PRE_FINAL_POOL_ENABLED", "0")

    def _force_diversity_fail(pool, **kwargs: Any) -> dict[str, Any]:
        result = _evaluate_diversity_stage(pool, **kwargs)
        return {
            **result,
            "passed": False,
            "status": "rejected",
            "failures": ["diversity_score=0.3728 abaixo de 0.42"],
            "metrics": {
                **dict(result.get("metrics") or {}),
                "diversity_score": 0.3728,
                "similarity_score": 0.6272,
                "max_overlap": 14,
            },
        }

    def _force_conformity_pass(pool, **kwargs: Any) -> dict[str, Any]:
        result = _evaluate_conformity_stage(pool, **kwargs)
        return {**result, "passed": True, "status": "approved", "failures": []}

    monkeypatch.setattr(
        "lotoia.ml.ml_operational_hierarchy._evaluate_diversity_stage",
        _force_diversity_fail,
    )
    monkeypatch.setattr(
        "lotoia.ml.ml_operational_hierarchy._evaluate_conformity_stage",
        _force_conformity_pass,
    )
    pool, bundle, _mission = execute_ml_operational_hierarchy(
        _simple_pool(50),
        game_size=15,
        requested_count=10,
        batch_label=None,
    )
    assert len(pool) >= 1
    assert dict(bundle["stage_results"].get(STAGE_CONFORMITY) or {}).get("passed") is True
    assert bundle["gp_quality_tier"] == QUALITY_TIER_ATENCAO
    assert bundle["gp_closure_allowed"] is True
    assert bundle["gp_delivery_blocked"] is False
    assert bundle.get("gp_delivery_status") == GP_ENTREGUE_COM_ALERTA


def test_resolve_gp_closure_allowed_blocks_only_conformity_and_critical() -> None:
    diversity_only = {
        STAGE_CONFORMITY: {"passed": True, "failures": []},
        STAGE_DIVERSITY: {"passed": False, "failures": ["diversity_score=0.37 abaixo de 0.42"]},
        STAGE_COVERAGE: {"passed": True, "failures": []},
    }
    allowed, reasons = resolve_gp_closure_allowed(_simple_pool(10), diversity_only)
    assert allowed is True
    assert not reasons

    conformity_fail = {
        STAGE_CONFORMITY: {"passed": False, "failures": ["compliance_rate=0.50 abaixo de 0.70"]},
        STAGE_DIVERSITY: {"passed": True, "failures": []},
    }
    blocked, reasons = resolve_gp_closure_allowed(_simple_pool(10), conformity_fail)
    assert blocked is False
    assert reasons
