from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from collections import Counter
from dataclasses import dataclass
from math import log2, sqrt
from itertools import product
from statistics import mean, median
from typing import Any, Iterable, Sequence

from sqlalchemy import select

from lotoia.data.loader import load_draws_csv
from lotoia.database.database import (
    DEFAULT_DATABASE_PATH,
    ImportedContest,
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


def _unique_ints(values: Sequence[int | float | None], *, lower: int, upper: int) -> list[int]:
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


def _unique_float_values(values: Sequence[float | int | None], *, lower: float, upper: float) -> list[float]:
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
    entropy = -sum((amount / total) * log2(amount / total) for amount in bands if amount)
    max_entropy = log2(len([amount for amount in bands if amount])) if sum(1 for amount in bands if amount) > 1 else 1.0
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


def _window_frequency_map(contests: Sequence[dict[str, Any]], window_size: int | None) -> dict[str, int]:
    windowed = _window_contests(contests, window_size)
    return {str(number): int(amount) for number, amount in sorted(_frequency_map(windowed).items())}


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
            "frequency_windows": {window: dict(values) for window, values in self.frequency_windows.items()},
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
            "preferred_parity_pairs": [list(pair) for pair in self.preferred_parity_pairs],
            "allowed_parity_pairs": [list(pair) for pair in self.allowed_parity_pairs],
            "sequence_max": self.sequence_max,
            "coverage_min": self.coverage_min,
            "entropy_min": self.entropy_min,
            "core_numbers": list(self.core_numbers),
            "discouraged_numbers": list(self.discouraged_numbers),
            "max_frequency_ratio": self.max_frequency_ratio,
            "min_frequency_ratio": self.min_frequency_ratio,
            "preferred_profile_ratios": {
                f"{pair[0]}/{pair[1]}": ratio for pair, ratio in self.preferred_profile_ratios.items()
            },
            "notes": list(self.notes),
        }


def _contest_record_from_db(row: Any) -> OfficialContestRecord:
    numbers = _normalize_numbers(str(getattr(row, "dezenas", "") or "").replace(",", " ").split())
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
    numbers = _normalize_numbers(str(getattr(row, "numbers", "") or "").replace(",", " ").split())
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
                select(LotofacilOfficialHistory).order_by(LotofacilOfficialHistory.contest_number.asc())
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
                    select(ImportedContest).order_by(ImportedContest.contest_number.asc())
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

    contests = sorted(contests, key=lambda item: int(item.get("contest_number", 0) or 0))
    if limit is not None and int(limit) > 0:
        contests = contests[-int(limit):]
    return contests


def _mean_or_zero(values: Sequence[float]) -> float:
    cleaned = [float(value) for value in values if value is not None]
    return round(mean(cleaned), 4) if cleaned else 0.0


def _build_transition(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
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
        line_distribution=calculate_line_distribution(type("DrawLike", (), {"numbers": current_numbers})()),
        column_distribution=calculate_column_distribution(type("DrawLike", (), {"numbers": current_numbers})()),
    )
    return transition.as_dict()


def _window_contests(contests: Sequence[dict[str, Any]], window_size: int | None) -> list[dict[str, Any]]:
    ordered = sorted(contests, key=lambda item: int(item.get("contest_number", 0) or 0))
    if window_size is not None and int(window_size) > 0:
        return ordered[-int(window_size):]
    return ordered


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
        self._contests = [dict(contest) for contest in contests] if contests is not None else None

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

    def analyze_lotofacil_history(self, window_size: int | None = None) -> dict[str, Any]:
        contests = _window_contests(self.contests, window_size)
        transitions = [
            _build_transition(previous, current)
            for previous, current in zip(contests, contests[1:], strict=False)
        ]
        profile = self._profile_from_contests(contests, transitions)
        return {
            "source": "imported_contests" if any(item.get("source") == "imported_contests" for item in contests) else "historico_lotofacil.csv",
            "window_size": len(contests),
            "history_size": len(self.contests),
            "contest_numbers": [int(item.get("contest_number", 0) or 0) for item in contests],
            "profile": profile,
            "transitions": transitions,
            "summary": {
                "contest_count": len(contests),
                "transition_count": len(transitions),
                "average_overlap": _mean_or_zero([float(item["overlap"]) for item in transitions]),
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
                    "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else "",
                    "memory_kind": _safe_str(getattr(row, "memory_kind", "")),
                    "strategy_name": _safe_str(getattr(row, "strategy_name", "")),
                    "game_size": int(getattr(row, "game_size", 0) or 0),
                    "batch_id": _safe_str(getattr(row, "batch_id", "")),
                    "generation_range": dict(getattr(row, "generation_range", {}) or {}),
                    "total_games": int(getattr(row, "total_games", 0) or 0),
                    "unique_games": int(getattr(row, "unique_games", 0) or 0),
                    "duplicate_games": int(getattr(row, "duplicate_games", 0) or 0),
                    "structural_status": _safe_str(getattr(row, "structural_status", "")),
                    "scientific_status": _safe_str(getattr(row, "scientific_status", "")),
                    "scientific_classification": _safe_str(getattr(row, "scientific_classification", "")),
                    "main_reason": _safe_str(getattr(row, "main_reason", "")),
                    "recommended_action": _safe_str(getattr(row, "recommended_action", "")),
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
                    "validation_contests": list(getattr(row, "validation_contests", []) or []),
                    "cross_validation_summary": dict(getattr(row, "cross_validation_summary", {}) or {}),
                    "frequency_alerts": list(getattr(row, "frequency_alerts", []) or []),
                    "absence_alerts": list(getattr(row, "absence_alerts", []) or []),
                    "parity_alerts": list(getattr(row, "parity_alerts", []) or []),
                    "repetition_alerts": list(getattr(row, "repetition_alerts", []) or []),
                    "sequence_alerts": list(getattr(row, "sequence_alerts", []) or []),
                    "low_high_alerts": list(getattr(row, "low_high_alerts", []) or []),
                    "range_alerts": list(getattr(row, "range_alerts", []) or []),
                    "decision_mode": _safe_str(getattr(row, "decision_mode", "OBSERVACAO"), "OBSERVACAO"),
                    "approved_for_use": bool(getattr(row, "approved_for_use", 0) or 0),
                    "notes": _safe_str(getattr(row, "notes", "")),
                    "official_history_count": int(getattr(row, "official_history_count", 0) or 0),
                    "official_history_first_contest": getattr(row, "official_history_first_contest", None),
                    "official_history_last_contest": getattr(row, "official_history_last_contest", None),
                    "official_history_window": list(getattr(row, "official_history_window", []) or []),
                    "source": _safe_str(getattr(row, "source", "scientific_calibration"), "scientific_calibration"),
                }
            )
        return memory_rows

    def _load_scientific_calibration_decisions(self, *, limit: int = 5) -> list[dict[str, Any]]:
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
                    "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else "",
                    "strategy": _safe_str(getattr(row, "strategy", "")),
                    "game_size": int(getattr(row, "game_size", 0) or 0),
                    "source_batch_id": _safe_str(getattr(row, "source_batch_id", "")),
                    "source_generation_range": dict(getattr(row, "source_generation_range", {}) or {}),
                    "structural_status": _safe_str(getattr(row, "structural_status", "")),
                    "scientific_status": _safe_str(getattr(row, "scientific_status", "")),
                    "classification": _safe_str(getattr(row, "classification", "")),
                    "main_reason": _safe_str(getattr(row, "main_reason", "")),
                    "recommended_action": _safe_str(getattr(row, "recommended_action", "")),
                    "policy_before": dict(getattr(row, "policy_before", {}) or {}),
                    "policy_after": dict(getattr(row, "policy_after", {}) or {}),
                    "mode": _safe_str(getattr(row, "mode", "OBSERVACAO"), "OBSERVACAO"),
                    "applied": bool(getattr(row, "applied", 0) or 0),
                    "approved_by": _safe_str(getattr(row, "approved_by", "")),
                    "notes": _safe_str(getattr(row, "notes", "")),
                }
            )
        return decisions

    def discover_scientific_generation_policy(
        self,
        game_size: int,
        *,
        candidate_limit: int = 120,
    ) -> dict[str, Any]:
        resolved_game_size = max(2, min(int(game_size or 15), 25))
        profile_window = max(20, min(len(self.contests), max(60, resolved_game_size * 4))) if self.contests else 0
        profile = self.build_scientific_profile(window_size=profile_window) if self.contests else {}
        history_count = int(profile.get("contest_count", len(self.contests)) or len(self.contests))
        frequency_map = {int(number): int(amount) for number, amount in (profile.get("number_frequency", {}) or {}).items() if int(_safe_int(number, default=0) or 0) > 0}
        dominant_numbers = [int(item.get("number", 0) or 0) for item in profile.get("dominant_numbers", []) if int(item.get("number", 0) or 0) > 0]
        core_numbers = tuple(dominant_numbers[:4]) if dominant_numbers else tuple(range(1, min(4, resolved_game_size) + 1))
        discouraged_numbers = tuple(
            sorted(
                {number for number in range(1, 26)} - set(core_numbers),
                key=lambda number: (int(profile.get("number_frequency", {}).get(str(number), 0) or 0), number),
            )[:6]
        )
        raw_repeat_mean = float(profile.get("average_repetition", max(1.0, resolved_game_size / 2)) or max(1.0, resolved_game_size / 2))
        repeat_mean = min(raw_repeat_mean, max(1.0, resolved_game_size / 2))
        raw_sequence_mean = float(profile.get("average_sequence_max", max(4.0, resolved_game_size / 3)) or max(4.0, resolved_game_size / 3))
        sequence_mean = min(raw_sequence_mean, max(4.0, resolved_game_size / 3 + 1.0))
        coverage_mean = float(profile.get("average_coverage", 0.35) or 0.35)
        entropy_mean = float(profile.get("average_entropy", 0.35) or 0.35)
        average_odd = float(profile.get("average_parity_odd", (resolved_game_size + 1) / 2) or ((resolved_game_size + 1) / 2))
        average_even = float(profile.get("average_parity_even", resolved_game_size / 2) or (resolved_game_size / 2))
        repeat_floor = max(0, int(round(repeat_mean)) - 1)
        repeat_ceiling = min(resolved_game_size, int(round(repeat_mean)) + 2)
        sequence_cap = max(4, int(round(sequence_mean + 1.0)))
        coverage_floor = max(0.30, min(0.75, round(coverage_mean, 2)))
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
            preferred_pairs = [(resolved_game_size // 2, resolved_game_size - (resolved_game_size // 2))]
        allowed_pairs = []
        for odd_count, even_count in preferred_pairs:
            for delta in (0, -1, 1):
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

        def _paired_profile_ratios(pairs: Sequence[tuple[int, int]]) -> dict[tuple[int, int], float]:
            if not pairs:
                return {}
            if len(pairs) == 1:
                return {tuple(pairs[0]): 1.0}
            weights = [1.0 / (index + 1) for index in range(len(pairs))]
            total = sum(weights) or 1.0
            return {tuple(pair): round(weight / total, 4) for pair, weight in zip(pairs, weights, strict=False)}

        def _policy_signature(policy: Mapping[str, Any]) -> str:
            payload = {
                "game_size": resolved_game_size,
                "repeat_min": int(policy.get("repeat_min", 0) or 0),
                "repeat_max": int(policy.get("repeat_max", 0) or 0),
                "preferred_parity_pairs": list(policy.get("preferred_parity_pairs", []) or []),
                "allowed_parity_pairs": list(policy.get("allowed_parity_pairs", []) or []),
                "sequence_max": int(policy.get("sequence_max", 0) or 0),
                "coverage_min": float(policy.get("coverage_min", 0.0) or 0.0),
                "entropy_min": float(policy.get("entropy_min", 0.0) or 0.0),
                "core_numbers": list(policy.get("core_numbers", []) or []),
                "discouraged_numbers": list(policy.get("discouraged_numbers", []) or []),
                "max_frequency_ratio": float(policy.get("max_frequency_ratio", 0.0) or 0.0),
                "min_frequency_ratio": float(policy.get("min_frequency_ratio", 0.0) or 0.0),
            }
            return hashlib.sha1(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:12]

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
                source=str(profile.get("source", "imported_contests") or "imported_contests"),
                contest_count=int(profile.get("contest_count", len(self.contests)) or len(self.contests)),
                repeat_min=max(0, min(resolved_game_size, int(repeat_min))),
                repeat_max=max(0, min(resolved_game_size, int(repeat_max))),
                preferred_parity_pairs=tuple(tuple(pair) for pair in preferred),
                allowed_parity_pairs=tuple(tuple(pair) for pair in allowed),
                sequence_max=max(1, min(resolved_game_size, int(sequence_max))),
                coverage_min=float(coverage_min),
                entropy_min=float(entropy_min),
                core_numbers=tuple(int(number) for number in core_numbers),
                discouraged_numbers=tuple(int(number) for number in discouraged_numbers),
                max_frequency_ratio=float(max_frequency_ratio),
                min_frequency_ratio=float(min_frequency_ratio),
                preferred_profile_ratios=_paired_profile_ratios(preferred),
                notes=tuple(notes),
            ).as_dict()
            policy["policy_variant"] = variant_name
            policy["policy_origin"] = "automatic_scientific_discovery"
            policy["policy_signature"] = hashlib.sha1(json.dumps(policy, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:12]
            return policy

        base_repeat_center = int(round(repeat_mean or max(1.0, resolved_game_size / 2)))
        observed_max_frequency = min(0.80, max(0.55, round((max(frequency_map.values()) / max(1, history_count)) + 0.05, 2))) if frequency_map else max_frequency_cap
        observed_min_frequency = min(0.30, max(0.10, round((min((amount for amount in frequency_map.values() if amount > 0), default=0) / max(1, history_count)) or 0.20, 2))) if frequency_map else min_frequency_floor
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
            parity_families[0] = [(resolved_game_size // 2, resolved_game_size - (resolved_game_size // 2))]
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
            max_frequency_ratio=observed_max_frequency if 'observed_max_frequency' in locals() else max_frequency_cap,
            min_frequency_ratio=observed_min_frequency if 'observed_min_frequency' in locals() else min_frequency_floor,
            notes=("automatic_discovery_seed", "derived_from_official_history"),
            variant_name="history_profile_seed",
        )

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
                "repeat_min": int(policy.get("repeat_min", repeat_floor) or repeat_floor),
                "repeat_max": int(policy.get("repeat_max", repeat_ceiling) or repeat_ceiling),
                "preferred": preferred_pairs_local,
                "allowed": allowed_pairs_local,
                "sequence_max": int(policy.get("sequence_max", sequence_cap) or sequence_cap),
                "coverage_min": float(policy.get("coverage_min", coverage_floor) or coverage_floor),
                "entropy_min": float(policy.get("entropy_min", entropy_floor) or entropy_floor),
                "max_frequency_ratio": float(policy.get("max_frequency_ratio", observed_max_frequency) or observed_max_frequency),
                "min_frequency_ratio": float(policy.get("min_frequency_ratio", observed_min_frequency) or observed_min_frequency),
                "notes": tuple(str(note) for note in policy.get("notes", ()) or ()),
            }

        memory_rows = self._load_scientific_memory_rows(limit=max(5, int(candidate_limit or 6)))
        decision_rows = self._load_scientific_calibration_decisions(limit=max(5, int(candidate_limit or 6)))
        latest_memory = memory_rows[0] if memory_rows else {}
        approved_memory = next((row for row in memory_rows if bool(row.get("approved_for_use")) and row.get("policy_after")), {})
        latest_decision = decision_rows[0] if decision_rows else {}
        memory_policy = dict(approved_memory.get("policy_after") or latest_memory.get("policy_after") or {})
        if memory_policy:
            memory_policy = {
                **base_policy,
                **{key: value for key, value in memory_policy.items() if key in base_policy},
                "policy_variant": "memory_blend",
                "policy_origin": "scientific_memory",
            }
        else:
            memory_policy = {}

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
        if memory_policy:
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
                                        if sequence_max < max(4, resolved_game_size // 4):
                                            continue
                                        variant_name = (
                                            "history_profile"
                                            if family_index == 1 and repeat_min == repeat_floor and repeat_max == repeat_ceiling and sequence_max == sequence_cap
                                            else f"auto_{family_index}_{repeat_min}_{repeat_max}_{sequence_max}"
                                        )
                                        candidate_variants.append(
                                            (
                                                variant_name,
                                                {
                                                    "repeat_min": repeat_min,
                                                    "repeat_max": repeat_max,
                                                    "preferred": parity_family,
                                                    "allowed": allowed_pairs if family_index == 1 else parity_family,
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
                                        if len(candidate_variants) >= max(20, int(candidate_limit or 120)):
                                            break
                                    if len(candidate_variants) >= max(20, int(candidate_limit or 120)):
                                        break
                                if len(candidate_variants) >= max(20, int(candidate_limit or 120)):
                                    break
                            if len(candidate_variants) >= max(20, int(candidate_limit or 120)):
                                break
                        if len(candidate_variants) >= max(20, int(candidate_limit or 120)):
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
                notes=tuple(params.get("notes", ())) + tuple(f"{key}={value}" for key, value in extra.items()),
                variant_name=variant_name,
            )
            candidate_signature = _policy_signature(candidate_policy)
            if candidate_signature in rejected_policy_signatures:
                candidate_policy["policy_variant"] = f"{variant_name}_rejected_by_guardian"
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
            max_frequency_ratio = float(candidate.get("max_frequency_ratio", 0.0) or 0.0)
            min_frequency_ratio = float(candidate.get("min_frequency_ratio", 0.0) or 0.0)
            candidate_preferred = [tuple(int(part) for part in pair) for pair in candidate.get("preferred_parity_pairs", []) or []]
            candidate_allowed = [tuple(int(part) for part in pair) for pair in candidate.get("allowed_parity_pairs", []) or []]
            candidate_core = [int(number) for number in candidate.get("core_numbers", []) or []]
            candidate_discouraged = [int(number) for number in candidate.get("discouraged_numbers", []) or []]

            acceptance_errors: list[str] = []
            if candidate.get("policy_variant") == "history_profile_seed" and history_count >= 60:
                acceptance_errors.append("seed_policy_requires_validation")
            if resolved_game_size == 15 and history_count >= 60:
                if repeat_min < 7 or repeat_max > 10:
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
            if any(sum(pair) != resolved_game_size for pair in candidate_preferred + candidate_allowed):
                acceptance_errors.append("parity_sum_mismatch")
            if not candidate_core:
                acceptance_errors.append("no_core_numbers")
            if max_frequency_ratio < 0.50 or max_frequency_ratio > 0.85:
                acceptance_errors.append("frequency_cap_out_of_bounds")
            if min_frequency_ratio < 0.05 or min_frequency_ratio > 0.35:
                acceptance_errors.append("frequency_floor_out_of_bounds")
            if coverage_min < 0.30 or coverage_min > 0.85:
                acceptance_errors.append("coverage_out_of_bounds")
            if entropy_min < 0.25 or entropy_min > 0.85:
                acceptance_errors.append("entropy_out_of_bounds")
            if sequence_max < 4:
                acceptance_errors.append("sequence_limit_too_low")
            if repeat_min < 0 or repeat_max > resolved_game_size:
                acceptance_errors.append("repeat_out_of_bounds")
            if sequence_max > resolved_game_size:
                acceptance_errors.append("sequence_limit_too_high")

            preferred_pair_match = target_pair in candidate_preferred or tuple(reversed(target_pair)) in candidate_preferred
            parity_penalty = 0.0 if preferred_pair_match else 12.0
            if not preferred_pair_match and target_pair_set.intersection(candidate_allowed):
                parity_penalty = 4.0
            core_overlap = len(dominant_set.intersection(candidate_core[:4]))
            discouraged_overlap = len(set(candidate_discouraged[:6]).intersection(set(candidate_discouraged[:6])))
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
                "official_history_first_contest": int(self.contests[0].get("contest_number", 0) or 0) if self.contests else None,
                "official_history_last_contest": int(self.contests[-1].get("contest_number", 0) or 0) if self.contests else None,
                "scientific_memory_count": len(memory_rows),
                "scientific_decision_count": len(decision_rows),
                "scientific_memory_latest": latest_memory,
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
                "rejected_by_rules": sum(1 for item in scored_candidates if item["acceptance_errors"]),
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
                    "window_size": int(profile.get("window_size", 0) or profile_window or 0),
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
        selected_candidate = min(accepted_candidates, key=lambda item: (float(item["score"]), int(item["rank"])))
        selected_policy = dict(selected_candidate["policy"])
        selected_policy["policy_origin"] = "automatic_scientific_discovery"
        selected_policy["policy_variant"] = str(selected_candidate["variant"])
        selected_policy["policy_signature"] = hashlib.sha1(
            json.dumps(
                {
                    "game_size": resolved_game_size,
                    "repeat_min": int(selected_policy.get("repeat_min", 0) or 0),
                    "repeat_max": int(selected_policy.get("repeat_max", 0) or 0),
                    "preferred_parity_pairs": selected_policy.get("preferred_parity_pairs", []),
                    "allowed_parity_pairs": selected_policy.get("allowed_parity_pairs", []),
                    "sequence_max": int(selected_policy.get("sequence_max", 0) or 0),
                    "coverage_min": float(selected_policy.get("coverage_min", 0.0) or 0.0),
                    "entropy_min": float(selected_policy.get("entropy_min", 0.0) or 0.0),
                    "core_numbers": selected_policy.get("core_numbers", []),
                    "discouraged_numbers": selected_policy.get("discouraged_numbers", []),
                    "max_frequency_ratio": float(selected_policy.get("max_frequency_ratio", 0.0) or 0.0),
                    "min_frequency_ratio": float(selected_policy.get("min_frequency_ratio", 0.0) or 0.0),
                },
                sort_keys=True,
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()[:12]
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
            "policy_origin": "automatic_scientific_discovery",
            "policies_tested": len(candidate_variants),
            "validation_window": int(profile_window or len(self.contests)),
            "official_history_count": history_count,
            "official_history_first_contest": int(self.contests[0].get("contest_number", 0) or 0) if self.contests else None,
            "official_history_last_contest": int(self.contests[-1].get("contest_number", 0) or 0) if self.contests else None,
            "scientific_memory_count": len(memory_rows),
            "scientific_decision_count": len(decision_rows),
            "scientific_memory_latest": latest_memory,
            "scientific_memory_latest_approved": approved_memory,
            "scientific_decision_latest": latest_decision,
            "selection_rank": int(selected_candidate["rank"]),
            "selection_variant": str(selected_candidate["variant"]),
            "selection_reason": selection_reason,
            "selection_status": "POLICY_SELECTED",
            "candidate_count": len(candidate_variants),
            "selection_score": float(selected_candidate["score"]),
            "selected_at": datetime.now(timezone.utc).isoformat(),
            "candidates_tested": scored_candidates,
            "approved_candidates": [item for item in scored_candidates if item["accepted"]],
            "rejected_by_guardian": rejected_by_guardian_count,
            "rejected_by_rules": sum(1 for item in scored_candidates if item["acceptance_errors"]),
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
                "window_size": int(profile.get("window_size", 0) or profile_window or 0),
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
            numbers = _normalize_numbers(contest.get("numbers", contest.get("dezenas", [])))
            number = _safe_int(contest.get("contest_number", contest.get("concurso")), default=contest_number) or contest_number
            draw_date = str(contest.get("draw_date", contest.get("data", "")) or "")
            return {"contest_number": int(number), "draw_date": draw_date, "numbers": numbers}
        numbers = _normalize_numbers(contest)
        return {"contest_number": int(contest_number), "draw_date": "", "numbers": numbers}

    def _profile_from_contests(
        self,
        contests: Sequence[dict[str, Any]],
        transitions: Sequence[dict[str, Any]],
    ) -> dict[str, Any]:
        contest_numbers = [int(item.get("contest_number", 0) or 0) for item in contests]
        frequency_map = _frequency_map(contests)
        ordered_frequency = sorted(frequency_map.items(), key=lambda item: (-item[1], item[0]))
        dominant_numbers = [{"number": number, "frequency": frequency} for number, frequency in ordered_frequency[:10]]
        discouraged_numbers = [number for number, _ in sorted(frequency_map.items(), key=lambda item: (item[1], item[0]))[:6]]

        repeats = [int(item.get("overlap", 0) or 0) for item in transitions]
        parity_distribution = Counter(
            f"{odd}/{even}" for odd, even in (_parity_pair(item.get("numbers", [])) for item in contests)
        )
        low_high_distribution = Counter(
            f"{low}/{high}" for low, high in (_low_high_pair(item.get("numbers", [])) for item in contests)
        )
        sequence_distribution = Counter(
            str(int(calculate_sequence_stats(_normalize_numbers(item.get("numbers", [])))["largest_sequence"]))
            for item in contests
        )
        coverage_distribution = Counter(
            str(len([amount for amount in _band_distribution(_normalize_numbers(item.get("numbers", []))) if amount > 0]))
            for item in contests
        )
        band_distribution = Counter()
        for contest in contests:
            for band_index, amount in enumerate(_band_distribution(_normalize_numbers(contest.get("numbers", []))), start=1):
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
        line_distribution = calculate_line_distribution(latest_draw) if latest_numbers else {}
        column_distribution = calculate_column_distribution(latest_draw) if latest_numbers else {}
        delay_metrics = {
            "current_delays": calculate_delays(ordered_draws) if ordered_draws else {},
            "hot_cold_numbers": calculate_hot_cold_numbers(ordered_draws) if ordered_draws else {},
            "repeated_numbers": calculate_repeated_numbers(ordered_draws) if ordered_draws else {},
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
            source="imported_contests" if any(item.get("source") == "imported_contests" for item in contests) else "historico_lotofacil.csv",
            window_size=len(contests),
            contest_count=len(self.contests),
            contest_numbers=tuple(contest_numbers),
            repeat_distribution={str(value): int(amount) for value, amount in sorted(Counter(repeats).items())},
            parity_distribution={key: int(amount) for key, amount in sorted(parity_distribution.items())},
            low_high_distribution={key: int(amount) for key, amount in sorted(low_high_distribution.items())},
            sequence_distribution={key: int(amount) for key, amount in sorted(sequence_distribution.items(), key=lambda item: int(item[0]))},
            coverage_distribution={key: int(amount) for key, amount in sorted(coverage_distribution.items(), key=lambda item: int(item[0]))},
            band_distribution={key: int(amount) for key, amount in sorted(band_distribution.items(), key=lambda item: int(item[0].split("_", 1)[1]))},
            average_repetition=_mean_or_zero(repeats),
            average_parity_odd=_mean_or_zero([_parity_pair(item.get("numbers", []))[0] for item in contests]),
            average_parity_even=_mean_or_zero([_parity_pair(item.get("numbers", []))[1] for item in contests]),
            average_low=_mean_or_zero([_low_high_pair(item.get("numbers", []))[0] for item in contests]),
            average_high=_mean_or_zero([_low_high_pair(item.get("numbers", []))[1] for item in contests]),
            average_sequence_max=_mean_or_zero([int(calculate_sequence_stats(_normalize_numbers(item.get("numbers", [])))["largest_sequence"]) for item in contests]),
            average_coverage=_mean_or_zero([_coverage_score(_normalize_numbers(item.get("numbers", []))) for item in contests]),
            average_entropy=_mean_or_zero([_entropy_score(_normalize_numbers(item.get("numbers", []))) for item in contests]),
            frequency_windows=frequency_windows,
            dominant_numbers=dominant_numbers,
            discouraged_numbers=discouraged_numbers,
            transitions=list(transitions),
            number_frequency={str(number): int(amount) for number, amount in sorted(frequency_map.items())},
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
) -> dict[str, Any]:
    core = LotofacilScientificCore(contests=contests, db_path=db_path)
    return core.discover_scientific_generation_policy(game_size, candidate_limit=candidate_limit)


def get_scientific_generation_policy(
    game_size: int,
    *,
    contests: Sequence[dict[str, Any]] | None = None,
    db_path: Any = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    core = LotofacilScientificCore(contests=contests, db_path=db_path)
    return core.get_scientific_generation_policy(game_size)
