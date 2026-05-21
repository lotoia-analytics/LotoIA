"""Scientific experiment governance primitives for LotoIA."""

from lotoia.experiments.temporal_governance import (
    ExperimentConsistencyReport,
    TemporalSplit,
    build_walk_forward_splits,
    validate_experiment_manifest,
    validate_supervised_rows,
    validate_temporal_integrity,
    validate_train_test_separation,
)
from lotoia.experiments.supervised_dataset import (
    SUPERVISED_DATASET_REGISTRY_VERSION,
    SUPERVISED_DATASET_STATUS,
    SupervisedSampleBoundary,
    validate_dataset_lineage,
    validate_feature_manifest,
    validate_supervised_dataset_manifest,
    validate_supervised_dataset_registry,
    validate_supervised_sample_boundaries,
    validate_target_manifest,
    validate_temporal_feature_contract,
)
from lotoia.experiments.supervised_scoring import (
    SUPERVISED_SCORING_REGISTRY_VERSION,
    SUPERVISED_SCORING_STATUS,
    validate_score_ml_manifest,
    validate_score_ml_rows,
    validate_supervised_scoring_registry,
)
from lotoia.experiments.longitudinal_baseline import (
    DEFAULT_CHECKPOINTS,
    DEFAULT_LONGITUDINAL_DIR,
    LongitudinalBaselineResult,
    run_longitudinal_baseline,
)

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
