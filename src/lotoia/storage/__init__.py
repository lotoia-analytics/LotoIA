"""Distributed operational storage foundation for LotoIA."""

from .distributed_artifact_store import DistributedArtifact, DistributedArtifactStore
from .operational_snapshot_store import OperationalSnapshot, OperationalSnapshotStore
from .storage_failover_controller import StorageFailoverController, StorageFailoverDecision
from .storage_replication_manager import ReplicationResult, StorageReplicationManager

__all__ = [
    "DistributedArtifact",
    "DistributedArtifactStore",
    "OperationalSnapshot",
    "OperationalSnapshotStore",
    "ReplicationResult",
    "StorageFailoverController",
    "StorageFailoverDecision",
    "StorageReplicationManager",
]
