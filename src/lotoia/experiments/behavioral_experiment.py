from __future__ import annotations

import json
import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from lotoia.data.loader import load_draws_csv
from lotoia.generator.basic_generator import generate_best_games
from lotoia.statistics.generation_trace import (
    behavioral_metrics,
    behavior_recovery_timeline,
    historical_adherence_score,
    marginal_recovery_gain,
    pressure_sensitivity_report,
    profile_stability_score,
    recovery_decision_protocol,
    recovery_plateau_detection,
    safe_recovery_zone,
)


@dataclass(frozen=True)
class BehavioralExperimentResult:
    experiment_id: str
    seeds: list[int]
    baseline_mode: str
    experimental_mode: str
    baseline_runs: list[dict[str, Any]]
    experimental_runs: list[dict[str, Any]]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "seeds": self.seeds,
            "baseline_mode": self.baseline_mode,
            "experimental_mode": self.experimental_mode,
            "baseline_runs": self.baseline_runs,
            "experimental_runs": self.experimental_runs,
            "summary": self.summary,
        }


@contextmanager
def _env_overrides(values: dict[str, str]):
    previous = {key: os.environ.get(key) for key in values}
    try:
        for key, value in values.items():
            os.environ[key] = value
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _summary_from_runs(runs: list[dict[str, Any]]) -> dict[str, float]:
    if not runs:
        return {
            "recovery": 0.0,
            "adherence": 0.0,
            "drift": 0.0,
            "false_recovery_rate": 0.0,
            "stability": 0.0,
            "divergence": 0.0,
            "rarity_std": 0.0,
            "normalization_pressure": 0.0,
            "recurrence_density": 0.0,
        }
    mean = lambda key: sum(float(run.get(key, 0.0)) for run in runs) / len(runs)
    return {
        "recovery": round(mean("recovery"), 4),
        "adherence": round(mean("adherence"), 4),
        "drift": round(mean("drift"), 4),
        "false_recovery_rate": round(sum(1 for run in runs if run.get("false_recovery")) / len(runs), 4),
        "stability": round(mean("profile_stability"), 4),
        "divergence": round(mean("pipeline_divergence"), 4),
        "rarity_std": round(mean("rarity_std"), 4),
        "normalization_pressure": round(mean("normalization_pressure"), 4),
        "recurrence_density": round(mean("recurrence_density"), 4),
    }


def run_experiment_01(
    *,
    seeds: Iterable[int] | None = None,
    count: int = 20,
    pool_size: int = 30,
    report_dir: Path | None = None,
) -> BehavioralExperimentResult:
    seed_list = list(seeds or [7, 11, 13, 17, 19])
    history = load_draws_csv()
    baseline_runs: list[dict[str, Any]] = []
    experimental_runs: list[dict[str, Any]] = []

    for seed in seed_list:
        with _env_overrides({"NORMALIZATION_PRESSURE_LEVEL": "hard", "FILTERS_DISABLED": "false"}):
            baseline = generate_best_games(count=count, pool_size=pool_size, ml_enabled=False, seed=seed)
        with _env_overrides({"NORMALIZATION_PRESSURE_LEVEL": "medium", "FILTERS_DISABLED": "false"}):
            experimental = generate_best_games(count=count, pool_size=pool_size, ml_enabled=False, seed=seed)
        baseline_metrics = behavioral_metrics([game for game in baseline["games"]], history=history)
        experimental_metrics = behavioral_metrics([game for game in experimental["games"]], history=history)
        baseline_row = {
            "seed": seed,
            "mode": "hard",
            "profile_counts": baseline["profile_counts"],
            "profile_percentages": baseline["profile_percentages"],
            "recovery": round((baseline_metrics["recurrence_density"] + baseline_metrics["structural_entropy"]) / 2, 4),
            "adherence": round(
                baseline_metrics["recurrence_density"] * 0.40
                + baseline_metrics["structural_entropy"] * 0.25
                + baseline_metrics["cluster_aggressiveness"] * 0.20
                + baseline_metrics["rarity_std"] * 0.15,
                4,
            ),
            "drift": round(baseline_metrics["normalization_pressure"] * 0.60, 4),
            "false_recovery": baseline_metrics["normalization_pressure"] > 0.20 and baseline_metrics["rarity_std"] < 0.20,
            "profile_stability": round((baseline["profile_percentages"].get("hibrido", 0.0) / 100.0) * 0.50, 4),
            "pipeline_divergence": round(
                baseline_metrics["normalization_pressure"] * 0.45
                + baseline_metrics["cluster_aggressiveness"] * 0.25
                + baseline_metrics["structural_entropy"] * 0.20
                + baseline_metrics["recurrence_density"] * 0.10,
                4,
            ),
            "rarity_std": baseline_metrics["rarity_std"],
            "normalization_pressure": baseline_metrics["normalization_pressure"],
            "recurrence_density": baseline_metrics["recurrence_density"],
            "trace": {},
            "history_size": len(history),
        }
        experimental_row = {
            "seed": seed,
            "mode": "medium",
            "profile_counts": experimental["profile_counts"],
            "profile_percentages": experimental["profile_percentages"],
            "recovery": round((experimental_metrics["recurrence_density"] + experimental_metrics["structural_entropy"]) / 2, 4),
            "adherence": round(
                experimental_metrics["recurrence_density"] * 0.40
                + experimental_metrics["structural_entropy"] * 0.25
                + experimental_metrics["cluster_aggressiveness"] * 0.20
                + experimental_metrics["rarity_std"] * 0.15,
                4,
            ),
            "drift": round(experimental_metrics["normalization_pressure"] * 0.60, 4),
            "false_recovery": experimental_metrics["normalization_pressure"] > 0.20 and experimental_metrics["rarity_std"] < 0.20,
            "profile_stability": round((experimental["profile_percentages"].get("hibrido", 0.0) / 100.0) * 0.50, 4),
            "pipeline_divergence": round(
                experimental_metrics["normalization_pressure"] * 0.45
                + experimental_metrics["cluster_aggressiveness"] * 0.25
                + experimental_metrics["structural_entropy"] * 0.20
                + experimental_metrics["recurrence_density"] * 0.10,
                4,
            ),
            "rarity_std": experimental_metrics["rarity_std"],
            "normalization_pressure": experimental_metrics["normalization_pressure"],
            "recurrence_density": experimental_metrics["recurrence_density"],
            "trace": {},
            "history_size": len(history),
        }
        baseline_runs.append(baseline_row)
        experimental_runs.append(experimental_row)

    summary = {
        "baseline": _summary_from_runs(baseline_runs),
        "experimental": _summary_from_runs(experimental_runs),
        "behavior_integrity_recovery": round(
            _summary_from_runs(experimental_runs)["recovery"] - _summary_from_runs(baseline_runs)["recovery"],
            4,
        ),
        "marginal_recovery_gain": round(
            _summary_from_runs(experimental_runs)["recovery"] - _summary_from_runs(baseline_runs)["recovery"],
            4,
        ),
        "recovery_decision_protocol": recovery_decision_protocol(),
        "safe_recovery_zone": safe_recovery_zone(),
        "behavior_recovery_timeline": behavior_recovery_timeline(),
        "marginal_recovery_gain": marginal_recovery_gain(),
        "plateau_detection": recovery_plateau_detection(),
        "historical_adherence": historical_adherence_score(),
        "pressure_sensitivity": pressure_sensitivity_report(),
        "profile_stability": profile_stability_score(),
    }

    if report_dir is not None:
        report_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "created_at": datetime.now(UTC).isoformat(),
            "result": {
                "experiment_id": "experiment_01_normalize_distribution",
                "baseline_mode": "hard",
                "experimental_mode": "medium",
                "seeds": seed_list,
                "summary": summary,
            },
            "baseline_runs": baseline_runs,
            "experimental_runs": experimental_runs,
        }
        (report_dir / "experiment_01_report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return BehavioralExperimentResult(
        experiment_id="experiment_01_normalize_distribution",
        seeds=seed_list,
        baseline_mode="hard",
        experimental_mode="medium",
        baseline_runs=baseline_runs,
        experimental_runs=experimental_runs,
        summary=summary,
    )
