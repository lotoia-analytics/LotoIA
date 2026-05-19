from __future__ import annotations

import json
from pathlib import Path

from lotoia.experiments.temporal_benchmark import (
    build_dataset_snapshot,
    hash_draws,
    validate_dataset_snapshot,
    validate_temporal_benchmark_manifest,
)
from lotoia.models.draw import Draw


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    ROOT / "experiments" / "temporal_benchmark" / "manifests" / "temporal_baseline_v0_1_0.json"
)
DATASET_SNAPSHOT_PATH = (
    ROOT
    / "experiments"
    / "temporal_benchmark"
    / "datasets"
    / "lotofacil_historico_v0_1_0_2026_05_16.json"
)


def make_draw(contest: int) -> Draw:
    numbers = sorted(((contest + offset - 1) % 25) + 1 for offset in range(15))
    return Draw(contest=contest, date=f"2026-01-{contest:02d}", numbers=numbers)


def test_dataset_snapshot_is_temporally_consistent_and_hash_reproducible() -> None:
    draws = [make_draw(contest) for contest in range(1, 6)]

    snapshot = build_dataset_snapshot(
        draws,
        dataset_version="test-dataset-v1",
        source_path="memory://draws",
    )

    assert snapshot.first_contest == 1
    assert snapshot.last_contest == 5
    assert snapshot.contests_count == 5
    assert snapshot.content_hash == hash_draws(list(reversed(draws)))
    assert validate_dataset_snapshot(snapshot.as_dict(), draws).valid is True


def test_dataset_snapshot_detects_content_drift() -> None:
    draws = [make_draw(contest) for contest in range(1, 4)]
    snapshot = build_dataset_snapshot(
        draws,
        dataset_version="test-dataset-v1",
        source_path="memory://draws",
    ).as_dict()
    snapshot["content_hash"] = "0" * 64

    report = validate_dataset_snapshot(snapshot, draws)

    assert report.valid is False
    assert "dataset snapshot content_hash does not match source draws" in report.errors


def test_temporal_benchmark_manifest_is_valid() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    report = validate_temporal_benchmark_manifest(manifest)

    assert report.valid is True
    assert report.errors == ()


def test_temporal_benchmark_manifest_blocks_supervised_execution_fields() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest["score_ml"] = 0.2
    manifest["inference_enabled"] = True

    report = validate_temporal_benchmark_manifest(manifest)

    assert report.valid is False
    assert any("prohibited supervised fields" in error for error in report.errors)


def test_temporal_benchmark_manifest_rejects_split_after_snapshot() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest["temporal_split"]["test_end"] = manifest["dataset_snapshot"]["last_contest"] + 1

    report = validate_temporal_benchmark_manifest(manifest)

    assert report.valid is False
    assert "temporal_split test_end exceeds dataset snapshot last_contest" in report.errors


def test_institutional_dataset_snapshot_file_has_required_integrity() -> None:
    snapshot = json.loads(DATASET_SNAPSHOT_PATH.read_text(encoding="utf-8"))

    report = validate_dataset_snapshot(snapshot)

    assert report.valid is True
    assert snapshot["contests_count"] > 0
    assert snapshot["first_contest"] < snapshot["last_contest"]
