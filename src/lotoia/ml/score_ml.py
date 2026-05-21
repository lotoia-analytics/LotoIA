from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Any
from datetime import UTC, datetime

SCORE_ML_MODEL_VERSION = "historical_recalibrated_v2"
SCORE_ML_FEATURE_SCHEMA_VERSION = "score-ml-features-v0.1.0"

OFFICIAL_FEATURES = (
    "final_score_norm",
    "quadra_density",
    "sum_balance",
    "odd_balance",
    "center_balance",
    "frame_balance",
)

DEFAULT_LINEAR_WEIGHTS = {
    "final_score_norm": 0.35,
    "quadra_density": 0.20,
    "sum_balance": 0.15,
    "odd_balance": 0.10,
    "center_balance": 0.10,
    "frame_balance": 0.10,
}

DEFAULT_CALIBRATION = {
    "type": "interpretable_linear_supervised_baseline",
    "version": SCORE_ML_MODEL_VERSION,
    "status": "active",
    "source": "runtime_default",
    "training_summary": {"mode": "institutional_default"},
}

ML_RUNTIME_TRACE: list[dict[str, object]] = []
ML_RUNTIME_STATE: dict[str, object] = {
    "status": "idle",
    "engine_version": SCORE_ML_MODEL_VERSION,
    "model_version": SCORE_ML_MODEL_VERSION,
    "calibration_loaded": False,
    "snapshot_loaded": False,
    "fallback_used": False,
    "last_update": "",
}


@dataclass(frozen=True)
class FeatureAttribution:
    feature: str
    value: float
    coefficient: float
    contribution: float

    def as_dict(self) -> dict[str, float | str]:
        return {
            "feature": self.feature,
            "value": self.value,
            "coefficient": self.coefficient,
            "contribution": self.contribution,
        }


@dataclass(frozen=True)
class ScoreMLResult:
    score_ml: float
    model_version: str
    feature_schema_version: str
    features: dict[str, float]
    attribution: tuple[FeatureAttribution, ...]
    calibration: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return {
            "score_ml": self.score_ml,
            "model_version": self.model_version,
            "feature_schema_version": self.feature_schema_version,
            "features": self.features,
            "attribution": [item.as_dict() for item in self.attribution],
            "calibration": self.calibration,
        }


@dataclass(frozen=True)
class InterpretableLinearScoreML:
    """Small supervised rerank baseline with explicit coefficients."""

    model_version: str = SCORE_ML_MODEL_VERSION
    feature_schema_version: str = SCORE_ML_FEATURE_SCHEMA_VERSION
    weights: Mapping[str, float] | None = None
    intercept: float = 0.0
    training_summary: Mapping[str, object] | None = None
    calibration: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "calibration", _normalize_calibration(self.calibration, self.model_version))
        _trace_ml("ML_LOAD_MODEL", status="ok", model_version=self.model_version)
        _trace_ml("ML_LOAD_CALIBRATION", status="ok", calibration_loaded=True)

    def _weights(self) -> dict[str, float]:
        raw_weights = dict(self.weights or DEFAULT_LINEAR_WEIGHTS)
        missing = sorted(set(OFFICIAL_FEATURES) - set(raw_weights))
        if missing:
            raise ValueError("score_ml model missing coefficients: " + ", ".join(missing))
        total = sum(max(0.0, float(raw_weights[feature])) for feature in OFFICIAL_FEATURES)
        if total <= 0:
            raise ValueError("score_ml coefficients must contain positive weight")
        return {feature: max(0.0, float(raw_weights[feature])) / total for feature in OFFICIAL_FEATURES}

    def score(self, game: Mapping[str, Any]) -> ScoreMLResult:
        features = extract_score_ml_features(game)
        weights = self._weights()
        contributions = {
            feature: weights[feature] * features[feature] * 100.0 for feature in OFFICIAL_FEATURES
        }
        score = self.intercept + sum(contributions.values())
        score = round(_clamp(score, 0.0, 100.0), 6)
        attribution = tuple(
            FeatureAttribution(
                feature=feature,
                value=round(features[feature], 6),
                coefficient=round(weights[feature], 6),
                contribution=round(contributions[feature], 6),
            )
            for feature in sorted(OFFICIAL_FEATURES, key=lambda name: abs(contributions[name]), reverse=True)
        )
        return ScoreMLResult(
            score_ml=score,
            model_version=self.model_version,
            feature_schema_version=self.feature_schema_version,
            features={feature: round(features[feature], 6) for feature in OFFICIAL_FEATURES},
            attribution=attribution,
            calibration={
                **dict(self.calibration or DEFAULT_CALIBRATION),
                "intercept": self.intercept,
                "training_summary": dict(self.training_summary or {"mode": "institutional_default"}),
            },
        )


def _normalize_calibration(
    calibration: Mapping[str, object] | None,
    model_version: str,
) -> dict[str, object]:
    payload = dict(DEFAULT_CALIBRATION)
    if calibration:
        payload.update(dict(calibration))
    payload.setdefault("version", model_version)
    payload.setdefault("model_version", model_version)
    payload.setdefault("calibration_version", model_version)
    payload.setdefault("status", "active")
    payload.setdefault("type", "interpretable_linear_supervised_baseline")
    payload.setdefault("training_summary", {"mode": "institutional_default"})
    return payload


def default_calibration_config(model_version: str = SCORE_ML_MODEL_VERSION) -> dict[str, object]:
    return _normalize_calibration(None, model_version)


def _trace_ml(event: str, *, status: str, **payload: object) -> None:
    record = {
        "event": event,
        "status": status,
        "timestamp": datetime.now(UTC).isoformat(),
        **payload,
    }
    ML_RUNTIME_TRACE.append(record)
    ML_RUNTIME_STATE.update(
        {
            "status": "active" if status == "ok" else ML_RUNTIME_STATE.get("status", "degraded"),
            "last_update": record["timestamp"],
            **{key: value for key, value in payload.items() if key in ML_RUNTIME_STATE},
        }
    )


def ensure_calibration(model: object, *, model_version: str = SCORE_ML_MODEL_VERSION) -> object:
    _trace_ml("ML_ATTACH_RUNTIME", status="ok", engine_version=model_version)
    if hasattr(model, "calibration"):
        calibration = getattr(model, "calibration")
        if calibration is None:
            object.__setattr__(model, "calibration", default_calibration_config(model_version))
        elif isinstance(calibration, Mapping):
            migrated = _normalize_calibration(calibration, model_version)
            object.__setattr__(model, "calibration", migrated)
    else:
        object.__setattr__(model, "calibration", default_calibration_config(model_version))
    if not getattr(model, "model_version", None):
        object.__setattr__(model, "model_version", model_version)
    _trace_ml("ML_READY", status="ok", calibration_loaded=True, engine_version=model_version)
    return model


def migrate_score_ml_snapshot(snapshot: Mapping[str, Any] | None) -> dict[str, Any]:
    _trace_ml("ML_LOAD_SNAPSHOT", status="ok", snapshot_loaded=True)
    payload = dict(snapshot or {})
    legacy_versions = {None, "", "score-ml-linear-baseline-v0.1.0"}
    payload["model_version"] = (
        SCORE_ML_MODEL_VERSION if payload.get("model_version") in legacy_versions else str(payload.get("model_version"))
    )
    payload["feature_schema_version"] = str(
        payload.get("feature_schema_version") or SCORE_ML_FEATURE_SCHEMA_VERSION
    )
    payload["calibration"] = _normalize_calibration(
        payload.get("calibration") if isinstance(payload.get("calibration"), Mapping) else None,
        payload["model_version"],
    )
    payload.setdefault("calibration_version", payload["model_version"])
    payload.setdefault("engine_version", payload["model_version"])
    payload.setdefault("ml_runtime_status", "active")
    payload.setdefault("fallback_used", False)
    payload.setdefault("ranking_strategy", "historical_recalibrated")
    payload.setdefault("profile_distribution", {})
    return payload


def ml_heartbeat() -> dict[str, object]:
    _trace_ml("ML_HEARTBEAT", status="ok", engine_version=ML_RUNTIME_STATE.get("engine_version", SCORE_ML_MODEL_VERSION))
    return dict(ML_RUNTIME_STATE)


def _clamp(value: float, lower: float, upper: float) -> float:
    if not isfinite(value):
        return lower
    return max(lower, min(upper, value))


def _number(value: object, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _final_score(game: Mapping[str, Any]) -> float:
    final_score = game.get("final_score")
    if isinstance(final_score, Mapping):
        return _number(final_score.get("final_score"))
    return _number(final_score)


def extract_score_ml_features(game: Mapping[str, Any]) -> dict[str, float]:
    """Build leakage-free candidate features from already available game metadata."""

    quadra_score = game.get("quadra_score")
    found_quadras = 0.0
    if isinstance(quadra_score, Mapping):
        found_quadras = _number(quadra_score.get("found_quadras"))

    return {
        "final_score_norm": _clamp(_final_score(game) / 100.0, 0.0, 1.0),
        "quadra_density": _clamp(found_quadras / 10.0, 0.0, 1.0),
        "sum_balance": _clamp(1.0 - abs(_number(game.get("sum"), 205.0) - 205.0) / 35.0, 0.0, 1.0),
        "odd_balance": _clamp(1.0 - abs(_number(game.get("odd"), 7.5) - 7.5) / 7.5, 0.0, 1.0),
        "center_balance": _clamp(1.0 - abs(_number(game.get("center"), 5.0) - 5.0) / 5.0, 0.0, 1.0),
        "frame_balance": _clamp(1.0 - abs(_number(game.get("frame"), 10.0) - 10.0) / 10.0, 0.0, 1.0),
    }


def attach_score_ml(
    game: dict[str, Any],
    *,
    model: InterpretableLinearScoreML | None = None,
) -> dict[str, Any]:
    scorer = ensure_calibration(model or InterpretableLinearScoreML())  # type: ignore[assignment]
    result = scorer.score(game)
    game["score_ml"] = result.score_ml
    game["score_ml_details"] = result.as_dict()
    return game


def score_ml_games(
    games: Sequence[dict[str, Any]],
    *,
    model: InterpretableLinearScoreML | None = None,
) -> list[dict[str, Any]]:
    return [attach_score_ml(game, model=model) for game in games]


def supervised_rerank_games(
    games: Sequence[dict[str, Any]],
    *,
    model: InterpretableLinearScoreML | None = None,
) -> list[dict[str, Any]]:
    scored = score_ml_games(list(games), model=model)
    return sorted(
        scored,
        key=lambda game: (
            -float(game["score_ml"]),
            -_final_score(game),
            tuple(game.get("numbers", ())),
        ),
    )


def calibrate_linear_score_ml(
    rows: Sequence[Mapping[str, object]],
    *,
    target_field: str = "target_hits",
) -> InterpretableLinearScoreML:
    """Create a tiny auditable calibration from governed supervised rows.

    The calibration intentionally avoids opaque fitting. It derives non-negative
    feature weights from absolute covariance against the declared target.
    """

    if not rows:
        raise ValueError("score_ml calibration requires at least one supervised row")

    feature_rows: list[dict[str, float]] = []
    targets: list[float] = []
    for index, row in enumerate(rows):
        if "feature_cutoff_contest" not in row or "label_contest" not in row:
            raise ValueError(f"row {index} must declare temporal supervised boundaries")
        if int(row["feature_cutoff_contest"]) >= int(row["label_contest"]):
            raise ValueError(f"row {index} leaks future information into score_ml calibration")
        if target_field not in row:
            raise ValueError(f"row {index} must declare {target_field}")

        features_payload = row.get("features")
        if not isinstance(features_payload, Mapping):
            raise ValueError(f"row {index} must declare structured features")
        feature_rows.append({feature: _number(features_payload.get(feature)) for feature in OFFICIAL_FEATURES})
        targets.append(_number(row[target_field]))

    target_mean = sum(targets) / len(targets)
    raw_weights: dict[str, float] = {}
    for feature in OFFICIAL_FEATURES:
        feature_values = [row[feature] for row in feature_rows]
        feature_mean = sum(feature_values) / len(feature_values)
        covariance = sum(
            (value - feature_mean) * (target - target_mean)
            for value, target in zip(feature_values, targets, strict=True)
        )
        raw_weights[feature] = abs(covariance)

    if sum(raw_weights.values()) <= 0:
        raw_weights = dict(DEFAULT_LINEAR_WEIGHTS)

    return InterpretableLinearScoreML(
        weights=raw_weights,
        training_summary={
            "mode": "covariance_weighted_supervised_baseline",
            "rows": len(rows),
            "target_field": target_field,
            "feature_schema_version": SCORE_ML_FEATURE_SCHEMA_VERSION,
        },
        calibration={
            "type": "interpretable_linear_supervised_baseline",
            "version": SCORE_ML_MODEL_VERSION,
            "status": "active",
            "source": "calibrated_runtime",
        },
    )
