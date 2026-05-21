from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from lotoia.data.loader import load_draws_csv
from lotoia.benchmark.benchmark_engine import run_benchmark

DEFAULT_LONGITUDINAL_DIR = Path("reports/longitudinal")
DEFAULT_CHECKPOINTS = (10, 25, 50, 100)


@dataclass(frozen=True)
class LongitudinalBaselineResult:
    baseline_mode: str
    seed: int
    checkpoints: list[int]
    runs: list[dict[str, Any]]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_mode": self.baseline_mode,
            "seed": self.seed,
            "checkpoints": self.checkpoints,
            "runs": self.runs,
            "summary": self.summary,
        }


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _strategy_snapshot(result: dict[str, Any]) -> dict[str, Any]:
    lotoia = result["strategies"]["lotoia_engine"]
    filtered = result["strategies"]["filtered_random"]
    pure = result["strategies"]["pure_random"]
    return {
        "contests_analyzed": result["contests_analyzed"],
        "lotoia": {
            "average_hits": round(float(lotoia["average_hits"]), 4),
            "standard_deviation": round(float(lotoia["standard_deviation"]), 4),
            "final_score_hit_correlation": round(float(lotoia["final_score_hit_correlation"]), 4),
            "stability_window_sd": round(
                _mean(float(window["standard_deviation"]) for window in lotoia["stability"]["windows"]),
                4,
            ),
            "hit_distribution": lotoia["hit_distribution"],
        },
        "filtered_random": {
            "average_hits": round(float(filtered["average_hits"]), 4),
            "standard_deviation": round(float(filtered["standard_deviation"]), 4),
        },
        "pure_random": {
            "average_hits": round(float(pure["average_hits"]), 4),
            "standard_deviation": round(float(pure["standard_deviation"]), 4),
        },
        "comparisons": result["comparisons"],
    }


def _snapshot_from_merged(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "contests_analyzed": result["contests_analyzed"],
        "lotoia": {
            "average_hits": round(float(result["lotoia"]["average_hits"]), 4),
            "standard_deviation": round(float(result["lotoia"]["standard_deviation"]), 4),
            "final_score_hit_correlation": round(float(result["lotoia"]["final_score_hit_correlation"]), 4),
            "stability_window_sd": round(float(result["lotoia"]["stability_window_sd"]), 4),
            "hit_distribution": result["lotoia"]["hit_distribution"],
        },
        "filtered_random": {
            "average_hits": round(float(result["filtered_random"]["average_hits"]), 4),
            "standard_deviation": round(float(result["filtered_random"]["standard_deviation"]), 4),
        },
        "pure_random": {
            "average_hits": round(float(result["pure_random"]["average_hits"]), 4),
            "standard_deviation": round(float(result["pure_random"]["standard_deviation"]), 4),
        },
        "comparisons": result["comparisons"],
    }


def _merge_run_snapshots(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    if not snapshots:
        return {
            "contests_analyzed": 0,
            "lotoia": {"average_hits": 0.0, "standard_deviation": 0.0, "final_score_hit_correlation": 0.0, "stability_window_sd": 0.0, "hit_distribution": {}},
            "filtered_random": {"average_hits": 0.0, "standard_deviation": 0.0},
            "pure_random": {"average_hits": 0.0, "standard_deviation": 0.0},
            "comparisons": {},
        }

    contests_analyzed = sum(int(snapshot["contests_analyzed"]) for snapshot in snapshots)
    lotoia_avgs = [float(snapshot["lotoia"]["average_hits"]) for snapshot in snapshots]
    lotoia_sds = [float(snapshot["lotoia"]["standard_deviation"]) for snapshot in snapshots]
    lotoia_corr = [float(snapshot["lotoia"]["final_score_hit_correlation"]) for snapshot in snapshots]
    lotoia_stability = [float(snapshot["lotoia"]["stability_window_sd"]) for snapshot in snapshots]
    filtered_avgs = [float(snapshot["filtered_random"]["average_hits"]) for snapshot in snapshots]
    filtered_sds = [float(snapshot["filtered_random"]["standard_deviation"]) for snapshot in snapshots]
    pure_avgs = [float(snapshot["pure_random"]["average_hits"]) for snapshot in snapshots]
    pure_sds = [float(snapshot["pure_random"]["standard_deviation"]) for snapshot in snapshots]

    merged_distribution: dict[str, int] = {}
    for snapshot in snapshots:
        for key, value in snapshot["lotoia"]["hit_distribution"].items():
            merged_distribution[key] = merged_distribution.get(key, 0) + int(value)

    return {
        "contests_analyzed": contests_analyzed,
        "lotoia": {
            "average_hits": round(_mean(lotoia_avgs), 4),
            "standard_deviation": round(_mean(lotoia_sds), 4),
            "final_score_hit_correlation": round(_mean(lotoia_corr), 4),
            "stability_window_sd": round(_mean(lotoia_stability), 4),
            "hit_distribution": merged_distribution,
        },
        "filtered_random": {
            "average_hits": round(_mean(filtered_avgs), 4),
            "standard_deviation": round(_mean(filtered_sds), 4),
        },
        "pure_random": {
            "average_hits": round(_mean(pure_avgs), 4),
            "standard_deviation": round(_mean(pure_sds), 4),
        },
        "comparisons": snapshots[-1]["comparisons"],
    }


def run_longitudinal_baseline(
    *,
    seed: int = 7,
    checkpoints: Iterable[int] | None = None,
    games_count: int = 5,
    pool_size: int = 8,
    history_window: int | None = 200,
    chunk_size: int = 10,
    output_dir: Path = DEFAULT_LONGITUDINAL_DIR,
) -> LongitudinalBaselineResult:
    checkpoint_list = sorted({int(checkpoint) for checkpoint in (checkpoints or DEFAULT_CHECKPOINTS)})
    if not checkpoint_list:
        raise ValueError("At least one checkpoint is required")

    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")

    ordered_draws = sorted(load_draws_csv(), key=lambda draw: draw.contest)
    runs: list[dict[str, Any]] = []
    for checkpoint in checkpoint_list:
        checkpoint_draws = [draw for draw in ordered_draws if draw.contest <= checkpoint]
        chunk_snapshots: list[dict[str, Any]] = []
        for chunk_start in range(0, len(checkpoint_draws), chunk_size):
            chunk_draws = checkpoint_draws[chunk_start : chunk_start + chunk_size]
            if not chunk_draws:
                continue
            benchmark = run_benchmark(
                draws=chunk_draws,
                contests_analyzed=[draw.contest for draw in chunk_draws],
                games_count=games_count,
                pool_size=pool_size,
                history_window=history_window,
                seed=seed,
                write_report=False,
                persist=False,
            )
            chunk_snapshots.append(_strategy_snapshot(benchmark.to_dict()))
        benchmark_dict = _merge_run_snapshots(chunk_snapshots)
        run_snapshot = {
            "checkpoint": checkpoint,
            "created_at": datetime.now(UTC).isoformat(),
            "result": _snapshot_from_merged(benchmark_dict),
            "chunks": chunk_snapshots,
        }
        runs.append(run_snapshot)

    lotoia_avgs = [float(run["result"]["lotoia"]["average_hits"]) for run in runs]
    lotoia_sd = [float(run["result"]["lotoia"]["standard_deviation"]) for run in runs]
    coverage_10 = sum(1 for run in runs if float(run["result"]["lotoia"]["average_hits"]) >= 10) / len(runs)
    coverage_11 = sum(1 for run in runs if float(run["result"]["lotoia"]["average_hits"]) >= 11) / len(runs)
    stability = 1 - (max(lotoia_sd) - min(lotoia_sd) if lotoia_sd else 0.0)

    summary = {
        "baseline_mode": "hard",
        "seed": seed,
        "checkpoints": checkpoint_list,
        "average_hits": round(_mean(lotoia_avgs), 4),
        "hits_standard_deviation": round(_mean(lotoia_sd), 4),
        "coverage_10": round(coverage_10, 4),
        "coverage_11": round(coverage_11, 4),
        "stability_index": round(stability, 4),
        "runtime_profile": "incremental_longitudinal",
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at": datetime.now(UTC).isoformat(),
        "baseline_mode": "hard",
        "seed": seed,
        "checkpoints": checkpoint_list,
        "summary": summary,
        "runs": runs,
    }
    (output_dir / "baseline_hard_longitudinal.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return LongitudinalBaselineResult(
        baseline_mode="hard",
        seed=seed,
        checkpoints=checkpoint_list,
        runs=runs,
        summary=summary,
    )
