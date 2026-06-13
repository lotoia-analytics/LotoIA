from __future__ import annotations

import logging
from pathlib import Path

from lotoia.database.contest_repository import ContestRepository
from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.ingestion.result_sync_service import ResultSyncService

logger = logging.getLogger(__name__)


def _contest_exists(db_path: Path, contest_number: int) -> bool:
    repository = ContestRepository(db_path)
    return bool(
        repository.get_official_history_contest(int(contest_number))
        or repository.get_contest(int(contest_number))
    )


def get_latest_official_contest(db_path: Path = DEFAULT_DATABASE_PATH) -> int | None:
    repository = ContestRepository(db_path)
    latest = repository.get_official_history_max_contest()
    if latest is not None:
        return int(latest)
    last_imported = repository.get_last_contest()
    return int(last_imported) if last_imported is not None else None


def sync_latest_official_results(db_path: Path = DEFAULT_DATABASE_PATH) -> list[int]:
    """Sincroniza concursos pendentes com a API Caixa e persiste no PostgreSQL."""
    service = ResultSyncService(db_path=db_path)
    summary = service.sync_latest()
    if summary.commit_state != "ok":
        logger.warning(
            "OFFICIAL_SYNC_LATEST_FAILED synced=%s error=%s",
            summary.synced_contests,
            summary.error_message,
        )
        return []
    logger.info(
        "OFFICIAL_SYNC_LATEST_OK latest=%s synced=%s",
        summary.latest_contest,
        summary.synced_contests,
    )
    return list(summary.synced_contests or [])


def ensure_official_contest_available(
    db_path: Path,
    contest_number: int,
    *,
    sync_latest_first: bool = True,
) -> bool:
    """Garante resultado oficial no PostgreSQL; tenta Caixa se ausente."""
    target = int(contest_number)
    if _contest_exists(db_path, target):
        return True

    service = ResultSyncService(db_path=db_path)

    if sync_latest_first:
        latest_summary = service.sync_latest()
        if target in (latest_summary.synced_contests or []) and latest_summary.commit_state == "ok":
            return True
        if _contest_exists(db_path, target):
            return True

    contest_summary = service.sync_contests([target])
    if target in (contest_summary.synced_contests or []) and contest_summary.commit_state == "ok":
        return True
    return _contest_exists(db_path, target)
