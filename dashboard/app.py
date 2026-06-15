"""Streamlit Cloud entrypoint for the full institutional dashboard.

Keep this file intentionally small: Streamlit Cloud should run
`dashboard/app.py`, which delegates to `dashboard.institutional_app.main`.
"""

from __future__ import annotations

from typing import Any


def main() -> None:
    from dashboard.institutional_app import main as institutional_main

    institutional_main()


def _format_numbers(numbers: list[int]) -> str:
    from dashboard.institutional_app import _format_numbers as institutional_format_numbers

    return institutional_format_numbers(numbers)


def _games_dataframe(games: list[dict[str, Any]]):
    from dashboard.institutional_app import _games_dataframe as institutional_games_dataframe

    return institutional_games_dataframe(games)


def _backtest_games_dataframe(result):
    from dashboard.institutional_app import _backtest_games_dataframe as institutional_backtest_games_dataframe

    return institutional_backtest_games_dataframe(result)


def _distribution_chart(hit_distribution: dict[str, int]):
    from dashboard.institutional_app import _distribution_chart as institutional_distribution_chart

    return institutional_distribution_chart(hit_distribution)


def _score_correlation_chart(result):
    from dashboard.institutional_app import _score_correlation_chart as institutional_score_correlation_chart

    return institutional_score_correlation_chart(result)


if __name__ == "__main__":
    main()
