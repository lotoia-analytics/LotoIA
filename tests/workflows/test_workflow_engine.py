from __future__ import annotations

from pathlib import Path

from lotoia.workflows import WorkflowEngine


class _FakeSyncSummary:
    def __init__(self) -> None:
        self.synced_contests = [5000]
        self.fallback_used = False

    def to_dict(self) -> dict[str, object]:
        return {
            "latest_contest": 5000,
            "synced_contests": self.synced_contests,
            "persisted_contests": 1,
            "source": "https://example.com",
            "fallback_used": self.fallback_used,
        }


def test_workflow_engine_tracks_sync_and_generation(tmp_path: Path, monkeypatch) -> None:
    engine = WorkflowEngine(tmp_path / "lotoia.db")
    monkeypatch.setattr(engine.sync_service, "sync_latest", lambda: _FakeSyncSummary())
    sync_snapshot = engine.run_sync_workflow(trigger="test")

    assert sync_snapshot.state == "completed"
    assert sync_snapshot.summary["synced_contests"] == [5000]
    assert sync_snapshot.telemetry["synced_contests"] == 1

    def fake_generate_public_games(*args, **kwargs):
        return {
            "games": [{"numbers": [1, 2, 3]}],
            "metadata": {
                "execution_id": "exec-test",
                "seed": 42,
                "strategy": "test",
                "ranking_score": 0.91,
                "execution_time_ms": 1.0,
                "ml_enabled": False,
                "source": "workflow",
                "user_agent": "pytest",
                "max_games": 2,
                "engine_version": "historical_recalibrated_v2",
                "fallback_used": False,
                "profile_distribution": {"recorrente": 1, "hibrido": 0, "caotico": 0},
                "target_contest": 5000,
                "score_ml_runtime": {"enabled": False},
            },
        }

    monkeypatch.setattr("lotoia.workflows.workflow_engine.generate_public_games", fake_generate_public_games)
    generation_snapshot = engine.run_generation_workflow(
        type("Request", (), {"ml_enabled": False})(),
        source="workflow",
        user_agent="pytest",
        ip_address="127.0.0.1",
    )

    assert generation_snapshot.state == "completed"
    assert generation_snapshot.summary["seed"] == 42
    assert generation_snapshot.summary["source"] == "workflow"
    assert generation_snapshot.telemetry["workflow_count"] >= 2


def test_workflow_engine_runs_full_cycle_in_partial_mode(tmp_path: Path, monkeypatch) -> None:
    engine = WorkflowEngine(tmp_path / "lotoia.db")
    monkeypatch.setattr(engine, "run_sync_workflow", lambda **kwargs: type("Sync", (), {"to_dict": lambda self: {"status": "completed", "step": "sync"}})())
    monkeypatch.setattr(engine, "run_reconciliation_workflow", lambda **kwargs: type("Reconcile", (), {"to_dict": lambda self: {"status": "completed", "step": "reconciliation"}})())
    monkeypatch.setattr(engine, "run_closure_workflow", lambda **kwargs: type("Closure", (), {"to_dict": lambda self: {"status": "completed", "step": "closure"}})())
    monkeypatch.setattr(engine, "build_telemetry", lambda: {"workflow_count": 1, "step_count": 1, "failure_count": 0, "retry_count": 0, "average_duration_ms": 0.0, "latest_status": "ok", "workflow_status": "healthy", "runtime_stability": 0.9, "scheduler_active": True, "active_signals": 1})

    payload = engine.run_full_cycle(generation_event_id=123, contest_id=3690, official_numbers=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])

    assert payload["status"] == "completed"
    assert [step["name"] for step in payload["steps"]] == ["sync", "reconciliation", "closure"]
    assert payload["telemetry"]["workflow_status"] == "healthy"
