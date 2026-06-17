from __future__ import annotations

import inspect
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest

from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL
from lotoia.generator.basic_generator import generate_best_games
from lotoia.ml.rerank import rerank_games


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_RERANK_PATH = PROJECT_ROOT / "src" / "lotoia" / "ml" / "rerank.py"


def make_scored_game(numbers: list[int], final_score: float) -> dict[str, object]:
    return {
        "numbers": numbers,
        "odd": 7,
        "even": 8,
        "sum": sum(numbers),
        "frame": 10,
        "center": 5,
        "quadra_score": {
            "found_quadras": 1,
            "total_frequency": 100,
            "average_frequency": 100,
            "average_rank": 10,
            "top_quadras": [],
        },
        "final_score": {"final_score": final_score, "components": {}},
    }


def test_rerank_games_implementation_source_is_official_src_module() -> None:
    source_file = inspect.getsourcefile(rerank_games)

    assert source_file is not None
    assert Path(source_file).resolve() == OFFICIAL_RERANK_PATH.resolve()


def test_rerank_games_preserves_disabled_compatibility_without_score_ml() -> None:
    games = [{"numbers": [1, 2, 3]}]

    result = rerank_games(games, enabled=False)

    assert result is games
    assert result[0]["ml_enabled"] is False
    assert "score_ml" not in result[0]


def test_rerank_games_attaches_incremental_score_ml_when_enabled() -> None:
    games = [make_scored_game([1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24], 10)]

    result = rerank_games(games, enabled=True)

    assert result is games
    assert result[0]["ml_enabled"] is True
    assert 0 <= result[0]["score_ml"] <= 100
    assert result[0]["score_ml_details"]["model_version"] == "historical_recalibrated_v2"


def test_generate_best_games_ml_enabled_does_not_change_ranking(
    monkeypatch, sovereign_generation_enabled
) -> None:
    pool = [
        make_scored_game([1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24], 10),
        make_scored_game([1, 2, 3, 5, 7, 8, 10, 12, 14, 16, 18, 20, 22, 24, 25], 30),
        make_scored_game([1, 2, 4, 5, 7, 9, 10, 12, 14, 16, 18, 20, 22, 24, 25], 20),
    ]

    def _mock_pool(pool_size, *, seed, history, config):
        return deepcopy(pool)[:pool_size]

    def _mock_compose(games, count, config, *, game_size=15):
        return list(games[:count])

    with patch("lotoia.generation.lei15_core_002.build_sovereign_pool", side_effect=_mock_pool):
        with patch(
            "lotoia.generation.lei15_core_002.compose_sovereign_gp",
            side_effect=_mock_compose,
        ):
            disabled_result = generate_best_games(
                count=3, pool_size=3, ml_enabled=False, batch_label=BATCH_LABEL
            )
            enabled_result = generate_best_games(
                count=3, pool_size=3, ml_enabled=True, batch_label=BATCH_LABEL
            )

    assert [game["numbers"] for game in enabled_result["games"]] == [
        game["numbers"] for game in disabled_result["games"]
    ]
    assert all(game["ml_enabled"] is False for game in disabled_result["games"])
    assert all(game["ml_enabled"] is True for game in enabled_result["games"])
    assert all("score_ml" in game for game in enabled_result["games"])


def test_generate_best_games_legacy_path_blocked_without_sovereign_label() -> None:
    with pytest.raises(RuntimeError, match="Geração Lei 15 bloqueada"):
        generate_best_games(count=3, pool_size=3, ml_enabled=False)
