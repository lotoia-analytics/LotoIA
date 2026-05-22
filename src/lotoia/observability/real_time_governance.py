from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lotoia.governance.operational_policy_guard import OperationalPolicyGuard

from .operational_health import build_operational_health_snapshot


@dataclass(frozen=True, slots=True)
class RealTimeGovernanceSnapshot:
    created_at: datetime
    source: str
    status: str
    score: float
    policy_allowed: bool
    health: dict[str, Any]
    summary: dict[str, Any]
    alerts: list[dict[str, Any]]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at.isoformat(),
            "source": self.source,
            "status": self.status,
            "score": self.score,
            "policy_allowed": self.policy_allowed,
            "health": self.health,
            "summary": self.summary,
            "alerts": self.alerts,
            "metadata": self.metadata,
        }


def build_real_time_governance(
    db_path: Path | None = None,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    health = build_operational_health_snapshot(db_path=db_path, limit=limit)
    metrics = {
        "health_score": float(health.get("score", 0.0)),
        "critical_anomaly_count": float(len([alert for alert in health.get("alerts", []) if str(alert.get("severity")) == "critical"])),
        "calibration_drift_signal": float(0.0 if health.get("telemetry_status") == "live" else 0.25),
        "confidence_average": float(health.get("score", 0.0)),
        "rerank_average_gain": float(0.0),
    }
    policy_result = OperationalPolicyGuard().evaluate(metrics)
    score = round(max(0.0, min(1.0, float(health.get("score", 0.0)) * (1.0 if policy_result.allowed else 0.75))), 2)
    status = "governed" if policy_result.allowed and health.get("status") == "healthy" else "watch" if health.get("status") == "degraded" else "alert"
    snapshot = RealTimeGovernanceSnapshot(
        created_at=datetime.now(UTC),
        source=str(db_path) if db_path else "",
        status=status,
        score=score,
        policy_allowed=policy_result.allowed,
        health=health,
        summary={
            "health_status": health.get("status", "-"),
            "health_score": health.get("score", 0.0),
            "policy_allowed": policy_result.allowed,
            "blocking_count": policy_result.blocking_count,
            "alert_count": len(health.get("alerts", [])),
        },
        alerts=list(health.get("alerts", [])),
        metadata={
            "layer": "real_time_governance",
            "policy_allowed": policy_result.allowed,
            "blocking_count": policy_result.blocking_count,
        },
    )
    return snapshot.to_dict()
