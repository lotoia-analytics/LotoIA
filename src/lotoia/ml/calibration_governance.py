from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

DEFAULT_ML_CALIBRATION_GOVERNANCE_DIR = Path("experiments/ml_calibration")
DEFAULT_ML_CALIBRATION_GOVERNANCE_REGISTRY = DEFAULT_ML_CALIBRATION_GOVERNANCE_DIR / "registry.json"


@dataclass(frozen=True)
class MLCalibrationGovernanceResult:
    model_version: str
    dataset_version: str
    calibration_version: str
    created_at: str
    registry_path: str
    snapshot_path: str
    reproducibility_hash: str
    confidence_tracking: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return {
            "model_version": self.model_version,
            "dataset_version": self.dataset_version,
            "calibration_version": self.calibration_version,
            "created_at": self.created_at,
            "registry_path": self.registry_path,
            "snapshot_path": self.snapshot_path,
            "reproducibility_hash": self.reproducibility_hash,
            "confidence_tracking": self.confidence_tracking,
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


def register_calibration_snapshot(
    *,
    model_version: str,
    dataset_version: str,
    calibration: Mapping[str, object],
    feature_lineage_hash: str | None = None,
    tracking_dir: Path = DEFAULT_ML_CALIBRATION_GOVERNANCE_DIR,
) -> MLCalibrationGovernanceResult:
    created_at = _now()
    calibration_version = str(calibration.get("version") or calibration.get("calibration_version") or model_version)
    snapshot_path = tracking_dir / "snapshots" / f"{model_version}.json"
    registry_path = tracking_dir / "registry.json"
    confidence_tracking = {
        "calibration_loaded": True,
        "snapshot_loaded": True,
        "confidence_reasoning": "calibration snapshot persisted with institutional lineage",
        "feature_lineage_hash": feature_lineage_hash,
    }
    snapshot_payload = {
        "schema_version": "ml-calibration-governance-v0.1.0",
        "model_version": model_version,
        "dataset_version": dataset_version,
        "calibration_version": calibration_version,
        "created_at": created_at,
        "calibration": dict(calibration),
        "confidence_tracking": confidence_tracking,
    }
    snapshot_payload["reproducibility_hash"] = _payload_hash(snapshot_payload)
    _write_json(snapshot_path, snapshot_payload)

    registry = _read_json(registry_path)
    snapshots = [item for item in registry.get("snapshots", []) if isinstance(item, Mapping)]
    snapshots = [item for item in snapshots if item.get("model_version") != model_version]
    registry_entry = {
        "model_version": model_version,
        "dataset_version": dataset_version,
        "calibration_version": calibration_version,
        "created_at": created_at,
        "snapshot_path": str(snapshot_path).replace("\\", "/"),
        "reproducibility_hash": snapshot_payload["reproducibility_hash"],
    }
    snapshots.append(registry_entry)
    registry["registry_version"] = "ml-calibration-governance-v0.1.0"
    registry["snapshots"] = snapshots
    _write_json(registry_path, registry)

    return MLCalibrationGovernanceResult(
        model_version=model_version,
        dataset_version=dataset_version,
        calibration_version=calibration_version,
        created_at=created_at,
        registry_path=str(registry_path),
        snapshot_path=str(snapshot_path),
        reproducibility_hash=str(snapshot_payload["reproducibility_hash"]),
        confidence_tracking=confidence_tracking,
    )
