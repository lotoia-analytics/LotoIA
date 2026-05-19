from collections import Counter
from collections.abc import Iterable
from typing import Protocol

from lotoia.statistics.advanced import (
    calculate_column_distribution,
    calculate_delays,
    calculate_frame_center_distribution,
    calculate_hot_cold_numbers,
    calculate_line_distribution,
    calculate_repeated_numbers,
    calculate_sum,
)
from lotoia.statistics.patterns import low_high_distribution, odd_even_distribution


class DrawLike(Protocol):
    contest: int
    date: str | None
    numbers: list[int]


def _draw_numbers(draw: DrawLike | Iterable[int]) -> Iterable[int]:
    if hasattr(draw, "numbers"):
        return draw.numbers
    return draw


def number_frequency(draws: Iterable[DrawLike | Iterable[int]]) -> dict[int, int]:
    counter: Counter[int] = Counter()
    for draw in draws:
        counter.update(_draw_numbers(draw))
    return {number: counter.get(number, 0) for number in range(1, 26)}


def total_odd_even_distribution(draws: Iterable[DrawLike | Iterable[int]]) -> dict[str, int]:
    distribution = {"odd": 0, "even": 0}
    for draw in draws:
        result = odd_even_distribution(list(_draw_numbers(draw)))
        distribution["odd"] += result["odd"]
        distribution["even"] += result["even"]
    return distribution


def total_low_high_distribution(draws: Iterable[DrawLike | Iterable[int]]) -> dict[str, int]:
    distribution = {"low": 0, "high": 0}
    for draw in draws:
        result = low_high_distribution(list(_draw_numbers(draw)))
        distribution["low"] += result["low"]
        distribution["high"] += result["high"]
    return distribution


def summarize_draws(draws: list[DrawLike | list[int]]) -> dict[str, object]:
    frequencies = number_frequency(draws)
    ordered_contest_draws = [draw for draw in draws if hasattr(draw, "contest")]
    last_draw = max(
        ordered_contest_draws,
        key=lambda draw: draw.contest,
        default=None,
    )
    return {
        "total_draws": len(draws),
        "last_contest": {
            "contest": last_draw.contest,
            "date": last_draw.date,
            "numbers": last_draw.numbers,
        }
        if last_draw
        else None,
        "numbers_tracked": 25,
        "frequencies": frequencies,
        "odd_even_distribution": total_odd_even_distribution(draws),
        "low_high_distribution": total_low_high_distribution(draws),
        "delays": calculate_delays(ordered_contest_draws),
        "line_distribution": calculate_line_distribution(last_draw) if last_draw else None,
        "column_distribution": calculate_column_distribution(last_draw) if last_draw else None,
        "frame_center_distribution": calculate_frame_center_distribution(last_draw)
        if last_draw
        else None,
        "repeated_numbers": calculate_repeated_numbers(ordered_contest_draws),
        "sum_distribution": calculate_sum(last_draw) if last_draw else None,
        "hot_cold_numbers": calculate_hot_cold_numbers(ordered_contest_draws),
    }
