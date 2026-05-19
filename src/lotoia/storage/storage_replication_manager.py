"""Storage replication manager for local and future cloud backends."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .distributed_artifact_store import DistributedArtifactStore


@dataclass(frozen=True, slots=True)
class ReplicationResult:
    """Result of one storage replication cycle."""

    source_root: str
    target_root: str
    copied_count: int
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


class StorageReplicationManager:
    """Replicate artifacts and manifests between storage roots."""

    def __init__(self, store: DistributedArtifactStore) -> None:
        self.store = store

    def replicate_to(self, target_root: str | Path) -> ReplicationResult:
        """Replicate local artifacts to a target root."""

        target = Path(target_root)
        copied = 0
        for source in self.store.root.rglob("*"):
            if not source.is_file():
                continue
            relative = source.relative_to(self.store.root)
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            copied += 1
        return ReplicationResult(
            source_root=str(self.store.root),
            target_root=str(target),
            copied_count=copied,
            metadata={"backend": "local", "cloud_ready": True},
        )
