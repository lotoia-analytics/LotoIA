from __future__ import annotations

import csv
import json
import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable

from lotoia.data.loader import load_draws_csv
from lotoia.benchmark.benchmark_engine import (
    _apply_hits,
    _compose_profiled_games,
    _generate_filtered_candidates,
    _history_for_target,
    _score_lotoia_games,
    _select_targets,
)
from lotoia.experiments.temporal_governance import validate_temporal_integrity, validate_train_test_separation
from lotoia.experiments.temporal_governance import build_walk_forward_splits
from lotoia.models.draw import Draw

HB_GEOMETRY_AUDIT_VERSION = "0.1.0"
HB_GEOMETRY_ENGINE_VERSION = "hb_geometry_audit_v1"
DEFAULT_HB_GEOMETRY_DIR = Path("reports/hb_geometry")
DEFAULT_HB_GEOMETRY_PROGRESS_FILE = "hb_geometry_audit.progress.json"


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


@dataclass(frozen=True)
class HBGeometryScenarioResult:
    scenario: str
    contest: int
    batch_id: int
    average_hits: float
    hits_11_plus: int
    hits_12_plus: int
    best_hits: int
    average_overlap: float
    entropy: float
    stability_sd: float
    unique_ratio_real: float
    dominant_numbers: list[dict[str, Any]]
    trace_snapshot: dict[str, Any] | None = None
    cluster_dispersion: float | None = None
    distance_mean: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "contest": self.contest,
            "batch_id": self.batch_id,
            "average_hits": self.average_hits,
            "hits_11_plus": self.hits_11_plus,
            "hits_12_plus": self.hits_12_plus,
            "best_hits": self.best_hits,
            "average_overlap": self.average_overlap,
            "entropy": self.entropy,
            "stability_sd": self.stability_sd,
            "unique_ratio_real": self.unique_ratio_real,
            "dominant_numbers": self.dominant_numbers,
            "cluster_dispersion": self.cluster_dispersion,
            "distance_mean": self.distance_mean,
            "trace_snapshot": self.trace_snapshot,
        }


@dataclass(frozen=True)
class HBGeometryAuditResult:
    benchmark_version: str
    geometry_version: str
    created_at: str
    seed: int
    contests_analyzed: int
    games_count: int
    pool_size: int
    history_window: int | None
    batch_size: int
    lightweight: bool
    completed: bool
    processed_batches: int
    scenarios: list[dict[str, Any]]
    summary: dict[str, Any]
    report_paths: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_version": self.benchmark_version,
            "geometry_version": self.geometry_version,
            "created_at": self.created_at,
            "seed": self.seed,
            "contests_analyzed": self.contests_analyzed,
            "games_count": self.games_count,
            "pool_size": self.pool_size,
            "history_window": self.history_window,
            "batch_size": self.batch_size,
            "lightweight": self.lightweight,
            "completed": self.completed,
            "processed_batches": self.processed_batches,
            "scenarios": self.scenarios,
            "summary": self.summary,
            "report_paths": self.report_paths,
        }


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _elapsed_seconds(started_at: str) -> float:
    try:
        started = datetime.fromisoformat(started_at)
    except ValueError:
        return 0.0
    return max(0.0, (datetime.now(UTC) - started).total_seconds())


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _safe_sd(values: Iterable[float]) -> float:
    values = list(values)
    if len(values) < 2:
        return 0.0
    mean = _mean(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return variance ** 0.5


def _numbers_overlap_mean(games: list[dict[str, Any]]) -> float:
    if len(games) < 2:
        return 0.0
    overlaps: list[float] = []
    for index, first in enumerate(games):
        first_numbers = set(first.get("numbers", []))
        for second in games[index + 1 :]:
            second_numbers = set(second.get("numbers", []))
            overlaps.append(len(first_numbers.intersection(second_numbers)) / 15.0)
    return round(_mean(overlaps), 4)


def _numbers_entropy(games: list[dict[str, Any]]) -> float:
    if not games:
        return 0.0
    signatures = [tuple(int(number) for number in game.get("numbers", [])) for game in games]
    counts: dict[tuple[int, ...], int] = {}
    for signature in signatures:
        counts[signature] = counts.get(signature, 0) + 1
    entropy = 0.0
    for count in counts.values():
        share = count / len(signatures)
        if share:
            entropy -= share * __import__("math").log2(share)
    max_entropy = __import__("math").log2(len(counts)) if len(counts) > 1 else 1.0
    return round((entropy / max_entropy) if max_entropy else 0.0, 4)


def _dominant_numbers(games: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[int, int] = {}
    for game in games:
        for number in game.get("numbers", []):
            counts[int(number)] = counts.get(int(number), 0) + 1
    return [
        {"number": number, "frequency": count}
        for number, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:10]
    ]


def _cluster_dispersion(games: list[dict[str, Any]]) -> float:
    if not games:
        return 0.0
    clusters = {((int(number) - 1) // 5) for game in games for number in game.get("numbers", [])}
    return round(len(clusters) / 5.0, 4)


def _distance_mean(games: list[dict[str, Any]]) -> float:
    if len(games) < 2:
        return 0.0
    distances: list[float] = []
    for index, first in enumerate(games):
        first_numbers = set(first.get("numbers", []))
        for second in games[index + 1 :]:
            second_numbers = set(second.get("numbers", []))
            distances.append(len(first_numbers.symmetric_difference(second_numbers)) / 30.0)
    return round(_mean(distances), 4)


def _dominant_numbers_signature(dominant_numbers: list[dict[str, Any]]) -> str:
    if not dominant_numbers:
        return ""
    return sha256(
        json.dumps(dominant_numbers, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:12]


def _copy_scored_game(game: dict[str, Any]) -> dict[str, Any]:
    copied = dict(game)
    if isinstance(copied.get("final_score"), dict):
        copied["final_score"] = dict(copied["final_score"])
    if isinstance(copied.get("quadra_score"), dict):
        copied["quadra_score"] = dict(copied["quadra_score"])
    return copied


def _history_hot_numbers(history: list[Draw], limit: int = 12) -> list[int]:
    counts: dict[int, int] = {number: 0 for number in range(1, 26)}
    for draw in history[-30:]:
        for number in draw.numbers:
            counts[int(number)] += 1
    return [number for number, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def _scenario_adjust_scored_pool(
    scored_pool: list[dict[str, Any]],
    *,
    scenario_name: str,
    target: Draw,
    history: list[Draw],
) -> list[dict[str, Any]]:
    hot_numbers = set(_history_hot_numbers(history))
    last_numbers = set(history[-1].numbers) if history else set()
    target_numbers = set(target.numbers)
    adjusted: list[dict[str, Any]] = []
    for game in scored_pool:
        item = _copy_scored_game(game)
        numbers = set(int(number) for number in item.get("numbers", []))
        profile_score = float(item.get("profile_score", 0.0) or 0.0)
        final_score = item.get("final_score", {})
        if isinstance(final_score, dict):
            final_value = float(final_score.get("final_score", 0.0) or 0.0)
        else:
            final_value = float(final_score or 0.0)
            final_score = {"final_score": final_value}
        quadra_score = item.get("quadra_score", {})
        if not isinstance(quadra_score, dict):
            quadra_score = {}
        found_quadras = float(quadra_score.get("found_quadras", 0) or 0)
        average_rank = float(quadra_score.get("average_rank", 0.0) or 0.0)
        hot_overlap = len(numbers.intersection(hot_numbers)) / max(1, len(numbers))
        recent_overlap = len(numbers.intersection(last_numbers)) / max(1, len(numbers))
        target_overlap = len(numbers.intersection(target_numbers)) / max(1, len(numbers))
        novelty = len(numbers.symmetric_difference(target_numbers)) / 30.0
        jitter_seed = int(sha256("".join(map(str, item.get("numbers", []))).encode("utf-8")).hexdigest()[:8], 16)
        jitter = ((jitter_seed % 1000) / 1000.0) * 0.02

        if scenario_name == "hb_reduced_hot":
            profile_score = profile_score - (hot_overlap * 8.0) - (recent_overlap * 2.0)
            final_value = final_value - (hot_overlap * 10.0)
        elif scenario_name == "hb_flexible_bounds":
            profile_score = profile_score - (recent_overlap * 3.0) - (target_overlap * 1.5) + (novelty * 1.5)
            final_value = final_value - (recent_overlap * 4.0) + (novelty * 1.5)
        elif scenario_name == "hb_exploration_active":
            profile_score = profile_score - (hot_overlap * 4.0) - (target_overlap * 1.5) + (novelty * 3.0) + jitter
            final_value = final_value - (hot_overlap * 4.5) + (novelty * 2.5) + jitter
        elif scenario_name == "hb_less_conservative_rerank":
            profile_score = profile_score * 0.72 + final_value * 0.18 + (found_quadras * 0.12) - (average_rank * 0.05)
            final_value = final_value * 0.82 + (found_quadras * 0.22) - (average_rank * 0.04)
        else:
            profile_score = profile_score
            final_value = final_value

        item["profile_score"] = round(profile_score, 6)
        final_score["final_score"] = round(final_value, 6)
        item["final_score"] = final_score
        adjusted.append(item)
    return adjusted


def _summarize_games(games: list[dict[str, Any]], *, lightweight: bool = True) -> dict[str, Any]:
    hits = [int(game.get("hits", 0)) for game in games]
    numbers = [tuple(int(number) for number in game.get("numbers", [])) for game in games]
    unique_ratio = round(len(set(numbers)) / max(1, len(numbers)), 4) if numbers else 0.0
    summary = {
        "average_hits": round(_mean(hits), 4),
        "hits_11_plus": sum(1 for hit in hits if hit >= 11),
        "hits_12_plus": sum(1 for hit in hits if hit >= 12),
        "best_hits": max(hits) if hits else 0,
        "average_overlap": _numbers_overlap_mean(games),
        "entropy": _numbers_entropy(games),
        "stability_sd": round(_safe_sd(hits), 4),
        "unique_ratio_real": unique_ratio,
        "dominant_numbers": _dominant_numbers(games),
    }
    if not lightweight:
        summary["cluster_dispersion"] = _cluster_dispersion(games)
        summary["distance_mean"] = _distance_mean(games)
    return summary


def _run_hb_variant(
    *,
    count: int,
    scenario_name: str,
    scored_pool: list[dict[str, Any]],
    target: Draw | None = None,
    history: list[Draw] | None = None,
    lightweight: bool = True,
) -> dict[str, Any]:
    if target is None or history is None:
        raise ValueError("target and history are required for incremental HB geometry runs")
    adjusted_pool = _scenario_adjust_scored_pool(scored_pool, scenario_name=scenario_name, target=target, history=history)
    selected = _compose_profiled_games(adjusted_pool, count)
    selected = _apply_hits([dict(game) for game in selected], target)
    summary = _summarize_games(selected, lightweight=lightweight)
    return {
        "summary": summary,
        "trace_snapshot": None if lightweight else {},
    }


def _default_variants() -> list[tuple[str, dict[str, Any]]]:
    return [
        ("hb_baseline", dict(pressure_level="hard", filters_disabled=False, normalization_disabled=False)),
        ("hb_reduced_hot", dict(pressure_level="medium", filters_disabled=False, normalization_disabled=False)),
        ("hb_flexible_bounds", dict(pressure_level="soft", filters_disabled=False, normalization_disabled=False)),
        ("hb_exploration_active", dict(pressure_level="soft", filters_disabled=True, normalization_disabled=False)),
        ("hb_less_conservative_rerank", dict(pressure_level="medium", filters_disabled=False, normalization_disabled=True)),
    ]


def _scenario_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "average_hits": 0.0,
            "hits_11_plus": 0,
            "hits_12_plus": 0,
            "best_hits": 0,
            "average_overlap": 0.0,
            "entropy": 0.0,
            "stability_sd": 0.0,
            "unique_ratio_real": 0.0,
            "dominant_numbers": [],
        }

    dominant_counts: dict[int, int] = {}
    for row in rows:
        for item in row.get("dominant_numbers", []):
            number = int(item["number"])
            dominant_counts[number] = dominant_counts.get(number, 0) + int(item["frequency"])

    dominant_numbers = [
        {"number": number, "frequency": frequency}
        for number, frequency in sorted(dominant_counts.items(), key=lambda item: (-item[1], item[0]))[:10]
    ]
    return {
        "average_hits": round(_mean([float(row["average_hits"]) for row in rows]), 4),
        "hits_11_plus": int(sum(int(row["hits_11_plus"]) for row in rows)),
        "hits_12_plus": int(sum(int(row["hits_12_plus"]) for row in rows)),
        "best_hits": max(int(row["best_hits"]) for row in rows),
        "average_overlap": round(_mean([float(row["average_overlap"]) for row in rows]), 4),
        "entropy": round(_mean([float(row["entropy"]) for row in rows]), 4),
        "stability_sd": round(_mean([float(row["stability_sd"]) for row in rows]), 4),
        "unique_ratio_real": round(_mean([float(row["unique_ratio_real"]) for row in rows]), 4),
        "dominant_numbers": dominant_numbers,
    }


def _progress_signature(config: dict[str, Any]) -> str:
    return sha256(
        json.dumps(config, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _load_progress(progress_path: Path, expected_signature: str) -> dict[str, Any] | None:
    if not progress_path.exists():
        return None
    try:
        payload = json.loads(progress_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if payload.get("progress_signature") != expected_signature:
        return None
    if payload.get("completed") is True:
        return None
    return payload


def _write_progress(progress_path: Path, payload: dict[str, Any]) -> None:
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_partial_csv(csv_path: Path, rows: list[dict[str, Any]]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "batch_id",
                "scenario",
                "contest",
                "average_hits",
                "hits_11_plus",
                "hits_12_plus",
                "best_hits",
                "average_overlap",
                "entropy",
                "stability_sd",
                "unique_ratio_real",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in writer.fieldnames})


def run_hb_geometry_audit(
    *,
    seeds: Iterable[int] | None = None,
    contests_analyzed: int = 30,
    games_count: int = 5,
    pool_size: int = 18,
    history_window: int | None = 200,
    batch_size: int = 5,
    lightweight: bool = True,
    resume: bool = True,
    max_batches_per_run: int | None = 1,
    output_dir: Path = DEFAULT_HB_GEOMETRY_DIR,
) -> HBGeometryAuditResult:
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    seed_list = list(seeds or [7])
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "hb_geometry_audit.json"
    csv_path = output_dir / "hb_geometry_audit.csv"
    progress_path = output_dir / DEFAULT_HB_GEOMETRY_PROGRESS_FILE

    ordered_draws = sorted(load_draws_csv(), key=lambda draw: draw.contest)
    validate_temporal_integrity([draw.contest for draw in ordered_draws]).assert_valid()
    target_draws = _select_targets(ordered_draws, contests_analyzed)
    for split in build_walk_forward_splits(
        [draw.contest for draw in ordered_draws],
        min_train_size=max(1, history_window or 1),
        test_size=1,
        step_size=1,
    ):
        validate_train_test_separation(split).assert_valid()

    scenario_variants = _default_variants()
    config = {
        "benchmark_version": HB_GEOMETRY_AUDIT_VERSION,
        "geometry_version": HB_GEOMETRY_ENGINE_VERSION,
        "seed": seed_list[0] if seed_list else 0,
        "contests_analyzed": [draw.contest for draw in target_draws],
        "games_count": games_count,
        "pool_size": pool_size,
        "history_window": history_window,
        "batch_size": batch_size,
        "lightweight": lightweight,
        "max_batches_per_run": max_batches_per_run,
        "seed_list": seed_list,
    }
    progress_signature = _progress_signature(config)
    progress_state = _load_progress(progress_path, progress_signature) if resume else None
    processed_contests = set(progress_state.get("processed_contests", [])) if progress_state else set()
    scenario_rows = list(progress_state.get("rows", [])) if progress_state else []
    current_batch = int(progress_state.get("current_batch", 0)) + 1 if progress_state else 1
    created_at = progress_state.get("created_at", _now()) if progress_state else _now()

    targets_to_process = [draw for draw in target_draws if draw.contest not in processed_contests]
    processed_batches_this_run = 0
    for batch_index, batch_start in enumerate(range(0, len(targets_to_process), batch_size), start=current_batch):
        batch_draws = targets_to_process[batch_start : batch_start + batch_size]
        if not batch_draws:
            continue
        batch_rows: list[dict[str, Any]] = []
        for target in batch_draws:
            history = _history_for_target(ordered_draws, target, history_window)
            if not history:
                continue
            base_seed = (seed_list[0] if seed_list else 0) + int(target.contest)
            base_pool = _generate_filtered_candidates(pool_size, __import__("random").Random(base_seed), history)
            scored_pool = _score_lotoia_games(base_pool, target, history)
            for scenario_name, _settings in scenario_variants:
                scenario_result = _run_hb_variant(
                    count=games_count,
                    scenario_name=scenario_name,
                    scored_pool=scored_pool,
                    target=target,
                    history=history,
                    lightweight=lightweight,
                )
                summary = scenario_result["summary"]
                row = {
                    "batch_id": batch_index,
                    "scenario": scenario_name,
                    "contest": target.contest,
                    "average_hits": float(summary["average_hits"]),
                    "hits_11_plus": int(summary["hits_11_plus"]),
                    "hits_12_plus": int(summary["hits_12_plus"]),
                    "best_hits": int(summary["best_hits"]),
                    "average_overlap": float(summary["average_overlap"]),
                    "entropy": float(summary["entropy"]),
                    "stability_sd": float(summary["stability_sd"]),
                    "unique_ratio_real": float(summary["unique_ratio_real"]),
                    "dominant_numbers": list(summary["dominant_numbers"]),
                    "trace_snapshot": scenario_result.get("trace_snapshot"),
                }
                if not lightweight:
                    row["cluster_dispersion"] = float(summary.get("cluster_dispersion", 0.0))
                    row["distance_mean"] = float(summary.get("distance_mean", 0.0))
                batch_rows.append(row)
        scenario_rows.extend(batch_rows)
        processed_contests.update(draw.contest for draw in batch_draws)
        _write_partial_csv(csv_path, scenario_rows)
        progress_payload = {
            "benchmark_version": HB_GEOMETRY_AUDIT_VERSION,
            "geometry_version": HB_GEOMETRY_ENGINE_VERSION,
            "created_at": created_at,
            "updated_at": _now(),
            "elapsed_seconds": round(_elapsed_seconds(created_at), 2),
            "progress_signature": progress_signature,
            "current_batch": batch_index,
            "batch_size": batch_size,
            "lightweight": lightweight,
            "seed": seed_list[0] if seed_list else 0,
            "contests_analyzed": [draw.contest for draw in target_draws],
            "processed_contests": sorted(processed_contests),
            "current_scenario": batch_rows[-1]["scenario"] if batch_rows else "",
            "last_contest": batch_draws[-1].contest if batch_draws else None,
            "processed_batches": processed_batches_this_run,
            "rows": scenario_rows,
            "summary": {item: _scenario_summary([row for row in scenario_rows if row["scenario"] == item]) for item, _ in scenario_variants},
        }
        _write_progress(progress_path, progress_payload)
        processed_batches_this_run += 1
        if max_batches_per_run is not None and processed_batches_this_run >= max_batches_per_run:
            break

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in scenario_rows:
        grouped.setdefault(str(row["scenario"]), []).append(row)

    summary = {scenario_name: _scenario_summary(rows) for scenario_name, rows in grouped.items()}
    completed = len(processed_contests) >= len(target_draws)
    payload = {
        "benchmark_version": HB_GEOMETRY_AUDIT_VERSION,
        "geometry_version": HB_GEOMETRY_ENGINE_VERSION,
        "created_at": created_at,
        "updated_at": _now(),
        "seed": seed_list[0] if seed_list else 0,
        "contests_analyzed": [draw.contest for draw in target_draws],
        "games_count": games_count,
        "pool_size": pool_size,
        "history_window": history_window,
        "batch_size": batch_size,
        "lightweight": lightweight,
        "elapsed_seconds": round(_elapsed_seconds(created_at), 2),
        "current_scenario": scenario_rows[-1]["scenario"] if scenario_rows else "",
        "last_contest": scenario_rows[-1]["contest"] if scenario_rows else None,
        "completed": completed,
        "processed_batches": processed_batches_this_run,
        "summary": summary,
        "scenarios": scenario_rows,
        "progress_path": str(progress_path.resolve()),
        "recovered_from_checkpoint": progress_state is not None,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_partial_csv(csv_path, scenario_rows)
    _write_progress(progress_path, {**payload, "completed": completed, "progress_signature": progress_signature})

    return HBGeometryAuditResult(
        benchmark_version=HB_GEOMETRY_AUDIT_VERSION,
        geometry_version=HB_GEOMETRY_ENGINE_VERSION,
        created_at=payload["created_at"],
        seed=seed_list[0] if seed_list else 0,
        contests_analyzed=len(processed_contests),
        games_count=games_count,
        pool_size=pool_size,
        history_window=history_window,
        batch_size=batch_size,
        lightweight=lightweight,
        completed=completed,
        processed_batches=processed_batches_this_run,
        scenarios=scenario_rows,
        summary=summary,
        report_paths={
            "json": str(json_path.resolve()),
            "csv": str(csv_path.resolve()),
            "progress": str(progress_path.resolve()),
        },
    )
