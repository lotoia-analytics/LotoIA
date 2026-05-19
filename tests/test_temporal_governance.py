from __future__ import annotations

import pytest

from lotoia.experiments.temporal_governance import (
    TemporalSplit,
    build_walk_forward_splits,
    validate_experiment_manifest,
    validate_supervised_rows,
    validate_temporal_integrity,
    validate_train_test_separation,
)


def test_validate_temporal_integrity_rejects_unsorted_or_duplicate_contests() -> None:
    report = validate_temporal_integrity([1, 2, 2, 4, 3])

    assert report.valid is False
    assert "contest series must be strictly ordered by time" in report.errors
    assert "contest series contains duplicated contest identifiers" in report.errors


def test_build_walk_forward_splits_creates_expanding_train_windows() -> None:
    splits = build_walk_forward_splits(
        list(range(1, 9)),
        min_train_size=4,
        test_size=2,
        step_size=2,
    )

    assert [split.as_dict() for split in splits] == [
        {
            "split_id": "wf_001",
            "train_start": 1,
            "train_end": 4,
            "test_start": 5,
            "test_end": 6,
        },
        {
            "split_id": "wf_002",
            "train_start": 1,
            "train_end": 6,
            "test_start": 7,
            "test_end": 8,
        },
    ]


def test_train_test_separation_rejects_overlap() -> None:
    split = TemporalSplit(
        split_id="invalid",
        train_start=1,
        train_end=10,
        test_start=10,
        test_end=12,
    )

    report = validate_train_test_separation(split)

    assert report.valid is False
    assert "training window must end before test window starts" in report.errors


def test_supervised_rows_reject_future_feature_cutoff_and_score_ml() -> None:
    report = validate_supervised_rows(
        [
            {
                "sample_id": "sample_001",
                "feature_cutoff_contest": 12,
                "label_contest": 12,
                "score_ml": 0.8,
            }
        ]
    )

    assert report.valid is False
    assert "row 0 leaks future information into supervised features" in report.errors
    assert "row 0 must not contain score_ml in governance baseline" in report.errors


def test_experiment_manifest_validates_temporal_split_and_required_fields() -> None:
    manifest = {
        "experiment_id": "wf-baseline-001",
        "created_at": "2026-05-16T00:00:00-03:00",
        "dataset_version": "dataset-placeholder-v0",
        "code_version": "uncommitted-local",
        "temporal_split": {
            "split_id": "wf_001",
            "train_start": 1,
            "train_end": 100,
            "test_start": 101,
            "test_end": 110,
        },
        "benchmark_reference": "reports/benchmark/benchmark_result.json",
        "reproducibility": {
            "random_seed_policy": "fixed when stochastic generation is introduced",
            "dataset_snapshot": "not generated in baseline",
        },
    }

    report = validate_experiment_manifest(manifest)

    assert report.valid is True
    assert report.errors == ()


def test_experiment_manifest_rejects_supervised_execution_fields() -> None:
    manifest = {
        "experiment_id": "wf-baseline-001",
        "score_ml": 0.4,
    }

    report = validate_experiment_manifest(manifest)

    assert report.valid is False
    assert any("missing required manifest fields" in error for error in report.errors)
    assert any("score_ml" in error for error in report.errors)


def test_walk_forward_requires_temporally_valid_series() -> None:
    with pytest.raises(ValueError, match="strictly ordered"):
        build_walk_forward_splits([1, 3, 2], min_train_size=2, test_size=1)
