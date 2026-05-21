from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from lotoia.ml.score_ml import InterpretableLinearScoreML, attach_score_ml

DEFAULT_ML_EXPLAINABILITY_DIR = Path("experiments/ml_explainability")
DEFAULT_ML_EXPLAINABILITY_REGISTRY = DEFAULT_ML_EXPLAINABILITY_DIR / "registry.json"


@dataclass(frozen=True)
class MLExplainabilityResult:
    model_version: str
    feature_schema_version: str
    created_at: str
    registry_path: str
    report_path: str
    reproducibility_hash: str
    score_ml: float
    feature_importance: dict[str, float]
    score_contribution: dict[str, float]
    confidence_reasoning: str

    def as_dict(self) -> dict[str, object]:
        return {
            "model_version": self.model_version,
            "feature_schema_version": self.feature_schema_version,
            "created_at": self.created_at,
            "registry_path": self.registry_path,
            "report_path": self.report_path,
            "reproducibility_hash": self.reproducibility_hash,
            "score_ml": self.score_ml,
            "feature_importance": self.feature_importance,
            "score_contribution": self.score_contribution,
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


def _feature_importance_from_attribution(attribution: list[dict[str, object]]) -> dict[str, float]:
    total = sum(abs(float(item.get("contribution", 0.0))) for item in attribution) or 1.0
    return {
        str(item.get("feature", "")): round(abs(float(item.get("contribution", 0.0))) / total, 6)
        for item in attribution
    }


def _score_contribution_from_attribution(attribution: list[dict[str, object]]) -> dict[str, float]:
    return {
        str(item.get("feature", "")): round(float(item.get("contribution", 0.0)), 6)
        for item in attribution
    }


def explain_score_ml_game(
    game: Mapping[str, object],
    *,
    model: InterpretableLinearScoreML | None = None,
    tracking_dir: Path = DEFAULT_ML_EXPLAINABILITY_DIR,
) -> MLExplainabilityResult:
    scorer = model or InterpretableLinearScoreML()
    scored_game = attach_score_ml(dict(game), model=scorer)
    score_details = scored_game["score_ml_details"]
    if not isinstance(score_details, Mapping):
        raise ValueError("score_ml_details must be structured")

    attribution = list(score_details.get("attribution", []))
    if not attribution:
        raise ValueError("score_ml explanation requires attribution payload")

    feature_importance = _feature_importance_from_attribution(attribution)
    score_contribution = _score_contribution_from_attribution(attribution)
    confidence_reasoning = (
        "high confidence"
        if float(score_details.get("score_ml", 0.0)) >= 50.0 and dict(score_details.get("calibration", {})).get("status") == "active"
        else "governed runtime confidence"
    )
    created_at = _now()
    report_payload = {
        "schema_version": "ml-explainability-v0.1.0",
        "model_version": scorer.model_version,
        "feature_schema_version": scorer.feature_schema_version,
        "created_at": created_at,
        "score_ml": float(score_details["score_ml"]),
        "features": dict(score_details["features"]),
        "feature_importance": feature_importance,
        "score_contribution": score_contribution,
        "confidence_reasoning": confidence_reasoning,
        "calibration": dict(score_details["calibration"]),
    }
    report_payload["reproducibility_hash"] = _payload_hash(report_payload)
    report_path = tracking_dir / "explainability_report.json"
    registry_path = tracking_dir / "registry.json"
    _write_json(report_path, report_payload)

    registry = _read_json(registry_path)
    runs = [run for run in registry.get("executed_runs", []) if isinstance(run, Mapping)]
    runs = [run for run in runs if run.get("reproducibility_hash") != report_payload["reproducibility_hash"]]
    registry_entry = {
        "model_version": scorer.model_version,
        "feature_schema_version": scorer.feature_schema_version,
        "created_at": created_at,
        "report_path": str(report_path).replace("\\", "/"),
        "reproducibility_hash": report_payload["reproducibility_hash"],
    }
    runs.append(registry_entry)
    registry["registry_version"] = "ml-explainability-v0.1.0"
    registry["executed_runs"] = runs
    _write_json(registry_path, registry)

    return MLExplainabilityResult(
        model_version=scorer.model_version,
        feature_schema_version=scorer.feature_schema_version,
        created_at=created_at,
        registry_path=str(registry_path),
        report_path=str(report_path),
        reproducibility_hash=str(report_payload["reproducibility_hash"]),
        score_ml=float(score_details["score_ml"]),
        feature_importance=feature_importance,
        score_contribution=score_contribution,
        confidence_reasoning=confidence_reasoning,
    )
