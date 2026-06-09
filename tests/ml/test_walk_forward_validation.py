from __future__ import annotations

import json

from lotoia.ml import (
    DEFAULT_WALK_FORWARD_VALIDATION_ID,
    build_walk_forward_validation_report,
    run_walk_forward_validation,
)


def test_walk_forward_validation_report_enforces_temporal_governance() -> None:
    report = build_walk_forward_validation_report([1, 2, 3, 4, 5, 6], min_train_size=3, test_size=1, step_size=1)

    assert report["validation_id"] == DEFAULT_WALK_FORWARD_VALIDATION_ID
    assert report["temporal_valid"] is True
    assert report["benchmark_mandatory"] is True
    assert report["no_temporal_leakage"] is True
    assert report["split_count"] >= 1
    for split in report["splits"]:
        assert split["train_end"] < split["test_start"]


def test_walk_forward_validation_run_is_reproducible(tmp_path) -> None:
    contests = [1, 2, 3, 4, 5, 6, 7]

    first = run_walk_forward_validation(
        contests,
        min_train_size=3,
        test_size=1,
        step_size=1,
        validation_dir=tmp_path / "first",
    )
    second = run_walk_forward_validation(
        contests,
        min_train_size=3,
        test_size=1,
        step_size=1,
        validation_dir=tmp_path / "second",
    )

    assert first.reproducibility_hash == second.reproducibility_hash
    assert first.temporal_valid is True
    assert first.manifest_path.endswith("walk_forward_validation_manifest.json")
    assert first.report_path.endswith("walk_forward_validation_report.json")
    assert json.loads((tmp_path / "first" / "walk_forward_validation_report.json").read_text())["split_count"] == first.split_count
