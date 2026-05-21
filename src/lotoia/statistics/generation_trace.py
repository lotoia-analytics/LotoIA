from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping
from collections import Counter

from lotoia.statistics.historical_intelligence import (
    cluster_type,
    entropy_score,
    partial_recurrence_metrics,
    recurrence_score,
    structural_rarity_score,
    structural_score,
)


TRACE_ROOT = Path("reports") / "snapshots" / "generation_pipeline"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _game_numbers(game: Mapping[str, Any]) -> list[int]:
    numbers = game.get("numbers", [])
    return [int(number) for number in numbers]


def behavioral_metrics(games: list[Mapping[str, Any]], history: list[Any] | None = None) -> dict[str, float]:
    history = history or []
    if not games:
        return {
            "recurrence_density": 0.0,
            "structural_entropy": 0.0,
            "cluster_aggressiveness": 0.0,
            "sequence_pressure": 0.0,
            "persistence_ratio": 0.0,
            "dispersion_index": 0.0,
            "normalization_pressure": 0.0,
            "rarity_std": 0.0,
        }

    recurrence_scores: list[float] = []
    structural_scores: list[float] = []
    entropy_scores: list[float] = []
    rarity_scores: list[float] = []
    cluster_extremes = 0
    sequence_pressure_values: list[float] = []
    persistence_values: list[float] = []
    dispersion_values: list[float] = []

    for game in games:
        numbers = _game_numbers(game)
        partial = partial_recurrence_metrics(numbers, history) if history else {"partial_match_avg": 0.0}
        recurrence_scores.append(recurrence_score(numbers, history) if history else 0.0)
        structural_scores.append(structural_score(numbers))
        entropy_scores.append(entropy_score(numbers))
        rarity_scores.append(structural_rarity_score(numbers, history))
        if cluster_type(numbers) == "extremo":
            cluster_extremes += 1
        sequence_pressure_values.append(float(game.get("sequence_pressure", partial.get("partial_match_avg", 0.0))))
        persistence_values.append(float(partial.get("partial_match_avg", 0.0)))
        dispersion_values.append(len(set(numbers)) / max(len(numbers), 1))

    mean = lambda values: sum(values) / len(values) if values else 0.0
    variance = lambda values: mean([(value - mean(values)) ** 2 for value in values]) if values else 0.0

    rarity_mean = mean(rarity_scores)
    rarity_std = (variance(rarity_scores)) ** 0.5 if rarity_scores else 0.0
    return {
        "recurrence_density": round(mean(recurrence_scores) / 100, 4),
        "structural_entropy": round(mean(entropy_scores) / 100, 4),
        "cluster_aggressiveness": round(cluster_extremes / len(games), 4),
        "sequence_pressure": round(mean(sequence_pressure_values), 4),
        "persistence_ratio": round(mean(persistence_values) / 15, 4),
        "dispersion_index": round(mean(dispersion_values), 4),
        "normalization_pressure": round(max(0.0, 1.0 - (mean(structural_scores) / 100)), 4),
        "rarity_std": round(rarity_std, 4),
        "rarity_mean": round(rarity_mean, 2),
    }


def stage_snapshot(
    stage: str,
    games: list[Mapping[str, Any]],
    *,
    history: list[Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metrics = behavioral_metrics(games, history=history)
    snapshot = {
        "stage": stage,
        "timestamp": _utc_now(),
        "engine": str((metadata or {}).get("engine_version", "historical_recalibrated_v2")),
        "profile_distribution": dict((metadata or {}).get("profile_distribution", {})),
        "games": len(games),
        "metrics": metrics,
        "games_preview": [
            {
                "numbers": _game_numbers(game),
                "profile_type": str(game.get("profile_type", "")),
                "profile_score": _safe_float(game.get("profile_score", 0.0)),
                "final_score": _safe_float((game.get("final_score") or {}).get("final_score", 0.0)),
                "rarity": _safe_float((game.get("historical_intelligence") or {}).get("structural_rarity", 0.0)),
            }
            for game in games[:10]
        ],
        "metadata": metadata or {},
    }
    return snapshot


def persist_stage_snapshot(snapshot: Mapping[str, Any]) -> Path | None:
    if os.getenv("NORMALIZATION_DISABLED", "").strip().lower() not in {"1", "true", "yes", "on"} and not snapshot.get("stage"):
        return None
    try:
        TRACE_ROOT.mkdir(parents=True, exist_ok=True)
        path = TRACE_ROOT / f"{snapshot.get('stage', 'stage')}_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%f')}.json"
        path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
    except Exception:
        return None


def record_discarded_game(
    stage: str,
    numbers: list[int],
    *,
    reason: str,
    metrics: dict[str, Any] | None = None,
    history: list[Any] | None = None,
    profile_type: str | None = None,
) -> Path | None:
    payload = {
        "stage": stage,
        "timestamp": _utc_now(),
        "discarded_by": stage,
        "reason": reason,
        "numbers": [int(number) for number in numbers],
        "profile_type": profile_type or "",
        "metrics": metrics or {},
        "history_size": len(history or []),
    }
    try:
        TRACE_ROOT.mkdir(parents=True, exist_ok=True)
        path = TRACE_ROOT / f"discarded_{stage}_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%f')}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
    except Exception:
        return None


def load_generation_trace_snapshots() -> list[dict[str, Any]]:
    if not TRACE_ROOT.exists():
        return []
    snapshots: list[dict[str, Any]] = []
    for path in sorted(TRACE_ROOT.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["_path"] = str(path)
            snapshots.append(payload)
        except Exception:
            continue
    return snapshots


def pressure_heatmap() -> list[dict[str, Any]]:
    discarded = Counter()
    reasons = Counter()
    for snapshot in load_generation_trace_snapshots():
        if "discarded_by" in snapshot:
            discarded[str(snapshot.get("discarded_by", ""))] += 1
            reasons[str(snapshot.get("reason", ""))] += 1
    rows = []
    for stage, count in discarded.most_common():
        rows.append(
            {
                "filter": stage,
                "discarded": count,
                "reason": reasons.most_common(1)[0][0] if reasons else "",
            }
        )
    return rows


def survival_summary() -> list[dict[str, Any]]:
    snapshots = load_generation_trace_snapshots()
    stage_rows = [snapshot for snapshot in snapshots if snapshot.get("stage") in {"raw_generation", "post_rerank", "post_normalization_disabled", "final_output"}]
    if not stage_rows:
        return []
    rows: list[dict[str, Any]] = []
    for stage in ("raw_generation", "post_rerank", "post_normalization_disabled", "final_output"):
        stage_snapshots = [snap for snap in stage_rows if snap.get("stage") == stage]
        if not stage_snapshots:
            continue
        latest = stage_snapshots[0]
        profiles = latest.get("profile_distribution") or {}
        total = sum(int(value) for value in profiles.values()) or int(latest.get("games", 0)) or 1
        rows.append(
            {
                "stage": stage,
                "recorrente": int(profiles.get("recorrente", 0)),
                "hibrido": int(profiles.get("hibrido", 0)),
                "caotico": int(profiles.get("caotico", 0)),
                "total": total,
            }
        )
    return rows


def diversity_collapse_report() -> list[dict[str, Any]]:
    snapshots = load_generation_trace_snapshots()
    selected = [snap for snap in snapshots if snap.get("stage") in {"raw_generation", "post_rerank", "post_normalization_disabled", "final_output"}]
    if not selected:
        return []
    selected = sorted(selected, key=lambda item: item.get("_path", ""))
    rows: list[dict[str, Any]] = []
    for snapshot in selected:
        metrics = snapshot.get("metrics") or {}
        rows.append(
            {
                "stage": snapshot.get("stage", ""),
                "diversity_score": round(float(metrics.get("rarity_std", 0.0)) + float(metrics.get("structural_entropy", 0.0)), 4),
                "rarity_std": metrics.get("rarity_std", 0.0),
                "recurrence_density": metrics.get("recurrence_density", 0.0),
                "structural_entropy": metrics.get("structural_entropy", 0.0),
                "normalization_pressure": metrics.get("normalization_pressure", 0.0),
            }
        )
    return rows


def normalization_comparison_report() -> list[dict[str, Any]]:
    snapshots = load_generation_trace_snapshots()
    stages = ("raw_generation", "post_rerank", "post_normalization_disabled", "final_output")
    rows: list[dict[str, Any]] = []
    by_stage: dict[str, dict[str, Any]] = {}
    for snapshot in snapshots:
        stage = str(snapshot.get("stage", ""))
        if stage in stages and stage not in by_stage:
            by_stage[stage] = snapshot
    for stage in stages:
        snapshot = by_stage.get(stage)
        if not snapshot:
            continue
        metrics = snapshot.get("metrics") or {}
        rows.append(
            {
                "mode": "filters_disabled" if stage == "post_normalization_disabled" else "normal",
                "stage": stage,
                "rarity_std": metrics.get("rarity_std", 0.0),
                "recurrence_density": metrics.get("recurrence_density", 0.0),
                "structural_entropy": metrics.get("structural_entropy", 0.0),
                "cluster_aggressiveness": metrics.get("cluster_aggressiveness", 0.0),
                "normalization_pressure": metrics.get("normalization_pressure", 0.0),
            }
        )
    return rows


def pipeline_divergence_score() -> list[dict[str, Any]]:
    comparison = normalization_comparison_report()
    rows: list[dict[str, Any]] = []
    for item in comparison:
        divergence = round(
            float(item.get("normalization_pressure", 0.0)) * 0.45
            + float(item.get("cluster_aggressiveness", 0.0)) * 0.25
            + float(item.get("structural_entropy", 0.0)) * 0.20
            + float(item.get("recurrence_density", 0.0)) * 0.10,
            4,
        )
        rows.append({**item, "divergence_score": divergence})
    return rows


def replay_snapshot(stage: str, *, seed: int | None = None) -> dict[str, Any]:
    snapshots = load_generation_trace_snapshots()
    candidates = [snapshot for snapshot in snapshots if snapshot.get("stage") == stage]
    if seed is not None:
        candidates = [snapshot for snapshot in candidates if int(snapshot.get("metadata", {}).get("seed", -1)) == seed]
    if not candidates:
        return {}
    replay = dict(candidates[0])
    replay["replay_requested"] = True
    replay["replay_seed"] = seed
    return replay


def _stage_metrics_by_mode() -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {"normal": [], "filters_disabled": []}
    for row in normalization_comparison_report():
        grouped.setdefault(str(row.get("mode", "normal")), []).append(row)
    return grouped


def destructive_filters_report() -> list[dict[str, Any]]:
    snapshots = load_generation_trace_snapshots()
    discarded = [snapshot for snapshot in snapshots if "discarded_by" in snapshot]
    if not discarded:
        return []

    by_filter: dict[str, list[dict[str, Any]]] = {}
    for snapshot in discarded:
        by_filter.setdefault(str(snapshot.get("discarded_by", "")), []).append(snapshot)

    comparison = normalization_comparison_report()
    comparison_lookup = {str(row.get("stage", "")): row for row in comparison}
    rows: list[dict[str, Any]] = []

    for filter_name, items in sorted(by_filter.items(), key=lambda item: len(item[1]), reverse=True):
        diversity_collapse = 0.0
        recurrence_kill = 0.0
        chaos_kill = 0.0
        contribution = 0.0
        for item in items:
            metrics = item.get("metrics") or {}
            recurrence_kill += float(metrics.get("recurrence_density", 0.0))
            chaos_kill += float(metrics.get("cluster_aggressiveness", 0.0))
            diversity_collapse += float(metrics.get("normalization_pressure", 0.0))
            contribution += float(metrics.get("divergence_score", 0.0))
        denominator = max(len(items), 1)
        rows.append(
            {
                "filter": filter_name,
                "discarded": len(items),
                "diversity_collapse": round(diversity_collapse / denominator, 4),
                "recurrence_kill": round(recurrence_kill / denominator, 4),
                "chaos_kill": round(chaos_kill / denominator, 4),
                "divergence_contribution": round(contribution / denominator, 4),
                "classification": (
                    "destrutivo"
                    if (diversity_collapse / denominator) >= 0.5 or (contribution / denominator) >= 0.5
                    else "agressivo"
                    if (diversity_collapse / denominator) >= 0.25
                    else "saudavel"
                ),
                "reference_stage": next(iter(comparison_lookup), ""),
            }
        )
    return rows


def executive_behavioral_report() -> list[dict[str, Any]]:
    report = destructive_filters_report()
    if not report:
        return []
    rows: list[dict[str, Any]] = []
    for item in report:
        rows.append(
            {
                "filter": item.get("filter", ""),
                "classification": item.get("classification", ""),
                "impact": (
                    "EXTREMO"
                    if float(item.get("diversity_collapse", 0.0)) >= 0.5 or float(item.get("divergence_contribution", 0.0)) >= 0.5
                    else "ALTO"
                    if float(item.get("diversity_collapse", 0.0)) >= 0.25
                    else "BAIXO"
                ),
                "diversity_collapse": item.get("diversity_collapse", 0.0),
                "recurrence_kill": item.get("recurrence_kill", 0.0),
                "chaos_kill": item.get("chaos_kill", 0.0),
                "divergence_contribution": item.get("divergence_contribution", 0.0),
            }
        )
    return rows


def behavior_recovery_timeline() -> list[dict[str, Any]]:
    comparison = normalization_comparison_report()
    if not comparison:
        return []
    baseline = next((row for row in comparison if row.get("mode") == "normal" and row.get("stage") == "raw_generation"), None)
    if not baseline:
        baseline = comparison[0]
    baseline_diversity = float(baseline.get("rarity_std", 0.0)) + float(baseline.get("structural_entropy", 0.0))
    baseline_recurrence = float(baseline.get("recurrence_density", 0.0))
    baseline_chaos = float(baseline.get("cluster_aggressiveness", 0.0))
    rows: list[dict[str, Any]] = []
    for item in comparison:
        diversity = float(item.get("rarity_std", 0.0)) + float(item.get("structural_entropy", 0.0))
        recurrence = float(item.get("recurrence_density", 0.0))
        chaos = float(item.get("cluster_aggressiveness", 0.0))
        recovery = round(
            max(0.0, (diversity - baseline_diversity)) * 0.45
            + max(0.0, (recurrence - baseline_recurrence)) * 0.30
            + max(0.0, (chaos - baseline_chaos)) * 0.25,
            4,
        )
        rows.append(
            {
                "mode": item.get("mode", ""),
                "stage": item.get("stage", ""),
                "recurrence_recovery": round(max(0.0, recurrence - baseline_recurrence), 4),
                "chaos_recovery": round(max(0.0, chaos - baseline_chaos), 4),
                "variance_recovery": round(max(0.0, diversity - baseline_diversity), 4),
                "recovery_score": recovery,
            }
        )
    return rows


def filter_profile_damage_report() -> list[dict[str, Any]]:
    report = destructive_filters_report()
    if not report:
        return []
    rows: list[dict[str, Any]] = []
    for item in report:
        rows.append(
            {
                "filter": item.get("filter", ""),
                "recorrente": round(float(item.get("recurrence_kill", 0.0)) * 100, 2),
                "hibrido": round(max(0.0, 100 - float(item.get("diversity_collapse", 0.0)) * 100), 2),
                "caotico": round(float(item.get("chaos_kill", 0.0)) * 100, 2),
            }
        )
    return rows


def safe_recovery_zone() -> list[dict[str, Any]]:
    return [
        {
            "metric": "recurrence_recovery",
            "minimum": 0.25,
            "maximum": 0.40,
            "target": 0.32,
        },
        {
            "metric": "chaos_recovery",
            "minimum": 0.10,
            "maximum": 0.25,
            "target": 0.18,
        },
        {
            "metric": "variance_recovery",
            "minimum": 0.30,
            "maximum": 0.55,
            "target": 0.42,
        },
        {
            "metric": "divergence_reduction",
            "minimum": 0.30,
            "maximum": 0.60,
            "target": 0.45,
        },
    ]


def historical_adherence_score() -> list[dict[str, Any]]:
    comparison = normalization_comparison_report()
    if not comparison:
        return []
    rows: list[dict[str, Any]] = []
    for item in comparison:
        adherence = round(
            float(item.get("recurrence_density", 0.0)) * 0.40
            + float(item.get("structural_entropy", 0.0)) * 0.25
            + float(item.get("cluster_aggressiveness", 0.0)) * 0.20
            + float(item.get("rarity_std", 0.0)) * 0.15,
            4,
        )
        rows.append({**item, "historical_adherence_score": adherence})
    return rows


def profile_stability_score() -> list[dict[str, Any]]:
    report = survival_summary()
    if not report:
        return []
    rows: list[dict[str, Any]] = []
    for item in report:
        total = max(int(item.get("total", 1)), 1)
        recurrent = int(item.get("recorrente", 0)) / total
        hybrid = int(item.get("hibrido", 0)) / total
        chaotic = int(item.get("caotico", 0)) / total
        stability = round((hybrid * 0.50) + (recurrent * 0.30) + ((1 - chaotic) * 0.20), 4)
        rows.append({**item, "profile_stability_score": stability})
    return rows


def pressure_sensitivity_report() -> list[dict[str, Any]]:
    report = destructive_filters_report()
    rows: list[dict[str, Any]] = []
    for item in report:
        sensitivity = round(
            float(item.get("diversity_collapse", 0.0)) * 0.50
            + float(item.get("divergence_contribution", 0.0)) * 0.30
            + float(item.get("recurrence_kill", 0.0)) * 0.10
            + float(item.get("chaos_kill", 0.0)) * 0.10,
            4,
        )
        rows.append({**item, "pressure_sensitivity": sensitivity})
    return rows


def recovery_decision_protocol() -> list[dict[str, Any]]:
    return [
        {
            "condition": "recovery up and adherence up",
            "action": "keep",
            "rule": "continue",
        },
        {
            "condition": "recovery up and adherence down strongly",
            "action": "reject",
            "rule": "rollback",
        },
        {
            "condition": "recovery down and adherence up slightly",
            "action": "review",
            "rule": "measure again",
        },
        {
            "condition": "variance up excessively",
            "action": "reduce pressure",
            "rule": "soften filter",
        },
        {
            "condition": "profile instability up",
            "action": "rollback",
            "rule": "restore baseline",
        },
    ]


def behavior_drift_report() -> list[dict[str, Any]]:
    comparison = normalization_comparison_report()
    if not comparison:
        return []
    baseline = next((row for row in comparison if row.get("mode") == "normal" and row.get("stage") == "raw_generation"), comparison[0])
    rows: list[dict[str, Any]] = []
    for item in comparison:
        drift = round(
            abs(float(item.get("recurrence_density", 0.0)) - float(baseline.get("recurrence_density", 0.0))) * 0.35
            + abs(float(item.get("structural_entropy", 0.0)) - float(baseline.get("structural_entropy", 0.0))) * 0.35
            + abs(float(item.get("cluster_aggressiveness", 0.0)) - float(baseline.get("cluster_aggressiveness", 0.0))) * 0.30,
            4,
        )
        rows.append({**item, "behavior_drift_score": drift})
    return rows


def golden_baselines() -> list[dict[str, Any]]:
    return [
        {"baseline": "legacy_hard", "description": "engine antiga"},
        {"baseline": "recalibrated_hard", "description": "nova sem recovery"},
        {"baseline": "recalibrated_medium", "description": "recovery medio"},
        {"baseline": "recalibrated_soft", "description": "recovery alto"},
    ]


def false_recovery_report() -> list[dict[str, Any]]:
    report = historical_adherence_score()
    rows: list[dict[str, Any]] = []
    for item in report:
        variance = float(item.get("structural_entropy", 0.0)) + float(item.get("rarity_std", 0.0))
        recurrence = float(item.get("recurrence_density", 0.0))
        chaos = float(item.get("cluster_aggressiveness", 0.0))
        adherence = float(item.get("historical_adherence_score", 0.0))
        false_recovery = variance > 0.20 and chaos > 0.20 and adherence < 0.30
        rows.append(
            {
                **item,
                "variance": round(variance, 4),
                "false_recovery": false_recovery,
                "recurrence": round(recurrence, 4),
                "chaos": round(chaos, 4),
            }
        )
    return rows


def experiment_baseline_report() -> list[dict[str, Any]]:
    return [
        {
            "baseline": "3b_current",
            "description": "baseline congelado da fase 3B",
            "seed_policy": "replay_required",
            "filter_policy": "one_filter_at_a_time",
        }
    ]


def experiment_comparison_report() -> list[dict[str, Any]]:
    comparison = normalization_comparison_report()
    if not comparison:
        return []
    rows: list[dict[str, Any]] = []
    for item in comparison:
        rows.append(
            {
                "mode": item.get("mode", ""),
                "stage": item.get("stage", ""),
                "recurrence_density": item.get("recurrence_density", 0.0),
                "structural_entropy": item.get("structural_entropy", 0.0),
                "cluster_aggressiveness": item.get("cluster_aggressiveness", 0.0),
                "rarity_std": item.get("rarity_std", 0.0),
                "normalization_pressure": item.get("normalization_pressure", 0.0),
                "behavior_integrity_recovery": round(
                    float(item.get("recurrence_density", 0.0)) * 0.35
                    + float(item.get("structural_entropy", 0.0)) * 0.25
                    + float(item.get("cluster_aggressiveness", 0.0)) * 0.20
                    + float(item.get("rarity_std", 0.0)) * 0.20,
                    4,
                ),
            }
        )
    return rows


def recovery_plateau_detection() -> list[dict[str, Any]]:
    timeline = behavior_recovery_timeline()
    if not timeline:
        return []
    rows: list[dict[str, Any]] = []
    for item in timeline:
        plateau = (
            float(item.get("recurrence_recovery", 0.0)) >= 0.39
            and float(item.get("variance_recovery", 0.0)) <= 0.05
        )
        rows.append({**item, "plateau_detected": plateau})
    return rows


def experiment_01_report() -> list[dict[str, Any]]:
    comparison = experiment_comparison_report()
    if not comparison:
        return []
    rows: list[dict[str, Any]] = []
    for item in comparison:
        rows.append(
            {
                "experiment": "01_normalize_distribution",
                "mode": item.get("mode", ""),
                "stage": item.get("stage", ""),
                "recovery": round(float(item.get("behavior_integrity_recovery", 0.0)), 4),
                "adherence": round(float(item.get("behavior_integrity_recovery", 0.0)) * 0.85 + float(item.get("recurrence_density", 0.0)) * 0.15, 4),
                "drift": round(float(item.get("normalization_pressure", 0.0)) * 0.60, 4),
                "false_recovery": float(item.get("normalization_pressure", 0.0)) > 0.20 and float(item.get("behavior_integrity_recovery", 0.0)) < 0.30,
                "profile_stability": round(float(item.get("cluster_aggressiveness", 0.0)) * 0.5 + float(item.get("rarity_std", 0.0)) * 0.5, 4),
            }
        )
    return rows


def marginal_recovery_gain() -> list[dict[str, Any]]:
    experiment = experiment_01_report()
    if not experiment:
        return []
    hard = next((item for item in experiment if item.get("mode") == "normal" and item.get("stage") == "raw_generation"), experiment[0])
    medium = next((item for item in experiment if item.get("mode") == "normal" and item.get("stage") == "post_rerank"), None)
    soft = next((item for item in experiment if item.get("mode") == "normal" and item.get("stage") == "final_output"), None)
    rows: list[dict[str, Any]] = []
    previous = hard
    for item in (medium, soft):
        if item is None:
            continue
        gain = round(float(item.get("recovery", 0.0)) - float(previous.get("recovery", 0.0)), 4)
        rows.append(
            {
                "from_stage": previous.get("stage", ""),
                "to_stage": item.get("stage", ""),
                "marginal_recovery_gain": gain,
                "adherence_delta": round(float(item.get("adherence", 0.0)) - float(previous.get("adherence", 0.0)), 4),
                "drift_delta": round(float(item.get("drift", 0.0)) - float(previous.get("drift", 0.0)), 4),
            }
        )
        previous = item
    return rows
