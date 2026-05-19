from lotoia.models.draw import Draw
from lotoia.statistics.basic import number_frequency, summarize_draws
from lotoia.statistics.patterns import low_high_distribution, odd_even_distribution


def test_number_frequency_counts_all_numbers() -> None:
    result = number_frequency([[1, 2, 3], [1, 3, 25]])

    assert result[1] == 2
    assert result[2] == 1
    assert result[25] == 1
    assert result[24] == 0


def test_summarize_draws() -> None:
    result = summarize_draws(
        [
            Draw(
                contest=1,
                date="2026-01-01",
                numbers=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
            )
        ]
    )

    assert result["total_draws"] == 1
    assert result["numbers_tracked"] == 25
    assert result["last_contest"] == {
        "contest": 1,
        "date": "2026-01-01",
        "numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    }
    assert result["frequencies"][1] == 1
    assert result["frequencies"][25] == 0


def test_pattern_distributions() -> None:
    draw = [1, 2, 3, 14, 20]

    assert odd_even_distribution(draw) == {"odd": 2, "even": 3}
    assert low_high_distribution(draw) == {"low": 3, "high": 2}
