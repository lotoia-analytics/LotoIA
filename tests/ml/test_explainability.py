from __future__ import annotations

import json

from lotoia.ml import explain_score_ml_game


def _sample_game() -> dict[str, object]:
    return {
        "numbers": [1, 2, 3, 4, 5, 7, 9, 11, 13, 15, 18, 20, 22, 24, 25],
        "odd": 8,
        "even": 7,
        "sum": 204,
        "frame": 10,
        "center": 5,
        "quadra_score": {"found_quadras": 4, "average_rank": 10.0},
        "final_score": {"final_score": 81.0, "components": {}}}


def test_explain_score_ml_game_persists_report_and_registry(tmp_path) -> None:
    result = explain_score_ml_game(_sample_game(), tracking_dir=tmp_path / "experiments" / "ml_explainability")

    report = json.loads((tmp_path / "experiments" / "ml_explainability" / "explainability_report.json").read_text())
    registry = json.loads((tmp_path / "experiments" / "ml_explainability" / "registry.json").read_text())

    assert result.score_ml >= 0
    assert report["confidence_reasoning"]
    assert report["reproducibility_hash"] == result.reproducibility_hash
    assert registry["registry_version"] == "ml-explainability-v0.1.0"
    assert registry["executed_runs"][0]["report_path"].endswith("explainability_report.json")


def test_explain_score_ml_game_exposes_feature_contribution(tmp_path) -> None:
    result = explain_score_ml_game(_sample_game(), tracking_dir=tmp_path / "experiments" / "ml_explainability")

    assert result.feature_importance
    assert result.score_contribution
    assert set(result.feature_importance) == set(result.score_contribution)
    assert abs(sum(result.feature_importance.values()) - 1.0) < 1e-6
