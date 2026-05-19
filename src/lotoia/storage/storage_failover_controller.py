"""Storage failover controller for resilient persistence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class StorageFailoverDecision:
    """Decision for storage backend failover."""

    active_backend: str
    failover_enabled: bool
    reason: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


class StorageFailoverController:
    """Select primary or replica storage root based on availability."""

    def decide(self, *, primary_root: str | Path, replica_root: str | Path) -> StorageFailoverDecision:
        """Return storage failover decision."""

        primary = Path(primary_root)
        replica = Path(replica_root)
        if primary.exists() and _writable(primary):
            return StorageFailoverDecision(
                active_backend=str(primary),
                failover_enabled=False,
                reason="primary_available",
            )
        replica.mkdir(parents=True, exist_ok=True)
        return StorageFailoverDecision(
            active_backend=str(replica),
            failover_enabled=True,
            reason="primary_unavailable",
            metadata={"primary_root": str(primary)},
        )


def _writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False
