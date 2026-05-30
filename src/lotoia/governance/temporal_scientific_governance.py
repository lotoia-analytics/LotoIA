from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite

from lotoia.experiments.temporal_governance import ExperimentConsistencyReport, TemporalSplit, validate_train_test_separation
from lotoia.governance.temporal_history_registry import (
    CANONICAL_TEMPORAL_HISTORY_CATEGORIES,
    TEMPORAL_HISTORY_AUDIT,
    TEMPORAL_HISTORY_BENCHMARK,
    TEMPORAL_HISTORY_CONFERENCE,
    TEMPORAL_HISTORY_EXPANSION,
    TEMPORAL_HISTORY_ML,
    TEMPORAL_HISTORY_OPERATIONS,
    TEMPORAL_HISTORY_SNAPSHOT,
    TEMPORAL_HISTORY_VALIDATION,
    build_canonical_temporal_history_registry,
)

TEMPORAL_SCIENTIFIC_GOVERNANCE_REGISTRY_VERSION = "0.1.0"
TEMPORAL_SCIENTIFIC_GOVERNANCE_STATUS = "temporal_scientific_governance_active"

TEMPORAL_OPERATIONAL_NUCLEI = (
    "jogos_passados",
    "testar_estrategia",
    "comparativos_operacionais",
    "ranking_ml",
    "cobertura_estrutural",
    "analiticas_persistidas",
)

TEMPORAL_FEATURE_IDS = (
    "frequency",
    "delay",
    "sequence",
    "quadras",
    "sum",
    "rows",
    "columns",
    "diagonals",
)

TEMPORAL_MATRIX_STRUCTURES = (
    "rows",
    "columns",
    "diagonals",
    "center",
    "frame",
    "distribution",
)

TEMPORAL_BENCHMARK_STRATEGIES = (
    "ranking_hybrid",
    "expansion",
    "score_ml",
    "random",
    "statistical_baseline",
)

TEMPORAL_BENCHMARK_ROLES = {
    "ranking_hybrid": "baseline_operational",
    "expansion": "structural",
    "score_ml": "supervised",
    "random": "control",
    "statistical_baseline": "scientific_baseline",
}

TEMPORAL_BENCHMARK_METRICS = (
    "average_hits",
    "temporal_stability",
    "drift_temporal",
    "ranking_consistency",
    "traceability_score",
)

TEMPORAL_FEATURE_TYPES = {
    "frequency": "temporal",
    "delay": "temporal",
    "sequence": "temporal",
    "quadras": "structural",
    "sum": "structural",
    "rows": "matrix",
    "columns": "matrix",
    "diagonals": "matrix",
}

TEMPORAL_FEATURE_SCOPES = {
    "frequency": "strictly_before_label_contest",
    "delay": "strictly_before_label_contest",
    "sequence": "strictly_before_label_contest",
    "quadras": "strictly_before_label_contest",
    "sum": "strictly_before_label_contest",
    "rows": "strictly_before_label_contest",
    "columns": "strictly_before_label_contest",
    "diagonals": "strictly_before_label_contest",
}

TEMPORAL_RUNTIME_INTEGRITY_METRICS = (
    "leakage_temporal",
    "datasets_correct",
    "benchmark_clean",
    "historical_segregation",
    "features_valid",
    "temporal_window_valid",
)

__all__ = [
    "TEMPORAL_SCIENTIFIC_GOVERNANCE_REGISTRY_VERSION",
    "TEMPORAL_SCIENTIFIC_GOVERNANCE_STATUS",
    "TEMPORAL_OPERATIONAL_NUCLEI",
    "TEMPORAL_FEATURE_IDS",
    "TEMPORAL_MATRIX_STRUCTURES",
    "TEMPORAL_BENCHMARK_STRATEGIES",
    "TEMPORAL_BENCHMARK_ROLES",
    "TEMPORAL_BENCHMARK_METRICS",
    "TEMPORAL_FEATURE_TYPES",
    "TEMPORAL_FEATURE_SCOPES",
    "TEMPORAL_RUNTIME_INTEGRITY_METRICS",
    "TemporalOperationalNucleus",
    "TemporalBenchmarkStrategy",
    "TemporalBenchmarkEngine",
    "TemporalFeatureDefinition",
    "TemporalFeatureGovernance",
    "TemporalMatrixGeometry",
    "TemporalRuntimeIntegrity",
    "TemporalScientificRuntimeRegistry",
    "build_temporal_operational_nuclei",
    "build_temporal_benchmark_engine",
    "build_temporal_feature_governance",
    "build_temporal_matrix_geometry",
    "build_temporal_runtime_integrity",
    "build_temporal_scientific_runtime_registry",
    "validate_temporal_operational_nuclei",
    "validate_temporal_benchmark_engine",
    "validate_temporal_feature_governance",
    "validate_temporal_matrix_geometry",
    "validate_temporal_runtime_integrity",
    "validate_temporal_scientific_runtime_registry",
]


@dataclass(frozen=True, slots=True)
class TemporalOperationalNucleus:
    nucleus_id: str
    official_artifact: str
    scientific_finality: str
    persistence_scope: str
    temporal_scope: str
    source_tables: tuple[str, ...]
    history_categories: tuple[str, ...]
    metadata: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return {
            "nucleus_id": self.nucleus_id,
            "official_artifact": self.official_artifact,
            "scientific_finality": self.scientific_finality,
            "persistence_scope": self.persistence_scope,
            "temporal_scope": self.temporal_scope,
            "source_tables": self.source_tables,
            "history_categories": self.history_categories,
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class TemporalBenchmarkStrategy:
    strategy: str
    benchmark_role: str
    temporal_split: TemporalSplit
    source_tables: tuple[str, ...]
    historical_metrics: dict[str, float]
    traceability: str
    future_relative_only: bool = True
    walk_forward_required: bool = True

    def as_dict(self) -> dict[str, object]:
        return {
            "strategy": self.strategy,
            "benchmark_role": self.benchmark_role,
            "temporal_split": self.temporal_split.as_dict(),
            "source_tables": self.source_tables,
            "historical_metrics": self.historical_metrics,
            "traceability": self.traceability,
            "future_relative_only": self.future_relative_only,
            "walk_forward_required": self.walk_forward_required,
        }


@dataclass(frozen=True, slots=True)
class TemporalBenchmarkEngine:
    engine_id: str
    benchmark_reference: str
    dataset_version: str
    temporal_split: TemporalSplit
    strategies: tuple[TemporalBenchmarkStrategy, ...]
    summary_metrics: dict[str, float]
    source_tables: tuple[str, ...]
    temporal_policy: str = "future_relative_only"

    def as_dict(self) -> dict[str, object]:
        return {
            "engine_id": self.engine_id,
            "benchmark_reference": self.benchmark_reference,
            "dataset_version": self.dataset_version,
            "temporal_split": self.temporal_split.as_dict(),
            "strategies": [strategy.as_dict() for strategy in self.strategies],
            "summary_metrics": self.summary_metrics,
            "source_tables": self.source_tables,
            "temporal_policy": self.temporal_policy,
        }


@dataclass(frozen=True, slots=True)
class TemporalFeatureDefinition:
    feature_id: str
    feature_name: str
    feature_type: str
    source_module: str
    temporal_scope: str
    description: str
    uses_future_information: bool = False
    uses_label_contest: bool = False
    metadata: dict[str, object] | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "feature_id": self.feature_id,
            "feature_name": self.feature_name,
            "feature_type": self.feature_type,
            "source_module": self.source_module,
            "temporal_scope": self.temporal_scope,
            "description": self.description,
            "uses_future_information": self.uses_future_information,
            "uses_label_contest": self.uses_label_contest,
            "metadata": self.metadata or {},
        }


@dataclass(frozen=True, slots=True)
class TemporalFeatureGovernance:
    registry_version: str
    status: str
    features: tuple[TemporalFeatureDefinition, ...]
    feature_cutoff_policy: str
    anti_leakage_rules: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "registry_version": self.registry_version,
            "status": self.status,
            "features": [feature.as_dict() for feature in self.features],
            "feature_cutoff_policy": self.feature_cutoff_policy,
            "anti_leakage_rules": self.anti_leakage_rules,
        }


@dataclass(frozen=True, slots=True)
class TemporalMatrixGeometry:
    geometry_id: str
    grid_shape: tuple[int, int]
    structures: tuple[str, ...]
    signal_links: tuple[str, ...]
    source_modules: tuple[str, ...]
    temporal_scope: str
    description: str
    metadata: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return {
            "geometry_id": self.geometry_id,
            "grid_shape": self.grid_shape,
            "structures": self.structures,
            "signal_links": self.signal_links,
            "source_modules": self.source_modules,
            "temporal_scope": self.temporal_scope,
            "description": self.description,
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class TemporalRuntimeIntegrity:
    runtime_id: str
    leakage_temporal: bool
    datasets_correct: bool
    benchmark_clean: bool
    historical_segregation: bool
    features_valid: bool
    temporal_window_valid: bool
    notes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "runtime_id": self.runtime_id,
            "leakage_temporal": self.leakage_temporal,
            "datasets_correct": self.datasets_correct,
            "benchmark_clean": self.benchmark_clean,
            "historical_segregation": self.historical_segregation,
            "features_valid": self.features_valid,
            "temporal_window_valid": self.temporal_window_valid,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class TemporalScientificRuntimeRegistry:
    registry_version: str
    status: str
    nuclei: tuple[TemporalOperationalNucleus, ...]
    benchmark_engine: TemporalBenchmarkEngine
    feature_governance: TemporalFeatureGovernance
    matrix_geometry: TemporalMatrixGeometry
    runtime_integrity: TemporalRuntimeIntegrity
    temporal_split: TemporalSplit
    dataset_version: str
    benchmark_reference: str

    def as_dict(self) -> dict[str, object]:
        return {
            "registry_version": self.registry_version,
            "status": self.status,
            "nuclei": [nucleus.as_dict() for nucleus in self.nuclei],
            "benchmark_engine": self.benchmark_engine.as_dict(),
            "feature_governance": self.feature_governance.as_dict(),
            "matrix_geometry": self.matrix_geometry.as_dict(),
            "runtime_integrity": self.runtime_integrity.as_dict(),
            "temporal_split": self.temporal_split.as_dict(),
            "dataset_version": self.dataset_version,
            "benchmark_reference": self.benchmark_reference,
        }


def _finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and isfinite(float(value))


def _require_fields(payload: Mapping[str, object], required: Sequence[str], label: str) -> list[str]:
    missing = [field for field in required if field not in payload]
    return [f"missing {label} fields: {', '.join(missing)}"] if missing else []


def build_temporal_operational_nuclei() -> tuple[TemporalOperationalNucleus, ...]:
    return (
        TemporalOperationalNucleus(
            nucleus_id="jogos_passados",
            official_artifact="contest_history",
            scientific_finality="historical contest baseline",
            persistence_scope="historical_contest_persistence",
            temporal_scope="historical_contests_only",
            source_tables=("imported_contests",),
            history_categories=(TEMPORAL_HISTORY_CONFERENCE, TEMPORAL_HISTORY_VALIDATION),
            metadata={
                "purpose": "contest_history",
                "temporal_scope": "historical_contests_only",
                "scientific_signature": "official_contest_history",
                "persistence_policy": "read_only_histories",
            },
        ),
        TemporalOperationalNucleus(
            nucleus_id="testar_estrategia",
            official_artifact="walk_forward_validation",
            scientific_finality="walk-forward evaluation",
            persistence_scope="validation_artifacts",
            temporal_scope="rolling_forward_validation",
            source_tables=("walk_forward_validation_manifest", "walk_forward_validation_report"),
            history_categories=(TEMPORAL_HISTORY_VALIDATION,),
            metadata={
                "purpose": "walk_forward_validation",
                "temporal_scope": "rolling_forward_validation",
                "scientific_signature": "temporal_validation_artifact",
                "persistence_policy": "validation_only",
            },
        ),
        TemporalOperationalNucleus(
            nucleus_id="comparativos_operacionais",
            official_artifact="temporal_benchmark",
            scientific_finality="temporal benchmark comparison",
            persistence_scope="benchmark_artifacts",
            temporal_scope="future_relative_only",
            source_tables=("benchmark_runs", "backtest_runs"),
            history_categories=(TEMPORAL_HISTORY_BENCHMARK,),
            metadata={
                "purpose": "temporal_benchmark",
                "temporal_scope": "future_relative_only",
                "scientific_signature": "benchmark_comparison_artifact",
                "persistence_policy": "benchmark_only",
            },
        ),
        TemporalOperationalNucleus(
            nucleus_id="ranking_ml",
            official_artifact="supervised_dataset",
            scientific_finality="supervised ranking dataset",
            persistence_scope="ml_datasets",
            temporal_scope="strictly_past_supervised_training",
            source_tables=(
                "supervised_dataset_manifest",
                "feature_lineage_manifest",
                "score_ml_artifacts",
                "ml_usage_events",
            ),
            history_categories=(TEMPORAL_HISTORY_ML,),
            metadata={
                "purpose": "supervised_training",
                "temporal_scope": "strictly_past_supervised_training",
                "scientific_signature": "supervised_dataset_artifact",
                "persistence_policy": "ml_only",
            },
        ),
        TemporalOperationalNucleus(
            nucleus_id="cobertura_estrutural",
            official_artifact="expansion_history",
            scientific_finality="segregated structural coverage history",
            persistence_scope="expansion_history",
            temporal_scope="operational_structural_coverage_history",
            source_tables=("expansion_events",),
            history_categories=(TEMPORAL_HISTORY_EXPANSION,),
            metadata={
                "purpose": "structural_coverage_history",
                "temporal_scope": "operational_structural_coverage_history",
                "scientific_signature": "segregated_structural_coverage_artifact",
                "persistence_policy": "expansion_only",
            },
        ),
        TemporalOperationalNucleus(
            nucleus_id="analiticas_persistidas",
            official_artifact="scientific_artifacts",
            scientific_finality="persisted scientific outputs",
            persistence_scope="scientific_outputs",
            temporal_scope="immutable_scientific_artifacts",
            source_tables=("adaptive_governance_reports", "snapshots", "audit_trail", "operational_logs"),
            history_categories=(TEMPORAL_HISTORY_SNAPSHOT, TEMPORAL_HISTORY_AUDIT, TEMPORAL_HISTORY_OPERATIONS),
            metadata={
                "purpose": "scientific_artifacts",
                "temporal_scope": "immutable_scientific_artifacts",
                "scientific_signature": "scientific_output_artifact",
                "persistence_policy": "append_only",
            },
        ),
    )


def validate_temporal_operational_nuclei(
    nuclei: Sequence[TemporalOperationalNucleus],
) -> ExperimentConsistencyReport:
    errors: list[str] = []
    seen_ids: set[str] = set()
    seen_tables: set[str] = set()
    seen_artifacts: set[str] = set()
    required_ids = set(TEMPORAL_OPERATIONAL_NUCLEI)
    allowed_categories = set(CANONICAL_TEMPORAL_HISTORY_CATEGORIES)

    for nucleus in nuclei:
        if not nucleus.nucleus_id:
            errors.append("nucleus_id is required")
        if nucleus.nucleus_id in seen_ids:
            errors.append(f"duplicated nucleus: {nucleus.nucleus_id}")
        seen_ids.add(nucleus.nucleus_id)
        if nucleus.official_artifact in seen_artifacts:
            errors.append(f"duplicated official artifact: {nucleus.official_artifact}")
        seen_artifacts.add(nucleus.official_artifact)
        if not nucleus.scientific_finality:
            errors.append(f"{nucleus.nucleus_id} scientific_finality is required")
        if not nucleus.persistence_scope:
            errors.append(f"{nucleus.nucleus_id} persistence_scope is required")
        if not nucleus.temporal_scope:
            errors.append(f"{nucleus.nucleus_id} temporal_scope is required")
        if not nucleus.source_tables:
            errors.append(f"{nucleus.nucleus_id} source_tables must be declared")
        if len(nucleus.source_tables) != len(set(nucleus.source_tables)):
            errors.append(f"{nucleus.nucleus_id} source_tables must be unique")
        overlap = seen_tables.intersection(nucleus.source_tables)
        if overlap:
            errors.append(f"source table contamination detected: {', '.join(sorted(overlap))}")
        seen_tables.update(nucleus.source_tables)

        if not nucleus.history_categories:
            errors.append(f"{nucleus.nucleus_id} history_categories must be declared")
        unknown_categories = [category for category in nucleus.history_categories if category not in allowed_categories]
        if unknown_categories:
            errors.append(
                f"{nucleus.nucleus_id} has invalid history categories: {', '.join(sorted(set(unknown_categories)))}"
            )

        metadata = nucleus.metadata
        if not isinstance(metadata, Mapping):
            errors.append(f"{nucleus.nucleus_id} metadata must be structured")
            continue
        for field in ("purpose", "temporal_scope", "scientific_signature", "persistence_policy"):
            if not metadata.get(field):
                errors.append(f"{nucleus.nucleus_id} metadata.{field} must be declared")

    missing = sorted(required_ids - seen_ids)
    if missing:
        errors.append("missing operational nuclei: " + ", ".join(missing))

    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors))


def build_temporal_benchmark_engine(
    *,
    temporal_split: TemporalSplit,
    dataset_version: str,
    benchmark_reference: str,
    metrics: Mapping[str, float] | None = None,
) -> TemporalBenchmarkEngine:
    base_metrics = dict(metrics or {})
    strategies = tuple(
        TemporalBenchmarkStrategy(
            strategy=strategy,
            benchmark_role=TEMPORAL_BENCHMARK_ROLES[strategy],
            temporal_split=temporal_split,
            source_tables=("benchmark_runs", "backtest_runs", "imported_contests"),
            historical_metrics={
                metric_name: float(base_metrics.get(metric_name, 0.0))
                for metric_name in TEMPORAL_BENCHMARK_METRICS
            },
            traceability=f"{benchmark_reference}::{strategy}",
        )
        for strategy in TEMPORAL_BENCHMARK_STRATEGIES
    )
    return TemporalBenchmarkEngine(
        engine_id="temporal_benchmark_engine_v0.1.0",
        benchmark_reference=benchmark_reference,
        dataset_version=dataset_version,
        temporal_split=temporal_split,
        strategies=strategies,
        summary_metrics={
            metric_name: float(base_metrics.get(metric_name, 0.0))
            for metric_name in TEMPORAL_BENCHMARK_METRICS
        },
        source_tables=("benchmark_runs", "backtest_runs", "imported_contests"),
    )


def validate_temporal_benchmark_engine(engine: TemporalBenchmarkEngine) -> ExperimentConsistencyReport:
    errors: list[str] = []
    errors.extend(validate_train_test_separation(engine.temporal_split).errors)

    if not engine.engine_id:
        errors.append("engine_id is required")
    if not engine.dataset_version:
        errors.append("dataset_version is required")
    if not engine.benchmark_reference:
        errors.append("benchmark_reference is required")
    if not engine.source_tables:
        errors.append("source_tables must be declared")
    if engine.temporal_policy != "future_relative_only":
        errors.append("temporal_policy must remain future_relative_only")

    if not isinstance(engine.summary_metrics, Mapping):
        errors.append("summary_metrics must be structured")
    else:
        for metric_name in TEMPORAL_BENCHMARK_METRICS:
            if metric_name not in engine.summary_metrics:
                errors.append(f"summary_metrics.{metric_name} must be declared")
        for metric_name, metric_value in engine.summary_metrics.items():
            if not _finite_number(metric_value):
                errors.append(f"summary_metrics.{metric_name} must be finite")

    strategies = [strategy.strategy for strategy in engine.strategies]
    missing = sorted(set(TEMPORAL_BENCHMARK_STRATEGIES) - set(strategies))
    if missing:
        errors.append("missing benchmark strategies: " + ", ".join(missing))
    if len(set(strategies)) != len(strategies):
        errors.append("benchmark strategies must be unique")

    for strategy in engine.strategies:
        if strategy.benchmark_role != TEMPORAL_BENCHMARK_ROLES.get(strategy.strategy):
            errors.append(f"{strategy.strategy} benchmark role is invalid")
        if not strategy.future_relative_only:
            errors.append(f"{strategy.strategy} must remain future_relative_only")
        if not strategy.walk_forward_required:
            errors.append(f"{strategy.strategy} must remain walk_forward_required")
        errors.extend(validate_train_test_separation(strategy.temporal_split).errors)
        if not strategy.traceability:
            errors.append(f"{strategy.strategy} traceability is required")
        if not isinstance(strategy.historical_metrics, Mapping):
            errors.append(f"{strategy.strategy} historical_metrics must be structured")
        else:
            for metric_name in TEMPORAL_BENCHMARK_METRICS:
                if metric_name not in strategy.historical_metrics:
                    errors.append(f"{strategy.strategy} historical_metrics.{metric_name} must be declared")
            for metric_name, metric_value in strategy.historical_metrics.items():
                if not _finite_number(metric_value):
                    errors.append(f"{strategy.strategy} historical_metrics.{metric_name} must be finite")

    if len(engine.strategies) != len(TEMPORAL_BENCHMARK_STRATEGIES):
        errors.append("benchmark engine must govern one artifact per official strategy")

    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors))


def build_temporal_feature_governance() -> TemporalFeatureGovernance:
    features = tuple(
        TemporalFeatureDefinition(
            feature_id=feature_name,
            feature_name=feature_name,
            feature_type=TEMPORAL_FEATURE_TYPES[feature_name],
            source_module="lotoia.statistics.temporal",
            temporal_scope=TEMPORAL_FEATURE_SCOPES[feature_name],
            description={
                "frequency": "Frequency governance computed strictly from prior contests.",
                "delay": "Delay governance uses only contest history before the label boundary.",
                "sequence": "Sequence governance prioritizes ordered history without future access.",
                "quadras": "Quadra governance preserves combinatorial counts before the label contest.",
                "sum": "Sum governance stays tied to historical aggregates only.",
                "rows": "Matrix row governance stays leakage-free and historical.",
                "columns": "Matrix column governance stays leakage-free and historical.",
                "diagonals": "Matrix diagonal governance stays leakage-free and historical.",
            }[feature_name],
            uses_future_information=False,
            uses_label_contest=False,
            metadata={
                "scientific_signature": f"official_temporal_feature_{feature_name}",
                "governance_mode": "strictly_before_label_contest",
                "future_access_prohibited": True,
            },
        )
        for feature_name in TEMPORAL_FEATURE_IDS
    )
    return TemporalFeatureGovernance(
        registry_version="temporal_feature_governance_v0.1.0",
        status="feature_governance_active",
        features=features,
        feature_cutoff_policy="feature_cutoff_contest < label_contest",
        anti_leakage_rules=(
            "no future contest",
            "no post-label derivation",
            "no benchmark contamination",
            "no leakage across validation windows",
        ),
    )


def validate_temporal_feature_governance(
    governance: TemporalFeatureGovernance,
) -> ExperimentConsistencyReport:
    errors: list[str] = []
    if governance.registry_version != "temporal_feature_governance_v0.1.0":
        errors.append("registry_version must match temporal feature governance version")
    if governance.status != "feature_governance_active":
        errors.append("status must declare feature governance active")
    if governance.feature_cutoff_policy != "feature_cutoff_contest < label_contest":
        errors.append("feature_cutoff_policy must remain feature_cutoff_contest < label_contest")
    if not governance.anti_leakage_rules:
        errors.append("anti_leakage_rules must be declared")

    seen: set[str] = set()
    names: list[str] = []
    for feature in governance.features:
        if feature.feature_name in seen:
            errors.append(f"duplicated feature: {feature.feature_name}")
        seen.add(feature.feature_name)
        names.append(feature.feature_name)
        if feature.feature_name not in TEMPORAL_FEATURE_IDS:
            errors.append(f"invalid official feature: {feature.feature_name}")
        if feature.feature_type != TEMPORAL_FEATURE_TYPES.get(feature.feature_name):
            errors.append(f"{feature.feature_name} feature_type is invalid")
        if feature.temporal_scope != TEMPORAL_FEATURE_SCOPES.get(feature.feature_name):
            errors.append(f"{feature.feature_name} temporal_scope is invalid")
        if feature.uses_future_information:
            errors.append(f"{feature.feature_name} must not use future information")
        if feature.uses_label_contest:
            errors.append(f"{feature.feature_name} must declare uses_label_contest=false")
        metadata = feature.metadata or {}
        if not isinstance(metadata, Mapping):
            errors.append(f"{feature.feature_name} metadata must be structured")
        else:
            if not metadata.get("scientific_signature"):
                errors.append(f"{feature.feature_name} metadata.scientific_signature must be declared")
            if not metadata.get("future_access_prohibited"):
                errors.append(f"{feature.feature_name} metadata.future_access_prohibited must be true")

    missing = sorted(set(TEMPORAL_FEATURE_IDS) - set(names))
    if missing:
        errors.append("missing temporal features: " + ", ".join(missing))

    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors))


def build_temporal_matrix_geometry() -> TemporalMatrixGeometry:
    return TemporalMatrixGeometry(
        geometry_id="lotofacil_matricial_temporal_v0.1.0",
        grid_shape=(5, 5),
        structures=TEMPORAL_MATRIX_STRUCTURES,
        signal_links=(
            "matrix_rows",
            "matrix_columns",
            "matrix_diagonals",
            "center_balance",
            "frame_balance",
            "distribution_balance",
        ),
        source_modules=(
            "lotoia.generator.basic_generator",
            "lotoia.statistics.temporal",
            "lotoia.ml.score_ml",
        ),
        temporal_scope="strictly_before_label_contest",
        description="Temporal geometry for the Lotofácil 5x5 matrix with leakage-free spatial signals.",
        metadata={
            "scientific_signature": "lotofacil_matricial_temporal_geometry",
            "grid_units": 25,
            "rows": 5,
            "columns": 5,
        },
    )


def validate_temporal_matrix_geometry(
    geometry: TemporalMatrixGeometry,
) -> ExperimentConsistencyReport:
    errors: list[str] = []
    if geometry.geometry_id != "lotofacil_matricial_temporal_v0.1.0":
        errors.append("geometry_id must match the Lotofácil temporal geometry version")
    if geometry.grid_shape != (5, 5):
        errors.append("grid_shape must remain 5x5")
    if geometry.temporal_scope != "strictly_before_label_contest":
        errors.append("temporal_scope must remain strictly_before_label_contest")
    if not geometry.structures:
        errors.append("matrix structures must be declared")
    missing = sorted(set(TEMPORAL_MATRIX_STRUCTURES) - set(geometry.structures))
    if missing:
        errors.append("missing matrix structures: " + ", ".join(missing))
    if len(geometry.structures) != len(set(geometry.structures)):
        errors.append("matrix structures must be unique")
    if not geometry.signal_links:
        errors.append("signal_links must be declared")
    if len(geometry.signal_links) != len(set(geometry.signal_links)):
        errors.append("signal_links must be unique")
    if not geometry.source_modules:
        errors.append("source_modules must be declared")
    if not isinstance(geometry.metadata, Mapping):
        errors.append("metadata must be structured")
    else:
        if not geometry.metadata.get("scientific_signature"):
            errors.append("metadata.scientific_signature must be declared")
    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors))


def build_temporal_runtime_integrity(
    *,
    temporal_split: TemporalSplit,
    leakage_temporal: bool = True,
    datasets_correct: bool = True,
    benchmark_clean: bool = True,
    historical_segregation: bool = True,
    features_valid: bool = True,
    temporal_window_valid: bool = True,
    notes: Sequence[str] = (),
) -> TemporalRuntimeIntegrity:
    return TemporalRuntimeIntegrity(
        runtime_id="scientific_runtime_integrity_v0.1.0",
        leakage_temporal=leakage_temporal,
        datasets_correct=datasets_correct,
        benchmark_clean=benchmark_clean,
        historical_segregation=historical_segregation,
        features_valid=features_valid,
        temporal_window_valid=temporal_window_valid,
        notes=tuple(str(note) for note in notes)
        + (f"train_end={temporal_split.train_end}", f"test_start={temporal_split.test_start}"),
    )


def validate_temporal_runtime_integrity(
    integrity: TemporalRuntimeIntegrity,
) -> ExperimentConsistencyReport:
    errors: list[str] = []
    if integrity.runtime_id != "scientific_runtime_integrity_v0.1.0":
        errors.append("runtime_id must match the scientific runtime integrity version")
    for field_name in TEMPORAL_RUNTIME_INTEGRITY_METRICS:
        if getattr(integrity, field_name) is not True:
            errors.append(f"{field_name} must remain true")
    if not isinstance(integrity.notes, tuple):
        errors.append("notes must be a tuple")
    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors))


def build_temporal_scientific_runtime_registry(
    *,
    temporal_split: TemporalSplit,
    dataset_version: str,
    benchmark_reference: str,
    engine_metrics: Mapping[str, float] | None = None,
    notes: Sequence[str] = (),
) -> TemporalScientificRuntimeRegistry:
    nuclei = build_temporal_operational_nuclei()
    benchmark_engine = build_temporal_benchmark_engine(
        temporal_split=temporal_split,
        dataset_version=dataset_version,
        benchmark_reference=benchmark_reference,
        metrics=engine_metrics,
    )
    feature_governance = build_temporal_feature_governance()
    matrix_geometry = build_temporal_matrix_geometry()
    runtime_integrity = build_temporal_runtime_integrity(
        temporal_split=temporal_split,
        notes=notes,
    )
    return TemporalScientificRuntimeRegistry(
        registry_version=TEMPORAL_SCIENTIFIC_GOVERNANCE_REGISTRY_VERSION,
        status=TEMPORAL_SCIENTIFIC_GOVERNANCE_STATUS,
        nuclei=nuclei,
        benchmark_engine=benchmark_engine,
        feature_governance=feature_governance,
        matrix_geometry=matrix_geometry,
        runtime_integrity=runtime_integrity,
        temporal_split=temporal_split,
        dataset_version=dataset_version,
        benchmark_reference=benchmark_reference,
    )


def validate_temporal_scientific_runtime_registry(
    registry: TemporalScientificRuntimeRegistry,
) -> ExperimentConsistencyReport:
    errors: list[str] = []
    if registry.registry_version != TEMPORAL_SCIENTIFIC_GOVERNANCE_REGISTRY_VERSION:
        errors.append("registry_version must match the temporal scientific governance version")
    if registry.status != TEMPORAL_SCIENTIFIC_GOVERNANCE_STATUS:
        errors.append("status must declare temporal scientific governance active")
    if not registry.dataset_version:
        errors.append("dataset_version is required")
    if not registry.benchmark_reference:
        errors.append("benchmark_reference is required")
    errors.extend(validate_train_test_separation(registry.temporal_split).errors)
    errors.extend(validate_temporal_operational_nuclei(registry.nuclei).errors)
    errors.extend(validate_temporal_benchmark_engine(registry.benchmark_engine).errors)
    errors.extend(validate_temporal_feature_governance(registry.feature_governance).errors)
    errors.extend(validate_temporal_matrix_geometry(registry.matrix_geometry).errors)
    errors.extend(validate_temporal_runtime_integrity(registry.runtime_integrity).errors)

    canonical_history_names = {artifact.name for artifact in build_canonical_temporal_history_registry()}
    for nucleus in registry.nuclei:
        for source_table in nucleus.source_tables:
            if source_table not in canonical_history_names:
                errors.append(f"{nucleus.nucleus_id} references non-canonical history source: {source_table}")

    if registry.runtime_integrity.leakage_temporal is not True:
        errors.append("runtime integrity must keep leakage_temporal true")
    if registry.runtime_integrity.datasets_correct is not True:
        errors.append("runtime integrity must keep datasets_correct true")
    if registry.runtime_integrity.benchmark_clean is not True:
        errors.append("runtime integrity must keep benchmark_clean true")
    if registry.runtime_integrity.historical_segregation is not True:
        errors.append("runtime integrity must keep historical_segregation true")
    if registry.runtime_integrity.features_valid is not True:
        errors.append("runtime integrity must keep features_valid true")
    if registry.runtime_integrity.temporal_window_valid is not True:
        errors.append("runtime integrity must keep temporal_window_valid true")

    return ExperimentConsistencyReport(valid=not errors, errors=tuple(errors))
