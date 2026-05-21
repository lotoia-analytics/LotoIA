from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import log2

from lotoia.statistics.temporal import CENTER_NUMBERS, calculate_sequence_stats


PROFILE_RECURRENT = "recorrente"
PROFILE_HYBRID = "hibrido"
PROFILE_CHAOTIC = "caotico"
GENERATION_PROFILE_RATIOS = {
    PROFILE_RECURRENT: 0.40,
    PROFILE_HYBRID: 0.40,
    PROFILE_CHAOTIC: 0.20,
}

_BLOCKS = (
    range(1, 6),
    range(6, 11),
    range(11, 16),
    range(16, 21),
    range(21, 26),
)
_PRIMES = {2, 3, 5, 7, 11, 13, 17, 19, 23}
_FIBONACCI = {1, 2, 3, 5, 8, 13, 21}


@dataclass(frozen=True)
class DrawLike:
    contest: int
    numbers: list[int]


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def _triangular_score(value: float, target: float, tolerance: float) -> float:
    if tolerance <= 0:
        return 100.0 if value == target else 0.0
    return _clamp((1 - (abs(value - target) / tolerance)) * 100)


def block_distribution(numbers: list[int]) -> list[int]:
    number_set = set(numbers)
    return [sum(1 for number in block if number in number_set) for block in _BLOCKS]


def max_sequence_length(numbers: list[int]) -> int:
    return int(calculate_sequence_stats(sorted(numbers))["largest_sequence"])


def _partial_matches(numbers: list[int], history: list[DrawLike]) -> list[int]:
    candidate = set(numbers)
    return [len(candidate & set(draw.numbers)) for draw in history]


def partial_recurrence_metrics(numbers: list[int], history: list[DrawLike]) -> dict[str, object]:
    matches = _partial_matches(numbers, history)
    if not matches:
        return {
            "partial_match_max": 0,
            "partial_match_avg": 0.0,
            "partial_match_counts": {"9": 0, "10": 0, "11": 0, "12_plus": 0},
            "jaccard_similarity": 0.0,
            "historical_similarity": 0.0,
        }

    counts = {
        "9": sum(1 for match in matches if match == 9),
        "10": sum(1 for match in matches if match == 10),
        "11": sum(1 for match in matches if match == 11),
        "12_plus": sum(1 for match in matches if match >= 12),
    }
    partial_match_max = max(matches)
    partial_match_avg = sum(matches) / len(matches)
    jaccard = partial_match_max / (30 - partial_match_max) if partial_match_max else 0.0
    historical_similarity = _clamp(
        (counts["9"] * 1.0)
        + (counts["10"] * 2.25)
        + (counts["11"] * 4.0)
        + (counts["12_plus"] * 6.0),
        maximum=100.0,
    )
    return {
        "partial_match_max": partial_match_max,
        "partial_match_avg": round(partial_match_avg, 2),
        "partial_match_counts": counts,
        "jaccard_similarity": round(jaccard, 4),
        "historical_similarity": round(historical_similarity, 2),
    }


def recurrence_score(numbers: list[int], history: list[DrawLike], recent_window: int = 30) -> float:
    if not history:
        return 0.0
    candidate = set(numbers)
    recent_history = history[-recent_window:]
    recent_repetitions = [len(candidate & set(draw.numbers)) for draw in recent_history]
    recent_average = sum(recent_repetitions) / len(recent_repetitions) if recent_repetitions else 0.0
    partial = partial_recurrence_metrics(numbers, history)
    hot_counts = Counter(number for draw in recent_history for number in draw.numbers)
    hot_average = sum(hot_counts[number] for number in candidate) / len(candidate)
    hot_score = _clamp((hot_average / max(1, len(recent_history))) * 160)
    recent_score = _triangular_score(recent_average, target=9.0, tolerance=4.0)
    partial_score = _clamp(float(partial["historical_similarity"]))
    return round((recent_score * 0.45) + (partial_score * 0.35) + (hot_score * 0.20), 2)


def structural_rarity_score(numbers: list[int], history: list[DrawLike]) -> float:
    distribution = block_distribution(numbers)
    odd = sum(1 for number in numbers if number % 2)
    even = len(numbers) - odd
    center = sum(1 for number in numbers if number in CENTER_NUMBERS)
    frame = len(numbers) - center
    sequence_length = max_sequence_length(numbers)
    repeated_last = len(set(numbers) & set(history[-1].numbers)) if history else 0
    prime_count = sum(1 for number in numbers if number in _PRIMES)
    fibonacci_count = sum(1 for number in numbers if number in _FIBONACCI)

    component_scores = [
        _triangular_score(sum(numbers), 195, 70),
        _triangular_score(abs(even - odd), 1, 7),
        _triangular_score(sequence_length, 4, 5),
        _triangular_score(max(distribution) - min(distribution), 2, 5),
        _triangular_score(repeated_last, 8, 6),
        _triangular_score(frame, 10, 5),
        _triangular_score(center, 5, 4),
        _triangular_score(prime_count, 5, 5),
        _triangular_score(fibonacci_count, 4, 4),
    ]
    weights = [0.22, 0.16, 0.14, 0.14, 0.14, 0.08, 0.06, 0.03, 0.03]
    return round(sum(score * weight for score, weight in zip(component_scores, weights, strict=True)), 2)


def entropy_score(numbers: list[int]) -> float:
    distribution = block_distribution(numbers)
    total = sum(distribution)
    if not total:
        return 0.0
    entropy = -sum((count / total) * log2(count / total) for count in distribution if count)
    normalized_entropy = (entropy / log2(len(distribution))) * 100
    sequence = max_sequence_length(numbers)
    sequence_bonus = _clamp((sequence - 2) * 8, maximum=24)
    return round(_clamp((normalized_entropy * 0.82) + sequence_bonus), 2)


def structural_score(numbers: list[int]) -> float:
    odd = sum(1 for number in numbers if number % 2)
    center = sum(1 for number in numbers if number in CENTER_NUMBERS)
    distribution = block_distribution(numbers)
    sequence = max_sequence_length(numbers)
    components = [
        _triangular_score(sum(numbers), 195, 55),
        _triangular_score(odd, 7.5, 3.5),
        _triangular_score(center, 5, 4),
        _triangular_score(max(distribution) - min(distribution), 2, 4),
        _triangular_score(sequence, 3.5, 3.5),
    ]
    return round(sum(components) / len(components), 2)


def cluster_type(numbers: list[int]) -> str:
    distribution = block_distribution(numbers)
    sequence = max_sequence_length(numbers)
    odd = sum(1 for number in numbers if number % 2)
    if sequence >= 6 or max(distribution) >= 6 or odd <= 4 or odd >= 11:
        return "extremo"
    if sequence >= 4 or max(distribution) >= 5:
        return "concentrado"
    return "distribuido"


def classify_profile(numbers: list[int], history: list[DrawLike]) -> str:
    repeated_last = len(set(numbers) & set(history[-1].numbers)) if history else 0
    sequence = max_sequence_length(numbers)
    distribution = block_distribution(numbers)
    odd = sum(1 for number in numbers if number % 2)
    total = sum(numbers)
    if sequence >= 6 or max(distribution) >= 6 or odd <= 4 or odd >= 11 or total < 160 or total > 240:
        return PROFILE_CHAOTIC
    if repeated_last >= 8 or sequence >= 4:
        return PROFILE_RECURRENT
    return PROFILE_HYBRID


def profile_score(numbers: list[int], history: list[DrawLike], profile_type: str) -> dict[str, object]:
    recurrence = recurrence_score(numbers, history)
    partial = partial_recurrence_metrics(numbers, history)
    historical_similarity = float(partial["historical_similarity"])
    structural = structural_score(numbers)
    entropy = entropy_score(numbers)
    rarity = structural_rarity_score(numbers, history)
    weights = {
        PROFILE_RECURRENT: {
            "recurrence_score": 0.40,
            "historical_similarity": 0.25,
            "structural_score": 0.20,
            "entropy_score": 0.10,
            "structural_rarity": 0.05,
        },
        PROFILE_HYBRID: {
            "structural_score": 0.30,
            "recurrence_score": 0.25,
            "historical_similarity": 0.20,
            "entropy_score": 0.15,
            "structural_rarity": 0.10,
        },
        PROFILE_CHAOTIC: {
            "entropy_score": 0.35,
            "structural_rarity": 0.25,
            "structural_score": 0.20,
            "recurrence_score": 0.10,
            "historical_similarity": 0.10,
        },
    }[profile_type]
    components = {
        "recurrence_score": recurrence,
        "historical_similarity": historical_similarity,
        "structural_score": structural,
        "entropy_score": entropy,
        "structural_rarity": rarity,
    }
    final = sum(components[name] * weight for name, weight in weights.items())
    sequence = max_sequence_length(numbers)
    block_density = max(block_distribution(numbers))
    recent_repetition_count = len(set(numbers) & set(history[-1].numbers)) if history else 0
    reason = (
        f"{profile_type}: recorrencia {recurrence:.1f}, "
        f"similaridade parcial {historical_similarity:.1f}, "
        f"estrutura {structural:.1f}, sequencia max {sequence}"
    )
    return {
        "profile_type": profile_type,
        "profile_score": round(final, 2),
        **components,
        **partial,
        "block_density": block_density,
        "max_sequence_length": sequence,
        "recent_repetition_count": recent_repetition_count,
        "cluster_type": cluster_type(numbers),
        "ranking_reason": reason,
        "block_distribution": block_distribution(numbers),
    }


def profile_quota(total: int) -> dict[str, int]:
    recurrent = round(total * GENERATION_PROFILE_RATIOS[PROFILE_RECURRENT])
    hybrid = round(total * GENERATION_PROFILE_RATIOS[PROFILE_HYBRID])
    chaotic = total - recurrent - hybrid
    return {
        PROFILE_RECURRENT: recurrent,
        PROFILE_HYBRID: hybrid,
        PROFILE_CHAOTIC: chaotic,
    }
