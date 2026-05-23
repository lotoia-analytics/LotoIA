"""Streamlit Cloud entrypoint for the full institutional dashboard.

Keep this file intentionally small: Streamlit Cloud should run
`dashboard/app.py`, which delegates to `dashboard.admin_app.main`.
"""

from __future__ import annotations

from typing import Any


def main() -> None:
    from dashboard.admin_app import main as admin_main

    admin_main()


def _format_numbers(numbers: list[int]) -> str:
    from dashboard.admin_app import _format_numbers as admin_format_numbers

    return admin_format_numbers(numbers)


def _games_dataframe(games: list[dict[str, Any]]):
    from dashboard.admin_app import _games_dataframe as admin_games_dataframe

    return admin_games_dataframe(games)


def _backtest_games_dataframe(result):
    from dashboard.admin_app import _backtest_games_dataframe as admin_backtest_games_dataframe

    return admin_backtest_games_dataframe(result)


def _distribution_chart(hit_distribution: dict[str, int]):
    from dashboard.admin_app import _distribution_chart as admin_distribution_chart

    return admin_distribution_chart(hit_distribution)


def _score_correlation_chart(result):
    from dashboard.admin_app import _score_correlation_chart as admin_score_correlation_chart

    return admin_score_correlation_chart(result)


if __name__ == "__main__":
    main()
