from __future__ import annotations

from dataclasses import replace

from lotoia.experiments.temporal_governance import TemporalSplit
from lotoia.governance.temporal_scientific_governance import (
    TEMPORAL_BENCHMARK_STRATEGIES,
    TEMPORAL_FEATURE_IDS,
    TEMPORAL_MATRIX_STRUCTURES,
    TEMPORAL_OPERATIONAL_NUCLEI,
    TemporalScientificRuntimeRegistry,
    build_temporal_benchmark_engine,
    build_temporal_feature_governance,
    build_temporal_matrix_geometry,
    build_temporal_operational_nuclei,
    build_temporal_runtime_integrity,
    build_temporal_scientific_runtime_registry,
    validate_temporal_benchmark_engine,
    validate_temporal_feature_governance,
    validate_temporal_matrix_geometry,
    validate_temporal_operational_nuclei,
    validate_temporal_runtime_integrity,
    validate_temporal_scientific_runtime_registry,
)


def _temporal_split() -> TemporalSplit:
    return TemporalSplit(
        split_id="wf_gt_11",
        train_start=1,
        train_end=120,
        test_start=121,
        test_end=140,
    )


def test_temporal_scientific_runtime_registry_is_complete_and_valid() -> None:
    registry = build_temporal_scientific_runtime_registry(
        temporal_split=_temporal_split(),
        dataset_version="scientific-temporal-dataset-v1",
        benchmark_reference="experiments/temporal_benchmark/manifests/temporal_baseline_v0_1_0.json",
        notes=("gt11_gt15",),
    )

    report = validate_temporal_scientific_runtime_registry(registry)

    assert isinstance(registry, TemporalScientificRuntimeRegistry)
    assert report.valid is True
    assert report.errors == ()
    assert {nucleus.nucleus_id for nucleus in registry.nuclei} == set(TEMPORAL_OPERATIONAL_NUCLEI)
    assert {strategy.strategy for strategy in registry.benchmark_engine.strategies} == set(TEMPORAL_BENCHMARK_STRATEGIES)
    assert {feature.feature_name for feature in registry.feature_governance.features} == set(TEMPORAL_FEATURE_IDS)
    assert set(registry.matrix_geometry.structures) == set(TEMPORAL_MATRIX_STRUCTURES)


def test_temporal_operational_nuclei_are_segregated() -> None:
    nuclei = build_temporal_operational_nuclei()
    report = validate_temporal_operational_nuclei(nuclei)

    assert report.valid is True
    assert report.errors == ()
    source_tables: list[str] = []
    for nucleus in nuclei:
        source_tables.extend(nucleus.source_tables)
    assert len(source_tables) == len(set(source_tables))


def test_temporal_benchmark_engine_requires_official_strategies_and_metrics() -> None:
    engine = build_temporal_benchmark_engine(
        temporal_split=_temporal_split(),
        dataset_version="scientific-temporal-dataset-v1",
        benchmark_reference="experiments/temporal_benchmark/manifests/temporal_baseline_v0_1_0.json",
        metrics={
            "average_hits": 0.42,
            "temporal_stability": 0.88,
            "drift_temporal": 0.05,
            "ranking_consistency": 0.91,
            "traceability_score": 1.0,
        },
    )

    report = validate_temporal_benchmark_engine(engine)

    assert report.valid is True
    assert report.errors == ()
    assert engine.temporal_policy == "future_relative_only"
    assert {strategy.strategy for strategy in engine.strategies} == set(TEMPORAL_BENCHMARK_STRATEGIES)


def test_temporal_feature_governance_blocks_future_information() -> None:
    governance = build_temporal_feature_governance()
    report = validate_temporal_feature_governance(governance)

    assert report.valid is True
    assert report.errors == ()

    leaked_feature = replace(governance.features[0], uses_future_information=True)
    leaked_governance = replace(governance, features=(leaked_feature,) + governance.features[1:])
    leaked_report = validate_temporal_feature_governance(leaked_governance)

    assert leaked_report.valid is False
    assert any("must not use future information" in error for error in leaked_report.errors)


def test_temporal_matrix_geometry_requires_official_lotofacil_grid() -> None:
    geometry = build_temporal_matrix_geometry()
    report = validate_temporal_matrix_geometry(geometry)

    assert report.valid is True
    assert report.errors == ()
    assert geometry.grid_shape == (5, 5)
    assert set(geometry.structures) == set(TEMPORAL_MATRIX_STRUCTURES)


def test_temporal_runtime_integrity_requires_everything_true() -> None:
    integrity = build_temporal_runtime_integrity(
        temporal_split=_temporal_split(),
        notes=("runtime_integrity",),
    )
    report = validate_temporal_runtime_integrity(integrity)

    assert report.valid is True
    assert report.errors == ()
    assert integrity.leakage_temporal is True
    assert integrity.datasets_correct is True
    assert integrity.benchmark_clean is True
    assert integrity.historical_segregation is True
    assert integrity.features_valid is True
    assert integrity.temporal_window_valid is True

    degraded_integrity = replace(integrity, benchmark_clean=False)
    degraded_report = validate_temporal_runtime_integrity(degraded_integrity)

    assert degraded_report.valid is False
    assert any("benchmark_clean" in error for error in degraded_report.errors)

