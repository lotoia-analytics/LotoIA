from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from lotoia.ingestion.result_sync_scheduler import ResultSyncScheduler, SyncWindow


@dataclass
class FakeSummary:
    synced_contests: list[int]

    def to_dict(self) -> dict[str, object]:
        return {"synced_contests": self.synced_contests}


class FakeService:
    def __init__(self) -> None:
        self.calls = 0

    def sync_latest(self):
        self.calls += 1
        return FakeSummary([3690] if self.calls == 1 else [])


class FailingThenSuccessService:
    def __init__(self) -> None:
        self.calls = 0

    def sync_latest(self):
        self.calls += 1
        return FakeSummary([] if self.calls == 1 else [3690])


def test_scheduler_marks_due_windows(tmp_path: Path) -> None:
    scheduler = ResultSyncScheduler(service=FakeService(), state_path=tmp_path / "scheduler_state.json")
    current = datetime(2026, 5, 21, 21, 31)
    assert scheduler.due_window_labels(current) == ["21:15", "21:30"]


def test_scheduler_advances_to_next_window_same_day(tmp_path: Path) -> None:
    service = FakeService()
    scheduler = ResultSyncScheduler(service=service, state_path=tmp_path / "scheduler_state.json")
    current = datetime(2026, 5, 21, 21, 31)

    summaries = scheduler.run_due_checks(current)

    assert len(summaries) == 1
    assert service.calls == 1
    assert scheduler.state.last_synced_window == "21:15"

    again = scheduler.run_due_checks(current)
    assert len(again) == 1
    assert service.calls == 2
    assert scheduler.state.last_synced_window == "21:30"


def test_scheduler_advances_to_next_window_after_no_sync(tmp_path: Path) -> None:
    service = FailingThenSuccessService()
    scheduler = ResultSyncScheduler(service=service, state_path=tmp_path / "scheduler_state.json")
    current = datetime(2026, 5, 21, 21, 31)

    first = scheduler.run_due_checks(current)
    second = scheduler.run_due_checks(current)

    assert len(first) == 1
    assert len(second) == 1
    assert scheduler.state.last_synced_window == "21:30"
    assert scheduler.state.successful_dates == {current.date()}
    assert service.calls == 2


def test_sync_window_parse() -> None:
    window = SyncWindow.parse("21:55")
    assert (window.hour, window.minute) == (21, 55)


def test_scheduler_persists_bootstrap_state(tmp_path: Path) -> None:
    state_path = tmp_path / "result_sync_state.json"
    service = FakeService()
    scheduler = ResultSyncScheduler(service=service, state_path=state_path)
    current = datetime(2026, 5, 21, 21, 31)

    scheduler.run_due_checks(current)

    assert state_path.exists()

    resumed = ResultSyncScheduler(service=service, state_path=state_path)
    assert resumed.due_window_labels(current) == ["21:30"]


def test_scheduler_keeps_later_windows_after_success_same_day(tmp_path: Path) -> None:
    scheduler = ResultSyncScheduler(service=FakeService(), state_path=tmp_path / "scheduler_state.json")
    current = datetime(2026, 5, 21, 21, 31)
    scheduler.state.successful_dates.add(current.date())
    assert scheduler.due_window_labels(current) == ["21:15", "21:30"]
