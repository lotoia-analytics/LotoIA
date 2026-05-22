from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text

from lotoia.database.database import DEFAULT_DATABASE_PATH, get_session
from lotoia.observability.observability_repository import ObservabilityRepository


def _isoformat(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


@dataclass(frozen=True, slots=True)
class LiveTelemetrySnapshot:
    created_at: datetime
    source: str
    summary: dict[str, Any]
    activity: dict[str, Any]
    live_signals: list[dict[str, Any]]
    runtime_status: dict[str, Any]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at.isoformat(),
            "source": self.source,
            "summary": self.summary,
            "activity": self.activity,
            "live_signals": self.live_signals,
            "runtime_status": self.runtime_status,
            "metadata": self.metadata,
        }


def build_live_telemetry_snapshot(
    db_path: Path = DEFAULT_DATABASE_PATH,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    repository = ObservabilityRepository(db_path)
    executions = repository.list_executions(limit=limit)
    metrics = repository.list_metrics(limit=limit)
    lineage = repository.list_lineage(limit=limit)
    snapshots = repository.list_snapshots(limit=limit)

    with get_session(db_path) as session:
        generation_events = int(session.execute(text("SELECT COUNT(*) FROM generation_events")).scalar() or 0)
        check_events = int(session.execute(text("SELECT COUNT(*) FROM check_events")).scalar() or 0)
        imported_contests = int(session.execute(text("SELECT COUNT(*) FROM imported_contests")).scalar() or 0)
        reconciliation_runs = int(session.execute(text("SELECT COUNT(*) FROM reconciliation_runs")).scalar() or 0)
        reconciliation_games = int(session.execute(text("SELECT COUNT(*) FROM reconciliation_games")).scalar() or 0)
        generated_games = int(session.execute(text("SELECT COUNT(*) FROM generated_games")).scalar() or 0)
        latest_generation = session.execute(
            text("SELECT created_at FROM generation_events ORDER BY created_at DESC, id DESC LIMIT 1")
        ).first()
        latest_check = session.execute(
            text("SELECT created_at FROM check_events ORDER BY created_at DESC, id DESC LIMIT 1")
        ).first()
        latest_sync = session.execute(
            text("SELECT created_at FROM imported_contests ORDER BY created_at DESC, contest_number DESC LIMIT 1")
        ).first()

    runtime_status = {
        "execution_count": len(executions),
        "active_execution_count": sum(1 for row in executions if str(row.get("status") or "") == "running"),
        "recent_snapshot_count": len(snapshots),
        "recent_metric_count": len(metrics),
        "recent_lineage_count": len(lineage),
        "latest_execution_id": executions[0]["execution_id"] if executions else "-",
        "latest_flow": executions[0]["flow_name"] if executions else "-",
        "latest_status": executions[0]["status"] if executions else "-",
    }

    activity = {
        "generation_events": generation_events,
        "check_events": check_events,
        "imported_contests": imported_contests,
        "reconciliation_runs": reconciliation_runs,
        "reconciliation_games": reconciliation_games,
        "generated_games": generated_games,
    }

    live_signals = [
        {
            "signal": "geracao",
            "value": generation_events,
            "status": "active" if generation_events else "idle",
            "last_seen": _isoformat(latest_generation[0]) if latest_generation else None,
        },
        {
            "signal": "conferencia",
            "value": check_events,
            "status": "active" if check_events else "idle",
            "last_seen": _isoformat(latest_check[0]) if latest_check else None,
        },
        {
            "signal": "caixa_sync",
            "value": imported_contests,
            "status": "active" if imported_contests else "idle",
            "last_seen": _isoformat(latest_sync[0]) if latest_sync else None,
        },
        {
            "signal": "reconciliacao",
            "value": reconciliation_runs,
            "status": "active" if reconciliation_runs else "idle",
            "last_seen": None,
        },
    ]

    snapshot = LiveTelemetrySnapshot(
        created_at=datetime.now(UTC),
        source=str(db_path),
        summary={
            "telemetry_status": "live" if any(item["status"] == "active" for item in live_signals) else "idle",
            "activity_level": "high" if generation_events + check_events >= 3 else "moderate" if generation_events + check_events else "idle",
            "runtime_awareness": "connected" if runtime_status["execution_count"] else "standby",
            "latest_execution_id": runtime_status["latest_execution_id"],
        },
        activity=activity,
        live_signals=live_signals,
        runtime_status=runtime_status,
        metadata={
            "layer": "live_telemetry_engine",
            "metrics_count": len(metrics),
            "lineage_count": len(lineage),
            "snapshot_count": len(snapshots),
        },
    )
    return snapshot.to_dict()
