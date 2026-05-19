from __future__ import annotations

import json
from pathlib import Path

from lotoia.experiments.supervised_scoring import (
    validate_score_ml_manifest,
    validate_score_ml_rows,
    validate_supervised_scoring_registry,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_score_ml_manifest_is_valid() -> None:
    manifest = json.loads(
        (PROJECT_ROOT / "experiments/supervised_scoring/score_ml_manifest_v0_1_0.json").read_text(
            encoding="utf-8"
        )
    )

    report = validate_score_ml_manifest(manifest)

    assert report.valid is True
    assert report.errors == ()


def test_supervised_scoring_registry_is_valid() -> None:
    registry = json.loads(
        (PROJECT_ROOT / "experiments/supervised_scoring/registry.json").read_text(
            encoding="utf-8"
        )
    )

    report = validate_supervised_scoring_registry(registry)

    assert report.valid is True
    assert report.errors == ()


def test_score_ml_rows_reject_temporal_leakage() -> None:
    report = validate_score_ml_rows(
        [
            {
                "sample_id": "sample-001",
                "feature_cutoff_contest": 20,
                "scoring_contest": 20,
                "label_contest": 21,
                "score_ml": 50,
            }
        ]
    )

    assert report.valid is False
    assert "row 0 leaks future information into score_ml features" in report.errors


def test_score_ml_rows_accept_valid_supervised_score() -> None:
    report = validate_score_ml_rows(
        [
            {
                "sample_id": "sample-001",
                "feature_cutoff_contest": 20,
                "scoring_contest": 21,
                "label_contest": 21,
                "score_ml": 50,
            }
        ]
    )

    assert report.valid is True
    assert report.errors == ()
