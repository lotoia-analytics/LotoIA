from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

DEFAULT_ML_FEATURE_LINEAGE_DIR = Path("experiments/ml_feature_lineage")
DEFAULT_ML_FEATURE_LINEAGE_REGISTRY = DEFAULT_ML_FEATURE_LINEAGE_DIR / "registry.json"


@dataclass(frozen=True)
class MLFeatureLineageResult:
    dataset_version: str
    created_at: str
    registry_path: str
    manifest_path: str
    feature_count: int
    reproducibility_hash: str

    def as_dict(self) -> dict[str, object]:
        return {
            "dataset_version": self.dataset_version,
            "created_at": self.created_at,
            "registry_path": self.registry_path,
            "manifest_path": self.manifest_path,
            "feature_count": self.feature_count,
            "reproducibility_hash": self.reproducibility_hash,
        }


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _payload_hash(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def _normalize_features(features: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    lineage_rows: list[dict[str, object]] = []
    for feature in features:
        lineage_rows.append(
            {
                "name": str(feature.get("name", "")),
                "dtype": str(feature.get("dtype", "")),
                "source": str(feature.get("source", "")),
                "temporal_scope": str(feature.get("temporal_scope", "")),
                "uses_label_contest": bool(feature.get("uses_label_contest", False)),
                "description": str(feature.get("description", "")),
            }
        )
    return lineage_rows


def build_feature_lineage(
    feature_manifest: Mapping[str, object],
    dataset_manifest: Mapping[str, object],
    *,
    tracking_dir: Path = DEFAULT_ML_FEATURE_LINEAGE_DIR,
) -> MLFeatureLineageResult:
    features = feature_manifest.get("features", [])
    if not isinstance(features, Sequence) or isinstance(features, str):
        raise ValueError("feature manifest must declare a sequence of features")
    normalized_features = _normalize_features([feature for feature in features if isinstance(feature, Mapping)])
    created_at = _now()
    dataset_version = str(dataset_manifest.get("dataset_version") or feature_manifest.get("dataset_version") or "unknown")

    manifest_payload = {
        "schema_version": "ml-feature-lineage-v0.1.0",
        "dataset_version": dataset_version,
        "created_at": created_at,
        "feature_manifest_id": str(feature_manifest.get("manifest_id", "")),
        "dataset_manifest_id": str(dataset_manifest.get("dataset_id", "")),
        "source_snapshot_path": str(dataset_manifest.get("source_snapshot", {}).get("path", "")) if isinstance(dataset_manifest.get("source_snapshot"), Mapping) else "",
        "lineage": normalized_features,
    }
    manifest_payload["reproducibility_hash"] = _payload_hash(manifest_payload)
    manifest_path = tracking_dir / "feature_lineage_manifest.json"
    registry_path = tracking_dir / "registry.json"
    _write_json(manifest_path, manifest_payload)

    registry = _read_json(registry_path) if registry_path.exists() else {}
    runs = [run for run in registry.get("executed_runs", []) if isinstance(run, Mapping)]
    runs = [run for run in runs if run.get("dataset_version") != dataset_version]
    registry_entry = {
        "dataset_version": dataset_version,
        "created_at": created_at,
        "manifest_path": str(manifest_path).replace("\\", "/"),
        "reproducibility_hash": manifest_payload["reproducibility_hash"],
        "feature_count": len(normalized_features),
    }
    runs.append(registry_entry)
    registry["registry_version"] = "ml-feature-lineage-v0.1.0"
    registry["executed_runs"] = runs
    _write_json(registry_path, registry)

    return MLFeatureLineageResult(
        dataset_version=dataset_version,
        created_at=created_at,
        registry_path=str(registry_path),
        manifest_path=str(manifest_path),
        feature_count=len(normalized_features),
        reproducibility_hash=str(manifest_payload["reproducibility_hash"]),
    )
