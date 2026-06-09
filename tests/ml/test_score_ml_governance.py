from __future__ import annotations

from copy import deepcopy

from lotoia.ml import activate_score_ml_runtime


def _sample_game() -> dict[str, object]:
    return {
        "numbers": [1, 2, 3, 4, 5, 7, 9, 11, 13, 15, 18, 20, 22, 24, 25],
        "odd": 8,
        "even": 7,
        "sum": 204,
        "frame": 10,
        "center": 5,
        "quadra_score": {"found_quadras": 4, "average_rank": 10.0},
        "final_score": {"final_score": 81.0, "components": {}},
    }


def test_activate_score_ml_runtime_attaches_metadata_without_changing_order() -> None:
    games = [deepcopy(_sample_game()), deepcopy(_sample_game())]

    activated_games, summary = activate_score_ml_runtime(games, enabled=True)

    assert activated_games is games
    assert summary["enabled"] is True
    assert summary["activated"] is True
    assert summary["hybrid_ranking_preserved"] is True
    assert summary["scored_count"] == 2
    assert all("score_ml" in game for game in activated_games)


def test_activate_score_ml_runtime_keeps_disabled_games_unscored() -> None:
    games = [deepcopy(_sample_game())]

    activated_games, summary = activate_score_ml_runtime(games, enabled=False)

    assert activated_games is games
    assert summary["enabled"] is False
    assert summary["activated"] is False
    assert summary["scored_count"] == 0
    assert "score_ml" not in activated_games[0]
