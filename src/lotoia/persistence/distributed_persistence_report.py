"""Distributed persistence report for enterprise storage operations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class DistributedPersistenceReport:
    """Report for one distributed persistence synchronization cycle."""

    snapshot_id: str
    artifact_id: str
    replicated_count: int
    backup_count: int
    failover_enabled: bool
    active_backend: str
    report_id: str = field(default_factory=lambda: f"persistence-report-{uuid4().hex}")
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def successful(self) -> bool:
        """Whether persistence completed successfully."""

        return self.replicated_count > 0 and self.backup_count >= 0

    def summary_metrics(self) -> dict[str, float]:
        """Return observability metrics."""

        return {
            "storage.replication.copied_count": float(self.replicated_count),
            "storage.backup.file_count": float(self.backup_count),
            "storage.failover.enabled": 1.0 if self.failover_enabled else 0.0,
            "storage.persistence.successful": 1.0 if self.successful else 0.0,
        }

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-ready report."""

        return _to_jsonable(self)


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value
