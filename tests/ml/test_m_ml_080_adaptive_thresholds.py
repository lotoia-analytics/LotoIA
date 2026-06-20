"""M-ML-080 — Limiares adaptativos por tamanho de lote."""

from __future__ import annotations

import pytest

from lotoia.ml.ml_operational_hierarchy import (
    MISSION_ID_080,
    _pool_candidate_slice,
    resolve_min_coverage_for_count,
    resolve_min_pool_compliance_rate,
)
from lotoia.ml.overlap_format_thresholds import (
    DIVERSITY_LOW_THRESHOLD,
    resolve_diversity_low_threshold,
)
from lotoia.ml.supervised_output_calibration import (
    DEFAULT_NEAR_DUP_PAIR_RATIO,
    resolve_near_duplicate_pair_ratio,
)


@pytest.mark.parametrize(
    ("requested_count", "expected"),
    [
        (1, 0.35),
        (5, 0.35),
        (10, 0.42),
        (20, 0.48),
        (50, 0.52),
        (100, 0.55),
    ],
)
def test_resolve_diversity_low_threshold(requested_count: int, expected: float) -> None:
    assert resolve_diversity_low_threshold(requested_count) == expected
    assert resolve_diversity_low_threshold(100) == DIVERSITY_LOW_THRESHOLD


@pytest.mark.parametrize(
    ("requested_count", "expected"),
    [
        (1, 0.60),
        (5, 0.60),
        (10, 0.50),
        (20, 0.40),
        (50, 0.33),
        (100, 0.28),
    ],
)
def test_resolve_near_duplicate_pair_ratio(requested_count: int, expected: float) -> None:
    assert resolve_near_duplicate_pair_ratio(requested_count) == expected
    assert resolve_near_duplicate_pair_ratio(100) == DEFAULT_NEAR_DUP_PAIR_RATIO


@pytest.mark.parametrize(
    ("requested_count", "expected"),
    [
        (1, 18),
        (5, 18),
        (10, 22),
        (15, 22),
        (16, 25),
        (100, 25),
    ],
)
def test_resolve_min_coverage_for_count(requested_count: int, expected: int) -> None:
    assert resolve_min_coverage_for_count(requested_count) == expected


@pytest.mark.parametrize(
    ("requested_count", "expected"),
    [
        (1, 0.70),
        (5, 0.70),
        (10, 0.80),
        (20, 0.85),
        (50, 0.90),
        (100, 0.90),
    ],
)
def test_resolve_min_pool_compliance_rate(requested_count: int, expected: float) -> None:
    assert resolve_min_pool_compliance_rate(requested_count) == expected


@pytest.mark.parametrize(
    ("requested_count", "expected_limit"),
    [
        (1, 30),
        (5, 30),
        (10, 50),
        (20, 100),
        (50, 250),
    ],
)
def test_pool_candidate_slice_limit(requested_count: int, expected_limit: int) -> None:
    pool = [{"profile_score": index, "numbers": list(range(1, 16))} for index in range(500)]
    sliced = _pool_candidate_slice(pool, requested_count=requested_count)
    assert len(sliced) == expected_limit


def test_legacy_constants_preserved_as_fallback() -> None:
    assert DIVERSITY_LOW_THRESHOLD == 0.55
    assert DEFAULT_NEAR_DUP_PAIR_RATIO == 0.28


def test_mission_id_declared() -> None:
    assert MISSION_ID_080 == "M-ML-080"
