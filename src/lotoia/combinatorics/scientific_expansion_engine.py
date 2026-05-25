from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import combinations
from math import comb, log2
from time import perf_counter
from typing import Any

from lotoia.statistics.historical_intelligence import (
    DrawLike,
    classify_profile,
    entropy_score,
    partial_recurrence_metrics,
    profile_score,
    recurrence_score,
    structural_rarity_score,
    structural_score,
)

SUPPORTED_SCIENTIFIC_SIZES = (16, 17, 18, 19, 20)
SIMPLE_GAME_SIZE = 15
DEFAULT_MAX_RUNTIME_SECONDS = 2.5
DEFAULT_MAX_CANDIDATES = 250
DEFAULT_MAX_OVERLAP = 11
DEFAULT_MINIMUM_HAMMING_DISTANCE = 4
DEFAULT_PREFERRED_PREMIUM_LIMITS = {
    16: (40, 80),
    17: (80, 150),
    18: (120, 250),
}


@dataclass(frozen=True)
class ScientificExpansionConfig:
    max_runtime_seconds: float = DEFAULT_MAX_RUNTIME_SECONDS
    max_candidates: int = DEFAULT_MAX_CANDIDATES
    premium_limit: int = DEFAULT_MAX_CANDIDATES
    max_overlap_between_games: int = DEFAULT_MAX_OVERLAP
    minimum_hamming_distance: int = DEFAULT_MINIMUM_HAMMING_DISTANCE
    sample_cap: int = 4000


@dataclass(frozen=True)
class ScientificExpansionResult:
    selected_numbers: tuple[int, ...]
    total_combinations: int
    candidate_count: int
    filtered_count: int
    generated_count: int
    ranked_candidates: tuple[dict[str, Any], ...]
    premium_games: tuple[dict[str, Any], ...]
    metrics: dict[str, Any]
    estimated_cost: float
    runtime_ms: float
    complete: bool
    stopped_reason: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "selected_numbers": list(self.selected_numbers),
            "total_combinations": self.total_combinations,
            "candidate_count": self.candidate_count,
            "filtered_count": self.filtered_count,
            "generated_count": self.generated_count,
            "ranked_candidates": [dict(row) for row in self.ranked_candidates],
            "premium_games": [dict(row) for row in self.premium_games],
            "metrics": dict(self.metrics),
            "estimated_cost": self.estimated_cost,
            "runtime_ms": self.runtime_ms,
            "complete": self.complete,
            "stopped_reason": self.stopped_reason,
        }


def validate_scientific_expanded_numbers(numbers: Sequence[int]) -> tuple[int, ...]:
    normalized = tuple(sorted(int(number) for number in numbers))
    if len(normalized) not in SUPPORTED_SCIENTIFIC_SIZES:
        raise ValueError("Jogo expandido científico deve conter entre 16 e 20 dezenas.")
    if len(set(normalized)) != len(normalized):
        raise ValueError("As dezenas expandidas nao podem se repetir.")
    if any(number < 1 or number > 25 for number in normalized):
        raise ValueError("As dezenas devem estar entre 1 e 25.")
    return normalized


def _normalize_history(history: Sequence[Any] | None) -> list[DrawLike]:
    normalized_history: list[DrawLike] = []
    for index, item in enumerate(history or [], start=1):
        if isinstance(item, DrawLike):
            normalized_history.append(item)
            continue
        if isinstance(item, dict):
            contest = int(item.get("contest", item.get("concurso", index)) or index)
            numbers = item.get("numbers") or item.get("dezenas") or []
            normalized_history.append(
                DrawLike(contest=contest, numbers=[int(number) for number in numbers])
            )
    return normalized_history


def _hamming_distance(first: Sequence[int], second: Sequence[int]) -> int:
    return len(set(first) ^ set(second))


def _overlap_count(first: Sequence[int], second: Sequence[int]) -> int:
    return len(set(first).intersection(second))


def _spread_score(numbers: Sequence[int]) -> dict[str, float]:
    normalized = tuple(sorted(int(number) for number in numbers))
    if not normalized:
        return {
            "spread": 0.0,
            "low_high_balance": 0.0,
            "frame_balance": 0.0,
            "gap_balance": 0.0,
            "center_balance": 0.0,
            "cluster_dispersion": 0.0,
            "coverage_score": 0.0,
            "structural_distance": 0.0,
        }
    gaps = [b - a for a, b in zip(normalized, normalized[1:], strict=False)]
    spread = (normalized[-1] - normalized[0]) / 24.0 if len(normalized) > 1 else 0.0
    low = sum(1 for number in normalized if number <= 12)
    high = len(normalized) - low
    low_high_balance = 1.0 - abs((low / len(normalized)) - 0.5) * 2.0
    frame = len(normalized) - sum(1 for number in normalized if 9 <= number <= 17)
    frame_balance = 1.0 - abs((frame / len(normalized)) - 0.5) * 2.0
    center_balance = 1.0 - abs((sum(1 for number in normalized if 9 <= number <= 17) / len(normalized)) - 0.5) * 2.0
    gap_balance = 1.0
    if gaps:
        gap_avg = sum(gaps) / len(gaps)
        gap_balance = max(0.0, 1.0 - abs(gap_avg - 1.0) / max(1.0, len(normalized) / 3.0))
    cluster_dispersion = max(0.0, min(1.0, len({number // 5 for number in normalized}) / 5.0))
    coverage_score = max(
        0.0,
        min(
            1.0,
            (spread * 0.3)
            + (low_high_balance * 0.2)
            + (frame_balance * 0.15)
            + (center_balance * 0.15)
            + (gap_balance * 0.1)
            + (cluster_dispersion * 0.1),
        ),
    )
    structural_distance = max(0.0, min(1.0, spread * 0.5 + cluster_dispersion * 0.5))
    return {
        "spread": round(spread, 4),
        "low_high_balance": round(low_high_balance, 4),
        "frame_balance": round(frame_balance, 4),
        "gap_balance": round(gap_balance, 4),
        "center_balance": round(center_balance, 4),
        "cluster_dispersion": round(cluster_dispersion, 4),
        "coverage_score": round(coverage_score, 4),
        "structural_distance": round(structural_distance, 4),
    }


def _candidate_metrics(numbers: Sequence[int], history: Sequence[DrawLike]) -> dict[str, Any]:
    normalized = tuple(sorted(int(number) for number in numbers))
    profile_type = classify_profile(list(normalized), list(history))
    intelligence = profile_score(list(normalized), list(history), profile_type)
    spread = _spread_score(normalized)
    return {
        "numbers": normalized,
        "dezenas": " ".join(f"{number:02d}" for number in normalized),
        "profile_type": profile_type,
        "profile_score": float(intelligence["profile_score"]),
        "recurrence_score": float(intelligence["recurrence_score"]),
        "historical_similarity": float(intelligence["historical_similarity"]),
        "structural_score": float(intelligence["structural_score"]),
        "entropy_score": float(intelligence["entropy_score"]),
        "structural_rarity": float(intelligence["structural_rarity"]),
        "partial_match_max": int(intelligence["partial_match_max"]),
        "partial_match_avg": float(intelligence["partial_match_avg"]),
        "block_density": int(intelligence["block_density"]),
        "max_sequence_length": int(intelligence["max_sequence_length"]),
        "recent_repetition_count": int(intelligence["recent_repetition_count"]),
        "cluster_type": str(intelligence["cluster_type"]),
        "ranking_reason": str(intelligence["ranking_reason"]),
        "spread": spread,
    }


def _scientific_score(candidate: dict[str, Any]) -> float:
    spread = candidate["spread"]
    recurrence = candidate["recurrence_score"]
    historical_similarity = candidate["historical_similarity"]
    structural_score_value = candidate["structural_score"]
    entropy_value = candidate["entropy_score"]
    rarity = candidate["structural_rarity"]
    coverage = spread["coverage_score"]
    distance = spread["structural_distance"]
    penalty = 0.0
    if candidate["max_sequence_length"] >= 6:
        penalty += 12.0
    if candidate["block_density"] >= 6:
        penalty += 10.0
    if candidate["partial_match_max"] >= 12:
        penalty += 12.0
    if candidate["recent_repetition_count"] >= 10:
        penalty += 8.0
    score = (
        structural_score_value * 0.22
        + entropy_value * 0.18
        + rarity * 0.12
        + coverage * 22.0
        + distance * 16.0
        + (100.0 - recurrence) * 0.12
        + (100.0 - historical_similarity) * 0.14
    ) - penalty
    return round(max(0.0, min(100.0, score)), 2)


def _sample_combinations(selected: tuple[int, ...], total: int, *, limit: int, max_runtime_seconds: float) -> list[tuple[int, ...]]:
    started = perf_counter()
    sampled: list[tuple[int, ...]] = []
    if total <= limit * 4:
        for combo in combinations(selected, SIMPLE_GAME_SIZE):
            if (perf_counter() - started) > max_runtime_seconds:
                break
            sampled.append(tuple(combo))
        return sampled

    stride = max(2, total // max(1, limit * 2))
    offset = sum(selected) % stride
    for index, combo in enumerate(combinations(selected, SIMPLE_GAME_SIZE)):
        if (perf_counter() - started) > max_runtime_seconds:
            break
        if index % stride != offset:
            continue
        sampled.append(tuple(combo))
        if len(sampled) >= limit * 4:
            break
    return sampled


def _scientific_sequence_limit(expansion_size: int) -> int:
    return max(8, min(12, expansion_size - 6))


def select_premium_expansive_games(
    numbers: Sequence[int],
    *,
    history: Sequence[Any] | None = None,
    config: ScientificExpansionConfig | None = None,
) -> ScientificExpansionResult:
    active_config = config or ScientificExpansionConfig()
    selected = validate_scientific_expanded_numbers(numbers)
    normalized_history = _normalize_history(history)
    total = comb(len(selected), SIMPLE_GAME_SIZE)
    premium_floor, premium_ceiling = DEFAULT_PREFERRED_PREMIUM_LIMITS.get(
        len(selected),
        (max(40, len(selected) * 5), min(active_config.max_candidates, total)),
    )
    premium_limit = min(active_config.premium_limit, premium_ceiling)
    if premium_limit <= 0:
        premium_limit = min(active_config.max_candidates, total)

    started = perf_counter()
    candidate_pool = _sample_combinations(
        selected,
        total,
        limit=min(active_config.max_candidates, premium_limit),
        max_runtime_seconds=active_config.max_runtime_seconds,
    )
    candidate_pool_count = len(candidate_pool)

    ranked_candidates: list[dict[str, Any]] = []
    filtered_count = 0
    for combo in candidate_pool:
        if (perf_counter() - started) > active_config.max_runtime_seconds:
            break
        candidate = _candidate_metrics(combo, normalized_history)
        sequence_limit = _scientific_sequence_limit(len(selected))
        if candidate["max_sequence_length"] >= sequence_limit:
            filtered_count += 1
            continue
        if candidate["block_density"] >= 6:
            filtered_count += 1
            continue
        if candidate["partial_match_max"] >= 13:
            filtered_count += 1
            continue
        if candidate["spread"]["coverage_score"] < 0.35:
            filtered_count += 1
            continue

        candidate["scientific_score"] = _scientific_score(candidate)
        candidate["diversity_index"] = round(
            max(
                0.0,
                min(
                    1.0,
                    candidate["spread"]["coverage_score"] * 0.4
                    + candidate["spread"]["cluster_dispersion"] * 0.2
                    + (1.0 - min(1.0, candidate["partial_match_max"] / 15.0)) * 0.2
                    + (1.0 - candidate["recurrence_score"] / 100.0) * 0.2,
                ),
            ),
            4,
        )
        candidate["diversity_score"] = candidate["diversity_index"]
        candidate["overlap_score"] = round(candidate["partial_match_max"] / 15.0, 4)
        candidate["coverage_score"] = candidate["spread"]["coverage_score"]
        candidate["cluster_dispersion"] = candidate["spread"]["cluster_dispersion"]
        ranked_candidates.append(candidate)

    ranked_candidates.sort(
        key=lambda row: (
            -float(row["scientific_score"]),
            -float(row["diversity_index"]),
            -float(row["coverage_score"]),
            float(row["overlap_score"]),
            float(row["partial_match_max"]),
            row["numbers"],
        )
    )

    premium_games: list[dict[str, Any]] = []
    for candidate in ranked_candidates:
        if len(premium_games) >= premium_limit:
            break
        overlaps = [len(set(candidate["numbers"]).intersection(previous["numbers"])) for previous in premium_games]
        hamming_distances = [_hamming_distance(candidate["numbers"], previous["numbers"]) for previous in premium_games]
        if overlaps and max(overlaps) > active_config.max_overlap_between_games:
            continue
        if hamming_distances and min(hamming_distances) < active_config.minimum_hamming_distance:
            continue
        premium_games.append(candidate)

    if len(premium_games) < premium_limit:
        for candidate in ranked_candidates:
            if candidate in premium_games:
                continue
            premium_games.append(candidate)
            if len(premium_games) >= premium_limit:
                break

    if not premium_games and ranked_candidates:
        premium_games = ranked_candidates[: min(premium_limit, len(ranked_candidates))]

    if premium_games:
        premium_overlaps: list[float] = []
        premium_distances: list[float] = []
        for index, first in enumerate(premium_games):
            for second in premium_games[index + 1 :]:
                premium_overlaps.append(len(set(first["numbers"]).intersection(second["numbers"])) / SIMPLE_GAME_SIZE)
                premium_distances.append(_hamming_distance(first["numbers"], second["numbers"]) / (SIMPLE_GAME_SIZE * 2))
        overlap_mean = round(sum(premium_overlaps) / len(premium_overlaps), 4) if premium_overlaps else 0.0
        unique_ratio = round(len({tuple(row["numbers"]) for row in premium_games}) / len(premium_games), 4)
        rerank_entropy = 0.0
        distribution: dict[str, int] = {}
        for row in premium_games:
            distribution[row["profile_type"]] = distribution.get(row["profile_type"], 0) + 1
        for count in distribution.values():
            share = count / len(premium_games)
            if share:
                rerank_entropy -= share * log2(share)
        max_entropy = log2(len(distribution)) if len(distribution) > 1 else 1.0
        rerank_entropy = round((rerank_entropy / max_entropy) if max_entropy else 0.0, 4)
        structural_diversity_score = round(
            max(
                0.0,
                min(
                    1.0,
                    (1.0 - overlap_mean) * 0.4
                    + unique_ratio * 0.2
                    + rerank_entropy * 0.2
                    + (sum(row["diversity_index"] for row in premium_games) / len(premium_games)) * 0.2,
                ),
            ),
            4,
        )
        premium_concentration_index = round(
            sum(float(row["scientific_score"]) for row in premium_games[: min(5, len(premium_games))])
            / max(1.0, sum(float(row["scientific_score"]) for row in premium_games)),
            4,
        )
        avg_distance = round(sum(premium_distances) / len(premium_distances), 4) if premium_distances else 0.0
        avg_score = round(sum(float(row["scientific_score"]) for row in premium_games) / len(premium_games), 4)
    else:
        overlap_mean = 0.0
        unique_ratio = 0.0
        rerank_entropy = 0.0
        structural_diversity_score = 0.0
        premium_concentration_index = 0.0
        avg_distance = 0.0
        avg_score = 0.0
        distribution = {}

    runtime_ms = round((perf_counter() - started) * 1000, 3)
    stopped_reason = None
    if len(ranked_candidates) < candidate_pool_count:
        stopped_reason = "runtime_limit"
    elif candidate_pool_count < total:
        stopped_reason = "sampled_pool"

    metrics = {
        "diversity_index": round(sum(row["diversity_index"] for row in premium_games) / len(premium_games), 4) if premium_games else 0.0,
        "overlap_score": round(sum(row["overlap_score"] for row in premium_games) / len(premium_games), 4) if premium_games else 0.0,
        "coverage_score": round(sum(row["coverage_score"] for row in premium_games) / len(premium_games), 4) if premium_games else 0.0,
        "structural_distance": avg_distance,
        "entropy_score": round(sum(float(row["entropy_score"]) for row in premium_games) / len(premium_games), 4) if premium_games else 0.0,
        "cluster_dispersion": round(sum(float(row["cluster_dispersion"]) for row in premium_games) / len(premium_games), 4) if premium_games else 0.0,
        "overlap_mean": overlap_mean,
        "unique_ratio": unique_ratio,
        "rerank_entropy": rerank_entropy,
        "structural_diversity_score": structural_diversity_score,
        "premium_concentration_index": premium_concentration_index,
        "profile_distribution": distribution,
        "average_scientific_score": avg_score,
        "premium_limit": premium_limit,
        "sequence_limit": _scientific_sequence_limit(len(selected)),
        "candidate_pool_count": candidate_pool_count,
        "filtered_count": filtered_count,
    }

    estimated_cost = round(total * 3.5, 2)
    complete = len(premium_games) >= premium_limit and candidate_pool_count >= total
    return ScientificExpansionResult(
        selected_numbers=selected,
        total_combinations=total,
        candidate_count=candidate_pool_count,
        filtered_count=filtered_count,
        generated_count=len(ranked_candidates),
        ranked_candidates=tuple(ranked_candidates),
        premium_games=tuple(premium_games),
        metrics=metrics,
        estimated_cost=estimated_cost,
        runtime_ms=runtime_ms,
        complete=complete,
        stopped_reason=stopped_reason,
    )
