"""Operational snapshot persistence for runtime, governance, and observability."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from lotoia.standards import ArtifactKind, artifact_name, metadata_envelope

from .distributed_artifact_store import DistributedArtifact, DistributedArtifactStore


@dataclass(frozen=True, slots=True)
class OperationalSnapshot:
    """One persisted operational snapshot."""

    snapshot_id: str
    created_at: datetime
    artifact: DistributedArtifact
    snapshot_type: str
    metadata: dict[str, Any] = field(default_factory=dict)


class OperationalSnapshotStore:
    """Persist operational snapshots through the distributed artifact store."""

    def __init__(self, artifact_store: DistributedArtifactStore) -> None:
        self.artifact_store = artifact_store

    def persist(
        self,
        *,
        snapshot_type: str,
        payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> OperationalSnapshot:
        """Persist a JSON operational snapshot."""

        import json

        created_at = datetime.now(UTC)
        snapshot_id = f"snapshot-{uuid4().hex}"
        envelope = metadata_envelope(
            artifact_type=ArtifactKind.SNAPSHOT,
            name=snapshot_type,
            context={"snapshot_id": snapshot_id, **(metadata or {})},
            created_at=created_at.isoformat().replace("+00:00", "Z"),
        )
        artifact = self.artifact_store.put_bytes(
            artifact_name(ArtifactKind.SNAPSHOT, snapshot_type, "json"),
            json.dumps({"metadata": envelope, "payload": payload}, indent=2, sort_keys=True, default=str).encode("utf-8"),
            metadata={"snapshot_id": snapshot_id, "snapshot_type": snapshot_type, **envelope, **(metadata or {})},
        )
        return OperationalSnapshot(
            snapshot_id=snapshot_id,
            created_at=created_at,
            artifact=artifact,
            snapshot_type=snapshot_type,
            metadata=envelope,
        )
