from __future__ import annotations

import json

from lotoia.ml import track_ml_experiment


def test_track_ml_experiment_persists_manifest_and_registry(tmp_path) -> None:
    result = track_ml_experiment(
        experiment_id="score-ml-governance-v0",
        dataset_version="dataset-v1",
        model_version="model-v1",
        hyperparameters={"alpha": 0.1, "max_depth": 3},
        metrics={"accuracy": 0.91, "loss": 0.12},
        artifacts={"report": "reports/ml/report.json"},
        tracking_dir=tmp_path / "experiments" / "ml_governance",
    )

    manifest = json.loads((tmp_path / "experiments" / "ml_governance" / "runs" / f"{result.run_id}.json").read_text())
    registry = json.loads((tmp_path / "experiments" / "ml_governance" / "registry.json").read_text())

    assert result.experiment_id == "score-ml-governance-v0"
    assert result.dataset_version == "dataset-v1"
    assert result.model_version == "model-v1"
    assert manifest["experiment_id"] == result.experiment_id
    assert manifest["hyperparameters"]["alpha"] == 0.1
    assert manifest["metrics"]["accuracy"] == 0.91
    assert manifest["reproducibility_hash"] == result.reproducibility_hash
    assert registry["executed_runs"][0]["run_id"] == result.run_id
    assert registry["registry_version"] == "ml-governance-v0.1.0"


def test_track_ml_experiment_is_reproducible_for_same_inputs(tmp_path) -> None:
    first = track_ml_experiment(
        experiment_id="score-ml-governance-v0",
        dataset_version="dataset-v1",
        model_version="model-v1",
        hyperparameters={"alpha": 0.1},
        metrics={"accuracy": 0.91},
        tracking_dir=tmp_path / "first" / "experiments" / "ml_governance",
    )
    second = track_ml_experiment(
        experiment_id="score-ml-governance-v0",
        dataset_version="dataset-v1",
        model_version="model-v1",
        hyperparameters={"alpha": 0.1},
        metrics={"accuracy": 0.91},
        tracking_dir=tmp_path / "second" / "experiments" / "ml_governance",
    )

    assert first.experiment_id == second.experiment_id
    assert first.dataset_version == second.dataset_version
    assert first.model_version == second.model_version
    assert first.hyperparameters == second.hyperparameters
    assert first.metrics == second.metrics
