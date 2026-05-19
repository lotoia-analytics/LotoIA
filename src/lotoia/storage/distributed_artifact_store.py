"""Distributed artifact store foundation for local and future cloud storage."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class DistributedArtifact:
    """Stored artifact metadata."""

    artifact_id: str
    logical_name: str
    storage_uri: str
    checksum_sha256: str
    size_bytes: int
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-ready artifact metadata."""

        return _to_jsonable(self)


class DistributedArtifactStore:
    """Local distributed-artifact abstraction prepared for B2/S3 adapters."""

    def __init__(self, root: str | Path = "infra/storage/local") -> None:
        self.root = Path(root)
        self.artifact_dir = self.root / "artifacts"
        self.manifest_dir = self.root / "manifests"
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_dir.mkdir(parents=True, exist_ok=True)

    def put_bytes(
        self,
        logical_name: str,
        payload: bytes,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> DistributedArtifact:
        """Persist bytes as a distributed artifact."""

        artifact_id = f"artifact-{uuid4().hex}"
        path = self.artifact_dir / artifact_id
        path.write_bytes(payload)
        artifact = DistributedArtifact(
            artifact_id=artifact_id,
            logical_name=logical_name,
            storage_uri=str(path),
            checksum_sha256=hashlib.sha256(payload).hexdigest(),
            size_bytes=len(payload),
            created_at=datetime.now(UTC),
            metadata={
                "backend": "local",
                "cloud_ready": True,
                **(metadata or {}),
            },
        )
        self._write_manifest(artifact)
        return artifact

    def put_file(
        self,
        source_path: str | Path,
        *,
        logical_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DistributedArtifact:
        """Copy a file into the distributed artifact store."""

        source = Path(source_path)
        payload = source.read_bytes()
        artifact = self.put_bytes(
            logical_name or source.name,
            payload,
            metadata={"source_path": str(source), **(metadata or {})},
        )
        return artifact

    def get_bytes(self, artifact_id: str) -> bytes:
        """Read artifact bytes."""

        return (self.artifact_dir / artifact_id).read_bytes()

    def list_artifacts(self) -> tuple[DistributedArtifact, ...]:
        """Return stored artifact metadata."""

        artifacts = []
        for manifest in sorted(self.manifest_dir.glob("*.json")):
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            artifacts.append(
                DistributedArtifact(
                    artifact_id=payload["artifact_id"],
                    logical_name=payload["logical_name"],
                    storage_uri=payload["storage_uri"],
                    checksum_sha256=payload["checksum_sha256"],
                    size_bytes=int(payload["size_bytes"]),
                    created_at=datetime.fromisoformat(payload["created_at"]),
                    metadata=payload.get("metadata", {}),
                )
            )
        return tuple(artifacts)

    def backup_to(self, backup_root: str | Path) -> tuple[Path, ...]:
        """Create an incremental backup copy of manifests and artifacts."""

        target = Path(backup_root) / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        target.mkdir(parents=True, exist_ok=True)
        copied = []
        for source in (*self.artifact_dir.glob("*"), *self.manifest_dir.glob("*.json")):
            if source.is_file():
                destination = target / source.name
                shutil.copy2(source, destination)
                copied.append(destination)
        return tuple(copied)

    def _write_manifest(self, artifact: DistributedArtifact) -> None:
        path = self.manifest_dir / f"{artifact.artifact_id}.json"
        path.write_text(json.dumps(artifact.to_dict(), indent=2, sort_keys=True), encoding="utf-8")


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
