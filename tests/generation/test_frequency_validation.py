"""Tests for frequency validation module."""

from lotoia.generation.frequency_validation import (
    FrequencyViolation,
    build_official_frequency_baseline,
    compute_deviation_metrics,
    compute_generated_frequency,
    validate_and_report,
    validate_frequency_alignment,
)


class MockContest:
    """Mock contest record for testing."""

    def __init__(self, numbers: list[int]):
        self.numbers = numbers


def test_build_official_frequency_baseline() -> None:
    """Test baseline construction from contest history."""
    # Create mock contests with known frequencies
    contests = [
        MockContest([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]),
        MockContest([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]),
        MockContest([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]),
        MockContest([16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 1, 2, 3, 4, 5]),
    ]

    baseline = build_official_frequency_baseline(contests, last=4)

    assert baseline.total_contests == 4
    assert baseline.window == 4
    # Dezena 1 appears in all 4 contests = 100%
    assert baseline.frequencies[1] == 100.0
    # Dezena 16 appears in 1 contest = 25%
    assert baseline.frequencies[16] == 25.0
    # Dezena 6 appears in 3 contests = 75%
    assert baseline.frequencies[6] == 75.0


def test_compute_generated_frequency() -> None:
    """Test frequency computation from generated games."""
    games = [
        {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]},
        {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]},
        {"numbers": [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 1, 2, 3, 4, 5]},
    ]

    freq = compute_generated_frequency(games, game_size=15)

    assert freq.game_size == 15
    assert freq.total_games == 3
    assert freq.expected_pct_per_dezena == 60.0
    # Dezena 1 appears in all 3 games = 100%
    assert freq.frequencies[1] == 100.0
    # Dezena 16 appears in 1 game = 33.33%
    assert abs(freq.frequencies[16] - 33.33) < 0.1


def test_validate_frequency_alignment_valid() -> None:
    """Test validation passes when frequencies are within tolerance."""
    games = [
        {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]},
        {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]},
        {"numbers": [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 1, 2, 3, 4, 5]},
    ]
    generated = compute_generated_frequency(games, game_size=15)

    # Create baseline with similar frequencies
    contests = [
        MockContest([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]),
        MockContest([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]),
        MockContest([16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 1, 2, 3, 4, 5]),
    ]
    baseline = build_official_frequency_baseline(contests, last=3)

    is_valid, violations = validate_frequency_alignment(
        generated, baseline, tolerance_pp=5.0
    )

    assert is_valid is True
    assert len(violations) == 0


def test_validate_frequency_alignment_with_violations() -> None:
    """Test validation detects violations when frequencies deviate."""
    # Generated games heavily favor dezena 16
    games = [
        {"numbers": [16, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]},
        {"numbers": [16, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]},
        {"numbers": [16, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]},
    ]
    generated = compute_generated_frequency(games, game_size=15)

    # Baseline where dezena 16 appears only 33% of the time
    contests = [
        MockContest([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]),
        MockContest([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]),
        MockContest([16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 1, 2, 3, 4, 5]),
    ]
    baseline = build_official_frequency_baseline(contests, last=3)

    is_valid, violations = validate_frequency_alignment(
        generated, baseline, tolerance_pp=5.0
    )

    assert is_valid is False
    assert len(violations) > 0
    # Dezena 16 should be in violations (100% vs 33.33% = +66.67pp)
    dezena_16_violation = next((v for v in violations if v.dezena == 16), None)
    assert dezena_16_violation is not None
    assert dezena_16_violation.deviation_pp > 60.0


def test_validate_and_report() -> None:
    """Test one-call validation function."""
    games = [
        {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]},
        {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]},
    ]
    contests = [
        MockContest([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]),
        MockContest([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]),
    ]

    result = validate_and_report(games, contests, game_size=15, last=2)

    assert result.game_size == 15
    assert result.max_deviation_pp >= 0
    assert result.avg_deviation_pp >= 0
    assert isinstance(result.summary, dict)
    assert "max_deviation_pp" in result.summary


def test_compute_deviation_metrics() -> None:
    """Test deviation metrics computation."""
    games = [
        {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]},
    ]
    generated = compute_generated_frequency(games, game_size=15)

    contests = [
        MockContest([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]),
    ]
    baseline = build_official_frequency_baseline(contests, last=1)

    metrics = compute_deviation_metrics(generated, baseline)

    assert "max_deviation_pp" in metrics
    assert "avg_deviation_pp" in metrics
    assert "details" in metrics
    assert metrics["game_size"] == 15
    assert metrics["total_games"] == 1


def test_empty_games() -> None:
    """Test handling of empty games list."""
    freq = compute_generated_frequency([], game_size=15)
    assert freq.total_games == 0
    assert freq.game_size == 15

    baseline = build_official_frequency_baseline([], last=300)
    assert baseline.total_contests == 0


def test_string_numbers_parsing() -> None:
    """Test parsing of comma-separated string numbers."""
    games = [
        {"numbers": "01,02,03,04,05,06,07,08,09,10,11,12,13,14,15"},
    ]
    freq = compute_generated_frequency(games, game_size=15)
    assert freq.frequencies[1] == 100.0
    assert freq.frequencies[15] == 100.0
