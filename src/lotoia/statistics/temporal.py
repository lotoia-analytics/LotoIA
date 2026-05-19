from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from typing import Protocol

from lotoia.statistics.combinations import combo_stats

CENTER_NUMBERS = {7, 8, 9, 12, 13, 14, 17, 18, 19}


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
