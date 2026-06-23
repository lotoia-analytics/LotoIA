from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, time
from pathlib import Path
from time import sleep
from typing import Any, Callable
from zoneinfo import ZoneInfo

from lotoia.clients.auto_conference_job import run_auto_conference
from lotoia.clients.premio_notifier import notify_winners
from lotoia.public.institutional_conference_job import run_institutional_conference
from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.ingestion.result_sync_service import ResultSyncService

# Add scripts directory to path for m_feedback_001_loop import
_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

SAO_PAULO = ZoneInfo("America/Sao_Paulo")


@dataclass(frozen=True, slots=True)
class ConferenceWindow:
    hour: int
    minute: int
    action: str

    @classmethod
    def parse(cls, value: str, action: str) -> "ConferenceWindow":
        hour_str, minute_str = value.split(":", maxsplit=1)
        return cls(hour=int(hour_str), minute=int(minute_str), action=action)

    def label(self) -> str:
        return f"{self.hour:02d}:{self.minute:02d}:{self.action}"

    def as_time(self) -> time:
        return time(self.hour, self.minute, tzinfo=SAO_PAULO)


@dataclass(frozen=True, slots=True)
class ClientConferenceSchedule:
    windows: tuple[ConferenceWindow, ...] = (
        ConferenceWindow.parse("22:30", "sync"),
        ConferenceWindow.parse("22:45", "conference"),
        ConferenceWindow.parse("22:50", "feedback"),
        ConferenceWindow.parse("23:00", "notify"),
    )

    def due_windows(self, current: datetime) -> list[ConferenceWindow]:
        if current.weekday() == 6:
            return []
        return [
            window
            for window in self.windows
            if datetime.combine(current.date(), window.as_time()).astimezone(SAO_PAULO)
            <= current
        ]


@dataclass(slots=True)
class ClientConferenceScheduleState:
    attempted_windows_by_date: dict[date, set[str]] = field(default_factory=dict)
    last_summary: dict[str, Any] = field(default_factory=dict)


class ClientConferenceScheduler:
    """Runs official sync, auto conference, and winner notifications (Mon-Sat BRT)."""

    DEFAULT_STATE_PATH = Path("data/client_conference_scheduler_state.json")

    def __init__(
        self,
        *,
        db_path: Path = DEFAULT_DATABASE_PATH,
        schedule: ClientConferenceSchedule | None = None,
        now_provider: Callable[[], datetime] | None = None,
        state_path: Path | None = DEFAULT_STATE_PATH,
        sync_service: ResultSyncService | None = None,
    ) -> None:
        self.db_path = db_path
        self.schedule = schedule or ClientConferenceSchedule()
        self.now_provider = now_provider or (lambda: datetime.now(SAO_PAULO))
        self.state_path = state_path
        self.sync_service = sync_service or ResultSyncService()
        self.state = ClientConferenceScheduleState()
        self._load_state()

    def due_window_labels(self, now: datetime | None = None) -> list[str]:
        current = self._normalize_now(now)
        attempted_windows = self.state.attempted_windows_by_date.get(
            current.date(), set()
        )
        return [
            window.label()
            for window in self.schedule.due_windows(current)
            if window.label() not in attempted_windows
        ]

    def run_due_jobs(self, now: datetime | None = None) -> list[dict[str, Any]]:
        current = self._normalize_now(now)
        summaries: list[dict[str, Any]] = []
        contest_number = 0
        attempted_windows = self.state.attempted_windows_by_date.get(
            current.date(), set()
        )
        for window in self.schedule.due_windows(current):
            label = window.label()
            if label in attempted_windows:
                continue
            if window.action == "sync":
                summary = self.sync_service.sync_latest().to_dict()
            elif window.action == "conference":
                client_summary = run_auto_conference(db_path=self.db_path)
                inst_summary = run_institutional_conference(db_path=self.db_path)
                summary = {
                    "client_conference": client_summary,
                    "institutional_conference": inst_summary,
                    "contest_number": client_summary.get("contest_number")
                    or inst_summary.get("contest_number"),
                }
                contest_number = int(summary.get("contest_number") or 0)
            elif window.action == "feedback":
                if contest_number <= 0:
                    from lotoia.database.contest_repository import ContestRepository

                    contest_number = int(
                        ContestRepository(
                            self.db_path
                        ).get_official_history_max_contest()
                        or 0
                    )
                if contest_number > 0:
                    from scripts.ops.m_feedback_001_loop import (
                        run_feedback_loop_programmatic,
                    )

                    summary = run_feedback_loop_programmatic(
                        contest_number=contest_number, persist=True
                    )
                else:
                    summary = {"status": "skipped", "reason": "no_contest_number"}
            else:
                if contest_number <= 0:
                    from lotoia.database.contest_repository import ContestRepository

                    contest_number = int(
                        ContestRepository(
                            self.db_path
                        ).get_official_history_max_contest()
                        or 0
                    )
                summary = (
                    notify_winners(contest_number, db_path=self.db_path)
                    if contest_number > 0
                    else {"status": "skipped", "reason": "no_contest_number"}
                )
            summary = {"window": label, **dict(summary)}
            summaries.append(summary)
            self.state.attempted_windows_by_date.setdefault(current.date(), set()).add(
                label
            )
            self.state.last_summary = summary
            self._save_state()
        if not summaries:
            self._save_state()
        return summaries

    def run_forever(self, *, poll_seconds: int = 30) -> None:
        while True:
            self.run_due_jobs()
            sleep(max(1, poll_seconds))

    def _normalize_now(self, now: datetime | None) -> datetime:
        current = now or self.now_provider()
        if current.tzinfo is None:
            return current.replace(tzinfo=SAO_PAULO)
        return current.astimezone(SAO_PAULO)

    def _load_state(self) -> None:
        if self.state_path is None or not self.state_path.exists():
            return
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return
        if not isinstance(payload, dict):
            return
        attempted_windows_by_date = payload.get("attempted_windows_by_date", {})
        if isinstance(attempted_windows_by_date, dict):
            parsed_attempts: dict[date, set[str]] = {}
            for key, value in attempted_windows_by_date.items():
                try:
                    parsed_date = date.fromisoformat(str(key))
                except Exception:
                    continue
                if isinstance(value, list):
                    parsed_attempts[parsed_date] = {
                        str(item) for item in value if str(item)
                    }
            self.state.attempted_windows_by_date = parsed_attempts
        last_summary = payload.get("last_summary", {})
        if isinstance(last_summary, dict):
            self.state.last_summary = dict(last_summary)

    def _save_state(self) -> None:
        if self.state_path is None:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "attempted_windows_by_date": {
                day.isoformat(): sorted(windows)
                for day, windows in self.state.attempted_windows_by_date.items()
            },
            "last_summary": self.state.last_summary,
        }
        self.state_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
