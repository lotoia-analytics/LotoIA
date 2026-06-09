from __future__ import annotations

from dataclasses import dataclass, field

from lotoia.ml.score_ml import ML_RUNTIME_STATE, ml_heartbeat


@dataclass(frozen=True)
class MLRuntimeIsolationContract:
    analytics_runtime: str = "statistical"
    ml_runtime: str = "isolated"
    inference_runtime: str = "governed"
    runtime_state: dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "analytics_runtime": self.analytics_runtime,
            "ml_runtime": self.ml_runtime,
            "inference_runtime": self.inference_runtime,
            "runtime_state": dict(self.runtime_state),
        }


def describe_ml_runtime_isolation() -> MLRuntimeIsolationContract:
    return MLRuntimeIsolationContract(
        runtime_state={
            "ml_runtime_status": ML_RUNTIME_STATE.get("status", "idle"),
            "engine_version": ML_RUNTIME_STATE.get("engine_version"),
            "model_version": ML_RUNTIME_STATE.get("model_version"),
            "calibration_loaded": bool(ML_RUNTIME_STATE.get("calibration_loaded", False)),
            "snapshot_loaded": bool(ML_RUNTIME_STATE.get("snapshot_loaded", False)),
        }
    )


def get_isolated_ml_runtime_state() -> dict[str, object]:
    return {
        "contract": describe_ml_runtime_isolation().as_dict(),
        "heartbeat": ml_heartbeat(),
    }
