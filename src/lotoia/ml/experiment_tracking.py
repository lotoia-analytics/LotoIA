from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

DEFAULT_ML_EXPERIMENT_TRACKING_DIR = Path("experiments/ml_governance")
DEFAULT_ML_EXPERIMENT_TRACKING_REGISTRY = DEFAULT_ML_EXPERIMENT_TRACKING_DIR / "registry.json"


@dataclass(frozen=True)
class MLExperimentTrackingResult:
    experiment_id: str
    run_id: str
    created_at: str
    manifest_path: str
    registry_path: str
    reproducibility_hash: str
    dataset_version: str
    model_version: str
    hyperparameters: dict[str, object]
    metrics: dict[str, float]
    artifacts: dict[str, str]

    def as_dict(self) -> dict[str, object]:
        return {
            "experiment_id": self.experiment_id,
            "run_id": self.run_id,
            "created_at": self.created_at,
            "manifest_path": self.manifest_path,
            "registry_path": self.registry_path,
            "reproducibility_hash": self.reproducibility_hash,
            "dataset_version": self.dataset_version,
            "model_version": self.model_version,
            "hyperparameters": self.hyperparameters,
            "metrics": self.metrics,
            "artifacts": self.artifacts,
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


def _normalize_artifacts(artifacts: Mapping[str, object] | None) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in dict(artifacts or {}).items():
        normalized[str(key)] = str(value)
    return normalized


def track_ml_experiment(
    *,
    experiment_id: str,
    dataset_version: str,
    model_version: str,
    hyperparameters: Mapping[str, object],
    metrics: Mapping[str, float],
    artifacts: Mapping[str, object] | None = None,
    tracking_dir: Path = DEFAULT_ML_EXPERIMENT_TRACKING_DIR,
) -> MLExperimentTrackingResult:
    created_at = _now()
    run_id = sha256(
        f"{experiment_id}:{dataset_version}:{model_version}:{created_at}".encode("utf-8")
    ).hexdigest()[:16]
    normalized_hyperparameters = {str(key): value for key, value in hyperparameters.items()}
    normalized_metrics = {str(key): float(value) for key, value in metrics.items()}
    normalized_artifacts = _normalize_artifacts(artifacts)
    manifest_path = tracking_dir / "runs" / f"{run_id}.json"
    registry_path = tracking_dir / "registry.json"
    manifest_payload = {
        "experiment_id": experiment_id,
        "run_id": run_id,
        "created_at": created_at,
        "dataset_version": dataset_version,
        "model_version": model_version,
        "hyperparameters": normalized_hyperparameters,
        "metrics": normalized_metrics,
        "artifacts": normalized_artifacts,
    }
    manifest_payload["reproducibility_hash"] = _payload_hash(manifest_payload)
    _write_json(manifest_path, manifest_payload)

    registry = _read_json(registry_path)
    runs = [run for run in registry.get("executed_runs", []) if isinstance(run, Mapping)]
    runs = [run for run in runs if run.get("run_id") != run_id]
    registry_entry = {
        "experiment_id": experiment_id,
        "run_id": run_id,
        "created_at": created_at,
        "dataset_version": dataset_version,
        "model_version": model_version,
        "manifest_path": str(manifest_path).replace("\\", "/"),
        "reproducibility_hash": manifest_payload["reproducibility_hash"],
    }
    runs.append(registry_entry)
    registry["executed_runs"] = runs
    registry["registry_version"] = "ml-governance-v0.1.0"
    _write_json(registry_path, registry)

    return MLExperimentTrackingResult(
        experiment_id=experiment_id,
        run_id=run_id,
        created_at=created_at,
        manifest_path=str(manifest_path),
        registry_path=str(registry_path),
        reproducibility_hash=str(manifest_payload["reproducibility_hash"]),
        dataset_version=dataset_version,
        model_version=model_version,
        hyperparameters=normalized_hyperparameters,
        metrics=normalized_metrics,
        artifacts=normalized_artifacts,
    )
