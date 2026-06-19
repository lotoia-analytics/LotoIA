"""M-ML-073 — Hierarquia operacional ML (memória decisória soberana)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import patch

import pytest

from dashboard.institutional_build import BUILD_MARKER
from lotoia.governance.lei15_core_002_sovereign import (
    BATCH_LABEL,
    ENV_GENERATION_ENABLED,
)
from lotoia.generator.basic_generator import _attach_scores, _build_game, generate_best_games
from lotoia.ml.ml_operational_hierarchy import (
    HIERARCHY_VERSION,
    MEMORY_KIND,
    MISSION_ID,
    QUALITY_TIER_APROVADO,
    QUALITY_TIER_ATENCAO,
    QUALITY_TIER_REPROVADO,
    STAGE_CONFORMITY,
    STAGE_COVERAGE,
    STAGE_DIVERSITY,
    STAGE_FINAL_VALIDATION,
    STAGE_GP_CLOSURE,
    build_gp_quality_classification,
    build_ml_operational_hierarchy_memory,
    build_ml_operational_hierarchy_trace,
    derive_gp_quality_tier,
    execute_ml_operational_hierarchy,
    finalize_ml_operational_hierarchy_validation,
    MlOperationalHierarchyBlockedError,
)


@dataclass
class _Draw:
    numbers: list[int]


def _history() -> list[_Draw]:
    return [_Draw(sorted(range(1, 16)))] + [
        _Draw(sorted({((offset * 3 + index * 2) % 25) + 1 for index in range(15)}))
        for offset in range(12)
    ]


def _pool(size: int = 30, card_size: int = 15) -> list[dict[str, Any]]:
    games: list[dict[str, Any]] = []
    for index in range(size):
        numbers = sorted({((index + offset * 5) % 25) + 1 for offset in range(card_size)})
        game = _build_game(numbers)
        _attach_scores(game, history=_history(), profile_type="recorrente")
        games.append(game)
    return games


@pytest.fixture(autouse=True)
def _enable_hierarchy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOTOIA_ML_OPERATIONAL_HIERARCHY_ENABLED", "1")
    monkeypatch.setenv("LOTOIA_ML_STRUCTURAL_15D_POOL_ENABLED", "1")
    monkeypatch.setenv("LOTOIA_ML_PRE_FINAL_POOL_ENABLED", "1")
    monkeypatch.setenv("LOTOIA_ML_OUTPUT_CALIBRATION_ENABLED", "1")
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


def test_build_ml_operational_hierarchy_memory_catalog() -> None:
    memory = build_ml_operational_hierarchy_memory()
    assert memory["memory_kind"] == MEMORY_KIND
    assert memory["ml_hierarchy_version"] == HIERARCHY_VERSION
    assert memory["ml_hierarchy_status"] == "active"
    assert "15D" in memory["supported_formats"]
    assert "23D" in memory["supported_formats"]


def test_execute_hierarchy_runs_stages_before_gp_closure() -> None:
    pool, bundle, mission_bundles = execute_ml_operational_hierarchy(
        _pool(35),
        game_size=15,
        requested_count=5,
        history=_history(),
        seed=11,
        batch_label=BATCH_LABEL,
    )
    assert bundle["hierarchy_applied"] is True
    assert STAGE_CONFORMITY in bundle["stage_results"]
    assert STAGE_DIVERSITY in bundle["stage_results"]
    assert STAGE_COVERAGE in bundle["stage_results"]
    assert STAGE_GP_CLOSURE in bundle["stage_results"]
    assert len(pool) >= 5
    assert mission_bundles.get("structural_pool") is not None
    if not bundle["gp_closure_allowed"]:
        assert bundle["stage_failures"]


def test_finalize_hierarchy_stage_five_verdict() -> None:
    hierarchy = {
        "gp_closure_allowed": True,
        "stage_results": {
            STAGE_GP_CLOSURE: {"passed": True},
        },
    }
    finalized = finalize_ml_operational_hierarchy_validation(
        hierarchy,
        final_gp=_pool(5)[:5],
        structural_policy_bundle={"structural_policy_applied": True},
        pre_final_bundle={"pre_final_calibration_applied": True},
        structural_pool_bundle={"structural_pool_applied": True},
    )
    assert STAGE_FINAL_VALIDATION in finalized["stage_results"]
    assert finalized["subordinate_missions_status"]["M-ML-070"] is True
    assert finalized["subordinate_missions_status"]["M-ML-071"] is True
    assert finalized["subordinate_missions_status"]["M-ML-072"] is True


def test_build_hierarchy_trace_safe() -> None:
    trace = build_ml_operational_hierarchy_trace(
        {
            "hierarchy_applied": True,
            "stage_results": {
                STAGE_CONFORMITY: {
                    "stage_id": STAGE_CONFORMITY,
                    "stage_label": "Etapa 1: Conformidade",
                    "status": "approved",
                    "passed": True,
                    "metrics": {"compliance_rate": 0.95},
                    "failures": [],
                }
            },
            "operational_hierarchy_memory": {"raw_pool": [{"numbers": list(range(1, 16))}]},
        }
    )
    assert "operational_hierarchy_memory" not in trace
    assert trace["stage_results"][STAGE_CONFORMITY]["passed"] is True


def _failed_hierarchy_bundle() -> dict[str, Any]:
    return {
        "hierarchy_applied": True,
        "gp_closure_allowed": False,
        "blocking_reason": "diversity_score abaixo do limite",
        "current_stage": STAGE_DIVERSITY,
        "stage_results": {
            STAGE_DIVERSITY: {"passed": False, "status": "rejected"},
            STAGE_COVERAGE: {"passed": True, "status": "approved"},
        },
        "stage_failures": ["diversity_score abaixo do limite"],
    }


def test_generate_best_games_uses_hierarchy_orchestrator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOTOIA_LEI15_CORE_002", "sovereign")
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "1")
    monkeypatch.setenv("LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1", "off")

    hierarchy_calls: list[int] = []

    def _mock_recovery(games, **kwargs):
        hierarchy_calls.append(len(games))
        return (
            list(games),
            {
                "mission_id": MISSION_ID,
                "hierarchy_applied": True,
                "gp_closure_allowed": True,
                "hierarchy_compliance": True,
                "current_stage": STAGE_GP_CLOSURE,
                "stage_results": {
                    STAGE_CONFORMITY: {"passed": True, "status": "approved"},
                    STAGE_DIVERSITY: {"passed": True, "status": "approved"},
                    STAGE_COVERAGE: {"passed": True, "status": "approved"},
                    STAGE_GP_CLOSURE: {"passed": True, "status": "approved"},
                },
                "stage_failures": [],
            },
            {
                "structural_pool": {"structural_pool_applied": True, "pool_origin": "ML_STRUCTURAL_15D_POOL"},
                "pre_final": {"pre_final_calibration_applied": True},
            },
            {
                "internal_recovery_attempted": True,
                "internal_recovery_attempts": 1,
                "internal_recovery_success": True,
                "final_gp_delivered": True,
            },
        )

    def _mock_pool(pool_size_arg, *, seed, history, config):
        rows = []
        for index in range(pool_size_arg):
            numbers = sorted({((index + offset * 7) % 25) + 1 for offset in range(15)})
            game = _build_game(numbers)
            _attach_scores(game, history=history, profile_type="recorrente")
            rows.append(game)
        return rows

    def _mock_compose(pool, count_arg, cfg, *, game_size=15):
        return list(pool[:count_arg])

    with patch("lotoia.generation.lei15_core_002.build_sovereign_pool", side_effect=_mock_pool):
        with patch(
            "lotoia.ml.pre_gp_deterministic_recovery.execute_pre_gp_recovery_cycle",
            side_effect=_mock_recovery,
        ):
            with patch(
                "lotoia.generation.lei15_core_002.compose_sovereign_gp",
                side_effect=_mock_compose,
            ):
                with patch(
                    "lotoia.ml.structural_policy_15d.apply_structural_policy_15d_to_sovereign_batch",
                    side_effect=lambda selected, **kwargs: (selected, {"structural_policy_applied": False}),
                ):
                    result = generate_best_games(
                        count=5,
                        pool_size=40,
                        ml_enabled=True,
                        batch_label=BATCH_LABEL,
                    )

    assert result["count"] == 5
    hierarchy = dict(result.get("ml_operational_hierarchy") or {})
    assert hierarchy.get("hierarchy_applied") is True
    assert hierarchy_calls == [40]


def test_derive_gp_quality_tier_mapping() -> None:
    approved = {
        STAGE_CONFORMITY: {"passed": True},
        STAGE_DIVERSITY: {"passed": True},
        STAGE_COVERAGE: {"passed": True},
    }
    assert derive_gp_quality_tier(approved) == QUALITY_TIER_APROVADO

    attention = {
        STAGE_CONFORMITY: {"passed": True},
        STAGE_DIVERSITY: {"passed": False},
        STAGE_COVERAGE: {"passed": True},
    }
    assert derive_gp_quality_tier(attention) == QUALITY_TIER_ATENCAO

    reproved = {
        STAGE_CONFORMITY: {"passed": False, "failures": ["compliance baixo"]},
        STAGE_DIVERSITY: {"passed": False},
        STAGE_COVERAGE: {"passed": True},
    }
    assert derive_gp_quality_tier(reproved) == QUALITY_TIER_REPROVADO


def test_build_gp_quality_classification_preserves_metrics() -> None:
    stage_results = {
        STAGE_DIVERSITY: {
            "passed": False,
            "metrics": {"diversity_score": 0.36, "similarity_score": 9.47, "max_overlap": 12},
        }
    }
    quality = build_gp_quality_classification(
        stage_results,
        stage_failures=["diversity_score=0.36 abaixo de 0.55"],
    )
    assert quality["gp_quality_tier"] == QUALITY_TIER_ATENCAO
    assert quality["diversity_score"] == 0.36
    assert quality["similarity_score"] == 9.47


def test_hierarchy_delivers_with_quality_warning_when_diversity_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOTOIA_LEI15_CORE_002", "sovereign")
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "1")
    monkeypatch.setenv("LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1", "off")
    monkeypatch.setenv("LOTOIA_ML_PRE_GP_RECOVERY_ATTEMPTS", "1")

    def _mock_recovery(games, **kwargs):
        bundle = _failed_hierarchy_bundle()
        bundle["gp_delivery_blocked"] = False
        bundle["gp_quality_tier"] = QUALITY_TIER_REPROVADO
        bundle["gp_quality_reasons"] = ["diversity_score abaixo do limite"]
        bundle["pre_gp_recovery"] = {
            "internal_recovery_attempted": True,
            "internal_recovery_attempts": 1,
            "internal_recovery_success": False,
            "recovery_exhausted": True,
            "final_gp_delivered": True,
        }
        return list(games), bundle, {}, dict(bundle["pre_gp_recovery"])

    def _mock_pool(pool_size_arg, *, seed, history, config):
        return _pool(pool_size_arg)

    def _mock_compose(pool, count_arg, cfg, *, game_size=15):
        return list(pool[:count_arg])

    with patch("lotoia.generation.lei15_core_002.build_sovereign_pool", side_effect=_mock_pool):
        with patch(
            "lotoia.ml.pre_gp_deterministic_recovery.execute_pre_gp_recovery_cycle",
            side_effect=_mock_recovery,
        ):
            with patch(
                "lotoia.generation.lei15_core_002.compose_sovereign_gp",
                side_effect=_mock_compose,
            ):
                with patch(
                    "lotoia.ml.structural_policy_15d.apply_structural_policy_15d_to_sovereign_batch",
                    side_effect=lambda selected, **kwargs: (selected, {"structural_policy_applied": False}),
                ):
                    result = generate_best_games(count=5, pool_size=40, ml_enabled=True, batch_label=BATCH_LABEL)

    assert result["count"] == 5
    assert result.get("gp_quality_tier") == QUALITY_TIER_REPROVADO
    hierarchy = dict(result.get("ml_operational_hierarchy") or {})
    assert hierarchy.get("gp_closure_allowed") is False
    assert hierarchy.get("gp_delivery_blocked") is not True


def test_hierarchy_blocks_only_on_critical_delivery_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOTOIA_LEI15_CORE_002", "sovereign")
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "1")
    monkeypatch.setenv("LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1", "off")
    monkeypatch.setenv("LOTOIA_ML_PRE_GP_RECOVERY_ATTEMPTS", "1")

    def _mock_recovery(games, **kwargs):
        bundle = _failed_hierarchy_bundle()
        bundle["gp_delivery_blocked"] = True
        bundle["gp_delivery_block_reasons"] = ["pool_vazio"]
        bundle["pre_gp_recovery"] = {
            "internal_recovery_attempted": True,
            "internal_recovery_attempts": 1,
            "internal_recovery_success": False,
            "recovery_exhausted": True,
        }
        return list(games), bundle, {}, dict(bundle["pre_gp_recovery"])

    def _mock_pool(pool_size_arg, *, seed, history, config):
        return _pool(pool_size_arg)

    with patch("lotoia.generation.lei15_core_002.build_sovereign_pool", side_effect=_mock_pool):
        with patch(
            "lotoia.ml.pre_gp_deterministic_recovery.execute_pre_gp_recovery_cycle",
            side_effect=_mock_recovery,
        ):
            with pytest.raises(MlOperationalHierarchyBlockedError, match="falha crítica"):
                generate_best_games(count=5, pool_size=40, ml_enabled=True, batch_label=BATCH_LABEL)


def test_build_marker_updated() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v74"
    assert MISSION_ID == "M-ML-073"
    assert HIERARCHY_VERSION == "M-ML-073-v2"
