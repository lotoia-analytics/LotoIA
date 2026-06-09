from __future__ import annotations

import json

from lotoia.ml import activate_model_version, register_model_version, rollback_model_version


def test_model_registry_registers_activates_and_rolls_back(tmp_path) -> None:
    registry_path = tmp_path / "experiments" / "ml_models" / "registry.json"

    registered = register_model_version(
        model_id="score-ml",
        model_version="v1",
        dataset_version="dataset-v1",
        calibration_version="calib-v1",
        registry_path=registry_path,
    )
    activated = activate_model_version(model_id="score-ml", model_version="v1", registry_path=registry_path)
    rolled_back = rollback_model_version(model_id="score-ml", target_version="v1", registry_path=registry_path)

    registry = json.loads(registry_path.read_text())

    assert registered.model_id == "score-ml"
    assert registered.active_version == "v1"
    assert activated.active_version == "v1"
    assert rolled_back.active_version == "v1"
    assert registry["registry_version"] == "ml-model-registry-v0.1.0"
    assert registry["active_version"] == "v1"
    assert registry["versions"][0]["dataset_version"] == "dataset-v1"


def test_model_registry_rejects_unregistered_activation(tmp_path) -> None:
    registry_path = tmp_path / "experiments" / "ml_models" / "registry.json"

    try:
        activate_model_version(model_id="score-ml", model_version="v1", registry_path=registry_path)
    except ValueError as exc:
        assert "not registered" in str(exc)
    else:
        raise AssertionError("activation should reject unknown versions")
