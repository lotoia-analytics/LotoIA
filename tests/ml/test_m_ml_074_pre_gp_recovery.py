"""M-ML-074 — recuperação determinística pré-GP."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import patch

import pytest

from dashboard.institutional_build import BUILD_MARKER
from dashboard.institutional_ml_hierarchy_block import (
    build_central_ml_recovery_success_notice,
    build_hierarchy_blocked_generation_result,
)
from lotoia.governance.institutional_agent_routing_matrix import AGENT_ESTATISTICO
from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL, ENV_GENERATION_ENABLED
from lotoia.generator.basic_generator import _attach_scores, _build_game, generate_best_games
from lotoia.ml.ml_operational_hierarchy import (
    QUALITY_TIER_APROVADO,
    QUALITY_TIER_REPROVADO,
    STAGE_COVERAGE,
    STAGE_DIVERSITY,
    STAGE_GP_CLOSURE,
    MlOperationalHierarchyBlockedError,
)
from lotoia.ml.pre_gp_deterministic_recovery import (
    DEFAULT_MAX_RECOVERY_ATTEMPTS,
    MISSION_ID,
    apply_deterministic_recovery_action,
    build_pre_gp_recovery_trace,
    execute_pre_gp_recovery_cycle,
    get_max_recovery_attempts,
    is_pre_gp_recovery_enabled,
)
from lotoia.statistics.diversity_remediation_audit import build_low_diversity_audit_pool


@dataclass
class _Draw:
    numbers: list[int]


def _history() -> list[_Draw]:
    return [_Draw(sorted(range(1, 16)))] + [
        _Draw(sorted({((offset * 3 + index * 2) % 25) + 1 for index in range(15)}))
        for offset in range(12)
    ]


def _pool(size: int = 100) -> list[dict[str, Any]]:
    games: list[dict[str, Any]] = []
    for index in range(size):
        numbers = sorted({((index + offset * 5) % 25) + 1 for offset in range(15)})
        game = _build_game(numbers)
        _attach_scores(game, history=_history(), profile_type="recorrente")
        games.append(game)
    return games


def _failed_hierarchy_bundle(*, stage: str = STAGE_DIVERSITY) -> dict[str, Any]:
    return {
        "hierarchy_applied": True,
        "gp_closure_allowed": False,
        "gp_delivery_blocked": False,
        "gp_quality_tier": QUALITY_TIER_REPROVADO,
        "gp_quality_reasons": ["diversity_score abaixo do limite"],
        "blocking_reason": "diversity_score abaixo do limite",
        "current_stage": stage,
        "stage_results": {
            STAGE_DIVERSITY: {
                "passed": stage != STAGE_DIVERSITY,
                "status": "rejected" if stage == STAGE_DIVERSITY else "approved",
                "stage_id": STAGE_DIVERSITY,
                "metrics": {"diversity_score": 0.34},
                "failures": ["diversity_score=0.34 abaixo de 0.55"],
            },
            STAGE_COVERAGE: {
                "passed": stage != STAGE_COVERAGE,
                "status": "rejected" if stage == STAGE_COVERAGE else "approved",
                "stage_id": STAGE_COVERAGE,
                "metrics": {},
                "failures": ["cobertura"] if stage == STAGE_COVERAGE else [],
            },
        },
        "stage_failures": ["diversity_score=0.34 abaixo de 0.55"],
    }


def _passed_hierarchy_bundle() -> dict[str, Any]:
    return {
        "hierarchy_applied": True,
        "gp_closure_allowed": True,
        "gp_delivery_blocked": False,
        "gp_quality_tier": QUALITY_TIER_APROVADO,
        "hierarchy_compliance": True,
        "current_stage": STAGE_GP_CLOSURE,
        "stage_results": {
            STAGE_DIVERSITY: {"passed": True, "status": "approved", "metrics": {"diversity_score": 0.62}},
            STAGE_COVERAGE: {"passed": True, "status": "approved", "metrics": {}},
        },
        "stage_failures": [],
    }


@pytest.fixture(autouse=True)
def _enable_ml_stack(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOTOIA_ML_OPERATIONAL_HIERARCHY_ENABLED", "1")
    monkeypatch.setenv("LOTOIA_ML_PRE_GP_RECOVERY_ENABLED", "1")
    monkeypatch.setenv("LOTOIA_ML_STRUCTURAL_15D_POOL_ENABLED", "1")
    monkeypatch.setenv("LOTOIA_ML_PRE_FINAL_POOL_ENABLED", "1")
    monkeypatch.setenv("LOTOIA_ML_PRE_GP_RECOVERY_ATTEMPTS", "5")
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


def test_get_max_recovery_attempts_default_and_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOTOIA_ML_PRE_GP_RECOVERY_ATTEMPTS", raising=False)
    assert get_max_recovery_attempts() == DEFAULT_MAX_RECOVERY_ATTEMPTS == 5
    monkeypatch.setenv("LOTOIA_ML_PRE_GP_RECOVERY_ATTEMPTS", "3")
    assert get_max_recovery_attempts() == 3


def test_recovery_first_fail_second_pass() -> None:
    calls = {"n": 0}

    def _mock_hierarchy(games, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return list(games), _failed_hierarchy_bundle(), {"structural_pool": {}, "pre_final": {}}
        return list(games), _passed_hierarchy_bundle(), {"structural_pool": {}, "pre_final": {}}

    with patch(
        "lotoia.ml.pre_gp_deterministic_recovery.execute_ml_operational_hierarchy",
        side_effect=_mock_hierarchy,
    ):
        pool, bundle, missions, recovery = execute_pre_gp_recovery_cycle(
            _pool(80),
            game_size=15,
            requested_count=20,
            history=_history(),
            seed=42,
            batch_label=BATCH_LABEL,
        )

    assert recovery["internal_recovery_success"] is True
    assert recovery["final_gp_delivered"] is True
    assert recovery["internal_recovery_attempts"] == 2
    assert recovery["successful_attempt_index"] == 2
    assert bundle["gp_closure_allowed"] is True
    assert calls["n"] == 2


def test_recovery_all_attempts_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOTOIA_ML_PRE_GP_RECOVERY_ATTEMPTS", "3")

    def _mock_hierarchy(games, **kwargs):
        return list(games), _failed_hierarchy_bundle(), {"structural_pool": {}, "pre_final": {}}

    with patch(
        "lotoia.ml.pre_gp_deterministic_recovery.execute_ml_operational_hierarchy",
        side_effect=_mock_hierarchy,
    ):
        pool, bundle, missions, recovery = execute_pre_gp_recovery_cycle(
            _pool(80),
            game_size=15,
            requested_count=20,
            history=_history(),
            seed=7,
            batch_label=BATCH_LABEL,
        )

    assert recovery["internal_recovery_success"] is False
    assert recovery["final_gp_delivered"] is True
    assert recovery["internal_recovery_attempts"] == 3
    assert recovery["recovery_exhausted"] is True
    assert bundle["gp_closure_allowed"] is False
    assert bundle.get("pre_gp_recovery", {}).get("best_attempt_selected") is not None


def test_material_substitution_not_only_rerank() -> None:
    pool = build_low_diversity_audit_pool(pool_size=100, requested_count=20)
    before_top = {
        tuple(sorted(game.get("numbers") or []))
        for game in pool[:60]
    }
    updated, actions = apply_deterministic_recovery_action(
        pool,
        failed_stage=STAGE_DIVERSITY,
        attempt_index=2,
        game_size=15,
        requested_count=20,
        history=_history(),
        seed=99,
        batch_label=BATCH_LABEL,
    )
    assert "substituicao_material_top_slice" in actions or "anti_clone_forte" in actions
    promoted = sum(1 for game in updated if game.get("pre_gp_recovery_promoted"))
    assert promoted >= 0
    after_ranked = sorted(
        updated,
        key=lambda row: float(row.get("profile_score", 0.0) or 0.0),
        reverse=True,
    )[:60]
    after_top = {tuple(sorted(game.get("numbers") or [])) for game in after_ranked}
    assert before_top != after_top or promoted > 0


def test_diversity_improves_between_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOTOIA_ML_PRE_GP_RECOVERY_ATTEMPTS", "2")
    calls = {"n": 0}

    def _mock_hierarchy(games, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return list(games), _failed_hierarchy_bundle(), {}
        return list(games), _passed_hierarchy_bundle(), {}

    with patch(
        "lotoia.ml.pre_gp_deterministic_recovery.execute_ml_operational_hierarchy",
        side_effect=_mock_hierarchy,
    ):
        _, _, _, recovery = execute_pre_gp_recovery_cycle(
            _pool(80),
            game_size=15,
            requested_count=20,
            history=_history(),
            seed=1,
            batch_label=BATCH_LABEL,
        )

    assert recovery["internal_recovery_attempts"] == 2
    assert recovery["attempt_results"][0]["recovery_actions"]
    assert recovery["internal_recovery_success"] is True


def test_build_pre_gp_recovery_trace_fields() -> None:
    trace = build_pre_gp_recovery_trace(
        {
            "internal_recovery_attempted": True,
            "internal_recovery_attempts": 2,
            "internal_recovery_success": True,
            "final_gp_delivered": True,
            "best_attempt_metrics": {"diversity_score": 0.61},
            "attempt_results": [{"attempt_index": 1, "gp_closure_allowed": False}],
            "successful_attempt_index": 2,
        }
    )
    assert trace["mission_id"] == MISSION_ID
    assert trace["internal_recovery_attempts"] == 2
    assert trace["final_gp_delivered"] is True
    assert trace["best_attempt_metrics"]["diversity_score"] == 0.61


def test_responsible_agent_preserved_on_recovery_bundle() -> None:
    failed = _failed_hierarchy_bundle()
    failed["stage_results"][STAGE_DIVERSITY]["responsible_agent"] = AGENT_ESTATISTICO

    def _mock_hierarchy(games, **kwargs):
        return list(games), dict(failed), {}

    with patch(
        "lotoia.ml.pre_gp_deterministic_recovery.execute_ml_operational_hierarchy",
        side_effect=_mock_hierarchy,
    ):
        _, bundle, _, _ = execute_pre_gp_recovery_cycle(
            _pool(60),
            game_size=15,
            requested_count=20,
            history=_history(),
            seed=3,
            batch_label=BATCH_LABEL,
        )

    stage = dict(bundle.get("stage_results", {}).get(STAGE_DIVERSITY) or {})
    assert stage.get("responsible_agent") == AGENT_ESTATISTICO


def test_central_ml_recovery_success_notice() -> None:
    notice = build_central_ml_recovery_success_notice(
        {
            "internal_recovery_success": True,
            "internal_recovery_attempts": 3,
            "successful_attempt_index": 3,
            "final_gp_delivered": True,
        }
    )
    assert notice.get("available") is True
    assert "3 tentativa" in notice.get("message", "")


def test_hierarchy_block_only_after_exhaustion_payload() -> None:
    bundle = _failed_hierarchy_bundle()
    bundle["pre_gp_recovery"] = build_pre_gp_recovery_trace(
        {
            "internal_recovery_attempted": True,
            "internal_recovery_attempts": 5,
            "internal_recovery_success": False,
            "recovery_exhausted": True,
            "best_attempt_metrics": {"diversity_score": 0.44},
        }
    )
    result = build_hierarchy_blocked_generation_result(
        hierarchy_bundle=bundle,
        exception_message=MlOperationalHierarchyBlockedError.from_bundle(bundle),
        requested_count=20,
        seed=1,
        analysis_batch_label=BATCH_LABEL,
        ml_enabled=True,
    )
    assert result["hierarchy_blocked"] is True
    assert result["internal_recovery_attempts"] == 5
    assert result["final_gp_delivered"] is False
    assert result["best_attempt_metrics"]["diversity_score"] == 0.44


def test_generate_best_games_uses_recovery_cycle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOTOIA_LEI15_CORE_002", "sovereign")
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "1")
    monkeypatch.setenv("LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1", "off")
    recovery_calls: list[int] = []

    def _mock_recovery(games, **kwargs):
        recovery_calls.append(len(games))
        return (
            list(games),
            _passed_hierarchy_bundle(),
            {"structural_pool": {"structural_pool_applied": True}, "pre_final": {}},
            {
                "internal_recovery_attempted": True,
                "internal_recovery_attempts": 2,
                "internal_recovery_success": True,
                "final_gp_delivered": True,
                "attempt_results": [],
                "best_attempt_metrics": {},
            },
        )

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
                    result = generate_best_games(
                        count=20,
                        pool_size=100,
                        ml_enabled=True,
                        batch_label=BATCH_LABEL,
                    )

    assert result["count"] == 20
    assert result["final_gp_delivered"] is True
    assert recovery_calls


def test_delivers_with_quality_warning_after_recovery_exhaustion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOTOIA_LEI15_CORE_002", "sovereign")
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "1")
    monkeypatch.setenv("LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1", "off")
    monkeypatch.setenv("LOTOIA_ML_PRE_GP_RECOVERY_ATTEMPTS", "2")

    def _mock_recovery(games, **kwargs):
        bundle = _failed_hierarchy_bundle()
        bundle["pre_gp_recovery"] = {
            "internal_recovery_attempted": True,
            "internal_recovery_attempts": 2,
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
                    result = generate_best_games(
                        count=20, pool_size=100, ml_enabled=True, batch_label=BATCH_LABEL
                    )

    assert result["count"] == 20
    assert result.get("gp_quality_tier") == QUALITY_TIER_REPROVADO


def test_build_marker_updated() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v91"
