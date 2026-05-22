from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH

from .workflow_engine import WorkflowEngine


@dataclass(frozen=True, slots=True)
class WorkflowDashboardSnapshot:
    source: str
    state: str
    summary: dict[str, Any]
    live_workflows: list[dict[str, Any]]
    alerts: list[dict[str, Any]]
    narrative: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "state": self.state,
            "summary": self.summary,
            "live_workflows": self.live_workflows,
            "alerts": self.alerts,
            "narrative": self.narrative,
        }


def build_workflow_dashboard(db_path: Path | None = None) -> dict[str, Any]:
    engine = WorkflowEngine(db_path or DEFAULT_DATABASE_PATH)
    dashboard = engine.build_dashboard()
    telemetry = engine.build_telemetry()
    state = "operational" if telemetry["workflow_status"] == "healthy" else "review"
    snapshot = WorkflowDashboardSnapshot(
        source=str(db_path or DEFAULT_DATABASE_PATH),
        state=state,
        summary={
            "workflow_count": telemetry["workflow_count"],
            "step_count": telemetry["step_count"],
            "failure_count": telemetry["failure_count"],
            "retry_count": telemetry["retry_count"],
            "latest_status": telemetry["latest_status"],
            "workflow_status": telemetry["workflow_status"],
            "runtime_stability": telemetry["runtime_stability"],
        },
        live_workflows=dashboard.get("active_workflows", []),
        alerts=dashboard.get("alerts", []),
        narrative=[
            f"Estado {state}",
            f"Fluxos {telemetry['workflow_count']}",
            f"Falhas {telemetry['failure_count']}",
            f"Retries {telemetry['retry_count']}",
        ],
    )
    return snapshot.to_dict()
