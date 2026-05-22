from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from time import sleep
from typing import Any, Callable
from zoneinfo import ZoneInfo

from sqlalchemy import text

from sqlalchemy import delete

from lotoia.database.database import DEFAULT_DATABASE_PATH, GeneratedGame, ReconciliationGame, get_session

SAO_PAULO = ZoneInfo("America/Sao_Paulo")


@dataclass(frozen=True, slots=True)
class DailyCleanupSchedule:
    hour: int = 0
    minute: int = 0

    def label(self) -> str:
        return f"{self.hour:02d}:{self.minute:02d}"


@dataclass(slots=True)
class DailyCleanupState:
    last_cleaned_date: date | None = None
    last_payload: dict[str, Any] = field(default_factory=dict)


class DailyOperationalCleanupScheduler:
    """Runs the daily cleanup after the official prize reconciliation."""

    def __init__(
        self,
        *,
        db_path: Path = DEFAULT_DATABASE_PATH,
        schedule: DailyCleanupSchedule | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self.db_path = db_path
        self.schedule = schedule or DailyCleanupSchedule()
        self.now_provider = now_provider or (lambda: datetime.now(SAO_PAULO))
        self.state = DailyCleanupState()

    def due_date(self, now: datetime | None = None) -> date:
        current = self._normalize_now(now)
        return (current - timedelta(days=1)).date()

    def run_due_cleanup(self, now: datetime | None = None) -> dict[str, Any]:
        current = self._normalize_now(now)
        target_date = (current - timedelta(days=1)).date()
        if self.state.last_cleaned_date == target_date:
            return {
                "date": target_date.isoformat(),
                "cleanup": [],
                "status": "skipped",
                "reason": "already_cleaned",
            }

        cleanup_runs: list[dict[str, Any]] = []
        with get_session(self.db_path) as session:
            rows = session.execute(
                text(
                    """
                    SELECT DISTINCT generation_event_id
                    FROM reconciliation_games
                    ORDER BY generation_event_id
                    """
                )
            ).all()

            for row in rows:
                generation_event_id = int(row[0])
                keep_rows = session.execute(
                    text(
                        """
                        SELECT game_index
                        FROM reconciliation_games
                        WHERE generation_event_id = :generation_event_id
                          AND prize_status = 'premiado'
                        """
                    ),
                    {"generation_event_id": generation_event_id},
                ).all()
                keep_indexes = {int(item[0]) for item in keep_rows}
                removed = self._prune_generation_event(
                    generation_event_id=generation_event_id,
                    keep_indexes=keep_indexes,
                )
                cleanup_runs.append(
                    {
                        "generation_event_id": generation_event_id,
                        "retained_indexes": sorted(keep_indexes),
                        "removed_rows": removed,
                    }
                )

        payload = {
            "scheduled_at": current.isoformat(),
            "schedule": self.schedule.label(),
            "date": target_date.isoformat(),
            "status": "completed" if cleanup_runs else "idle",
            "cleanup": cleanup_runs,
        }
        self.state.last_cleaned_date = target_date
        self.state.last_payload = payload
        return payload

    def run_forever(self, *, poll_seconds: int = 60) -> None:
        while True:
            current = self._normalize_now(None)
            if current.hour >= self.schedule.hour and current.minute >= self.schedule.minute:
                self.run_due_cleanup(current)
            sleep(max(5, poll_seconds))

    def _normalize_now(self, now: datetime | None) -> datetime:
        current = now or self.now_provider()
        if current.tzinfo is None:
            return current.replace(tzinfo=SAO_PAULO)
        return current.astimezone(SAO_PAULO)

    def _prune_generation_event(self, *, generation_event_id: int, keep_indexes: set[int]) -> int:
        with get_session(self.db_path) as session:
            generated_stmt = delete(GeneratedGame).where(GeneratedGame.generation_event_id == generation_event_id)
            reconciliation_stmt = delete(ReconciliationGame).where(
                ReconciliationGame.generation_event_id == generation_event_id,
            )
            if keep_indexes:
                generated_stmt = generated_stmt.where(~GeneratedGame.game_index.in_(sorted(keep_indexes)))
                reconciliation_stmt = reconciliation_stmt.where(~ReconciliationGame.game_index.in_(sorted(keep_indexes)))
            removed_generated = int(session.execute(generated_stmt).rowcount or 0)
            removed_reconciliation = int(session.execute(reconciliation_stmt).rowcount or 0)
            session.commit()
            return removed_generated + removed_reconciliation
