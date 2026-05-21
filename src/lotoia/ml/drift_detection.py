from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from statistics import mean

DEFAULT_ML_DRIFT_DETECTION_DIR = Path("experiments/ml_drift")
DEFAULT_ML_DRIFT_DETECTION_REGISTRY = DEFAULT_ML_DRIFT_DETECTION_DIR / "registry.json"


@dataclass(frozen=True)
class MLDriftDetectionResult:
    model_version: str
    dataset_version: str
    created_at: str
    registry_path: str
    report_path: str
    reproducibility_hash: str
    drift_statistical: float
    drift_temporal: float
    drift_structural: float
    confidence_state: str
    confidence_reasoning: str

    def as_dict(self) -> dict[str, object]:
        return {
            "model_version": self.model_version,
            "dataset_version": self.dataset_version,
            "created_at": self.created_at,
            "registry_path": self.registry_path,
            "report_path": self.report_path,
            "reproducibility_hash": self.reproducibility_hash,
            "drift_statistical": self.drift_statistical,
            "drift_temporal": self.drift_temporal,
            "drift_structural": self.drift_structural,
            "confidence_state": self.confidence_state,
            "confidence_reasoning": self.confidence_reasoning,
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


def _normalize_series(values: Sequence[float]) -> list[float]:
    return [float(value) for value in values]


def detect_ml_drift(
    *,
    model_version: str,
    dataset_version: str,
    baseline_scores: Sequence[float],
    current_scores: Sequence[float],
    baseline_timestamps: Sequence[str] | None = None,
    current_timestamps: Sequence[str] | None = None,
    structural_signals: Mapping[str, float] | None = None,
    tracking_dir: Path = DEFAULT_ML_DRIFT_DETECTION_DIR,
) -> MLDriftDetectionResult:
    if not baseline_scores:
        raise ValueError("baseline_scores must not be empty")
    if not current_scores:
        raise ValueError("current_scores must not be empty")

    baseline = _normalize_series(baseline_scores)
    current = _normalize_series(current_scores)
    drift_statistical = abs(mean(current) - mean(baseline)) / max(abs(mean(baseline)), 1.0)
    drift_temporal = 0.0
    if baseline_timestamps and current_timestamps:
        drift_temporal = abs(len(current_timestamps) - len(baseline_timestamps)) / max(
            max(len(baseline_timestamps), len(current_timestamps)), 1
        )
    structural = dict(structural_signals or {})
    drift_structural = sum(abs(float(value)) for value in structural.values()) / max(len(structural), 1)

    if drift_statistical < 0.05 and drift_temporal < 0.05 and drift_structural < 0.05:
        confidence_state = "stable"
        confidence_reasoning = "statistical, temporal, and structural drift remain low"
    elif drift_statistical < 0.15 and drift_temporal < 0.15 and drift_structural < 0.15:
        confidence_state = "watch"
        confidence_reasoning = "drift remains moderate and should be monitored"
    else:
        confidence_state = "alert"
        confidence_reasoning = "drift increased beyond governed tolerances"

    created_at = _now()
    report_payload = {
        "schema_version": "ml-drift-detection-v0.1.0",
        "model_version": model_version,
        "dataset_version": dataset_version,
        "created_at": created_at,
        "baseline_scores": baseline,
        "current_scores": current,
        "baseline_timestamps": list(baseline_timestamps or []),
        "current_timestamps": list(current_timestamps or []),
        "structural_signals": structural,
        "drift_statistical": drift_statistical,
        "drift_temporal": drift_temporal,
        "drift_structural": drift_structural,
        "confidence_state": confidence_state,
        "confidence_reasoning": confidence_reasoning,
    }
    report_payload["reproducibility_hash"] = _payload_hash(report_payload)
    report_path = tracking_dir / "drift_report.json"
    registry_path = tracking_dir / "registry.json"
    _write_json(report_path, report_payload)

    registry = _read_json(registry_path)
    runs = [run for run in registry.get("executed_runs", []) if isinstance(run, Mapping)]
    runs = [run for run in runs if run.get("model_version") != model_version or run.get("dataset_version") != dataset_version]
    registry_entry = {
        "model_version": model_version,
        "dataset_version": dataset_version,
        "created_at": created_at,
        "report_path": str(report_path).replace("\\", "/"),
        "reproducibility_hash": report_payload["reproducibility_hash"],
        "confidence_state": confidence_state,
    }
    runs.append(registry_entry)
    registry["registry_version"] = "ml-drift-detection-v0.1.0"
    registry["executed_runs"] = runs
    _write_json(registry_path, registry)

    return MLDriftDetectionResult(
        model_version=model_version,
        dataset_version=dataset_version,
        created_at=created_at,
        registry_path=str(registry_path),
        report_path=str(report_path),
        reproducibility_hash=str(report_payload["reproducibility_hash"]),
        drift_statistical=drift_statistical,
        drift_temporal=drift_temporal,
        drift_structural=drift_structural,
        confidence_state=confidence_state,
        confidence_reasoning=confidence_reasoning,
    )
