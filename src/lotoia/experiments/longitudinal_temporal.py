from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from math import log2
from pathlib import Path
from random import Random
from statistics import pstdev
from typing import Any

from lotoia.benchmark.benchmark_engine import (
    _apply_hits,
    _compose_profiled_games,
    _generate_filtered_candidates,
    _history_for_target,
    _hybrid_sort_key,
    _score_lotoia_games,
    _select_targets,
)
from lotoia.data.loader import load_draws_csv
from lotoia.experiments.temporal_governance import (
    TemporalSplit,
    build_walk_forward_splits,
    validate_temporal_integrity,
    validate_train_test_separation,
)
from lotoia.models.draw import Draw
from lotoia.statistics.temporal import MAX_TEMPORAL_INFLUENCE, build_temporal_signal, temporal_rerank

TEMPORAL_LONGITUDINAL_BENCHMARK_VERSION = "0.1.0"
TEMPORAL_LONGITUDINAL_ENGINE_VERSION = "temporal_v1"
DEFAULT_TEMPORAL_LONGITUDINAL_DIR = Path("reports/temporal_longitudinal")


@dataclass(frozen=True)
class TemporalContestReplay:
    contest: int
    cutoff_contest: int
    history_size: int
    replay_window: str
    baseline: dict[str, Any]
    temporal: dict[str, Any]
    delta_average_hits: float
    temporal_adjustment: float
    observability_signature: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "contest": self.contest,
            "cutoff_contest": self.cutoff_contest,
            "history_size": self.history_size,
            "replay_window": self.replay_window,
            "baseline": self.baseline,
            "temporal": self.temporal,
            "delta_average_hits": self.delta_average_hits,
            "temporal_adjustment": self.temporal_adjustment,
            "observability_signature": self.observability_signature,
        }


@dataclass(frozen=True)
class TemporalLongitudinalBenchmarkResult:
    benchmark_version: str
    temporal_version: str
    created_at: str
    seed: int
    contests_analyzed: int
    games_count: int
    pool_size: int
    history_window: int | None
    min_train_size: int
    test_size: int
    step_size: int
    replay_windows: list[dict[str, Any]]
    summary: dict[str, Any]
    report_paths: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_version": self.benchmark_version,
            "temporal_version": self.temporal_version,
            "created_at": self.created_at,
            "seed": self.seed,
            "contests_analyzed": self.contests_analyzed,
            "games_count": self.games_count,
            "pool_size": self.pool_size,
            "history_window": self.history_window,
            "min_train_size": self.min_train_size,
            "test_size": self.test_size,
            "step_size": self.step_size,
            "replay_windows": self.replay_windows,
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


def _window_bucket(history_size: int) -> str:
    if history_size < 20:
        return "short"
    if history_size < 50:
        return "medium"
    return "long"


def _load_ordered_draws(draws: Sequence[Draw] | None = None) -> list[Draw]:
    ordered_draws = sorted(draws or load_draws_csv(), key=lambda draw: draw.contest)
    validate_temporal_integrity([draw.contest for draw in ordered_draws]).assert_valid()
    return ordered_draws


def _temporal_adjusted_games(
    games: list[dict[str, Any]],
    history: list[Draw],
    *,
    contest: int,
) -> list[dict[str, Any]]:
    adjusted_games: list[dict[str, Any]] = []
    for index, game in enumerate(games, start=1):
        numbers = [int(number) for number in game["numbers"]]
        temporal_signal = build_temporal_signal(numbers, history)
        rerank = temporal_rerank(
            float(game.get("profile_score", game.get("final_score", {}).get("final_score", 0.0))) / 100.0,
            temporal_signal,
        )
        adjusted_games.append(
            {
                **game,
                "contest": contest,
                "rank": index,
                "temporal_signal": temporal_signal.as_dict(),
                "base_score": float(rerank["base_score"]),
                "temporal_adjustment": float(rerank["temporal_adjustment"]),
                "final_score": {
                    "base_score": float(rerank["base_score"]),
                    "temporal_adjustment": float(rerank["temporal_adjustment"]),
                    "final_score": round(float(rerank["final_score"]) * 100.0, 2),
                },
                "cycle_state": rerank["cycle_state"],
                "pressure_score": float(rerank["pressure_score"]),
                "migration_signal": float(rerank["migration_signal"]),
                "temporal_decay": float(rerank["temporal_decay"]),
                "temporal_rerank_reason": str(rerank["rerank_reason"]),
            }
        )
    return adjusted_games


def _temporal_selection_sort_key(game: Mapping[str, object]) -> tuple[float, float, int, float]:
    final_score = game.get("final_score", {})
    if isinstance(final_score, Mapping):
        temporal_value = float(final_score.get("final_score", 0.0) or 0.0)
    else:
        temporal_value = float(final_score or 0.0)
    quadra_score = game.get("quadra_score", {})
    if not isinstance(quadra_score, Mapping):
        quadra_score = {}
    return (
        -temporal_value,
        -float(game.get("profile_score", 0.0) or 0.0),
        -int(quadra_score.get("found_quadras", 0) or 0),
        float(quadra_score.get("average_rank", 0.0) or 0.0),
    )


def _selection_summary(games: Sequence[Mapping[str, object]]) -> dict[str, object]:
    hits = [int(game["hits"]) for game in games]
    scores = [
        float(game.get("final_score", {}).get("final_score", 0.0))
        if isinstance(game.get("final_score"), Mapping)
        else float(game.get("final_score", 0.0) or 0.0)
        for game in games
    ]
    return {
        "games_count": len(games),
        "average_hits": _mean(hits),
        "standard_deviation": _safe_pstdev(hits),
        "final_score_average": _mean(scores),
        "best_hits": max(hits) if hits else 0,
        "worst_hits": min(hits) if hits else 0,
        "games": [
            {
                "numbers": list(game["numbers"]),
                "hits": int(game["hits"]),
                "final_score": game.get("final_score", {}),
                "temporal_adjustment": float(game.get("temporal_adjustment", 0.0) or 0.0),
                "cycle_state": game.get("cycle_state"),
                "pressure_score": game.get("pressure_score"),
                "migration_signal": game.get("migration_signal"),
                "temporal_decay": game.get("temporal_decay"),
                "observability_signature": game.get("observability_signature"),
            }
            for game in games
        ],
    }


def _persist_rows_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "split_id",
        "contest",
        "replay_window",
        "baseline_average_hits",
        "temporal_average_hits",
        "delta_average_hits",
        "baseline_stability",
        "temporal_stability",
        "temporal_adjustment",
        "observability_signature",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_longitudinal_temporal_benchmark(
    *,
    draws: Sequence[Draw] | None = None,
    contests_analyzed: int | Sequence[int] = 10,
    games_count: int = 10,
    pool_size: int = 30,
    history_window: int | None = 200,
    seed: int = 42,
    min_train_size: int = 2000,
    test_size: int = 10,
    step_size: int = 10,
    stability_window: int = 5,
    output_dir: Path = DEFAULT_TEMPORAL_LONGITUDINAL_DIR,
) -> TemporalLongitudinalBenchmarkResult:
    if games_count < 1:
        raise ValueError("A quantidade de jogos deve ser maior que zero.")
    if pool_size < games_count:
        raise ValueError("O pool deve ser maior ou igual a quantidade de jogos.")
    if history_window is not None and history_window < 1:
        raise ValueError("A janela historica deve ser maior que zero.")
    if stability_window < 1:
        raise ValueError("A janela de estabilidade deve ser maior que zero.")
    if min_train_size < 1:
        raise ValueError("min_train_size must be positive")
    if test_size < 1:
        raise ValueError("test_size must be positive")
    if step_size < 1:
        raise ValueError("step_size must be positive")

    ordered_draws = _load_ordered_draws(draws)
    contests = [draw.contest for draw in ordered_draws]
    split_windows = build_walk_forward_splits(
        contests,
        min_train_size=min_train_size,
        test_size=test_size,
        step_size=step_size,
    )
    for split in split_windows:
        validate_train_test_separation(split).assert_valid()

    targets = _select_targets(ordered_draws, contests_analyzed)
    replay_windows: list[dict[str, Any]] = []
    csv_rows: list[dict[str, object]] = []

    for split in split_windows:
        split_targets = [draw for draw in targets if split.test_start <= draw.contest <= split.test_end]
        for target in split_targets:
            history = _history_for_target(ordered_draws, target, history_window)
            if not history:
                continue

            base_seed = seed + target.contest
            pool = _generate_filtered_candidates(pool_size, Random(base_seed), history)
            scored_pool = _score_lotoia_games(pool, target, history)

            baseline_selected = _compose_profiled_games([dict(game) for game in scored_pool], games_count)
            temporal_scored_pool = _temporal_adjusted_games([dict(game) for game in scored_pool], history, contest=target.contest)
            temporal_selected = sorted(temporal_scored_pool, key=_temporal_selection_sort_key)[:games_count]

            baseline_with_hits = _apply_hits([dict(game) for game in baseline_selected], target)
            temporal_with_hits = _apply_hits([dict(game) for game in temporal_selected], target)

            baseline_summary = _selection_summary(baseline_with_hits)
            temporal_summary = _selection_summary(temporal_with_hits)
            delta_average_hits = float(temporal_summary["average_hits"]) - float(baseline_summary["average_hits"])
            adjustment_mean = _mean(float(game.get("temporal_adjustment", 0.0)) for game in temporal_selected)
            observability_signature = sha256(
                json.dumps(
                    {
                        "contest": target.contest,
                        "split_id": split.split_id,
                        "baseline": baseline_summary,
                        "temporal": temporal_summary,
                        "history_size": len(history),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                ).encode("utf-8")
            ).hexdigest()

            replay_windows.append(
                {
                    "split_id": split.split_id,
                    "contest": target.contest,
                    "cutoff_contest": history[-1].contest,
                    "history_size": len(history),
                    "replay_window": _window_bucket(len(history)),
                    "baseline": baseline_summary,
                    "temporal": temporal_summary,
                    "delta_average_hits": round(delta_average_hits, 4),
                    "temporal_adjustment": round(adjustment_mean, 4),
                    "observability_signature": observability_signature,
                }
            )
            csv_rows.append(
                {
                    "split_id": split.split_id,
                    "contest": target.contest,
                    "replay_window": _window_bucket(len(history)),
                    "baseline_average_hits": round(float(baseline_summary["average_hits"]), 4),
                    "temporal_average_hits": round(float(temporal_summary["average_hits"]), 4),
                    "delta_average_hits": round(delta_average_hits, 4),
                    "baseline_stability": round(float(baseline_summary["standard_deviation"]), 4),
                    "temporal_stability": round(float(temporal_summary["standard_deviation"]), 4),
                    "temporal_adjustment": round(adjustment_mean, 4),
                    "observability_signature": observability_signature,
                }
            )

    if not replay_windows:
        raise ValueError("No replay windows were produced for the requested configuration")

    baseline_hits = [float(row["baseline"]["average_hits"]) for row in replay_windows]
    temporal_hits = [float(row["temporal"]["average_hits"]) for row in replay_windows]
    delta_hits = [float(row["delta_average_hits"]) for row in replay_windows]
    baseline_stability = [float(row["baseline"]["standard_deviation"]) for row in replay_windows]
    temporal_stability = [float(row["temporal"]["standard_deviation"]) for row in replay_windows]
    temporal_adjustments = [float(row["temporal_adjustment"]) for row in replay_windows]

    bucketed: dict[str, list[float]] = {"short": [], "medium": [], "long": []}
    for row in replay_windows:
        bucketed[str(row["replay_window"])].append(float(row["delta_average_hits"]))

    summary = {
        "benchmark_version": TEMPORAL_LONGITUDINAL_BENCHMARK_VERSION,
        "temporal_version": TEMPORAL_LONGITUDINAL_ENGINE_VERSION,
        "seed": seed,
        "contests_analyzed": len(replay_windows),
        "games_count": games_count,
        "pool_size": pool_size,
        "history_window": history_window,
        "min_train_size": min_train_size,
        "test_size": test_size,
        "step_size": step_size,
        "baseline_average_hits": round(_mean(baseline_hits), 4),
        "temporal_average_hits": round(_mean(temporal_hits), 4),
        "average_hit_delta": round(_mean(delta_hits), 4),
        "baseline_stability": round(_mean(baseline_stability), 4),
        "temporal_stability": round(_mean(temporal_stability), 4),
        "stability_delta": round(_mean(temporal_stability) - _mean(baseline_stability), 4),
        "temporal_adjustment": round(_mean(temporal_adjustments), 4),
        "window_deltas": {
            "short": round(_mean(bucketed["short"]), 4),
            "medium": round(_mean(bucketed["medium"]), 4),
            "long": round(_mean(bucketed["long"]), 4),
        },
        "reproducibility": {
            "freeze_level": "hb_temporal_v1_locked",
            "no_temporal_leakage": True,
            "cap": MAX_TEMPORAL_INFLUENCE,
        },
    }

    created_at = _now()
    output_dir.mkdir(parents=True, exist_ok=True)
    report_payload = {
        "benchmark_version": TEMPORAL_LONGITUDINAL_BENCHMARK_VERSION,
        "temporal_version": TEMPORAL_LONGITUDINAL_ENGINE_VERSION,
        "created_at": created_at,
        "summary": summary,
        "replay_windows": replay_windows,
        "configuration": {
            "contests_analyzed": list(contests[-contests_analyzed:]) if isinstance(contests_analyzed, int) else list(contests_analyzed),
            "games_count": games_count,
            "pool_size": pool_size,
            "history_window": history_window,
            "seed": seed,
            "min_train_size": min_train_size,
            "test_size": test_size,
            "step_size": step_size,
        },
    }
    json_path = output_dir / "temporal_longitudinal_result.json"
    csv_path = output_dir / "temporal_longitudinal_contests.csv"
    _write_json(json_path, report_payload)
    _persist_rows_csv(csv_path, csv_rows)

    return TemporalLongitudinalBenchmarkResult(
        benchmark_version=TEMPORAL_LONGITUDINAL_BENCHMARK_VERSION,
        temporal_version=TEMPORAL_LONGITUDINAL_ENGINE_VERSION,
        created_at=created_at,
        seed=seed,
        contests_analyzed=len(replay_windows),
        games_count=games_count,
        pool_size=pool_size,
        history_window=history_window,
        min_train_size=min_train_size,
        test_size=test_size,
        step_size=step_size,
        replay_windows=replay_windows,
        summary=summary,
        report_paths={"json": str(json_path), "csv": str(csv_path)},
    )
