from __future__ import annotations

import json
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.database.contest_repository import ContestRepository
from lotoia.ingestion.caixa_api_client import CaixaApiClient, CaixaContestResult


@dataclass(frozen=True)
class ResultSyncSummary:
    latest_contest: int | None
    synced_contests: list[int]
    synced_contests_count: int
    persisted_contests: int
    provider_payload_count: int
    contest_ids: list[int]
    db_backend: str
    engine_url: str
    commit_state: str
    source: str
    fallback_used: bool = False
    error_message: str | None = None
    traceback: str | None = None
    rollback: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "latest_contest": self.latest_contest,
            "synced_contests": self.synced_contests,
            "synced_contests_count": self.synced_contests_count,
            "persisted_contests": self.persisted_contests,
            "provider_payload_count": self.provider_payload_count,
            "contest_ids": self.contest_ids,
            "db_backend": self.db_backend,
            "engine_url": self.engine_url,
            "commit_state": self.commit_state,
            "source": self.source,
            "fallback_used": self.fallback_used,
            "error_message": self.error_message,
            "traceback": self.traceback,
            "rollback": self.rollback,
        }


class ResultSyncService:
    """Official draw synchronization service with conservative persistence."""

    MAX_SYNCED_CONTESTS_PER_RUN = 10

    def __init__(
        self,
        *,
        client: CaixaApiClient | None = None,
        repository: ContestRepository | None = None,
        db_path: str | Path | None = None,
    ) -> None:
        self.client = client or CaixaApiClient()
        resolved_db_path = Path(db_path) if db_path is not None else DEFAULT_DATABASE_PATH
        self.repository = repository or ContestRepository(resolved_db_path)

    def _build_summary(
        self,
        *,
        latest_contest: int | None,
        synced_contests: list[int],
        provider_payload_count: int,
        source: str,
        commit_state: str,
        persisted_contests: int | None = None,
        fallback_used: bool = False,
        error_message: str | None = None,
        tb: str | None = None,
        rollback: bool = False,
    ) -> ResultSyncSummary:
        return ResultSyncSummary(
            latest_contest=latest_contest,
            synced_contests=synced_contests,
            synced_contests_count=len(synced_contests),
            persisted_contests=persisted_contests if persisted_contests is not None else len(synced_contests),
            provider_payload_count=provider_payload_count,
            contest_ids=list(synced_contests),
            db_backend=getattr(self.repository, "backend", "sqlite"),
            engine_url=getattr(self.repository, "database_url", ""),
            commit_state=commit_state,
            source=source,
            fallback_used=fallback_used,
            error_message=error_message,
            traceback=tb,
            rollback=rollback,
        )

    def sync_latest(self) -> ResultSyncSummary:
        self.repository.create_table()
        try:
            latest = self.client.fetch_latest()
            latest_contest = int(latest.contest_number)
            last_imported = int(self.repository.get_last_contest() or 0)

            synced_contests: list[int] = []
            contests_to_sync = [latest_contest]
            gap = latest_contest - last_imported
            if 0 < last_imported < latest_contest and gap <= self.MAX_SYNCED_CONTESTS_PER_RUN:
                contests_to_sync = list(range(last_imported + 1, latest_contest + 1))

            provider_payload_count = len(contests_to_sync)
            for contest_number in contests_to_sync:
                try:
                    contest = latest if contest_number == latest_contest else self.client.fetch_contest(contest_number)
                    with self.repository.transaction() as tx:
                        self.repository.save_contest(
                            contest.to_contest_record(),
                            commit=False,
                            session=tx,
                        )
                    synced_contests.append(contest.contest_number)
                except Exception:
                    if contest_number == latest_contest:
                        raise
                    continue

            latest_record = self.repository.get_latest_contest_record()
            persisted_contest = int(latest_record["concurso"]) if latest_record else None
            if persisted_contest != latest_contest:
                raise RuntimeError(
                    f"PostgreSQL persistence mismatch: latest={latest_contest} persisted={persisted_contest}"
                )

            return self._build_summary(
                latest_contest=latest_contest,
                synced_contests=synced_contests,
                provider_payload_count=provider_payload_count,
                source=latest.source_url,
                commit_state="ok",
            )
        except Exception as exc:
            tb = traceback.format_exc()
            latest_record = self.repository.get_latest_contest_record()
            fallback_contest = int(latest_record["concurso"]) if latest_record else None
            return self._build_summary(
                latest_contest=fallback_contest,
                synced_contests=[],
                provider_payload_count=0,
                source=self.client.base_url,
                commit_state="failed",
                persisted_contests=0,
                fallback_used=True,
                error_message=str(exc),
                tb=tb,
                rollback=True,
            )

    def sync_contests(self, contest_numbers: list[int]) -> ResultSyncSummary:
        self.repository.create_table()
        try:
            synced_contests: list[int] = []
            latest_contest: int | None = None
            provider_payload_count = len(contest_numbers)
            with self.repository.transaction() as tx:
                for contest in self.client.fetch_contests(contest_numbers):
                    self.repository.save_contest(
                        contest.to_contest_record(),
                        commit=False,
                        session=tx,
                    )
                    synced_contests.append(contest.contest_number)
                    latest_contest = contest.contest_number
            return self._build_summary(
                latest_contest=latest_contest,
                synced_contests=synced_contests,
                provider_payload_count=provider_payload_count,
                source=self.client.base_url,
                commit_state="ok",
            )
        except Exception as exc:
            tb = traceback.format_exc()
            latest_record = self.repository.get_latest_contest_record()
            fallback_contest = int(latest_record["concurso"]) if latest_record else None
            return self._build_summary(
                latest_contest=fallback_contest,
                synced_contests=[],
                provider_payload_count=0,
                source=self.client.base_url,
                commit_state="failed",
                persisted_contests=0,
                fallback_used=True,
                error_message=str(exc),
                tb=tb,
                rollback=True,
            )

    def sync_to_report(self, report_path: Path, contest_numbers: list[int] | None = None) -> dict[str, Any]:
        summary = self.sync_contests(contest_numbers) if contest_numbers else self.sync_latest()
        payload = {
            "schema_version": "operational-result-sync-v1.0.0",
            "generated_by": "ResultSyncService.sync_to_report",
            "summary": summary.to_dict(),
        }
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload
