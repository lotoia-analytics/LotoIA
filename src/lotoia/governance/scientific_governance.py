from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from math import isfinite

from lotoia.experiments.temporal_governance import (
    ExperimentConsistencyReport,
    TemporalSplit,
    validate_supervised_rows,
    validate_temporal_integrity,
    validate_train_test_separation,
)

SCIENTIFIC_GOVERNANCE_REGISTRY_VERSION = "0.1.0"
SCIENTIFIC_GOVERNANCE_STATUS = "scientific_governance_active"

DATASET_OPERATIONAL = "dataset_operational"
DATASET_BENCHMARK = "dataset_benchmark"
DATASET_ML = "dataset_ml"
DATASET_VALIDATION = "dataset_validation"
DATASET_EXPANSION = "dataset_expansion"

BENCHMARK_RANKING_HYBRID = "ranking_hybrid"
BENCHMARK_EXPANSION = "expansion"
BENCHMARK_SCORE_ML = "score_ml"
BENCHMARK_RANDOM = "random"
BENCHMARK_STATISTICAL_BASELINE = "statistical_baseline"

BENCHMARK_STRATEGIES = (
    BENCHMARK_RANKING_HYBRID,
    BENCHMARK_EXPANSION,
    BENCHMARK_SCORE_ML,
    BENCHMARK_RANDOM,
    BENCHMARK_STATISTICAL_BASELINE,
)

SCIENTIFIC_OBSERVABILITY_METRICS = (
    "drift_temporal",
    "score_stability",
    "benchmark_evolution",
    "statistical_degradation",
)

__all__ = [
    "SCIENTIFIC_GOVERNANCE_REGISTRY_VERSION",
    "SCIENTIFIC_GOVERNANCE_STATUS",
    "DATASET_OPERATIONAL",
    "DATASET_BENCHMARK",
    "DATASET_ML",
    "DATASET_VALIDATION",
    "DATASET_EXPANSION",
    "BENCHMARK_RANKING_HYBRID",
    "BENCHMARK_EXPANSION",
    "BENCHMARK_SCORE_ML",
    "BENCHMARK_RANDOM",
    "BENCHMARK_STATISTICAL_BASELINE",
    "BENCHMARK_STRATEGIES",
    "SCIENTIFIC_OBSERVABILITY_METRICS",
    "ScientificDatasetArtifact",
    "ScientificBenchmarkArtifact",
    "ScientificScoreMLContract",
    "ScientificExperimentRecord",
    "ScientificObservabilitySnapshot",
    "ScientificRuntimeContract",
    "ScientificGovernanceRegistry",
    "build_scientific_dataset_registry",
    "build_scientific_benchmark_registry",
    "build_scientific_score_ml_contract",
    "build_anti_leakage_policy",
    "build_scientific_experiment_record",
    "build_scientific_observability_snapshot",
    "build_scientific_runtime_contract",
    "build_scientific_governance_registry",
    "validate_scientific_dataset_artifact",
    "validate_scientific_dataset_registry",
    "validate_scientific_benchmark_artifact",
    "validate_scientific_benchmark_registry",
    "validate_scientific_score_ml_contract",
    "validate_anti_leakage_policy",
    "validate_scientific_experiment_record",
    "validate_scientific_observability_snapshot",
    "validate_scientific_runtime_contract",
    "validate_scientific_governance_registry",
]


@dataclass(frozen=True, slots=True)
class ScientificDatasetArtifact:
    dataset_id: str
    dataset_type: str
    version: str
    source_tables: tuple[str, ...]
    temporal_split: TemporalSplit | None
    metadata: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return {
            "dataset_id": self.dataset_id,
            "dataset_type": self.dataset_type,
            "version": self.version,
            "source_tables": self.source_tables,
            "temporal_split": self.temporal_split.as_dict() if self.temporal_split else None,
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class ScientificBenchmarkArtifact:
    benchmark_id: str
    strategy: str
    temporal_split: TemporalSplit
    dataset_version: str
    source_tables: tuple[str, ...]
    metrics: dict[str, float]

    def as_dict(self) -> dict[str, object]:
        return {
            "benchmark_id": self.benchmark_id,
            "strategy": self.strategy,
            "temporal_split": self.temporal_split.as_dict(),
            "dataset_version": self.dataset_version,
            "source_tables": self.source_tables,
            "metrics": self.metrics,
        }


@dataclass(frozen=True, slots=True)
class ScientificScoreMLContract:
    enabled: bool
    dataset_version: str
    model_version: str
    benchmark_reference: str
    temporal_split: TemporalSplit
    walk_forward_required: bool = True
    anti_leakage_required: bool = True
    supervised_role: str = "auxiliary_incremental_rerank"

    def as_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "dataset_version": self.dataset_version,
            "model_version": self.model_version,
            "benchmark_reference": self.benchmark_reference,
            "temporal_split": self.temporal_split.as_dict(),
            "walk_forward_required": self.walk_forward_required,
            "anti_leakage_required": self.anti_leakage_required,
            "supervised_role": self.supervised_role,
        }


@dataclass(frozen=True, slots=True)
class AntiLeakagePolicy:
    forbidden_sources: tuple[str, ...]
    forbidden_patterns: tuple[str, ...]
    benchmark_requires_walk_forward: bool = True
    train_must_precede_test: bool = True

    def validate_payload(self, payload: Mapping[str, object]) -> ExperimentConsistencyReport:
        errors: list[str] = []
        warnings: list[str] = []

        payload_text = _flatten_payload(payload)
        for forbidden_source in self.forbidden_sources:
            if forbidden_source and forbidden_source in payload_text:
                errors.append(f"payload references forbidden source: {forbidden_source}")
        for forbidden_pattern in self.forbidden_patterns:
            if forbidden_pattern and forbidden_pattern in payload_text:
                errors.append(f"payload contains forbidden pattern: {forbidden_pattern}")

        if self.benchmark_requires_walk_forward and not payload.get("walk_forward_enabled", False):
            warnings.append("walk-forward should be explicitly enabled for scientific benchmarks")

        return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors), warnings=tuple(warnings))


@dataclass(frozen=True, slots=True)
class ScientificExperimentRecord:
    experiment_id: str
    dataset_version: str
    temporal_split: TemporalSplit
    seed: int
    model_version: str
    benchmark_reference: str
    metrics: dict[str, float]
    created_at: str
    walk_forward_required: bool = True

    def as_dict(self) -> dict[str, object]:
        return {
            "experiment_id": self.experiment_id,
            "dataset_version": self.dataset_version,
            "temporal_split": self.temporal_split.as_dict(),
            "seed": self.seed,
            "model_version": self.model_version,
            "benchmark_reference": self.benchmark_reference,
            "metrics": self.metrics,
            "created_at": self.created_at,
            "walk_forward_required": self.walk_forward_required,
        }


@dataclass(frozen=True, slots=True)
class ScientificObservabilitySnapshot:
    drift_temporal: float
    score_stability: float
    benchmark_evolution: float
    statistical_degradation: float
    notes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "drift_temporal": self.drift_temporal,
            "score_stability": self.score_stability,
            "benchmark_evolution": self.benchmark_evolution,
            "statistical_degradation": self.statistical_degradation,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class ScientificRuntimeContract:
    benchmark_continuous: bool
    scientific_observability: bool
    temporal_validation: bool
    supervised_ml: bool
    experiment_governance: bool

    def as_dict(self) -> dict[str, bool]:
        return {
            "benchmark_continuous": self.benchmark_continuous,
            "scientific_observability": self.scientific_observability,
            "temporal_validation": self.temporal_validation,
            "supervised_ml": self.supervised_ml,
            "experiment_governance": self.experiment_governance,
        }


@dataclass(frozen=True, slots=True)
class ScientificGovernanceRegistry:
    registry_version: str
    status: str
    datasets: tuple[ScientificDatasetArtifact, ...]
    benchmarks: tuple[ScientificBenchmarkArtifact, ...]
    score_ml_contract: ScientificScoreMLContract
    anti_leakage_policy: AntiLeakagePolicy
    experiment: ScientificExperimentRecord
    observability: ScientificObservabilitySnapshot
    runtime_contract: ScientificRuntimeContract

    def as_dict(self) -> dict[str, object]:
        return {
            "registry_version": self.registry_version,
            "status": self.status,
            "datasets": [dataset.as_dict() for dataset in self.datasets],
            "benchmarks": [benchmark.as_dict() for benchmark in self.benchmarks],
            "score_ml_contract": self.score_ml_contract.as_dict(),
            "anti_leakage_policy": {
                "forbidden_sources": self.anti_leakage_policy.forbidden_sources,
                "forbidden_patterns": self.anti_leakage_policy.forbidden_patterns,
                "benchmark_requires_walk_forward": self.anti_leakage_policy.benchmark_requires_walk_forward,
                "train_must_precede_test": self.anti_leakage_policy.train_must_precede_test,
            },
            "experiment": self.experiment.as_dict(),
            "observability": self.observability.as_dict(),
            "runtime_contract": self.runtime_contract.as_dict(),
        }


def _is_finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and isfinite(float(value))


def _require_fields(payload: Mapping[str, object], required: Sequence[str], label: str) -> list[str]:
    missing = [field for field in required if field not in payload]
    return [f"missing {label} fields: {', '.join(missing)}"] if missing else []


def validate_scientific_dataset_artifact(artifact: ScientificDatasetArtifact) -> ExperimentConsistencyReport:
    errors: list[str] = []
    if artifact.dataset_type not in {
        DATASET_OPERATIONAL,
        DATASET_BENCHMARK,
        DATASET_ML,
        DATASET_VALIDATION,
        DATASET_EXPANSION,
    }:
        errors.append(f"invalid dataset_type: {artifact.dataset_type}")
    if not artifact.dataset_id:
        errors.append("dataset_id is required")
    if not artifact.version:
        errors.append(f"{artifact.dataset_id} must declare a version")
    if not artifact.source_tables:
        errors.append(f"{artifact.dataset_id} must declare source tables")

    metadata = artifact.metadata
    if not isinstance(metadata, Mapping):
        errors.append(f"{artifact.dataset_id} metadata must be structured")
    else:
        for field in ("purpose", "temporal_scope", "scientific_signature"):
            if not metadata.get(field):
                errors.append(f"{artifact.dataset_id} metadata.{field} must be declared")
        if metadata.get("dataset_role") not in {
            "operational_runtime",
            "scientific_benchmark",
            "supervised_training",
            "walk_forward_validation",
            "expansion_history",
        }:
            errors.append(f"{artifact.dataset_id} metadata.dataset_role is invalid")

    if artifact.temporal_split is not None:
        errors.extend(validate_train_test_separation(artifact.temporal_split).errors)

    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors))


def validate_scientific_dataset_registry(
    datasets: Sequence[ScientificDatasetArtifact],
) -> ExperimentConsistencyReport:
    errors: list[str] = []
    required = {
        DATASET_OPERATIONAL,
        DATASET_BENCHMARK,
        DATASET_ML,
        DATASET_VALIDATION,
        DATASET_EXPANSION,
    }
    seen: set[str] = set()
    versions: list[str] = []

    for dataset in datasets:
        report = validate_scientific_dataset_artifact(dataset)
        errors.extend(report.errors)
        if dataset.dataset_type in seen:
            errors.append(f"duplicated dataset type: {dataset.dataset_type}")
        seen.add(dataset.dataset_type)
        if dataset.version:
            versions.append(dataset.version)

    missing = sorted(required - seen)
    if missing:
        errors.append("missing scientific datasets: " + ", ".join(missing))
    if len(set(versions)) != len(versions):
        errors.append("scientific dataset versions must be unique")

    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors))


def validate_scientific_benchmark_artifact(
    benchmark: ScientificBenchmarkArtifact,
) -> ExperimentConsistencyReport:
    errors: list[str] = []
    if benchmark.strategy not in BENCHMARK_STRATEGIES:
        errors.append(f"invalid benchmark strategy: {benchmark.strategy}")
    if not benchmark.benchmark_id:
        errors.append("benchmark_id is required")
    if not benchmark.dataset_version:
        errors.append(f"{benchmark.benchmark_id} must declare a dataset_version")
    if not benchmark.source_tables:
        errors.append(f"{benchmark.benchmark_id} must declare source tables")
    errors.extend(validate_train_test_separation(benchmark.temporal_split).errors)

    metrics = benchmark.metrics
    if not isinstance(metrics, Mapping):
        errors.append(f"{benchmark.benchmark_id} metrics must be structured")
    else:
        for field in SCIENTIFIC_OBSERVABILITY_METRICS:
            if field not in metrics:
                errors.append(f"{benchmark.benchmark_id} metrics.{field} must be declared")
        for field, value in metrics.items():
            if not _is_finite_number(value):
                errors.append(f"{benchmark.benchmark_id} metrics.{field} must be finite")

    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors))


def validate_scientific_benchmark_registry(
    benchmarks: Sequence[ScientificBenchmarkArtifact],
) -> ExperimentConsistencyReport:
    errors: list[str] = []
    strategies: list[str] = []
    required = set(BENCHMARK_STRATEGIES)

    for benchmark in benchmarks:
        errors.extend(validate_scientific_benchmark_artifact(benchmark).errors)
        strategies.append(benchmark.strategy)

    missing = sorted(required - set(strategies))
    if missing:
        errors.append("missing scientific benchmarks: " + ", ".join(missing))
    if len(set(strategies)) != len(strategies):
        errors.append("scientific benchmark strategies must be unique")

    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors))


def validate_scientific_score_ml_contract(
    contract: ScientificScoreMLContract,
) -> ExperimentConsistencyReport:
    errors: list[str] = []
    if not contract.enabled:
        errors.append("score_ml must be enabled for GT-03")
    if not contract.dataset_version:
        errors.append("dataset_version is required for score_ml governance")
    if not contract.model_version:
        errors.append("model_version is required for score_ml governance")
    if not contract.benchmark_reference:
        errors.append("benchmark_reference is required for score_ml governance")
    if not contract.walk_forward_required:
        errors.append("walk_forward_required must remain true")
    if not contract.anti_leakage_required:
        errors.append("anti_leakage_required must remain true")
    if contract.supervised_role != "auxiliary_incremental_rerank":
        errors.append("supervised_role must remain auxiliary_incremental_rerank")
    errors.extend(validate_train_test_separation(contract.temporal_split).errors)
    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors))


def validate_anti_leakage_policy(policy: AntiLeakagePolicy) -> ExperimentConsistencyReport:
    errors: list[str] = []
    if not policy.forbidden_sources:
        errors.append("forbidden_sources must be declared")
    if not policy.forbidden_patterns:
        errors.append("forbidden_patterns must be declared")
    if not policy.benchmark_requires_walk_forward:
        errors.append("benchmark_requires_walk_forward must remain true")
    if not policy.train_must_precede_test:
        errors.append("train_must_precede_test must remain true")
    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors))


def validate_scientific_experiment_record(record: ScientificExperimentRecord) -> ExperimentConsistencyReport:
    errors: list[str] = []

    if not record.experiment_id:
        errors.append("experiment_id is required")
    if not record.dataset_version:
        errors.append("dataset_version is required")
    if not record.model_version:
        errors.append("model_version is required")
    if not record.benchmark_reference:
        errors.append("benchmark_reference is required")
    if record.seed < 0:
        errors.append("seed must be non-negative")
    if record.walk_forward_required is not True:
        errors.append("walk_forward_required must be true")
    if record.temporal_split.train_end >= record.temporal_split.test_start:
        errors.append("experiment temporal_split must preserve train before test")
    if not record.metrics:
        errors.append("metrics are required")
    else:
        for metric_name, metric_value in record.metrics.items():
            if not _is_finite_number(metric_value):
                errors.append(f"metric {metric_name} must be finite")
    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors))


def validate_scientific_observability_snapshot(
    snapshot: ScientificObservabilitySnapshot,
) -> ExperimentConsistencyReport:
    errors: list[str] = []
    for field_name in SCIENTIFIC_OBSERVABILITY_METRICS:
        value = getattr(snapshot, field_name)
        if not _is_finite_number(value):
            errors.append(f"{field_name} must be a finite number")
        elif not 0.0 <= float(value) <= 1.0:
            errors.append(f"{field_name} must remain in the [0, 1] band")
    if not isinstance(snapshot.notes, tuple):
        errors.append("notes must be a tuple")
    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors))


def validate_scientific_runtime_contract(contract: ScientificRuntimeContract) -> ExperimentConsistencyReport:
    errors: list[str] = []
    if not contract.benchmark_continuous:
        errors.append("benchmark_continuous must be enabled")
    if not contract.scientific_observability:
        errors.append("scientific_observability must be enabled")
    if not contract.temporal_validation:
        errors.append("temporal_validation must be enabled")
    if not contract.supervised_ml:
        errors.append("supervised_ml must be enabled")
    if not contract.experiment_governance:
        errors.append("experiment_governance must be enabled")
    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors))


def validate_scientific_governance_registry(
    registry: ScientificGovernanceRegistry,
) -> ExperimentConsistencyReport:
    errors: list[str] = []
    if registry.registry_version != SCIENTIFIC_GOVERNANCE_REGISTRY_VERSION:
        errors.append("registry_version must match the scientific governance registry version")
    if registry.status != SCIENTIFIC_GOVERNANCE_STATUS:
        errors.append("status must declare the scientific governance baseline")
    errors.extend(validate_scientific_dataset_registry(registry.datasets).errors)
    errors.extend(validate_scientific_benchmark_registry(registry.benchmarks).errors)
    errors.extend(validate_scientific_score_ml_contract(registry.score_ml_contract).errors)
    errors.extend(validate_anti_leakage_policy(registry.anti_leakage_policy).errors)
    errors.extend(
        validate_anti_leakage_payload(
            {
                "walk_forward_enabled": registry.score_ml_contract.walk_forward_required,
                "feature_cutoff_contest": registry.score_ml_contract.temporal_split.train_end,
                "label_contest": registry.score_ml_contract.temporal_split.test_start,
                "source": registry.score_ml_contract.benchmark_reference,
                "benchmark_reference": registry.score_ml_contract.benchmark_reference,
            },
            registry.anti_leakage_policy,
        ).errors
    )
    errors.extend(validate_scientific_experiment_record(registry.experiment).errors)
    errors.extend(validate_scientific_observability_snapshot(registry.observability).errors)
    errors.extend(validate_scientific_runtime_contract(registry.runtime_contract).errors)
    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors))


def build_scientific_dataset_registry() -> tuple[ScientificDatasetArtifact, ...]:
    return (
        ScientificDatasetArtifact(
            dataset_id=DATASET_OPERATIONAL,
            dataset_type=DATASET_OPERATIONAL,
            version="scientific_dataset_operational_v1",
            source_tables=(
                "generation_events",
                "generated_games",
                "report_events",
                "workflow_events",
                "feature_usage_events",
                "operational_logs",
                "audit_trail",
            ),
            temporal_split=None,
            metadata={
                "purpose": "runtime",
                "temporal_scope": "present_runtime_only",
                "scientific_signature": "operational_runtime_scientific_dataset",
                "dataset_role": "operational_runtime",
            },
        ),
        ScientificDatasetArtifact(
            dataset_id=DATASET_BENCHMARK,
            dataset_type=DATASET_BENCHMARK,
            version="scientific_dataset_benchmark_v1",
            source_tables=("benchmark_runs", "backtest_runs", "imported_contests", "temporal_benchmark_runs"),
            temporal_split=None,
            metadata={
                "purpose": "benchmark",
                "temporal_scope": "past_and_holdout_only",
                "scientific_signature": "temporal_benchmark_scientific_dataset",
                "dataset_role": "scientific_benchmark",
            },
        ),
        ScientificDatasetArtifact(
            dataset_id=DATASET_ML,
            dataset_type=DATASET_ML,
            version="scientific_dataset_ml_v1",
            source_tables=(
                "score_ml_artifacts",
                "feature_lineage_manifest",
                "ml_usage_events",
                "supervised_dataset_manifest",
                "walk_forward_validation_manifest",
            ),
            temporal_split=None,
            metadata={
                "purpose": "training",
                "temporal_scope": "strictly_past_supervised_training",
                "scientific_signature": "supervised_ml_scientific_dataset",
                "dataset_role": "supervised_training",
            },
        ),
        ScientificDatasetArtifact(
            dataset_id=DATASET_VALIDATION,
            dataset_type=DATASET_VALIDATION,
            version="scientific_dataset_validation_v1",
            source_tables=("walk_forward_validation_report", "walk_forward_validation_manifest", "validation_runs"),
            temporal_split=None,
            metadata={
                "purpose": "walk_forward_validation",
                "temporal_scope": "rolling_forward_validation",
                "scientific_signature": "walk_forward_validation_dataset",
                "dataset_role": "walk_forward_validation",
            },
        ),
        ScientificDatasetArtifact(
            dataset_id=DATASET_EXPANSION,
            dataset_type=DATASET_EXPANSION,
            version="scientific_dataset_expansion_v1",
            source_tables=("expansion_events", "expansion_history"),
            temporal_split=None,
            metadata={
                "purpose": "expansion",
                "temporal_scope": "operational_expansion_history",
                "scientific_signature": "expansion_scientific_dataset",
                "dataset_role": "expansion_history",
            },
        ),
    )


def build_scientific_benchmark_registry(
    *,
    temporal_split: TemporalSplit,
    dataset_version: str,
    metrics: Mapping[str, float] | None = None,
) -> tuple[ScientificBenchmarkArtifact, ...]:
    base_metrics = dict(metrics or {})
    return tuple(
        ScientificBenchmarkArtifact(
            benchmark_id=f"benchmark-{strategy}",
            strategy=strategy,
            temporal_split=temporal_split,
            dataset_version=dataset_version,
            source_tables=("benchmark_runs", "backtest_runs", "imported_contests"),
            metrics={
                "average_hits": float(base_metrics.get("average_hits", 0.0)),
                "stability": float(base_metrics.get("stability", 0.0)),
                "correlation": float(base_metrics.get("correlation", 0.0)),
                "drift_temporal": float(base_metrics.get("drift_temporal", 0.0)),
                "score_stability": float(base_metrics.get("score_stability", 0.0)),
                "benchmark_evolution": float(base_metrics.get("benchmark_evolution", 0.0)),
                "statistical_degradation": float(base_metrics.get("statistical_degradation", 0.0)),
            },
        )
        for strategy in BENCHMARK_STRATEGIES
    )


def build_scientific_score_ml_contract(
    *,
    temporal_split: TemporalSplit,
    dataset_version: str,
    model_version: str,
    benchmark_reference: str,
    enabled: bool = True,
    walk_forward_required: bool = True,
    anti_leakage_required: bool = True,
    supervised_role: str = "auxiliary_incremental_rerank",
) -> ScientificScoreMLContract:
    return ScientificScoreMLContract(
        enabled=enabled,
        dataset_version=dataset_version,
        model_version=model_version,
        benchmark_reference=benchmark_reference,
        temporal_split=temporal_split,
        walk_forward_required=walk_forward_required,
        anti_leakage_required=anti_leakage_required,
        supervised_role=supervised_role,
    )


def validate_benchmark_temporal_integrity(
    *,
    contests: Iterable[int],
    temporal_split: TemporalSplit,
) -> ExperimentConsistencyReport:
    integrity = validate_temporal_integrity(contests)
    if not integrity.valid:
        return integrity
    return validate_train_test_separation(temporal_split)


def build_anti_leakage_policy() -> AntiLeakagePolicy:
    return AntiLeakagePolicy(
        forbidden_sources=(
            "future_contest",
            "future_label",
            "post_result_only",
            "temporal_leakage",
            "benchmark_contaminated",
            "contest_after_cutoff",
            "post_cutoff_draws",
        ),
        forbidden_patterns=(
            "score_ml=derived_from_future",
            "contest_after_cutoff",
            "future_statistics",
            "future_contest_statistics",
            "future_label",
        ),
        benchmark_requires_walk_forward=True,
        train_must_precede_test=True,
    )


def build_scientific_experiment_record(
    *,
    experiment_id: str,
    dataset_version: str,
    temporal_split: TemporalSplit,
    seed: int,
    model_version: str,
    benchmark_reference: str,
    metrics: Mapping[str, float],
    created_at: str,
    walk_forward_required: bool = True,
) -> ScientificExperimentRecord:
    return ScientificExperimentRecord(
        experiment_id=experiment_id,
        dataset_version=dataset_version,
        temporal_split=temporal_split,
        seed=seed,
        model_version=model_version,
        benchmark_reference=benchmark_reference,
        metrics={str(key): float(value) for key, value in metrics.items()},
        created_at=created_at,
        walk_forward_required=walk_forward_required,
    )


def validate_anti_leakage_payload(
    payload: Mapping[str, object],
    policy: AntiLeakagePolicy | None = None,
) -> ExperimentConsistencyReport:
    active_policy = policy or build_anti_leakage_policy()
    report = active_policy.validate_payload(payload)
    errors = list(report.errors)
    warnings = list(report.warnings)

    for field in ("feature_cutoff_contest", "label_contest"):
        if field in payload and not isinstance(payload[field], int):
            errors.append(f"{field} must be an integer")

    if isinstance(payload.get("feature_cutoff_contest"), int) and isinstance(
        payload.get("label_contest"), int
    ):
        if int(payload["feature_cutoff_contest"]) >= int(payload["label_contest"]):
            errors.append("feature_cutoff_contest must be strictly before label_contest")

    if payload.get("walk_forward_enabled") is not True:
        warnings.append("walk-forward should stay explicitly enabled")

    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors), warnings=tuple(warnings))


def build_scientific_observability_snapshot(
    *,
    drift_temporal: float,
    score_stability: float,
    benchmark_evolution: float,
    statistical_degradation: float,
    notes: Iterable[str] = (),
) -> ScientificObservabilitySnapshot:
    return ScientificObservabilitySnapshot(
        drift_temporal=drift_temporal,
        score_stability=score_stability,
        benchmark_evolution=benchmark_evolution,
        statistical_degradation=statistical_degradation,
        notes=tuple(str(note) for note in notes),
    )


def build_scientific_runtime_contract(
    *,
    benchmark_continuous: bool = True,
    scientific_observability: bool = True,
    temporal_validation: bool = True,
    supervised_ml: bool = True,
    experiment_governance: bool = True,
) -> ScientificRuntimeContract:
    return ScientificRuntimeContract(
        benchmark_continuous=benchmark_continuous,
        scientific_observability=scientific_observability,
        temporal_validation=temporal_validation,
        supervised_ml=supervised_ml,
        experiment_governance=experiment_governance,
    )


def build_scientific_governance_registry(
    *,
    temporal_split: TemporalSplit,
    dataset_version: str,
    model_version: str,
    benchmark_reference: str,
    seed: int,
    created_at: str,
    observability: ScientificObservabilitySnapshot | None = None,
    runtime_contract: ScientificRuntimeContract | None = None,
    anti_leakage_policy: AntiLeakagePolicy | None = None,
) -> ScientificGovernanceRegistry:
    observability_snapshot = observability or build_scientific_observability_snapshot(
        drift_temporal=0.0,
        score_stability=0.0,
        benchmark_evolution=0.0,
        statistical_degradation=0.0,
        notes=("scientific_governance_initialized",),
    )
    runtime = runtime_contract or build_scientific_runtime_contract()
    anti_leakage = anti_leakage_policy or build_anti_leakage_policy()
    return ScientificGovernanceRegistry(
        registry_version=SCIENTIFIC_GOVERNANCE_REGISTRY_VERSION,
        status=SCIENTIFIC_GOVERNANCE_STATUS,
        datasets=build_scientific_dataset_registry(),
        benchmarks=build_scientific_benchmark_registry(
            temporal_split=temporal_split,
            dataset_version=dataset_version,
        ),
        score_ml_contract=build_scientific_score_ml_contract(
            temporal_split=temporal_split,
            dataset_version=dataset_version,
            model_version=model_version,
            benchmark_reference=benchmark_reference,
        ),
        anti_leakage_policy=anti_leakage,
        experiment=build_scientific_experiment_record(
            experiment_id=f"scientific-experiment-{dataset_version}",
            dataset_version=dataset_version,
            temporal_split=temporal_split,
            seed=seed,
            model_version=model_version,
            benchmark_reference=benchmark_reference,
            metrics={
                "benchmark_average_hits": 0.0,
                "score_ml_average_hits": 0.0,
                "average_hit_delta": 0.0,
            },
            created_at=created_at,
        ),
        observability=observability_snapshot,
        runtime_contract=runtime,
    )


def _flatten_payload(payload: Mapping[str, object]) -> str:
    parts: list[str] = []
    for key, value in payload.items():
        parts.append(str(key))
        if isinstance(value, Mapping):
            parts.append(_flatten_payload(value))
        elif isinstance(value, Sequence) and not isinstance(value, str):
            parts.extend(str(item) for item in value)
        else:
            parts.append(str(value))
    return " ".join(parts)
