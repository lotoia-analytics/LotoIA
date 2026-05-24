from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


TEMPORAL_HISTORY_OPERATIONS = "operational"
TEMPORAL_HISTORY_BENCHMARK = "benchmark"
TEMPORAL_HISTORY_VALIDATION = "validation"
TEMPORAL_HISTORY_EXPANSION = "expansion"
TEMPORAL_HISTORY_ML = "ml"
TEMPORAL_HISTORY_CONFERENCE = "conference"
TEMPORAL_HISTORY_SNAPSHOT = "snapshot"
TEMPORAL_HISTORY_AUDIT = "audit"

CANONICAL_TEMPORAL_HISTORY_CATEGORIES = (
    TEMPORAL_HISTORY_OPERATIONS,
    TEMPORAL_HISTORY_BENCHMARK,
    TEMPORAL_HISTORY_VALIDATION,
    TEMPORAL_HISTORY_EXPANSION,
    TEMPORAL_HISTORY_ML,
    TEMPORAL_HISTORY_CONFERENCE,
    TEMPORAL_HISTORY_SNAPSHOT,
    TEMPORAL_HISTORY_AUDIT,
)


@dataclass(frozen=True, slots=True)
class TemporalHistoryArtifact:
    """One canonical historical artifact participating in temporal governance."""

    name: str
    category: str
    source_kind: str
    description: str
    canonical_location: str
    temporal_policy: str
    leakage_risk: str = "none"

    def as_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "category": self.category,
            "source_kind": self.source_kind,
            "description": self.description,
            "canonical_location": self.canonical_location,
            "temporal_policy": self.temporal_policy,
            "leakage_risk": self.leakage_risk,
        }


@dataclass(frozen=True, slots=True)
class TemporalHistoryValidationReport:
    """Validation result for the temporal history segregation registry."""

    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    def assert_valid(self) -> None:
        if not self.valid:
            raise ValueError("; ".join(self.errors))


def build_canonical_temporal_history_registry() -> tuple[TemporalHistoryArtifact, ...]:
    """Return the canonical segregation used by GT-01."""

    return (
        TemporalHistoryArtifact(
            name="generation_events",
            category=TEMPORAL_HISTORY_OPERATIONS,
            source_kind="sql_table",
            description="Operational generation runs and request metadata.",
            canonical_location="src/lotoia/database/database.py",
            temporal_policy="operation_only",
        ),
        TemporalHistoryArtifact(
            name="generated_games",
            category=TEMPORAL_HISTORY_OPERATIONS,
            source_kind="sql_table",
            description="Operational generated games persisted from the public flow.",
            canonical_location="src/lotoia/database/database.py",
            temporal_policy="operation_only",
        ),
        TemporalHistoryArtifact(
            name="report_events",
            category=TEMPORAL_HISTORY_OPERATIONS,
            source_kind="sql_table",
            description="Operational report emission and user-facing output records.",
            canonical_location="src/lotoia/database/database.py",
            temporal_policy="operation_only",
        ),
        TemporalHistoryArtifact(
            name="feature_usage_events",
            category=TEMPORAL_HISTORY_OPERATIONS,
            source_kind="sql_table",
            description="Operational feature usage telemetry for the public and institutional surfaces.",
            canonical_location="src/lotoia/database/database.py",
            temporal_policy="operation_only",
        ),
        TemporalHistoryArtifact(
            name="workflow_events",
            category=TEMPORAL_HISTORY_OPERATIONS,
            source_kind="sql_table",
            description="Operational workflow execution lifecycle.",
            canonical_location="src/lotoia/database/database.py",
            temporal_policy="operation_only",
        ),
        TemporalHistoryArtifact(
            name="workflow_runs",
            category=TEMPORAL_HISTORY_OPERATIONS,
            source_kind="sql_table",
            description="Operational workflow orchestration run registry.",
            canonical_location="src/lotoia/database/database.py",
            temporal_policy="operation_only",
        ),
        TemporalHistoryArtifact(
            name="workflow_steps",
            category=TEMPORAL_HISTORY_OPERATIONS,
            source_kind="sql_table",
            description="Operational workflow step tracking.",
            canonical_location="src/lotoia/database/database.py",
            temporal_policy="operation_only",
        ),
        TemporalHistoryArtifact(
            name="reset_events",
            category=TEMPORAL_HISTORY_OPERATIONS,
            source_kind="sql_table",
            description="Operational reset and recovery tracking.",
            canonical_location="src/lotoia/database/database.py",
            temporal_policy="operation_only",
        ),
        TemporalHistoryArtifact(
            name="operational_logs",
            category=TEMPORAL_HISTORY_AUDIT,
            source_kind="table_or_log",
            description="Operational log trail used for forensic review.",
            canonical_location="src/lotoia/public/",
            temporal_policy="immutable_audit",
        ),
        TemporalHistoryArtifact(
            name="audit_trail",
            category=TEMPORAL_HISTORY_AUDIT,
            source_kind="table_or_log",
            description="Audit evidence for governance and traceability.",
            canonical_location="src/lotoia/public/",
            temporal_policy="immutable_audit",
        ),
        TemporalHistoryArtifact(
            name="expansion_events",
            category=TEMPORAL_HISTORY_EXPANSION,
            source_kind="sql_table",
            description="Combinatorial expansion history that must remain isolated from benchmark datasets.",
            canonical_location="src/lotoia/database/database.py",
            temporal_policy="expansion_only",
        ),
        TemporalHistoryArtifact(
            name="reconciliation_events",
            category=TEMPORAL_HISTORY_CONFERENCE,
            source_kind="sql_table",
            description="Conference layer used to compare generated games with official results.",
            canonical_location="src/lotoia/database/database.py",
            temporal_policy="post_result_only",
            leakage_risk="future_results",
        ),
        TemporalHistoryArtifact(
            name="reconciliation_runs",
            category=TEMPORAL_HISTORY_CONFERENCE,
            source_kind="sql_table",
            description="Conference orchestration for result comparison.",
            canonical_location="src/lotoia/database/database.py",
            temporal_policy="post_result_only",
            leakage_risk="future_results",
        ),
        TemporalHistoryArtifact(
            name="reconciliation_games",
            category=TEMPORAL_HISTORY_CONFERENCE,
            source_kind="sql_table",
            description="Conference game-level comparison output.",
            canonical_location="src/lotoia/database/database.py",
            temporal_policy="post_result_only",
            leakage_risk="future_results",
        ),
        TemporalHistoryArtifact(
            name="check_events",
            category=TEMPORAL_HISTORY_CONFERENCE,
            source_kind="sql_table",
            description="Official contest checking and hit counting.",
            canonical_location="src/lotoia/database/database.py",
            temporal_policy="post_result_only",
            leakage_risk="future_results",
        ),
        TemporalHistoryArtifact(
            name="imported_contests",
            category=TEMPORAL_HISTORY_VALIDATION,
            source_kind="sql_table",
            description="Official contest history used as temporal baseline for validation.",
            canonical_location="src/lotoia/database/database.py",
            temporal_policy="historical_cutoff_only",
            leakage_risk="future_results",
        ),
        TemporalHistoryArtifact(
            name="benchmark_runs",
            category=TEMPORAL_HISTORY_BENCHMARK,
            source_kind="sql_table",
            description="Benchmark runs comparing LotoIA against statistical baselines.",
            canonical_location="src/lotoia/database/database.py",
            temporal_policy="benchmark_window_only",
        ),
        TemporalHistoryArtifact(
            name="backtest_runs",
            category=TEMPORAL_HISTORY_BENCHMARK,
            source_kind="sql_table",
            description="Backtesting runs with temporal validity requirements.",
            canonical_location="src/lotoia/database/database.py",
            temporal_policy="benchmark_window_only",
        ),
        TemporalHistoryArtifact(
            name="walk_forward_validation_report",
            category=TEMPORAL_HISTORY_VALIDATION,
            source_kind="json_artifact",
            description="Temporal validation report generated by walk-forward evaluation.",
            canonical_location="reports/ml/walk_forward_validation_v0_1_0",
            temporal_policy="strict_train_before_test",
            leakage_risk="future_contest",
        ),
        TemporalHistoryArtifact(
            name="walk_forward_validation_manifest",
            category=TEMPORAL_HISTORY_VALIDATION,
            source_kind="json_artifact",
            description="Manifest guaranteeing walk-forward reproducibility.",
            canonical_location="reports/ml/walk_forward_validation_v0_1_0",
            temporal_policy="strict_train_before_test",
            leakage_risk="future_contest",
        ),
        TemporalHistoryArtifact(
            name="supervised_dataset_manifest",
            category=TEMPORAL_HISTORY_ML,
            source_kind="json_artifact",
            description="Versioned supervised dataset manifest with leakage guards.",
            canonical_location="experiments/supervised_dataset",
            temporal_policy="feature_cutoff_before_label",
            leakage_risk="future_label",
        ),
        TemporalHistoryArtifact(
            name="feature_lineage_manifest",
            category=TEMPORAL_HISTORY_ML,
            source_kind="json_artifact",
            description="Feature lineage metadata for supervised assistance.",
            canonical_location="experiments/ml_feature_lineage",
            temporal_policy="feature_cutoff_before_label",
            leakage_risk="future_label",
        ),
        TemporalHistoryArtifact(
            name="model_registry",
            category=TEMPORAL_HISTORY_ML,
            source_kind="json_artifact",
            description="Versioned registry for supervised models.",
            canonical_location="experiments/ml_models",
            temporal_policy="model_versioned_only",
        ),
        TemporalHistoryArtifact(
            name="calibration_governance",
            category=TEMPORAL_HISTORY_ML,
            source_kind="json_artifact",
            description="Calibration snapshots used for supervised scoring governance.",
            canonical_location="experiments/ml_calibration",
            temporal_policy="model_versioned_only",
        ),
        TemporalHistoryArtifact(
            name="score_ml_artifacts",
            category=TEMPORAL_HISTORY_ML,
            source_kind="python_module",
            description="Supervised scoring logic and calibrated score outputs.",
            canonical_location="src/lotoia/ml/score_ml.py",
            temporal_policy="feature_cutoff_before_label",
            leakage_risk="future_label",
        ),
        TemporalHistoryArtifact(
            name="ml_usage_events",
            category=TEMPORAL_HISTORY_ML,
            source_kind="sql_table",
            description="Supervised assistance usage history used to monitor ML adoption.",
            canonical_location="src/lotoia/database/database.py",
            temporal_policy="feature_cutoff_before_label",
            leakage_risk="future_label",
        ),
        TemporalHistoryArtifact(
            name="snapshots",
            category=TEMPORAL_HISTORY_SNAPSHOT,
            source_kind="sql_table_or_artifact",
            description="Institutional evolution snapshots and runtime state captures.",
            canonical_location="src/lotoia/database/database.py",
            temporal_policy="immutable_snapshot",
        ),
        TemporalHistoryArtifact(
            name="adaptive_governance_reports",
            category=TEMPORAL_HISTORY_SNAPSHOT,
            source_kind="sql_table_or_artifact",
            description="Decision support snapshots for operational governance.",
            canonical_location="src/lotoia/database/database.py",
            temporal_policy="immutable_snapshot",
        ),
        TemporalHistoryArtifact(
            name="runtime_snapshots",
            category=TEMPORAL_HISTORY_SNAPSHOT,
            source_kind="sql_table",
            description="Runtime observability snapshot store.",
            canonical_location="src/lotoia/database/database.py",
            temporal_policy="immutable_snapshot",
        ),
        TemporalHistoryArtifact(
            name="institutional_memory_snapshots",
            category=TEMPORAL_HISTORY_SNAPSHOT,
            source_kind="sql_table",
            description="Institutional memory snapshot archive.",
            canonical_location="src/lotoia/database/database.py",
            temporal_policy="immutable_snapshot",
        ),
        TemporalHistoryArtifact(
            name="institutional_memory_states",
            category=TEMPORAL_HISTORY_SNAPSHOT,
            source_kind="sql_table",
            description="Institutional memory state archive.",
            canonical_location="src/lotoia/database/database.py",
            temporal_policy="immutable_snapshot",
        ),
        TemporalHistoryArtifact(
            name="institutional_memory_lineage",
            category=TEMPORAL_HISTORY_SNAPSHOT,
            source_kind="sql_table",
            description="Institutional memory lineage archive.",
            canonical_location="src/lotoia/database/database.py",
            temporal_policy="immutable_snapshot",
        ),
        TemporalHistoryArtifact(
            name="institutional_memory_replay",
            category=TEMPORAL_HISTORY_SNAPSHOT,
            source_kind="sql_table",
            description="Replay archive for institutional memory.",
            canonical_location="src/lotoia/database/database.py",
            temporal_policy="immutable_snapshot",
        ),
    )


class TemporalHistoryRegistry:
    """Canonical segregation registry for temporal scientific governance."""

    def __init__(self, artifacts: Iterable[TemporalHistoryArtifact] | None = None) -> None:
        self._artifacts = tuple(artifacts) if artifacts is not None else build_canonical_temporal_history_registry()

    def list_artifacts(self) -> tuple[TemporalHistoryArtifact, ...]:
        return self._artifacts

    def list_categories(self) -> tuple[str, ...]:
        categories = []
        for artifact in self._artifacts:
            if artifact.category not in categories:
                categories.append(artifact.category)
        return tuple(categories)

    def list_by_category(self, category: str) -> tuple[TemporalHistoryArtifact, ...]:
        return tuple(artifact for artifact in self._artifacts if artifact.category == category)

    def classify(self, name: str) -> TemporalHistoryArtifact | None:
        for artifact in self._artifacts:
            if artifact.name == name:
                return artifact
        return None

    def table_categories(self) -> dict[str, str]:
        return {artifact.name: artifact.category for artifact in self._artifacts}

    def validate(self) -> TemporalHistoryValidationReport:
        errors: list[str] = []
        warnings: list[str] = []
        seen: dict[str, str] = {}

        if not self._artifacts:
            errors.append("temporal history registry is empty")

        for artifact in self._artifacts:
            if not artifact.name:
                errors.append("temporal history artifact must declare a name")
            if artifact.category not in CANONICAL_TEMPORAL_HISTORY_CATEGORIES:
                errors.append(f"{artifact.name or '<unnamed>'} declares invalid category: {artifact.category}")
            if not artifact.canonical_location:
                errors.append(f"{artifact.name} must declare a canonical location")
            if artifact.name in seen and seen[artifact.name] != artifact.category:
                errors.append(f"{artifact.name} is assigned to multiple categories: {seen[artifact.name]}, {artifact.category}")
            else:
                seen[artifact.name] = artifact.category
            if artifact.leakage_risk in {"future_contest", "future_label"} and artifact.category not in {
                TEMPORAL_HISTORY_VALIDATION,
                TEMPORAL_HISTORY_ML,
                TEMPORAL_HISTORY_CONFERENCE,
            }:
                warnings.append(f"{artifact.name} carries leakage risk metadata but is not isolated in a scientific category")

        required_categories = {
            TEMPORAL_HISTORY_OPERATIONS,
            TEMPORAL_HISTORY_BENCHMARK,
            TEMPORAL_HISTORY_VALIDATION,
            TEMPORAL_HISTORY_EXPANSION,
            TEMPORAL_HISTORY_ML,
            TEMPORAL_HISTORY_CONFERENCE,
            TEMPORAL_HISTORY_SNAPSHOT,
            TEMPORAL_HISTORY_AUDIT,
        }
        missing_categories = sorted(required_categories - set(self.list_categories()))
        if missing_categories:
            errors.append("missing canonical temporal categories: " + ", ".join(missing_categories))

        return TemporalHistoryValidationReport(valid=not errors, errors=tuple(errors), warnings=tuple(warnings))

    def summary(self) -> dict[str, object]:
        return {
            "artifact_count": len(self._artifacts),
            "categories": self.list_categories(),
            "by_category": {
                category: tuple(artifact.name for artifact in self.list_by_category(category))
                for category in self.list_categories()
            },
        }
