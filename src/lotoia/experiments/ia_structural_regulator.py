from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from math import comb, log2
from pathlib import Path
from statistics import pstdev
from typing import Any, Sequence

from lotoia.backtesting.backtester import _select_targets
from lotoia.combinatorics.scientific_expansion_engine import (
    DEFAULT_PREFERRED_PREMIUM_LIMITS,
    SIMPLE_GAME_SIZE,
    ScientificExpansionConfig,
    _candidate_metrics,
    _hamming_distance,
    _normalize_history,
    _sample_combinations,
    _scientific_score,
    _scientific_sequence_limit,
    select_premium_expansive_games,
    validate_scientific_expanded_numbers,
)
from lotoia.benchmark.benchmark_engine import _history_for_target
from lotoia.data.loader import load_draws_csv
from lotoia.models.draw import Draw

IA_STRUCTURAL_EXPERIMENT_VERSION = "0.1.0"
IA_STRUCTURAL_ENGINE_VERSION = "ia_structural_v1"
DEFAULT_IA_STRUCTURAL_DIR = Path("reports/ia_structural")


@dataclass(frozen=True)
class StructuralPoolObservation:
    candidate_count: int
    filtered_count: int
    ranked_count: int
    premium_count: int
    overlap_mean: float
    entropy: float
    unique_ratio_real: float
    cluster_dispersion: float
    dominant_numbers: list[dict[str, Any]]
    overexplored_regions: list[dict[str, Any]]
    concentration_index: float
    average_distance: float
    structural_collision_rate: float
    pool_entropy_score: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_count": self.candidate_count,
            "filtered_count": self.filtered_count,
            "ranked_count": self.ranked_count,
            "premium_count": self.premium_count,
            "overlap_mean": self.overlap_mean,
            "entropy": self.entropy,
            "unique_ratio_real": self.unique_ratio_real,
            "cluster_dispersion": self.cluster_dispersion,
            "dominant_numbers": self.dominant_numbers,
            "overexplored_regions": self.overexplored_regions,
            "concentration_index": self.concentration_index,
            "average_distance": self.average_distance,
            "structural_collision_rate": self.structural_collision_rate,
            "pool_entropy_score": self.pool_entropy_score,
        }


@dataclass(frozen=True)
class StructuralContestReplay:
    contest: int
    baseline: dict[str, Any]
    ia_structural: dict[str, Any]
    delta_average_hits: float
    delta_11_plus: int
    delta_12_plus: int
    observational_signature: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "contest": self.contest,
            "baseline": self.baseline,
            "ia_structural": self.ia_structural,
            "delta_average_hits": self.delta_average_hits,
            "delta_11_plus": self.delta_11_plus,
            "delta_12_plus": self.delta_12_plus,
            "observational_signature": self.observational_signature,
        }


@dataclass(frozen=True)
class IAStructuralExperimentResult:
    benchmark_version: str
    structural_version: str
    created_at: str
    seed: int
    contests_analyzed: int
    games_count: int
    pool_size: int
    history_window: int | None
    replay: list[dict[str, Any]]
    summary: dict[str, Any]
    report_paths: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_version": self.benchmark_version,
            "structural_version": self.structural_version,
            "created_at": self.created_at,
            "seed": self.seed,
            "contests_analyzed": self.contests_analyzed,
            "games_count": self.games_count,
            "pool_size": self.pool_size,
            "history_window": self.history_window,
            "replay": self.replay,
            "summary": self.summary,
            "report_paths": self.report_paths,
        }


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _mean(values: Sequence[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _safe_pstdev(values: Sequence[float]) -> float:
    values = list(values)
    return pstdev(values) if len(values) > 1 else 0.0


def _default_experiment_numbers(selected_count: int) -> str:
    if selected_count <= 1:
        return "01"
    spread: list[int] = []
    for index in range(selected_count):
        raw_value = round(1 + (24 * index / max(1, selected_count - 1)))
        value = max(1, min(25, raw_value))
        while value in spread and value < 25:
            value += 1
        while value in spread and value > 1:
            value -= 1
        if value not in spread:
            spread.append(value)
    if len(spread) < selected_count:
        for value in range(1, 26):
            if value not in spread:
                spread.append(value)
            if len(spread) >= selected_count:
                break
    return " ".join(f"{number:02d}" for number in sorted(spread[:selected_count]))


def _numbers_signature(numbers: Sequence[int]) -> tuple[int, ...]:
    return tuple(sorted(int(number) for number in numbers))


def _pairwise_overlap_mean(games: Sequence[Sequence[int]]) -> float:
    normalized = [tuple(sorted(int(number) for number in game)) for game in games]
    overlaps: list[float] = []
    for index, first in enumerate(normalized):
        for second in normalized[index + 1 :]:
            overlaps.append(len(set(first).intersection(second)) / SIMPLE_GAME_SIZE)
    return round(sum(overlaps) / len(overlaps), 4) if overlaps else 0.0


def _pairwise_distance_mean(games: Sequence[Sequence[int]]) -> float:
    normalized = [tuple(sorted(int(number) for number in game)) for game in games]
    distances: list[float] = []
    for index, first in enumerate(normalized):
        for second in normalized[index + 1 :]:
            distances.append(_hamming_distance(first, second) / (SIMPLE_GAME_SIZE * 2))
    return round(sum(distances) / len(distances), 4) if distances else 0.0


def _cluster_bucket(number: int) -> int:
    return (int(number) - 1) // 5


def _structural_observation(
    ranked_candidates: Sequence[dict[str, Any]],
    premium_games: Sequence[dict[str, Any]],
) -> StructuralPoolObservation:
    candidate_count = len(ranked_candidates)
    filtered_count = len(ranked_candidates)
    ranked_count = len(ranked_candidates)
    premium_count = len(premium_games)
    numbers = [int(number) for row in ranked_candidates for number in row.get("numbers", [])]
    numbers_counter = Counter(numbers)
    dominant_numbers = [
        {"number": number, "frequency": count}
        for number, count in numbers_counter.most_common(10)
    ]
    cluster_counter = Counter(_cluster_bucket(number) for number in numbers)
    total_clusters = max(1, len(cluster_counter))
    cluster_dispersion = round(len(cluster_counter) / 5.0, 4) if numbers else 0.0
    overexplored_regions = [
        {"cluster": int(cluster), "frequency": round(count / max(1, len(numbers)), 4)}
        for cluster, count in cluster_counter.items()
        if count / max(1, len(numbers)) >= 0.18
    ]

    distribution: dict[tuple[int, ...], int] = {}
    for row in ranked_candidates:
        signature = _numbers_signature(row.get("numbers", []))
        distribution[signature] = distribution.get(signature, 0) + 1
    entropy = 0.0
    for count in distribution.values():
        share = count / max(1, len(ranked_candidates))
        if share:
            entropy -= share * log2(share)
    max_entropy = log2(len(distribution)) if len(distribution) > 1 else 1.0
    pool_entropy_score = round((entropy / max_entropy) if max_entropy else 0.0, 4)
    unique_ratio_real = round(len(distribution) / max(1, len(ranked_candidates)), 4)
    overlap_mean = _pairwise_overlap_mean([row.get("numbers", []) for row in ranked_candidates])
    average_distance = _pairwise_distance_mean([row.get("numbers", []) for row in ranked_candidates])
    structural_collision_rate = round(1.0 - unique_ratio_real, 4)
    concentration_index = round(
        max((count / max(1, len(numbers))) for count in numbers_counter.values()) if numbers_counter else 0.0,
        4,
    )
    return StructuralPoolObservation(
        candidate_count=candidate_count,
        filtered_count=filtered_count,
        ranked_count=ranked_count,
        premium_count=premium_count,
        overlap_mean=overlap_mean,
        entropy=round(pool_entropy_score, 4),
        unique_ratio_real=unique_ratio_real,
        cluster_dispersion=cluster_dispersion,
        dominant_numbers=dominant_numbers,
        overexplored_regions=overexplored_regions,
        concentration_index=concentration_index,
        average_distance=average_distance,
        structural_collision_rate=structural_collision_rate,
        pool_entropy_score=pool_entropy_score,
    )


def _structural_adjusted_score(candidate: dict[str, Any], observation: StructuralPoolObservation) -> float:
    scientific = float(candidate.get("scientific_score", 0.0) or 0.0)
    diversity = float(candidate.get("diversity_index", candidate.get("diversity_score", 0.0)) or 0.0)
    coverage = float(candidate.get("coverage_score", 0.0) or 0.0)
    recurrence = float(candidate.get("recurrence_score", 0.0) or 0.0)
    entropy = float(candidate.get("entropy_score", 0.0) or 0.0)
    cluster_dispersion = float(candidate.get("cluster_dispersion", 0.0) or 0.0)
    structural_distance = float(candidate.get("spread", {}).get("structural_distance", 0.0) or 0.0)
    dominant_penalty = observation.concentration_index * 8.0 + observation.structural_collision_rate * 12.0
    exploration_boost = (1.0 - observation.entropy) * 10.0 + (1.0 - observation.cluster_dispersion) * 6.0
    return round(
        max(
            0.0,
            min(
                100.0,
                scientific * 0.60
                + diversity * 12.0
                + coverage * 12.0
                + structural_distance * 8.0
                + cluster_dispersion * 4.0
                + entropy * 2.0
                + (100.0 - recurrence) * 0.05
                - dominant_penalty
                + exploration_boost,
            ),
        ),
        2,
    )


def _structural_adjusted_score_moderate(candidate: dict[str, Any], observation: StructuralPoolObservation) -> float:
    base = _structural_adjusted_score(candidate, observation)
    compression_signal = observation.concentration_index * 0.25 + observation.structural_collision_rate * 0.35
    exploration_signal = (1.0 - observation.entropy) * 0.25 + (1.0 - observation.cluster_dispersion) * 0.15
    return round(max(0.0, min(100.0, base + (compression_signal + exploration_signal) * 10.0)), 2)


def _build_structural_candidate_pool(
    numbers: Sequence[int],
    history: Sequence[Any],
    *,
    max_runtime_seconds: float = 1.5,
    max_candidates: int = 250,
    premium_limit: int = 250,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    selected = validate_scientific_expanded_numbers(numbers)
    normalized_history = _normalize_history(history)
    total = comb(len(selected), SIMPLE_GAME_SIZE)
    premium_limit = min(premium_limit, DEFAULT_PREFERRED_PREMIUM_LIMITS.get(len(selected), (premium_limit, premium_limit))[1])
    config = ScientificExpansionConfig(
        max_runtime_seconds=max_runtime_seconds,
        max_candidates=max_candidates,
        premium_limit=premium_limit,
    )
    candidate_pool = _sample_combinations(
        selected,
        total,
        limit=min(config.max_candidates, premium_limit),
        max_runtime_seconds=config.max_runtime_seconds,
    )
    ranked_candidates: list[dict[str, Any]] = []
    filtered_count = 0
    for combo in candidate_pool:
        candidate = _candidate_metrics(combo, normalized_history)
        if candidate["max_sequence_length"] >= _scientific_sequence_limit(len(selected)):
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
        if overlaps and max(overlaps) > config.max_overlap_between_games:
            continue
        if hamming_distances and min(hamming_distances) < config.minimum_hamming_distance:
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

    compression_metrics = {
        "candidate_space_size": len(candidate_pool),
        "initial_candidate_count": len(candidate_pool),
        "post_filter_count": len(ranked_candidates),
        "post_rerank_count": len(ranked_candidates),
        "final_gate_count": len(premium_games),
        "unique_hash_count_before_gate": len({tuple(row["numbers"]) for row in ranked_candidates}),
        "unique_hash_count_after_gate": len({tuple(row["numbers"]) for row in premium_games}),
        "unique_ratio_before_gate": round(len({tuple(row["numbers"]) for row in ranked_candidates}) / max(1, len(ranked_candidates)), 4),
        "unique_ratio_after_gate": round(len({tuple(row["numbers"]) for row in premium_games}) / max(1, len(premium_games)), 4),
        "structural_collision_rate": round(1.0 - (len({tuple(row["numbers"]) for row in ranked_candidates}) / max(1, len(ranked_candidates))), 4),
        "rerank_compression_ratio": round(len(premium_games) / max(1, len(ranked_candidates)), 4),
        "dominant_hash_frequency": max(
            (count for count in Counter(tuple(row["numbers"]) for row in ranked_candidates).values()),
            default=0,
        ),
        "pool_entropy_score": 0.0,
    }

    observation = _structural_observation(ranked_candidates, premium_games)
    compression_metrics["pool_entropy_score"] = observation.pool_entropy_score
    return ranked_candidates, premium_games, {
        "compression_metrics": compression_metrics,
        "observation": observation.as_dict(),
        "candidate_pool_count": len(candidate_pool),
        "filtered_count": filtered_count,
        "total_combinations": total,
        "premium_limit": premium_limit,
    }


def _summarize_games(
    games: Sequence[dict[str, Any]],
    target: Draw,
) -> dict[str, Any]:
    hits = [len(set(game["numbers"]) & set(target.numbers)) for game in games]
    numbers = [tuple(game["numbers"]) for game in games]
    overlaps = []
    for index, first in enumerate(numbers):
        for second in numbers[index + 1 :]:
            overlaps.append(len(set(first).intersection(second)) / SIMPLE_GAME_SIZE)
    distribution = Counter(numbers)
    entropy = 0.0
    for count in distribution.values():
        share = count / max(1, len(numbers))
        if share:
            entropy -= share * log2(share)
    max_entropy = log2(len(distribution)) if len(distribution) > 1 else 1.0
    entropy = round((entropy / max_entropy) if max_entropy else 0.0, 4)
    return {
        "games_count": len(games),
        "average_hits": round(_mean(hits), 4),
        "best_hits": max(hits) if hits else 0,
        "worst_hits": min(hits) if hits else 0,
        "hits_11_plus": sum(1 for hit in hits if hit >= 11),
        "hits_12_plus": sum(1 for hit in hits if hit >= 12),
        "average_overlap": round(_mean(overlaps), 4),
        "entropy": entropy,
        "unique_ratio_real": round(len(distribution) / max(1, len(numbers)), 4),
        "dominant_numbers": [
            {"number": number, "frequency": count}
            for number, count in Counter(number for game in numbers for number in game).most_common(10)
        ],
        "cluster_dispersion": round(
            len({(number - 1) // 5 for game in numbers for number in game}) / 5.0 if numbers else 0.0,
            4,
        ),
        "average_distance": round(
            _mean(
                _hamming_distance(first, second) / (SIMPLE_GAME_SIZE * 2)
                for index, first in enumerate(numbers)
                for second in numbers[index + 1 :]
            ),
            4,
        ),
    }


def _persist_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "contest",
        "baseline_average_hits",
        "ia_structural_average_hits",
        "ia_structural_moderate_average_hits",
        "delta_average_hits",
        "delta_moderate_average_hits",
        "baseline_11_plus",
        "ia_structural_11_plus",
        "ia_structural_moderate_11_plus",
        "delta_11_plus",
        "delta_moderate_11_plus",
        "baseline_12_plus",
        "ia_structural_12_plus",
        "ia_structural_moderate_12_plus",
        "delta_12_plus",
        "delta_moderate_12_plus",
        "baseline_overlap",
        "ia_structural_overlap",
        "ia_structural_moderate_overlap",
        "baseline_entropy",
        "ia_structural_entropy",
        "ia_structural_moderate_entropy",
        "baseline_unique_ratio_real",
        "ia_structural_unique_ratio_real",
        "ia_structural_moderate_unique_ratio_real",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _persist_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_ia_structural_experiment(
    *,
    draws: Sequence[Draw] | None = None,
    contests_analyzed: int | Sequence[int] = 30,
    games_count: int = 5,
    pool_size: int = 30,
    history_window: int | None = 200,
    seed: int = 7,
    output_dir: Path = DEFAULT_IA_STRUCTURAL_DIR,
) -> IAStructuralExperimentResult:
    if games_count < 1:
        raise ValueError("A quantidade de jogos deve ser maior que zero.")
    if pool_size < games_count:
        raise ValueError("O pool deve ser maior ou igual a quantidade de jogos.")
    if history_window is not None and history_window < 1:
        raise ValueError("A janela historica deve ser maior que zero.")

    ordered_draws = sorted(draws or load_draws_csv(), key=lambda draw: draw.contest)
    targets = _select_targets(ordered_draws, contests_analyzed)
    replay_rows: list[dict[str, Any]] = []
    per_contest: list[StructuralContestReplay] = []
    per_contest_moderate: list[dict[str, Any]] = []
    last_observation: dict[str, Any] = {}

    for target in targets:
        history = _history_for_target(ordered_draws, target, history_window)
        if not history:
            continue

        base_numbers_text = _default_experiment_numbers(18)
        base_numbers = [int(number) for number in base_numbers_text.split()]
        ranked_candidates, premium_games, audit = _build_structural_candidate_pool(
            base_numbers,
            history,
            max_runtime_seconds=1.5,
            max_candidates=max(40, pool_size),
            premium_limit=pool_size,
        )

        baseline_selected = list(premium_games[:games_count])
        observation = StructuralPoolObservation(**audit["observation"])
        last_observation = observation.as_dict()
        light_candidates = []
        moderate_candidates = []
        for candidate in ranked_candidates:
            lightweight_candidate = dict(candidate)
            lightweight_candidate["ia_structural_score"] = _structural_adjusted_score(lightweight_candidate, observation)
            light_candidates.append(lightweight_candidate)

            moderate_candidate = dict(candidate)
            moderate_candidate["ia_structural_score"] = _structural_adjusted_score_moderate(moderate_candidate, observation)
            moderate_candidates.append(moderate_candidate)

        sort_key = lambda row: (
            -float(row["ia_structural_score"]),
            -float(row.get("diversity_index", 0.0)),
            -float(row.get("coverage_score", 0.0)),
            float(row.get("overlap_score", 0.0)),
            float(row.get("partial_match_max", 0)),
            row["numbers"],
        )
        light_candidates.sort(key=sort_key)
        moderate_candidates.sort(key=sort_key)

        ia_structural_selected = light_candidates[:games_count]
        ia_structural_moderate_selected = moderate_candidates[:games_count]
        if len(ia_structural_selected) < games_count:
            ia_structural_selected = light_candidates[: min(games_count, len(light_candidates))]
        if len(ia_structural_moderate_selected) < games_count:
            ia_structural_moderate_selected = moderate_candidates[: min(games_count, len(moderate_candidates))]

        baseline_summary = _summarize_games(baseline_selected, target)
        ia_structural_summary = _summarize_games(ia_structural_selected, target)
        ia_structural_moderate_summary = _summarize_games(ia_structural_moderate_selected, target)
        signature_source = {
            "contest": target.contest,
            "seed": seed,
            "base_numbers": base_numbers,
            "observation": observation.as_dict(),
            "baseline": baseline_summary,
            "ia_structural": ia_structural_summary,
            "ia_structural_moderate": ia_structural_moderate_summary,
        }
        observability_signature = hashlib.sha256(
            json.dumps(signature_source, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()

        per_contest.append(
            StructuralContestReplay(
                contest=target.contest,
                baseline=baseline_summary,
                ia_structural=ia_structural_summary,
                delta_average_hits=round(
                    ia_structural_summary["average_hits"] - baseline_summary["average_hits"],
                    4,
                ),
                delta_11_plus=int(ia_structural_summary["hits_11_plus"] - baseline_summary["hits_11_plus"]),
                delta_12_plus=int(ia_structural_summary["hits_12_plus"] - baseline_summary["hits_12_plus"]),
                observational_signature=observability_signature,
            )
        )

        replay_rows.append(
            {
                "contest": target.contest,
                "baseline_average_hits": baseline_summary["average_hits"],
                "ia_structural_average_hits": ia_structural_summary["average_hits"],
                "ia_structural_moderate_average_hits": ia_structural_moderate_summary["average_hits"],
                "delta_average_hits": round(ia_structural_summary["average_hits"] - baseline_summary["average_hits"], 4),
                "delta_moderate_average_hits": round(
                    ia_structural_moderate_summary["average_hits"] - baseline_summary["average_hits"],
                    4,
                ),
                "baseline_11_plus": baseline_summary["hits_11_plus"],
                "ia_structural_11_plus": ia_structural_summary["hits_11_plus"],
                "ia_structural_moderate_11_plus": ia_structural_moderate_summary["hits_11_plus"],
                "delta_11_plus": int(ia_structural_summary["hits_11_plus"] - baseline_summary["hits_11_plus"]),
                "delta_moderate_11_plus": int(
                    ia_structural_moderate_summary["hits_11_plus"] - baseline_summary["hits_11_plus"]
                ),
                "baseline_12_plus": baseline_summary["hits_12_plus"],
                "ia_structural_12_plus": ia_structural_summary["hits_12_plus"],
                "ia_structural_moderate_12_plus": ia_structural_moderate_summary["hits_12_plus"],
                "delta_12_plus": int(ia_structural_summary["hits_12_plus"] - baseline_summary["hits_12_plus"]),
                "delta_moderate_12_plus": int(
                    ia_structural_moderate_summary["hits_12_plus"] - baseline_summary["hits_12_plus"]
                ),
                "baseline_overlap": baseline_summary["average_overlap"],
                "ia_structural_overlap": ia_structural_summary["average_overlap"],
                "ia_structural_moderate_overlap": ia_structural_moderate_summary["average_overlap"],
                "baseline_entropy": baseline_summary["entropy"],
                "ia_structural_entropy": ia_structural_summary["entropy"],
                "ia_structural_moderate_entropy": ia_structural_moderate_summary["entropy"],
                "baseline_unique_ratio_real": baseline_summary["unique_ratio_real"],
                "ia_structural_unique_ratio_real": ia_structural_summary["unique_ratio_real"],
                "ia_structural_moderate_unique_ratio_real": ia_structural_moderate_summary["unique_ratio_real"],
            }
        )

        per_contest_moderate.append({
            "contest": target.contest,
            "baseline": baseline_summary,
            "ia_structural": ia_structural_summary,
            "ia_structural_moderate": ia_structural_moderate_summary,
        })

    baseline_hits = [row.baseline["average_hits"] for row in per_contest]
    ia_structural_hits = [row.ia_structural["average_hits"] for row in per_contest]
    ia_structural_moderate_hits = [row["ia_structural_moderate"]["average_hits"] for row in per_contest_moderate]
    baseline_11_plus = [row.baseline["hits_11_plus"] for row in per_contest]
    ia_structural_11_plus = [row.ia_structural["hits_11_plus"] for row in per_contest]
    ia_structural_moderate_11_plus = [row["ia_structural_moderate"]["hits_11_plus"] for row in per_contest_moderate]
    baseline_12_plus = [row.baseline["hits_12_plus"] for row in per_contest]
    ia_structural_12_plus = [row.ia_structural["hits_12_plus"] for row in per_contest]
    ia_structural_moderate_12_plus = [row["ia_structural_moderate"]["hits_12_plus"] for row in per_contest_moderate]
    baseline_overlap = [row.baseline["average_overlap"] for row in per_contest]
    ia_structural_overlap = [row.ia_structural["average_overlap"] for row in per_contest]
    ia_structural_moderate_overlap = [row["ia_structural_moderate"]["average_overlap"] for row in per_contest_moderate]
    baseline_entropy = [row.baseline["entropy"] for row in per_contest]
    ia_structural_entropy = [row.ia_structural["entropy"] for row in per_contest]
    ia_structural_moderate_entropy = [row["ia_structural_moderate"]["entropy"] for row in per_contest_moderate]

    summary = {
        "baseline": {
            "average_hits": round(_mean(baseline_hits), 4),
            "hits_11_plus": int(sum(baseline_11_plus)),
            "hits_12_plus": int(sum(baseline_12_plus)),
            "average_overlap": round(_mean(baseline_overlap), 4),
            "entropy": round(_mean(baseline_entropy), 4),
            "unique_ratio_real": round(_mean([row.baseline["unique_ratio_real"] for row in per_contest]), 4) if per_contest else 0.0,
            "standard_deviation": round(_safe_pstdev(baseline_hits), 4),
        },
        "ia_structural": {
            "average_hits": round(_mean(ia_structural_hits), 4),
            "hits_11_plus": int(sum(ia_structural_11_plus)),
            "hits_12_plus": int(sum(ia_structural_12_plus)),
            "average_overlap": round(_mean(ia_structural_overlap), 4),
            "entropy": round(_mean(ia_structural_entropy), 4),
            "unique_ratio_real": round(_mean([row.ia_structural["unique_ratio_real"] for row in per_contest]), 4) if per_contest else 0.0,
            "standard_deviation": round(_safe_pstdev(ia_structural_hits), 4),
        },
        "ia_structural_moderate": {
            "average_hits": round(_mean(ia_structural_moderate_hits), 4),
            "hits_11_plus": int(sum(ia_structural_moderate_11_plus)),
            "hits_12_plus": int(sum(ia_structural_moderate_12_plus)),
            "average_overlap": round(_mean(ia_structural_moderate_overlap), 4),
            "entropy": round(_mean(ia_structural_moderate_entropy), 4),
            "unique_ratio_real": round(
                _mean([row["ia_structural_moderate_unique_ratio_real"] for row in replay_rows]),
                4,
            )
            if replay_rows
            else 0.0,
            "standard_deviation": round(_safe_pstdev(ia_structural_moderate_hits), 4),
        },
        "delta": {
            "average_hits": round(_mean(ia_structural_hits) - _mean(baseline_hits), 4),
            "hits_11_plus": int(sum(ia_structural_11_plus) - sum(baseline_11_plus)),
            "hits_12_plus": int(sum(ia_structural_12_plus) - sum(baseline_12_plus)),
            "average_overlap": round(_mean(ia_structural_overlap) - _mean(baseline_overlap), 4),
            "entropy": round(_mean(ia_structural_entropy) - _mean(baseline_entropy), 4),
            "unique_ratio_real": round(
                _mean([row.ia_structural["unique_ratio_real"] for row in per_contest])
                - _mean([row.baseline["unique_ratio_real"] for row in per_contest]),
                4,
            )
            if per_contest
            else 0.0,
        },
        "delta_moderate": {
            "average_hits": round(_mean(ia_structural_moderate_hits) - _mean(baseline_hits), 4),
            "hits_11_plus": int(sum(ia_structural_moderate_11_plus) - sum(baseline_11_plus)),
            "hits_12_plus": int(sum(ia_structural_moderate_12_plus) - sum(baseline_12_plus)),
            "average_overlap": round(_mean(ia_structural_moderate_overlap) - _mean(baseline_overlap), 4),
            "entropy": round(_mean(ia_structural_moderate_entropy) - _mean(baseline_entropy), 4),
            "unique_ratio_real": round(
                _mean([row["ia_structural_moderate_unique_ratio_real"] for row in replay_rows])
                - _mean([row.baseline["unique_ratio_real"] for row in per_contest]),
                4,
            )
            if per_contest
            else 0.0,
        },
        "observation": last_observation,
        "benchmark_configuration": {
            "contests_analyzed": len(per_contest),
            "games_count": games_count,
            "pool_size": pool_size,
            "history_window": history_window,
            "seed": seed,
            "package_size": 18,
            "operational_mode": "HB + IA_structural_light",
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "benchmark_version": IA_STRUCTURAL_EXPERIMENT_VERSION,
        "structural_version": IA_STRUCTURAL_ENGINE_VERSION,
        "created_at": _now(),
        "seed": seed,
        "contests_analyzed": len(per_contest),
        "games_count": games_count,
        "pool_size": pool_size,
        "history_window": history_window,
        "summary": summary,
        "replay": [row.as_dict() for row in per_contest],
    }
    _persist_json(output_dir / "ia_structural_experiment.json", payload)
    _persist_csv(output_dir / "ia_structural_experiment.csv", replay_rows)

    return IAStructuralExperimentResult(
        benchmark_version=IA_STRUCTURAL_EXPERIMENT_VERSION,
        structural_version=IA_STRUCTURAL_ENGINE_VERSION,
        created_at=payload["created_at"],
        seed=seed,
        contests_analyzed=len(per_contest),
        games_count=games_count,
        pool_size=pool_size,
        history_window=history_window,
        replay=[row.as_dict() for row in per_contest],
        summary=summary,
        report_paths={
            "json": str((output_dir / "ia_structural_experiment.json").resolve()),
            "csv": str((output_dir / "ia_structural_experiment.csv").resolve()),
        },
    )
