from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.database.database import (
    CheckEvent,
    ExpansionEvent,
    GenerationEvent,
    Lead,
    MlUsageEvent,
    ReportEvent,
    ReconciliationEvent,
    get_session,
)
from lotoia.public.persistence.repositories import (
    CheckEventRepository,
    ExpansionEventRepository,
    GenerationEventRepository,
    LeadRepository,
    MlUsageEventRepository,
    ReportEventRepository,
    ReconciliationEventRepository,
)


@dataclass(frozen=True)
class InstitutionalDatabaseAdapter:
    """Resolve the institutional database backend and connection target."""

    path: Path = DEFAULT_DATABASE_PATH

    @property
    def database_url(self) -> str:
        env_url = os.getenv("DATABASE_URL", "").strip()
        if env_url:
            return env_url
        resolved = self.path if self.path.is_absolute() else self.path.resolve()
        return f"sqlite:///{resolved.as_posix()}"

    @property
    def backend(self) -> str:
        url = self.database_url.lower()
        if url.startswith("sqlite:///"):
            return "sqlite"
        if url.startswith("postgresql") or url.startswith("postgres://"):
            return "postgresql"
        return "unknown"

    @property
    def sqlite_path(self) -> Path:
        return self.path if self.path.is_absolute() else self.path.resolve()

    @property
    def is_shared_cloud_ready(self) -> bool:
        return self.backend == "postgresql"

    def save_lead(self, **kwargs: Any) -> dict[str, Any]:
        repository = LeadRepository(self.sqlite_path)
        return repository.insert(**kwargs)

    def save_generation_event(self, **kwargs: Any) -> dict[str, Any]:
        repository = GenerationEventRepository(self.sqlite_path)
        return repository.insert(**kwargs)

    def save_check_event(self, **kwargs: Any) -> dict[str, Any]:
        repository = CheckEventRepository(self.sqlite_path)
        return repository.insert(**kwargs)

    def save_ml_usage_event(self, **kwargs: Any) -> dict[str, Any]:
        repository = MlUsageEventRepository(self.sqlite_path)
        return repository.insert(**kwargs)

    def save_report_event(self, **kwargs: Any) -> dict[str, Any]:
        repository = ReportEventRepository(self.sqlite_path)
        return repository.insert(**kwargs)

    def save_expansion_event(self, **kwargs: Any) -> dict[str, Any]:
        repository = ExpansionEventRepository(self.sqlite_path)
        return repository.insert(**kwargs)

    def save_reconciliation_event(self, **kwargs: Any) -> dict[str, Any]:
        repository = ReconciliationEventRepository(self.sqlite_path)
        return repository.insert(**kwargs)

    def fetch_generation_events(self, lead_id: int | None = None) -> list[dict[str, Any]]:
        with get_session(self.sqlite_path) as session:
            query = session.query(GenerationEvent)
            if lead_id is not None:
                query = query.filter(GenerationEvent.lead_id == lead_id)
            rows = query.order_by(GenerationEvent.created_at.desc(), GenerationEvent.id.desc()).all()
            return [
                {column.name: getattr(row, column.name) for column in row.__table__.columns}
                for row in rows
            ]

    def fetch_usage_metrics(self) -> dict[str, int]:
        with get_session(self.sqlite_path) as session:
            return {
                "leads": int(session.query(Lead).count()),
                "generation_events": int(session.query(GenerationEvent).count()),
                "ml_usage_events": int(session.query(MlUsageEvent).count()),
                "check_events": int(session.query(CheckEvent).count()),
                "report_events": int(session.query(ReportEvent).count()),
                "expansion_events": int(session.query(ExpansionEvent).count()),
                "reconciliation_events": int(session.query(ReconciliationEvent).count()),
            }

    def fetch_latest_usage_snapshot(self) -> dict[str, Any]:
        metrics = self.fetch_usage_metrics()
        return {
            **metrics,
            "backend": self.backend,
            "database_url": self.database_url,
            "sqlite_path": str(self.sqlite_path),
            "shared_cloud_ready": self.is_shared_cloud_ready,
        }


class SQLiteInstitutionalAdapter(InstitutionalDatabaseAdapter):
    """SQLite-backed institutional adapter kept for local/runtime compatibility."""

    pass
