from __future__ import annotations

import json

from lotoia.ml import InterpretableLinearScoreML, register_calibration_snapshot


def test_register_calibration_snapshot_persists_registry_and_snapshot(tmp_path) -> None:
    calibration = InterpretableLinearScoreML().calibration
    assert calibration is not None

    result = register_calibration_snapshot(
        model_version="historical_recalibrated_v2",
        dataset_version="dataset-v1",
        calibration=calibration,
        feature_lineage_hash="feature-lineage-hash",
        tracking_dir=tmp_path / "experiments" / "ml_calibration",
    )

    snapshot = json.loads((tmp_path / "experiments" / "ml_calibration" / "snapshots" / "historical_recalibrated_v2.json").read_text())
    registry = json.loads((tmp_path / "experiments" / "ml_calibration" / "registry.json").read_text())

    assert result.model_version == "historical_recalibrated_v2"
    assert result.dataset_version == "dataset-v1"
    assert snapshot["calibration_version"] == "historical_recalibrated_v2"
    assert snapshot["confidence_tracking"]["feature_lineage_hash"] == "feature-lineage-hash"
    assert registry["registry_version"] == "ml-calibration-governance-v0.1.0"
    assert registry["snapshots"][0]["snapshot_path"].endswith("historical_recalibrated_v2.json")


def test_register_calibration_snapshot_is_reproducible(tmp_path) -> None:
    calibration = InterpretableLinearScoreML().calibration
    assert calibration is not None

    first = register_calibration_snapshot(
        model_version="historical_recalibrated_v2",
        dataset_version="dataset-v1",
        calibration=calibration,
        tracking_dir=tmp_path / "first" / "experiments" / "ml_calibration",
    )
    second = register_calibration_snapshot(
        model_version="historical_recalibrated_v2",
        dataset_version="dataset-v1",
        calibration=calibration,
        tracking_dir=tmp_path / "second" / "experiments" / "ml_calibration",
    )

    assert first.reproducibility_hash == second.reproducibility_hash
    assert first.calibration_version == second.calibration_version
