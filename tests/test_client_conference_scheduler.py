from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from lotoia.clients.client_conference_scheduler import ClientConferenceScheduler

SAO_PAULO = ZoneInfo("America/Sao_Paulo")


def test_scheduler_skips_sunday(tmp_path: Path) -> None:
    scheduler = ClientConferenceScheduler(
        db_path=tmp_path / "lotoia.db",
        state_path=tmp_path / "scheduler_state.json",
        now_provider=lambda: datetime(2026, 6, 14, 23, 0, tzinfo=SAO_PAULO),
    )
    assert scheduler.due_window_labels() == []


def test_scheduler_exposes_brt_windows(tmp_path: Path) -> None:
    scheduler = ClientConferenceScheduler(
        db_path=tmp_path / "lotoia.db",
        state_path=tmp_path / "scheduler_state.json",
        now_provider=lambda: datetime(2026, 6, 11, 23, 5, tzinfo=SAO_PAULO),
    )
    labels = scheduler.due_window_labels()
    assert labels == ["22:30:sync", "22:45:conference", "23:00:notify"]
