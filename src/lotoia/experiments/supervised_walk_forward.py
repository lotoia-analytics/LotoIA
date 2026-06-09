from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from random import Random
from statistics import mean

from lotoia.benchmark.benchmark_engine import (
    STRATEGY_LOTOIA,
    _apply_hits,
    _generate_filtered_candidates,
    _history_for_target,
    _hybrid_sort_key,
    _score_lotoia_games,
)
from lotoia.data.loader import DEFAULT_HISTORY_PATH, load_draws_csv
from lotoia.experiments.supervised_scoring import validate_score_ml_rows
from lotoia.experiments.temporal_benchmark import build_dataset_snapshot
from lotoia.experiments.temporal_governance import (
    TemporalSplit,
    build_walk_forward_splits,
    validate_temporal_integrity,
    validate_train_test_separation,
)
from lotoia.ml.score_ml import (
    SCORE_ML_FEATURE_SCHEMA_VERSION,
    SCORE_ML_MODEL_VERSION,
    calibrate_linear_score_ml,
    extract_score_ml_features,
    supervised_rerank_games,
)
from lotoia.models.draw import Draw

DEFAULT_EXPERIMENT_ID = "score-ml-walk-forward-v0.1.0"
DEFAULT_DATASET_VERSION = "lotofacil-historico-v0.1.0-2026-05-16"
DEFAULT_REPORT_DIR = Path("reports/supervised_walk_forward/score_ml_v0_1_0")
DEFAULT_EXPERIMENT_DIR = Path("experiments/supervised_scoring/runs/score_ml_walk_forward_v0_1_0")


@dataclass(frozen=True)
class WalkForwardExecutionResult:
    experiment_id: str
    manifest_path: str
    report_path: str
    split_count: int
    benchmark_average_hits: float
    score_ml_average_hits: float
    average_hit_delta: float
    reproducibility_hash: str

    def as_dict(self) -> dict[str, object]:
        return {
            "experiment_id": self.experiment_id,
            "manifest_path": self.manifest_path,
            "report_path": self.report_path,
            "split_count": self.split_count,
            "benchmark_average_hits": self.benchmark_average_hits,
            "score_ml_average_hits": self.score_ml_average_hits,
            "average_hit_delta": self.average_hit_delta,
            "reproducibility_hash": self.reproducibility_hash,
        }


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _payload_hash(payload: Mapping[str, object] | Sequence[Mapping[str, object]]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def _contests_in_range(draws: Sequence[Draw], start: int, end: int) -> list[Draw]:
    return [draw for draw in draws if start <= draw.contest <= end]


def _target_rows(
    draws: Sequence[Draw],
    targets: Sequence[Draw],
    *,
    games_count: int,
    pool_size: int,
    history_window: int | None,
    seed: int,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for target in targets:
        history = _history_for_target(list(draws), target, history_window)
        if not history:
            continue

        base_seed = seed + target.contest
        pool = _generate_filtered_candidates(pool_size, Random(base_seed))
        scored_pool = _score_lotoia_games(pool, target, history)

        statistical_selected = sorted(scored_pool, key=_hybrid_sort_key)[:games_count]
        score_ml_selected = supervised_rerank_games([dict(game) for game in scored_pool])[:games_count]

        statistical_with_hits = _apply_hits([dict(game) for game in statistical_selected], target)
        score_ml_with_hits = _apply_hits([dict(game) for game in score_ml_selected], target)

        rows.append(
            {
                "contest": target.contest,
                "feature_cutoff_contest": history[-1].contest,
                "history_first_contest": history[0].contest,
                "history_last_contest": history[-1].contest,
                "history_size": len(history),
                "benchmark": _selection_summary(statistical_with_hits),
                "score_ml_rerank": _selection_summary(score_ml_with_hits),
            }
        )
    return rows


def _selection_summary(games: Sequence[Mapping[str, object]]) -> dict[str, object]:
    hits = [int(game["hits"]) for game in games]
    return {
        "strategy": STRATEGY_LOTOIA,
        "games_count": len(games),
        "average_hits": mean(hits) if hits else 0.0,
        "best_hits": max(hits) if hits else 0,
        "worst_hits": min(hits) if hits else 0,
        "games": [
            {
                "numbers": list(game["numbers"]),
                "hits": int(game["hits"]),
                "final_score": _final_score(game),
                **({"score_ml": float(game["score_ml"])} if "score_ml" in game else {}),
            }
            for game in games
        ],
    }


def _final_score(game: Mapping[str, object]) -> float:
    value = game.get("final_score")
    if isinstance(value, Mapping):
        return float(value.get("final_score", 0.0))
    return float(value or 0.0)


def _training_rows_for_split(
    draws: Sequence[Draw],
    split: TemporalSplit,
    *,
    games_count: int,
    pool_size: int,
    history_window: int | None,
    seed: int,
    max_training_contests: int,
) -> list[dict[str, object]]:
    train_targets = _contests_in_range(draws, split.train_start, split.train_end)
    if max_training_contests < 1:
        raise ValueError("max_training_contests must be positive")
    train_targets = train_targets[-max_training_contests:]
    rows: list[dict[str, object]] = []
    for target_row in _target_rows(
        draws,
        train_targets,
        games_count=games_count,
        pool_size=pool_size,
        history_window=history_window,
        seed=seed,
    ):
        for index, game in enumerate(target_row["benchmark"]["games"]):  # type: ignore[index]
            row = {
                "sample_id": f"{split.split_id}_train_{target_row['contest']}_{index:03d}",
                "feature_cutoff_contest": int(target_row["feature_cutoff_contest"]),
                "label_contest": int(target_row["contest"]),
                "scoring_contest": int(target_row["contest"]),
                "features": extract_score_ml_features(game),  # type: ignore[arg-type]
                "target_hits": int(game["hits"]),  # type: ignore[index]
            }
            rows.append(row)
    validate_score_ml_rows(rows).assert_valid()
    return rows


def _execute_split(
    draws: Sequence[Draw],
    split: TemporalSplit,
    *,
    games_count: int,
    pool_size: int,
    history_window: int | None,
    seed: int,
    max_training_contests: int,
) -> dict[str, object]:
    train_rows = _training_rows_for_split(
        draws,
        split,
        games_count=games_count,
        pool_size=pool_size,
        history_window=history_window,
        seed=seed,
        max_training_contests=max_training_contests,
    )
    model = calibrate_linear_score_ml(train_rows)
    test_targets = _contests_in_range(draws, split.test_start, split.test_end)
    contest_rows: list[dict[str, object]] = []

    for target in test_targets:
        history = _history_for_target(list(draws), target, history_window)
        if not history:
            continue
        base_seed = seed + target.contest
        pool = _generate_filtered_candidates(pool_size, Random(base_seed))
        scored_pool = _score_lotoia_games(pool, target, history)

        statistical_selected = sorted(scored_pool, key=_hybrid_sort_key)[:games_count]
        ml_selected = supervised_rerank_games([dict(game) for game in scored_pool], model=model)[:games_count]
        statistical_with_hits = _apply_hits([dict(game) for game in statistical_selected], target)
        ml_with_hits = _apply_hits([dict(game) for game in ml_selected], target)

        benchmark_average = mean([int(game["hits"]) for game in statistical_with_hits])
        ml_average = mean([int(game["hits"]) for game in ml_with_hits])
        contest_rows.append(
            {
                "contest": target.contest,
                "feature_cutoff_contest": history[-1].contest,
                "benchmark": _selection_summary(statistical_with_hits),
                "score_ml_rerank": _selection_summary(ml_with_hits),
                "delta_average_hits": ml_average - benchmark_average,
            }
        )

    benchmark_values = [float(row["benchmark"]["average_hits"]) for row in contest_rows]  # type: ignore[index]
    ml_values = [float(row["score_ml_rerank"]["average_hits"]) for row in contest_rows]  # type: ignore[index]
    return {
        "split": split.as_dict(),
        "training": {
            "rows": len(train_rows),
            "max_training_contests": max_training_contests,
            "feature_cutoff_max": split.train_end,
            "model_version": SCORE_ML_MODEL_VERSION,
            "feature_schema_version": SCORE_ML_FEATURE_SCHEMA_VERSION,
            "training_summary": dict(model.training_summary or {}),
        },
        "test": {
            "contests": [row["contest"] for row in contest_rows],
            "contest_count": len(contest_rows),
            "benchmark_average_hits": mean(benchmark_values) if benchmark_values else 0.0,
            "score_ml_average_hits": mean(ml_values) if ml_values else 0.0,
            "average_hit_delta": (mean(ml_values) - mean(benchmark_values)) if benchmark_values else 0.0,
            "contest_results": contest_rows,
        },
    }


def _write_csv_report(path: Path, split_results: Sequence[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "split_id",
                "contest",
                "benchmark_average_hits",
                "score_ml_average_hits",
                "delta_average_hits",
            ],
        )
        writer.writeheader()
        for split_result in split_results:
            split = split_result["split"]
            test = split_result["test"]
            for row in test["contest_results"]:  # type: ignore[index]
                writer.writerow(
                    {
                        "split_id": split["split_id"],  # type: ignore[index]
                        "contest": row["contest"],
                        "benchmark_average_hits": row["benchmark"]["average_hits"],
                        "score_ml_average_hits": row["score_ml_rerank"]["average_hits"],
                        "delta_average_hits": row["delta_average_hits"],
                    }
                )


def _update_registries(
    *,
    manifest_path: Path,
    report_path: Path,
    reproducibility_hash: str,
    executed_at: str,
) -> None:
    run_entry = {
        "experiment_id": DEFAULT_EXPERIMENT_ID,
        "status": "executed_walk_forward_validation",
        "manifest_path": str(manifest_path).replace("\\", "/"),
        "report_path": str(report_path).replace("\\", "/"),
        "executed_at": executed_at,
        "reproducibility_hash": reproducibility_hash,
    }
    for registry_path in (
        Path("experiments/supervised_scoring/registry.json"),
        Path("experiments/temporal_benchmark/registry.json"),
    ):
        registry = _read_json(registry_path)
        runs = [run for run in registry.get("executed_runs", []) if isinstance(run, Mapping)]
        runs = [run for run in runs if run.get("experiment_id") != DEFAULT_EXPERIMENT_ID]
        runs.append(run_entry)
        registry["executed_runs"] = runs
        _write_json(registry_path, registry)

    dataset_registry_path = Path("experiments/supervised_dataset/registry.json")
    dataset_registry = _read_json(dataset_registry_path)
    for dataset in dataset_registry.get("datasets", []):
        if isinstance(dataset, dict) and dataset.get("status") == "declared_governance_baseline":
            dataset["status"] = "active_snapshot"
    dataset_registry["executed_runs"] = [
        run
        for run in dataset_registry.get("executed_runs", [])
        if isinstance(run, Mapping) and run.get("experiment_id") != DEFAULT_EXPERIMENT_ID
    ] + [run_entry]
    _write_json(dataset_registry_path, dataset_registry)


def run_score_ml_walk_forward(
    *,
    draws: Sequence[Draw] | None = None,
    dataset_version: str = DEFAULT_DATASET_VERSION,
    source_path: str | Path = DEFAULT_HISTORY_PATH,
    min_train_size: int = 2000,
    test_size: int = 10,
    step_size: int = 10,
    games_count: int = 10,
    pool_size: int = 30,
    history_window: int | None = 200,
    max_training_contests: int = 50,
    seed: int = 42,
    experiment_dir: Path = DEFAULT_EXPERIMENT_DIR,
    report_dir: Path = DEFAULT_REPORT_DIR,
    update_registries: bool = True,
) -> WalkForwardExecutionResult:
    ordered_draws = sorted(draws or load_draws_csv(source_path), key=lambda draw: draw.contest)
    validate_temporal_integrity([draw.contest for draw in ordered_draws]).assert_valid()
    splits = build_walk_forward_splits(
        [draw.contest for draw in ordered_draws],
        min_train_size=min_train_size,
        test_size=test_size,
        step_size=step_size,
    )
    for split in splits:
        validate_train_test_separation(split).assert_valid()

    split_results = [
        _execute_split(
            ordered_draws,
            split,
            games_count=games_count,
            pool_size=pool_size,
            history_window=history_window,
            seed=seed,
            max_training_contests=max_training_contests,
        )
        for split in splits
    ]
    benchmark_values = [float(result["test"]["benchmark_average_hits"]) for result in split_results]  # type: ignore[index]
    ml_values = [float(result["test"]["score_ml_average_hits"]) for result in split_results]  # type: ignore[index]
    scientific_delta = {
        "benchmark_average_hits": mean(benchmark_values) if benchmark_values else 0.0,
        "score_ml_average_hits": mean(ml_values) if ml_values else 0.0,
        "average_hit_delta": (mean(ml_values) - mean(benchmark_values)) if benchmark_values else 0.0,
        "interpretation": "score_ml is evaluated only as an auxiliary rerank over the same candidate pools and temporal windows.",
    }
    dataset_snapshot = build_dataset_snapshot(
        ordered_draws,
        dataset_version=dataset_version,
        source_path=str(source_path).replace("\\", "/"),
    ).as_dict()
    executed_at = _now()
    report_payload: dict[str, object] = {
        "experiment_id": DEFAULT_EXPERIMENT_ID,
        "executed_at": executed_at,
        "dataset_snapshot": dataset_snapshot,
        "configuration": {
            "min_train_size": min_train_size,
            "test_size": test_size,
            "step_size": step_size,
            "games_count": games_count,
            "pool_size": pool_size,
            "history_window": history_window,
            "max_training_contests": max_training_contests,
            "seed": seed,
        },
        "scientific_delta": scientific_delta,
        "split_results": split_results,
        "governance": {
            "no_temporal_leakage": True,
            "benchmark_mandatory": True,
            "ml_role": "auxiliary_incremental_rerank",
            "statistical_benchmark_replaced": False,
        },
    }
    reproducibility_hash = _payload_hash(
        {
            "dataset_snapshot": dataset_snapshot,
            "configuration": report_payload["configuration"],
            "scientific_delta": scientific_delta,
            "split_results": split_results,
        }
    )
    report_payload["reproducibility_hash"] = reproducibility_hash

    report_path = report_dir / "walk_forward_result.json"
    csv_path = report_dir / "walk_forward_contests.csv"
    manifest_path = experiment_dir / "manifest.json"
    _write_json(report_path, report_payload)
    _write_csv_report(csv_path, split_results)
    manifest_payload: dict[str, object] = {
        "experiment_id": DEFAULT_EXPERIMENT_ID,
        "status": "executed_walk_forward_validation",
        "created_at": executed_at,
        "dataset_version": dataset_version,
        "dataset_snapshot": dataset_snapshot,
        "score_ml_manifest": "experiments/supervised_scoring/score_ml_manifest_v0_1_0.json",
        "benchmark_reference": "experiments/temporal_benchmark/manifests/temporal_baseline_v0_1_0.json",
        "report_path": str(report_path).replace("\\", "/"),
        "csv_path": str(csv_path).replace("\\", "/"),
        "walk_forward": {
            "type": "expanding_window",
            "split_count": len(splits),
            "splits": [split.as_dict() for split in splits],
        },
        "reproducibility": {
            "random_seed_policy": f"fixed_seed_{seed}_plus_contest_id",
            "model_version": SCORE_ML_MODEL_VERSION,
            "feature_schema_version": SCORE_ML_FEATURE_SCHEMA_VERSION,
            "reproducibility_hash": reproducibility_hash,
        },
        "scientific_delta": scientific_delta,
        "prohibitions": {
            "temporal_leakage": True,
            "benchmark_replacement": True,
            "opaque_modeling": True,
        },
    }
    _write_json(manifest_path, manifest_payload)
    if update_registries:
        _update_registries(
            manifest_path=manifest_path,
            report_path=report_path,
            reproducibility_hash=reproducibility_hash,
            executed_at=executed_at,
        )

    return WalkForwardExecutionResult(
        experiment_id=DEFAULT_EXPERIMENT_ID,
        manifest_path=str(manifest_path),
        report_path=str(report_path),
        split_count=len(splits),
        benchmark_average_hits=float(scientific_delta["benchmark_average_hits"]),
        score_ml_average_hits=float(scientific_delta["score_ml_average_hits"]),
        average_hit_delta=float(scientific_delta["average_hit_delta"]),
        reproducibility_hash=reproducibility_hash,
    )
