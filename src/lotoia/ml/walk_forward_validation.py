from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from lotoia.experiments.temporal_governance import (
    TemporalSplit,
    build_walk_forward_splits,
    validate_temporal_integrity,
)

DEFAULT_WALK_FORWARD_VALIDATION_ID = "ml-walk-forward-validation-v0.1.0"
DEFAULT_WALK_FORWARD_VALIDATION_DIR = Path("reports/ml/walk_forward_validation_v0_1_0")


@dataclass(frozen=True)
class WalkForwardValidationResult:
    validation_id: str
    created_at: str
    manifest_path: str
    report_path: str
    split_count: int
    contest_count: int
    reproducibility_hash: str
    temporal_valid: bool
    benchmark_mandatory: bool
    no_temporal_leakage: bool
    splits: tuple[TemporalSplit, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "validation_id": self.validation_id,
            "created_at": self.created_at,
            "manifest_path": self.manifest_path,
            "report_path": self.report_path,
            "split_count": self.split_count,
            "contest_count": self.contest_count,
            "reproducibility_hash": self.reproducibility_hash,
            "temporal_valid": self.temporal_valid,
            "benchmark_mandatory": self.benchmark_mandatory,
            "no_temporal_leakage": self.no_temporal_leakage,
            "splits": [split.as_dict() for split in self.splits],
        }


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _payload_hash(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def build_walk_forward_validation_report(
    contests: Sequence[int],
    *,
    min_train_size: int,
    test_size: int,
    step_size: int = 1,
) -> dict[str, object]:
    validation = validate_temporal_integrity(contests)
    validation.assert_valid()
    splits = build_walk_forward_splits(
        contests,
        min_train_size=min_train_size,
        test_size=test_size,
        step_size=step_size,
    )
    split_payload = [split.as_dict() for split in splits]
    return {
        "validation_id": DEFAULT_WALK_FORWARD_VALIDATION_ID,
        "contest_count": len(contests),
        "split_count": len(splits),
        "temporal_valid": True,
        "benchmark_mandatory": True,
        "no_temporal_leakage": True,
        "min_train_size": min_train_size,
        "test_size": test_size,
        "step_size": step_size,
        "splits": split_payload,
        "reproducibility_hash": _payload_hash(
            {
                "contests": list(contests),
                "min_train_size": min_train_size,
                "test_size": test_size,
                "step_size": step_size,
                "splits": split_payload,
            }
        ),
    }


def run_walk_forward_validation(
    contests: Sequence[int],
    *,
    min_train_size: int,
    test_size: int,
    step_size: int = 1,
    validation_dir: Path = DEFAULT_WALK_FORWARD_VALIDATION_DIR,
) -> WalkForwardValidationResult:
    report = build_walk_forward_validation_report(
        contests,
        min_train_size=min_train_size,
        test_size=test_size,
        step_size=step_size,
    )
    created_at = _now()
    report_path = validation_dir / "walk_forward_validation_report.json"
    manifest_path = validation_dir / "walk_forward_validation_manifest.json"

    manifest_payload = {
        "validation_id": report["validation_id"],
        "created_at": created_at,
        "contest_count": report["contest_count"],
        "split_count": report["split_count"],
        "min_train_size": min_train_size,
        "test_size": test_size,
        "step_size": step_size,
        "temporal_valid": report["temporal_valid"],
        "benchmark_mandatory": report["benchmark_mandatory"],
        "no_temporal_leakage": report["no_temporal_leakage"],
        "reproducibility": {
            "reproducibility_hash": report["reproducibility_hash"],
            "random_seed_policy": "not_applicable_temporal_validation_only",
        },
        "governance": {
            "benchmark_mandatory": True,
            "no_temporal_leakage": True,
            "walk_forward_required": True,
        },
    }

    _write_json(report_path, report)
    _write_json(manifest_path, manifest_payload)

    splits = tuple(
        TemporalSplit(
            split_id=str(split["split_id"]),
            train_start=int(split["train_start"]),
            train_end=int(split["train_end"]),
            test_start=int(split["test_start"]),
            test_end=int(split["test_end"]),
        )
        for split in report["splits"]
    )
    return WalkForwardValidationResult(
        validation_id=str(report["validation_id"]),
        created_at=created_at,
        manifest_path=str(manifest_path),
        report_path=str(report_path),
        split_count=int(report["split_count"]),
        contest_count=int(report["contest_count"]),
        reproducibility_hash=str(report["reproducibility_hash"]),
        temporal_valid=bool(report["temporal_valid"]),
        benchmark_mandatory=bool(report["benchmark_mandatory"]),
        no_temporal_leakage=bool(report["no_temporal_leakage"]),
        splits=splits,
    )
