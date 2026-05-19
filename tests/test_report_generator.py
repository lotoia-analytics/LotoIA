import json

from lotoia.backtesting.backtester import BacktestResult
from lotoia.reports import ReportSummary, generate_backtest_report


def make_game(contest: int, numbers: list[int], hits: int, final_score: float) -> dict[str, object]:
    return {
        "contest": contest,
        "numbers": numbers,
        "hits": hits,
        "final_score": {"final_score": final_score, "components": {}},
        "quadra_score": {
            "found_quadras": 10,
            "total_frequency": 100,
            "average_frequency": 10,
            "average_rank": 20,
            "top_quadras": [],
        },
    }


def make_result() -> BacktestResult:
    first_games = [
        make_game(1, list(range(1, 16)), 11, 70),
        make_game(1, list(range(2, 17)), 9, 50),
    ]
    second_games = [
        make_game(2, list(range(3, 18)), 12, 80),
        make_game(2, list(range(4, 19)), 8, 40),
    ]
    return BacktestResult(
        contests_analyzed=2,
        games_per_contest=2,
        pool_size=4,
        history_window=10,
        total_games=4,
        average_hits=10,
        hit_distribution={"11": 1, "12": 1, "13": 0, "14": 0, "15": 0},
        best_game=first_games[0],
        worst_game=second_games[1],
        average_winner_final_score=75,
        final_score_hit_correlation=0.5,
        contest_results=[
            {
                "contest": 1,
                "target_numbers": list(range(1, 16)),
                "games": first_games,
                "best_hits": 11,
                "average_hits": 10,
            },
            {
                "contest": 2,
                "target_numbers": list(range(2, 17)),
                "games": second_games,
                "best_hits": 12,
                "average_hits": 10,
            },
        ],
    )


def make_calibration() -> dict[str, object]:
    return {
        "evaluations": [
            {
                "configuration": "official",
                "average_hits": 10,
                "final_score_hit_correlation": 0.5,
                "hit_standard_deviation": 1.5,
                "total_weight": 100,
            },
            {
                "configuration": "experimental",
                "average_hits": 10.5,
                "final_score_hit_correlation": 0.6,
                "hit_standard_deviation": 1.2,
                "total_weight": 100,
            },
        ]
    }


def test_generate_backtest_report_creates_files(tmp_path) -> None:
    summary = generate_backtest_report(make_result(), make_calibration(), tmp_path, "test_report")

    assert isinstance(summary, ReportSummary)
    assert summary.json_path.exists()
    assert all(path.exists() for path in summary.csv_paths.values())
    assert all(path.exists() for path in summary.chart_paths.values())


def test_generate_backtest_report_exports_consistent_json(tmp_path) -> None:
    summary = generate_backtest_report(make_result(), make_calibration(), tmp_path, "test_report")

    payload = json.loads(summary.json_path.read_text(encoding="utf-8"))

    assert payload["metrics"]["average_hits"] == 10
    assert payload["metrics"]["hit_distribution"] == {"11": 1, "12": 1, "13": 0, "14": 0, "15": 0}
    assert len(payload["metrics"]["best_games"]) == 4
    assert payload["metrics"]["configuration_metrics"][0]["configuration"] == "official"


def test_generate_backtest_report_exports_csv_data(tmp_path) -> None:
    summary = generate_backtest_report(make_result(), make_calibration(), tmp_path, "test_report")

    summary_csv = summary.csv_paths["summary"].read_text(encoding="utf-8")
    games_csv = summary.csv_paths["games"].read_text(encoding="utf-8")
    configs_csv = summary.csv_paths["configurations"].read_text(encoding="utf-8")

    assert "average_hits,10" in summary_csv
    assert "final_score" in games_csv
    assert "experimental" in configs_csv


def test_generate_backtest_report_metrics_include_stability(tmp_path) -> None:
    summary = generate_backtest_report(make_result(), make_calibration(), tmp_path, "test_report")

    assert summary.metrics["stability"]["hit_standard_deviation"] > 0
    assert summary.metrics["stability"]["min_hits"] == 8
    assert summary.metrics["stability"]["max_hits"] == 12


def test_generate_backtest_report_creates_expected_charts(tmp_path) -> None:
    summary = generate_backtest_report(make_result(), make_calibration(), tmp_path, "test_report")

    assert set(summary.chart_paths) == {
        "hit_distribution",
        "final_score_evolution",
        "correlation",
        "weight_comparison",
        "hits_by_contest",
    }
    assert all(path.stat().st_size > 0 for path in summary.chart_paths.values())
