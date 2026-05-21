from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lotoia.database.contest_repository import ContestRepository
from lotoia.ingestion.caixa_api_client import CaixaApiClient, CaixaContestResult


@dataclass(frozen=True)
class ResultSyncSummary:
    latest_contest: int | None
    synced_contests: list[int]
    persisted_contests: int
    source: str
    fallback_used: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "latest_contest": self.latest_contest,
            "synced_contests": self.synced_contests,
            "persisted_contests": self.persisted_contests,
            "source": self.source,
            "fallback_used": self.fallback_used,
        }


class ResultSyncService:
    """Official draw synchronization service with conservative persistence."""

    MAX_SYNCED_CONTESTS_PER_RUN = 10

    def __init__(
        self,
        *,
        client: CaixaApiClient | None = None,
        repository: ContestRepository | None = None,
    ) -> None:
        self.client = client or CaixaApiClient()
        self.repository = repository or ContestRepository()

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

            for contest_number in contests_to_sync:
                contest = latest if contest_number == latest_contest else self.client.fetch_contest(contest_number)
                self.repository.save_contest(contest.to_contest_record())
                synced_contests.append(contest.contest_number)

            return ResultSyncSummary(
                latest_contest=latest_contest,
                synced_contests=synced_contests,
                persisted_contests=len(synced_contests),
                source=latest.source_url,
            )
        except Exception:
            latest_record = self.repository.get_latest_contest_record()
            fallback_contest = int(latest_record["concurso"]) if latest_record else None
            return ResultSyncSummary(
                latest_contest=fallback_contest,
                synced_contests=[],
                persisted_contests=0,
                source=self.client.base_url,
                fallback_used=True,
            )

    def sync_contests(self, contest_numbers: list[int]) -> ResultSyncSummary:
        self.repository.create_table()
        try:
            synced_contests: list[int] = []
            latest_contest: int | None = None
            for contest in self.client.fetch_contests(contest_numbers):
                self.repository.save_contest(contest.to_contest_record())
                synced_contests.append(contest.contest_number)
                latest_contest = contest.contest_number
            return ResultSyncSummary(
                latest_contest=latest_contest,
                synced_contests=synced_contests,
                persisted_contests=len(synced_contests),
                source=self.client.base_url,
            )
        except Exception:
            latest_record = self.repository.get_latest_contest_record()
            fallback_contest = int(latest_record["concurso"]) if latest_record else None
            return ResultSyncSummary(
                latest_contest=fallback_contest,
                synced_contests=[],
                persisted_contests=0,
                source=self.client.base_url,
                fallback_used=True,
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
