from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch

import pytest

from lotoia.benchmark.benchmark_engine import STRATEGY_LOTOIA, run_benchmark
from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL
from lotoia.generator.basic_generator import generate_best_games
from lotoia.ml.score_ml import (
    InterpretableLinearScoreML,
    calibrate_linear_score_ml,
    migrate_score_ml_snapshot,
    extract_score_ml_features,
    supervised_rerank_games,
)
from lotoia.models.draw import Draw


def make_game(numbers: list[int], final_score: float) -> dict[str, object]:
    return {
        "numbers": numbers,
        "odd": sum(1 for number in numbers if number % 2),
        "even": sum(1 for number in numbers if not number % 2),
        "sum": sum(numbers),
        "frame": 10,
        "center": 5,
        "quadra_score": {
            "found_quadras": 3,
            "total_frequency": 100,
            "average_frequency": 100,
            "average_rank": 10,
            "top_quadras": [],
        },
        "final_score": {"final_score": final_score, "components": {}},
    }


def test_score_ml_is_stable_for_same_game() -> None:
    game = make_game([1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24], 70)
    scorer = InterpretableLinearScoreML()

    first = scorer.score(game)
    second = scorer.score(deepcopy(game))

    assert first.as_dict() == second.as_dict()
    assert 0 <= first.score_ml <= 100


def test_score_ml_attribution_covers_official_features() -> None:
    game = make_game([1, 2, 3, 4, 5, 7, 9, 11, 13, 15, 18, 20, 22, 24, 25], 80)

    result = InterpretableLinearScoreML().score(game)

    assert set(result.features) == set(extract_score_ml_features(game))
    assert {item.feature for item in result.attribution} == set(result.features)
    assert all(item.contribution >= 0 for item in result.attribution)


def test_supervised_rerank_is_explicit_and_does_not_mutate_hybrid_contract() -> None:
    low_ml = make_game([1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24], 10)
    high_ml = make_game([1, 2, 3, 4, 5, 7, 9, 11, 13, 15, 18, 20, 22, 24, 25], 90)

    ranked = supervised_rerank_games([low_ml, high_ml])

    assert ranked[0]["score_ml"] >= ranked[1]["score_ml"]
    assert ranked[0]["numbers"] == high_ml["numbers"]


def test_generator_keeps_hybrid_ranking_when_score_ml_enabled(
    monkeypatch, sovereign_generation_enabled
) -> None:
    pool = [
        make_game([1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24], 10),
        make_game([1, 2, 3, 5, 7, 8, 10, 12, 14, 16, 18, 20, 22, 24, 25], 30),
        make_game([1, 2, 4, 5, 7, 9, 10, 12, 14, 16, 18, 20, 22, 24, 25], 20),
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
            result = generate_best_games(
                count=3, pool_size=3, ml_enabled=True, batch_label=BATCH_LABEL
            )

    assert len(result["games"]) == 3
    assert all("score_ml" in game for game in result["games"])


def test_generator_legacy_path_blocked_without_sovereign_label() -> None:
    with pytest.raises(RuntimeError, match="Geração Lei 15 bloqueada"):
        generate_best_games(count=3, pool_size=3, ml_enabled=True)


def test_score_ml_calibration_rejects_temporal_leakage() -> None:
    rows = [
        {
            "feature_cutoff_contest": 10,
            "label_contest": 10,
            "features": {name: 0.5 for name in extract_score_ml_features(make_game([], 0))},
            "target_hits": 11,
        }
    ]

    try:
        calibrate_linear_score_ml(rows)
    except ValueError as exc:
        assert "leaks future information" in str(exc)
    else:
        raise AssertionError("calibration must reject leaked rows")


def test_old_snapshot_is_migrated_to_recalibrated_model() -> None:
    migrated = migrate_score_ml_snapshot(
        {
            "model_version": "score-ml-linear-baseline-v0.1.0",
            "feature_schema_version": "score-ml-features-v0.1.0",
        }
    )

    assert migrated["model_version"] == "historical_recalibrated_v2"
    assert migrated["calibration"]["version"] == "historical_recalibrated_v2"
    assert migrated["fallback_used"] is False


def test_benchmark_remains_statistical_without_score_ml_fields(tmp_path) -> None:
    draws = [
        Draw(contest=index, numbers=list(range(1, 16)))
        for index in range(1, 8)
    ]

    result = run_benchmark(
        draws=draws,
        contests_analyzed=1,
        games_count=1,
        pool_size=1,
        history_window=3,
        output_dir=tmp_path,
        write_report=False,
        persist=False,
    )

    lotoia_game = result.contest_results[0]["strategy_results"][STRATEGY_LOTOIA]["games"][0]
    assert "final_score" in lotoia_game
    assert "score_ml" not in lotoia_game
