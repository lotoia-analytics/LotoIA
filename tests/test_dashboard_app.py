from lotoia.backtesting import BacktestResult

from dashboard.app import (
    _backtest_games_dataframe,
    _distribution_chart,
    _format_numbers,
    _games_dataframe,
    _score_correlation_chart,
)


def test_format_numbers_uses_two_digits() -> None:
    assert _format_numbers([1, 2, 10, 25]) == "01 02 10 25"


def test_games_dataframe_contains_scores_and_rank() -> None:
    dataframe = _games_dataframe(
        [
            {
                "numbers": [1, 2, 3, 4, 5],
                "odd": 3,
                "even": 2,
                "sum": 15,
                "final_score": {"final_score": 87.5, "components": {}},
                "quadra_score": {"found_quadras": 12, "average_rank": 123.4},
            }
        ]
    )

    assert dataframe.loc[0, "rank"] == 1
    assert dataframe.loc[0, "final_score"] == 87.5
    assert dataframe.loc[0, "quadras"] == 12


def test_backtest_dataframe_and_charts_are_created() -> None:
    result = BacktestResult(
        contests_analyzed=1,
        games_per_contest=1,
        pool_size=1,
        history_window=20,
        total_games=1,
        average_hits=11,
        hit_distribution={"11": 1, "12": 0, "13": 0, "14": 0, "15": 0},
        best_game=None,
        worst_game=None,
        average_winner_final_score=70,
        final_score_hit_correlation=0,
        contest_results=[
            {
                "contest": 100,
                "target_numbers": list(range(1, 16)),
                "best_hits": 11,
                "average_hits": 11,
                "games": [
                    {
                        "contest": 100,
                        "numbers": list(range(1, 16)),
                        "hits": 11,
                        "final_score": {"final_score": 70, "components": {}},
                        "quadra_score": {"found_quadras": 20, "average_rank": 300},
                    }
                ],
            }
        ],
    )

    dataframe = _backtest_games_dataframe(result)
    distribution_chart = _distribution_chart(result.hit_distribution)
    correlation_chart = _score_correlation_chart(result)

    assert dataframe.loc[0, "concurso"] == 100
    assert dataframe.loc[0, "acertos"] == 11
    assert distribution_chart.data
    assert correlation_chart.data
