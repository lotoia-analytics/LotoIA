from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from time import sleep
from typing import Any, Callable
from zoneinfo import ZoneInfo

from lotoia.ingestion.result_sync_service import ResultSyncService, ResultSyncSummary

SAO_PAULO = ZoneInfo("America/Sao_Paulo")


@dataclass(frozen=True, slots=True)
class SyncWindow:
    hour: int
    minute: int

    @classmethod
    def parse(cls, value: str) -> "SyncWindow":
        hour_str, minute_str = value.split(":", maxsplit=1)
        return cls(hour=int(hour_str), minute=int(minute_str))

    def label(self) -> str:
        return f"{self.hour:02d}:{self.minute:02d}"

    def as_time(self) -> time:
        return time(self.hour, self.minute, tzinfo=SAO_PAULO)


@dataclass(frozen=True, slots=True)
class ResultSyncSchedule:
    windows: tuple[SyncWindow, ...] = (
        SyncWindow(21, 15),
        SyncWindow(21, 30),
        SyncWindow(21, 55),
    )

    def due_windows(self, current: datetime) -> list[SyncWindow]:
        return [
            window
            for window in self.windows
            if datetime.combine(current.date(), window.as_time()).astimezone(SAO_PAULO) <= current
        ]


@dataclass(slots=True)
class ResultSyncScheduleState:
    successful_dates: set[date] = field(default_factory=set)
    attempted_windows_by_date: dict[date, set[str]] = field(default_factory=dict)
    last_synced_window: str | None = None
    last_summary: dict[str, Any] = field(default_factory=dict)


class ResultSyncScheduler:
    """Automatic official result checker for the Caixa windows."""

    def __init__(
        self,
        *,
        service: ResultSyncService | None = None,
        schedule: ResultSyncSchedule | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self.service = service or ResultSyncService()
        self.schedule = schedule or ResultSyncSchedule()
        self.now_provider = now_provider or (lambda: datetime.now(SAO_PAULO))
        self.state = ResultSyncScheduleState()

    def due_window_labels(self, now: datetime | None = None) -> list[str]:
        current = self._normalize_now(now)
        if current.date() in self.state.successful_dates:
            return []
        attempted_windows = self.state.attempted_windows_by_date.get(current.date(), set())
        return [
            window.label()
            for window in self.schedule.due_windows(current)
            if window.label() not in attempted_windows
        ]

    def run_due_checks(self, now: datetime | None = None) -> list[ResultSyncSummary]:
        current = self._normalize_now(now)
        if current.date() in self.state.successful_dates:
            return []

        summaries: list[ResultSyncSummary] = []
        for label in self.due_window_labels(current)[:1]:
            summary = self.service.sync_latest()
            self.state.last_synced_window = label
            self.state.last_summary = summary.to_dict()
            self.state.attempted_windows_by_date.setdefault(current.date(), set()).add(label)
            summaries.append(summary)
            if summary.synced_contests:
                self.state.successful_dates.add(current.date())
                break
        return summaries

    def run_forever(self, *, poll_seconds: int = 30, stop_after_first_success: bool = False) -> None:
        while True:
            summaries = self.run_due_checks()
            if stop_after_first_success and any(summary.synced_contests for summary in summaries):
                return
            sleep(max(1, poll_seconds))

    def _normalize_now(self, now: datetime | None) -> datetime:
        current = now or self.now_provider()
        if current.tzinfo is None:
            return current.replace(tzinfo=SAO_PAULO)
        return current.astimezone(SAO_PAULO)
