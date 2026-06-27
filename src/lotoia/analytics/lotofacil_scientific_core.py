from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from collections import Counter
from dataclasses import dataclass
from math import log2, sqrt
from itertools import product
from statistics import mean, median
from typing import Any, Iterable, Mapping, Sequence

from sqlalchemy import select

from lotoia.data.loader import load_draws_csv
from lotoia.database.database import (
    DEFAULT_DATABASE_PATH,
    ImportedContest,
    GeneratedGame,
    GenerationEvent,
    LotofacilOfficialHistory,
    ScientificCalibrationDecision,
    ScientificInstitutionalMemory,
    get_session,
)
from lotoia.statistics.advanced import (
    calculate_column_distribution,
    calculate_delays,
    calculate_frame_center_distribution,
    calculate_hot_cold_numbers,
    calculate_line_distribution,
    calculate_repeated_numbers,
    calculate_sequence_stats,
)
from lotoia.statistics.basic import number_frequency

__all__ = [
    "OfficialContestRecord",
    "ContestTransitionAnalysis",
    "ScientificHistoryProfile",
    "ScientificGenerationPolicy",
    "LotofacilScientificCore",
    "load_official_lotofacil_contests",
    "analyze_lotofacil_history",
    "analyze_contest_transition",
    "build_scientific_profile",
    "discover_scientific_generation_policy",
    "get_scientific_generation_policy",
]


def _safe_int(value: Any, default: int | None = None) -> int | None:
    if value is None:
        return default
    try:
        if isinstance(value, str):
            value = value.strip()
            if value in {"", "-", "None", "nan", "NaN"}:
                return default
        if value != value:  # NaN guard
            return default
        return int(float(value))
    except Exception:
        return default


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        text = str(value).strip()
    except Exception:
        return default
    return text or default


def _unique_ints(
    values: Sequence[int | float | None], *, lower: int, upper: int
) -> list[int]:
    unique: list[int] = []
    for value in values:
        try:
            number = int(round(float(value)))
        except Exception:
            continue
        number = max(lower, min(upper, number))
        if number not in unique:
            unique.append(number)
    return unique


def _unique_float_values(
    values: Sequence[float | int | None], *, lower: float, upper: float
) -> list[float]:
    unique: list[float] = []
    for value in values:
        try:
            number = round(float(value), 2)
        except Exception:
            continue
        number = max(lower, min(upper, number))
        if number not in unique:
            unique.append(number)
    return unique


def _normalize_numbers(raw_numbers: Any) -> list[int]:
    numbers: list[int] = []
    if raw_numbers is None:
        return numbers
    if isinstance(raw_numbers, str):
        raw_numbers = raw_numbers.replace(",", " ").split()
    if isinstance(raw_numbers, dict):
        raw_numbers = raw_numbers.get("numbers", [])
    if not isinstance(raw_numbers, Iterable) or isinstance(raw_numbers, (str, bytes)):
        return numbers
    for item in raw_numbers:
        number = _safe_int(item, default=None)
        if number is None or not 1 <= number <= 25:
            continue
        if number not in numbers:
            numbers.append(number)
    return sorted(numbers)


def _band_distribution(numbers: Sequence[int]) -> list[int]:
    bands = [0, 0, 0, 0, 0]
    for number in numbers:
        if 1 <= int(number) <= 25:
            index = (int(number) - 1) // 5
            bands[index] += 1
    return bands


def _coverage_score(numbers: Sequence[int]) -> float:
    bands = _band_distribution(numbers)
    return round(sum(1 for amount in bands if amount > 0) / 5.0, 4) if bands else 0.0


def _entropy_score(numbers: Sequence[int]) -> float:
    bands = _band_distribution(numbers)
    total = sum(bands)
    if not total:
        return 0.0
    entropy = -sum(
        (amount / total) * log2(amount / total) for amount in bands if amount
    )
    max_entropy = (
        log2(len([amount for amount in bands if amount]))
        if sum(1 for amount in bands if amount) > 1
        else 1.0
    )
    if not max_entropy:
        return 0.0
    return round(entropy / max_entropy, 4)


def _parity_pair(numbers: Sequence[int]) -> tuple[int, int]:
    odd = sum(1 for number in numbers if int(number) % 2 != 0)
    even = len(numbers) - odd
    return odd, even


def _low_high_pair(numbers: Sequence[int]) -> tuple[int, int]:
    low = sum(1 for number in numbers if int(number) <= 13)
    high = len(numbers) - low
    return low, high


def _frequency_map(contests: Sequence[dict[str, Any]]) -> dict[int, int]:
    counter: Counter[int] = Counter()
    for contest in contests:
        counter.update(_normalize_numbers(contest.get("numbers", [])))
    return {number: int(counter.get(number, 0)) for number in range(1, 26)}


def _window_frequency_map(
    contests: Sequence[dict[str, Any]], window_size: int | None
) -> dict[str, int]:
    windowed = _window_contests(contests, window_size)
    return {
        str(number): int(amount)
        for number, amount in sorted(_frequency_map(windowed).items())
    }


def _contests_to_draws(contests: Sequence[dict[str, Any]]) -> list[object]:
    draws: list[object] = []
    for item in contests:
        numbers = _normalize_numbers(item.get("numbers", []))
        contest_number = int(item.get("contest_number", 0) or 0)
        draws.append(
            type(
                "LotofacilDrawLike",
                (),
                {"contest": contest_number, "numbers": numbers},
            )()
        )
    return draws


@dataclass(frozen=True, slots=True)
class OfficialContestRecord:
    contest_number: int
    draw_date: str
    numbers: tuple[int, ...]
    source: str
    metadata: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "contest_number": self.contest_number,
            "draw_date": self.draw_date,
            "numbers": list(self.numbers),
            "source": self.source,
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class ContestTransitionAnalysis:
    previous_contest: int
    current_contest: int
    overlap: int
    overlap_ratio: float
    repeated_numbers: tuple[int, ...]
    parity_pair: tuple[int, int]
    low_high_pair: tuple[int, int]
    sequence_max: int
    coverage_score: float
    entropy_score: float
    band_distribution: tuple[int, ...]
    line_distribution: dict[str, int]
    column_distribution: dict[str, int]

    def as_dict(self) -> dict[str, Any]:
        return {
            "previous_contest": self.previous_contest,
            "current_contest": self.current_contest,
            "overlap": self.overlap,
            "overlap_ratio": self.overlap_ratio,
            "repeated_numbers": list(self.repeated_numbers),
            "parity_pair": list(self.parity_pair),
            "low_high_pair": list(self.low_high_pair),
            "sequence_max": self.sequence_max,
            "coverage_score": self.coverage_score,
            "entropy_score": self.entropy_score,
            "band_distribution": list(self.band_distribution),
            "line_distribution": dict(self.line_distribution),
            "column_distribution": dict(self.column_distribution),
        }


@dataclass(frozen=True, slots=True)
class ScientificHistoryProfile:
    source: str
    window_size: int
    contest_count: int
    contest_numbers: tuple[int, ...]
    repeat_distribution: dict[str, int]
    parity_distribution: dict[str, int]
    low_high_distribution: dict[str, int]
    sequence_distribution: dict[str, int]
    coverage_distribution: dict[str, int]
    band_distribution: dict[str, int]
    average_repetition: float
    average_parity_odd: float
    average_parity_even: float
    average_low: float
    average_high: float
    average_sequence_max: float
    average_coverage: float
    average_entropy: float
    frequency_windows: dict[str, dict[str, int]]
    dominant_numbers: list[dict[str, int]]
    discouraged_numbers: list[int]
    transitions: list[dict[str, Any]]
    number_frequency: dict[str, int]
    hot_cold_numbers: dict[str, Any]
    delay_metrics: dict[str, Any]
    return_metrics: dict[str, Any]
    latest_line_distribution: dict[str, int]
    latest_column_distribution: dict[str, int]

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "window_size": self.window_size,
            "contest_count": self.contest_count,
            "contest_numbers": list(self.contest_numbers),
            "repeat_distribution": dict(self.repeat_distribution),
            "parity_distribution": dict(self.parity_distribution),
            "low_high_distribution": dict(self.low_high_distribution),
            "sequence_distribution": dict(self.sequence_distribution),
            "coverage_distribution": dict(self.coverage_distribution),
            "band_distribution": dict(self.band_distribution),
            "average_repetition": self.average_repetition,
            "average_parity_odd": self.average_parity_odd,
            "average_parity_even": self.average_parity_even,
            "average_low": self.average_low,
            "average_high": self.average_high,
            "average_sequence_max": self.average_sequence_max,
            "average_coverage": self.average_coverage,
            "average_entropy": self.average_entropy,
            "frequency_windows": {
                window: dict(values)
                for window, values in self.frequency_windows.items()
            },
            "dominant_numbers": list(self.dominant_numbers),
            "discouraged_numbers": list(self.discouraged_numbers),
            "transitions": list(self.transitions),
            "number_frequency": dict(self.number_frequency),
            "hot_cold_numbers": dict(self.hot_cold_numbers),
            "delay_metrics": dict(self.delay_metrics),
            "return_metrics": dict(self.return_metrics),
            "latest_line_distribution": dict(self.latest_line_distribution),
            "latest_column_distribution": dict(self.latest_column_distribution),
        }


@dataclass(frozen=True, slots=True)
class ScientificGenerationPolicy:
    game_size: int
    window_size: int
    source: str
    contest_count: int
    repeat_min: int
    repeat_max: int
    preferred_parity_pairs: tuple[tuple[int, int], ...]
    allowed_parity_pairs: tuple[tuple[int, int], ...]
    sequence_max: int
    coverage_min: float
    entropy_min: float
    core_numbers: tuple[int, ...]
    discouraged_numbers: tuple[int, ...]
    max_frequency_ratio: float
    min_frequency_ratio: float
    preferred_profile_ratios: dict[tuple[int, int], float]
    notes: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "game_size": self.game_size,
            "window_size": self.window_size,
            "source": self.source,
            "contest_count": self.contest_count,
            "repeat_min": self.repeat_min,
            "repeat_max": self.repeat_max,
            "preferred_parity_pairs": [
                list(pair) for pair in self.preferred_parity_pairs
            ],
            "allowed_parity_pairs": [list(pair) for pair in self.allowed_parity_pairs],
            "sequence_max": self.sequence_max,
            "coverage_min": self.coverage_min,
            "entropy_min": self.entropy_min,
            "core_numbers": list(self.core_numbers),
            "discouraged_numbers": list(self.discouraged_numbers),
            "max_frequency_ratio": self.max_frequency_ratio,
            "min_frequency_ratio": self.min_frequency_ratio,
            "preferred_profile_ratios": {
                f"{pair[0]}/{pair[1]}": ratio
                for pair, ratio in self.preferred_profile_ratios.items()
            },
            "notes": list(self.notes),
        }


def _contest_record_from_db(row: Any) -> OfficialContestRecord:
    numbers = _normalize_numbers(
        str(getattr(row, "dezenas", "") or "").replace(",", " ").split()
    )
    metadata = {}
    metadata_json = str(getattr(row, "metadata_json", "{}") or "{}")
    try:
        import json

        parsed = json.loads(metadata_json)
        if isinstance(parsed, dict):
            metadata = parsed
    except Exception:
        metadata = {}
    return OfficialContestRecord(
        contest_number=int(getattr(row, "contest_number", 0) or 0),
        draw_date=str(getattr(row, "data", "") or ""),
        numbers=tuple(numbers),
        source="imported_contests",
        metadata=metadata,
    )


def _contest_record_from_official_history(row: Any) -> OfficialContestRecord:
    numbers = _normalize_numbers(
        str(getattr(row, "numbers", "") or "").replace(",", " ").split()
    )
    metadata = {}
    metadata_json = str(getattr(row, "metadata_json", "{}") or "{}")
    try:
        import json

        parsed = json.loads(metadata_json)
        if isinstance(parsed, dict):
            metadata = parsed
    except Exception:
        metadata = {}
    return OfficialContestRecord(
        contest_number=int(getattr(row, "contest_number", 0) or 0),
        draw_date=str(getattr(row, "draw_date", "") or ""),
        numbers=tuple(numbers),
        source="lotofacil_official_history",
        metadata=metadata,
    )


def load_official_lotofacil_contests(
    db_path: Any = DEFAULT_DATABASE_PATH,
    *,
    limit: int | None = None,
    use_csv_fallback: bool = True,
) -> list[dict[str, Any]]:
    contests: list[dict[str, Any]] = []
    try:
        with get_session(db_path) as session:
            query = session.execute(
                select(LotofacilOfficialHistory).order_by(
                    LotofacilOfficialHistory.contest_number.asc()
                )
            )
            official_rows = [row[0] for row in query.all()]
    except Exception:
        official_rows = []

    for row in official_rows:
        record = _contest_record_from_official_history(row)
        contests.append(record.as_dict())

    if not contests:
        try:
            with get_session(db_path) as session:
                query = session.execute(
                    select(ImportedContest).order_by(
                        ImportedContest.contest_number.asc()
                    )
                )
                rows = [row[0] for row in query.all()]
        except Exception:
            rows = []

        for row in rows:
            record = _contest_record_from_db(row)
            contests.append(record.as_dict())

    if not contests and use_csv_fallback:
        try:
            draws = load_draws_csv()
        except Exception:
            draws = []
        for draw in draws:
            contests.append(
                OfficialContestRecord(
                    contest_number=int(draw.contest),
                    draw_date=str(draw.date or ""),
                    numbers=tuple(_normalize_numbers(draw.numbers)),
                    source="historico_lotofacil.csv",
                    metadata={},
                ).as_dict()
            )

    contests = sorted(
        contests, key=lambda item: int(item.get("contest_number", 0) or 0)
    )
    if limit is not None and int(limit) > 0:
        contests = contests[-int(limit) :]
    return contests


def _mean_or_zero(values: Sequence[float]) -> float:
    cleaned = [float(value) for value in values if value is not None]
    return round(mean(cleaned), 4) if cleaned else 0.0


def _build_transition(
    previous: dict[str, Any], current: dict[str, Any]
) -> dict[str, Any]:
    previous_numbers = _normalize_numbers(previous.get("numbers", []))
    current_numbers = _normalize_numbers(current.get("numbers", []))
    repeated_numbers = sorted(set(previous_numbers) & set(current_numbers))
    transition = ContestTransitionAnalysis(
        previous_contest=int(previous.get("contest_number", 0) or 0),
        current_contest=int(current.get("contest_number", 0) or 0),
        overlap=len(repeated_numbers),
        overlap_ratio=round(len(repeated_numbers) / max(1, len(current_numbers)), 4),
        repeated_numbers=tuple(repeated_numbers),
        parity_pair=_parity_pair(current_numbers),
        low_high_pair=_low_high_pair(current_numbers),
        sequence_max=int(calculate_sequence_stats(current_numbers)["largest_sequence"]),
        coverage_score=_coverage_score(current_numbers),
        entropy_score=_entropy_score(current_numbers),
        band_distribution=tuple(_band_distribution(current_numbers)),
        line_distribution=calculate_line_distribution(
            type("DrawLike", (), {"numbers": current_numbers})()
        ),
        column_distribution=calculate_column_distribution(
            type("DrawLike", (), {"numbers": current_numbers})()
        ),
    )
    return transition.as_dict()


def _window_contests(
    contests: Sequence[dict[str, Any]], window_size: int | None
) -> list[dict[str, Any]]:
    ordered = sorted(contests, key=lambda item: int(item.get("contest_number", 0) or 0))
    if window_size is not None and int(window_size) > 0:
        return ordered[-int(window_size) :]
    return ordered


def _scientific_local_classification(
    *,
    validation_threshold: int,
    validation_count_plus: int,
    best_hits: int,
    count_10: int,
    count_11_plus: int,
    count_12_plus: int,
    count_13_plus: int,
    count_14_plus: int,
    count_15: int,
) -> str:
    if count_15 > 0 or best_hits >= 15:
        return "TARGET_MAXIMUM"
    if count_14_plus > 0 or best_hits >= 14:
        return "EXCELLENT"
    if count_13_plus > 0 or best_hits >= 13:
        return "VERY_STRONG"
    if count_12_plus > 0 or best_hits >= 12:
        return "STRONG"
    if validation_count_plus > 0 and best_hits >= validation_threshold:
        return "APPROVED_MINIMUM"
    if best_hits >= 10 or count_10 > 0:
        return "NEAR_MISS_LOCAL"
    if best_hits == 9:
        return "FAILED_MEDIUM"
    return "FAILED_LOW"


def _scientific_local_action(classification: str) -> str:
    normalized = str(classification or "").strip().upper()
    return {
        "TARGET_MAXIMUM": "stabilize_target_maximum_and_preserve_diversity",
        "EXCELLENT": "stabilize_excellence_and_seek_15",
        "VERY_STRONG": "preserve_strong_pattern_and_seek_14_plus",
        "STRONG": "reinforce_pattern_and_seek_13_plus",
        "APPROVED_MINIMUM": "preserve_and_push_towards_12_plus",
        "NEAR_MISS_LOCAL": "recalibrate_from_near_miss_towards_15",
        "FAILED_MEDIUM": "recalibrate_from_near_miss_towards_15",
        "FAILED_LOW": "recalibrate_from_low_performance_towards_15",
    }.get(normalized, "recalibrate_from_near_miss_towards_15")


def _scientific_local_confidence(
    *,
    classification: str,
    overfit_risk: float,
    cross_validation_support: float,
) -> str:
    normalized = str(classification or "").strip().upper()
    if (
        normalized in {"TARGET_MAXIMUM", "EXCELLENT"}
        and cross_validation_support >= 0.65
        and overfit_risk <= 0.35
    ):
        return "HIGH"
    if (
        normalized in {"VERY_STRONG", "STRONG"}
        and cross_validation_support >= 0.45
        and overfit_risk <= 0.55
    ):
        return "MEDIUM_HIGH"
    if normalized in {"APPROVED_MINIMUM"} and cross_validation_support >= 0.30:
        return "MEDIUM"
    if normalized in {"NEAR_MISS_LOCAL", "FAILED_MEDIUM"}:
        return "LOW_TO_MEDIUM"
    return "LOW_LOCAL_ONLY"


def _scientific_tier_weighted_score(
    *,
    count_10: int,
    count_11_plus: int,
    count_12_plus: int,
    count_13_plus: int,
    count_14_plus: int,
    count_15: int,
    best_hits: int,
    average_hits: float,
    stability: float,
    overfit_risk: float,
    concentration_risk: float,
) -> float:
    tier_score = (
        float(count_10) * 1.0
        + float(count_11_plus) * 4.0
        + float(count_12_plus) * 8.0
        + float(count_13_plus) * 13.0
        + float(count_14_plus) * 21.0
        + float(count_15) * 34.0
    )
    momentum_bonus = float(best_hits) * 1.25 + float(average_hits) * 0.75
    stability_bonus = float(stability) * 12.0
    penalty = float(overfit_risk) * 18.0 + float(concentration_risk) * 10.0
    return round(tier_score + momentum_bonus + stability_bonus - penalty, 4)


validation_threshold_by_game_size = {
    15: 11,
    17: 12,
    18: 13,
}

target_band_by_game_size = {
    15: "11_to_15",
    17: "12_to_15",
    18: "13_to_15",
}

_scientific_15_vnext_core_numbers = (1, 10, 18, 20, 9, 11, 6, 21)
_scientific_15_vnext_controlled_support_numbers = (24, 15)
_scientific_15_vnext_promote_numbers = (17, 14, 7)
_scientific_15_vnext_real_gap_number = 16
_scientific_15_vnext_reduce_priority_numbers = (2, 3, 5, 8)


def _scientific_15_vnext_policy_metadata() -> dict[str, Any]:
    return {
        "policy_mode": "hybrid_15_towards_12_plus",
        "validation_threshold": 11,
        "target_band": "11_to_15",
        "memory_role": "strong_support",
        "dominant_memory": "conditional",
        "dominant_memory_mode": "conditional",
        "current_target": "12_plus",
        "secondary_target": "13_plus",
        "current_target_label": "12+",
        "secondary_target_label": "13+",
        "validation_priority": {
            "primary": "12_plus",
            "secondary": "13_plus",
            "stability_floor": "11",
            "diagnostic_only": ["10"],
        },
        "policy_objective": "increase_12_plus_while_preserving_11_floor",
        "policy_notes": [
            "12_plus is the primary reference",
            "13_plus is refinement",
            "11 remains the stability floor",
            "10 is diagnostic only",
        ],
        "core_numbers_to_preserve": list(_scientific_15_vnext_core_numbers),
        "controlled_support_numbers": list(
            _scientific_15_vnext_controlled_support_numbers
        ),
        "promote_numbers_for_12_plus": list(_scientific_15_vnext_promote_numbers),
        "real_gap_number": _scientific_15_vnext_real_gap_number,
        "reduce_priority_numbers": list(_scientific_15_vnext_reduce_priority_numbers),
        "forbidden_numbers": [],
        "avoid_hard_veto_numbers": [],
    }


def _apply_scientific_15_vnext_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    enriched = dict(policy)
    if int(enriched.get("game_size", 0) or 0) != 15:
        return enriched
    enriched.update(_scientific_15_vnext_policy_metadata())
    core_numbers = list(_scientific_15_vnext_core_numbers)
    reduce_priority_numbers = list(_scientific_15_vnext_reduce_priority_numbers)
    support_numbers = list(_scientific_15_vnext_controlled_support_numbers)
    if core_numbers:
        enriched["core_numbers"] = core_numbers
    if reduce_priority_numbers:
        enriched["discouraged_numbers"] = reduce_priority_numbers + [12, 22]
    if support_numbers:
        enriched["controlled_support_numbers"] = support_numbers
    enriched.setdefault("policy_adjustment_reason", "hybrid_15_towards_12_plus")
    enriched.setdefault("policy_origin", "scientific_calibration_vnext_15")
    return enriched


def _apply_scientific_15_baseline_governance(
    policy: Mapping[str, Any],
    baseline: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    from lotoia.governance.scientific_governance import (
        build_scientific_policy_15_baseline_governance,
    )

    enriched = _apply_scientific_15_vnext_policy(policy)
    if int(enriched.get("game_size", 0) or 0) != 15:
        return enriched

    baseline_policy = dict(baseline or {})
    baseline_policy_after = dict(
        baseline_policy.get("policy_after")
        or baseline_policy.get("policy_applied")
        or {}
    )
    baseline_summary = dict(baseline_policy.get("cross_validation_summary") or {})
    baseline_notes_raw = baseline_policy.get("notes") or {}
    if isinstance(baseline_notes_raw, str):
        try:
            baseline_notes = (
                json.loads(baseline_notes_raw) if baseline_notes_raw.strip() else {}
            )
        except Exception:
            baseline_notes = {}
    elif isinstance(baseline_notes_raw, Mapping):
        baseline_notes = dict(baseline_notes_raw)
    else:
        baseline_notes = {}

    if baseline_policy_after:
        for key in (
            "policy_mode",
            "policy_validation_status",
            "official_15_search_standard",
            "validated_game_size",
            "validated_threshold",
            "target_band",
            "current_target",
            "secondary_target",
            "highest_validated_hit",
            "gold_target_14",
            "diamond_target_15",
            "baseline_batch_id",
            "baseline_contest_number",
            "baseline_total_games_checked",
            "baseline_count_11_exact",
            "baseline_count_12_exact",
            "baseline_count_13_exact",
            "baseline_count_14_exact",
            "baseline_count_15_exact",
            "validated_target",
            "validated_target_band",
            "official_15_status_label",
            "gold_signal_14",
            "diamond_signal_15",
        ):
            if key in baseline_policy_after:
                enriched[key] = baseline_policy_after[key]

    for key in (
        "policy_validation_status",
        "official_15_search_standard",
        "validated_game_size",
        "validated_threshold",
        "target_band",
        "current_target",
        "secondary_target",
        "highest_validated_hit",
        "gold_target_14",
        "diamond_target_15",
        "baseline_batch_id",
        "baseline_contest_number",
        "baseline_total_games_checked",
        "baseline_count_11_exact",
        "baseline_count_12_exact",
        "baseline_count_13_exact",
        "baseline_count_14_exact",
        "baseline_count_15_exact",
        "validated_target",
        "validated_target_band",
        "official_15_status_label",
        "gold_signal_14",
        "diamond_signal_15",
    ):
        if key in baseline_summary:
            enriched[key] = baseline_summary[key]
        elif key in baseline_notes:
            enriched[key] = baseline_notes[key]

    if baseline_policy_after:
        enriched.setdefault(
            "baseline_batch_id", baseline_policy_after.get("baseline_batch_id")
        )
        enriched.setdefault(
            "baseline_contest_number",
            baseline_policy_after.get("baseline_contest_number"),
        )
        enriched.setdefault(
            "baseline_total_games_checked",
            baseline_policy_after.get("baseline_total_games_checked"),
        )
        enriched.setdefault(
            "baseline_count_11_exact",
            baseline_policy_after.get("baseline_count_11_exact"),
        )
        enriched.setdefault(
            "baseline_count_12_exact",
            baseline_policy_after.get("baseline_count_12_exact"),
        )
        enriched.setdefault(
            "baseline_count_13_exact",
            baseline_policy_after.get("baseline_count_13_exact"),
        )
        enriched.setdefault(
            "baseline_count_14_exact",
            baseline_policy_after.get("baseline_count_14_exact"),
        )
        enriched.setdefault(
            "baseline_count_15_exact",
            baseline_policy_after.get("baseline_count_15_exact"),
        )

    enriched.setdefault("policy_validation_status", "VALIDATED_15_POLICY_LEVEL_3")
    enriched.setdefault("official_15_search_standard", True)
    enriched.setdefault("validated_game_size", 15)
    enriched.setdefault("validated_threshold", 11)
    enriched.setdefault("target_band", "11_to_15")
    enriched.setdefault("current_target", "12_plus")
    enriched.setdefault("secondary_target", "13_plus")
    enriched.setdefault("highest_validated_hit", 13)
    enriched.setdefault("gold_target_14", False)
    enriched.setdefault("diamond_target_15", False)
    enriched.setdefault("validated_target", 13)
    enriched.setdefault("validated_target_band", "13_plus_detected")
    governance = build_scientific_policy_15_baseline_governance(
        baseline_batch_id=str(
            baseline_summary.get("baseline_batch_id")
            or baseline_policy_after.get("baseline_batch_id")
            or baseline_policy.get("batch_id")
            or policy.get("batch_id")
            or ""
        ),
        baseline_contest_number=int(
            baseline_summary.get("baseline_contest_number")
            or baseline_policy_after.get("baseline_contest_number")
            or baseline_policy.get("contest_number")
            or policy.get("contest_number")
            or 3697
        ),
        baseline_total_games_checked=int(
            baseline_summary.get("baseline_total_games_checked")
            or baseline_policy_after.get("baseline_total_games_checked")
            or baseline_policy.get("baseline_total_games_checked")
            or baseline_policy.get("total_games_checked")
            or 50
        ),
        baseline_count_11_exact=int(
            baseline_summary.get("baseline_count_11_exact")
            or baseline_policy_after.get("baseline_count_11_exact")
            or baseline_policy.get("baseline_count_11_exact")
            or baseline_policy.get("count_11_exact")
            or 23
        ),
        baseline_count_12_exact=int(
            baseline_summary.get("baseline_count_12_exact")
            or baseline_policy_after.get("baseline_count_12_exact")
            or baseline_policy.get("baseline_count_12_exact")
            or baseline_policy.get("count_12_exact")
            or 13
        ),
        baseline_count_13_exact=int(
            baseline_summary.get("baseline_count_13_exact")
            or baseline_policy_after.get("baseline_count_13_exact")
            or baseline_policy.get("baseline_count_13_exact")
            or baseline_policy.get("count_13_exact")
            or 3
        ),
        baseline_count_14_exact=int(
            baseline_summary.get("baseline_count_14_exact")
            or baseline_policy_after.get("baseline_count_14_exact")
            or baseline_policy.get("baseline_count_14_exact")
            or baseline_policy.get("count_14_exact")
            or 0
        ),
        baseline_count_15_exact=int(
            baseline_summary.get("baseline_count_15_exact")
            or baseline_policy_after.get("baseline_count_15_exact")
            or baseline_policy.get("baseline_count_15_exact")
            or baseline_policy.get("count_15_exact")
            or 0
        ),
        policy_mode=str(
            baseline_policy_after.get("policy_mode")
            or baseline_policy.get("policy_mode")
            or "hybrid_15_towards_12_plus"
        ),
        policy_validation_status=str(
            baseline_summary.get("policy_validation_status")
            or baseline_policy_after.get("policy_validation_status")
            or "VALIDATED_15_POLICY_LEVEL_3"
        ),
        official_15_search_standard=bool(
            baseline_summary.get("official_15_search_standard")
            if "official_15_search_standard" in baseline_summary
            else baseline_policy_after.get("official_15_search_standard", True)
        ),
        validated_game_size=int(
            baseline_summary.get("validated_game_size")
            or baseline_policy_after.get("validated_game_size")
            or 15
        ),
        validated_threshold=int(
            baseline_summary.get("validated_threshold")
            or baseline_policy_after.get("validated_threshold")
            or 11
        ),
        target_band=str(
            baseline_summary.get("target_band")
            or baseline_policy_after.get("target_band")
            or "11_to_15"
        ),
        current_target=str(
            baseline_summary.get("current_target")
            or baseline_policy_after.get("current_target")
            or "12_plus"
        ),
        secondary_target=str(
            baseline_summary.get("secondary_target")
            or baseline_policy_after.get("secondary_target")
            or "13_plus"
        ),
        highest_validated_hit=int(
            baseline_summary.get("highest_validated_hit")
            or baseline_policy_after.get("highest_validated_hit")
            or 13
        ),
        gold_target_14=bool(
            baseline_summary.get("gold_target_14")
            if "gold_target_14" in baseline_summary
            else baseline_policy_after.get("gold_target_14", False)
        ),
        diamond_target_15=bool(
            baseline_summary.get("diamond_target_15")
            if "diamond_target_15" in baseline_summary
            else baseline_policy_after.get("diamond_target_15", False)
        ),
        approved_for_use=bool(baseline_policy.get("approved_for_use", True)),
        validated_target=int(
            baseline_summary.get("validated_target")
            or baseline_policy_after.get("validated_target")
            or 13
        ),
        validated_target_band=str(
            baseline_summary.get("validated_target_band")
            or baseline_policy_after.get("validated_target_band")
            or "13_plus_detected"
        ),
        official_15_status_label=str(
            baseline_summary.get("official_15_status_label")
            or baseline_policy_after.get("official_15_status_label")
            or "Política 15 validada nível 3. Estabilizou 11+, atingiu 12+ em volume e produziu 13 acertos em bateria prospectiva de 50 jogos. Ouro 14 e diamante 15 seguem como metas superiores futuras."
        ),
    ).as_dict()
    enriched.update(governance)
    enriched["baseline_governance"] = dict(governance)
    return enriched


def _decompose_hit_counts(hits: Sequence[int]) -> dict[str, Any]:
    normalized_hits = [max(0, min(15, int(hit))) for hit in hits if hit is not None]
    histogram = {str(index): 0 for index in range(16)}
    for hit in normalized_hits:
        histogram[str(hit)] += 1
    count_10_exact = histogram["10"]
    count_11_exact = histogram["11"]
    count_12_exact = histogram["12"]
    count_13_exact = histogram["13"]
    count_14_exact = histogram["14"]
    count_15_exact = histogram["15"]
    count_11_plus = sum(histogram[str(index)] for index in range(11, 16))
    count_12_plus = sum(histogram[str(index)] for index in range(12, 16))
    count_13_plus = sum(histogram[str(index)] for index in range(13, 16))
    count_14_plus = sum(histogram[str(index)] for index in range(14, 16))
    count_15 = count_15_exact
    return {
        "hit_histogram": histogram,
        "count_10_exact": count_10_exact,
        "count_10": count_10_exact,
        "count_11_exact": count_11_exact,
        "count_12_exact": count_12_exact,
        "count_13_exact": count_13_exact,
        "count_14_exact": count_14_exact,
        "count_15_exact": count_15_exact,
        "count_11_plus": count_11_plus,
        "count_12_plus": count_12_plus,
        "count_13_plus": count_13_plus,
        "count_14_plus": count_14_plus,
        "count_15": count_15,
    }


def _scientific_validation_rule(game_size: int) -> dict[str, Any]:
    resolved_game_size = max(1, int(game_size or 15))
    validation_threshold = validation_threshold_by_game_size.get(resolved_game_size)
    if validation_threshold is None:
        validation_threshold = (
            13 if resolved_game_size >= 18 else 12 if resolved_game_size >= 17 else 11
        )
    target_band = target_band_by_game_size.get(
        resolved_game_size, f"{validation_threshold}_to_15"
    )
    return {
        "game_size": resolved_game_size,
        "validation_threshold": validation_threshold,
        "target_band": target_band,
        "validation_zone_label": f"Zona de valida\u00e7\u00e3o cient\u00edfica: {validation_threshold} a 15 acertos.",
        "validation_minimum_label": f"{validation_threshold} = valida\u00e7\u00e3o m\u00ednima",
        "validation_band_counts": [
            str(index) for index in range(validation_threshold, 16)
        ],
    }


def _scientific_validation_payload(
    *,
    game_size: int,
    hit_decomposition: Mapping[str, Any],
    best_hits: int,
    validation_count_plus: int,
) -> dict[str, Any]:
    validation_rule = _scientific_validation_rule(game_size)
    validation_threshold = int(validation_rule["validation_threshold"])
    exact_counts = {
        f"count_{hit}_exact": int(hit_decomposition.get(f"count_{hit}_exact", 0) or 0)
        for hit in range(validation_threshold, 16)
    }
    plus_counts = {
        f"count_{hit}_plus": int(hit_decomposition.get(f"count_{hit}_plus", 0) or 0)
        for hit in range(validation_threshold, 15)
    }
    return {
        "game_size": int(validation_rule["game_size"]),
        "validation_threshold": validation_threshold,
        "target_band": str(validation_rule["target_band"]),
        "validation_zone_label": str(validation_rule["validation_zone_label"]),
        "validation_minimum_label": str(validation_rule["validation_minimum_label"]),
        "validation_band_counts": list(validation_rule["validation_band_counts"]),
        "validation_exact_counts": exact_counts,
        "validation_plus_counts": plus_counts,
        "scientific_validation_zone_count": int(validation_count_plus),
        "policy_validation_status": "APROVADO"
        if int(best_hits or 0) >= validation_threshold
        and int(validation_count_plus or 0) > 0
        else "REPROVADO",
    }


def _merge_policy_adjustments(
    base_policy: Mapping[str, Any],
    adjustments: Mapping[str, Any],
) -> dict[str, Any]:
    merged = dict(base_policy or {})
    if not merged:
        return {}
    for key in (
        "repeat_min",
        "repeat_max",
        "sequence_max",
        "coverage_min",
        "entropy_min",
        "max_frequency_ratio",
        "min_frequency_ratio",
        "preferred_parity_pairs",
        "allowed_parity_pairs",
        "core_numbers",
        "discouraged_numbers",
        "preferred_profile_ratios",
    ):
        if key in adjustments:
            merged[key] = adjustments[key]
    if adjustments.get("policy_origin") is not None:
        merged["policy_origin"] = adjustments.get("policy_origin")
    if adjustments.get("policy_variant") is not None:
        merged["policy_variant"] = adjustments.get("policy_variant")
    if adjustments.get("policy_adjustment_reason") is not None:
        merged["policy_adjustment_reason"] = adjustments.get("policy_adjustment_reason")
    if adjustments.get("scientific_score") is not None:
        merged["scientific_score"] = adjustments.get("scientific_score")
    if adjustments.get("next_generation_policy_adjustments") is not None:
        merged["next_generation_policy_adjustments"] = dict(
            adjustments.get("next_generation_policy_adjustments") or {}
        )
    return merged


class LotofacilScientificCore:
    def __init__(
        self,
        contests: Sequence[dict[str, Any]] | None = None,
        *,
        db_path: Any = DEFAULT_DATABASE_PATH,
        use_csv_fallback: bool = True,
    ) -> None:
        self.db_path = db_path
        self.use_csv_fallback = use_csv_fallback
        self._contests = (
            [dict(contest) for contest in contests] if contests is not None else None
        )

    @property
    def contests(self) -> list[dict[str, Any]]:
        if self._contests is None:
            self._contests = load_official_lotofacil_contests(
                self.db_path,
                use_csv_fallback=self.use_csv_fallback,
            )
        return list(self._contests)

    def analyze_contest_transition(
        self,
        previous_contest: dict[str, Any] | Sequence[int],
        current_contest: dict[str, Any] | Sequence[int],
    ) -> dict[str, Any]:
        previous = self._normalize_contest(previous_contest, contest_number=0)
        current = self._normalize_contest(current_contest, contest_number=0)
        return _build_transition(previous, current)

    def analyze_lotofacil_history(
        self, window_size: int | None = None
    ) -> dict[str, Any]:
        contests = _window_contests(self.contests, window_size)
        transitions = [
            _build_transition(previous, current)
            for previous, current in zip(contests, contests[1:], strict=False)
        ]
        profile = self._profile_from_contests(contests, transitions)
        return {
            "source": "imported_contests"
            if any(item.get("source") == "imported_contests" for item in contests)
            else "historico_lotofacil.csv",
            "window_size": len(contests),
            "history_size": len(self.contests),
            "contest_numbers": [
                int(item.get("contest_number", 0) or 0) for item in contests
            ],
            "profile": profile,
            "transitions": transitions,
            "summary": {
                "contest_count": len(contests),
                "transition_count": len(transitions),
                "average_overlap": _mean_or_zero(
                    [float(item["overlap"]) for item in transitions]
                ),
                "average_repetition": profile["average_repetition"],
                "average_coverage": profile["average_coverage"],
                "average_entropy": profile["average_entropy"],
                "average_sequence_max": profile["average_sequence_max"],
                "dominant_numbers": profile["dominant_numbers"],
            },
        }

    def build_scientific_profile(self, window_size: int = 100) -> dict[str, Any]:
        analysis = self.analyze_lotofacil_history(window_size=window_size)
        return dict(analysis["profile"])

    def _load_scientific_memory_rows(self, *, limit: int = 5) -> list[dict[str, Any]]:
        resolved_limit = max(1, int(limit or 1))
        with get_session(self.db_path) as session:
            rows = (
                session.query(ScientificInstitutionalMemory)
                .order_by(
                    ScientificInstitutionalMemory.created_at.desc(),
                    ScientificInstitutionalMemory.id.desc(),
                )
                .limit(resolved_limit)
                .all()
            )
        memory_rows: list[dict[str, Any]] = []
        for row in rows:
            memory_rows.append(
                {
                    "id": int(getattr(row, "id", 0) or 0),
                    "created_at": row.created_at.isoformat()
                    if getattr(row, "created_at", None)
                    else "",
                    "memory_kind": _safe_str(getattr(row, "memory_kind", "")),
                    "strategy_name": _safe_str(getattr(row, "strategy_name", "")),
                    "game_size": int(getattr(row, "game_size", 0) or 0),
                    "batch_id": _safe_str(getattr(row, "batch_id", "")),
                    "generation_range": dict(
                        getattr(row, "generation_range", {}) or {}
                    ),
                    "total_games": int(getattr(row, "total_games", 0) or 0),
                    "unique_games": int(getattr(row, "unique_games", 0) or 0),
                    "duplicate_games": int(getattr(row, "duplicate_games", 0) or 0),
                    "structural_status": _safe_str(
                        getattr(row, "structural_status", "")
                    ),
                    "scientific_status": _safe_str(
                        getattr(row, "scientific_status", "")
                    ),
                    "scientific_classification": _safe_str(
                        getattr(row, "scientific_classification", "")
                    ),
                    "main_reason": _safe_str(getattr(row, "main_reason", "")),
                    "recommended_action": _safe_str(
                        getattr(row, "recommended_action", "")
                    ),
                    "policy_applied": dict(getattr(row, "policy_applied", {}) or {}),
                    "policy_before": dict(getattr(row, "policy_before", {}) or {}),
                    "policy_after": dict(getattr(row, "policy_after", {}) or {}),
                    "best_hit": int(getattr(row, "best_hit", 0) or 0),
                    "average_hits": float(getattr(row, "average_hits", 0.0) or 0.0),
                    "count_11_plus": int(getattr(row, "count_11_plus", 0) or 0),
                    "count_12_plus": int(getattr(row, "count_12_plus", 0) or 0),
                    "count_13_plus": int(getattr(row, "count_13_plus", 0) or 0),
                    "count_14_plus": int(getattr(row, "count_14_plus", 0) or 0),
                    "count_15": int(getattr(row, "count_15", 0) or 0),
                    "validation_contests": list(
                        getattr(row, "validation_contests", []) or []
                    ),
                    "cross_validation_summary": dict(
                        getattr(row, "cross_validation_summary", {}) or {}
                    ),
                    "frequency_alerts": list(
                        getattr(row, "frequency_alerts", []) or []
                    ),
                    "absence_alerts": list(getattr(row, "absence_alerts", []) or []),
                    "parity_alerts": list(getattr(row, "parity_alerts", []) or []),
                    "repetition_alerts": list(
                        getattr(row, "repetition_alerts", []) or []
                    ),
                    "sequence_alerts": list(getattr(row, "sequence_alerts", []) or []),
                    "low_high_alerts": list(getattr(row, "low_high_alerts", []) or []),
                    "range_alerts": list(getattr(row, "range_alerts", []) or []),
                    "decision_mode": _safe_str(
                        getattr(row, "decision_mode", "OBSERVACAO"), "OBSERVACAO"
                    ),
                    "approved_for_use": bool(getattr(row, "approved_for_use", 0) or 0),
                    "notes": _safe_str(getattr(row, "notes", "")),
                    "official_history_count": int(
                        getattr(row, "official_history_count", 0) or 0
                    ),
                    "official_history_first_contest": getattr(
                        row, "official_history_first_contest", None
                    ),
                    "official_history_last_contest": getattr(
                        row, "official_history_last_contest", None
                    ),
                    "official_history_window": list(
                        getattr(row, "official_history_window", []) or []
                    ),
                    "source": _safe_str(
                        getattr(row, "source", "scientific_calibration"),
                        "scientific_calibration",
                    ),
                }
            )
        return memory_rows

    def _load_scientific_calibration_decisions(
        self, *, limit: int = 5
    ) -> list[dict[str, Any]]:
        resolved_limit = max(1, int(limit or 1))
        with get_session(self.db_path) as session:
            rows = (
                session.query(ScientificCalibrationDecision)
                .order_by(
                    ScientificCalibrationDecision.created_at.desc(),
                    ScientificCalibrationDecision.id.desc(),
                )
                .limit(resolved_limit)
                .all()
            )
        decisions: list[dict[str, Any]] = []
        for row in rows:
            decisions.append(
                {
                    "id": int(getattr(row, "id", 0) or 0),
                    "created_at": row.created_at.isoformat()
                    if getattr(row, "created_at", None)
                    else "",
                    "strategy": _safe_str(getattr(row, "strategy", "")),
                    "game_size": int(getattr(row, "game_size", 0) or 0),
                    "source_batch_id": _safe_str(getattr(row, "source_batch_id", "")),
                    "source_generation_range": dict(
                        getattr(row, "source_generation_range", {}) or {}
                    ),
                    "structural_status": _safe_str(
                        getattr(row, "structural_status", "")
                    ),
                    "scientific_status": _safe_str(
                        getattr(row, "scientific_status", "")
                    ),
                    "classification": _safe_str(getattr(row, "classification", "")),
                    "main_reason": _safe_str(getattr(row, "main_reason", "")),
                    "recommended_action": _safe_str(
                        getattr(row, "recommended_action", "")
                    ),
                    "policy_before": dict(getattr(row, "policy_before", {}) or {}),
                    "policy_after": dict(getattr(row, "policy_after", {}) or {}),
                    "mode": _safe_str(getattr(row, "mode", "OBSERVACAO"), "OBSERVACAO"),
                    "applied": bool(getattr(row, "applied", 0) or 0),
                    "approved_by": _safe_str(getattr(row, "approved_by", "")),
                    "notes": _safe_str(getattr(row, "notes", "")),
                }
            )
        return decisions

    def build_post_reconciliation_scientific_memory(
        self,
        *,
        generation_event_id: int,
        batch_id: str,
        contest: dict[str, Any],
        games: Sequence[dict[str, Any]],
        reconciliation_results: Sequence[dict[str, Any]] | None = None,
        policy_before: dict[str, Any] | None = None,
        policy_after: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        resolved_generation_event_id = int(generation_event_id or 0)
        resolved_batch_id = str(batch_id or "").strip()
        contest_numbers = _normalize_numbers(
            contest.get("numbers", contest.get("dezenas", []))
        )
        contest_number = _safe_int(
            contest.get(
                "contest_number", contest.get("contest_id", contest.get("concurso"))
            ),
            default=None,
        )
        game_rows = [dict(game or {}) for game in games or []]
        game_numbers = [
            _normalize_numbers(game.get("numbers", [])) for game in game_rows
        ]
        game_size = (
            len(game_numbers[0])
            if game_numbers
            else len(_normalize_numbers(game_rows[0].get("numbers", [])))
            if game_rows
            else 15
        )
        validation_rule = _scientific_validation_rule(game_size)
        reconciliation_rows = [dict(row or {}) for row in reconciliation_results or []]
        if reconciliation_rows:
            game_hits = [
                int(_safe_int(row.get("hits"), default=0) or 0)
                for row in reconciliation_rows
            ]
        else:
            game_hits = [
                len(set(numbers) & set(contest_numbers)) for numbers in game_numbers
            ]
        best_hits = max(game_hits, default=0)
        average_hits = _mean_or_zero([float(hit) for hit in game_hits])
        count_10 = sum(1 for hit in game_hits if hit == 10)
        count_11_plus = sum(1 for hit in game_hits if hit >= 11)
        count_12_plus = sum(1 for hit in game_hits if hit >= 12)
        count_13_plus = sum(1 for hit in game_hits if hit >= 13)
        count_14_plus = sum(1 for hit in game_hits if hit >= 14)
        count_15 = sum(1 for hit in game_hits if hit >= 15)
        hit_decomposition = _decompose_hit_counts(game_hits)
        validation_threshold = int(validation_rule["validation_threshold"])
        validation_count_plus = {
            11: count_11_plus,
            12: count_12_plus,
            13: count_13_plus,
        }.get(validation_threshold, count_11_plus)
        validation_payload = _scientific_validation_payload(
            game_size=game_size,
            hit_decomposition=hit_decomposition,
            best_hits=best_hits,
            validation_count_plus=validation_count_plus,
        )
        local_classification = _scientific_local_classification(
            validation_threshold=validation_threshold,
            validation_count_plus=validation_count_plus,
            best_hits=best_hits,
            count_10=count_10,
            count_11_plus=count_11_plus,
            count_12_plus=count_12_plus,
            count_13_plus=count_13_plus,
            count_14_plus=count_14_plus,
            count_15=count_15,
        )
        recommended_action = _scientific_local_action(local_classification)
        frequency_counter: Counter[int] = Counter(
            number for numbers in game_numbers for number in numbers
        )
        max_frequency_number = (
            max(frequency_counter, key=frequency_counter.get)
            if frequency_counter
            else None
        )
        max_frequency_count = (
            int(frequency_counter.get(max_frequency_number, 0) or 0)
            if max_frequency_number is not None
            else 0
        )
        total_games = max(1, len(game_numbers))
        max_frequency_ratio = (
            round(max_frequency_count / total_games, 4) if total_games else 0.0
        )
        concentration_risk = (
            round(max(0.0, min(1.0, (max_frequency_ratio - 0.70) / 0.30)), 4)
            if max_frequency_ratio > 0.70
            else 0.0
        )
        windows_payload: dict[str, dict[str, Any]] = {}
        validation_contests: list[int] = []
        support_scores: list[float] = []
        history = self.contests
        for window_size in (10, 60, 100, 300, None):
            window_label = "all" if window_size is None else str(int(window_size))
            window_contests = _window_contests(history, window_size)
            window_contest_numbers = [
                int(item.get("contest_number", 0) or 0) for item in window_contests
            ]
            validation_contests.extend(window_contest_numbers)
            best_hits_per_contest: list[int] = []
            average_hits_per_contest: list[float] = []
            for official_contest in window_contests:
                official_numbers = set(
                    _normalize_numbers(official_contest.get("numbers", []))
                )
                per_game_hits = [
                    len(official_numbers.intersection(set(numbers)))
                    for numbers in game_numbers
                ]
                best_hits_per_contest.append(max(per_game_hits, default=0))
                average_hits_per_contest.append(
                    _mean_or_zero([float(hit) for hit in per_game_hits])
                )
            window_best_hits = max(best_hits_per_contest, default=0)
            window_count_10 = sum(1 for hit in best_hits_per_contest if hit == 10)
            window_count_11_plus = sum(1 for hit in best_hits_per_contest if hit >= 11)
            window_count_12_plus = sum(1 for hit in best_hits_per_contest if hit >= 12)
            window_count_13_plus = sum(1 for hit in best_hits_per_contest if hit >= 13)
            window_count_14_plus = sum(1 for hit in best_hits_per_contest if hit >= 14)
            window_count_15 = sum(1 for hit in best_hits_per_contest if hit >= 15)
            window_hit_decomposition = _decompose_hit_counts(best_hits_per_contest)
            if len(best_hits_per_contest) > 1:
                avg_window_best = mean(best_hits_per_contest)
                variance = mean(
                    (value - avg_window_best) ** 2 for value in best_hits_per_contest
                )
                stability = round(max(0.0, 1.0 - min(sqrt(variance) / 5.0, 1.0)), 4)
            else:
                stability = 1.0 if best_hits_per_contest else 0.0
            overfit_risk = round(
                min(
                    1.0,
                    max(
                        0.0,
                        (
                            1.0
                            - (window_count_11_plus / max(1, len(window_contests)))
                            * 0.5
                        )
                        + ((1.0 - stability) * 0.5),
                    ),
                ),
                4,
            )
            window_support = _mean_or_zero(
                [
                    min(
                        1.0,
                        (
                            float(window_count_10) * 0.5
                            + float(window_count_11_plus) * 1.0
                            + float(window_count_12_plus) * 1.5
                            + float(window_count_13_plus) * 2.0
                            + float(window_count_14_plus) * 2.5
                            + float(window_count_15) * 3.0
                        )
                        / max(1, len(window_contests)),
                    )
                ]
            )
            support_scores.append(window_support)
            windows_payload[window_label] = {
                "contest_scope": "SINGLE_CONTEST"
                if window_size is None
                else "HISTORICAL_WINDOW",
                "window_size": None if window_size is None else int(window_size),
                "contest_count": len(window_contests),
                "contest_numbers": window_contest_numbers,
                "best_hits_average": _mean_or_zero(
                    [float(value) for value in best_hits_per_contest]
                ),
                "best_hits_median": round(median(best_hits_per_contest), 4)
                if best_hits_per_contest
                else 0.0,
                "best_hits_min": min(best_hits_per_contest)
                if best_hits_per_contest
                else 0,
                "best_hits_max": window_best_hits,
                "count_10": window_count_10,
                "count_11_plus": window_count_11_plus,
                "count_12_plus": window_count_12_plus,
                "count_13_plus": window_count_13_plus,
                "count_14_plus": window_count_14_plus,
                "count_15": window_count_15,
                "count_10_exact": window_hit_decomposition["count_10_exact"],
                "count_11_exact": window_hit_decomposition["count_11_exact"],
                "count_12_exact": window_hit_decomposition["count_12_exact"],
                "count_13_exact": window_hit_decomposition["count_13_exact"],
                "count_14_exact": window_hit_decomposition["count_14_exact"],
                "count_15_exact": window_hit_decomposition["count_15_exact"],
                "hit_histogram": dict(window_hit_decomposition["hit_histogram"]),
                "average_hits_per_contest": _mean_or_zero(average_hits_per_contest),
                "stability": stability,
                "overfit_risk": overfit_risk,
                "scientific_score": _scientific_tier_weighted_score(
                    count_10=window_count_10,
                    count_11_plus=window_count_11_plus,
                    count_12_plus=window_count_12_plus,
                    count_13_plus=window_count_13_plus,
                    count_14_plus=window_count_14_plus,
                    count_15=window_count_15,
                    best_hits=window_best_hits,
                    average_hits=_mean_or_zero(
                        [float(value) for value in best_hits_per_contest]
                    ),
                    stability=stability,
                    overfit_risk=overfit_risk,
                    concentration_risk=concentration_risk,
                ),
            }
        historical_windows = dict(windows_payload)
        cross_validation_support = _mean_or_zero(support_scores)
        if local_classification in {"TARGET_MAXIMUM", "EXCELLENT"}:
            confidence_level = "HIGH"
        elif local_classification in {"VERY_STRONG", "STRONG"}:
            confidence_level = "MEDIUM_HIGH"
        elif local_classification in {"APPROVED_MINIMUM"}:
            confidence_level = "MEDIUM"
        else:
            confidence_level = (
                "LOW_TO_MEDIUM"
                if cross_validation_support >= 0.20
                else "LOW_LOCAL_ONLY"
            )
        if confidence_level == "LOW_LOCAL_ONLY" and historical_windows:
            confidence_level = "LOW_TO_MEDIUM"
        base_policy = dict(policy_before or {})
        adjusted_policy = dict(policy_after or base_policy or {})
        if not adjusted_policy and base_policy:
            adjusted_policy = dict(base_policy)
        adjustments: dict[str, Any] = {
            "policy_origin": "scientific_reconciliation_memory",
            "policy_variant": "recalibrate_from_near_miss_towards_15",
            "policy_adjustment_reason": recommended_action,
            "based_on_reconciliation_id": resolved_generation_event_id,
            "based_on_generation_event_id": resolved_generation_event_id,
            "based_on_post_reconciliation_memory_id": None,
            "contest_scope": "SINGLE_CONTEST",
            "confidence_level": confidence_level,
            "requires_cross_validation": True,
            "scientific_score": _scientific_tier_weighted_score(
                count_10=count_10,
                count_11_plus=count_11_plus,
                count_12_plus=count_12_plus,
                count_13_plus=count_13_plus,
                count_14_plus=count_14_plus,
                count_15=count_15,
                best_hits=best_hits,
                average_hits=average_hits,
                stability=cross_validation_support,
                overfit_risk=max(
                    (
                        window.get("overfit_risk", 0.0)
                        for window in historical_windows.values()
                    ),
                    default=0.0,
                ),
                concentration_risk=concentration_risk,
            ),
            "next_generation_policy_adjustments": {
                "repeat_min": int(base_policy.get("repeat_min", 0) or 0),
                "repeat_max": int(base_policy.get("repeat_max", 0) or 0),
                "sequence_max": int(base_policy.get("sequence_max", 0) or 0),
                "coverage_min": round(
                    min(
                        0.95,
                        float(base_policy.get("coverage_min", 0.80) or 0.80) + 0.03,
                    ),
                    4,
                ),  # Elevado de 0.35 para 0.80 (M-OPS-083)
                "entropy_min": round(
                    min(
                        0.85, float(base_policy.get("entropy_min", 0.35) or 0.35) + 0.03
                    ),
                    4,
                ),
                "max_frequency_ratio": round(
                    max(
                        0.50,
                        float(base_policy.get("max_frequency_ratio", 0.70) or 0.70)
                        - 0.05,
                    ),
                    4,
                ),
                "min_frequency_ratio": round(
                    max(
                        0.05,
                        float(base_policy.get("min_frequency_ratio", 0.20) or 0.20),
                    ),
                    4,
                ),
                "prefer_12_plus": True,
                "prefer_13_plus": True,
                "preserve_14_15_path": True,
                "reduce_concentration": concentration_risk > 0.0,
            },
        }
        adjusted_policy = _merge_policy_adjustments(adjusted_policy, adjustments)
        adjusted_policy.update(
            {
                "policy_origin": adjustments["policy_origin"],
                "policy_variant": adjustments["policy_variant"],
                "policy_adjustment_reason": recommended_action,
                "scientific_score": adjustments["scientific_score"],
                "next_generation_policy_adjustments": adjustments[
                    "next_generation_policy_adjustments"
                ],
            }
        )
        return {
            "event_type": "post_reconciliation_scientific_expansion",
            "memory_kind": "scientific_reconciliation",
            "generation_event_id": resolved_generation_event_id,
            "batch_id": resolved_batch_id,
            "contest_number": contest_number,
            "generation_range": {
                "generation_event_id": resolved_generation_event_id,
                "batch_id": resolved_batch_id,
                "contest_number": contest_number,
                "contest_scope": "SINGLE_CONTEST",
                "official_history_window": [10, 60, 100, 300],
                "validation_threshold": validation_threshold,
                "target_band": str(validation_rule["target_band"]),
                "validation_zone_label": str(validation_rule["validation_zone_label"]),
            },
            "contest_scope": "SINGLE_CONTEST",
            "local_classification": local_classification,
            "scientific_classification": local_classification,
            "confidence_level": confidence_level,
            "requires_cross_validation": True,
            "historical_windows": historical_windows,
            "validation_threshold": validation_threshold,
            "target_band": str(validation_rule["target_band"]),
            "validation_zone_label": str(validation_rule["validation_zone_label"]),
            "validation_minimum_label": str(
                validation_rule["validation_minimum_label"]
            ),
            "recommended_action": recommended_action,
            "policy_adjustment_reason": recommended_action,
            "next_generation_policy_adjustments": adjustments[
                "next_generation_policy_adjustments"
            ],
            "scientific_score": adjustments["scientific_score"],
            "scientific_score_components": {
                "count_10": count_10,
                "count_10_exact": hit_decomposition["count_10_exact"],
                "count_11_exact": hit_decomposition["count_11_exact"],
                "count_12_exact": hit_decomposition["count_12_exact"],
                "count_13_exact": hit_decomposition["count_13_exact"],
                "count_14_exact": hit_decomposition["count_14_exact"],
                "count_15_exact": hit_decomposition["count_15_exact"],
                "count_11_plus": count_11_plus,
                "count_12_plus": count_12_plus,
                "count_13_plus": count_13_plus,
                "count_14_plus": count_14_plus,
                "count_15": count_15,
                "hit_histogram": dict(hit_decomposition["hit_histogram"]),
                "best_hits": best_hits,
                "average_hits": average_hits,
                "stability": cross_validation_support,
                "overfit_risk": max(
                    (
                        window.get("overfit_risk", 0.0)
                        for window in historical_windows.values()
                    ),
                    default=0.0,
                ),
                "concentration_risk": concentration_risk,
                "frequency_maxima_dezena": max_frequency_number,
                "frequency_maxima_dezena_percentual": round(
                    max_frequency_ratio * 100.0, 4
                ),
                "frequency_teto_percentual": 70.0,
                "validation_threshold": validation_threshold,
                "target_band": str(validation_rule["target_band"]),
                "validation_zone_label": str(validation_rule["validation_zone_label"]),
                "validation_count_plus": validation_count_plus,
            },
            "policy_before": base_policy,
            "policy_after": adjusted_policy,
            "policy_id": str(
                adjusted_policy.get("policy_signature")
                or adjusted_policy.get("policy_id")
                or base_policy.get("policy_signature")
                or base_policy.get("policy_id")
                or ""
            ),
            "policy_origin": "scientific_reconciliation_memory",
            "policy_variant": "recalibrate_from_near_miss_towards_15",
            "policy_applied": dict(policy_after or base_policy or {}),
            "total_games": len(game_rows),
            "unique_games": len({tuple(numbers) for numbers in game_numbers}),
            "duplicate_games": max(
                0, len(game_rows) - len({tuple(numbers) for numbers in game_numbers})
            ),
            "structural_status": "APROVADO"
            if int(generation_event_id or 0) and int(best_hits or 0) >= 0
            else "REPROVADO",
            "scientific_status": "APROVADO"
            if validation_count_plus > 0
            else "REPROVADO",
            "main_reason": (
                "alvo_maximo_15"
                if count_15 > 0
                else "excelencia_14"
                if count_14_plus > 0
                else "forte_13"
                if count_13_plus > 0
                else "forte_12"
                if count_12_plus > 0
                else f"minimo_premiavel_{validation_threshold}"
                if validation_count_plus > 0
                else "near_miss_local"
            ),
            "best_hit": best_hits,
            "average_hits": average_hits,
            "count_10": count_10,
            "count_10_exact": hit_decomposition["count_10_exact"],
            "count_11_exact": hit_decomposition["count_11_exact"],
            "count_12_exact": hit_decomposition["count_12_exact"],
            "count_13_exact": hit_decomposition["count_13_exact"],
            "count_14_exact": hit_decomposition["count_14_exact"],
            "count_15_exact": hit_decomposition["count_15_exact"],
            "count_11_plus": count_11_plus,
            "count_12_plus": count_12_plus,
            "count_13_plus": count_13_plus,
            "count_14_plus": count_14_plus,
            "count_15": count_15,
            "hit_histogram": dict(hit_decomposition["hit_histogram"]),
            "decision_mode": "OBSERVACAO"
            if confidence_level.startswith("LOW")
            else "AUTONOMIA_SUPERVISIONADA",
            "approved_for_use": int(
                validation_count_plus > 0 and concentration_risk <= 0.5
            ),
            "notes": (
                f"contest_scope=SINGLE_CONTEST | confidence_level={confidence_level} | "
                f"requires_cross_validation=true | overfit_risk={max((window.get('overfit_risk', 0.0) for window in historical_windows.values()), default=0.0):.4f}"
            ),
            "official_history_count": len(history),
            "official_history_first_contest": int(
                history[0].get("contest_number", 0) or 0
            )
            if history
            else None,
            "official_history_last_contest": int(
                history[-1].get("contest_number", 0) or 0
            )
            if history
            else None,
            "official_history_window": [10, 60, 100, 300],
            "validation_threshold": validation_threshold,
            "target_band": str(validation_rule["target_band"]),
            "validation_zone_label": str(validation_rule["validation_zone_label"]),
            "validation_contests": sorted(set(validation_contests)),
            "cross_validation_summary": {
                "contest_scope": "SINGLE_CONTEST",
                "confidence_level": confidence_level,
                "requires_cross_validation": True,
                "validation_threshold": validation_threshold,
                "target_band": str(validation_rule["target_band"]),
                "validation_zone_label": str(validation_rule["validation_zone_label"]),
                "historical_windows": historical_windows,
                "scientific_score": adjustments["scientific_score"],
                "scientific_score_components": {
                    "count_10": count_10,
                    "count_10_exact": hit_decomposition["count_10_exact"],
                    "count_11_exact": hit_decomposition["count_11_exact"],
                    "count_12_exact": hit_decomposition["count_12_exact"],
                    "count_13_exact": hit_decomposition["count_13_exact"],
                    "count_14_exact": hit_decomposition["count_14_exact"],
                    "count_15_exact": hit_decomposition["count_15_exact"],
                    "count_11_plus": count_11_plus,
                    "count_12_plus": count_12_plus,
                    "count_13_plus": count_13_plus,
                    "count_14_plus": count_14_plus,
                    "count_15": count_15,
                    "hit_histogram": dict(hit_decomposition["hit_histogram"]),
                    "best_hits": best_hits,
                    "average_hits": average_hits,
                    "stability": cross_validation_support,
                    "overfit_risk": max(
                        (
                            window.get("overfit_risk", 0.0)
                            for window in historical_windows.values()
                        ),
                        default=0.0,
                    ),
                    "concentration_risk": concentration_risk,
                    "frequency_maxima_dezena": max_frequency_number,
                    "frequency_maxima_dezena_percentual": round(
                        max_frequency_ratio * 100.0, 4
                    ),
                    "frequency_teto_percentual": 70.0,
                    "validation_threshold": validation_threshold,
                    "target_band": str(validation_rule["target_band"]),
                    "validation_zone_label": str(
                        validation_rule["validation_zone_label"]
                    ),
                    "validation_count_plus": validation_count_plus,
                },
                "next_generation_policy_adjustments": adjustments[
                    "next_generation_policy_adjustments"
                ],
                "local_classification": local_classification,
                "recommended_action": recommended_action,
            },
            "frequency_alerts": (
                [
                    f"frequencia_maxima_dezena_percentual={round(max_frequency_ratio * 100.0, 4)}"
                ]
                if max_frequency_ratio > 0.70
                else []
            ),
            "absence_alerts": [],
            "parity_alerts": [],
            "repetition_alerts": [],
            "sequence_alerts": [],
            "low_high_alerts": [],
            "range_alerts": [],
            **validation_payload,
        }

    def build_strong_near_miss_scientific_memory(
        self,
        *,
        batch_id: str,
        contest: dict[str, Any],
        generation_results: Sequence[dict[str, Any]],
        policy_before: dict[str, Any] | None = None,
        policy_after: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        resolved_batch_id = str(batch_id or "").strip()
        contest_payload = dict(contest or {})
        contest_numbers = _normalize_numbers(
            contest_payload.get("numbers", contest_payload.get("dezenas", []))
        )
        contest_number = _safe_int(
            contest_payload.get(
                "contest_number",
                contest_payload.get("contest_id", contest_payload.get("concurso")),
            ),
            default=None,
        )
        generation_rows = [dict(row or {}) for row in generation_results or []]
        analyzed_generations: list[dict[str, Any]] = []
        for row in generation_rows:
            result_rows = [
                dict(result or {}) for result in row.get("results", []) or []
            ]
            result_hits = [
                int(_safe_int(result.get("hits"), default=0) or 0)
                for result in result_rows
            ]
            if not result_hits and row.get("games"):
                result_hits = [
                    len(
                        set(_normalize_numbers(game.get("numbers", [])))
                        & set(contest_numbers)
                    )
                    for game in row.get("games", []) or []
                    if isinstance(game, dict)
                ]
            if not result_hits:
                continue
            best_hits = max(result_hits, default=0)
            count_10 = sum(1 for hit in result_hits if hit == 10)
            count_11_plus = sum(1 for hit in result_hits if hit >= 11)
            count_12_plus = sum(1 for hit in result_hits if hit >= 12)
            count_13_plus = sum(1 for hit in result_hits if hit >= 13)
            count_14_plus = sum(1 for hit in result_hits if hit >= 14)
            count_15 = sum(1 for hit in result_hits if hit >= 15)
            hit_decomposition = _decompose_hit_counts(result_hits)
            avg_hits = _mean_or_zero([float(hit) for hit in result_hits])
            dispersion = round(
                sqrt(
                    _mean_or_zero([(float(hit) - avg_hits) ** 2 for hit in result_hits])
                )
                if len(result_hits) > 1
                else 0.0,
                4,
            )
            below_9 = sum(1 for hit in result_hits if hit < 9)
            scientific_score = round(
                (
                    best_hits * 100.0
                    + count_10 * 25.0
                    + count_11_plus * 120.0
                    + count_12_plus * 160.0
                    + count_13_plus * 220.0
                    + count_14_plus * 300.0
                    + count_15 * 400.0
                    + avg_hits * 10.0
                    - dispersion * 15.0
                    - below_9 * 4.0
                ),
                4,
            )
            analyzed_generations.append(
                {
                    "generation_event_id": int(row.get("generation_event_id", 0) or 0),
                    "batch_id": str(
                        row.get("batch_id", resolved_batch_id) or resolved_batch_id
                    ),
                    "total_games": int(
                        row.get("total_games", len(result_rows)) or len(result_rows)
                    ),
                    "best_hits": best_hits,
                    "count_10": count_10,
                    "count_11_plus": count_11_plus,
                    "count_12_plus": count_12_plus,
                    "count_13_plus": count_13_plus,
                    "count_14_plus": count_14_plus,
                    "count_15": count_15,
                    "count_10_exact": hit_decomposition["count_10_exact"],
                    "count_11_exact": hit_decomposition["count_11_exact"],
                    "count_12_exact": hit_decomposition["count_12_exact"],
                    "count_13_exact": hit_decomposition["count_13_exact"],
                    "count_14_exact": hit_decomposition["count_14_exact"],
                    "count_15_exact": hit_decomposition["count_15_exact"],
                    "hit_histogram": dict(hit_decomposition["hit_histogram"]),
                    "average_hits": avg_hits,
                    "dispersion": dispersion,
                    "games_below_9": below_9,
                    "scientific_score": scientific_score,
                    "results": result_rows,
                    "games": list(row.get("games") or []),
                    "contest_number": int(
                        row.get("contest_number", contest_number or 0) or 0
                    ),
                    "created_at": str(row.get("created_at", "") or ""),
                }
            )
        strong_candidates = [
            item
            for item in analyzed_generations
            if item["best_hits"] >= 10
            and item["count_10"] >= 7
            and item["count_11_plus"] == 0
        ]
        if not strong_candidates:
            return {}
        strong_candidates = sorted(
            strong_candidates,
            key=lambda item: (
                -int(item["best_hits"]),
                -int(item["count_10"]),
                -int(item["count_11_plus"]),
                -int(item["count_12_plus"]),
                -int(item["count_13_plus"]),
                -float(item["average_hits"]),
                float(item["dispersion"]),
                int(item["games_below_9"]),
                -float(item["scientific_score"]),
                int(item["generation_event_id"]),
            ),
        )
        best_generation = strong_candidates[0]
        secondary_generation = (
            strong_candidates[1] if len(strong_candidates) > 1 else {}
        )
        best_generation_games = [
            dict(game or {}) for game in best_generation.get("games", []) or []
        ]
        best_generation_results = [
            dict(result or {}) for result in best_generation.get("results", []) or []
        ]
        best_generation_result = max(
            best_generation_results,
            key=lambda result: int(_safe_int(result.get("hits"), default=0) or 0),
            default={},
        )
        best_game_numbers = _normalize_numbers(
            best_generation_result.get("numbers", [])
        )
        if not best_game_numbers and best_generation_games:
            best_game_numbers = _normalize_numbers(
                best_generation_games[0].get("numbers", [])
            )
        batch_game_size = (
            len(best_game_numbers)
            if best_game_numbers
            else (
                len(_normalize_numbers(best_generation_games[0].get("numbers", [])))
                if best_generation_games
                else (
                    len(
                        _normalize_numbers(
                            (generation_rows[0].get("games", [{}]) or [{}])[0].get(
                                "numbers", []
                            )
                        )
                    )
                    if generation_rows and generation_rows[0].get("games")
                    else 15
                )
            )
        )
        validation_rule = _scientific_validation_rule(batch_game_size)
        validation_threshold = int(validation_rule["validation_threshold"])
        validation_count_plus = {
            11: int(best_generation.get("count_11_plus", 0) or 0),
            12: int(best_generation.get("count_12_plus", 0) or 0),
            13: int(best_generation.get("count_13_plus", 0) or 0),
        }.get(validation_threshold, int(best_generation.get("count_11_plus", 0) or 0))
        matched_numbers = sorted(set(best_game_numbers).intersection(contest_numbers))
        missing_numbers = sorted(set(contest_numbers).difference(best_game_numbers))
        extra_numbers = sorted(set(best_game_numbers).difference(contest_numbers))
        base_memory = self.build_post_reconciliation_scientific_memory(
            generation_event_id=int(best_generation.get("generation_event_id", 0) or 0),
            batch_id=resolved_batch_id,
            contest=contest_payload,
            games=best_generation_games,
            reconciliation_results=best_generation_results,
            policy_before=policy_before,
            policy_after=policy_after,
        )
        if not base_memory:
            return {}
        best_generation_event_id = int(
            best_generation.get("generation_event_id", 0) or 0
        )
        secondary_generation_event_id = (
            int(secondary_generation.get("generation_event_id", 0) or 0)
            if secondary_generation
            else None
        )
        candidate_generation_event_ids = [
            int(item.get("generation_event_id", 0) or 0)
            for item in strong_candidates
            if int(item.get("generation_event_id", 0) or 0) > 0
        ]
        base_generation_range = dict(base_memory.get("generation_range") or {})
        base_generation_range.update(
            {
                "batch_id": resolved_batch_id,
                "contest_number": contest_number,
                "validation_threshold": validation_threshold,
                "target_band": str(validation_rule["target_band"]),
                "validation_zone_label": str(validation_rule["validation_zone_label"]),
                "best_generation_event_id": best_generation_event_id,
                "secondary_reference_generation_event_id": secondary_generation_event_id,
                "candidate_generation_event_ids": candidate_generation_event_ids,
                "total_generations_analyzed": len(analyzed_generations),
                "best_generation_count_10": int(
                    best_generation.get("count_10", 0) or 0
                ),
                "best_generation_count_11_plus": int(
                    best_generation.get("count_11_plus", 0) or 0
                ),
                "best_generation_best_hits": int(
                    best_generation.get("best_hits", 0) or 0
                ),
                "classification": "NEAR_MISS_FORTE",
                "recommended_action": "recalibrate_from_strong_near_miss_towards_11_plus_and_15",
            }
        )
        base_cross_validation = dict(base_memory.get("cross_validation_summary") or {})
        base_cross_validation.setdefault("scientific_score_components", {})
        base_cross_validation["scientific_score_components"].update(
            {
                "count_10": int(best_generation.get("count_10", 0) or 0),
                "count_11_plus": int(best_generation.get("count_11_plus", 0) or 0),
                "count_12_plus": int(best_generation.get("count_12_plus", 0) or 0),
                "count_13_plus": int(best_generation.get("count_13_plus", 0) or 0),
                "count_14_plus": int(best_generation.get("count_14_plus", 0) or 0),
                "count_15": int(best_generation.get("count_15", 0) or 0),
                "best_hits": int(best_generation.get("best_hits", 0) or 0),
                "average_hits": float(best_generation.get("average_hits", 0.0) or 0.0),
                "dispersion": float(best_generation.get("dispersion", 0.0) or 0.0),
                "games_below_9": int(best_generation.get("games_below_9", 0) or 0),
                "contest_number": contest_number,
                "best_generation_event_id": best_generation_event_id,
            }
        )
        base_cross_validation["historical_expansion_json"] = dict(
            base_memory.get("historical_windows") or {}
        )
        base_cross_validation["ranking_summary"] = {
            "top_generation_event_id": best_generation_event_id,
            "secondary_generation_event_id": secondary_generation_event_id,
            "selected_score": float(
                best_generation.get("scientific_score", 0.0) or 0.0
            ),
            "candidates_scored": len(analyzed_generations),
        }
        base_cross_validation["matched_patterns_json"] = matched_numbers
        base_cross_validation["missing_numbers_json"] = missing_numbers
        base_cross_validation["extra_numbers_json"] = extra_numbers
        next_generation_policy_adjustments = dict(
            base_memory.get("next_generation_policy_adjustments") or {}
        )
        next_generation_policy_adjustments.update(
            {
                "policy_origin": "scientific_strong_near_miss_memory",
                "policy_variant": "recalibrate_from_strong_near_miss_towards_11_plus_and_15",
                "strengthen_11_plus": True,
                "seek_12_plus": True,
                "seek_13_plus": True,
                "preserve_14_15_path": True,
                "recalibrate_from_near_miss_towards_15": True,
            }
        )
        adjusted_policy = dict(
            base_memory.get("policy_after") or policy_after or policy_before or {}
        )
        adjusted_policy["policy_origin"] = "scientific_strong_near_miss_memory"
        adjusted_policy["policy_variant"] = (
            "recalibrate_from_strong_near_miss_towards_11_plus_and_15"
        )
        adjusted_policy["policy_adjustment_reason"] = (
            "recalibrate_from_strong_near_miss_towards_11_plus_and_15"
        )
        adjusted_policy["next_generation_policy_adjustments"] = (
            next_generation_policy_adjustments
        )
        payload = dict(base_memory)
        payload.update(
            {
                "event_type": "post_reconciliation_strong_near_miss",
                "memory_kind": "scientific_strong_near_miss",
                "generation_range": base_generation_range,
                "contest_scope": "SINGLE_CONTEST",
                "local_classification": "NEAR_MISS_FORTE",
                "scientific_classification": "NEAR_MISS_FORTE",
                "confidence_level": "LOW_TO_MEDIUM",
                "requires_cross_validation": True,
                "historical_windows": dict(base_memory.get("historical_windows") or {}),
                "recommended_action": "recalibrate_from_strong_near_miss_towards_11_plus_and_15",
                "policy_adjustment_reason": "recalibrate_from_strong_near_miss_towards_11_plus_and_15",
                "next_generation_policy_adjustments": next_generation_policy_adjustments,
                "scientific_score": float(
                    best_generation.get("scientific_score", 0.0) or 0.0
                ),
                "validation_threshold": validation_threshold,
                "target_band": str(validation_rule["target_band"]),
                "validation_zone_label": str(validation_rule["validation_zone_label"]),
                "validation_count_plus": validation_count_plus,
                "scientific_score_components": {
                    "count_10": int(best_generation.get("count_10", 0) or 0),
                    "count_10_exact": int(
                        best_generation.get("count_10_exact", 0) or 0
                    ),
                    "count_11_exact": int(
                        best_generation.get("count_11_exact", 0) or 0
                    ),
                    "count_12_exact": int(
                        best_generation.get("count_12_exact", 0) or 0
                    ),
                    "count_13_exact": int(
                        best_generation.get("count_13_exact", 0) or 0
                    ),
                    "count_14_exact": int(
                        best_generation.get("count_14_exact", 0) or 0
                    ),
                    "count_15_exact": int(
                        best_generation.get("count_15_exact", 0) or 0
                    ),
                    "count_11_plus": int(best_generation.get("count_11_plus", 0) or 0),
                    "count_12_plus": int(best_generation.get("count_12_plus", 0) or 0),
                    "count_13_plus": int(best_generation.get("count_13_plus", 0) or 0),
                    "count_14_plus": int(best_generation.get("count_14_plus", 0) or 0),
                    "count_15": int(best_generation.get("count_15", 0) or 0),
                    "validation_threshold": validation_threshold,
                    "target_band": str(validation_rule["target_band"]),
                    "validation_zone_label": str(
                        validation_rule["validation_zone_label"]
                    ),
                    "validation_count_plus": validation_count_plus,
                    "hit_histogram": dict(
                        best_generation.get("hit_histogram", {}) or {}
                    ),
                    "best_hits": int(best_generation.get("best_hits", 0) or 0),
                    "average_hits": float(
                        best_generation.get("average_hits", 0.0) or 0.0
                    ),
                    "dispersion": float(best_generation.get("dispersion", 0.0) or 0.0),
                    "games_below_9": int(best_generation.get("games_below_9", 0) or 0),
                    "contest_number": contest_number,
                    "best_generation_event_id": best_generation_event_id,
                    "secondary_reference_generation_event_id": secondary_generation_event_id,
                    "candidate_generation_event_ids": candidate_generation_event_ids,
                },
                "policy_before": dict(policy_before or {}),
                "policy_after": adjusted_policy,
                "policy_id": str(
                    adjusted_policy.get("policy_signature")
                    or adjusted_policy.get("policy_id")
                    or base_memory.get("policy_id")
                    or ""
                ),
                "policy_origin": "scientific_strong_near_miss_memory",
                "policy_variant": "recalibrate_from_strong_near_miss_towards_11_plus_and_15",
                "policy_applied": dict(policy_after or policy_before or {}),
                "best_hit": int(best_generation.get("best_hits", 0) or 0),
                "average_hits": float(best_generation.get("average_hits", 0.0) or 0.0),
                "count_10": int(best_generation.get("count_10", 0) or 0),
                "count_10_exact": int(best_generation.get("count_10_exact", 0) or 0),
                "count_11_exact": int(best_generation.get("count_11_exact", 0) or 0),
                "count_12_exact": int(best_generation.get("count_12_exact", 0) or 0),
                "count_13_exact": int(best_generation.get("count_13_exact", 0) or 0),
                "count_14_exact": int(best_generation.get("count_14_exact", 0) or 0),
                "count_15_exact": int(best_generation.get("count_15_exact", 0) or 0),
                "count_11_plus": int(best_generation.get("count_11_plus", 0) or 0),
                "count_12_plus": int(best_generation.get("count_12_plus", 0) or 0),
                "count_13_plus": int(best_generation.get("count_13_plus", 0) or 0),
                "count_14_plus": int(best_generation.get("count_14_plus", 0) or 0),
                "count_15": int(best_generation.get("count_15", 0) or 0),
                "hit_histogram": dict(best_generation.get("hit_histogram", {}) or {}),
                "main_reason": "near_miss_forte",
                "decision_mode": "OBSERVACAO",
                "approved_for_use": int(validation_count_plus > 0),
                "notes": (
                    f"strong_near_miss=batch_id={resolved_batch_id} | contest_number={contest_number} | "
                    f"best_generation_event_id={best_generation_event_id} | secondary_reference_generation_event_id={secondary_generation_event_id} | "
                    f"count_10={best_generation.get('count_10', 0)} | validation_count_plus={validation_count_plus} | "
                    f"matched_numbers={matched_numbers} | missing_numbers={missing_numbers} | extra_numbers={extra_numbers}"
                ),
                "based_on_strong_near_miss_generation_id": best_generation_event_id,
                "secondary_reference_generation_id": secondary_generation_event_id,
                "candidate_generation_event_ids": candidate_generation_event_ids,
                "total_generations_analyzed": len(analyzed_generations),
            }
        )
        payload["cross_validation_summary"] = base_cross_validation
        payload["policy_adjustment_reason"] = (
            "recalibrate_from_strong_near_miss_towards_11_plus_and_15"
        )
        return payload

    def build_batch_reconciliation_scientific_memory(
        self,
        *,
        batch_id: str,
        contest: dict[str, Any],
        generation_results: Sequence[dict[str, Any]],
        policy_before: dict[str, Any] | None = None,
        policy_after: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        resolved_batch_id = str(batch_id or "").strip()
        contest_payload = dict(contest or {})
        contest_numbers = _normalize_numbers(
            contest_payload.get("numbers", contest_payload.get("dezenas", []))
        )
        contest_number = _safe_int(
            contest_payload.get(
                "contest_number",
                contest_payload.get("contest_id", contest_payload.get("concurso")),
            ),
            default=None,
        )
        generation_rows = [dict(row or {}) for row in generation_results or []]
        analyzed_generations: list[dict[str, Any]] = []
        all_hits: list[int] = []
        for row in generation_rows:
            result_rows = [
                dict(result or {}) for result in row.get("results", []) or []
            ]
            result_hits = [
                int(_safe_int(result.get("hits"), default=0) or 0)
                for result in result_rows
            ]
            if not result_hits and row.get("games"):
                result_hits = [
                    len(
                        set(_normalize_numbers(game.get("numbers", [])))
                        & set(contest_numbers)
                    )
                    for game in row.get("games", []) or []
                    if isinstance(game, dict)
                ]
            if not result_hits:
                continue
            all_hits.extend(result_hits)
            best_hits = max(result_hits, default=0)
            count_10 = sum(1 for hit in result_hits if hit == 10)
            count_11_plus = sum(1 for hit in result_hits if hit >= 11)
            count_12_plus = sum(1 for hit in result_hits if hit >= 12)
            count_13_plus = sum(1 for hit in result_hits if hit >= 13)
            count_14_plus = sum(1 for hit in result_hits if hit >= 14)
            count_15 = sum(1 for hit in result_hits if hit >= 15)
            hit_decomposition = _decompose_hit_counts(result_hits)
            avg_hits = _mean_or_zero([float(hit) for hit in result_hits])
            dispersion = round(
                sqrt(
                    _mean_or_zero([(float(hit) - avg_hits) ** 2 for hit in result_hits])
                )
                if len(result_hits) > 1
                else 0.0,
                4,
            )
            below_9 = sum(1 for hit in result_hits if hit < 9)
            scientific_score = round(
                (
                    best_hits * 100.0
                    + count_10 * 25.0
                    + count_11_plus * 120.0
                    + count_12_plus * 160.0
                    + count_13_plus * 220.0
                    + count_14_plus * 300.0
                    + count_15 * 400.0
                    + avg_hits * 10.0
                    - dispersion * 15.0
                    - below_9 * 4.0
                ),
                4,
            )
            analyzed_generations.append(
                {
                    "generation_event_id": int(row.get("generation_event_id", 0) or 0),
                    "batch_id": str(
                        row.get("batch_id", resolved_batch_id) or resolved_batch_id
                    ),
                    "total_games": int(
                        row.get("total_games", len(result_rows)) or len(result_rows)
                    ),
                    "best_hits": best_hits,
                    "count_10": count_10,
                    "count_11_plus": count_11_plus,
                    "count_12_plus": count_12_plus,
                    "count_13_plus": count_13_plus,
                    "count_14_plus": count_14_plus,
                    "count_15": count_15,
                    "count_10_exact": hit_decomposition["count_10_exact"],
                    "count_11_exact": hit_decomposition["count_11_exact"],
                    "count_12_exact": hit_decomposition["count_12_exact"],
                    "count_13_exact": hit_decomposition["count_13_exact"],
                    "count_14_exact": hit_decomposition["count_14_exact"],
                    "count_15_exact": hit_decomposition["count_15_exact"],
                    "hit_histogram": dict(hit_decomposition["hit_histogram"]),
                    "average_hits": avg_hits,
                    "dispersion": dispersion,
                    "games_below_9": below_9,
                    "scientific_score": scientific_score,
                    "results": result_rows,
                    "games": list(row.get("games") or []),
                    "contest_number": int(
                        row.get("contest_number", contest_number or 0) or 0
                    ),
                    "created_at": str(row.get("created_at", "") or ""),
                }
            )
        if not analyzed_generations:
            return {}
        total_generations = len(analyzed_generations)
        total_games_checked = sum(
            int(item.get("total_games", 0) or 0) for item in analyzed_generations
        )
        global_best_hits = max(
            (item.get("best_hits", 0) or 0 for item in analyzed_generations), default=0
        )
        global_count_10 = sum(
            item.get("count_10", 0) or 0 for item in analyzed_generations
        )
        global_count_11_plus = sum(
            item.get("count_11_plus", 0) or 0 for item in analyzed_generations
        )
        global_count_12_plus = sum(
            item.get("count_12_plus", 0) or 0 for item in analyzed_generations
        )
        global_count_13_plus = sum(
            item.get("count_13_plus", 0) or 0 for item in analyzed_generations
        )
        global_count_14_plus = sum(
            item.get("count_14_plus", 0) or 0 for item in analyzed_generations
        )
        global_count_15 = sum(
            item.get("count_15", 0) or 0 for item in analyzed_generations
        )
        batch_game_size = (
            len(
                _normalize_numbers(
                    (generation_rows[0].get("games", [{}]) or [{}])[0].get(
                        "numbers", []
                    )
                )
            )
            if generation_rows and generation_rows[0].get("games")
            else 15
        )
        validation_rule = _scientific_validation_rule(batch_game_size)
        validation_threshold = int(validation_rule["validation_threshold"])
        validation_count_plus = {
            11: global_count_11_plus,
            12: global_count_12_plus,
            13: global_count_13_plus,
        }.get(validation_threshold, global_count_11_plus)
        validation_payload = _scientific_validation_payload(
            game_size=batch_game_size,
            hit_decomposition=_decompose_hit_counts(all_hits),
            best_hits=global_best_hits,
            validation_count_plus=validation_count_plus,
        )
        average_hits = _mean_or_zero([float(value) for value in all_hits])
        dispersion = round(
            sqrt(_mean_or_zero([(float(hit) - average_hits) ** 2 for hit in all_hits]))
            if len(all_hits) > 1
            else 0.0,
            4,
        )
        strong_batch = (
            total_games_checked >= 100
            and global_best_hits >= max(10, validation_threshold - 1)
            and validation_count_plus == 0
            and global_count_10 > 0
        )
        batch_classification = (
            "STRONG_NEAR_MISS_BATCH"
            if strong_batch
            else ("NEAR_MISS_GLOBAL" if global_best_hits >= 10 else "BATCH_REVIEW")
        )
        recommended_action = (
            "recalibrate_from_strong_near_miss_towards_11_plus_and_15"
            if batch_classification == "STRONG_NEAR_MISS_BATCH"
            else "recalibrate_from_near_miss_towards_15"
        )
        analyzed_generations = sorted(
            analyzed_generations,
            key=lambda item: (
                -int(item["best_hits"]),
                -int(item["count_10"]),
                -int(item["count_11_plus"]),
                -int(item["count_12_plus"]),
                -int(item["count_13_plus"]),
                -float(item["average_hits"]),
                float(item["dispersion"]),
                int(item["games_below_9"]),
                -float(item["scientific_score"]),
                int(item["generation_event_id"]),
            ),
        )
        best_generation = analyzed_generations[0]
        secondary_generation_event_ids = [
            int(item.get("generation_event_id", 0) or 0)
            for item in analyzed_generations[1:4]
            if int(item.get("generation_event_id", 0) or 0) > 0
        ]
        best_generation_games = [
            dict(game or {}) for game in best_generation.get("games", []) or []
        ]
        best_generation_results = [
            dict(result or {}) for result in best_generation.get("results", []) or []
        ]
        best_generation_result = max(
            best_generation_results,
            key=lambda result: int(_safe_int(result.get("hits"), default=0) or 0),
            default={},
        )
        best_game_numbers = _normalize_numbers(
            best_generation_result.get("numbers", [])
        )
        if not best_game_numbers and best_generation_games:
            best_game_numbers = _normalize_numbers(
                best_generation_games[0].get("numbers", [])
            )
        matched_numbers = sorted(set(best_game_numbers).intersection(contest_numbers))
        missing_numbers = sorted(set(contest_numbers).difference(best_game_numbers))
        extra_numbers = sorted(set(best_game_numbers).difference(contest_numbers))
        base_memory = self.build_post_reconciliation_scientific_memory(
            generation_event_id=int(best_generation.get("generation_event_id", 0) or 0),
            batch_id=resolved_batch_id,
            contest=contest_payload,
            games=best_generation_games,
            reconciliation_results=best_generation_results,
            policy_before=policy_before,
            policy_after=policy_after,
        )
        if not base_memory:
            return {}
        best_generation_event_id = int(
            best_generation.get("generation_event_id", 0) or 0
        )
        generation_event_ids = [
            int(item.get("generation_event_id", 0) or 0)
            for item in analyzed_generations
            if int(item.get("generation_event_id", 0) or 0) > 0
        ]
        generation_details: list[dict[str, Any]] = []
        ten_hit_game_details: list[dict[str, Any]] = []
        eleven_plus_game_details: list[dict[str, Any]] = []
        for generation in analyzed_generations:
            generation_id = int(generation.get("generation_event_id", 0) or 0)
            generation_games = [
                dict(game or {}) for game in generation.get("games", []) or []
            ]
            generation_results = [
                dict(result or {}) for result in generation.get("results", []) or []
            ]
            generation_ten_hit_games: list[dict[str, Any]] = []
            generation_eleven_plus_games: list[dict[str, Any]] = []
            for index, result in enumerate(generation_results):
                hits = int(_safe_int(result.get("hits"), default=0) or 0)
                source_game = (
                    generation_games[index] if index < len(generation_games) else {}
                )
                numbers = _normalize_numbers(
                    result.get("numbers", source_game.get("numbers", []))
                )
                source_context = dict(source_game.get("context_json") or {})
                detail = {
                    "generation_event_id": generation_id,
                    "batch_id": str(
                        generation.get("batch_id", resolved_batch_id)
                        or resolved_batch_id
                    ),
                    "game_index": int(
                        result.get(
                            "game_index", source_game.get("game_index", index + 1)
                        )
                        or index + 1
                    ),
                    "game_signature": str(
                        result.get("game_signature")
                        or source_game.get("game_signature")
                        or ""
                    ),
                    "numbers": numbers,
                    "hits": hits,
                    "matched_numbers": list(result.get("matched_numbers", []) or []),
                    "missing_draw_numbers": list(
                        result.get("missing_draw_numbers", []) or []
                    ),
                    "extra_numbers": list(result.get("extra_numbers", []) or []),
                    "score_original": float(
                        result.get("score_original", source_game.get("score", 0.0))
                        or 0.0
                    ),
                    "perfil": str(
                        result.get("perfil")
                        or source_game.get("perfil")
                        or source_game.get("profile_type", "")
                        or ""
                    ),
                    "profile_type": str(
                        result.get("profile_type")
                        or source_game.get("profile_type", "")
                        or ""
                    ),
                    "contest_number": int(
                        generation.get("contest_number", contest_number or 0) or 0
                    ),
                    "source_memory_id": _safe_int(
                        source_context.get(
                            "based_on_memory_id",
                            source_context.get(
                                "source_memory_id", source_context.get("memory_id")
                            ),
                        ),
                        default=None,
                    ),
                    "based_on_memory_kind": str(
                        source_context.get(
                            "based_on_memory_kind",
                            source_context.get("memory_kind", ""),
                        )
                        or ""
                    ),
                    "based_on_batch_id": str(
                        source_context.get(
                            "based_on_batch_id", source_context.get("batch_id", "")
                        )
                        or ""
                    ),
                    "hit_classification": (
                        f"EXACT_{hits}"
                        if 11 <= hits <= 15
                        else ("NEAR_MISS_10" if hits == 10 else "BELOW_PRIZE")
                    ),
                }
                if hits == 10:
                    generation_ten_hit_games.append(detail)
                    ten_hit_game_details.append(detail)
                if hits >= 11:
                    generation_eleven_plus_games.append(detail)
                    eleven_plus_game_details.append(detail)
            generation_details.append(
                {
                    "generation_event_id": generation_id,
                    "batch_id": str(
                        generation.get("batch_id", resolved_batch_id)
                        or resolved_batch_id
                    ),
                    "total_games": int(
                        generation.get("total_games", len(generation_results))
                        or len(generation_results)
                    ),
                    "best_hits": int(generation.get("best_hits", 0) or 0),
                    "count_10": int(generation.get("count_10", 0) or 0),
                    "count_11_plus": int(generation.get("count_11_plus", 0) or 0),
                    "count_12_plus": int(generation.get("count_12_plus", 0) or 0),
                    "count_13_plus": int(generation.get("count_13_plus", 0) or 0),
                    "count_14_plus": int(generation.get("count_14_plus", 0) or 0),
                    "count_15": int(generation.get("count_15", 0) or 0),
                    "average_hits": float(generation.get("average_hits", 0.0) or 0.0),
                    "dispersion": float(generation.get("dispersion", 0.0) or 0.0),
                    "games_below_9": int(generation.get("games_below_9", 0) or 0),
                    "scientific_score": float(
                        generation.get("scientific_score", 0.0) or 0.0
                    ),
                    "contest_number": int(
                        generation.get("contest_number", contest_number or 0) or 0
                    ),
                    "created_at": str(generation.get("created_at", "") or ""),
                    "games_with_10_hits": generation_ten_hit_games,
                    "games_with_11_plus": generation_eleven_plus_games,
                }
            )
        historical_windows = dict(base_memory.get("historical_windows") or {})
        if not historical_windows:
            historical_windows = {
                "10": {
                    "contest_scope": "SINGLE_CONTEST",
                    "window_size": 10,
                    "contest_count": min(10, total_generations),
                    "contest_numbers": generation_event_ids[-10:],
                    "best_hits_average": average_hits,
                    "best_hits_median": average_hits,
                    "best_hits_min": global_best_hits,
                    "best_hits_max": global_best_hits,
                    "count_10": global_count_10,
                    "count_11_plus": global_count_11_plus,
                    "count_12_plus": global_count_12_plus,
                    "count_13_plus": global_count_13_plus,
                    "count_14_plus": global_count_14_plus,
                    "count_15": global_count_15,
                    "average_hits_per_contest": average_hits,
                    "stability": 0.0,
                    "overfit_risk": 0.0,
                    "scientific_score": 0.0,
                }
            }
        batch_generation_range = {
            "batch_id": resolved_batch_id,
            "contest_number": contest_number,
            "generation_event_ids": generation_event_ids,
            "first_generation_event_id": min(generation_event_ids)
            if generation_event_ids
            else None,
            "last_generation_event_id": max(generation_event_ids)
            if generation_event_ids
            else None,
            "validation_threshold": validation_threshold,
            "target_band": str(validation_rule["target_band"]),
            "validation_zone_label": str(validation_rule["validation_zone_label"]),
            "best_generations": [best_generation_event_id]
            + [item for item in secondary_generation_event_ids if item > 0],
            "total_generations": total_generations,
            "total_games_checked": total_games_checked,
            "global_best_hits": global_best_hits,
            "global_count_10": global_count_10,
            "global_count_11_plus": global_count_11_plus,
            "global_count_12_plus": global_count_12_plus,
            "global_count_13_plus": global_count_13_plus,
            "global_count_14_plus": global_count_14_plus,
            "global_count_15": global_count_15,
            "count_10_exact": global_count_10,
            "count_11_exact": max(0, global_count_11_plus - global_count_12_plus),
            "count_12_exact": max(0, global_count_12_plus - global_count_13_plus),
            "count_13_exact": max(0, global_count_13_plus - global_count_14_plus),
            "count_14_exact": max(0, global_count_14_plus - global_count_15),
            "count_15_exact": global_count_15,
            "count_11_plus": global_count_11_plus,
            "count_12_plus": global_count_12_plus,
            "count_13_plus": global_count_13_plus,
            "count_14_plus": global_count_14_plus,
            "count_15": global_count_15,
            "hit_histogram": dict(_decompose_hit_counts(all_hits)["hit_histogram"]),
            "best_generation_event_id": best_generation_event_id,
            "best_generation_count_10": int(best_generation.get("count_10", 0) or 0),
            "secondary_generation_event_ids": secondary_generation_event_ids,
            "classification": batch_classification,
            "confidence_level": "MEDIUM_HIGH" if strong_batch else "LOW_TO_MEDIUM",
            "requires_cross_validation": True,
            "overfit_risk": round(min(1.0, dispersion / 5.0), 4),
            "recommended_action": recommended_action,
            **validation_payload,
        }
        best_generation_details = [
            detail
            for detail in generation_details
            if int(detail.get("generation_event_id", 0) or 0)
            in (
                [best_generation_event_id]
                + [item for item in secondary_generation_event_ids if item > 0]
            )
        ]
        batch_generation_range.update(
            {
                "generation_details": generation_details,
                "best_generation_details": best_generation_details,
                "games_with_10_hits": ten_hit_game_details,
                "games_with_11_plus": eleven_plus_game_details,
            }
        )
        next_generation_policy_adjustments = dict(
            base_memory.get("next_generation_policy_adjustments") or {}
        )
        next_generation_policy_adjustments.update(
            {
                "policy_origin": "scientific_batch_reconciliation_memory",
                "policy_variant": "batch_near_miss_consolidation",
                "strengthen_11_plus": True,
                "seek_12_plus": True,
                "seek_13_plus": True,
                "preserve_14_15_path": True,
                "recalibrate_from_strong_near_miss_towards_11_plus_and_15": strong_batch,
            }
        )
        adjusted_policy = dict(
            base_memory.get("policy_after") or policy_after or policy_before or {}
        )
        adjusted_policy["policy_origin"] = "scientific_batch_reconciliation_memory"
        adjusted_policy["policy_variant"] = "batch_near_miss_consolidation"
        adjusted_policy["policy_adjustment_reason"] = recommended_action
        adjusted_policy["next_generation_policy_adjustments"] = (
            next_generation_policy_adjustments
        )
        payload = dict(base_memory)
        payload.update(
            {
                "event_type": "post_reconciliation_scientific_batch_expansion",
                "memory_kind": "scientific_batch_reconciliation",
                "generation_range": batch_generation_range,
                "contest_scope": "BATCH_CONSOLIDATED",
                "local_classification": batch_classification,
                "scientific_classification": batch_classification,
                "confidence_level": batch_generation_range["confidence_level"],
                "requires_cross_validation": True,
                "validation_threshold": validation_threshold,
                "target_band": str(validation_rule["target_band"]),
                "validation_zone_label": str(validation_rule["validation_zone_label"]),
                "historical_windows": historical_windows,
                "recommended_action": recommended_action,
                "policy_adjustment_reason": recommended_action,
                "next_generation_policy_adjustments": next_generation_policy_adjustments,
                "scientific_score": _scientific_tier_weighted_score(
                    count_10=global_count_10,
                    count_11_plus=global_count_11_plus,
                    count_12_plus=global_count_12_plus,
                    count_13_plus=global_count_13_plus,
                    count_14_plus=global_count_14_plus,
                    count_15=global_count_15,
                    best_hits=global_best_hits,
                    average_hits=average_hits,
                    stability=1.0 - min(1.0, dispersion / 5.0),
                    overfit_risk=batch_generation_range["overfit_risk"],
                    concentration_risk=0.0 if global_count_10 else 1.0,
                ),
                "scientific_score_components": {
                    "count_10": global_count_10,
                    "count_10_exact": global_count_10,
                    "count_11_exact": max(
                        0, global_count_11_plus - global_count_12_plus
                    ),
                    "count_12_exact": max(
                        0, global_count_12_plus - global_count_13_plus
                    ),
                    "count_13_exact": max(
                        0, global_count_13_plus - global_count_14_plus
                    ),
                    "count_14_exact": max(0, global_count_14_plus - global_count_15),
                    "count_15_exact": global_count_15,
                    "count_11_plus": global_count_11_plus,
                    "count_12_plus": global_count_12_plus,
                    "count_13_plus": global_count_13_plus,
                    "count_14_plus": global_count_14_plus,
                    "count_15": global_count_15,
                    "hit_histogram": dict(
                        _decompose_hit_counts(all_hits)["hit_histogram"]
                    ),
                    "best_hits": global_best_hits,
                    "average_hits": average_hits,
                    "dispersion": dispersion,
                    "global_games_below_9": sum(1 for hit in all_hits if hit < 9),
                    "generation_event_ids": generation_event_ids,
                    "best_generation_event_id": best_generation_event_id,
                    "secondary_generation_event_ids": secondary_generation_event_ids,
                    "total_generations": total_generations,
                    "total_games_checked": total_games_checked,
                    "validation_threshold": validation_threshold,
                    "target_band": str(validation_rule["target_band"]),
                    "validation_zone_label": str(
                        validation_rule["validation_zone_label"]
                    ),
                    "validation_count_plus": validation_count_plus,
                },
                "policy_before": dict(policy_before or {}),
                "policy_after": adjusted_policy,
                "policy_id": str(
                    adjusted_policy.get("policy_signature")
                    or adjusted_policy.get("policy_id")
                    or base_memory.get("policy_id")
                    or ""
                ),
                "policy_origin": "scientific_batch_reconciliation_memory",
                "policy_variant": "batch_near_miss_consolidation",
                "policy_applied": dict(policy_after or policy_before or {}),
                "best_hit": global_best_hits,
                "average_hits": average_hits,
                "count_10": global_count_10,
                "count_10_exact": global_count_10,
                "count_11_exact": max(0, global_count_11_plus - global_count_12_plus),
                "count_12_exact": max(0, global_count_12_plus - global_count_13_plus),
                "count_13_exact": max(0, global_count_13_plus - global_count_14_plus),
                "count_14_exact": max(0, global_count_14_plus - global_count_15),
                "count_15_exact": global_count_15,
                "count_11_plus": global_count_11_plus,
                "count_12_plus": global_count_12_plus,
                "count_13_plus": global_count_13_plus,
                "count_14_plus": global_count_14_plus,
                "count_15": global_count_15,
                "hit_histogram": dict(_decompose_hit_counts(all_hits)["hit_histogram"]),
                "main_reason": batch_classification.lower(),
                "decision_mode": "OBSERVACAO",
                "approved_for_use": int(validation_count_plus > 0),
                "notes": (
                    f"batch_reconciliation=batch_id={resolved_batch_id} | contest_number={contest_number} | "
                    f"generation_event_ids={generation_event_ids} | best_generation_event_id={best_generation_event_id} | "
                    f"global_count_10={global_count_10} | global_count_11_plus={global_count_11_plus}"
                ),
                "based_on_batch_id": resolved_batch_id,
                "based_on_post_reconciliation_memory_id": base_memory.get(
                    "based_on_post_reconciliation_memory_id"
                ),
                "best_generation_event_id": best_generation_event_id,
                "best_generations": [best_generation_event_id]
                + [item for item in secondary_generation_event_ids if item > 0],
                "best_generation_count_10": int(
                    best_generation.get("count_10", 0) or 0
                ),
                "secondary_generation_event_ids": secondary_generation_event_ids,
                "generation_event_ids": generation_event_ids,
                "total_generations": total_generations,
                "total_games_checked": total_games_checked,
                "matched_patterns_json": matched_numbers,
                "missing_numbers_json": missing_numbers,
                "extra_numbers_json": extra_numbers,
                "generation_details": generation_details,
                "best_generation_details": best_generation_details,
                "games_with_10_hits": ten_hit_game_details,
                "games_with_11_plus": eleven_plus_game_details,
                "near_miss_generation_ranking": analyzed_generations,
                "historical_expansion_json": historical_windows,
            }
        )
        payload["cross_validation_summary"] = {
            "contest_scope": "BATCH_CONSOLIDATED",
            "confidence_level": batch_generation_range["confidence_level"],
            "requires_cross_validation": True,
            "validation_threshold": validation_threshold,
            "target_band": str(validation_rule["target_band"]),
            "validation_zone_label": str(validation_rule["validation_zone_label"]),
            "historical_windows": historical_windows,
            "scientific_score": payload["scientific_score"],
            "scientific_score_components": payload["scientific_score_components"],
            "next_generation_policy_adjustments": next_generation_policy_adjustments,
            "local_classification": batch_classification,
            "recommended_action": recommended_action,
            "ranking_summary": {
                "best_generation_event_id": best_generation_event_id,
                "secondary_generation_event_ids": secondary_generation_event_ids,
                "best_generations": [best_generation_event_id]
                + [item for item in secondary_generation_event_ids if item > 0],
                "total_generations": total_generations,
                "total_games_checked": total_games_checked,
            },
            "generation_details": generation_details,
            "best_generation_details": best_generation_details,
            "games_with_10_hits": ten_hit_game_details,
            "near_miss_generation_ranking": analyzed_generations,
            "matched_patterns_json": matched_numbers,
            "missing_numbers_json": missing_numbers,
            "extra_numbers_json": extra_numbers,
        }
        payload["policy_adjustment_reason"] = recommended_action
        payload.update(validation_payload)
        return payload

    def discover_scientific_generation_policy(
        self,
        game_size: int,
        *,
        candidate_limit: int = 120,
    ) -> dict[str, Any]:
        resolved_game_size = max(2, min(int(game_size or 15), 25))
        profile_window = (
            max(20, min(len(self.contests), max(60, resolved_game_size * 4)))
            if self.contests
            else 0
        )
        profile = (
            self.build_scientific_profile(window_size=profile_window)
            if self.contests
            else {}
        )
        history_count = int(
            profile.get("contest_count", len(self.contests)) or len(self.contests)
        )
        frequency_map = {
            int(number): int(amount)
            for number, amount in (profile.get("number_frequency", {}) or {}).items()
            if int(_safe_int(number, default=0) or 0) > 0
        }
        dominant_numbers = [
            int(item.get("number", 0) or 0)
            for item in profile.get("dominant_numbers", [])
            if int(item.get("number", 0) or 0) > 0
        ]
        core_numbers = (
            tuple(dominant_numbers[:4])
            if dominant_numbers
            else tuple(range(1, min(4, resolved_game_size) + 1))
        )
        discouraged_numbers = tuple(
            sorted(
                {number for number in range(1, 26)} - set(core_numbers),
                key=lambda number: (
                    int(profile.get("number_frequency", {}).get(str(number), 0) or 0),
                    number,
                ),
            )[:6]
        )
        raw_repeat_mean = float(
            profile.get("average_repetition", max(1.0, resolved_game_size / 2))
            or max(1.0, resolved_game_size / 2)
        )
        repeat_mean = min(raw_repeat_mean, max(1.0, resolved_game_size / 2))
        raw_sequence_mean = float(
            profile.get("average_sequence_max", max(4.0, resolved_game_size / 3))
            or max(4.0, resolved_game_size / 3)
        )
        sequence_mean = min(raw_sequence_mean, max(4.0, resolved_game_size / 3 + 1.0))
        coverage_mean = float(profile.get("average_coverage", 0.35) or 0.35)
        entropy_mean = float(profile.get("average_entropy", 0.35) or 0.35)
        average_odd = float(
            profile.get("average_parity_odd", (resolved_game_size + 1) / 2)
            or ((resolved_game_size + 1) / 2)
        )
        average_even = float(
            profile.get("average_parity_even", resolved_game_size / 2)
            or (resolved_game_size / 2)
        )
        # Expandir variância: permitir delta de -2/+2 em relação à média (ex: se média=9, aceitar 7 a 11)
        # Isso garante que a faixa de 8 repetições (muito comum) seja incluída no pool principal.
        repeat_floor = max(0, int(round(repeat_mean)) - 2)
        repeat_ceiling = min(resolved_game_size, int(round(repeat_mean)) + 2)
        sequence_cap = max(4, int(round(sequence_mean + 1.0)))
        coverage_floor = max(
            0.80, min(0.95, round(coverage_mean, 2))
        )  # Elevado de 0.30-0.75 para 0.80-0.95 (M-OPS-083)
        entropy_floor = max(0.25, min(0.75, round(entropy_mean, 2)))
        max_frequency_cap = 0.70
        min_frequency_floor = 0.20
        odd_target = max(0, min(resolved_game_size, int(round(average_odd))))
        even_target = resolved_game_size - odd_target
        if even_target < 0:
            even_target = max(0, min(resolved_game_size, int(round(average_even))))
            odd_target = resolved_game_size - even_target
        preferred_pairs = []
        base_pair = (odd_target, even_target)
        if sum(base_pair) == resolved_game_size:
            preferred_pairs.append(base_pair)
            if base_pair[0] != base_pair[1]:
                preferred_pairs.append((base_pair[1], base_pair[0]))
        if not preferred_pairs:
            preferred_pairs = [
                (
                    resolved_game_size // 2,
                    resolved_game_size - (resolved_game_size // 2),
                )
            ]
        allowed_pairs = []
        for odd_count, even_count in preferred_pairs:
            # Expandir delta para +/- 2 para permitir variância natural (ex: 6 e 9 ímpares quando a média é 7 ou 8)
            for delta in (0, -1, 1, -2, 2):
                candidate_odd = max(0, min(resolved_game_size, odd_count + delta))
                candidate_even = resolved_game_size - candidate_odd
                pair = (candidate_odd, candidate_even)
                if sum(pair) == resolved_game_size and pair not in allowed_pairs:
                    allowed_pairs.append(pair)
        if not allowed_pairs:
            allowed_pairs = list(preferred_pairs)

        def _unique_pairs(pairs: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
            unique: list[tuple[int, int]] = []
            for pair in pairs:
                normalized_pair = (int(pair[0]), int(pair[1]))
                if normalized_pair not in unique:
                    unique.append(normalized_pair)
            return unique

        preferred_pairs = _unique_pairs(preferred_pairs)
        allowed_pairs = _unique_pairs(allowed_pairs)

        def _paired_profile_ratios(
            pairs: Sequence[tuple[int, int]],
        ) -> dict[tuple[int, int], float]:
            if not pairs:
                return {}
            if len(pairs) == 1:
                return {tuple(pairs[0]): 1.0}
            weights = [1.0 / (index + 1) for index in range(len(pairs))]
            total = sum(weights) or 1.0
            return {
                tuple(pair): round(weight / total, 4)
                for pair, weight in zip(pairs, weights, strict=False)
            }

        def _policy_signature(policy: Mapping[str, Any]) -> str:
            payload = {
                "game_size": resolved_game_size,
                "repeat_min": int(policy.get("repeat_min", 0) or 0),
                "repeat_max": int(policy.get("repeat_max", 0) or 0),
                "preferred_parity_pairs": list(
                    policy.get("preferred_parity_pairs", []) or []
                ),
                "allowed_parity_pairs": list(
                    policy.get("allowed_parity_pairs", []) or []
                ),
                "sequence_max": int(policy.get("sequence_max", 0) or 0),
                "coverage_min": float(policy.get("coverage_min", 0.0) or 0.0),
                "entropy_min": float(policy.get("entropy_min", 0.0) or 0.0),
                "core_numbers": list(policy.get("core_numbers", []) or []),
                "discouraged_numbers": list(
                    policy.get("discouraged_numbers", []) or []
                ),
                "max_frequency_ratio": float(
                    policy.get("max_frequency_ratio", 0.0) or 0.0
                ),
                "min_frequency_ratio": float(
                    policy.get("min_frequency_ratio", 0.0) or 0.0
                ),
            }
            return hashlib.sha1(
                json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
            ).hexdigest()[:12]

        def _canonical_policy(
            *,
            repeat_min: int,
            repeat_max: int,
            preferred: Sequence[tuple[int, int]],
            allowed: Sequence[tuple[int, int]],
            sequence_max: int,
            coverage_min: float,
            entropy_min: float,
            max_frequency_ratio: float,
            min_frequency_ratio: float,
            notes: Sequence[str],
            variant_name: str,
        ) -> dict[str, Any]:
            policy = ScientificGenerationPolicy(
                game_size=resolved_game_size,
                window_size=int(profile_window or len(self.contests)),
                source=str(
                    profile.get("source", "imported_contests") or "imported_contests"
                ),
                contest_count=int(
                    profile.get("contest_count", len(self.contests))
                    or len(self.contests)
                ),
                repeat_min=max(0, min(resolved_game_size, int(repeat_min))),
                repeat_max=max(0, min(resolved_game_size, int(repeat_max))),
                preferred_parity_pairs=tuple(tuple(pair) for pair in preferred),
                allowed_parity_pairs=tuple(tuple(pair) for pair in allowed),
                sequence_max=max(1, min(resolved_game_size, int(sequence_max))),
                coverage_min=float(coverage_min),
                entropy_min=float(entropy_min),
                core_numbers=tuple(int(number) for number in core_numbers),
                discouraged_numbers=tuple(
                    int(number) for number in discouraged_numbers
                ),
                max_frequency_ratio=float(max_frequency_ratio),
                min_frequency_ratio=float(min_frequency_ratio),
                preferred_profile_ratios=_paired_profile_ratios(preferred),
                notes=tuple(notes),
            ).as_dict()
            policy["policy_variant"] = variant_name
            policy["policy_origin"] = "automatic_scientific_discovery"
            policy["policy_signature"] = hashlib.sha1(
                json.dumps(policy, sort_keys=True, ensure_ascii=False).encode("utf-8")
            ).hexdigest()[:12]
            return policy

        base_repeat_center = int(round(repeat_mean or max(1.0, resolved_game_size / 2)))
        observed_max_frequency = (
            min(
                0.80,
                max(
                    0.55,
                    round(
                        (max(frequency_map.values()) / max(1, history_count)) + 0.05, 2
                    ),
                ),
            )
            if frequency_map
            else max_frequency_cap
        )
        observed_min_frequency = (
            min(
                0.30,
                max(
                    0.10,
                    round(
                        (
                            min(
                                (
                                    amount
                                    for amount in frequency_map.values()
                                    if amount > 0
                                ),
                                default=0,
                            )
                            / max(1, history_count)
                        )
                        or 0.20,
                        2,
                    ),
                ),
            )
            if frequency_map
            else min_frequency_floor
        )
        repeat_min_candidates = _unique_ints(
            [
                repeat_floor - 1,
                repeat_floor,
                repeat_floor + 1,
                max(0, base_repeat_center - 1),
                base_repeat_center,
            ],
            lower=0,
            upper=resolved_game_size,
        )
        repeat_max_candidates = _unique_ints(
            [
                repeat_ceiling - 1,
                repeat_ceiling,
                repeat_ceiling + 1,
                max(0, base_repeat_center + 1),
                min(resolved_game_size, base_repeat_center + 2),
            ],
            lower=0,
            upper=resolved_game_size,
        )
        sequence_candidates = _unique_ints(
            [
                sequence_cap - 2,
                sequence_cap - 1,
                sequence_cap,
                sequence_cap + 1,
                sequence_cap + 2,
            ],
            lower=4,
            upper=resolved_game_size,
        )
        coverage_candidates = _unique_float_values(
            [
                coverage_floor - 0.08,
                coverage_floor - 0.04,
                coverage_floor,
                coverage_floor + 0.04,
                coverage_floor + 0.08,
                coverage_mean,
                0.40,
                0.45,
                0.50,
            ],
            lower=0.30,
            upper=0.85,
        )
        entropy_candidates = _unique_float_values(
            [
                entropy_floor - 0.08,
                entropy_floor - 0.04,
                entropy_floor,
                entropy_floor + 0.04,
                entropy_floor + 0.08,
                entropy_mean,
                0.35,
                0.40,
                0.45,
            ],
            lower=0.25,
            upper=0.85,
        )
        max_frequency_candidates = _unique_float_values(
            [
                max_frequency_cap - 0.10,
                max_frequency_cap - 0.05,
                max_frequency_cap,
                observed_max_frequency,
                min(0.80, max(0.55, observed_max_frequency + 0.05)),
            ],
            lower=0.50,
            upper=0.85,
        )
        min_frequency_candidates = _unique_float_values(
            [
                min_frequency_floor - 0.05,
                min_frequency_floor,
                min_frequency_floor + 0.05,
                observed_min_frequency,
                max(0.10, min(0.30, observed_min_frequency + 0.05)),
            ],
            lower=0.05,
            upper=0.35,
        )
        parity_families = [preferred_pairs, allowed_pairs]
        if not parity_families[0]:
            parity_families[0] = [
                (
                    resolved_game_size // 2,
                    resolved_game_size - (resolved_game_size // 2),
                )
            ]
        if not parity_families[1]:
            parity_families[1] = list(parity_families[0])

        base_policy = _canonical_policy(
            repeat_min=repeat_floor,
            repeat_max=repeat_ceiling,
            preferred=preferred_pairs,
            allowed=allowed_pairs,
            sequence_max=sequence_cap,
            coverage_min=coverage_floor,
            entropy_min=entropy_floor,
            max_frequency_ratio=observed_max_frequency
            if "observed_max_frequency" in locals()
            else max_frequency_cap,
            min_frequency_ratio=observed_min_frequency
            if "observed_min_frequency" in locals()
            else min_frequency_floor,
            notes=("automatic_discovery_seed", "derived_from_official_history"),
            variant_name="history_profile_seed",
        )
        base_policy = _apply_scientific_15_vnext_policy(base_policy)

        def _policy_to_candidate_params(policy: dict[str, Any]) -> dict[str, Any]:
            preferred_raw = policy.get("preferred_parity_pairs", []) or []
            allowed_raw = policy.get("allowed_parity_pairs", []) or []
            preferred_pairs_local: list[tuple[int, int]] = []
            allowed_pairs_local: list[tuple[int, int]] = []
            for pair in preferred_raw:
                if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                    preferred_pairs_local.append((int(pair[0]), int(pair[1])))
            for pair in allowed_raw:
                if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                    allowed_pairs_local.append((int(pair[0]), int(pair[1])))
            if not preferred_pairs_local:
                preferred_pairs_local = list(preferred_pairs)
            if not allowed_pairs_local:
                allowed_pairs_local = list(allowed_pairs)
            return {
                "repeat_min": int(
                    policy.get("repeat_min", repeat_floor) or repeat_floor
                ),
                "repeat_max": int(
                    policy.get("repeat_max", repeat_ceiling) or repeat_ceiling
                ),
                "preferred": preferred_pairs_local,
                "allowed": allowed_pairs_local,
                "sequence_max": int(
                    policy.get("sequence_max", sequence_cap) or sequence_cap
                ),
                "coverage_min": float(
                    policy.get("coverage_min", coverage_floor) or coverage_floor
                ),
                "entropy_min": float(
                    policy.get("entropy_min", entropy_floor) or entropy_floor
                ),
                "max_frequency_ratio": float(
                    policy.get("max_frequency_ratio", observed_max_frequency)
                    or observed_max_frequency
                ),
                "min_frequency_ratio": float(
                    policy.get("min_frequency_ratio", observed_min_frequency)
                    or observed_min_frequency
                ),
                "notes": tuple(str(note) for note in policy.get("notes", ()) or ()),
            }

        memory_rows = self._load_scientific_memory_rows(
            limit=max(5, int(candidate_limit or 6))
        )
        decision_rows = self._load_scientific_calibration_decisions(
            limit=max(5, int(candidate_limit or 6))
        )
        latest_memory = memory_rows[0] if memory_rows else {}
        latest_batch_memory = next(
            (
                row
                for row in memory_rows
                if str(row.get("memory_kind", "") or "").strip()
                == "scientific_batch_reconciliation"
            ),
            {},
        )
        latest_strong_near_miss_memory = next(
            (
                row
                for row in memory_rows
                if str(row.get("memory_kind", "") or "").strip()
                == "scientific_strong_near_miss"
            ),
            {},
        )
        latest_reconciliation_memory = next(
            (
                row
                for row in memory_rows
                if str(row.get("memory_kind", "") or "").strip()
                == "scientific_reconciliation"
            ),
            {},
        )
        approved_memory = next(
            (
                row
                for row in memory_rows
                if bool(row.get("approved_for_use")) and row.get("policy_after")
            ),
            {},
        )
        latest_decision = decision_rows[0] if decision_rows else {}
        batch_memory_rows: list[dict[str, Any]] = []
        with get_session(self.db_path) as session:
            rows = (
                session.query(ScientificInstitutionalMemory)
                .filter(
                    ScientificInstitutionalMemory.memory_kind
                    == "scientific_batch_reconciliation"
                )
                .order_by(
                    ScientificInstitutionalMemory.created_at.desc(),
                    ScientificInstitutionalMemory.id.desc(),
                )
                .limit(2)
                .all()
            )
        for row in rows:
            batch_memory_rows.append(
                {
                    "id": int(getattr(row, "id", 0) or 0),
                    "created_at": row.created_at.isoformat()
                    if getattr(row, "created_at", None)
                    else "",
                    "memory_kind": _safe_str(getattr(row, "memory_kind", "")),
                    "strategy_name": _safe_str(getattr(row, "strategy_name", "")),
                    "game_size": int(getattr(row, "game_size", 0) or 0),
                    "batch_id": _safe_str(getattr(row, "batch_id", "")),
                    "generation_range": dict(
                        getattr(row, "generation_range", {}) or {}
                    ),
                    "total_games": int(getattr(row, "total_games", 0) or 0),
                    "unique_games": int(getattr(row, "unique_games", 0) or 0),
                    "duplicate_games": int(getattr(row, "duplicate_games", 0) or 0),
                    "structural_status": _safe_str(
                        getattr(row, "structural_status", "")
                    ),
                    "scientific_status": _safe_str(
                        getattr(row, "scientific_status", "")
                    ),
                    "scientific_classification": _safe_str(
                        getattr(row, "scientific_classification", "")
                    ),
                    "main_reason": _safe_str(getattr(row, "main_reason", "")),
                    "recommended_action": _safe_str(
                        getattr(row, "recommended_action", "")
                    ),
                    "policy_applied": dict(getattr(row, "policy_applied", {}) or {}),
                    "policy_before": dict(getattr(row, "policy_before", {}) or {}),
                    "policy_after": dict(getattr(row, "policy_after", {}) or {}),
                    "best_hit": int(getattr(row, "best_hit", 0) or 0),
                    "average_hits": float(getattr(row, "average_hits", 0.0) or 0.0),
                    "count_11_plus": int(getattr(row, "count_11_plus", 0) or 0),
                    "count_12_plus": int(getattr(row, "count_12_plus", 0) or 0),
                    "count_13_plus": int(getattr(row, "count_13_plus", 0) or 0),
                    "count_14_plus": int(getattr(row, "count_14_plus", 0) or 0),
                    "count_15": int(getattr(row, "count_15", 0) or 0),
                    "validation_contests": list(
                        getattr(row, "validation_contests", []) or []
                    ),
                    "cross_validation_summary": dict(
                        getattr(row, "cross_validation_summary", {}) or {}
                    ),
                    "decision_mode": _safe_str(
                        getattr(row, "decision_mode", "OBSERVACAO"), "OBSERVACAO"
                    ),
                    "approved_for_use": bool(getattr(row, "approved_for_use", 0) or 0),
                    "notes": _safe_str(getattr(row, "notes", "")),
                    "official_history_count": int(
                        getattr(row, "official_history_count", 0) or 0
                    ),
                    "official_history_first_contest": getattr(
                        row, "official_history_first_contest", None
                    ),
                    "official_history_last_contest": getattr(
                        row, "official_history_last_contest", None
                    ),
                    "official_history_window": list(
                        getattr(row, "official_history_window", []) or []
                    ),
                    "source": _safe_str(
                        getattr(row, "source", "scientific_calibration"),
                        "scientific_calibration",
                    ),
                }
            )
        prioritized_memory_row = next(
            (
                row
                for row in (
                    latest_batch_memory,
                    latest_strong_near_miss_memory,
                    latest_reconciliation_memory,
                    approved_memory,
                    latest_memory,
                )
                if row
            ),
            {},
        )
        prioritized_memory_kind = str(
            prioritized_memory_row.get("memory_kind", "") or ""
        ).strip()
        prioritized_memory_id = int(prioritized_memory_row.get("id", 0) or 0)
        prioritized_batch_id = str(
            prioritized_memory_row.get("batch_id", "") or ""
        ).strip()
        prioritized_generation_range = dict(
            prioritized_memory_row.get("generation_range", {}) or {}
        )
        prioritized_policy_after = dict(
            prioritized_memory_row.get("policy_after", {}) or {}
        )
        prioritized_policy_before = dict(
            prioritized_memory_row.get("policy_before", {}) or {}
        )
        prioritized_policy = dict(
            prioritized_policy_after or prioritized_policy_before or {}
        )
        if prioritized_policy:
            prioritized_policy = {
                **base_policy,
                **{
                    key: value
                    for key, value in prioritized_policy.items()
                    if key in base_policy
                },
                **{
                    key: value
                    for key, value in prioritized_policy.items()
                    if key not in base_policy
                },
            }
        if prioritized_memory_kind == "scientific_batch_reconciliation":
            prioritized_policy.setdefault(
                "policy_adjustment_reason",
                "recalibrate_from_strong_near_miss_towards_11_plus_and_15",
            )
            prioritized_policy.setdefault(
                "policy_origin", "scientific_batch_reconciliation_memory"
            )
        elif prioritized_memory_kind == "scientific_strong_near_miss":
            prioritized_policy.setdefault(
                "policy_adjustment_reason",
                "recalibrate_from_strong_near_miss_towards_11_plus_and_15",
            )
            prioritized_policy.setdefault(
                "policy_origin", "scientific_strong_near_miss_memory"
            )
        elif prioritized_memory_kind == "scientific_reconciliation":
            prioritized_policy.setdefault(
                "policy_adjustment_reason", "recalibrate_from_near_miss_towards_15"
            )
            prioritized_policy.setdefault(
                "policy_origin", "scientific_reconciliation_memory"
            )
        elif prioritized_memory_kind == "scientific_calibration":
            prioritized_policy.setdefault(
                "policy_origin", "scientific_calibration_memory"
            )
        memory_policy = dict(prioritized_policy) if prioritized_policy else {}
        latest_persisted_batch_memory = (
            batch_memory_rows[0] if batch_memory_rows else latest_batch_memory
        )
        previous_persisted_batch_memory = (
            batch_memory_rows[1] if len(batch_memory_rows) > 1 else {}
        )
        latest_batch_generation_range = dict(
            latest_persisted_batch_memory.get("generation_range", {}) or {}
        )
        previous_batch_generation_range = dict(
            previous_persisted_batch_memory.get("generation_range", {}) or {}
        )
        batch_memory_current_best_hits = int(
            latest_batch_generation_range.get(
                "global_best_hits", latest_persisted_batch_memory.get("best_hit", 0)
            )
            or 0
        )
        batch_memory_current_count_10 = int(
            latest_batch_generation_range.get("global_count_10", 0) or 0
        )
        batch_memory_current_count_11_plus = int(
            latest_batch_generation_range.get(
                "global_count_11_plus",
                latest_persisted_batch_memory.get("count_11_plus", 0),
            )
            or 0
        )
        batch_memory_previous_best_hits = int(
            previous_batch_generation_range.get(
                "global_best_hits", previous_persisted_batch_memory.get("best_hit", 0)
            )
            or 0
        )
        batch_memory_previous_count_10 = int(
            previous_batch_generation_range.get("global_count_10", 0) or 0
        )
        batch_memory_previous_count_11_plus = int(
            previous_batch_generation_range.get(
                "global_count_11_plus",
                previous_persisted_batch_memory.get("count_11_plus", 0),
            )
            or 0
        )
        batch_memory_has_evolution = batch_memory_current_count_11_plus > 0
        hybrid_auxiliary_mode = (
            prioritized_memory_kind == "scientific_batch_reconciliation"
            and not batch_memory_has_evolution
        )
        hybrid_selection_variant = "hybrid_history_profile_with_auxiliary_near_miss"
        hybrid_selection_reason = "hybrid_recalibration_with_diversity_expansion"

        def _load_batch_games_for_cross_validation(
            batch_id: str,
        ) -> list[dict[str, Any]]:
            resolved_batch_id = str(batch_id or "").strip()
            if not resolved_batch_id:
                return []
            with get_session(self.db_path) as session:
                rows = (
                    session.query(
                        GenerationEvent.id.label("generation_event_id"),
                        GenerationEvent.context_json,
                        GeneratedGame.game_index,
                        GeneratedGame.numbers,
                        GeneratedGame.final_score,
                        GeneratedGame.profile_type,
                    )
                    .join(
                        GeneratedGame,
                        GeneratedGame.generation_event_id == GenerationEvent.id,
                    )
                    .filter(
                        GenerationEvent.context_json["batch_id"].as_string()
                        == resolved_batch_id
                    )
                    .order_by(GenerationEvent.id.asc(), GeneratedGame.game_index.asc())
                    .all()
                )
            games: list[dict[str, Any]] = []
            for row in rows:
                context_json = dict(getattr(row, "context_json", {}) or {})
                numbers = _normalize_numbers(getattr(row, "numbers", []))
                final_score = dict(getattr(row, "final_score", {}) or {})
                games.append(
                    {
                        "generation_event_id": int(
                            getattr(row, "generation_event_id", 0) or 0
                        ),
                        "game_index": int(getattr(row, "game_index", 0) or 0),
                        "numbers": numbers,
                        "game_signature": str(
                            context_json.get("game_signature", "") or ""
                        ),
                        "score": float(final_score.get("final_score", 0.0) or 0.0),
                        "perfil": str(
                            context_json.get(
                                "perfil", getattr(row, "profile_type", "") or ""
                            )
                            or getattr(row, "profile_type", "")
                            or ""
                        ),
                        "profile_type": str(
                            getattr(row, "profile_type", "")
                            or context_json.get("profile_type", "")
                            or ""
                        ),
                    }
                )
            return games

        def _build_cross_validation_summary(batch_id: str) -> dict[str, Any]:
            resolved_batch_id = str(batch_id or "").strip()
            if not resolved_batch_id or not self.contests:
                return {}
            games = _load_batch_games_for_cross_validation(resolved_batch_id)
            if not games:
                with get_session(self.db_path) as session:
                    memory_row = (
                        session.query(ScientificInstitutionalMemory)
                        .filter(
                            ScientificInstitutionalMemory.batch_id == resolved_batch_id
                        )
                        .order_by(
                            ScientificInstitutionalMemory.created_at.desc(),
                            ScientificInstitutionalMemory.id.desc(),
                        )
                        .first()
                    )
                if memory_row:
                    recovered_summary = dict(
                        getattr(memory_row, "cross_validation_summary", {}) or {}
                    )
                    recovered_windows = dict(
                        recovered_summary.get(
                            "windows",
                            recovered_summary.get("cross_validation_windows", {}),
                        )
                        or {}
                    )
                    if recovered_windows:
                        total_count_11_plus = sum(
                            int(window.get("total_count_11_plus", 0) or 0)
                            for window in recovered_windows.values()
                        )
                        contests_with_11_plus = sum(
                            int(window.get("contests_with_11_plus", 0) or 0)
                            for window in recovered_windows.values()
                        )
                        support_level = str(
                            recovered_summary.get("support_level", "") or ""
                        ).strip() or (
                            "dominant_conditional"
                            if any(
                                float(window.get("average_best_hits", 0.0) or 0.0)
                                >= 11.0
                                and int(window.get("max_best_hits", 0) or 0) >= 13
                                for window in recovered_windows.values()
                            )
                            else "strong_support"
                            if any(
                                float(window.get("average_best_hits", 0.0) or 0.0)
                                >= 11.0
                                for window in recovered_windows.values()
                            )
                            else "none"
                        )
                        cross_validation_reason = str(
                            recovered_summary.get("cross_validation_reason", "") or ""
                        ).strip() or (
                            "historical_cross_validation_supports_memory"
                            if support_level != "none"
                            else "historical_cross_validation_does_not_support_memory"
                        )
                        return {
                            "batch_id": resolved_batch_id,
                            "support_level": support_level,
                            "cross_validation_reason": cross_validation_reason,
                            "total_count_11_plus": total_count_11_plus,
                            "contests_with_11_plus": contests_with_11_plus,
                            "windows": recovered_windows,
                        }
                return {}

            def _window_summary(window_size: int) -> dict[str, Any]:
                if window_size <= 0 or len(self.contests) < window_size:
                    return {}
                window_contests = self.contests[-window_size:]
                contest_details: list[dict[str, Any]] = []
                total_count_10 = 0
                total_count_11_plus = 0
                total_count_12_plus = 0
                total_count_13_plus = 0
                total_count_14_plus = 0
                total_count_15 = 0
                contest_numbers_with_11_plus: list[int] = []
                contest_numbers_with_12_plus: list[int] = []
                contest_numbers_with_13_plus: list[int] = []
                contest_numbers_with_14_plus: list[int] = []
                contest_numbers_with_15: list[int] = []
                best_hits_values: list[int] = []
                for contest in window_contests:
                    contest_numbers = set(
                        _normalize_numbers(contest.get("numbers", []))
                    )
                    per_game: list[dict[str, Any]] = []
                    for game in games:
                        matched_numbers = sorted(
                            contest_numbers.intersection(game["numbers"])
                        )
                        missing_draw_numbers = sorted(
                            contest_numbers.difference(game["numbers"])
                        )
                        extra_numbers = sorted(
                            set(game["numbers"]).difference(contest_numbers)
                        )
                        hits = len(matched_numbers)
                        per_game.append(
                            {
                                "generation_event_id": int(
                                    game.get("generation_event_id", 0) or 0
                                ),
                                "game_index": int(game.get("game_index", 0) or 0),
                                "game_signature": str(
                                    game.get("game_signature", "") or ""
                                ),
                                "numbers": list(game.get("numbers", []) or []),
                                "hits": hits,
                                "matched_numbers": matched_numbers,
                                "missing_draw_numbers": missing_draw_numbers,
                                "extra_numbers": extra_numbers,
                                "score_original": float(game.get("score", 0.0) or 0.0),
                                "perfil": str(game.get("perfil", "") or ""),
                                "profile_type": str(game.get("profile_type", "") or ""),
                            }
                        )
                    if not per_game:
                        continue
                    best_game = max(
                        per_game,
                        key=lambda item: (
                            int(item["hits"]),
                            float(item["score_original"]),
                            -int(item["game_index"]),
                        ),
                    )
                    best_hits = int(best_game["hits"])
                    count_10 = sum(1 for item in per_game if int(item["hits"]) == 10)
                    count_11_plus = sum(
                        1 for item in per_game if int(item["hits"]) >= 11
                    )
                    count_12_plus = sum(
                        1 for item in per_game if int(item["hits"]) >= 12
                    )
                    count_13_plus = sum(
                        1 for item in per_game if int(item["hits"]) >= 13
                    )
                    count_14_plus = sum(
                        1 for item in per_game if int(item["hits"]) >= 14
                    )
                    count_15 = sum(1 for item in per_game if int(item["hits"]) == 15)
                    best_hits_values.append(best_hits)
                    total_count_10 += count_10
                    total_count_11_plus += count_11_plus
                    total_count_12_plus += count_12_plus
                    total_count_13_plus += count_13_plus
                    total_count_14_plus += count_14_plus
                    total_count_15 += count_15
                    if count_11_plus > 0:
                        contest_numbers_with_11_plus.append(
                            int(contest["contest_number"])
                        )
                    if count_12_plus > 0:
                        contest_numbers_with_12_plus.append(
                            int(contest["contest_number"])
                        )
                    if count_13_plus > 0:
                        contest_numbers_with_13_plus.append(
                            int(contest["contest_number"])
                        )
                    if count_14_plus > 0:
                        contest_numbers_with_14_plus.append(
                            int(contest["contest_number"])
                        )
                    if count_15 > 0:
                        contest_numbers_with_15.append(int(contest["contest_number"]))
                    contest_details.append(
                        {
                            "contest_number": int(contest["contest_number"]),
                            "best_hits": best_hits,
                            "count_10": count_10,
                            "count_11_plus": count_11_plus,
                            "count_12_plus": count_12_plus,
                            "count_13_plus": count_13_plus,
                            "count_14_plus": count_14_plus,
                            "count_15": count_15,
                            "best_game_signature": str(
                                best_game.get("game_signature", "") or ""
                            ),
                            "matched_numbers": list(
                                best_game.get("matched_numbers", []) or []
                            ),
                            "missing_draw_numbers": list(
                                best_game.get("missing_draw_numbers", []) or []
                            ),
                            "extra_numbers": list(
                                best_game.get("extra_numbers", []) or []
                            ),
                            "best_games": sorted(
                                per_game,
                                key=lambda item: (
                                    -int(item["hits"]),
                                    -float(item["score_original"]),
                                    int(item["game_index"]),
                                ),
                            )[:3],
                        }
                    )
                average_best_hits = (
                    round(
                        _mean_or_zero([float(value) for value in best_hits_values]), 4
                    )
                    if best_hits_values
                    else 0.0
                )
                max_best_hits = max(best_hits_values) if best_hits_values else 0
                contests_with_11_plus = len(contest_numbers_with_11_plus)
                contests_with_12_plus = len(contest_numbers_with_12_plus)
                contests_with_13_plus = len(contest_numbers_with_13_plus)
                contests_with_14_plus = len(contest_numbers_with_14_plus)
                contests_with_15 = len(contest_numbers_with_15)
                count_11_exact = max(0, total_count_11_plus - total_count_12_plus)
                count_12_exact = max(0, total_count_12_plus - total_count_13_plus)
                count_13_exact = max(0, total_count_13_plus - total_count_14_plus)
                count_14_exact = max(0, total_count_14_plus - total_count_15)
                return {
                    "window_size": window_size,
                    "contest_numbers": [
                        int(item["contest_number"]) for item in window_contests
                    ],
                    "average_best_hits": average_best_hits,
                    "max_best_hits": max_best_hits,
                    "total_count_10": total_count_10,
                    "total_count_11_plus": total_count_11_plus,
                    "total_count_12_plus": total_count_12_plus,
                    "total_count_13_plus": total_count_13_plus,
                    "total_count_14_plus": total_count_14_plus,
                    "total_count_15": total_count_15,
                    "count_11_exact": count_11_exact,
                    "count_12_exact": count_12_exact,
                    "count_13_exact": count_13_exact,
                    "count_14_exact": count_14_exact,
                    "contests_with_11_plus": contests_with_11_plus,
                    "contests_with_12_plus": contests_with_12_plus,
                    "contests_with_13_plus": contests_with_13_plus,
                    "contests_with_14_plus": contests_with_14_plus,
                    "contests_with_15": contests_with_15,
                    "contest_numbers_with_11_plus": contest_numbers_with_11_plus,
                    "contest_numbers_with_12_plus": contest_numbers_with_12_plus,
                    "contest_numbers_with_13_plus": contest_numbers_with_13_plus,
                    "contest_numbers_with_14_plus": contest_numbers_with_14_plus,
                    "contest_numbers_with_15": contest_numbers_with_15,
                    "best_contests": contest_details[:5],
                }

            windows: dict[str, dict[str, Any]] = {}
            for window_size in (10, 30, 60):
                summary = _window_summary(window_size)
                if summary:
                    windows[str(window_size)] = summary
            if not windows:
                return {}
            support_windows = {
                key: value
                for key, value in windows.items()
                if float(value.get("average_best_hits", 0.0) or 0.0) >= 11.0
                and int(value.get("max_best_hits", 0) or 0) >= 12
                and int(value.get("total_count_11_plus", 0) or 0) > 0
                and int(value.get("contests_with_11_plus", 0) or 0) >= 2
            }
            dominant_windows = {
                key: value
                for key, value in support_windows.items()
                if float(value.get("average_best_hits", 0.0) or 0.0) >= 11.0
                and int(value.get("max_best_hits", 0) or 0) >= 13
                and int(value.get("total_count_11_plus", 0) or 0) >= 5
            }
            support_level = "none"
            if dominant_windows:
                support_level = "dominant_conditional"
            elif support_windows:
                support_level = "strong_support"
            total_count_11_plus = sum(
                int(window.get("total_count_11_plus", 0) or 0)
                for window in windows.values()
            )
            contests_with_11_plus = sum(
                int(window.get("contests_with_11_plus", 0) or 0)
                for window in windows.values()
            )
            cross_validation_reason = (
                "historical_cross_validation_supports_memory"
                if support_level != "none"
                else "historical_cross_validation_does_not_support_memory"
            )
            return {
                "batch_id": resolved_batch_id,
                "support_level": support_level,
                "cross_validation_reason": cross_validation_reason,
                "total_count_11_plus": total_count_11_plus,
                "contests_with_11_plus": contests_with_11_plus,
                "windows": windows,
            }

        batch_cross_validation_summary = (
            _build_cross_validation_summary(prioritized_batch_id)
            if prioritized_memory_kind == "scientific_batch_reconciliation"
            else {}
        )
        batch_cross_validation_support_level = str(
            batch_cross_validation_summary.get("support_level", "") or ""
        ).strip()
        batch_cross_validation_reason = str(
            batch_cross_validation_summary.get("cross_validation_reason", "") or ""
        ).strip()
        batch_cross_validation_windows = dict(
            batch_cross_validation_summary.get("windows", {}) or {}
        )
        batch_cross_validation_supported = batch_cross_validation_support_level in {
            "strong_support",
            "dominant_conditional",
        }
        batch_cross_validation_dominant = (
            batch_cross_validation_support_level == "dominant_conditional"
        )
        cross_validated_batch_mode = (
            prioritized_memory_kind == "scientific_batch_reconciliation"
            and batch_cross_validation_supported
        )
        hybrid_auxiliary_mode = (
            prioritized_memory_kind == "scientific_batch_reconciliation"
            and not batch_cross_validation_supported
        )

        candidate_policies: list[dict[str, Any]] = []
        rejected_by_guardian_count = 0
        candidate_variants: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
        candidate_variants.append(
            (
                "history_profile_seed",
                _policy_to_candidate_params(base_policy),
                {"seed": "official_history"},
            )
        )
        if memory_policy and not hybrid_auxiliary_mode:
            candidate_variants.append(
                (
                    "memory_blend",
                    _policy_to_candidate_params(memory_policy),
                    {"notes": ("scientific_memory_blend",)},
                )
            )

        rejected_policy_signatures: set[str] = set()
        for row in memory_rows:
            if bool(row.get("approved_for_use")):
                continue
            policy_after = dict(row.get("policy_after") or {})
            policy_before = dict(row.get("policy_before") or {})
            if policy_after:
                rejected_policy_signatures.add(_policy_signature(policy_after))
            if policy_before:
                rejected_policy_signatures.add(_policy_signature(policy_before))
        for row in decision_rows:
            if bool(row.get("applied")):
                continue
            policy_after = dict(row.get("policy_after") or {})
            policy_before = dict(row.get("policy_before") or {})
            if policy_after:
                rejected_policy_signatures.add(_policy_signature(policy_after))
            if policy_before:
                rejected_policy_signatures.add(_policy_signature(policy_before))

        repeat_anchor = max(0, min(resolved_game_size, base_repeat_center))
        for family_index, parity_family in enumerate(parity_families, start=1):
            for repeat_min in repeat_min_candidates:
                for repeat_max in repeat_max_candidates:
                    if repeat_min > repeat_max:
                        continue
                    if repeat_max - repeat_min > max(3, resolved_game_size // 2):
                        continue
                    for sequence_max in sequence_candidates:
                        for coverage_min in coverage_candidates:
                            for entropy_min in entropy_candidates:
                                for max_frequency_ratio in max_frequency_candidates:
                                    for min_frequency_ratio in min_frequency_candidates:
                                        if min_frequency_ratio > max_frequency_ratio:
                                            continue
                                        if sequence_max < max(
                                            4, resolved_game_size // 4
                                        ):
                                            continue
                                        variant_name = (
                                            "history_profile"
                                            if family_index == 1
                                            and repeat_min == repeat_floor
                                            and repeat_max == repeat_ceiling
                                            and sequence_max == sequence_cap
                                            else f"auto_{family_index}_{repeat_min}_{repeat_max}_{sequence_max}"
                                        )
                                        candidate_variants.append(
                                            (
                                                variant_name,
                                                {
                                                    "repeat_min": repeat_min,
                                                    "repeat_max": repeat_max,
                                                    "preferred": parity_family,
                                                    "allowed": allowed_pairs
                                                    if family_index == 1
                                                    else parity_family,
                                                    "sequence_max": sequence_max,
                                                    "coverage_min": coverage_min,
                                                    "entropy_min": entropy_min,
                                                    "max_frequency_ratio": max_frequency_ratio,
                                                    "min_frequency_ratio": min_frequency_ratio,
                                                    "notes": (
                                                        "automatic_scientific_search",
                                                        f"parity_family_{family_index}",
                                                    ),
                                                },
                                                {
                                                    "repeat_center": repeat_anchor,
                                                    "parity_family": family_index,
                                                },
                                            )
                                        )
                                        if len(candidate_variants) >= max(
                                            20, int(candidate_limit or 120)
                                        ):
                                            break
                                    if len(candidate_variants) >= max(
                                        20, int(candidate_limit or 120)
                                    ):
                                        break
                                if len(candidate_variants) >= max(
                                    20, int(candidate_limit or 120)
                                ):
                                    break
                            if len(candidate_variants) >= max(
                                20, int(candidate_limit or 120)
                            ):
                                break
                        if len(candidate_variants) >= max(
                            20, int(candidate_limit or 120)
                        ):
                            break
                    if len(candidate_variants) >= max(20, int(candidate_limit or 120)):
                        break

        candidate_variants = candidate_variants[: max(20, int(candidate_limit or 120))]
        for variant_name, params, extra in candidate_variants:
            candidate_policy = _canonical_policy(
                repeat_min=int(params["repeat_min"]),
                repeat_max=int(params["repeat_max"]),
                preferred=list(params["preferred"]),
                allowed=list(params["allowed"]),
                sequence_max=int(params["sequence_max"]),
                coverage_min=float(params["coverage_min"]),
                entropy_min=float(params["entropy_min"]),
                max_frequency_ratio=float(params["max_frequency_ratio"]),
                min_frequency_ratio=float(params["min_frequency_ratio"]),
                notes=tuple(params.get("notes", ()))
                + tuple(f"{key}={value}" for key, value in extra.items()),
                variant_name=variant_name,
            )
            candidate_signature = _policy_signature(candidate_policy)
            if candidate_signature in rejected_policy_signatures:
                candidate_policy["policy_variant"] = (
                    f"{variant_name}_rejected_by_guardian"
                )
                candidate_policy["policy_signature"] = candidate_signature
                rejected_by_guardian_count += 1
                continue
            candidate_policies.append(candidate_policy)

        scored_candidates: list[dict[str, Any]] = []
        target_repeat = round(repeat_mean or max(1.0, resolved_game_size / 2), 2)
        target_sequence = round(sequence_mean or max(4.0, resolved_game_size / 3), 2)
        target_coverage = round(coverage_mean or 0.35, 2)
        target_entropy = round(entropy_mean or 0.35, 2)
        target_max_frequency_ratio = round(observed_max_frequency, 2)
        target_min_frequency_ratio = round(observed_min_frequency, 2)
        target_pair = preferred_pairs[0]
        target_pair_set = {tuple(pair) for pair in preferred_pairs}
        dominant_set = {int(number) for number in core_numbers[:4]}

        for index, candidate in enumerate(candidate_policies, start=1):
            repeat_min = int(candidate.get("repeat_min", 0) or 0)
            repeat_max = int(candidate.get("repeat_max", 0) or 0)
            sequence_max = int(candidate.get("sequence_max", 0) or 0)
            coverage_min = float(candidate.get("coverage_min", 0.0) or 0.0)
            entropy_min = float(candidate.get("entropy_min", 0.0) or 0.0)
            max_frequency_ratio = float(
                candidate.get("max_frequency_ratio", 0.0) or 0.0
            )
            min_frequency_ratio = float(
                candidate.get("min_frequency_ratio", 0.0) or 0.0
            )
            candidate_preferred = [
                tuple(int(part) for part in pair)
                for pair in candidate.get("preferred_parity_pairs", []) or []
            ]
            candidate_allowed = [
                tuple(int(part) for part in pair)
                for pair in candidate.get("allowed_parity_pairs", []) or []
            ]
            candidate_core = [
                int(number) for number in candidate.get("core_numbers", []) or []
            ]
            candidate_discouraged = [
                int(number) for number in candidate.get("discouraged_numbers", []) or []
            ]

            acceptance_errors: list[str] = []
            if (
                candidate.get("policy_variant") == "history_profile_seed"
                and history_count >= 60
            ):
                acceptance_errors.append("seed_policy_requires_validation")
            if resolved_game_size == 15 and history_count >= 60:
                # Expandir limites de aceitação para 15D: permitir repetição mínima de 6 (antes era 7)
                # Isso permite que políticas que focam em 8 repetições (centro da faixa 6-10) sejam aceitas.
                if repeat_min < 6 or repeat_max > 11:
                    acceptance_errors.append("repeat_policy_out_of_bounds_for_15")
                if max_frequency_ratio > 0.70:
                    acceptance_errors.append("frequency_cap_above_threshold")
                if min_frequency_ratio < 0.20:
                    acceptance_errors.append("frequency_floor_below_threshold")
                if sequence_max > 6:
                    acceptance_errors.append("sequence_limit_above_threshold")
            if repeat_min > repeat_max:
                acceptance_errors.append("repetition_range_inverted")
            if not candidate_preferred:
                acceptance_errors.append("no_preferred_parity")
            if not candidate_allowed:
                acceptance_errors.append("no_allowed_parity")
            if any(
                sum(pair) != resolved_game_size
                for pair in candidate_preferred + candidate_allowed
            ):
                acceptance_errors.append("parity_sum_mismatch")
            if not candidate_core:
                acceptance_errors.append("no_core_numbers")
            if max_frequency_ratio < 0.50 or max_frequency_ratio > 0.85:
                acceptance_errors.append("frequency_cap_out_of_bounds")
            if min_frequency_ratio < 0.05 or min_frequency_ratio > 0.35:
                acceptance_errors.append("frequency_floor_out_of_bounds")
            if (
                coverage_min < 0.80 or coverage_min > 0.95
            ):  # Elevado de 0.30-0.85 para 0.80-0.95 (M-OPS-083)
                acceptance_errors.append("coverage_out_of_bounds")
            if entropy_min < 0.25 or entropy_min > 0.85:
                acceptance_errors.append("entropy_out_of_bounds")
            if sequence_max < 4:
                acceptance_errors.append("sequence_limit_too_low")
            if repeat_min < 0 or repeat_max > resolved_game_size:
                acceptance_errors.append("repeat_out_of_bounds")
            if sequence_max > resolved_game_size:
                acceptance_errors.append("sequence_limit_too_high")

            preferred_pair_match = (
                target_pair in candidate_preferred
                or tuple(reversed(target_pair)) in candidate_preferred
            )
            parity_penalty = 0.0 if preferred_pair_match else 12.0
            if not preferred_pair_match and target_pair_set.intersection(
                candidate_allowed
            ):
                parity_penalty = 4.0
            core_overlap = len(dominant_set.intersection(candidate_core[:4]))
            discouraged_overlap = len(
                set(candidate_discouraged[:6]).intersection(
                    set(candidate_discouraged[:6])
                )
            )
            distance = 0.0
            distance += abs(((repeat_min + repeat_max) / 2.0) - target_repeat) * 4.0
            distance += abs(sequence_max - target_sequence) * 5.0
            distance += abs(coverage_min - target_coverage) * 100.0
            distance += abs(entropy_min - target_entropy) * 100.0
            distance += abs(max_frequency_ratio - target_max_frequency_ratio) * 100.0
            distance += abs(min_frequency_ratio - target_min_frequency_ratio) * 100.0
            distance += parity_penalty
            distance -= core_overlap * 3.0
            distance -= discouraged_overlap * 0.5
            if memory_policy and candidate.get("policy_variant") == "memory_blend":
                distance -= 3.0
            if candidate.get("policy_variant") == "balanced_history_profile":
                distance -= 1.5
            if candidate.get("policy_variant") == "conservative_frequency":
                distance -= 0.5
            if candidate.get("policy_variant") == "memory_blend":
                distance -= 2.0
            if acceptance_errors:
                distance += 1000.0 + len(acceptance_errors) * 50.0

            scored_candidates.append(
                {
                    "rank": index,
                    "variant": candidate.get("policy_variant", f"candidate_{index}"),
                    "policy": candidate,
                    "accepted": not acceptance_errors,
                    "acceptance_errors": acceptance_errors,
                    "score": round(distance, 4),
                    "preferred_pair_match": preferred_pair_match,
                    "core_overlap": core_overlap,
                }
            )

        accepted_candidates = [item for item in scored_candidates if item["accepted"]]
        if (
            not accepted_candidates
            and prioritized_memory_kind
            in {
                "scientific_batch_reconciliation",
                "scientific_strong_near_miss",
                "scientific_reconciliation",
                "scientific_calibration",
            }
            and memory_policy
            and not hybrid_auxiliary_mode
        ):
            accepted_candidates = [
                {
                    "variant": (
                        "scientific_batch_reconciliation_memory"
                        if prioritized_memory_kind == "scientific_batch_reconciliation"
                        else "scientific_strong_near_miss_memory"
                        if prioritized_memory_kind == "scientific_strong_near_miss"
                        else "scientific_reconciliation_memory"
                        if prioritized_memory_kind == "scientific_reconciliation"
                        else "scientific_calibration_memory"
                    ),
                    "policy": dict(memory_policy),
                    "rank": 0,
                    "score": 0.0,
                    "accepted": True,
                    "acceptance_errors": [],
                }
            ]
        if not accepted_candidates:
            selection_reason = ""
            return {
                "game_size": resolved_game_size,
                "policy": {},
                "policy_before": dict(base_policy),
                "policy_after": {},
                "policy_id": "",
                "policy_origin": "automatic_scientific_discovery",
                "policies_tested": len(candidate_variants),
                "validation_window": int(profile_window or len(self.contests)),
                "official_history_count": history_count,
                "official_history_first_contest": int(
                    self.contests[0].get("contest_number", 0) or 0
                )
                if self.contests
                else None,
                "official_history_last_contest": int(
                    self.contests[-1].get("contest_number", 0) or 0
                )
                if self.contests
                else None,
                "scientific_memory_count": len(memory_rows),
                "scientific_decision_count": len(decision_rows),
                "scientific_memory_latest": latest_memory,
                "scientific_memory_latest_batch_reconciliation": latest_batch_memory,
                "scientific_memory_latest_strong_near_miss": latest_strong_near_miss_memory,
                "scientific_memory_latest_reconciliation": latest_reconciliation_memory,
                "scientific_memory_latest_approved": approved_memory,
                "scientific_decision_latest": latest_decision,
                "selection_rank": None,
                "selection_variant": "",
                "selection_reason": "",
                "selection_status": "NONE_APPROVED",
                "candidate_count": len(candidate_variants),
                "selection_score": None,
                "selected_at": datetime.now(timezone.utc).isoformat(),
                "candidates_tested": scored_candidates,
                "approved_candidates": [],
                "rejected_by_guardian": rejected_by_guardian_count,
                "rejected_by_rules": sum(
                    1 for item in scored_candidates if item["acceptance_errors"]
                ),
                "parameter_reasoning": {
                    "repeat": f"derived from average repetition {repeat_mean:.2f} and adjusted around official-history stability",
                    "parity": f"derived from average odd/even {average_odd:.2f}/{average_even:.2f} and validated parity families {preferred_pairs}",
                    "sequence": f"derived from average sequence max {sequence_mean:.2f} with controlled ceiling {sequence_cap}",
                    "coverage": f"derived from average coverage {coverage_mean:.2f} with floor {coverage_floor:.2f}",
                    "entropy": f"derived from average entropy {entropy_mean:.2f} with floor {entropy_floor:.2f}",
                    "core_numbers": f"top recurring numbers from official history: {list(core_numbers)}",
                    "discouraged_numbers": f"least frequent numbers from official history: {list(discouraged_numbers)}",
                    "frequency": f"observed history frequencies guided cap {observed_max_frequency:.2f} and floor {observed_min_frequency:.2f}",
                    "selection": "none_approved",
                },
                "history_profile": {
                    "contest_count": history_count,
                    "window_size": int(
                        profile.get("window_size", 0) or profile_window or 0
                    ),
                    "average_repetition": repeat_mean,
                    "average_sequence_max": sequence_mean,
                    "average_coverage": coverage_mean,
                    "average_entropy": entropy_mean,
                    "average_parity_odd": average_odd,
                    "average_parity_even": average_even,
                    "dominant_numbers": profile.get("dominant_numbers", []),
                    "discouraged_numbers": profile.get("discouraged_numbers", []),
                    "source": profile.get("source", "imported_contests"),
                },
            }
        selected_candidate = min(
            accepted_candidates,
            key=lambda item: (float(item["score"]), int(item["rank"])),
        )
        if cross_validated_batch_mode and memory_policy:
            selected_policy = dict(memory_policy)
            selected_policy["policy_origin"] = "scientific_batch_reconciliation_memory"
            selected_policy["policy_variant"] = (
                "cross_validated_scientific_batch_memory"
            )
            selected_policy["memory_role"] = "strong_support"
            selected_policy["dominant_memory"] = "conditional"
            selected_policy["dominant_memory_mode"] = "conditional"
            selected_policy["status_prospectivo"] = "pending_prospective_validation"
            selected_policy["reason"] = "historical_cross_validation_supports_memory"
            selected_policy["recommended_action"] = (
                "historical_cross_validation_supports_memory"
            )
            selected_policy["policy_adjustment_reason"] = (
                "historical_cross_validation_supports_memory"
            )
            selected_policy["selection_variant"] = (
                "cross_validated_scientific_batch_memory"
            )
            selected_policy["selection_reason"] = (
                "historical_cross_validation_supports_memory"
            )
            selected_policy["selection_status"] = "POLICY_SELECTED"
            selected_policy["cross_validation_windows"] = dict(
                batch_cross_validation_windows
            )
            selected_policy["cross_validation_summary"] = dict(
                batch_cross_validation_summary
            )
            selected_policy["cross_validation_reason"] = batch_cross_validation_reason
            selected_variant = "cross_validated_scientific_batch_memory"
            selected_rank = 0
            selected_score = None
            selection_reason = "historical_cross_validation_supports_memory"
        elif hybrid_auxiliary_mode:
            selected_policy = dict(selected_candidate["policy"])
            selected_policy["policy_origin"] = "automatic_scientific_discovery"
            selected_policy["policy_variant"] = hybrid_selection_variant
            selected_policy["memory_role"] = "auxiliary"
            selected_policy["dominant_memory"] = False
            selected_policy["dominant_memory_mode"] = "false"
            selected_policy["status_prospectivo"] = "pending_prospective_validation"
            selected_policy["reason"] = (
                "historical_cross_validation_did_not_support_memory"
            )
            selected_policy["previous_best_hits"] = batch_memory_previous_best_hits
            selected_policy["previous_count_10"] = batch_memory_previous_count_10
            selected_policy["previous_count_11_plus"] = (
                batch_memory_previous_count_11_plus
            )
            selected_policy["current_best_hits"] = batch_memory_current_best_hits
            selected_policy["current_count_10"] = batch_memory_current_count_10
            selected_policy["current_count_11_plus"] = (
                batch_memory_current_count_11_plus
            )
            selected_policy["recommended_action"] = (
                "historical_cross_validation_does_not_support_memory"
            )
            selected_policy["policy_adjustment_reason"] = (
                "historical_cross_validation_does_not_support_memory"
            )
            selected_policy["selection_variant"] = hybrid_selection_variant
            selected_policy["selection_reason"] = (
                "historical_cross_validation_does_not_support_memory"
            )
            selected_policy["selection_status"] = "POLICY_SELECTED"
            selected_policy["policy_mode"] = "HYBRID_AUXILIARY_NEAR_MISS"
            selected_variant = hybrid_selection_variant
            selected_rank = int(selected_candidate["rank"])
            selected_score = float(selected_candidate["score"])
            selection_reason = "historical_cross_validation_does_not_support_memory"
        elif (
            prioritized_memory_kind == "scientific_batch_reconciliation"
            and memory_policy
        ):
            selected_policy = dict(memory_policy)
            selection_reason = "historical_cross_validation_supports_memory"
            selected_variant = "cross_validated_scientific_batch_memory"
            selected_rank = 0
            selected_score = None
            selected_policy["status_prospectivo"] = "pending_prospective_validation"
        elif prioritized_memory_kind == "scientific_strong_near_miss" and memory_policy:
            selected_policy = dict(memory_policy)
            selection_reason = "policy_from_scientific_strong_near_miss"
            selected_variant = "scientific_strong_near_miss_memory"
            selected_rank = 0
            selected_score = None
            selected_policy["status_prospectivo"] = "pending_prospective_validation"
        elif prioritized_memory_kind == "scientific_reconciliation" and memory_policy:
            selected_policy = dict(memory_policy)
            selection_reason = "policy_from_scientific_reconciliation"
            selected_variant = "scientific_reconciliation_memory"
            selected_rank = 0
            selected_score = None
            selected_policy["status_prospectivo"] = "pending_prospective_validation"
        elif prioritized_memory_kind == "scientific_calibration" and memory_policy:
            selected_policy = dict(memory_policy)
            selection_reason = "policy_from_scientific_calibration"
            selected_variant = "scientific_calibration_memory"
            selected_rank = 0
            selected_score = None
            selected_policy["status_prospectivo"] = "pending_prospective_validation"
        else:
            selected_policy = dict(selected_candidate["policy"])
            selected_policy["policy_origin"] = "automatic_scientific_discovery"
            selected_policy["policy_variant"] = str(selected_candidate["variant"])
            selected_variant = str(selected_candidate["variant"])
            selected_rank = int(selected_candidate["rank"])
            selected_score = float(selected_candidate["score"])
        selected_policy.update(
            {
                "generation_hierarchy": "LOTOIA_LAW_ONLY",
                "scientific_law_role": "COMMANDER",
                "legacy_calibrator_role": "REMOVED_FROM_RUNTIME",
                "calibration_engine_role": "DISABLED",
                "geometric_filters_role": "SAFETY_GUARDRAIL",
                "output_commander_role": "AUDITOR",
                "memory_registry_role": "REGISTRY",
                "legacy_removed_from_runtime": True,
                "legacy_runtime_access": False,
                "legacy_reason": "historical_compatibility_or_tests_only",
                "based_on_memory_kind": prioritized_memory_kind or None,
                "based_on_memory_id": prioritized_memory_id or None,
                "based_on_batch_id": prioritized_batch_id or None,
                "based_on_generation_range": prioritized_generation_range or None,
                "based_on_best_generations": list(
                    prioritized_generation_range.get("best_generations")
                    or prioritized_generation_range.get("generation_event_ids")
                    or []
                ),
            }
        )
        selected_policy = _apply_scientific_15_vnext_policy(selected_policy)
        selected_policy = _apply_scientific_15_baseline_governance(
            selected_policy, approved_memory or latest_memory
        )
        validation_rule = _scientific_validation_rule(resolved_game_size)
        selected_policy["game_size"] = resolved_game_size
        selected_policy["validation_threshold"] = int(
            validation_rule["validation_threshold"]
        )
        selected_policy["target_band"] = str(validation_rule["target_band"])
        selected_policy["validation_zone_label"] = str(
            validation_rule["validation_zone_label"]
        )
        selected_policy["validation_minimum_label"] = str(
            validation_rule["validation_minimum_label"]
        )
        selected_policy["validation_band_counts"] = list(
            validation_rule["validation_band_counts"]
        )
        if (
            cross_validated_batch_mode
            and memory_policy
            and not (
                selected_policy.get("official_15_search_standard")
                and str(selected_policy.get("policy_validation_status", "")).upper()
                == "VALIDATED_15_POLICY_LEVEL_3"
            )
        ):
            selected_policy["memory_role"] = "strong_support"
            selected_policy["dominant_memory"] = "conditional"
            selected_policy["dominant_memory_mode"] = "conditional"
            selected_policy["policy_mode"] = "CROSS_VALIDATED_BATCH_SUPPORT"
            selected_policy["status_prospectivo"] = "pending_prospective_validation"
        elif (
            not (
                selected_policy.get("official_15_search_standard")
                and str(selected_policy.get("policy_validation_status", "")).upper()
                == "VALIDATED_15_POLICY_LEVEL_3"
            )
            and not hybrid_auxiliary_mode
            and prioritized_memory_kind
            in {
                "scientific_batch_reconciliation",
                "scientific_strong_near_miss",
                "scientific_reconciliation",
                "scientific_calibration",
            }
            and memory_policy
        ):
            selected_policy["dominant_memory"] = True
            selected_policy["memory_role"] = "dominant"
            selected_policy["policy_mode"] = "MEMORY_DOMINANT"
            selected_policy["status_prospectivo"] = "pending_prospective_validation"
        selected_policy["policy_signature"] = hashlib.sha1(
            json.dumps(
                {
                    "game_size": resolved_game_size,
                    "repeat_min": int(selected_policy.get("repeat_min", 0) or 0),
                    "repeat_max": int(selected_policy.get("repeat_max", 0) or 0),
                    "preferred_parity_pairs": selected_policy.get(
                        "preferred_parity_pairs", []
                    ),
                    "allowed_parity_pairs": selected_policy.get(
                        "allowed_parity_pairs", []
                    ),
                    "sequence_max": int(selected_policy.get("sequence_max", 0) or 0),
                    "coverage_min": float(
                        selected_policy.get("coverage_min", 0.0) or 0.0
                    ),
                    "entropy_min": float(
                        selected_policy.get("entropy_min", 0.0) or 0.0
                    ),
                    "core_numbers": selected_policy.get("core_numbers", []),
                    "discouraged_numbers": selected_policy.get(
                        "discouraged_numbers", []
                    ),
                    "max_frequency_ratio": float(
                        selected_policy.get("max_frequency_ratio", 0.0) or 0.0
                    ),
                    "min_frequency_ratio": float(
                        selected_policy.get("min_frequency_ratio", 0.0) or 0.0
                    ),
                    "validation_threshold": int(
                        selected_policy.get("validation_threshold", 0) or 0
                    ),
                    "target_band": str(selected_policy.get("target_band", "") or ""),
                },
                sort_keys=True,
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()[:12]
        if cross_validated_batch_mode:
            selection_reason = (
                batch_cross_validation_reason
                or "historical_cross_validation_supports_memory"
            )
        elif hybrid_auxiliary_mode:
            selection_reason = hybrid_selection_reason
        elif (
            prioritized_memory_kind
            in {
                "scientific_batch_reconciliation",
                "scientific_strong_near_miss",
                "scientific_reconciliation",
                "scientific_calibration",
            }
            and memory_policy
        ):
            selection_reason = (
                prioritized_memory_row.get("policy_adjustment_reason")
                or prioritized_memory_row.get("recommended_action")
                or selection_reason
            )
        else:
            selection_reason = (
                "policy_derived_from_official_history"
                if selected_candidate["variant"] == "base_history_profile"
                else f"policy_{selected_candidate['variant']}_best_scored_against_official_history"
            )
        policy_discovery = {
            "game_size": resolved_game_size,
            "policy": selected_policy,
            "policy_before": dict(base_policy),
            "policy_after": dict(selected_policy),
            "policy_id": selected_policy["policy_signature"],
            "policy_origin": "automatic_scientific_discovery"
            if not memory_policy
            else str(selected_policy.get("policy_origin", "scientific_memory")),
            "policies_tested": len(candidate_variants),
            "validation_window": int(profile_window or len(self.contests)),
            "official_history_count": history_count,
            "official_history_first_contest": int(
                self.contests[0].get("contest_number", 0) or 0
            )
            if self.contests
            else None,
            "official_history_last_contest": int(
                self.contests[-1].get("contest_number", 0) or 0
            )
            if self.contests
            else None,
            "scientific_memory_count": len(memory_rows),
            "scientific_decision_count": len(decision_rows),
            "scientific_memory_latest": latest_memory,
            "scientific_memory_latest_batch_reconciliation": latest_batch_memory,
            "scientific_memory_latest_strong_near_miss": latest_strong_near_miss_memory,
            "scientific_memory_latest_reconciliation": latest_reconciliation_memory,
            "scientific_memory_latest_approved": approved_memory,
            "scientific_decision_latest": latest_decision,
            "selection_rank": selected_rank,
            "selection_variant": selected_variant,
            "selection_reason": selection_reason,
            "selection_status": "POLICY_SELECTED",
            "candidate_count": len(candidate_variants),
            "selection_score": selected_score,
            "selected_at": datetime.now(timezone.utc).isoformat(),
            "generation_hierarchy": "LOTOIA_LAW_ONLY",
            "scientific_law_role": "COMMANDER",
            "legacy_calibrator_role": "REMOVED_FROM_RUNTIME",
            "calibration_engine_role": "DISABLED",
            "geometric_filters_role": "SAFETY_GUARDRAIL",
            "output_commander_role": "AUDITOR",
            "memory_registry_role": "REGISTRY",
            "legacy_removed_from_runtime": True,
            "legacy_runtime_access": False,
            "legacy_reason": "historical_compatibility_or_tests_only",
            "validation_threshold": int(validation_rule["validation_threshold"]),
            "target_band": str(validation_rule["target_band"]),
            "validation_zone_label": str(validation_rule["validation_zone_label"]),
            "candidates_tested": scored_candidates,
            "approved_candidates": [
                item for item in scored_candidates if item["accepted"]
            ],
            "rejected_by_guardian": rejected_by_guardian_count,
            "rejected_by_rules": sum(
                1 for item in scored_candidates if item["acceptance_errors"]
            ),
            "memory_role": "strong_support"
            if cross_validated_batch_mode
            else (
                "auxiliary"
                if hybrid_auxiliary_mode
                else ("dominant" if memory_policy else "")
            ),
            "dominant_memory": "conditional"
            if cross_validated_batch_mode
            else (False if hybrid_auxiliary_mode else bool(memory_policy)),
            "dominant_memory_mode": "conditional"
            if cross_validated_batch_mode
            else (
                "false" if hybrid_auxiliary_mode else ("true" if memory_policy else "")
            ),
            "reason": batch_cross_validation_reason
            if cross_validated_batch_mode
            else (
                "historical_cross_validation_did_not_support_memory"
                if hybrid_auxiliary_mode
                else ""
            ),
            "previous_best_hits": batch_memory_previous_best_hits
            if (hybrid_auxiliary_mode or cross_validated_batch_mode)
            else None,
            "previous_count_10": batch_memory_previous_count_10
            if (hybrid_auxiliary_mode or cross_validated_batch_mode)
            else None,
            "previous_count_11_plus": batch_memory_previous_count_11_plus
            if (hybrid_auxiliary_mode or cross_validated_batch_mode)
            else None,
            "current_best_hits": batch_memory_current_best_hits
            if (hybrid_auxiliary_mode or cross_validated_batch_mode)
            else None,
            "current_count_10": batch_memory_current_count_10
            if (hybrid_auxiliary_mode or cross_validated_batch_mode)
            else None,
            "current_count_11_plus": batch_memory_current_count_11_plus
            if (hybrid_auxiliary_mode or cross_validated_batch_mode)
            else None,
            "recommended_action": "historical_cross_validation_supports_memory"
            if cross_validated_batch_mode
            else (
                "historical_cross_validation_does_not_support_memory"
                if hybrid_auxiliary_mode
                else selection_reason
            ),
            "policy_adjustment_reason": "historical_cross_validation_supports_memory"
            if cross_validated_batch_mode
            else (
                "historical_cross_validation_does_not_support_memory"
                if hybrid_auxiliary_mode
                else selection_reason
            ),
            "cross_validation_windows": batch_cross_validation_windows
            if cross_validated_batch_mode
            else batch_cross_validation_windows
            if prioritized_memory_kind == "scientific_batch_reconciliation"
            else {},
            "cross_validation_summary": batch_cross_validation_summary
            if prioritized_memory_kind == "scientific_batch_reconciliation"
            else {},
            "cross_validation_reason": batch_cross_validation_reason
            if prioritized_memory_kind == "scientific_batch_reconciliation"
            else "",
            "based_on_memory_kind": prioritized_memory_kind or None,
            "based_on_memory_id": prioritized_memory_id or None,
            "based_on_batch_id": prioritized_batch_id or None,
            "based_on_generation_range": prioritized_generation_range or None,
            "based_on_best_generations": list(
                prioritized_generation_range.get("best_generations")
                or prioritized_generation_range.get("generation_event_ids")
                or []
            ),
            "parameter_reasoning": {
                "repeat": f"derived from average repetition {repeat_mean:.2f} and adjusted around official-history stability",
                "parity": f"derived from average odd/even {average_odd:.2f}/{average_even:.2f} and validated parity families {preferred_pairs}",
                "sequence": f"derived from average sequence max {sequence_mean:.2f} with controlled ceiling {sequence_cap}",
                "coverage": f"derived from average coverage {coverage_mean:.2f} with floor {coverage_floor:.2f}",
                "entropy": f"derived from average entropy {entropy_mean:.2f} with floor {entropy_floor:.2f}",
                "core_numbers": f"top recurring numbers from official history: {list(core_numbers)}",
                "discouraged_numbers": f"least frequent numbers from official history: {list(discouraged_numbers)}",
                "frequency": f"observed history frequencies guided cap {observed_max_frequency:.2f} and floor {observed_min_frequency:.2f}",
                "selection": selection_reason,
            },
            "history_profile": {
                "contest_count": history_count,
                "window_size": int(
                    profile.get("window_size", 0) or profile_window or 0
                ),
                "average_repetition": repeat_mean,
                "average_sequence_max": sequence_mean,
                "average_coverage": coverage_mean,
                "average_entropy": entropy_mean,
                "average_parity_odd": average_odd,
                "average_parity_even": average_even,
                "dominant_numbers": profile.get("dominant_numbers", []),
                "discouraged_numbers": profile.get("discouraged_numbers", []),
                "source": profile.get("source", "imported_contests"),
            },
        }
        return policy_discovery

    def get_scientific_generation_policy(self, game_size: int) -> dict[str, Any]:
        discovery = self.discover_scientific_generation_policy(game_size)
        return dict(discovery.get("policy") or {})

    def _normalize_contest(
        self,
        contest: dict[str, Any] | Sequence[int],
        *,
        contest_number: int,
    ) -> dict[str, Any]:
        if isinstance(contest, dict):
            numbers = _normalize_numbers(
                contest.get("numbers", contest.get("dezenas", []))
            )
            number = (
                _safe_int(
                    contest.get("contest_number", contest.get("concurso")),
                    default=contest_number,
                )
                or contest_number
            )
            draw_date = str(contest.get("draw_date", contest.get("data", "")) or "")
            return {
                "contest_number": int(number),
                "draw_date": draw_date,
                "numbers": numbers,
            }
        numbers = _normalize_numbers(contest)
        return {
            "contest_number": int(contest_number),
            "draw_date": "",
            "numbers": numbers,
        }

    def _profile_from_contests(
        self,
        contests: Sequence[dict[str, Any]],
        transitions: Sequence[dict[str, Any]],
    ) -> dict[str, Any]:
        contest_numbers = [int(item.get("contest_number", 0) or 0) for item in contests]
        frequency_map = _frequency_map(contests)
        ordered_frequency = sorted(
            frequency_map.items(), key=lambda item: (-item[1], item[0])
        )
        dominant_numbers = [
            {"number": number, "frequency": frequency}
            for number, frequency in ordered_frequency[:10]
        ]
        discouraged_numbers = [
            number
            for number, _ in sorted(
                frequency_map.items(), key=lambda item: (item[1], item[0])
            )[:6]
        ]

        repeats = [int(item.get("overlap", 0) or 0) for item in transitions]
        parity_distribution = Counter(
            f"{odd}/{even}"
            for odd, even in (
                _parity_pair(item.get("numbers", [])) for item in contests
            )
        )
        low_high_distribution = Counter(
            f"{low}/{high}"
            for low, high in (
                _low_high_pair(item.get("numbers", [])) for item in contests
            )
        )
        sequence_distribution = Counter(
            str(
                int(
                    calculate_sequence_stats(
                        _normalize_numbers(item.get("numbers", []))
                    )["largest_sequence"]
                )
            )
            for item in contests
        )
        coverage_distribution = Counter(
            str(
                len(
                    [
                        amount
                        for amount in _band_distribution(
                            _normalize_numbers(item.get("numbers", []))
                        )
                        if amount > 0
                    ]
                )
            )
            for item in contests
        )
        band_distribution = Counter()
        for contest in contests:
            for band_index, amount in enumerate(
                _band_distribution(_normalize_numbers(contest.get("numbers", []))),
                start=1,
            ):
                band_distribution[f"band_{band_index}"] += int(amount)

        latest_contest = contests[-1] if contests else {}
        latest_numbers = _normalize_numbers(latest_contest.get("numbers", []))
        latest_draw = type(
            "LotofacilDrawLike",
            (),
            {
                "contest": int(latest_contest.get("contest_number", 0) or 0),
                "numbers": latest_numbers,
            },
        )()
        ordered_draws = _contests_to_draws(contests)
        line_distribution = (
            calculate_line_distribution(latest_draw) if latest_numbers else {}
        )
        column_distribution = (
            calculate_column_distribution(latest_draw) if latest_numbers else {}
        )
        delay_metrics = {
            "current_delays": calculate_delays(ordered_draws) if ordered_draws else {},
            "hot_cold_numbers": calculate_hot_cold_numbers(ordered_draws)
            if ordered_draws
            else {},
            "repeated_numbers": calculate_repeated_numbers(ordered_draws)
            if ordered_draws
            else {},
        }
        return_metrics = delay_metrics["repeated_numbers"]
        frequency_windows = {
            "full_history": _window_frequency_map(contests, None),
            "window_300": _window_frequency_map(contests, 300),
            "window_100": _window_frequency_map(contests, 100),
            "window_50": _window_frequency_map(contests, 50),
            "window_30": _window_frequency_map(contests, 30),
            "window_10": _window_frequency_map(contests, 10),
        }
        return ScientificHistoryProfile(
            source="imported_contests"
            if any(item.get("source") == "imported_contests" for item in contests)
            else "historico_lotofacil.csv",
            window_size=len(contests),
            contest_count=len(self.contests),
            contest_numbers=tuple(contest_numbers),
            repeat_distribution={
                str(value): int(amount)
                for value, amount in sorted(Counter(repeats).items())
            },
            parity_distribution={
                key: int(amount) for key, amount in sorted(parity_distribution.items())
            },
            low_high_distribution={
                key: int(amount)
                for key, amount in sorted(low_high_distribution.items())
            },
            sequence_distribution={
                key: int(amount)
                for key, amount in sorted(
                    sequence_distribution.items(), key=lambda item: int(item[0])
                )
            },
            coverage_distribution={
                key: int(amount)
                for key, amount in sorted(
                    coverage_distribution.items(), key=lambda item: int(item[0])
                )
            },
            band_distribution={
                key: int(amount)
                for key, amount in sorted(
                    band_distribution.items(),
                    key=lambda item: int(item[0].split("_", 1)[1]),
                )
            },
            average_repetition=_mean_or_zero(repeats),
            average_parity_odd=_mean_or_zero(
                [_parity_pair(item.get("numbers", []))[0] for item in contests]
            ),
            average_parity_even=_mean_or_zero(
                [_parity_pair(item.get("numbers", []))[1] for item in contests]
            ),
            average_low=_mean_or_zero(
                [_low_high_pair(item.get("numbers", []))[0] for item in contests]
            ),
            average_high=_mean_or_zero(
                [_low_high_pair(item.get("numbers", []))[1] for item in contests]
            ),
            average_sequence_max=_mean_or_zero(
                [
                    int(
                        calculate_sequence_stats(
                            _normalize_numbers(item.get("numbers", []))
                        )["largest_sequence"]
                    )
                    for item in contests
                ]
            ),
            average_coverage=_mean_or_zero(
                [
                    _coverage_score(_normalize_numbers(item.get("numbers", [])))
                    for item in contests
                ]
            ),
            average_entropy=_mean_or_zero(
                [
                    _entropy_score(_normalize_numbers(item.get("numbers", [])))
                    for item in contests
                ]
            ),
            frequency_windows=frequency_windows,
            dominant_numbers=dominant_numbers,
            discouraged_numbers=discouraged_numbers,
            transitions=list(transitions),
            number_frequency={
                str(number): int(amount)
                for number, amount in sorted(frequency_map.items())
            },
            hot_cold_numbers=delay_metrics["hot_cold_numbers"],
            delay_metrics=dict(delay_metrics),
            return_metrics=return_metrics,
            latest_line_distribution=dict(line_distribution),
            latest_column_distribution=dict(column_distribution),
        ).as_dict()


def analyze_lotofacil_history(
    contests: Sequence[dict[str, Any]] | None = None,
    *,
    db_path: Any = DEFAULT_DATABASE_PATH,
    window_size: int | None = 100,
) -> dict[str, Any]:
    core = LotofacilScientificCore(contests=contests, db_path=db_path)
    return core.analyze_lotofacil_history(window_size=window_size)


def analyze_contest_transition(
    previous_contest: dict[str, Any] | Sequence[int],
    current_contest: dict[str, Any] | Sequence[int],
) -> dict[str, Any]:
    core = LotofacilScientificCore(contests=[])
    return core.analyze_contest_transition(previous_contest, current_contest)


def build_scientific_profile(
    window_size: int = 100,
    *,
    contests: Sequence[dict[str, Any]] | None = None,
    db_path: Any = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    core = LotofacilScientificCore(contests=contests, db_path=db_path)
    return core.build_scientific_profile(window_size=window_size)


def discover_scientific_generation_policy(
    game_size: int,
    *,
    contests: Sequence[dict[str, Any]] | None = None,
    db_path: Any = DEFAULT_DATABASE_PATH,
    candidate_limit: int = 120,
    use_csv_fallback: bool = True,
) -> dict[str, Any]:
    core = LotofacilScientificCore(
        contests=contests,
        db_path=db_path,
        use_csv_fallback=use_csv_fallback,
    )
    return core.discover_scientific_generation_policy(
        game_size, candidate_limit=candidate_limit
    )


def get_scientific_generation_policy(
    game_size: int,
    *,
    contests: Sequence[dict[str, Any]] | None = None,
    db_path: Any = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    core = LotofacilScientificCore(contests=contests, db_path=db_path)
    return core.get_scientific_generation_policy(game_size)


def build_post_reconciliation_scientific_memory(
    *,
    generation_event_id: int,
    batch_id: str,
    contest: dict[str, Any],
    games: Sequence[dict[str, Any]],
    reconciliation_results: Sequence[dict[str, Any]] | None = None,
    policy_before: dict[str, Any] | None = None,
    policy_after: dict[str, Any] | None = None,
    contests: Sequence[dict[str, Any]] | None = None,
    db_path: Any = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    core = LotofacilScientificCore(contests=contests, db_path=db_path)
    return core.build_post_reconciliation_scientific_memory(
        generation_event_id=generation_event_id,
        batch_id=batch_id,
        contest=contest,
        games=games,
        reconciliation_results=reconciliation_results,
        policy_before=policy_before,
        policy_after=policy_after,
    )


def build_strong_near_miss_scientific_memory(
    *,
    batch_id: str,
    contest: dict[str, Any],
    generation_results: Sequence[dict[str, Any]],
    policy_before: dict[str, Any] | None = None,
    policy_after: dict[str, Any] | None = None,
    contests: Sequence[dict[str, Any]] | None = None,
    db_path: Any = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    core = LotofacilScientificCore(contests=contests, db_path=db_path)
    return core.build_strong_near_miss_scientific_memory(
        batch_id=batch_id,
        contest=contest,
        generation_results=generation_results,
        policy_before=policy_before,
        policy_after=policy_after,
    )


def build_batch_reconciliation_scientific_memory(
    *,
    batch_id: str,
    contest: dict[str, Any],
    generation_results: Sequence[dict[str, Any]],
    policy_before: dict[str, Any] | None = None,
    policy_after: dict[str, Any] | None = None,
    contests: Sequence[dict[str, Any]] | None = None,
    db_path: Any = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    core = LotofacilScientificCore(contests=contests, db_path=db_path)
    return core.build_batch_reconciliation_scientific_memory(
        batch_id=batch_id,
        contest=contest,
        generation_results=generation_results,
        policy_before=policy_before,
        policy_after=policy_after,
    )
