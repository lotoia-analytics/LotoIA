from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from lotoia.experiments.temporal_governance import (
    ExperimentConsistencyReport,
    TemporalSplit,
    validate_train_test_separation,
)

SUPERVISED_DATASET_REGISTRY_VERSION = "0.1.0"
SUPERVISED_DATASET_STATUS = "supervised_dataset_governance_baseline"

REQUIRED_ADR_REFERENCES = (
    "ADR_001",
    "ADR_002",
    "ADR_003",
    "ADR_004",
    "ADR_005",
    "ADR_006",
    "ADR_007",
)

FORBIDDEN_SUPERVISED_EXECUTION_FIELDS = {
    "score_ml",
    "trained_model_path",
    "model_path",
    "model_version",
    "inference_enabled",
    "training_enabled",
    "prediction",
    "predicted_score",
}

REQUIRED_FEATURE_MANIFEST_FIELDS = {
    "manifest_id",
    "schema_version",
    "dataset_version",
    "created_at",
    "adr_references",
    "feature_schema_version",
    "features",
    "temporal_policy",
    "prohibitions",
}

REQUIRED_TARGET_MANIFEST_FIELDS = {
    "manifest_id",
    "schema_version",
    "dataset_version",
    "created_at",
    "adr_references",
    "target_schema_version",
    "targets",
    "temporal_policy",
    "prohibitions",
}

REQUIRED_CONTRACT_FIELDS = {
    "contract_id",
    "schema_version",
    "dataset_version",
    "created_at",
    "adr_references",
    "feature_cutoff_policy",
    "allowed_source_window",
    "forbidden_sources",
    "validation_rules",
}

REQUIRED_DATASET_MANIFEST_FIELDS = {
    "dataset_id",
    "dataset_version",
    "schema_version",
    "created_at",
    "adr_references",
    "source_snapshot",
    "feature_manifest",
    "target_manifest",
    "temporal_feature_contract",
    "temporal_split",
    "lineage",
    "reproducibility",
    "prohibitions",
}

REQUIRED_REGISTRY_FIELDS = {
    "registry_version",
    "status",
    "created_at",
    "adr_references",
    "datasets",
    "manifests",
}


@dataclass(frozen=True)
class SupervisedSampleBoundary:
    sample_id: str
    feature_cutoff_contest: int
    label_contest: int

    def as_dict(self) -> dict[str, int | str]:
        return {
            "sample_id": self.sample_id,
            "feature_cutoff_contest": self.feature_cutoff_contest,
            "label_contest": self.label_contest,
        }


def _missing_fields(payload: Mapping[str, object], required: set[str], label: str) -> list[str]:
    missing = sorted(required - set(payload))
    if not missing:
        return []
    return [f"missing {label} fields: {', '.join(missing)}"]


def _validate_adr_references(payload: Mapping[str, object]) -> list[str]:
    adr_references = payload.get("adr_references")
    if not isinstance(adr_references, Sequence) or isinstance(adr_references, str):
        return ["adr_references must be a sequence"]

    missing_adrs = [
        required_adr
        for required_adr in REQUIRED_ADR_REFERENCES
        if not any(str(reference).startswith(required_adr) for reference in adr_references)
    ]
    if missing_adrs:
        return ["adr_references must include ADR_001 through ADR_007"]
    return []


def _validate_absent_forbidden_fields(payload: Mapping[str, object], label: str) -> list[str]:
    present = sorted(FORBIDDEN_SUPERVISED_EXECUTION_FIELDS & set(payload))
    if not present:
        return []
    return [f"{label} declares prohibited supervised execution fields: {', '.join(present)}"]


def validate_supervised_sample_boundaries(
    rows: Sequence[Mapping[str, object]],
) -> ExperimentConsistencyReport:
    errors: list[str] = []
    sample_ids: list[str] = []

    for index, row in enumerate(rows):
        if "sample_id" not in row:
            errors.append(f"row {index} must declare sample_id")
        else:
            sample_ids.append(str(row["sample_id"]))

        if "feature_cutoff_contest" not in row or "label_contest" not in row:
            errors.append(f"row {index} must declare feature_cutoff_contest and label_contest")
            continue

        feature_cutoff = row["feature_cutoff_contest"]
        label_contest = row["label_contest"]
        if not isinstance(feature_cutoff, int) or not isinstance(label_contest, int):
            errors.append(f"row {index} temporal boundaries must be integers")
            continue

        if feature_cutoff < 1 or label_contest < 1:
            errors.append(f"row {index} temporal boundaries must be positive")
        if feature_cutoff >= label_contest:
            errors.append(f"row {index} leaks future information into supervised features")

        forbidden = sorted(FORBIDDEN_SUPERVISED_EXECUTION_FIELDS & set(row))
        if forbidden:
            errors.append(
                f"row {index} declares prohibited supervised execution fields: "
                + ", ".join(forbidden)
            )

    if len(set(sample_ids)) != len(sample_ids):
        errors.append("supervised rows contain duplicated sample_id values")

    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors))


def validate_feature_manifest(manifest: Mapping[str, object]) -> ExperimentConsistencyReport:
    errors: list[str] = []
    warnings: list[str] = []

    errors.extend(_missing_fields(manifest, REQUIRED_FEATURE_MANIFEST_FIELDS, "feature manifest"))
    errors.extend(_validate_absent_forbidden_fields(manifest, "feature manifest"))
    if "adr_references" in manifest:
        errors.extend(_validate_adr_references(manifest))

    features = manifest.get("features")
    if isinstance(features, Sequence) and not isinstance(features, str):
        if not features:
            errors.append("feature manifest must declare at least one feature")
        names: list[str] = []
        for index, feature in enumerate(features):
            if not isinstance(feature, Mapping):
                errors.append(f"feature {index} must be a structured mapping")
                continue
            for field in ("name", "dtype", "source", "temporal_scope"):
                if not feature.get(field):
                    errors.append(f"feature {index} must declare {field}")
            temporal_scope = feature.get("temporal_scope")
            if temporal_scope not in {"historical_before_cutoff", "candidate_static"}:
                errors.append(f"feature {index} declares invalid temporal_scope")
            if feature.get("uses_label_contest") is not False:
                errors.append(f"feature {index} must declare uses_label_contest=false")
            if "name" in feature:
                names.append(str(feature["name"]))
        if len(set(names)) != len(names):
            errors.append("feature manifest contains duplicated feature names")
    elif "features" in manifest:
        errors.append("features must be a sequence")

    temporal_policy = manifest.get("temporal_policy")
    if isinstance(temporal_policy, Mapping):
        if temporal_policy.get("requires_feature_cutoff_contest") is not True:
            errors.append("temporal_policy.requires_feature_cutoff_contest must be true")
        if temporal_policy.get("feature_window") != "strictly_before_label_contest":
            errors.append("temporal_policy.feature_window must be strictly_before_label_contest")
    elif "temporal_policy" in manifest:
        errors.append("temporal_policy must be a structured mapping")

    prohibitions = manifest.get("prohibitions")
    if isinstance(prohibitions, Mapping):
        if prohibitions.get("future_contest_statistics") is not True:
            errors.append("prohibitions.future_contest_statistics must be true")
        if prohibitions.get("label_derived_features") is not True:
            errors.append("prohibitions.label_derived_features must be true")
    elif "prohibitions" in manifest:
        errors.append("prohibitions must be a structured mapping")

    if not manifest.get("feature_schema_version"):
        warnings.append("feature_schema_version should be explicitly versioned")

    return ExperimentConsistencyReport(
        valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def validate_target_manifest(manifest: Mapping[str, object]) -> ExperimentConsistencyReport:
    errors: list[str] = []

    errors.extend(_missing_fields(manifest, REQUIRED_TARGET_MANIFEST_FIELDS, "target manifest"))
    errors.extend(_validate_absent_forbidden_fields(manifest, "target manifest"))
    if "adr_references" in manifest:
        errors.extend(_validate_adr_references(manifest))

    targets = manifest.get("targets")
    if isinstance(targets, Sequence) and not isinstance(targets, str):
        if not targets:
            errors.append("target manifest must declare at least one target")
        names: list[str] = []
        for index, target in enumerate(targets):
            if not isinstance(target, Mapping):
                errors.append(f"target {index} must be a structured mapping")
                continue
            for field in ("name", "dtype", "label_source", "temporal_relation"):
                if not target.get(field):
                    errors.append(f"target {index} must declare {field}")
            if target.get("temporal_relation") != "after_feature_cutoff":
                errors.append(f"target {index} must occur after feature cutoff")
            if target.get("allowed_for_features") is not False:
                errors.append(f"target {index} must declare allowed_for_features=false")
            if "name" in target:
                names.append(str(target["name"]))
        if len(set(names)) != len(names):
            errors.append("target manifest contains duplicated target names")
    elif "targets" in manifest:
        errors.append("targets must be a sequence")

    temporal_policy = manifest.get("temporal_policy")
    if isinstance(temporal_policy, Mapping):
        if temporal_policy.get("requires_label_contest") is not True:
            errors.append("temporal_policy.requires_label_contest must be true")
        if temporal_policy.get("label_window") != "future_after_feature_cutoff":
            errors.append("temporal_policy.label_window must be future_after_feature_cutoff")
    elif "temporal_policy" in manifest:
        errors.append("temporal_policy must be a structured mapping")

    prohibitions = manifest.get("prohibitions")
    if isinstance(prohibitions, Mapping):
        if prohibitions.get("target_as_feature") is not True:
            errors.append("prohibitions.target_as_feature must be true")
    elif "prohibitions" in manifest:
        errors.append("prohibitions must be a structured mapping")

    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors))


def validate_temporal_feature_contract(contract: Mapping[str, object]) -> ExperimentConsistencyReport:
    errors: list[str] = []

    errors.extend(_missing_fields(contract, REQUIRED_CONTRACT_FIELDS, "temporal feature contract"))
    errors.extend(_validate_absent_forbidden_fields(contract, "temporal feature contract"))
    if "adr_references" in contract:
        errors.extend(_validate_adr_references(contract))

    cutoff_policy = contract.get("feature_cutoff_policy")
    if isinstance(cutoff_policy, Mapping):
        if cutoff_policy.get("required") is not True:
            errors.append("feature_cutoff_policy.required must be true")
        if cutoff_policy.get("comparison") != "feature_cutoff_contest < label_contest":
            errors.append(
                "feature_cutoff_policy.comparison must be feature_cutoff_contest < label_contest"
            )
    elif "feature_cutoff_policy" in contract:
        errors.append("feature_cutoff_policy must be a structured mapping")

    source_window = contract.get("allowed_source_window")
    if isinstance(source_window, Mapping):
        if source_window.get("max_contest") != "feature_cutoff_contest":
            errors.append("allowed_source_window.max_contest must be feature_cutoff_contest")
        if source_window.get("inclusive") is not False:
            errors.append("allowed_source_window.inclusive must be false")
    elif "allowed_source_window" in contract:
        errors.append("allowed_source_window must be a structured mapping")

    forbidden_sources = contract.get("forbidden_sources")
    if isinstance(forbidden_sources, Sequence) and not isinstance(forbidden_sources, str):
        required_forbidden = {"label_contest", "future_global_statistics", "post_cutoff_draws"}
        missing = sorted(required_forbidden - {str(source) for source in forbidden_sources})
        if missing:
            errors.append("forbidden_sources missing required entries: " + ", ".join(missing))
    elif "forbidden_sources" in contract:
        errors.append("forbidden_sources must be a sequence")

    validation_rules = contract.get("validation_rules")
    if isinstance(validation_rules, Sequence) and not isinstance(validation_rules, str):
        if "feature_cutoff_contest < label_contest" not in {
            str(rule) for rule in validation_rules
        }:
            errors.append("validation_rules must include feature_cutoff_contest < label_contest")
    elif "validation_rules" in contract:
        errors.append("validation_rules must be a sequence")

    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors))


def validate_dataset_lineage(lineage: Mapping[str, object]) -> ExperimentConsistencyReport:
    required_fields = {
        "source_dataset_version",
        "source_snapshot_path",
        "generation_policy",
        "transforms",
        "materialization_status",
    }
    errors: list[str] = []

    errors.extend(_missing_fields(lineage, required_fields, "dataset lineage"))
    transforms = lineage.get("transforms")
    if isinstance(transforms, Sequence) and not isinstance(transforms, str):
        if not transforms:
            errors.append("dataset lineage must declare at least one transform")
        for index, transform in enumerate(transforms):
            if not isinstance(transform, Mapping):
                errors.append(f"lineage transform {index} must be a structured mapping")
                continue
            for field in ("name", "input", "output", "temporal_rule"):
                if not transform.get(field):
                    errors.append(f"lineage transform {index} must declare {field}")
            if transform.get("temporal_rule") not in {
                "uses_only_contests_before_feature_cutoff",
                "labels_joined_after_feature_materialization",
            }:
                errors.append(f"lineage transform {index} declares invalid temporal_rule")
    elif "transforms" in lineage:
        errors.append("dataset lineage transforms must be a sequence")

    if lineage.get("materialization_status") not in {
        "declared_not_materialized",
        "materialized_governed_snapshot",
    }:
        errors.append("dataset lineage materialization_status is invalid")

    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors))


def _validate_manifest_reference(
    dataset_manifest: Mapping[str, object],
    field: str,
    expected_id_prefix: str,
) -> list[str]:
    reference = dataset_manifest.get(field)
    if not isinstance(reference, Mapping):
        return [f"{field} must be a structured mapping"]
    if not reference.get("manifest_id"):
        return [f"{field}.manifest_id must be declared"]
    if not str(reference["manifest_id"]).startswith(expected_id_prefix):
        return [f"{field}.manifest_id must reference {expected_id_prefix}"]
    if not reference.get("path"):
        return [f"{field}.path must be declared"]
    return []


def validate_supervised_dataset_manifest(
    manifest: Mapping[str, object],
) -> ExperimentConsistencyReport:
    errors: list[str] = []
    warnings: list[str] = []

    errors.extend(_missing_fields(manifest, REQUIRED_DATASET_MANIFEST_FIELDS, "dataset manifest"))
    errors.extend(_validate_absent_forbidden_fields(manifest, "dataset manifest"))
    if "adr_references" in manifest:
        errors.extend(_validate_adr_references(manifest))

    for field, prefix in (
        ("feature_manifest", "feature-manifest"),
        ("target_manifest", "target-manifest"),
        ("temporal_feature_contract", "temporal-feature-contract"),
    ):
        if field in manifest:
            errors.extend(_validate_manifest_reference(manifest, field, prefix))

    temporal_split = manifest.get("temporal_split")
    if isinstance(temporal_split, Mapping):
        try:
            split = TemporalSplit(
                split_id=str(temporal_split["split_id"]),
                train_start=int(temporal_split["train_start"]),
                train_end=int(temporal_split["train_end"]),
                test_start=int(temporal_split["test_start"]),
                test_end=int(temporal_split["test_end"]),
            )
        except KeyError as exc:
            errors.append(f"temporal_split missing boundary: {exc.args[0]}")
        else:
            errors.extend(validate_train_test_separation(split).errors)
    elif "temporal_split" in manifest:
        errors.append("temporal_split must be a structured mapping")

    lineage = manifest.get("lineage")
    if isinstance(lineage, Mapping):
        errors.extend(validate_dataset_lineage(lineage).errors)
    elif "lineage" in manifest:
        errors.append("lineage must be a structured mapping")

    reproducibility = manifest.get("reproducibility")
    if isinstance(reproducibility, Mapping):
        for field in ("code_version", "dataset_version", "random_seed_policy", "hash_policy"):
            if not reproducibility.get(field):
                errors.append(f"reproducibility.{field} must be declared")
    elif "reproducibility" in manifest:
        errors.append("reproducibility must be a structured mapping")

    prohibitions = manifest.get("prohibitions")
    if isinstance(prohibitions, Mapping):
        for field in ("ml_training", "score_ml", "supervised_inference"):
            if prohibitions.get(field) is not True:
                errors.append(f"prohibitions.{field} must remain true in this consolidation")
    elif "prohibitions" in manifest:
        errors.append("prohibitions must be a structured mapping")

    source_snapshot = manifest.get("source_snapshot")
    if isinstance(source_snapshot, Mapping):
        if not source_snapshot.get("dataset_version"):
            errors.append("source_snapshot.dataset_version must be declared")
        if not source_snapshot.get("content_hash"):
            warnings.append("source_snapshot.content_hash should be declared")
    elif "source_snapshot" in manifest:
        errors.append("source_snapshot must be a structured mapping")

    return ExperimentConsistencyReport(
        valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def validate_supervised_dataset_registry(
    registry: Mapping[str, object],
) -> ExperimentConsistencyReport:
    errors: list[str] = []

    errors.extend(_missing_fields(registry, REQUIRED_REGISTRY_FIELDS, "supervised registry"))
    errors.extend(_validate_absent_forbidden_fields(registry, "supervised registry"))
    if "adr_references" in registry:
        errors.extend(_validate_adr_references(registry))

    datasets = registry.get("datasets")
    if isinstance(datasets, Sequence) and not isinstance(datasets, str):
        if not datasets:
            errors.append("supervised registry must declare at least one dataset")
        versions: list[str] = []
        for index, dataset in enumerate(datasets):
            if not isinstance(dataset, Mapping):
                errors.append(f"registry dataset {index} must be a structured mapping")
                continue
            for field in ("dataset_id", "dataset_version", "manifest_path", "status"):
                if not dataset.get(field):
                    errors.append(f"registry dataset {index} must declare {field}")
            if dataset.get("status") not in {"declared_governance_baseline", "active_snapshot"}:
                errors.append(f"registry dataset {index} declares invalid status")
            if "dataset_version" in dataset:
                versions.append(str(dataset["dataset_version"]))
        if len(set(versions)) != len(versions):
            errors.append("supervised registry contains duplicated dataset_version values")
    elif "datasets" in registry:
        errors.append("datasets must be a sequence")

    manifests = registry.get("manifests")
    if isinstance(manifests, Mapping):
        for field in ("feature", "target", "temporal_contract"):
            if not manifests.get(field):
                errors.append(f"manifests.{field} must be declared")
    elif "manifests" in registry:
        errors.append("manifests must be a structured mapping")

    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors))
