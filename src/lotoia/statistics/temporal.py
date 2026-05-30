from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from math import log2
from typing import Protocol

from lotoia.statistics.combinations import combo_stats

CENTER_NUMBERS = {7, 8, 9, 12, 13, 14, 17, 18, 19}
MAX_TEMPORAL_INFLUENCE = 0.05


class DrawLike(Protocol):
    contest: int
    numbers: list[int]


@dataclass(frozen=True)
class FeatureContext(Mapping[str, object]):
    cutoff_contest: int
    history: list[DrawLike]
    history_model: dict[str, object]
    delays: dict[str, int]
    hot_cold_numbers: dict[str, object]
    repeated_numbers: dict[str, object]

    @property
    def history_size(self) -> int:
        return len(self.history)

    @property
    def first_contest(self) -> int | None:
        return self.history[0].contest if self.history else None

    @property
    def last_contest(self) -> int | None:
        return self.history[-1].contest if self.history else None

    def to_dict(self) -> dict[str, object]:
        return {
            "cutoff_contest": self.cutoff_contest,
            "history": self.history,
            "history_size": self.history_size,
            "first_contest": self.first_contest,
            "last_contest": self.last_contest,
            "delays": self.delays,
            "hot_cold_numbers": self.hot_cold_numbers,
            "repeated_numbers": self.repeated_numbers,
            "history_model": self.history_model,
        }

    def __getitem__(self, key: str) -> object:
        return self.to_dict()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.to_dict())

    def __len__(self) -> int:
        return len(self.to_dict())


@dataclass(frozen=True)
class TemporalSignal:
    cycle_state: str | None
    pressure_score: float
    migration_signal: float
    decay_factor: float
    temporal_adjustment: float

    def as_dict(self) -> dict[str, object]:
        return {
            "cycle_state": self.cycle_state,
            "pressure_score": round(self.pressure_score, 4),
            "migration_signal": round(self.migration_signal, 4),
            "decay_factor": round(self.decay_factor, 4),
            "temporal_adjustment": round(self.temporal_adjustment, 4),
        }


def calculate_delays(draws: Iterable[DrawLike]) -> dict[str, int]:
    ordered_draws = sorted(draws, key=lambda draw: draw.contest)
    last_contest = ordered_draws[-1].contest if ordered_draws else 0
    last_seen = {number: 0 for number in range(1, 26)}

    for draw in ordered_draws:
        for number in draw.numbers:
            last_seen[number] = draw.contest

    return {str(number): last_contest - last_seen[number] for number in range(1, 26)}


def calculate_repeated_numbers(draws: Iterable[DrawLike]) -> dict[str, object]:
    ordered_draws = sorted(draws, key=lambda draw: draw.contest)
    if len(ordered_draws) < 2:
        return {"count": 0, "numbers": []}

    previous_draw, last_draw = ordered_draws[-2], ordered_draws[-1]
    repeated_numbers = sorted(set(previous_draw.numbers) & set(last_draw.numbers))

    return {"count": len(repeated_numbers), "numbers": repeated_numbers}


def calculate_hot_cold_numbers(draws: Iterable[DrawLike], window: int = 20) -> dict[str, object]:
    ordered_draws = sorted(draws, key=lambda draw: draw.contest)
    recent_draws = ordered_draws[-window:]
    frequencies: Counter[int] = Counter()

    for draw in recent_draws:
        frequencies.update(draw.numbers)

    number_frequencies = [
        {"number": number, "frequency": frequencies.get(number, 0)}
        for number in range(1, 26)
    ]
    hot_numbers = sorted(
        number_frequencies,
        key=lambda item: (-item["frequency"], item["number"]),
    )[:5]
    cold_numbers = sorted(
        number_frequencies,
        key=lambda item: (item["frequency"], item["number"]),
    )[:5]

    return {"window": window, "hot": hot_numbers, "cold": cold_numbers}


def find_sequences(numbers: list[int]) -> list[list[int]]:
    if not numbers:
        return []

    sequences: list[list[int]] = []
    current_sequence = [numbers[0]]

    for number in numbers[1:]:
        if number == current_sequence[-1] + 1:
            current_sequence.append(number)
            continue

        if len(current_sequence) > 1:
            sequences.append(current_sequence)
        current_sequence = [number]

    if len(current_sequence) > 1:
        sequences.append(current_sequence)

    return sequences


def calculate_sequence_stats(numbers: list[int]) -> dict[str, object]:
    sequences = find_sequences(numbers)
    largest_sequence = max((len(sequence) for sequence in sequences), default=0)

    return {
        "sequence_count": len(sequences),
        "largest_sequence": largest_sequence,
        "sequences": sequences,
    }


def build_history_model(history: list[DrawLike]) -> dict[str, object]:
    return {
        "duos": combo_stats(history, 2),
        "ternos": combo_stats(history, 3),
        "quadras": combo_stats(history, 4),
        "quinas": combo_stats(history, 5),
    }


def build_features(history: Iterable[DrawLike], cutoff_contest: int) -> FeatureContext:
    if cutoff_contest < 1:
        raise ValueError("O concurso de corte deve ser maior que zero.")

    previous_history = sorted(
        (draw for draw in history if draw.contest < cutoff_contest),
        key=lambda draw: draw.contest,
    )
    return FeatureContext(
        cutoff_contest=cutoff_contest,
        history=previous_history,
        history_model=build_history_model(previous_history),
        delays=calculate_delays(previous_history),
        hot_cold_numbers=calculate_hot_cold_numbers(previous_history),
        repeated_numbers=calculate_repeated_numbers(previous_history),
    )


def delay_component(numbers: list[int], history: list[DrawLike]) -> float:
    last_seen = {number: 0 for number in range(1, 26)}
    last_contest = history[-1].contest if history else 0
    for draw in history:
        for number in draw.numbers:
            last_seen[number] = draw.contest

    scores = []
    for number in numbers:
        delay = last_contest - last_seen[number]
        distance = abs(delay - 3)
        scores.append(max(0, 1 - (distance / 3)) * 100)
    return sum(scores) / len(scores) if scores else 0


def frequency_component(numbers: list[int], history: list[DrawLike]) -> float:
    counts = {number: 0 for number in range(1, 26)}
    for draw in history:
        for number in draw.numbers:
            counts[number] += 1

    selected = [counts[number] for number in numbers]
    all_counts = list(counts.values())
    min_count = min(all_counts)
    max_count = max(all_counts)
    if max_count == min_count:
        return 100

    average_count = sum(selected) / len(selected)
    return max(0, min(100, ((average_count - min_count) / (max_count - min_count)) * 100))


def sum_component(numbers: list[int]) -> float:
    return max(0, min(100, (1 - (abs(sum(numbers) - 195) / 45)) * 100))


def sequence_component(numbers: list[int]) -> float:
    sequence_stats = calculate_sequence_stats(numbers)
    penalty = (int(sequence_stats["sequence_count"]) * 12) + (
        max(0, int(sequence_stats["largest_sequence"]) - 2) * 16
    )
    return max(0, 100 - penalty)


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def infer_cycle_state(history: Sequence[DrawLike], current_contest: int | None = None) -> str:
    ordered_history = sorted(history, key=lambda draw: draw.contest)
    if not ordered_history:
        return "early_cycle"
    history_size = len(ordered_history)
    if history_size < 50:
        return "early_cycle"
    if history_size < 200:
        return "mid_cycle"
    return "late_cycle"


def calculate_temporal_pressure(numbers: Sequence[int], history: Sequence[DrawLike]) -> float:
    ordered_history = sorted(history, key=lambda draw: draw.contest)
    if not ordered_history:
        return 0.0

    counts = Counter()
    recent_window = ordered_history[-20:]
    prior_window = ordered_history[-40:-20] if len(ordered_history) > 20 else ordered_history[:-20]
    recent_counts = Counter()
    prior_counts = Counter()
    for draw in recent_window:
        recent_counts.update(draw.numbers)
    for draw in prior_window:
        prior_counts.update(draw.numbers)

    average_delay = 0.0
    last_seen = {number: 0 for number in range(1, 26)}
    for draw in ordered_history:
        for number in draw.numbers:
            last_seen[number] = draw.contest
    last_contest = ordered_history[-1].contest
    if numbers:
        average_delay = sum(last_contest - last_seen.get(int(number), last_contest) for number in numbers) / len(numbers)
    delay_pressure = _clamp(average_delay / max(1.0, len(ordered_history) / 2.0))

    recurrence_pressure = 0.0
    if numbers:
        recurrence_pressure = sum(recent_counts.get(int(number), 0) for number in numbers) / max(1.0, len(numbers) * len(recent_window))

    frequency_compression = 0.0
    if recent_counts:
        recent_values = list(recent_counts.values())
        prior_values = list(prior_counts.values()) or [0]
        recent_mean = sum(recent_values) / len(recent_values)
        prior_mean = sum(prior_values) / len(prior_values)
        if prior_mean:
            frequency_compression = _clamp((recent_mean - prior_mean) / max(prior_mean, 1.0), 0.0, 1.0)

    density = _clamp(len(recent_window) / max(1.0, len(ordered_history)))
    pressure = _clamp((delay_pressure * 0.45) + (recurrence_pressure * 0.25) + (frequency_compression * 0.2) + (density * 0.1))
    return round(pressure, 4)


def detect_migration_signal(numbers: Sequence[int], history: Sequence[DrawLike]) -> float:
    ordered_history = sorted(history, key=lambda draw: draw.contest)
    if len(ordered_history) < 10:
        return 0.0

    recent_window = ordered_history[-20:]
    prior_window = ordered_history[-40:-20] if len(ordered_history) > 20 else ordered_history[:-20]
    if not prior_window:
        return 0.0

    def _cluster_distribution(draws: Sequence[DrawLike]) -> dict[int, float]:
        counts = Counter()
        total = 0
        for draw in draws:
            for number in draw.numbers:
                counts[number // 5] += 1
                total += 1
        return {cluster: count / max(1, total) for cluster, count in counts.items()}

    recent_distribution = _cluster_distribution(recent_window)
    prior_distribution = _cluster_distribution(prior_window)
    all_clusters = set(recent_distribution) | set(prior_distribution)
    divergence = 0.0
    for cluster in all_clusters:
        divergence += abs(recent_distribution.get(cluster, 0.0) - prior_distribution.get(cluster, 0.0))

    selected_clusters = {int(number) // 5 for number in numbers}
    cluster_bias = 0.0
    if selected_clusters:
        recent_bias = sum(recent_distribution.get(cluster, 0.0) for cluster in selected_clusters) / len(selected_clusters)
        prior_bias = sum(prior_distribution.get(cluster, 0.0) for cluster in selected_clusters) / len(selected_clusters)
        cluster_bias = abs(recent_bias - prior_bias)

    return round(_clamp((divergence * 0.6) + (cluster_bias * 0.4)), 4)


def calculate_temporal_decay(numbers: Sequence[int], history: Sequence[DrawLike]) -> float:
    ordered_history = sorted(history, key=lambda draw: draw.contest)
    if not ordered_history or not numbers:
        return 0.0
    last_contest = ordered_history[-1].contest
    last_seen = {number: 0 for number in range(1, 26)}
    for draw in ordered_history:
        for number in draw.numbers:
            last_seen[number] = draw.contest
    ages = [last_contest - last_seen.get(int(number), last_contest) for number in numbers]
    average_age = sum(ages) / len(ages) if ages else 0.0
    return round(_clamp(1.0 - (average_age / max(1.0, len(ordered_history)))), 4)


def build_temporal_signal(numbers: Sequence[int], history: Sequence[DrawLike]) -> TemporalSignal:
    cycle_state = infer_cycle_state(history)
    pressure_score = calculate_temporal_pressure(numbers, history)
    migration_signal = detect_migration_signal(numbers, history)
    decay_factor = calculate_temporal_decay(numbers, history)
    temporal_adjustment = _clamp((pressure_score * 0.03) + (migration_signal * 0.02) + (decay_factor * 0.015), 0.0, 0.05)
    return TemporalSignal(
        cycle_state=cycle_state,
        pressure_score=pressure_score,
        migration_signal=migration_signal,
        decay_factor=decay_factor,
        temporal_adjustment=round(temporal_adjustment, 4),
    )


def apply_temporal_adjustment(base_score: float, signal: TemporalSignal, *, cap: float = 0.05) -> float:
    adjustment = min(max(signal.temporal_adjustment, 0.0), cap)
    return round(max(0.0, min(1.0, base_score + adjustment)), 4)


def temporal_rerank(base_score: float, signal: TemporalSignal, *, cap: float = MAX_TEMPORAL_INFLUENCE) -> dict[str, float | str | None]:
    adjustment = min(max(signal.temporal_adjustment, 0.0), cap)
    final_score = max(0.0, min(1.0, base_score + adjustment))
    return {
        "base_score": round(max(0.0, min(1.0, base_score)), 4),
        "temporal_adjustment": round(adjustment, 4),
        "final_score": round(final_score, 4),
        "cycle_state": signal.cycle_state,
        "pressure_score": round(signal.pressure_score, 4),
        "migration_signal": round(signal.migration_signal, 4),
        "temporal_decay": round(signal.decay_factor, 4),
        "rerank_reason": (
            "temporal_adjustment_capped" if adjustment >= cap else "temporal_adjustment_applied"
        ),
    }
