"""Persistence synchronization engine for distributed operational artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lotoia.storage import (
    DistributedArtifactStore,
    OperationalSnapshotStore,
    StorageFailoverController,
    StorageReplicationManager,
)

from .distributed_persistence_report import DistributedPersistenceReport


class PersistenceSyncEngine:
    """Persist snapshots, replicate artifacts, run backups, and emit observability."""

    def __init__(
        self,
        *,
        artifact_store: DistributedArtifactStore,
        snapshot_store: OperationalSnapshotStore,
        replication_manager: StorageReplicationManager,
        failover_controller: StorageFailoverController,
        replica_root: str | Path = "infra/storage/replication",
        backup_root: str | Path = "infra/storage/backups",
    ) -> None:
        self.artifact_store = artifact_store
        self.snapshot_store = snapshot_store
        self.replication_manager = replication_manager
        self.failover_controller = failover_controller
        self.replica_root = Path(replica_root)
        self.backup_root = Path(backup_root)

    def sync(
        self,
        *,
        payload: dict[str, Any],
        snapshot_type: str = "runtime",
        metadata: dict[str, Any] | None = None,
        metrics: Any | None = None,
    ) -> DistributedPersistenceReport:
        """Run one persistence synchronization cycle."""

        snapshot = self.snapshot_store.persist(
            snapshot_type=snapshot_type,
            payload=payload,
            metadata=metadata,
        )
        replication = self.replication_manager.replicate_to(self.replica_root)
        backup_files = self.artifact_store.backup_to(self.backup_root)
        failover = self.failover_controller.decide(
            primary_root=self.artifact_store.root,
            replica_root=self.replica_root,
        )
        report = DistributedPersistenceReport(
            snapshot_id=snapshot.snapshot_id,
            artifact_id=snapshot.artifact.artifact_id,
            replicated_count=replication.copied_count,
            backup_count=len(backup_files),
            failover_enabled=failover.failover_enabled,
            active_backend=failover.active_backend,
            metadata={
                "snapshot_type": snapshot_type,
                "replication": replication.metadata,
                "failover_reason": failover.reason,
                **(metadata or {}),
            },
        )
        if metrics is not None:
            for name, value in report.summary_metrics().items():
                metrics.gauge(name, value, labels={"source": "persistence_sync"})
        return report
