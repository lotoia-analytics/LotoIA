from lotoia.models.draw import Draw
from lotoia.statistics.advanced import (
    calculate_column_distribution,
    calculate_delays,
    calculate_frame_center_distribution,
    calculate_hot_cold_numbers,
    calculate_line_distribution,
    calculate_repeated_numbers,
    calculate_sequence_stats,
    calculate_sum,
    find_sequences,
)


def make_draw(contest: int, numbers: list[int]) -> Draw:
    return Draw(contest=contest, numbers=numbers)


def test_calculate_delays_zero_for_number_in_last_draw() -> None:
    draws = [
        make_draw(1, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]),
        make_draw(2, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16]),
    ]

    result = calculate_delays(draws)

    assert result["16"] == 0


def test_calculate_delays_for_absent_numbers() -> None:
    draws = [
        make_draw(1, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]),
        make_draw(2, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16]),
        make_draw(3, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 17]),
    ]

    result = calculate_delays(draws)

    assert result["15"] == 2
    assert result["16"] == 1
    assert result["17"] == 0


def test_calculate_delays_returns_25_numbers() -> None:
    draws = [
        make_draw(1, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]),
    ]

    result = calculate_delays(draws)

    assert len(result) == 25
    assert set(result) == {str(number) for number in range(1, 26)}


def test_calculate_repeated_numbers_counts_last_two_draws() -> None:
    draws = [
        make_draw(1, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]),
        make_draw(2, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 16, 17, 18, 19, 20]),
    ]

    result = calculate_repeated_numbers(draws)

    assert result["count"] == 10


def test_calculate_repeated_numbers_returns_repeated_numbers_from_last_two_draws() -> None:
    draws = [
        make_draw(1, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]),
        make_draw(2, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 16, 17, 18, 19, 20]),
        make_draw(3, [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 21, 22, 23, 24, 25]),
    ]

    result = calculate_repeated_numbers(draws)

    assert result["numbers"] == [6, 7, 8, 9, 10]


def test_calculate_repeated_numbers_returns_empty_without_two_draws() -> None:
    draws = [
        make_draw(1, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]),
    ]

    result = calculate_repeated_numbers(draws)

    assert result == {"count": 0, "numbers": []}


def test_calculate_sum_returns_correct_total() -> None:
    draw = make_draw(1, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])

    result = calculate_sum(draw)

    assert result == {"total": 120}


def test_calculate_sum_returns_integer_total() -> None:
    draw = make_draw(1, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])

    result = calculate_sum(draw)

    assert isinstance(result["total"], int)


def test_calculate_sum_uses_last_contest_in_summary() -> None:
    from lotoia.statistics.basic import summarize_draws

    draws = [
        make_draw(1, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]),
        make_draw(2, [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]),
    ]

    result = summarize_draws(draws)

    assert result["sum_distribution"] == {"total": 270}


def test_calculate_hot_cold_numbers_returns_five_hot_and_five_cold() -> None:
    draws = [
        make_draw(1, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]),
        make_draw(2, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 16, 17, 18, 19, 20]),
    ]

    result = calculate_hot_cold_numbers(draws)

    assert len(result["hot"]) == 5
    assert len(result["cold"]) == 5


def test_calculate_hot_cold_numbers_orders_by_frequency() -> None:
    draws = [
        make_draw(1, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]),
        make_draw(2, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 16, 17, 18, 19, 20]),
        make_draw(3, [1, 2, 3, 4, 5, 11, 12, 13, 14, 15, 21, 22, 23, 24, 25]),
    ]

    result = calculate_hot_cold_numbers(draws)

    assert result["hot"] == [
        {"number": 1, "frequency": 3},
        {"number": 2, "frequency": 3},
        {"number": 3, "frequency": 3},
        {"number": 4, "frequency": 3},
        {"number": 5, "frequency": 3},
    ]
    assert result["cold"] == [
        {"number": 16, "frequency": 1},
        {"number": 17, "frequency": 1},
        {"number": 18, "frequency": 1},
        {"number": 19, "frequency": 1},
        {"number": 20, "frequency": 1},
    ]


def test_calculate_hot_cold_numbers_uses_window() -> None:
    draws = [
        make_draw(1, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]),
        make_draw(2, [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]),
        make_draw(3, [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 21, 22, 23, 24, 25]),
    ]

    result = calculate_hot_cold_numbers(draws, window=2)

    assert result["window"] == 2
    assert result["hot"] == [
        {"number": 6, "frequency": 2},
        {"number": 7, "frequency": 2},
        {"number": 8, "frequency": 2},
        {"number": 9, "frequency": 2},
        {"number": 10, "frequency": 2},
    ]


def test_calculate_hot_cold_numbers_breaks_ties_by_number() -> None:
    draws = [
        make_draw(1, [21, 22, 23, 24, 25, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
    ]

    result = calculate_hot_cold_numbers(draws)

    assert result["hot"] == [
        {"number": 1, "frequency": 1},
        {"number": 2, "frequency": 1},
        {"number": 3, "frequency": 1},
        {"number": 4, "frequency": 1},
        {"number": 5, "frequency": 1},
    ]
    assert result["cold"] == [
        {"number": 11, "frequency": 0},
        {"number": 12, "frequency": 0},
        {"number": 13, "frequency": 0},
        {"number": 14, "frequency": 0},
        {"number": 15, "frequency": 0},
    ]


def test_find_sequences_identifies_consecutive_groups() -> None:
    result = find_sequences([1, 2, 3, 7, 8, 11, 15, 16])

    assert result == [[1, 2, 3], [7, 8], [15, 16]]


def test_calculate_sequence_stats_returns_largest_sequence() -> None:
    result = calculate_sequence_stats([1, 2, 3, 7, 8, 11, 15, 16])

    assert result == {
        "sequence_count": 3,
        "largest_sequence": 3,
        "sequences": [[1, 2, 3], [7, 8], [15, 16]],
    }


def test_calculate_sequence_stats_without_sequences() -> None:
    result = calculate_sequence_stats([1, 3, 5, 7, 9])

    assert result == {
        "sequence_count": 0,
        "largest_sequence": 0,
        "sequences": [],
    }


def test_calculate_line_distribution_returns_5_lines_and_total_15() -> None:
    draw = make_draw(1, [1, 2, 3, 4, 5, 6, 7, 11, 12, 16, 17, 21, 22, 23, 24])

    result = calculate_line_distribution(draw)

    assert len(result) == 5
    assert sum(result.values()) == 15


def test_calculate_column_distribution_returns_5_columns_and_total_15() -> None:
    draw = make_draw(1, [1, 2, 3, 4, 5, 6, 7, 11, 12, 16, 17, 21, 22, 23, 24])

    result = calculate_column_distribution(draw)

    assert len(result) == 5
    assert sum(result.values()) == 15


def test_calculate_line_distribution_counts_correctly() -> None:
    draw = make_draw(1, [1, 2, 3, 4, 5, 6, 7, 11, 12, 16, 17, 21, 22, 23, 24])

    result = calculate_line_distribution(draw)

    assert result == {
        "line_1": 5,
        "line_2": 2,
        "line_3": 2,
        "line_4": 2,
        "line_5": 4,
    }


def test_calculate_column_distribution_counts_correctly() -> None:
    draw = make_draw(1, [1, 2, 3, 4, 5, 6, 7, 11, 12, 16, 17, 21, 22, 23, 24])

    result = calculate_column_distribution(draw)

    assert result == {
        "column_1": 5,
        "column_2": 5,
        "column_3": 2,
        "column_4": 2,
        "column_5": 1,
    }


def test_calculate_frame_center_distribution_total_is_15() -> None:
    draw = make_draw(1, [1, 2, 3, 4, 5, 7, 8, 9, 12, 13, 14, 17, 18, 19, 25])

    result = calculate_frame_center_distribution(draw)

    assert result["frame"] + result["center"] == 15


def test_calculate_frame_center_distribution_counts_correctly() -> None:
    draw = make_draw(1, [1, 2, 3, 4, 5, 7, 8, 9, 12, 13, 14, 17, 18, 19, 25])

    result = calculate_frame_center_distribution(draw)

    assert result == {"frame": 6, "center": 9}


def test_calculate_frame_center_distribution_identifies_center_numbers() -> None:
    draw = make_draw(1, [7, 8, 9, 12, 13, 14, 17, 18, 19, 1, 2, 3, 4, 5, 6])

    result = calculate_frame_center_distribution(draw)

    assert result["center"] == 9


def test_calculate_frame_center_distribution_identifies_frame_numbers() -> None:
    draw = make_draw(1, [1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 25])

    result = calculate_frame_center_distribution(draw)

    assert result == {"frame": 15, "center": 0}
