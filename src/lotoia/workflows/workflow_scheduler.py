from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, time
from time import sleep
from typing import Any, Callable
from zoneinfo import ZoneInfo

from lotoia.workflows.workflow_engine import WorkflowEngine

SAO_PAULO = ZoneInfo("America/Sao_Paulo")


@dataclass(frozen=True, slots=True)
class WorkflowSchedule:
    polling_windows: tuple[time, ...] = (
        time(21, 15, tzinfo=SAO_PAULO),
        time(21, 30, tzinfo=SAO_PAULO),
        time(21, 55, tzinfo=SAO_PAULO),
    )
    cleanup_window: time = time(0, 0, tzinfo=SAO_PAULO)


@dataclass(slots=True)
class WorkflowSchedulerState:
    last_sync_date: datetime | None = None
    last_cleanup_date: datetime | None = None
    last_payload: dict[str, Any] = field(default_factory=dict)


class WorkflowScheduler:
    """Coordinate Caixa sync, closure cleanup, and workflow snapshots."""

    def __init__(
        self,
        *,
        engine: WorkflowEngine | None = None,
        schedule: WorkflowSchedule | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self.engine = engine or WorkflowEngine()
        self.schedule = schedule or WorkflowSchedule()
        self.now_provider = now_provider or (lambda: datetime.now(SAO_PAULO))
        self.state = WorkflowSchedulerState()

    def due_sync_windows(self, now: datetime | None = None) -> list[str]:
        current = self._normalize(now)
        return [
            window.strftime("%H:%M")
            for window in self.schedule.polling_windows
            if datetime.combine(current.date(), window).astimezone(SAO_PAULO) <= current
        ]

    def run_due_workflows(self, now: datetime | None = None) -> dict[str, Any]:
        current = self._normalize(now)
        payload: dict[str, Any] = {
            "scheduled_at": current.isoformat(),
            "sync_windows": self.due_sync_windows(current),
            "sync_runs": [],
            "cleanup": {"due": current.time() >= self.schedule.cleanup_window, "status": "idle"},
            "workflow_telemetry": self.engine.build_telemetry(),
        }
        if payload["sync_windows"]:
            sync_result = self.engine.run_schedule_cycle()
            payload["sync_runs"].append(sync_result)
            self.state.last_sync_date = current
        if current.time() >= self.schedule.cleanup_window:
            self.state.last_cleanup_date = current
            payload["cleanup"] = {"due": True, "status": "scheduled", "executed_at": current.isoformat()}
        self.state.last_payload = payload
        return payload

    def run_forever(self, *, poll_seconds: int = 30) -> None:
        while True:
            self.run_due_workflows()
            sleep(max(5, poll_seconds))

    def _normalize(self, now: datetime | None) -> datetime:
        current = now or self.now_provider()
        if current.tzinfo is None:
            return current.replace(tzinfo=SAO_PAULO)
        return current.astimezone(SAO_PAULO)
