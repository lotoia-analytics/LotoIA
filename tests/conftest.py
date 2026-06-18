"""Fixtures compartilhadas para testes de geração institucional LEI15_CORE_002."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL
from lotoia.generator.basic_generator import _attach_scores, _build_game
from lotoia.database.env_resolution import COMPAT_DATABASE_PUBLIC_URL_ENV, PRIMARY_DATABASE_ENV_VARS


@pytest.fixture(autouse=True)
def _isolate_database_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent host Cloud Agent secrets from leaking into unit tests."""
    for env_name in (*PRIMARY_DATABASE_ENV_VARS, COMPAT_DATABASE_PUBLIC_URL_ENV):
        monkeypatch.delenv(env_name, raising=False)


@pytest.fixture
def sovereign_generation_enabled(monkeypatch: pytest.MonkeyPatch):
    """Habilita flag soberana e mocka pool/compose sem gerar jogos reais CAND-D."""
    monkeypatch.setenv("LOTOIA_LEI15_CORE_002", "sovereign")
    monkeypatch.setenv("LOTOIA_LEI15_CORE_002_GENERATION_ENABLED", "1")
    monkeypatch.setenv("LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1", "off")

    def _mock_pool(pool_size, *, seed, history, config):
        games = []
        for i in range(pool_size):
            nums = sorted({((i + j * 7) % 25) + 1 for j in range(15)})
            game = _build_game(nums)
            _attach_scores(game, history=history, profile_type="recorrente")
            games.append(game)
        return games

    def _mock_compose(pool, count, config, *, game_size=15):
        from lotoia.generation.lei15_core_002 import tag_sovereign_gp_metadata

        selected = list(pool[:count])
        tag_sovereign_gp_metadata(selected, config=config)
        for game in selected:
            game["v1_selection_compose_applied"] = True
            game["generation_path"] = "LEI15_CORE_002"
        return selected

    with patch(
        "lotoia.generation.lei15_core_002.build_sovereign_pool",
        side_effect=_mock_pool,
    ), patch(
        "lotoia.generation.lei15_core_002.compose_sovereign_gp",
        side_effect=_mock_compose,
    ):
        yield BATCH_LABEL
