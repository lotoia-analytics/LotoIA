from __future__ import annotations

from datetime import datetime
from pathlib import Path

from lotoia.workflows import WorkflowScheduler, WorkflowSchedule


def test_workflow_scheduler_marks_due_windows_and_runs_once(monkeypatch, tmp_path: Path) -> None:
    scheduler = WorkflowScheduler(
        schedule=WorkflowSchedule(),
        now_provider=lambda: datetime(2026, 5, 21, 21, 30),
    )

    monkeypatch.setattr(scheduler.engine, "run_schedule_cycle", lambda: {"status": "completed", "sync_runs": [{"ok": True}]})
    payload = scheduler.run_due_workflows()

    assert payload["sync_windows"] == ["21:15", "21:30"]
    assert payload["sync_runs"][0]["status"] == "completed"
    assert payload["workflow_telemetry"]["workflow_status"] in {"healthy", "degraded"}


def test_workflow_scheduler_marks_cleanup_window(monkeypatch) -> None:
    scheduler = WorkflowScheduler(
        schedule=WorkflowSchedule(),
        now_provider=lambda: datetime(2026, 5, 22, 0, 10),
    )

    monkeypatch.setattr(scheduler.engine, "run_schedule_cycle", lambda: {"status": "idle", "sync_runs": []})
    payload = scheduler.run_due_workflows()

    assert payload["cleanup"]["due"] is True
    assert payload["cleanup"]["status"] == "scheduled"
