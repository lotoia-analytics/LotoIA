import pytest

from lotoia.backtesting import BacktestResult, run_backtest
from lotoia.models.draw import Draw
from lotoia.statistics.scoring import ScoreConfig


def make_draw(contest: int, numbers: list[int]) -> Draw:
    return Draw(contest=contest, date=None, numbers=numbers)


def test_backtest_does_not_leak_future_draws() -> None:
    draws = [
        make_draw(1, list(range(1, 16))),
        make_draw(2, list(range(2, 17))),
        make_draw(3, list(range(3, 18))),
    ]
    max_history_contests = []

    def provider(history, target, games_count, pool_size, seed):
        max_history_contests.append(max(draw.contest for draw in history))
        assert all(draw.contest < target.contest for draw in history)
        return [list(range(1, 16)), list(range(2, 17))]

    run_backtest(
        draws=draws,
        contests_analyzed=[2, 3],
        games_count=1,
        pool_size=2,
        history_window=None,
        candidate_provider=provider,
        persist=False,
    )

    assert max_history_contests == [1, 2]


def test_backtest_records_cutoff_context() -> None:
    draws = [
        make_draw(1, list(range(1, 16))),
        make_draw(2, list(range(2, 17))),
        make_draw(3, list(range(3, 18))),
    ]

    def provider(history, target, games_count, pool_size, seed):
        return [list(range(1, 16))]

    result = run_backtest(
        draws=draws,
        contests_analyzed=[3],
        games_count=1,
        pool_size=1,
        history_window=None,
        candidate_provider=provider,
        persist=False,
    )

    contest_result = result.contest_results[0]
    assert contest_result["cutoff_contest"] == 3
    assert contest_result["history_first_contest"] == 1
    assert contest_result["history_last_contest"] == 2
    assert contest_result["history_size"] == 2


def test_backtest_calculates_hits_correctly() -> None:
    draws = [
        make_draw(1, list(range(1, 16))),
        make_draw(2, list(range(1, 16))),
    ]

    def provider(history, target, games_count, pool_size, seed):
        return [list(range(1, 16))]

    result = run_backtest(
        draws=draws,
        contests_analyzed=[2],
        games_count=1,
        pool_size=1,
        history_window=None,
        candidate_provider=provider,
        persist=False,
    )

    assert result.best_game["hits"] == 15
    assert result.hit_distribution["15"] == 1


def test_backtest_calculates_metrics() -> None:
    draws = [
        make_draw(1, list(range(1, 16))),
        make_draw(2, list(range(1, 16))),
    ]

    def provider(history, target, games_count, pool_size, seed):
        return [list(range(1, 16)), list(range(11, 26))]

    result = run_backtest(
        draws=draws,
        contests_analyzed=[2],
        games_count=2,
        pool_size=2,
        history_window=None,
        candidate_provider=provider,
        persist=False,
    )

    assert isinstance(result, BacktestResult)
    assert result.contests_analyzed == 1
    assert result.total_games == 2
    assert result.average_hits == 10
    assert result.hit_distribution["15"] == 1
    assert result.hit_distribution["5"] if "5" in result.hit_distribution else 0 == 0
    assert result.best_game["hits"] == 15
    assert result.worst_game["hits"] == 5
    assert -1 <= result.final_score_hit_correlation <= 1


def test_backtest_is_stable_with_seed() -> None:
    draws = [
        make_draw(contest, list(range(1 + (contest % 5), 16 + (contest % 5))))
        for contest in range(1, 8)
    ]

    first_result = run_backtest(
        draws=draws,
        contests_analyzed=2,
        games_count=2,
        pool_size=4,
        history_window=3,
        seed=123,
        persist=False,
    )
    second_result = run_backtest(
        draws=draws,
        contests_analyzed=2,
        games_count=2,
        pool_size=4,
        history_window=3,
        seed=123,
        persist=False,
    )

    assert first_result.to_dict() == second_result.to_dict()


def test_backtest_degrades_when_candidate_pool_is_too_strict() -> None:
    draws = [
        make_draw(contest, list(range(1 + (contest % 5), 16 + (contest % 5))))
        for contest in range(1, 5)
    ]

    result = run_backtest(
        draws=draws,
        contests_analyzed=[4],
        games_count=2,
        pool_size=2,
        history_window=2,
        seed=42,
        persist=False,
    )

    assert result.total_games >= 2
    assert result.contests_analyzed == 1


def test_backtest_uses_explicit_score_weights() -> None:
    draws = [
        make_draw(contest, list(range(1 + (contest % 5), 16 + (contest % 5))))
        for contest in range(1, 5)
    ]

    def provider(history, target, games_count, pool_size, seed):
        return [list(range(1, 16))]

    sum_only_weights = {
        "duo_score": 0,
        "terno_score": 0,
        "quadra_score": 0,
        "quina_score": 0,
        "delay_score": 0,
        "frequency_score": 0,
        "sum_score": 1,
        "sequence_score": 0,
    }

    result = run_backtest(
        draws=draws,
        contests_analyzed=[4],
        games_count=1,
        pool_size=1,
        history_window=None,
        seed=1,
        candidate_provider=provider,
        score_config=ScoreConfig(weights=sum_only_weights, name="sum_only"),
        persist=False,
    )

    game = result.contest_results[0]["games"][0]
    assert game["final_score"]["final_score"] == game["final_score"]["components"]["sum_score"]


def test_backtest_validates_explicit_score_weights() -> None:
    with pytest.raises(ValueError, match="ausentes: .*duo_score"):
        run_backtest(
            draws=[make_draw(1, list(range(1, 16))), make_draw(2, list(range(1, 16)))],
            contests_analyzed=[2],
            games_count=1,
            pool_size=1,
            score_weights={"sum_score": 1},
            persist=False,
        )


def test_backtest_validates_parameters() -> None:
    with pytest.raises(ValueError, match="maior que zero"):
        run_backtest(draws=[], games_count=0, persist=False)
