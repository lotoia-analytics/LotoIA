from __future__ import annotations

import json

from lotoia.ml import detect_ml_drift


def test_detect_ml_drift_persists_report_and_registry(tmp_path) -> None:
    result = detect_ml_drift(
        model_version="historical_recalibrated_v2",
        dataset_version="dataset-v1",
        baseline_scores=[0.10, 0.12, 0.11],
        current_scores=[0.14, 0.15, 0.13],
        baseline_timestamps=["2026-05-01T00:00:00Z", "2026-05-02T00:00:00Z"],
        current_timestamps=["2026-05-03T00:00:00Z", "2026-05-04T00:00:00Z"],
        structural_signals={"confidence_drift": 0.02, "structural_health": 0.01},
        tracking_dir=tmp_path / "experiments" / "ml_drift",
    )

    report = json.loads((tmp_path / "experiments" / "ml_drift" / "drift_report.json").read_text())
    registry = json.loads((tmp_path / "experiments" / "ml_drift" / "registry.json").read_text())

    assert result.model_version == "historical_recalibrated_v2"
    assert result.dataset_version == "dataset-v1"
    assert report["confidence_state"] in {"stable", "watch", "alert"}
    assert report["reproducibility_hash"] == result.reproducibility_hash
    assert registry["registry_version"] == "ml-drift-detection-v0.1.0"
    assert registry["executed_runs"][0]["report_path"].endswith("drift_report.json")


def test_detect_ml_drift_is_reproducible(tmp_path) -> None:
    kwargs = dict(
        model_version="historical_recalibrated_v2",
        dataset_version="dataset-v1",
        baseline_scores=[0.1, 0.2, 0.3],
        current_scores=[0.12, 0.21, 0.29],
        structural_signals={"confidence_drift": 0.01},
    )

    first = detect_ml_drift(tracking_dir=tmp_path / "first" / "experiments" / "ml_drift", **kwargs)
    second = detect_ml_drift(tracking_dir=tmp_path / "second" / "experiments" / "ml_drift", **kwargs)

    assert first.reproducibility_hash == second.reproducibility_hash
    assert first.confidence_state == second.confidence_state
