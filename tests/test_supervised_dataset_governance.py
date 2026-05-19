from __future__ import annotations

import json
from pathlib import Path

from lotoia.experiments.supervised_dataset import (
    validate_feature_manifest,
    validate_supervised_dataset_manifest,
    validate_supervised_dataset_registry,
    validate_supervised_sample_boundaries,
    validate_target_manifest,
    validate_temporal_feature_contract,
)

ROOT = Path(__file__).resolve().parents[1]
SUPERVISED_ROOT = ROOT / "experiments" / "supervised_dataset"
REGISTRY_PATH = SUPERVISED_ROOT / "registry.json"
FEATURE_MANIFEST_PATH = SUPERVISED_ROOT / "manifests" / "feature_manifest_v0_1_0.json"
TARGET_MANIFEST_PATH = SUPERVISED_ROOT / "manifests" / "target_manifest_v0_1_0.json"
TEMPORAL_CONTRACT_PATH = (
    SUPERVISED_ROOT / "manifests" / "temporal_feature_contract_v0_1_0.json"
)
DATASET_MANIFEST_PATH = (
    SUPERVISED_ROOT / "datasets" / "lotofacil_supervised_governance_v0_1_0.json"
)


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_institutional_supervised_manifests_are_valid() -> None:
    feature_report = validate_feature_manifest(read_json(FEATURE_MANIFEST_PATH))
    target_report = validate_target_manifest(read_json(TARGET_MANIFEST_PATH))
    contract_report = validate_temporal_feature_contract(read_json(TEMPORAL_CONTRACT_PATH))

    assert feature_report.valid is True
    assert feature_report.errors == ()
    assert target_report.valid is True
    assert target_report.errors == ()
    assert contract_report.valid is True
    assert contract_report.errors == ()


def test_supervised_dataset_registry_and_lineage_are_valid() -> None:
    registry_report = validate_supervised_dataset_registry(read_json(REGISTRY_PATH))
    dataset_report = validate_supervised_dataset_manifest(read_json(DATASET_MANIFEST_PATH))

    assert registry_report.valid is True
    assert registry_report.errors == ()
    assert dataset_report.valid is True
    assert dataset_report.errors == ()


def test_supervised_sample_boundaries_reject_temporal_leakage() -> None:
    report = validate_supervised_sample_boundaries(
        [
            {
                "sample_id": "sample-001",
                "feature_cutoff_contest": 100,
                "label_contest": 100,
            }
        ]
    )

    assert report.valid is False
    assert "row 0 leaks future information into supervised features" in report.errors


def test_supervised_sample_boundaries_reject_execution_fields() -> None:
    report = validate_supervised_sample_boundaries(
        [
            {
                "sample_id": "sample-001",
                "feature_cutoff_contest": 100,
                "label_contest": 101,
                "score_ml": 0.9,
                "inference_enabled": True,
            }
        ]
    )

    assert report.valid is False
    assert any("prohibited supervised execution fields" in error for error in report.errors)


def test_target_manifest_rejects_target_as_feature() -> None:
    manifest = read_json(TARGET_MANIFEST_PATH)
    targets = manifest["targets"]
    assert isinstance(targets, list)
    targets[0]["allowed_for_features"] = True

    report = validate_target_manifest(manifest)

    assert report.valid is False
    assert "target 0 must declare allowed_for_features=false" in report.errors


def test_feature_manifest_rejects_label_derived_features() -> None:
    manifest = read_json(FEATURE_MANIFEST_PATH)
    features = manifest["features"]
    assert isinstance(features, list)
    features[0]["uses_label_contest"] = True

    report = validate_feature_manifest(manifest)

    assert report.valid is False
    assert "feature 0 must declare uses_label_contest=false" in report.errors


def test_temporal_contract_requires_strict_cutoff_before_label() -> None:
    contract = read_json(TEMPORAL_CONTRACT_PATH)
    cutoff_policy = contract["feature_cutoff_policy"]
    assert isinstance(cutoff_policy, dict)
    cutoff_policy["comparison"] = "feature_cutoff_contest <= label_contest"

    report = validate_temporal_feature_contract(contract)

    assert report.valid is False
    assert (
        "feature_cutoff_policy.comparison must be feature_cutoff_contest < label_contest"
        in report.errors
    )


def test_supervised_dataset_manifest_rejects_invalid_lineage_rule() -> None:
    manifest = read_json(DATASET_MANIFEST_PATH)
    lineage = manifest["lineage"]
    assert isinstance(lineage, dict)
    transforms = lineage["transforms"]
    assert isinstance(transforms, list)
    transforms[0]["temporal_rule"] = "uses_global_future_history"

    report = validate_supervised_dataset_manifest(manifest)

    assert report.valid is False
    assert "lineage transform 0 declares invalid temporal_rule" in report.errors
