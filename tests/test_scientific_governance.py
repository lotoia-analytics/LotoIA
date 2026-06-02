from __future__ import annotations

from lotoia.experiments.temporal_governance import TemporalSplit
from lotoia.governance.scientific_governance import (
    BENCHMARK_STRATEGIES,
    DATASET_BENCHMARK,
    DATASET_EXPANSION,
    DATASET_ML,
    DATASET_OPERATIONAL,
    DATASET_VALIDATION,
    ScientificGovernanceRegistry,
    ScientificPolicy15BaselineGovernance,
    build_anti_leakage_policy,
    build_scientific_benchmark_registry,
    build_scientific_dataset_registry,
    build_scientific_experiment_record,
    build_scientific_governance_registry,
    build_scientific_observability_snapshot,
    build_scientific_policy_15_baseline_governance,
    build_scientific_runtime_contract,
    build_scientific_score_ml_contract,
    validate_anti_leakage_payload,
    validate_scientific_benchmark_registry,
    validate_scientific_dataset_registry,
    validate_scientific_experiment_record,
    validate_scientific_governance_registry,
    validate_scientific_observability_snapshot,
    validate_scientific_policy_15_baseline_governance,
    validate_scientific_runtime_contract,
    validate_scientific_score_ml_contract,
)


def _temporal_split() -> TemporalSplit:
    return TemporalSplit(
        split_id="wf_001",
        train_start=1,
        train_end=10,
        test_start=11,
        test_end=12,
    )


def test_scientific_governance_registry_is_complete_and_valid() -> None:
    registry = build_scientific_governance_registry(
        temporal_split=_temporal_split(),
        dataset_version="scientific-dataset-v1",
        model_version="historical_recalibrated_v2",
        benchmark_reference="experiments/temporal_benchmark/manifests/temporal_baseline_v0_1_0.json",
        seed=42,
        created_at="2026-05-24T00:00:00+00:00",
    )

    report = validate_scientific_governance_registry(registry)

    assert isinstance(registry, ScientificGovernanceRegistry)
    assert report.valid is True
    assert report.errors == ()
    assert {dataset.dataset_id for dataset in registry.datasets} == {
        DATASET_OPERATIONAL,
        DATASET_BENCHMARK,
        DATASET_ML,
        DATASET_VALIDATION,
        DATASET_EXPANSION,
    }
    assert {benchmark.strategy for benchmark in registry.benchmarks} == set(BENCHMARK_STRATEGIES)


def test_scientific_dataset_registry_and_benchmark_registry_cover_official_sources() -> None:
    datasets = build_scientific_dataset_registry()
    benchmark_registry = build_scientific_benchmark_registry(
        temporal_split=_temporal_split(),
        dataset_version="scientific-dataset-v1",
        metrics={
            "average_hits": 0.42,
            "stability": 0.88,
            "correlation": 0.66,
            "drift_temporal": 0.05,
            "score_stability": 0.91,
        },
    )

    dataset_report = validate_scientific_dataset_registry(datasets)
    benchmark_report = validate_scientific_benchmark_registry(benchmark_registry)

    assert dataset_report.valid is True
    assert benchmark_report.valid is True
    assert {dataset.dataset_id for dataset in datasets} == {
        DATASET_OPERATIONAL,
        DATASET_BENCHMARK,
        DATASET_ML,
        DATASET_VALIDATION,
        DATASET_EXPANSION,
    }
    assert {benchmark.strategy for benchmark in benchmark_registry} == set(BENCHMARK_STRATEGIES)


def test_score_ml_governance_requires_walk_forward_and_auxiliary_role() -> None:
    contract = build_scientific_score_ml_contract(
        temporal_split=_temporal_split(),
        dataset_version="scientific-dataset-v1",
        model_version="historical_recalibrated_v2",
        benchmark_reference="experiments/temporal_benchmark/manifests/temporal_baseline_v0_1_0.json",
    )

    report = validate_scientific_score_ml_contract(contract)

    assert report.valid is True
    assert report.errors == ()
    assert contract.enabled is True
    assert contract.walk_forward_required is True
    assert contract.anti_leakage_required is True
    assert contract.supervised_role == "auxiliary_incremental_rerank"


def test_anti_leakage_protocol_blocks_future_references() -> None:
    policy = build_anti_leakage_policy()
    report = validate_anti_leakage_payload(
        {
            "walk_forward_enabled": True,
            "feature_cutoff_contest": 10,
            "label_contest": 11,
            "source": "future_contest",
            "details": "uses past-only features",
        },
        policy,
    )

    assert report.valid is False
    assert any("forbidden source" in error for error in report.errors)


def test_anti_leakage_protocol_accepts_temporally_governed_payload() -> None:
    report = validate_anti_leakage_payload(
        {
            "walk_forward_enabled": True,
            "feature_cutoff_contest": 10,
            "label_contest": 11,
            "source": "historical_only",
            "details": "uses only past contests",
        }
    )

    assert report.valid is True
    assert report.errors == ()


def test_scientific_experiment_record_requires_temporal_validity_and_metrics() -> None:
    record = build_scientific_experiment_record(
        experiment_id="scientific-exp-v1",
        dataset_version="scientific-dataset-v1",
        temporal_split=_temporal_split(),
        seed=7,
        model_version="historical_recalibrated_v2",
        benchmark_reference="experiments/temporal_benchmark/manifests/temporal_baseline_v0_1_0.json",
        metrics={"benchmark_average_hits": 3.2, "score_ml_average_hits": 3.6, "average_hit_delta": 0.4},
        created_at="2026-05-24T00:00:00+00:00",
    )

    report = validate_scientific_experiment_record(record)

    assert report.valid is True
    assert report.errors == ()


def test_scientific_observability_and_runtime_contract_are_validated() -> None:
    observability = build_scientific_observability_snapshot(
        drift_temporal=0.05,
        score_stability=0.93,
        benchmark_evolution=0.12,
        statistical_degradation=0.08,
        notes=("scientific_observation",),
    )
    runtime = build_scientific_runtime_contract()

    observability_report = validate_scientific_observability_snapshot(observability)
    runtime_report = validate_scientific_runtime_contract(runtime)

    assert observability_report.valid is True
    assert runtime_report.valid is True
    assert observability_report.errors == ()
    assert runtime_report.errors == ()


def test_scientific_policy_15_baseline_governance_is_valid() -> None:
    governance = build_scientific_policy_15_baseline_governance(
        baseline_batch_id="calibration-20260602172948-20a682cd",
        baseline_contest_number=3697,
        baseline_total_games_checked=50,
        baseline_count_11_exact=23,
        baseline_count_12_exact=13,
        baseline_count_13_exact=3,
        baseline_count_14_exact=0,
        baseline_count_15_exact=0,
    )
    report = validate_scientific_policy_15_baseline_governance(governance)

    assert isinstance(governance, ScientificPolicy15BaselineGovernance)
    assert report.valid is True
    assert report.errors == ()
    assert governance.policy_mode == "hybrid_15_towards_12_plus"
    assert governance.policy_validation_status == "VALIDATED_15_POLICY_LEVEL_3"
    assert governance.official_15_search_standard is True
    assert governance.validated_game_size == 15
    assert governance.validated_threshold == 11
    assert governance.current_target == "12_plus"
    assert governance.secondary_target == "13_plus"
    assert governance.highest_validated_hit == 13
    assert governance.gold_target_14 is False
    assert governance.diamond_target_15 is False


def test_scientific_observability_rejects_out_of_band_metrics() -> None:
    observability = build_scientific_observability_snapshot(
        drift_temporal=1.2,
        score_stability=0.93,
        benchmark_evolution=0.12,
        statistical_degradation=0.08,
    )

    report = validate_scientific_observability_snapshot(observability)

    assert report.valid is False
    assert any("drift_temporal" in error for error in report.errors)
