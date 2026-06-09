from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.analytics import build_user_lifecycle_analytics
from lotoia.observability.observability_alerts import ObservabilityAlertEngine

from .live_telemetry import build_live_telemetry_snapshot


@dataclass(frozen=True, slots=True)
class OperationalHealthSnapshot:
    created_at: datetime
    status: str
    score: float
    telemetry_status: str
    runtime_awareness: str
    active_signals: int
    alerts: list[dict[str, Any]]
    summary: dict[str, Any]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "score": self.score,
            "telemetry_status": self.telemetry_status,
            "runtime_awareness": self.runtime_awareness,
            "active_signals": self.active_signals,
            "alerts": self.alerts,
            "summary": self.summary,
            "metadata": self.metadata,
        }


def build_operational_health_snapshot(
    db_path: Any = None,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    telemetry = build_live_telemetry_snapshot(db_path=db_path or DEFAULT_DATABASE_PATH, limit=limit)
    lifecycle = build_user_lifecycle_analytics(db_path=db_path or DEFAULT_DATABASE_PATH, limit=limit)
    metrics = {
        "execution.failure_rate": float(telemetry["runtime_status"]["latest_status"] == "failed"),
        "execution.queue_depth": float(telemetry["activity"]["generation_events"] + telemetry["activity"]["check_events"]),
        "worker.available_count": 1.0 if telemetry["summary"]["runtime_awareness"] == "connected" else 0.0,
        "api.route_count": float(telemetry["activity"]["imported_contests"] > 0),
        "user.lifecycle_event_volume": float(lifecycle["lifecycle"]["event_volume"]),
        "user.active_sessions": float(lifecycle["lifecycle"]["active_sessions"]),
        "user.institutional_users": float(lifecycle["lifecycle"]["institutional_users"]),
    }
    alert_engine = ObservabilityAlertEngine()
    alerts = [asdict(alert) for alert in alert_engine.evaluate(metrics)]
    active_signals = sum(1 for item in telemetry.get("live_signals", []) if item.get("status") == "active")
    score = max(0.0, 1.0 - min(1.0, float(len(alerts)) * 0.25))
    status = "healthy" if not alerts else "degraded" if score >= 0.5 else "critical"
    snapshot = OperationalHealthSnapshot(
        created_at=datetime.now(UTC),
        status=status,
        score=round(score, 2),
        telemetry_status=str(telemetry["summary"]["telemetry_status"]),
        runtime_awareness=str(telemetry["summary"]["runtime_awareness"]),
        active_signals=active_signals,
        alerts=alerts,
        summary={
            "latest_execution_id": telemetry["summary"]["latest_execution_id"],
            "activity_level": telemetry["summary"]["activity_level"],
            "telemetry_status": telemetry["summary"]["telemetry_status"],
            "runtime_awareness": telemetry["summary"]["runtime_awareness"],
            "lifecycle_status": lifecycle["summary"]["status"],
            "lifecycle_event_volume": lifecycle["lifecycle"]["event_volume"],
            "lifecycle_active_sessions": lifecycle["lifecycle"]["active_sessions"],
        },
        metadata={
            "layer": "operational_health_engine",
            "active_signal_count": active_signals,
            "alert_count": len(alerts),
            "lifecycle_timeline_size": lifecycle["summary"]["timeline_size"],
        },
    )
    return snapshot.to_dict()
