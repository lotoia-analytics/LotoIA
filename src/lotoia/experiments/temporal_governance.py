from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class TemporalSplit:
    """Declared temporal boundary for benchmark or supervised validation."""

    split_id: str
    train_start: int
    train_end: int
    test_start: int
    test_end: int

    def as_dict(self) -> dict[str, int | str]:
        return {
            "split_id": self.split_id,
            "train_start": self.train_start,
            "train_end": self.train_end,
            "test_start": self.test_start,
            "test_end": self.test_end,
        }


@dataclass(frozen=True)
class ExperimentConsistencyReport:
    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    def assert_valid(self) -> None:
        if not self.valid:
            raise ValueError("; ".join(self.errors))


def validate_temporal_integrity(contests: Iterable[int]) -> ExperimentConsistencyReport:
    contest_list = list(contests)
    errors: list[str] = []

    if not contest_list:
        errors.append("temporal series is empty")

    invalid_contests = [contest for contest in contest_list if contest < 1]
    if invalid_contests:
        errors.append("contest identifiers must be positive integers")

    if contest_list != sorted(contest_list):
        errors.append("contest series must be strictly ordered by time")

    if len(set(contest_list)) != len(contest_list):
        errors.append("contest series contains duplicated contest identifiers")

    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors))


def validate_train_test_separation(split: TemporalSplit) -> ExperimentConsistencyReport:
    errors: list[str] = []

    if split.train_start > split.train_end:
        errors.append("training window must have train_start <= train_end")
    if split.test_start > split.test_end:
        errors.append("test window must have test_start <= test_end")
    if split.train_end >= split.test_start:
        errors.append("training window must end before test window starts")
    if min(split.train_start, split.train_end, split.test_start, split.test_end) < 1:
        errors.append("temporal split boundaries must be positive")

    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors))


def build_walk_forward_splits(
    contests: Sequence[int],
    *,
    min_train_size: int,
    test_size: int,
    step_size: int = 1,
) -> list[TemporalSplit]:
    integrity = validate_temporal_integrity(contests)
    integrity.assert_valid()

    if min_train_size < 1:
        raise ValueError("min_train_size must be positive")
    if test_size < 1:
        raise ValueError("test_size must be positive")
    if step_size < 1:
        raise ValueError("step_size must be positive")
    if len(contests) < min_train_size + test_size:
        raise ValueError("not enough contests for the requested walk-forward structure")

    splits: list[TemporalSplit] = []
    split_number = 1
    train_end_index = min_train_size - 1

    while train_end_index + test_size < len(contests):
        test_start_index = train_end_index + 1
        test_end_index = train_end_index + test_size
        split = TemporalSplit(
            split_id=f"wf_{split_number:03d}",
            train_start=contests[0],
            train_end=contests[train_end_index],
            test_start=contests[test_start_index],
            test_end=contests[test_end_index],
        )
        validate_train_test_separation(split).assert_valid()
        splits.append(split)
        split_number += 1
        train_end_index += step_size

    return splits


def validate_supervised_rows(rows: Iterable[Mapping[str, object]]) -> ExperimentConsistencyReport:
    errors: list[str] = []

    for index, row in enumerate(rows):
        if "feature_cutoff_contest" not in row or "label_contest" not in row:
            errors.append(f"row {index} must declare feature_cutoff_contest and label_contest")
            continue

        feature_cutoff = row["feature_cutoff_contest"]
        label_contest = row["label_contest"]
        if not isinstance(feature_cutoff, int) or not isinstance(label_contest, int):
            errors.append(f"row {index} temporal boundaries must be integers")
            continue

        if feature_cutoff >= label_contest:
            errors.append(f"row {index} leaks future information into supervised features")

        if "score_ml" in row:
            errors.append(f"row {index} must not contain score_ml in governance baseline")

    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors))


def validate_experiment_manifest(manifest: Mapping[str, object]) -> ExperimentConsistencyReport:
    required_fields = {
        "experiment_id",
        "created_at",
        "dataset_version",
        "code_version",
        "temporal_split",
        "benchmark_reference",
        "reproducibility",
    }
    errors: list[str] = []
    warnings: list[str] = []

    missing = sorted(required_fields - set(manifest))
    if missing:
        errors.append(f"missing required manifest fields: {', '.join(missing)}")

    forbidden = {"score_ml", "trained_model_path", "inference_enabled"}
    present_forbidden = sorted(forbidden & set(manifest))
    if present_forbidden:
        errors.append(
            "manifest declares supervised execution fields prohibited in the baseline: "
            + ", ".join(present_forbidden)
        )

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
            split_report = validate_train_test_separation(split)
            errors.extend(split_report.errors)
    elif "temporal_split" in manifest:
        errors.append("temporal_split must be a structured mapping")

    reproducibility = manifest.get("reproducibility")
    if isinstance(reproducibility, Mapping):
        if not reproducibility.get("random_seed_policy"):
            warnings.append("reproducibility.random_seed_policy is not declared")
        if not reproducibility.get("dataset_snapshot"):
            warnings.append("reproducibility.dataset_snapshot is not declared")
    elif "reproducibility" in manifest:
        errors.append("reproducibility must be a structured mapping")

    return ExperimentConsistencyReport(
        valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
