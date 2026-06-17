from __future__ import annotations

from unittest.mock import patch

import pytest

from lotoia.governance.analysis_batch_labels import LEI15_CORE_002_SOVEREIGN, infer_batch_type
from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL, ENV_GENERATION_ENABLED
from lotoia.governance.lei15_generation_routing_policy import (
    SOVEREIGN_BATCH_TYPE,
    SOVEREIGN_GENERATION_PATH,
    assert_v1_active_global_blocked,
    effective_should_apply_gp_realignment,
    enforce_lei15_generation_routing,
    enforce_legacy_lei15_entry_blocked,
    institutional_routing_report,
    is_historical_evidence_label,
    resolve_generation_routing,
)
from lotoia.governance.lei15_legacy_core_baseline import LEGACY_CORE_BASELINE_LABEL
from lotoia.generator.basic_generator import (
    generate_best_games,
    generate_filtered_game,
    generate_multiple_games,
)


def test_batch_label_none_blocked() -> None:
    decision = resolve_generation_routing(None)
    assert decision.allowed is False
    assert decision.legacy_path_blocked is True
    with pytest.raises(RuntimeError, match="batch_label=None"):
        enforce_lei15_generation_routing(None, source="test")


def test_legacy_default_entrypoints_blocked() -> None:
    with pytest.raises(RuntimeError, match="batch_label=None"):
        enforce_legacy_lei15_entry_blocked(source="generate_filtered_game")
    with pytest.raises(RuntimeError, match="Geração Lei 15 bloqueada"):
        generate_filtered_game()
    with pytest.raises(RuntimeError, match="Geração Lei 15 bloqueada"):
        generate_multiple_games(count=1)


def test_historical_labels_blocked_operational() -> None:
    assert is_historical_evidence_label("STRUCT_REALIGN_V1_15D_001") is True
    assert is_historical_evidence_label(BATCH_LABEL) is False
    with pytest.raises(RuntimeError, match="evidência histórica"):
        enforce_lei15_generation_routing("STRUCT_REALIGN_V1_15D_001", source="test")
    with pytest.raises(RuntimeError, match="Nucleo antigo Lei 15 congelado"):
        enforce_lei15_generation_routing(LEGACY_CORE_BASELINE_LABEL, source="test")


def test_sovereign_label_routes_core_002(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOTOIA_LEI15_CORE_002", "sovereign")
    monkeypatch.delenv(ENV_GENERATION_ENABLED, raising=False)
    decision = resolve_generation_routing(BATCH_LABEL)
    assert decision.apply_sovereign_core_002 is True
    assert decision.generation_path == SOVEREIGN_GENERATION_PATH
    assert infer_batch_type(BATCH_LABEL) == LEI15_CORE_002_SOVEREIGN
    assert decision.batch_type == SOVEREIGN_BATCH_TYPE


def test_generation_blocked_when_flag_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOTOIA_LEI15_CORE_002", "sovereign")
    monkeypatch.delenv(ENV_GENERATION_ENABLED, raising=False)
    with pytest.raises(RuntimeError, match="Geração Lei 15 bloqueada"):
        generate_best_games(count=3, pool_size=5, batch_label=BATCH_LABEL)


def test_v1_active_global_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1", "active")
    with pytest.raises(RuntimeError, match="V1 active global bloqueado"):
        assert_v1_active_global_blocked(source="test")


def test_v1_compose_blocked_outside_sovereign_compose(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1", "shadow_test")
    assert effective_should_apply_gp_realignment("STRUCT_REALIGN_V1_15D_001", apply_sovereign=True) is False
    monkeypatch.setenv("LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1", "active")
    with pytest.raises(RuntimeError, match="V1 active global bloqueado"):
        effective_should_apply_gp_realignment("STRUCT_REALIGN_V1_15D_001", apply_sovereign=False)


def test_sovereign_path_with_mock_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOTOIA_LEI15_CORE_002", "sovereign")
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "1")
    monkeypatch.setenv("LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1", "off")

    def _mock_pool(pool_size, *, seed, history, config):
        from lotoia.generator.basic_generator import _attach_scores, _build_game

        games = []
        for i in range(pool_size):
            nums = sorted({((i + j * 7) % 25) + 1 for j in range(15)})
            game = _build_game(nums)
            _attach_scores(game, history=history, profile_type="recorrente")
            games.append(game)
        return games

    with patch("lotoia.generation.lei15_core_002.build_sovereign_pool", side_effect=_mock_pool):
        with patch(
            "lotoia.generation.lei15_core_002.compose_sovereign_gp",
            side_effect=lambda pool, count, cfg, *, game_size=15: pool[:count],
        ):
            result = generate_best_games(count=3, pool_size=6, batch_label=BATCH_LABEL)

    assert result["count"] == 3
    game = result["games"][0]
    assert game["generation_path"] == SOVEREIGN_GENERATION_PATH
    assert game["batch_label"] == BATCH_LABEL
    assert game["batch_type"] == SOVEREIGN_BATCH_TYPE
    assert game["legacy_path_blocked"] is True
    assert game["v1_active_global_blocked"] is True
    assert game["lei15_core_002_applied"] is True


def test_institutional_routing_report() -> None:
    report = institutional_routing_report()
    assert report["confirmations"]["legacy_default_blocked"] is True
    assert report["confirmations"]["historical_v1_blocked"] is True
    assert report["confirmations"]["sovereign_routes_core_002"] is True
