from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import log2, sqrt
from statistics import mean, median
from typing import Any, Iterable, Sequence

from sqlalchemy import select

from lotoia.data.loader import load_draws_csv
from lotoia.database.database import DEFAULT_DATABASE_PATH, ImportedContest, get_session
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

    def get_scientific_generation_policy(self, game_size: int) -> dict[str, Any]:
        profile = self.build_scientific_profile(window_size=max(20, min(len(self.contests), max(60, game_size * 4)))) if self.contests else {}
        game_size = max(2, min(int(game_size or 15), 25))
        repeat_mean = float(profile.get("average_repetition", 8.0) or 8.0)
        sequence_mean = float(profile.get("average_sequence_max", 5.0) or 5.0)
        coverage_mean = float(profile.get("average_coverage", 0.4) or 0.4)
        entropy_mean = float(profile.get("average_entropy", 0.45) or 0.45)
        dominant_numbers = [int(item.get("number", 0) or 0) for item in profile.get("dominant_numbers", []) if int(item.get("number", 0) or 0) > 0]
        core_numbers = tuple(dominant_numbers[:4]) if dominant_numbers else (7, 12, 16, 23)
        discouraged_numbers = tuple(sorted({number for number in range(1, 26)} - set(core_numbers), key=lambda number: (int(profile.get("number_frequency", {}).get(str(number), 0) or 0), number))[:6])

        if game_size == 15:
            repeat_min = 7
            repeat_max = 10
            preferred_parity_pairs = ((7, 8), (8, 7))
            allowed_parity_pairs = ((7, 8), (8, 7), (6, 9), (9, 6))
            sequence_max = 6
            coverage_min = 0.40
            entropy_min = 0.45
            max_frequency_ratio = 0.70
            min_frequency_ratio = 0.20
            preferred_profile_ratios = {(7, 8): 0.52, (8, 7): 0.48}
            notes = (
                "faixa_15_calibrada_com_repeticao_7_a_10",
                "paridade_favorita_7_8_e_8_7",
                "bloqueio_de_concentracao_absoluta",
            )
        elif game_size == 17:
            repeat_min = max(7, int(round(repeat_mean - 1.0)))
            repeat_max = min(11, max(repeat_min, int(round(repeat_mean + 2.0))))
            preferred_parity_pairs = ((8, 9), (9, 8))
            allowed_parity_pairs = ((8, 9), (9, 8), (7, 10), (10, 7))
            sequence_max = min(game_size, max(6, int(round(sequence_mean + 1.0))))
            coverage_min = min(0.50, max(0.40, round(coverage_mean, 2)))
            entropy_min = min(0.55, max(0.45, round(entropy_mean, 2)))
            max_frequency_ratio = 0.65
            min_frequency_ratio = 0.15
            preferred_profile_ratios = {(8, 9): 0.55, (9, 8): 0.45}
            notes = ("faixa_17_balanceada", "repeticao_temporal_controlada")
        elif game_size == 18:
            repeat_min = max(8, int(round(repeat_mean - 1.0)))
            repeat_max = min(12, max(repeat_min, int(round(repeat_mean + 2.0))))
            preferred_parity_pairs = ((9, 9), (8, 10), (10, 8))
            allowed_parity_pairs = ((9, 9), (8, 10), (10, 8), (7, 11), (11, 7))
            sequence_max = min(game_size, max(6, int(round(sequence_mean + 1.0))))
            coverage_min = min(0.55, max(0.45, round(coverage_mean, 2)))
            entropy_min = min(0.60, max(0.48, round(entropy_mean, 2)))
            max_frequency_ratio = 0.65
            min_frequency_ratio = 0.15
            preferred_profile_ratios = {(9, 9): 0.45, (8, 10): 0.30, (10, 8): 0.25}
            notes = ("faixa_18_balanceada", "mais_espaco_para_diversidade")
        else:
            ideal_odd = min(max((game_size + 1) // 2, 0), game_size)
            ideal_even = game_size - ideal_odd
            repeat_base = max(0, min(game_size, int(round(repeat_mean))))
            repeat_min = max(0, min(game_size, max(0, repeat_base - 2)))
            repeat_max = max(repeat_min, min(game_size, repeat_base + 2))
            preferred_parity_pairs = ((ideal_odd, ideal_even),)
            allowed_parity_pairs = (
                (ideal_odd, ideal_even),
                (max(0, ideal_odd - 1), min(game_size, ideal_even + 1)),
                (min(game_size, ideal_odd + 1), max(0, ideal_even - 1)),
            )
            sequence_max = min(game_size, max(4, int(round(sequence_mean + 1.0))))
            coverage_min = min(0.65, max(0.35, round(coverage_mean, 2)))
            entropy_min = min(0.70, max(0.30, round(entropy_mean, 2)))
            max_frequency_ratio = 0.75
            min_frequency_ratio = 0.10
            preferred_profile_ratios = {preferred_parity_pairs[0]: 1.0}
            notes = ("policy_derived_from_history",)

        return ScientificGenerationPolicy(
            game_size=game_size,
            window_size=int(profile.get("window_size", 0) or len(self.contests)),
            source=str(profile.get("source", "imported_contests") or "imported_contests"),
            contest_count=int(profile.get("contest_count", len(self.contests)) or len(self.contests)),
            repeat_min=int(repeat_min),
            repeat_max=int(repeat_max),
            preferred_parity_pairs=tuple(tuple(pair) for pair in preferred_parity_pairs),
            allowed_parity_pairs=tuple(tuple(pair) for pair in allowed_parity_pairs),
            sequence_max=int(sequence_max),
            coverage_min=float(coverage_min),
            entropy_min=float(entropy_min),
            core_numbers=tuple(int(number) for number in core_numbers),
            discouraged_numbers=tuple(int(number) for number in discouraged_numbers),
            max_frequency_ratio=float(max_frequency_ratio),
            min_frequency_ratio=float(min_frequency_ratio),
            preferred_profile_ratios={tuple(pair): float(ratio) for pair, ratio in preferred_profile_ratios.items()},
            notes=notes,
        ).as_dict()

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


def get_scientific_generation_policy(
    game_size: int,
    *,
    contests: Sequence[dict[str, Any]] | None = None,
    db_path: Any = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    core = LotofacilScientificCore(contests=contests, db_path=db_path)
    return core.get_scientific_generation_policy(game_size)
