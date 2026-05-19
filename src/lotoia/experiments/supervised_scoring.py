from __future__ import annotations

from collections.abc import Mapping, Sequence

from lotoia.experiments.temporal_governance import (
    ExperimentConsistencyReport,
    TemporalSplit,
    validate_train_test_separation,
)

SUPERVISED_SCORING_REGISTRY_VERSION = "0.1.0"
SUPERVISED_SCORING_STATUS = "incremental_score_ml_baseline"

REQUIRED_ADR_REFERENCES = (
    "ADR_001",
    "ADR_002",
    "ADR_003",
    "ADR_004",
    "ADR_005",
    "ADR_006",
    "ADR_007",
    "ADR_008",
)

REQUIRED_SCORE_ML_MANIFEST_FIELDS = {
    "manifest_id",
    "schema_version",
    "created_at",
    "adr_references",
    "model",
    "feature_schema",
    "attribution",
    "calibration",
    "temporal_validation",
    "benchmark_comparability",
    "reproducibility",
    "operational_constraints",
}

REQUIRED_REGISTRY_FIELDS = {
    "registry_version",
    "status",
    "created_at",
    "adr_references",
    "score_ml_manifests",
    "models",
    "benchmark_comparability",
}


def _missing_fields(payload: Mapping[str, object], required: set[str], label: str) -> list[str]:
    missing = sorted(required - set(payload))
    return [f"missing {label} fields: {', '.join(missing)}"] if missing else []


def _validate_adr_references(payload: Mapping[str, object]) -> list[str]:
    adr_references = payload.get("adr_references")
    if not isinstance(adr_references, Sequence) or isinstance(adr_references, str):
        return ["adr_references must be a sequence"]

    missing = [
        adr
        for adr in REQUIRED_ADR_REFERENCES
        if not any(str(reference).startswith(adr) for reference in adr_references)
    ]
    if missing:
        return ["adr_references must include ADR_001 through ADR_008"]
    return []


def validate_score_ml_rows(rows: Sequence[Mapping[str, object]]) -> ExperimentConsistencyReport:
    errors: list[str] = []
    sample_ids: list[str] = []

    for index, row in enumerate(rows):
        if "sample_id" in row:
            sample_ids.append(str(row["sample_id"]))

        for field in ("feature_cutoff_contest", "scoring_contest"):
            if field not in row:
                errors.append(f"row {index} must declare {field}")

        if "feature_cutoff_contest" not in row or "scoring_contest" not in row:
            continue

        feature_cutoff = row["feature_cutoff_contest"]
        scoring_contest = row["scoring_contest"]
        if not isinstance(feature_cutoff, int) or not isinstance(scoring_contest, int):
            errors.append(f"row {index} score_ml temporal boundaries must be integers")
            continue
        if feature_cutoff < 1 or scoring_contest < 1:
            errors.append(f"row {index} score_ml temporal boundaries must be positive")
        if feature_cutoff >= scoring_contest:
            errors.append(f"row {index} leaks future information into score_ml features")

        label_contest = row.get("label_contest")
        if label_contest is not None:
            if not isinstance(label_contest, int):
                errors.append(f"row {index} label_contest must be an integer")
            elif feature_cutoff >= label_contest:
                errors.append(f"row {index} label_contest must occur after feature cutoff")

        if "score_ml" in row:
            score = row["score_ml"]
            if not isinstance(score, (int, float)) or not 0 <= float(score) <= 100:
                errors.append(f"row {index} score_ml must be numeric between 0 and 100")

    if sample_ids and len(set(sample_ids)) != len(sample_ids):
        errors.append("score_ml rows contain duplicated sample_id values")

    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors))


def validate_score_ml_manifest(manifest: Mapping[str, object]) -> ExperimentConsistencyReport:
    errors: list[str] = []
    warnings: list[str] = []

    errors.extend(_missing_fields(manifest, REQUIRED_SCORE_ML_MANIFEST_FIELDS, "score_ml manifest"))
    if "adr_references" in manifest:
        errors.extend(_validate_adr_references(manifest))

    model = manifest.get("model")
    if isinstance(model, Mapping):
        if model.get("model_family") != "interpretable_linear_baseline":
            errors.append("model.model_family must be interpretable_linear_baseline")
        if model.get("role") != "auxiliary_incremental_rerank":
            errors.append("model.role must be auxiliary_incremental_rerank")
        if model.get("replaces_statistical_ranking") is not False:
            errors.append("model.replaces_statistical_ranking must be false")
    elif "model" in manifest:
        errors.append("model must be a structured mapping")

    attribution = manifest.get("attribution")
    if isinstance(attribution, Mapping):
        if attribution.get("required") is not True:
            errors.append("attribution.required must be true")
        if attribution.get("method") != "linear_feature_contribution":
            errors.append("attribution.method must be linear_feature_contribution")
    elif "attribution" in manifest:
        errors.append("attribution must be a structured mapping")

    temporal_validation = manifest.get("temporal_validation")
    if isinstance(temporal_validation, Mapping):
        if temporal_validation.get("walk_forward_required") is not True:
            errors.append("temporal_validation.walk_forward_required must be true")
        split_payload = temporal_validation.get("temporal_split")
        if isinstance(split_payload, Mapping):
            try:
                split = TemporalSplit(
                    split_id=str(split_payload["split_id"]),
                    train_start=int(split_payload["train_start"]),
                    train_end=int(split_payload["train_end"]),
                    test_start=int(split_payload["test_start"]),
                    test_end=int(split_payload["test_end"]),
                )
            except KeyError as exc:
                errors.append(f"temporal_validation.temporal_split missing boundary: {exc.args[0]}")
            else:
                errors.extend(validate_train_test_separation(split).errors)
        elif "temporal_split" in temporal_validation:
            errors.append("temporal_validation.temporal_split must be structured")
    elif "temporal_validation" in manifest:
        errors.append("temporal_validation must be a structured mapping")

    comparability = manifest.get("benchmark_comparability")
    if isinstance(comparability, Mapping):
        if comparability.get("benchmark_required") is not True:
            errors.append("benchmark_comparability.benchmark_required must be true")
        if comparability.get("statistical_benchmark_replaced") is not False:
            errors.append("benchmark_comparability.statistical_benchmark_replaced must be false")
    elif "benchmark_comparability" in manifest:
        errors.append("benchmark_comparability must be a structured mapping")

    constraints = manifest.get("operational_constraints")
    if isinstance(constraints, Mapping):
        for field in (
            "no_deep_learning",
            "no_automl",
            "no_opaque_models",
            "no_temporal_leakage",
        ):
            if constraints.get(field) is not True:
                errors.append(f"operational_constraints.{field} must be true")
    elif "operational_constraints" in manifest:
        errors.append("operational_constraints must be a structured mapping")

    reproducibility = manifest.get("reproducibility")
    if isinstance(reproducibility, Mapping):
        for field in ("model_version", "feature_schema_version", "random_seed_policy"):
            if not reproducibility.get(field):
                errors.append(f"reproducibility.{field} must be declared")
    elif "reproducibility" in manifest:
        errors.append("reproducibility must be a structured mapping")

    if not manifest.get("schema_version"):
        warnings.append("score_ml manifest schema_version should be explicit")

    return ExperimentConsistencyReport(
        valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def validate_supervised_scoring_registry(
    registry: Mapping[str, object],
) -> ExperimentConsistencyReport:
    errors: list[str] = []

    errors.extend(_missing_fields(registry, REQUIRED_REGISTRY_FIELDS, "supervised scoring registry"))
    if "adr_references" in registry:
        errors.extend(_validate_adr_references(registry))

    if registry.get("registry_version") != SUPERVISED_SCORING_REGISTRY_VERSION:
        errors.append("registry_version must match supervised scoring registry version")
    if registry.get("status") != SUPERVISED_SCORING_STATUS:
        errors.append("status must declare incremental score_ml baseline")

    manifests = registry.get("score_ml_manifests")
    if isinstance(manifests, Sequence) and not isinstance(manifests, str):
        if not manifests:
            errors.append("score_ml registry must declare at least one manifest")
        manifest_ids: list[str] = []
        for index, manifest in enumerate(manifests):
            if not isinstance(manifest, Mapping):
                errors.append(f"registry manifest {index} must be structured")
                continue
            for field in ("manifest_id", "path", "status"):
                if not manifest.get(field):
                    errors.append(f"registry manifest {index} must declare {field}")
            if manifest.get("status") != "active_incremental_baseline":
                errors.append(f"registry manifest {index} status must be active_incremental_baseline")
            if "manifest_id" in manifest:
                manifest_ids.append(str(manifest["manifest_id"]))
        if len(set(manifest_ids)) != len(manifest_ids):
            errors.append("score_ml registry contains duplicated manifest_id values")
    elif "score_ml_manifests" in registry:
        errors.append("score_ml_manifests must be a sequence")

    models = registry.get("models")
    if isinstance(models, Sequence) and not isinstance(models, str):
        if not models:
            errors.append("score_ml registry must declare at least one model")
        for index, model in enumerate(models):
            if not isinstance(model, Mapping):
                errors.append(f"registry model {index} must be structured")
                continue
            if model.get("model_family") != "interpretable_linear_baseline":
                errors.append(f"registry model {index} must remain interpretable linear baseline")
            if model.get("supervised_role") != "auxiliary_rerank_only":
                errors.append(f"registry model {index} must be auxiliary_rerank_only")
    elif "models" in registry:
        errors.append("models must be a sequence")

    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors))
