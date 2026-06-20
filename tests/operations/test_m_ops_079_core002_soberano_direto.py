"""M-OPS-079 — CORE_002 soberano direto; ML opt-in."""

from __future__ import annotations

from typing import Any

import pytest

from dashboard.institutional_supervised_ml import (
    ENV_ML_OPERATIONAL_ENABLED,
    is_ml_operational_enabled,
)
from lotoia.generator.basic_generator import generate_best_games
from lotoia.governance.lei15_core_002_sovereign import (
    ENV_GENERATION_ENABLED,
    resolve_core_002_batch_label,
)
from lotoia.ml.agent_operador_ml_executor import (
    ENV_AGENT_ENABLED,
    is_agent_operador_ml_enabled,
)
from lotoia.ml.ml_operational_hierarchy import (
    ENV_HIERARCHY_ENABLED,
    is_ml_operational_hierarchy_enabled,
)
from lotoia.ml.pre_final_pool_ml_calibration import (
    ENV_PRE_FINAL_POOL_ML_ENABLED,
    is_pre_final_pool_ml_enabled,
)
from lotoia.ml.pre_gp_deterministic_recovery import (
    ENV_PRE_GP_RECOVERY_ENABLED,
    is_pre_gp_recovery_enabled,
)


@pytest.fixture(autouse=True)
def _mock_structural_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    policy: dict[str, Any] = {
        "policy_version": "M-ML-070-v1",
        "core_numbers": [7, 12, 16, 23],
        "discouraged_numbers": [2, 4, 11, 15, 24, 25],
    }
    monkeypatch.setattr(
        "lotoia.ml.structural_policy_15d.ensure_structural_policy_15d_memory",
        lambda db_path=None: policy,
    )
    monkeypatch.setattr(
        "lotoia.ml.supervised_output_calibration.ensure_structural_policy_15d_memory",
        lambda db_path=None: policy,
    )
    monkeypatch.setattr(
        "lotoia.ml.supervised_output_calibration.build_structural_policy_15d_calibration_plan",
        lambda bundle, policy_payload: {"has_plan": False, "parametros_sugeridos": {}},
    )


@pytest.fixture(autouse=True)
def _clear_ml_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for env_name in (
        ENV_ML_OPERATIONAL_ENABLED,
        ENV_HIERARCHY_ENABLED,
        ENV_PRE_FINAL_POOL_ML_ENABLED,
        ENV_AGENT_ENABLED,
        ENV_PRE_GP_RECOVERY_ENABLED,
    ):
        monkeypatch.delenv(env_name, raising=False)


def test_core002_soberano_direto(sovereign_generation_enabled) -> None:
    result = generate_best_games(
        count=5,
        pool_size=20,
        ml_enabled=None,
        seed=42,
        batch_label="STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
    )
    assert len(result["games"]) == 5
    assert result.get("ml_operational_hierarchy", {}).get("hierarchy_applied") is not True


def test_ml_opt_in_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_ML_OPERATIONAL_ENABLED, "1")
    assert is_ml_operational_enabled() is True


def test_ml_default_desativado(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_ML_OPERATIONAL_ENABLED, raising=False)
    assert is_ml_operational_enabled() is False


def test_ml_stack_defaults_desativados() -> None:
    assert is_ml_operational_hierarchy_enabled() is False
    assert is_pre_final_pool_ml_enabled() is False
    assert is_agent_operador_ml_enabled() is False
    assert is_pre_gp_recovery_enabled() is False


@pytest.mark.parametrize("card_format", [15, 17, 20])
def test_multidezena_sem_ml(sovereign_generation_enabled, card_format: int) -> None:
    batch_label = resolve_core_002_batch_label(card_format)
    result = generate_best_games(
        count=5,
        pool_size=20,
        ml_enabled=None,
        seed=42,
        batch_label=batch_label,
    )
    assert len(result["games"]) == 5
    assert result.get("ml_operational_hierarchy", {}).get("hierarchy_applied") is not True


def test_ml_hierarchy_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_HIERARCHY_ENABLED, "1")
    assert is_ml_operational_hierarchy_enabled() is True


def test_generation_still_requires_sovereign_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "0")
    with pytest.raises(RuntimeError, match="Geração Lei 15 bloqueada"):
        generate_best_games(
            count=5,
            pool_size=20,
            ml_enabled=None,
            seed=42,
            batch_label="STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
        )
