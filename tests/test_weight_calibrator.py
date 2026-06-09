import pytest

from lotoia.calibration import (
    WeightConfiguration,
    compare_weight_configurations,
    evaluate_weight_configuration,
)
from lotoia.models.draw import Draw
from lotoia.statistics.advanced import FINAL_SCORE_WEIGHTS


def make_draw(contest: int, numbers: list[int]) -> Draw:
    return Draw(contest=contest, date=None, numbers=numbers)


def make_draws() -> list[Draw]:
    return [
        make_draw(contest, list(range(1 + (contest % 5), 16 + (contest % 5))))
        for contest in range(1, 8)
    ]


def official_like_configuration(name: str = "test") -> WeightConfiguration:
    return WeightConfiguration(
        name=name,
        duo=15,
        terno=20,
        quadra=25,
        quina=20,
        delay=10,
        frequency=5,
        sum=3,
        sequence=2,
    )


def fixed_provider(history, target, games_count, pool_size, seed):
    del history, target, games_count, seed
    candidates = [
        list(range(1, 16)),
        list(range(2, 17)),
        list(range(3, 18)),
    ]
    return candidates[:pool_size]


def test_evaluate_weight_configuration_restores_original_weights() -> None:
    original_weights = FINAL_SCORE_WEIGHTS.copy()
    configuration = WeightConfiguration(
        name="temporary",
        duo=1,
        terno=1,
        quadra=1,
        quina=1,
        delay=1,
        frequency=1,
        sum=1,
        sequence=1,
    )

    evaluate_weight_configuration(
        configuration,
        draws=make_draws(),
        contests_analyzed=1,
        games_count=1,
        pool_size=2,
        history_window=3,
        seed=1,
        candidate_provider=fixed_provider,
        persist=False,
    )

    assert FINAL_SCORE_WEIGHTS == original_weights


def test_evaluations_are_isolated_between_executions() -> None:
    first = evaluate_weight_configuration(
        official_like_configuration("first"),
        draws=make_draws(),
        contests_analyzed=1,
        games_count=1,
        pool_size=2,
        history_window=3,
        seed=1,
        candidate_provider=fixed_provider,
        persist=False,
    )
    second = evaluate_weight_configuration(
        WeightConfiguration("second", 1, 1, 1, 1, 1, 1, 1, 1),
        draws=make_draws(),
        contests_analyzed=1,
        games_count=1,
        pool_size=2,
        history_window=3,
        seed=1,
        candidate_provider=fixed_provider,
        persist=False,
    )

    assert first["configuration"] == "first"
    assert second["configuration"] == "second"
    assert first["weights"] != second["weights"]


def test_evaluate_weight_configuration_returns_metrics() -> None:
    result = evaluate_weight_configuration(
        official_like_configuration(),
        draws=make_draws(),
        contests_analyzed=1,
        games_count=2,
        pool_size=3,
        history_window=3,
        seed=1,
        candidate_provider=fixed_provider,
        persist=False,
    )

    assert result["average_hits"] >= 0
    assert set(result["hit_distribution"]) == {"8", "9", "10", "11", "12", "13", "14", "15"}
    assert -1 <= result["final_score_hit_correlation"] <= 1
    assert "average_best_game_final_score" in result
    assert "hit_standard_deviation" in result


def test_weight_configuration_validates_negative_weights() -> None:
    configuration = WeightConfiguration("invalid", -1, 1, 1, 1, 1, 1, 1, 1)

    with pytest.raises(ValueError, match="negativos"):
        evaluate_weight_configuration(configuration, draws=make_draws(), persist=False)


def test_weight_configuration_validates_total_weight() -> None:
    configuration = WeightConfiguration("zero", 0, 0, 0, 0, 0, 0, 0, 0)

    with pytest.raises(ValueError, match="soma total"):
        evaluate_weight_configuration(configuration, draws=make_draws(), persist=False)


def test_weight_configuration_reports_total_weight() -> None:
    configuration = official_like_configuration()

    assert configuration.total_weight == 100


def test_compare_weight_configurations_returns_best_configuration() -> None:
    result = compare_weight_configurations(
        [
            official_like_configuration("official"),
            WeightConfiguration("experimental", 1, 1, 1, 1, 1, 1, 1, 1),
        ],
        draws=make_draws(),
        contests_analyzed=1,
        games_count=1,
        pool_size=2,
        history_window=3,
        seed=1,
        candidate_provider=fixed_provider,
        persist=False,
    )

    assert len(result["evaluations"]) == 2
    assert result["best_configuration"] in {"official", "experimental"}


def test_compare_weight_configurations_requires_configurations() -> None:
    with pytest.raises(ValueError, match="ao menos uma"):
        compare_weight_configurations([], persist=False)
