from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

DEFAULT_ML_MODEL_REGISTRY_DIR = Path("experiments/ml_models")
DEFAULT_ML_MODEL_REGISTRY_PATH = DEFAULT_ML_MODEL_REGISTRY_DIR / "registry.json"


@dataclass(frozen=True)
class MLModelRegistryResult:
    model_id: str
    model_version: str
    created_at: str
    registry_path: str
    version_count: int
    active_version: str
    rollback_version: str | None
    reproducibility_hash: str

    def as_dict(self) -> dict[str, object]:
        return {
            "model_id": self.model_id,
            "model_version": self.model_version,
            "created_at": self.created_at,
            "registry_path": self.registry_path,
            "version_count": self.version_count,
            "active_version": self.active_version,
            "rollback_version": self.rollback_version,
            "reproducibility_hash": self.reproducibility_hash,
        }


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _payload_hash(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def register_model_version(
    *,
    model_id: str,
    model_version: str,
    dataset_version: str,
    calibration_version: str,
    status: str = "candidate",
    registry_path: Path = DEFAULT_ML_MODEL_REGISTRY_PATH,
) -> MLModelRegistryResult:
    created_at = _now()
    registry = _read_json(registry_path)
    versions = [item for item in registry.get("versions", []) if isinstance(item, Mapping)]
    versions = [item for item in versions if item.get("model_version") != model_version or item.get("model_id") != model_id]

    entry = {
        "model_id": model_id,
        "model_version": model_version,
        "dataset_version": dataset_version,
        "calibration_version": calibration_version,
        "status": status,
        "created_at": created_at,
    }
    versions.append(entry)

    active_version = model_version
    registry_payload = {
        "registry_version": "ml-model-registry-v0.1.0",
        "model_id": model_id,
        "active_version": active_version,
        "versions": versions,
    }
    registry_payload["reproducibility_hash"] = _payload_hash(registry_payload)
    _write_json(registry_path, registry_payload)

    return MLModelRegistryResult(
        model_id=model_id,
        model_version=model_version,
        created_at=created_at,
        registry_path=str(registry_path),
        version_count=len(versions),
        active_version=active_version,
        rollback_version=None,
        reproducibility_hash=str(registry_payload["reproducibility_hash"]),
    )


def activate_model_version(
    *,
    model_id: str,
    model_version: str,
    registry_path: Path = DEFAULT_ML_MODEL_REGISTRY_PATH,
) -> MLModelRegistryResult:
    registry = _read_json(registry_path)
    versions = [item for item in registry.get("versions", []) if isinstance(item, Mapping)]
    matching = [item for item in versions if item.get("model_id") == model_id and item.get("model_version") == model_version]
    if not matching:
        raise ValueError(f"model version not registered: {model_id}:{model_version}")

    registry["active_version"] = model_version
    registry["registry_version"] = registry.get("registry_version", "ml-model-registry-v0.1.0")
    registry["reproducibility_hash"] = _payload_hash(registry)
    _write_json(registry_path, registry)
    created_at = _now()
    return MLModelRegistryResult(
        model_id=model_id,
        model_version=model_version,
        created_at=created_at,
        registry_path=str(registry_path),
        version_count=len(versions),
        active_version=model_version,
        rollback_version=None,
        reproducibility_hash=str(registry["reproducibility_hash"]),
    )


def rollback_model_version(
    *,
    model_id: str,
    target_version: str,
    registry_path: Path = DEFAULT_ML_MODEL_REGISTRY_PATH,
) -> MLModelRegistryResult:
    registry = _read_json(registry_path)
    versions = [item for item in registry.get("versions", []) if isinstance(item, Mapping)]
    matching = [item for item in versions if item.get("model_id") == model_id and item.get("model_version") == target_version]
    if not matching:
        raise ValueError(f"rollback target not registered: {model_id}:{target_version}")

    previous_version = str(registry.get("active_version") or "")
    registry["active_version"] = target_version
    registry["registry_version"] = registry.get("registry_version", "ml-model-registry-v0.1.0")
    registry["reproducibility_hash"] = _payload_hash(registry)
    _write_json(registry_path, registry)
    created_at = _now()
    return MLModelRegistryResult(
        model_id=model_id,
        model_version=target_version,
        created_at=created_at,
        registry_path=str(registry_path),
        version_count=len(versions),
        active_version=target_version,
        rollback_version=previous_version or None,
        reproducibility_hash=str(registry["reproducibility_hash"]),
    )
