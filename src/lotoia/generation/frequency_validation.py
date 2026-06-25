"""Frequency validation against official Lotofácil history.

This module validates that generated games have dezena frequencies
aligned with the official Lotofácil history (last 300 contests).

Purpose:
- Detect bias where certain dezenas are over/under-represented
- Provide actionable metrics for dashboard monitoring
- Support frequency-based calibration per game_size (15D-23D)

Usage:
    from lotoia.generation.frequency_validation import (
        build_official_frequency_baseline,
        compute_generated_frequency,
        validate_frequency_alignment,
        FrequencyViolation,
    )

    baseline = build_official_frequency_baseline(official_history, last=300)
    generated_freq = compute_generated_frequency(games, game_size=15)
    is_valid, violations = validate_frequency_alignment(
        generated_freq, baseline, tolerance_pp=5.0
    )

Author: LotoIA Core Team
Date: June 2026
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from typing import Any, Sequence

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_OFFICIAL_WINDOW: int = 300
DEFAULT_TOLERANCE_PP: float = 5.0
TOTAL_DEZENAS: int = 25


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FrequencyViolation:
    """A single dezena frequency violation."""

    dezena: int
    actual_pct: float
    expected_pct: float
    deviation_pp: float

    def __str__(self) -> str:
        direction = "OVER" if self.deviation_pp > 0 else "UNDER"
        return (
            f"Dezena {self.dezena:02d}: {self.actual_pct:.1f}% vs "
            f"{self.expected_pct:.1f}% ({direction} {abs(self.deviation_pp):.1f}pp)"
        )


@dataclass
class FrequencyBaseline:
    """Official frequency baseline from last N contests."""

    window: int
    total_contests: int
    frequencies: dict[int, float]  # dezena -> percentage
    raw_counts: dict[int, int]  # dezena -> absolute count
    computed_at: str = ""  # ISO timestamp (optional)


@dataclass
class GeneratedFrequency:
    """Generated games frequency distribution."""

    game_size: int
    total_games: int
    expected_pct_per_dezena: float  # game_size / 25 * 100
    frequencies: dict[int, float]  # dezena -> percentage
    raw_counts: dict[int, int]  # dezena -> absolute count


@dataclass
class FrequencyValidationResult:
    """Result of frequency alignment validation."""

    is_valid: bool
    game_size: int
    max_deviation_pp: float
    avg_deviation_pp: float
    violations: list[FrequencyViolation]
    summary: dict[str, Any]

    def __bool__(self) -> bool:
        return self.is_valid


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def build_official_frequency_baseline(
    official_history: Sequence[Any],
    *,
    last: int = DEFAULT_OFFICIAL_WINDOW,
) -> FrequencyBaseline:
    """Build frequency baseline from last N official contests.

    Args:
        official_history: Sequence of official contest records.
            Each record must have a 'numbers' attribute or key.
        last: Number of recent contests to use (default 300).

    Returns:
        FrequencyBaseline with per-dezena frequencies.
    """
    if not official_history:
        return FrequencyBaseline(
            window=last,
            total_contests=0,
            frequencies={d: 0.0 for d in range(1, TOTAL_DEZENAS + 1)},
            raw_counts={d: 0 for d in range(1, TOTAL_DEZENAS + 1)},
        )

    # Take last N contests
    recent = list(official_history)[-last:]
    total = len(recent)

    counter: Counter[int] = Counter()
    for contest in recent:
        # Support both object attributes and dict keys
        if hasattr(contest, "numbers"):
            numbers = contest.numbers
        elif isinstance(contest, dict):
            numbers = contest.get("numbers", [])
        else:
            numbers = []

        if isinstance(numbers, str):
            # Parse comma-separated string "01,02,03,..."
            try:
                numbers = [int(n.strip()) for n in numbers.split(",")]
            except (ValueError, AttributeError):
                continue

        for num in numbers:
            try:
                counter[int(num)] += 1
            except (ValueError, TypeError):
                continue

    # Build frequency dict
    frequencies: dict[int, float] = {}
    raw_counts: dict[int, int] = {}
    for dezena in range(1, TOTAL_DEZENAS + 1):
        count = counter.get(dezena, 0)
        raw_counts[dezena] = count
        frequencies[dezena] = (count / total * 100.0) if total > 0 else 0.0

    logger.info(
        "[FrequencyValidation] baseline built: window=%d contests=%d",
        last,
        total,
    )

    return FrequencyBaseline(
        window=last,
        total_contests=total,
        frequencies=frequencies,
        raw_counts=raw_counts,
    )


def compute_generated_frequency(
    games: Sequence[dict[str, Any]],
    *,
    game_size: int | None = None,
) -> GeneratedFrequency:
    """Compute frequency distribution from generated games.

    Args:
        games: Sequence of game dicts with 'numbers' key.
        game_size: Expected game size (15, 18, 19, 20, 21).
            If None, inferred from first game.

    Returns:
        GeneratedFrequency with per-dezena frequencies.
    """
    if not games:
        resolved_size = game_size or 15
        return GeneratedFrequency(
            game_size=resolved_size,
            total_games=0,
            expected_pct_per_dezena=(resolved_size / TOTAL_DEZENAS * 100.0),
            frequencies={d: 0.0 for d in range(1, TOTAL_DEZENAS + 1)},
            raw_counts={d: 0 for d in range(1, TOTAL_DEZENAS + 1)},
        )

    # Infer game_size from first game if not provided
    if game_size is None:
        first_numbers = games[0].get("numbers", [])
        if isinstance(first_numbers, str):
            first_numbers = [int(n.strip()) for n in first_numbers.split(",")]
        game_size = len(first_numbers)

    total = len(games)
    counter: Counter[int] = Counter()

    for game in games:
        numbers = game.get("numbers", [])
        if isinstance(numbers, str):
            try:
                numbers = [int(n.strip()) for n in numbers.split(",")]
            except (ValueError, AttributeError):
                continue

        for num in numbers:
            try:
                counter[int(num)] += 1
            except (ValueError, TypeError):
                continue

    # Build frequency dict
    expected_pct = (game_size / TOTAL_DEZENAS) * 100.0
    frequencies: dict[int, float] = {}
    raw_counts: dict[int, int] = {}
    for dezena in range(1, TOTAL_DEZENAS + 1):
        count = counter.get(dezena, 0)
        raw_counts[dezena] = count
        frequencies[dezena] = (count / total * 100.0) if total > 0 else 0.0

    return GeneratedFrequency(
        game_size=game_size,
        total_games=total,
        expected_pct_per_dezena=expected_pct,
        frequencies=frequencies,
        raw_counts=raw_counts,
    )


def validate_frequency_alignment(
    generated: GeneratedFrequency,
    baseline: FrequencyBaseline,
    *,
    tolerance_pp: float = DEFAULT_TOLERANCE_PP,
) -> tuple[bool, list[FrequencyViolation]]:
    """Validate that generated frequency aligns with official baseline.

    Args:
        generated: Generated games frequency distribution.
        baseline: Official frequency baseline.
        tolerance_pp: Maximum allowed deviation in percentage points.

    Returns:
        Tuple of (is_valid, violations).
        is_valid is True if all deviations are within tolerance.
        violations is a list of FrequencyViolation for out-of-tolerance dezenas.
    """
    violations: list[FrequencyViolation] = []

    for dezena in range(1, TOTAL_DEZENAS + 1):
        actual_pct = generated.frequencies.get(dezena, 0.0)
        expected_pct = baseline.frequencies.get(dezena, 0.0)
        deviation = actual_pct - expected_pct

        if abs(deviation) > tolerance_pp:
            violations.append(
                FrequencyViolation(
                    dezena=dezena,
                    actual_pct=actual_pct,
                    expected_pct=expected_pct,
                    deviation_pp=deviation,
                )
            )

    is_valid = len(violations) == 0

    if violations:
        violations.sort(key=lambda v: abs(v.deviation_pp), reverse=True)
        logger.warning(
            "[FrequencyValidation] %d violations found (tolerance=%.1fpp): %s",
            len(violations),
            tolerance_pp,
            "; ".join(str(v) for v in violations[:5]),
        )
    else:
        logger.info(
            "[FrequencyValidation] all dezenas within tolerance (%.1fpp)",
            tolerance_pp,
        )

    return is_valid, violations


def compute_deviation_metrics(
    generated: GeneratedFrequency,
    baseline: FrequencyBaseline,
) -> dict[str, Any]:
    """Compute summary deviation metrics.

    Args:
        generated: Generated games frequency distribution.
        baseline: Official frequency baseline.

    Returns:
        Dict with max_deviation_pp, avg_deviation_pp, and per-dezena details.
    """
    deviations: list[float] = []
    details: dict[str, Any] = {}

    for dezena in range(1, TOTAL_DEZENAS + 1):
        actual = generated.frequencies.get(dezena, 0.0)
        expected = baseline.frequencies.get(dezena, 0.0)
        dev = actual - expected
        deviations.append(abs(dev))

        details[f"d{dezena:02d}"] = {
            "actual_pct": round(actual, 2),
            "expected_pct": round(expected, 2),
            "deviation_pp": round(dev, 2),
        }

    max_dev = max(deviations) if deviations else 0.0
    avg_dev = sum(deviations) / len(deviations) if deviations else 0.0

    return {
        "max_deviation_pp": round(max_dev, 2),
        "avg_deviation_pp": round(avg_dev, 2),
        "total_dezenas": TOTAL_DEZENAS,
        "game_size": generated.game_size,
        "total_games": generated.total_games,
        "baseline_window": baseline.window,
        "baseline_contests": baseline.total_contests,
        "details": details,
    }


def validate_and_report(
    games: Sequence[dict[str, Any]],
    official_history: Sequence[Any],
    *,
    game_size: int | None = None,
    last: int = DEFAULT_OFFICIAL_WINDOW,
    tolerance_pp: float = DEFAULT_TOLERANCE_PP,
) -> FrequencyValidationResult:
    """One-call validation: build baseline, compute freqs, validate.

    Args:
        games: Generated games to validate.
        official_history: Official contest history.
        game_size: Expected game size (inferred if None).
        last: Number of recent contests for baseline.
        tolerance_pp: Maximum allowed deviation.

    Returns:
        FrequencyValidationResult with full details.
    """
    baseline = build_official_frequency_baseline(official_history, last=last)
    generated = compute_generated_frequency(games, game_size=game_size)
    is_valid, violations = validate_frequency_alignment(
        generated, baseline, tolerance_pp=tolerance_pp
    )
    metrics = compute_deviation_metrics(generated, baseline)

    max_dev = max((abs(v.deviation_pp) for v in violations), default=0.0)
    avg_dev = (
        sum(abs(v.deviation_pp) for v in violations) / len(violations)
        if violations
        else 0.0
    )

    return FrequencyValidationResult(
        is_valid=is_valid,
        game_size=generated.game_size,
        max_deviation_pp=round(max_dev, 2),
        avg_deviation_pp=round(avg_dev, 2),
        violations=violations,
        summary=metrics,
    )
