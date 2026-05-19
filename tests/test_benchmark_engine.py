from pathlib import Path

from lotoia.benchmark.benchmark_engine import (
    STRATEGY_FILTERED_RANDOM,
    STRATEGY_LOTOIA,
    STRATEGY_PURE_RANDOM,
    _history_for_target,
    run_benchmark,
)
from lotoia.models.draw import Draw


def make_draw(contest: int) -> Draw:
    numbers = sorted(((contest + offset - 1) % 25) + 1 for offset in range(15))
    return Draw(contest=contest, date=None, numbers=numbers)


def make_draws(count: int = 12) -> list[Draw]:
    return [make_draw(contest) for contest in range(1, count + 1)]


def test_benchmark_runs_all_three_strategies() -> None:
    result = run_benchmark(
        draws=make_draws(),
        contests_analyzed=2,
        games_count=2,
        pool_size=4,
        history_window=5,
        seed=7,
        write_report=False,
        persist=False,
    )

    assert result.contests_analyzed == 2
    assert set(result.strategies) == {
        STRATEGY_LOTOIA,
        STRATEGY_FILTERED_RANDOM,
        STRATEGY_PURE_RANDOM,
    }
    assert result.strategies[STRATEGY_LOTOIA]["total_games"] == 4
    assert result.strategies[STRATEGY_FILTERED_RANDOM]["total_games"] == 4
    assert result.strategies[STRATEGY_PURE_RANDOM]["total_games"] == 4


def test_benchmark_uses_only_previous_history() -> None:
    draws = make_draws()
    target = draws[7]

    history = _history_for_target(draws, target, history_window=3)

    assert [draw.contest for draw in history] == [5, 6, 7]
    assert all(draw.contest < target.contest for draw in history)


def test_benchmark_records_cutoff_context() -> None:
    result = run_benchmark(
        draws=make_draws(),
        contests_analyzed=1,
        games_count=1,
        pool_size=2,
        history_window=3,
        seed=19,
        write_report=False,
        persist=False,
    )

    contest_result = result.contest_results[0]
    assert contest_result["cutoff_contest"] == contest_result["contest"]
    assert contest_result["history_size"] == 3
    assert contest_result["history_last_contest"] < contest_result["cutoff_contest"]


def test_benchmark_metrics_are_consistent() -> None:
    result = run_benchmark(
        draws=make_draws(),
        contests_analyzed=2,
        games_count=2,
        pool_size=4,
        history_window=5,
        seed=11,
        write_report=False,
        persist=False,
    )

    for metrics in result.strategies.values():
        assert 0 <= metrics["average_hits"] <= 15
        assert metrics["standard_deviation"] >= 0
        assert set(metrics["hit_distribution"]) == {"11", "12", "13", "14", "15"}
        assert "windows" in metrics["stability"]

    comparison = result.comparisons[f"{STRATEGY_LOTOIA}_vs_{STRATEGY_FILTERED_RANDOM}"]
    assert -15 <= comparison["average_hit_difference"] <= 15
    assert 0 <= comparison["superiority_rate"] <= 1
    assert comparison["lotoia_average_rank"] >= 1


def test_benchmark_filtered_and_pure_do_not_use_scores() -> None:
    result = run_benchmark(
        draws=make_draws(),
        contests_analyzed=1,
        games_count=2,
        pool_size=4,
        history_window=5,
        seed=13,
        write_report=False,
        persist=False,
    )
    contest_result = result.contest_results[0]["strategy_results"]

    assert "final_score" in contest_result[STRATEGY_LOTOIA]["games"][0]
    assert "final_score" not in contest_result[STRATEGY_FILTERED_RANDOM]["games"][0]
    assert "final_score" not in contest_result[STRATEGY_PURE_RANDOM]["games"][0]


def test_benchmark_writes_reports(tmp_path: Path) -> None:
    result = run_benchmark(
        draws=make_draws(),
        contests_analyzed=1,
        games_count=1,
        pool_size=2,
        history_window=5,
        seed=17,
        output_dir=tmp_path,
        persist=False,
    )

    assert Path(result.report_paths["json"]).exists()
    assert Path(result.report_paths["summary_csv"]).exists()
    assert Path(result.report_paths["contests_csv"]).exists()
    assert Path(result.report_paths["comparison_chart"]).exists()
    assert Path(result.report_paths["evolution_chart"]).exists()
