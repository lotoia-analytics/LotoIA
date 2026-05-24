from __future__ import annotations

from lotoia.governance.temporal_history_registry import (
    TEMPORAL_HISTORY_BENCHMARK,
    TEMPORAL_HISTORY_CONFERENCE,
    TEMPORAL_HISTORY_ML,
    TEMPORAL_HISTORY_OPERATIONS,
    TEMPORAL_HISTORY_SNAPSHOT,
    TEMPORAL_HISTORY_VALIDATION,
    TemporalHistoryRegistry,
)


def test_canonical_temporal_history_registry_is_segregated() -> None:
    registry = TemporalHistoryRegistry()
    report = registry.validate()

    assert report.valid is True
    assert report.errors == ()
    assert registry.classify("generation_events") is not None
    assert registry.classify("benchmark_runs") is not None
    assert registry.classify("walk_forward_validation_report") is not None
    assert registry.classify("score_ml_artifacts") is not None
    assert registry.classify("reconciliation_events") is not None


def test_canonical_temporal_history_registry_maps_core_artifacts_to_expected_categories() -> None:
    registry = TemporalHistoryRegistry()

    assert registry.classify("generation_events").category == TEMPORAL_HISTORY_OPERATIONS
    assert registry.classify("generated_games").category == TEMPORAL_HISTORY_OPERATIONS
    assert registry.classify("benchmark_runs").category == TEMPORAL_HISTORY_BENCHMARK
    assert registry.classify("backtest_runs").category == TEMPORAL_HISTORY_BENCHMARK
    assert registry.classify("imported_contests").category == TEMPORAL_HISTORY_VALIDATION
    assert registry.classify("walk_forward_validation_report").category == TEMPORAL_HISTORY_VALIDATION
    assert registry.classify("score_ml_artifacts").category == TEMPORAL_HISTORY_ML
    assert registry.classify("ml_usage_events").category == TEMPORAL_HISTORY_ML
    assert registry.classify("reconciliation_events").category == TEMPORAL_HISTORY_CONFERENCE
    assert registry.classify("snapshots").category == TEMPORAL_HISTORY_SNAPSHOT


def test_canonical_temporal_history_registry_summary_exposes_by_category() -> None:
    registry = TemporalHistoryRegistry()
    summary = registry.summary()

    assert summary["artifact_count"] >= 20
    assert TEMPORAL_HISTORY_OPERATIONS in summary["categories"]
    assert TEMPORAL_HISTORY_BENCHMARK in summary["categories"]
    assert TEMPORAL_HISTORY_VALIDATION in summary["categories"]
    assert TEMPORAL_HISTORY_ML in summary["categories"]
    assert TEMPORAL_HISTORY_CONFERENCE in summary["categories"]
    assert TEMPORAL_HISTORY_SNAPSHOT in summary["categories"]
    by_category = summary["by_category"]
    assert "generation_events" in by_category[TEMPORAL_HISTORY_OPERATIONS]
    assert "benchmark_runs" in by_category[TEMPORAL_HISTORY_BENCHMARK]
