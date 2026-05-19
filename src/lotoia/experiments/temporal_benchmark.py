from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256

from lotoia.experiments.temporal_governance import (
    ExperimentConsistencyReport,
    TemporalSplit,
    validate_temporal_integrity,
    validate_train_test_separation,
)
from lotoia.models.draw import Draw

BENCHMARK_REGISTRY_VERSION = "0.1.0"
TEMPORAL_BENCHMARK_STATUS = "scientific_temporal_benchmark_baseline"
FORBIDDEN_SUPERVISED_FIELDS = {
    "score_ml",
    "trained_model_path",
    "model_path",
    "model_version",
    "inference_enabled",
}
REQUIRED_MANIFEST_FIELDS = {
    "manifest_id",
    "benchmark_id",
    "benchmark_type",
    "created_at",
    "adr_references",
    "dataset_snapshot",
    "temporal_split",
    "walk_forward",
    "baseline_reference",
    "comparability",
    "reproducibility",
    "prohibitions",
}


@dataclass(frozen=True)
class DatasetSnapshot:
    dataset_version: str
    source_path: str
    contests_count: int
    first_contest: int
    last_contest: int
    content_hash: str

    def as_dict(self) -> dict[str, object]:
        return {
            "dataset_version": self.dataset_version,
            "source_path": self.source_path,
            "contests_count": self.contests_count,
            "first_contest": self.first_contest,
            "last_contest": self.last_contest,
            "content_hash": self.content_hash,
        }


def _draw_hash_payload(draws: Sequence[Draw]) -> str:
    lines = []
    for draw in draws:
        numbers = ",".join(str(number) for number in draw.numbers)
        lines.append(f"{draw.contest}|{draw.date or ''}|{numbers}")
    return "\n".join(lines)


def hash_draws(draws: Iterable[Draw]) -> str:
    ordered_draws = sorted(draws, key=lambda draw: draw.contest)
    validate_temporal_integrity([draw.contest for draw in ordered_draws]).assert_valid()
    return sha256(_draw_hash_payload(ordered_draws).encode("utf-8")).hexdigest()


def build_dataset_snapshot(
    draws: Sequence[Draw],
    *,
    dataset_version: str,
    source_path: str,
) -> DatasetSnapshot:
    ordered_draws = sorted(draws, key=lambda draw: draw.contest)
    validate_temporal_integrity([draw.contest for draw in ordered_draws]).assert_valid()
    if not dataset_version:
        raise ValueError("dataset_version must be declared")
    if not source_path:
        raise ValueError("source_path must be declared")

    return DatasetSnapshot(
        dataset_version=dataset_version,
        source_path=source_path,
        contests_count=len(ordered_draws),
        first_contest=ordered_draws[0].contest,
        last_contest=ordered_draws[-1].contest,
        content_hash=hash_draws(ordered_draws),
    )


def validate_dataset_snapshot(
    snapshot: Mapping[str, object],
    draws: Sequence[Draw] | None = None,
) -> ExperimentConsistencyReport:
    required_fields = {
        "dataset_version",
        "source_path",
        "contests_count",
        "first_contest",
        "last_contest",
        "content_hash",
    }
    errors: list[str] = []

    missing = sorted(required_fields - set(snapshot))
    if missing:
        errors.append(f"missing dataset snapshot fields: {', '.join(missing)}")

    for field in ("contests_count", "first_contest", "last_contest"):
        if field in snapshot and not isinstance(snapshot[field], int):
            errors.append(f"dataset snapshot field {field} must be an integer")

    if (
        isinstance(snapshot.get("first_contest"), int)
        and isinstance(snapshot.get("last_contest"), int)
        and int(snapshot["first_contest"]) > int(snapshot["last_contest"])
    ):
        errors.append("dataset snapshot first_contest must be <= last_contest")

    content_hash = snapshot.get("content_hash")
    if isinstance(content_hash, str):
        if len(content_hash) != 64:
            errors.append("dataset snapshot content_hash must be a sha256 hex digest")
    elif "content_hash" in snapshot:
        errors.append("dataset snapshot content_hash must be a string")

    if draws is not None and not errors:
        expected = build_dataset_snapshot(
            draws,
            dataset_version=str(snapshot["dataset_version"]),
            source_path=str(snapshot["source_path"]),
        )
        if snapshot["contests_count"] != expected.contests_count:
            errors.append("dataset snapshot contests_count does not match source draws")
        if snapshot["first_contest"] != expected.first_contest:
            errors.append("dataset snapshot first_contest does not match source draws")
        if snapshot["last_contest"] != expected.last_contest:
            errors.append("dataset snapshot last_contest does not match source draws")
        if snapshot["content_hash"] != expected.content_hash:
            errors.append("dataset snapshot content_hash does not match source draws")

    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors))


def validate_temporal_benchmark_manifest(
    manifest: Mapping[str, object],
) -> ExperimentConsistencyReport:
    errors: list[str] = []
    warnings: list[str] = []

    missing = sorted(REQUIRED_MANIFEST_FIELDS - set(manifest))
    if missing:
        errors.append(f"missing temporal benchmark manifest fields: {', '.join(missing)}")

    forbidden = sorted(FORBIDDEN_SUPERVISED_FIELDS & set(manifest))
    if forbidden:
        errors.append(
            "temporal benchmark manifest declares prohibited supervised fields: "
            + ", ".join(forbidden)
        )

    benchmark_type = manifest.get("benchmark_type")
    if benchmark_type not in {
        "temporal_baseline",
        "walk_forward_benchmark",
        "experiment_comparability",
    }:
        errors.append("benchmark_type must declare an official temporal benchmark category")

    adr_references = manifest.get("adr_references")
    if isinstance(adr_references, Sequence) and not isinstance(adr_references, str):
        required_adrs = ("ADR_001", "ADR_002", "ADR_003", "ADR_004", "ADR_005", "ADR_006")
        missing_adrs = [
            required_adr
            for required_adr in required_adrs
            if not any(str(reference).startswith(required_adr) for reference in adr_references)
        ]
        if missing_adrs:
            errors.append("adr_references must include ADR_001 through ADR_006")
    elif "adr_references" in manifest:
        errors.append("adr_references must be a sequence")

    dataset_snapshot = manifest.get("dataset_snapshot")
    if isinstance(dataset_snapshot, Mapping):
        snapshot_report = validate_dataset_snapshot(dataset_snapshot)
        errors.extend(snapshot_report.errors)
    elif "dataset_snapshot" in manifest:
        errors.append("dataset_snapshot must be a structured mapping")

    temporal_split = manifest.get("temporal_split")
    if isinstance(temporal_split, Mapping):
        try:
            split = TemporalSplit(
                split_id=str(temporal_split["split_id"]),
                train_start=int(temporal_split["train_start"]),
                train_end=int(temporal_split["train_end"]),
                test_start=int(temporal_split["test_start"]),
                test_end=int(temporal_split["test_end"]),
            )
        except KeyError as exc:
            errors.append(f"temporal_split missing boundary: {exc.args[0]}")
        else:
            errors.extend(validate_train_test_separation(split).errors)
            last_contest = None
            if isinstance(dataset_snapshot, Mapping):
                last_contest = dataset_snapshot.get("last_contest")
            if isinstance(last_contest, int) and split.test_end > last_contest:
                errors.append("temporal_split test_end exceeds dataset snapshot last_contest")
    elif "temporal_split" in manifest:
        errors.append("temporal_split must be a structured mapping")

    walk_forward = manifest.get("walk_forward")
    if isinstance(walk_forward, Mapping):
        if walk_forward.get("required") is not True:
            warnings.append("walk_forward.required should remain true for supervised benchmarks")
        if walk_forward.get("status") == "executed_model_training":
            errors.append("walk_forward cannot declare executed supervised model training")
    elif "walk_forward" in manifest:
        errors.append("walk_forward must be a structured mapping")

    reproducibility = manifest.get("reproducibility")
    if isinstance(reproducibility, Mapping):
        for field in ("random_seed_policy", "code_version", "dataset_version", "rerun_command"):
            if not reproducibility.get(field):
                errors.append(f"reproducibility.{field} must be declared")
    elif "reproducibility" in manifest:
        errors.append("reproducibility must be a structured mapping")

    prohibitions = manifest.get("prohibitions")
    if isinstance(prohibitions, Mapping):
        if prohibitions.get("ml_training") is not True:
            errors.append("prohibitions.ml_training must remain true in this consolidation")
        if prohibitions.get("score_ml") is not True:
            errors.append("prohibitions.score_ml must remain true in this consolidation")
    elif "prohibitions" in manifest:
        errors.append("prohibitions must be a structured mapping")

    return ExperimentConsistencyReport(
        valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
