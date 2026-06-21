"""M-MEMORY-001 — persistência de cobertura estrutural e memória evolutiva."""

from __future__ import annotations

import inspect

import pytest

from lotoia.database.database import (
    GenerationEvent,
    OperationalStructuralMemory,
    create_database,
    get_session,
)
from lotoia.generator.basic_generator import generate_best_games
from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL
from lotoia.operations.operational_structural_memory import (
    MISSION_ID,
    STATUS_CRITICAL_BIAS,
    build_bias_timeline_trend,
    compute_operational_structural_memory_snapshot,
    load_operational_structural_memory_for_event,
    load_operational_structural_memory_timeline,
    persist_operational_structural_memory,
    should_persist_structural_memory_for_batch,
)
def _sample_games(count: int = 10) -> list[dict]:
    games: list[dict] = []
    for index in range(count):
        base = index % 10
        numbers = sorted(
            {
                1 + base,
                2 + base,
                3 + base,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15 + (index % 5),
            }
        )
        while len(numbers) < 15:
            numbers.append(max(numbers) + 1)
        games.append(
            {
                "numbers": numbers[:15],
                "final_card_numbers": numbers[:15],
                "profile_type": "balanced",
            }
        )
    return games


def test_should_persist_structural_memory_for_sovereign_batch() -> None:
    assert should_persist_structural_memory_for_batch(BATCH_LABEL) is True
    assert should_persist_structural_memory_for_batch("LEGACY_BATCH") is False


def test_compute_operational_structural_memory_snapshot_fields() -> None:
    snapshot = compute_operational_structural_memory_snapshot(_sample_games(12))
    assert snapshot.get("available") is True
    assert snapshot.get("mission_id") == MISSION_ID
    assert isinstance(snapshot.get("prefix_distribution"), dict)
    assert isinstance(snapshot.get("suffix_distribution"), dict)
    assert isinstance(snapshot.get("bias_alerts"), list)
    assert float(snapshot.get("official_divergence_score", -1)) >= 0.0
    assert snapshot.get("coverage_snapshot")


def test_persist_and_load_operational_structural_memory(tmp_path) -> None:
    db_path = tmp_path / "memory.db"
    create_database(db_path)
    games = _sample_games(8)
    snapshot = compute_operational_structural_memory_snapshot(games)
    with get_session(db_path) as session:
        event = GenerationEvent(
            generated_games=games,
            context_json={"analysis_batch_label": BATCH_LABEL},
            analysis_batch_label=BATCH_LABEL,
            ml_enabled=1,
            seed=1,
            strategy="test",
            ranking_score=0.0,
            execution_time_ms=1.0,
        )
        session.add(event)
        session.commit()
        ge_id = int(event.id)

    result = persist_operational_structural_memory(
        db_path,
        generation_event_id=ge_id,
        snapshot=snapshot,
    )
    assert result.get("persisted") is True
    loaded = load_operational_structural_memory_for_event(db_path, ge_id)
    assert loaded is not None
    assert int(loaded.get("generation_event_id", 0) or 0) == ge_id
    assert loaded.get("mission_id") == MISSION_ID

    timeline = load_operational_structural_memory_timeline(db_path, limit=10)
    assert len(timeline) == 1
    trend = build_bias_timeline_trend(timeline)
    assert trend.get("available") is True
    assert trend.get("points") == 1


def test_critical_bias_status_when_divergence_high(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "lotoia.operations.operational_structural_memory.compute_official_divergence_score",
        lambda _report: 20.0,
    )
    snapshot = compute_operational_structural_memory_snapshot(_sample_games(6))
    assert snapshot.get("memory_status") == STATUS_CRITICAL_BIAS
    alerts = list(snapshot.get("bias_alerts") or [])
    assert any(alert.get("kind") == "critical_bias" for alert in alerts)


def test_basic_generator_attaches_structural_memory_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("LOTOIA_DATABASE_URL", raising=False)
    monkeypatch.setenv("LOTOIA_ML_STRUCTURAL_15D_POOL_ENABLED", "0")
    monkeypatch.setenv("LOTOIA_ML_OPERATIONAL_HIERARCHY_ENABLED", "0")
    monkeypatch.setattr(
        "lotoia.ml.structural_policy_15d.apply_structural_policy_15d_to_sovereign_batch",
        lambda selected, **kwargs: (list(selected), {"structural_policy_applied": True}),
    )
    result = generate_best_games(
        count=5,
        pool_size=40,
        batch_label=BATCH_LABEL,
        ml_enabled=False,
        seed=3,
    )
    snapshot = dict(result.get("operational_structural_memory_snapshot") or {})
    assert snapshot.get("available") is True
    assert snapshot.get("mission_id") == MISSION_ID


def test_institutional_app_wires_structural_memory(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    import dashboard.institutional_app as institutional_app

    coverage_source = inspect.getsource(institutional_app._render_cobertura_estrutural_page)
    assert "render_modern_structural_coverage_dashboard" in coverage_source
    persist_source = inspect.getsource(institutional_app._persist_generation_snapshot)
    assert "persist_operational_structural_memory" in persist_source
    assert "operational_structural_memory_snapshot" in persist_source


def test_build_marker_v93() -> None:
    from dashboard.institutional_build import BUILD_MARKER

    assert BUILD_MARKER == "institutional-adm-runtime-v97"
