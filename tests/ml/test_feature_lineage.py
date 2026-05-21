from __future__ import annotations

import json
from pathlib import Path

from lotoia.ml import build_feature_lineage


def test_build_feature_lineage_persists_manifest_and_registry(tmp_path) -> None:
    feature_manifest = json.loads(
        Path("experiments/supervised_dataset/manifests/feature_manifest_v0_1_0.json").read_text(encoding="utf-8")
    )
    dataset_manifest = json.loads(
        Path("experiments/supervised_dataset/datasets/lotofacil_supervised_governance_v0_1_0.json").read_text(
            encoding="utf-8"
        )
    )

    result = build_feature_lineage(
        feature_manifest,
        dataset_manifest,
        tracking_dir=tmp_path / "experiments" / "ml_feature_lineage",
    )

    manifest = json.loads((tmp_path / "experiments" / "ml_feature_lineage" / "feature_lineage_manifest.json").read_text())
    registry = json.loads((tmp_path / "experiments" / "ml_feature_lineage" / "registry.json").read_text())

    assert result.dataset_version == dataset_manifest["dataset_version"]
    assert result.feature_count == len(feature_manifest["features"])
    assert manifest["feature_manifest_id"] == feature_manifest["manifest_id"]
    assert manifest["reproducibility_hash"] == result.reproducibility_hash
    assert registry["registry_version"] == "ml-feature-lineage-v0.1.0"
    assert registry["executed_runs"][0]["feature_count"] == len(feature_manifest["features"])


def test_build_feature_lineage_is_reproducible_for_same_manifests(tmp_path) -> None:
    feature_manifest = json.loads(
        Path("experiments/supervised_dataset/manifests/feature_manifest_v0_1_0.json").read_text(encoding="utf-8")
    )
    dataset_manifest = json.loads(
        Path("experiments/supervised_dataset/datasets/lotofacil_supervised_governance_v0_1_0.json").read_text(
            encoding="utf-8"
        )
    )

    first = build_feature_lineage(
        feature_manifest,
        dataset_manifest,
        tracking_dir=tmp_path / "first" / "experiments" / "ml_feature_lineage",
    )
    second = build_feature_lineage(
        feature_manifest,
        dataset_manifest,
        tracking_dir=tmp_path / "second" / "experiments" / "ml_feature_lineage",
    )

    assert first.reproducibility_hash == second.reproducibility_hash
    assert first.feature_count == second.feature_count
