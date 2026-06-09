"""Scientific experiment governance primitives for LotoIA."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "ExperimentConsistencyReport",
    "SUPERVISED_DATASET_REGISTRY_VERSION",
    "SUPERVISED_DATASET_STATUS",
    "SUPERVISED_SCORING_REGISTRY_VERSION",
    "SUPERVISED_SCORING_STATUS",
    "DEFAULT_CHECKPOINTS",
    "DEFAULT_LONGITUDINAL_DIR",
    "SupervisedSampleBoundary",
    "TemporalSplit",
    "LongitudinalBaselineResult",
    "IA_STRUCTURAL_EXPERIMENT_VERSION",
    "IA_STRUCTURAL_ENGINE_VERSION",
    "DEFAULT_IA_STRUCTURAL_DIR",
    "StructuralPoolObservation",
    "StructuralContestReplay",
    "IAStructuralExperimentResult",
    "run_ia_structural_experiment",
    "HB_GEOMETRY_AUDIT_VERSION",
    "HB_GEOMETRY_ENGINE_VERSION",
    "DEFAULT_HB_GEOMETRY_DIR",
    "HBGeometryScenarioResult",
    "HBGeometryAuditResult",
    "run_hb_geometry_audit",
    "TEMPORAL_LONGITUDINAL_BENCHMARK_VERSION",
    "TemporalLongitudinalBenchmarkResult",
    "build_walk_forward_splits",
    "validate_dataset_lineage",
    "validate_experiment_manifest",
    "validate_feature_manifest",
    "validate_score_ml_manifest",
    "validate_score_ml_rows",
    "validate_supervised_dataset_manifest",
    "validate_supervised_dataset_registry",
    "validate_supervised_sample_boundaries",
    "validate_supervised_scoring_registry",
    "validate_supervised_rows",
    "validate_target_manifest",
    "validate_temporal_feature_contract",
    "validate_temporal_integrity",
    "validate_train_test_separation",
    "run_longitudinal_baseline",
]

_EXPORTS: dict[str, tuple[str, str]] = {
    "ExperimentConsistencyReport": ("lotoia.experiments.temporal_governance", "ExperimentConsistencyReport"),
    "TemporalSplit": ("lotoia.experiments.temporal_governance", "TemporalSplit"),
    "build_walk_forward_splits": ("lotoia.experiments.temporal_governance", "build_walk_forward_splits"),
    "validate_experiment_manifest": ("lotoia.experiments.temporal_governance", "validate_experiment_manifest"),
    "validate_supervised_rows": ("lotoia.experiments.temporal_governance", "validate_supervised_rows"),
    "validate_temporal_integrity": ("lotoia.experiments.temporal_governance", "validate_temporal_integrity"),
    "validate_train_test_separation": ("lotoia.experiments.temporal_governance", "validate_train_test_separation"),
    "SUPERVISED_DATASET_REGISTRY_VERSION": ("lotoia.experiments.supervised_dataset", "SUPERVISED_DATASET_REGISTRY_VERSION"),
    "SUPERVISED_DATASET_STATUS": ("lotoia.experiments.supervised_dataset", "SUPERVISED_DATASET_STATUS"),
    "SupervisedSampleBoundary": ("lotoia.experiments.supervised_dataset", "SupervisedSampleBoundary"),
    "validate_dataset_lineage": ("lotoia.experiments.supervised_dataset", "validate_dataset_lineage"),
    "validate_feature_manifest": ("lotoia.experiments.supervised_dataset", "validate_feature_manifest"),
    "validate_supervised_dataset_manifest": ("lotoia.experiments.supervised_dataset", "validate_supervised_dataset_manifest"),
    "validate_supervised_dataset_registry": ("lotoia.experiments.supervised_dataset", "validate_supervised_dataset_registry"),
    "validate_supervised_sample_boundaries": ("lotoia.experiments.supervised_dataset", "validate_supervised_sample_boundaries"),
    "validate_target_manifest": ("lotoia.experiments.supervised_dataset", "validate_target_manifest"),
    "validate_temporal_feature_contract": ("lotoia.experiments.supervised_dataset", "validate_temporal_feature_contract"),
    "SUPERVISED_SCORING_REGISTRY_VERSION": ("lotoia.experiments.supervised_scoring", "SUPERVISED_SCORING_REGISTRY_VERSION"),
    "SUPERVISED_SCORING_STATUS": ("lotoia.experiments.supervised_scoring", "SUPERVISED_SCORING_STATUS"),
    "validate_score_ml_manifest": ("lotoia.experiments.supervised_scoring", "validate_score_ml_manifest"),
    "validate_score_ml_rows": ("lotoia.experiments.supervised_scoring", "validate_score_ml_rows"),
    "validate_supervised_scoring_registry": ("lotoia.experiments.supervised_scoring", "validate_supervised_scoring_registry"),
    "DEFAULT_CHECKPOINTS": ("lotoia.experiments.longitudinal_baseline", "DEFAULT_CHECKPOINTS"),
    "DEFAULT_LONGITUDINAL_DIR": ("lotoia.experiments.longitudinal_baseline", "DEFAULT_LONGITUDINAL_DIR"),
    "LongitudinalBaselineResult": ("lotoia.experiments.longitudinal_baseline", "LongitudinalBaselineResult"),
    "run_longitudinal_baseline": ("lotoia.experiments.longitudinal_baseline", "run_longitudinal_baseline"),
    "IA_STRUCTURAL_EXPERIMENT_VERSION": ("lotoia.experiments.ia_structural_regulator", "IA_STRUCTURAL_EXPERIMENT_VERSION"),
    "IA_STRUCTURAL_ENGINE_VERSION": ("lotoia.experiments.ia_structural_regulator", "IA_STRUCTURAL_ENGINE_VERSION"),
    "DEFAULT_IA_STRUCTURAL_DIR": ("lotoia.experiments.ia_structural_regulator", "DEFAULT_IA_STRUCTURAL_DIR"),
    "StructuralPoolObservation": ("lotoia.experiments.ia_structural_regulator", "StructuralPoolObservation"),
    "StructuralContestReplay": ("lotoia.experiments.ia_structural_regulator", "StructuralContestReplay"),
    "IAStructuralExperimentResult": ("lotoia.experiments.ia_structural_regulator", "IAStructuralExperimentResult"),
    "run_ia_structural_experiment": ("lotoia.experiments.ia_structural_regulator", "run_ia_structural_experiment"),
    "HB_GEOMETRY_AUDIT_VERSION": ("lotoia.experiments.hb_geometry_audit", "HB_GEOMETRY_AUDIT_VERSION"),
    "HB_GEOMETRY_ENGINE_VERSION": ("lotoia.experiments.hb_geometry_audit", "HB_GEOMETRY_ENGINE_VERSION"),
    "DEFAULT_HB_GEOMETRY_DIR": ("lotoia.experiments.hb_geometry_audit", "DEFAULT_HB_GEOMETRY_DIR"),
    "HBGeometryScenarioResult": ("lotoia.experiments.hb_geometry_audit", "HBGeometryScenarioResult"),
    "HBGeometryAuditResult": ("lotoia.experiments.hb_geometry_audit", "HBGeometryAuditResult"),
    "run_hb_geometry_audit": ("lotoia.experiments.hb_geometry_audit", "run_hb_geometry_audit"),
    "TEMPORAL_LONGITUDINAL_BENCHMARK_VERSION": (
        "lotoia.experiments.longitudinal_temporal",
        "TEMPORAL_LONGITUDINAL_BENCHMARK_VERSION",
    ),
    "TemporalLongitudinalBenchmarkResult": (
        "lotoia.experiments.longitudinal_temporal",
        "TemporalLongitudinalBenchmarkResult",
    ),
    "run_longitudinal_temporal_benchmark": (
        "lotoia.experiments.longitudinal_temporal",
        "run_longitudinal_temporal_benchmark",
    ),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
