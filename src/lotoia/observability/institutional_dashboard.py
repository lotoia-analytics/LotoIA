from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean
from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH

from .observability_repository import ObservabilityRepository


@dataclass(frozen=True, slots=True)
class InstitutionalObservabilityDashboard:
    """Executive observability summary built from persisted runtime evidence."""

    created_at: datetime
    source: str
    summary: dict[str, Any]
    runtime_health: dict[str, Any]
    execution_graph: list[dict[str, Any]]
    lineage_timeline: list[dict[str, Any]]
    snapshots: list[dict[str, Any]]
    metrics: list[dict[str, Any]]
    drift_evolution: list[dict[str, Any]]
    confidence_stability: list[dict[str, Any]]
    structural_integrity: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at.isoformat(),
            "source": self.source,
            "summary": self.summary,
            "runtime_health": self.runtime_health,
            "execution_graph": self.execution_graph,
            "lineage_timeline": self.lineage_timeline,
            "snapshots": self.snapshots,
            "metrics": self.metrics,
            "drift_evolution": self.drift_evolution,
            "confidence_stability": self.confidence_stability,
            "structural_integrity": self.structural_integrity,
            "metadata": self.metadata,
        }


def build_institutional_observability_dashboard(
    db_path: Path = DEFAULT_DATABASE_PATH,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    repository = ObservabilityRepository(db_path)
    executions = repository.list_executions(limit=limit)
    spans = repository.list_spans(limit=limit)
    metrics = repository.list_metrics(limit=limit)
    lineage = repository.list_lineage(limit=limit)
    snapshots = repository.list_snapshots(limit=limit)
    latest_execution = executions[0] if executions else {}

    runtime_health = _runtime_health(executions, spans, metrics, lineage, snapshots)
    drift_evolution = _metric_evolution(metrics, "confidence_drift")
    confidence_stability = _metric_evolution(metrics, "confidence_stability")
    structural_integrity = {
        "ok": runtime_health["failed_executions"] == 0 and runtime_health["failed_spans"] == 0,
        "failed_executions": runtime_health["failed_executions"],
        "failed_spans": runtime_health["failed_spans"],
        "recent_snapshot_count": runtime_health["snapshot_count"],
    }

    return {
        "created_at": datetime.now(UTC).isoformat(),
        "source": str(db_path),
        "summary": {
            "execution_count": runtime_health["execution_count"],
            "running_execution_count": runtime_health["running_execution_count"],
            "completed_execution_count": runtime_health["completed_execution_count"],
            "failed_execution_count": runtime_health["failed_executions"],
            "span_count": runtime_health["span_count"],
            "metric_count": runtime_health["metric_count"],
            "lineage_count": runtime_health["lineage_count"],
            "snapshot_count": runtime_health["snapshot_count"],
            "average_execution_duration_ms": runtime_health["average_execution_duration_ms"],
            "latest_flow": runtime_health["latest_flow"],
            "latest_status": runtime_health["latest_status"],
            "latest_execution_id": latest_execution.get("execution_id", "-"),
        },
        "runtime_health": runtime_health,
        "execution_graph": executions[:limit],
        "lineage_timeline": lineage[:limit],
        "snapshots": snapshots[:limit],
        "metrics": metrics[:limit],
        "drift_evolution": drift_evolution,
        "confidence_stability": confidence_stability,
        "structural_integrity": structural_integrity,
        "metadata": {
            "layer": "institutional_observability_dashboard",
            "execution_graph_ready": bool(executions),
            "lineage_ready": bool(lineage),
            "snapshot_ready": bool(snapshots),
            "metrics_ready": bool(metrics),
        },
    }


def _runtime_health(
    executions: list[dict[str, Any]],
    spans: list[dict[str, Any]],
    metrics: list[dict[str, Any]],
    lineage: list[dict[str, Any]],
    snapshots: list[dict[str, Any]],
) -> dict[str, Any]:
    durations = [float(row["duration_ms"]) for row in executions if row.get("duration_ms") is not None]
    statuses = Counter(str(row.get("status") or "") for row in executions)
    latest_execution = executions[0] if executions else {}
    return {
        "execution_count": len(executions),
        "running_execution_count": statuses.get("running", 0),
        "completed_execution_count": statuses.get("ok", 0) + statuses.get("success", 0),
        "failed_executions": statuses.get("failed", 0),
        "span_count": len(spans),
        "metric_count": len(metrics),
        "lineage_count": len(lineage),
        "snapshot_count": len(snapshots),
        "average_execution_duration_ms": round(fmean(durations), 2) if durations else 0.0,
        "latest_flow": latest_execution.get("flow_name", "-"),
        "latest_status": latest_execution.get("status", "-"),
        "latest_stage": latest_execution.get("stage", "-"),
        "failed_spans": sum(1 for row in spans if str(row.get("status") or "") == "failed"),
    }


def _metric_evolution(metrics: list[dict[str, Any]], metric_name: str) -> list[dict[str, Any]]:
    rows = [row for row in metrics if str(row.get("name") or "") == metric_name]
    rows = sorted(rows, key=lambda row: (row.get("observed_at"), row.get("id", 0)), reverse=True)
    return [
        {
            "observed_at": row.get("observed_at"),
            "value": row.get("value"),
            "labels_json": row.get("labels_json"),
            "metadata_json": row.get("metadata_json"),
        }
        for row in rows
    ]
