from __future__ import annotations

import argparse
import json
from pathlib import Path

from lotoia import cli


def test_run_institutional_analytics_cli(monkeypatch, capsys, tmp_path: Path) -> None:
    payload = {
        "executive_report": {"status": "saudavel"},
        "historical_report": {"summary": {"trend": "estavel"}},
        "snapshot": {"summary": {"status": "saudavel", "trend": "estavel"}},
    }

    def fake_publish_institutional_analytics(**kwargs):
        assert kwargs["report_dir"] == tmp_path / "analytics"
        assert kwargs["executive_report_path"] == tmp_path / "analytics" / "executive_analytical_report.json"
        assert kwargs["historical_report_path"] == tmp_path / "analytics" / "institutional_historical_intelligence.json"
        assert kwargs["snapshot_path"] == tmp_path / "analytics" / "institutional_analytics_snapshot.json"
        return {**payload, "timeline": {"schema_version": "institutional-analytics-v1.0.0", "generated_by": "build_institutional_analytical_timeline", "report": {"summary": {"trend": "estavel"}}}}

    monkeypatch.setattr(cli, "publish_institutional_analytics", fake_publish_institutional_analytics)
    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self, argv=None: argparse.Namespace(
            report_dir=tmp_path / "analytics",
            executive_report_path=tmp_path / "analytics" / "executive_analytical_report.json",
            historical_report_path=tmp_path / "analytics" / "institutional_historical_intelligence.json",
            snapshot_path=tmp_path / "analytics" / "institutional_analytics_snapshot.json",
        ),
    )

    cli.run_institutional_analytics_cli()

    captured = capsys.readouterr().out
    parsed = json.loads(captured)
    assert parsed["executive_report"] == payload["executive_report"]
    assert parsed["historical_report"] == payload["historical_report"]
    assert parsed["snapshot"] == payload["snapshot"]
    assert parsed["timeline"]["generated_by"] == "build_institutional_analytical_timeline"


def test_run_observational_stabilization_cli(monkeypatch, capsys, tmp_path: Path) -> None:
    payload = {
        "schema_version": "observational-stabilization-v1.0.0",
        "generated_by": "persist_observational_stabilization_report",
        "report": {
            "summary": {"homepage_priority": "institutional_first", "stability_note": "cockpit institucional validado"},
            "counts": {"generation_events": 1, "check_events": 1, "generated_games": 1, "imported_contests": 1},
        },
    }

    def fake_persist_observational_stabilization_report(report_path, *, db_path):
        assert report_path == tmp_path / "observability" / "observational_stabilization.json"
        assert db_path == tmp_path / "lotoia.db"
        return payload

    monkeypatch.setattr(cli, "persist_observational_stabilization_report", fake_persist_observational_stabilization_report)
    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self, argv=None: argparse.Namespace(
            report_path=tmp_path / "observability" / "observational_stabilization.json",
            db_path=tmp_path / "lotoia.db",
        ),
    )

    cli.run_observational_stabilization_cli()

    parsed = json.loads(capsys.readouterr().out)
    assert parsed == payload


def test_run_result_sync_cli(monkeypatch, capsys, tmp_path: Path) -> None:
    payload = {
        "schema_version": "operational-result-sync-v1.0.0",
        "generated_by": "ResultSyncService.sync_to_report",
        "summary": {
            "latest_contest": 3690,
            "synced_contests": [3690],
            "persisted_contests": 1,
            "source": "https://example.test/api/lotofacil",
            "fallback_used": False,
        },
    }

    class FakeRepository:
        def __init__(self, db_path: Path) -> None:
            assert db_path == tmp_path / "lotoia.db"

    class FakeService:
        def __init__(self, *, repository) -> None:  # noqa: ANN001
            self.repository = repository

        def sync_to_report(self, report_path: Path):
            assert report_path == tmp_path / "ingestion" / "result_sync.json"
            return payload

    monkeypatch.setattr(cli, "ContestRepository", FakeRepository)
    monkeypatch.setattr(cli, "ResultSyncService", FakeService)
    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self, argv=None: argparse.Namespace(
            db_path=tmp_path / "lotoia.db",
            report_path=tmp_path / "ingestion" / "result_sync.json",
        ),
    )

    cli.run_result_sync_cli()

    parsed = json.loads(capsys.readouterr().out)
    assert parsed == payload


def test_run_operational_lifecycle_cli(monkeypatch, capsys, tmp_path: Path) -> None:
    payload = {
        "created_at": "2026-05-21T19:43:00+00:00",
        "contest_id": 3690,
        "prize_count": 1,
        "retained_games": 1,
        "removed_games": 1,
        "telemetry": {"operational_status": "healthy"},
        "dashboard": {
            "total_runs": 1,
            "total_games": 2,
            "prize_count": 1,
            "best_hits": 15,
            "latest_contest": 3690,
            "status": "operational",
            "prize_tiers": {"faixa_15": 1},
            "post_draw_notes": ["há premiações registradas"],
        },
        "detections": [],
        "decisions": [],
    }

    class FakeAdapter:
        def __init__(self, db_path: Path) -> None:
            assert db_path == tmp_path / "lotoia.db"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
            return None

        def load_generated_games(self, generation_event_id: int):  # noqa: ARG002
            return [{"numbers": list(range(1, 16))}, {"numbers": [1, 2, 3]}]

        def load_lead_id(self, generation_event_id: int):  # noqa: ARG002
            return 7

    class FakeEngine:
        def __init__(self, db_path: Path) -> None:
            assert db_path == tmp_path / "lotoia.db"

        def close_day(self, **kwargs):
            assert kwargs["contest_id"] == 3690
            assert kwargs["generation_event_id"] == 88
            assert kwargs["lead_id"] == 7
            assert kwargs["cleanup"] is True
            return type("Report", (), {"to_dict": lambda self: payload})()

    monkeypatch.setattr(cli, "OperationalLifecycleEngine", FakeEngine)
    monkeypatch.setattr(cli, "ContestsRepositoryAdapter", FakeAdapter)
    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self, argv=None: argparse.Namespace(
            contest_id=3690,
            generation_event_id=88,
            official_numbers="1,2,3,4,5,6,7,8,9,10,11,12,13,14,15",
            db_path=tmp_path / "lotoia.db",
            cleanup=True,
        ),
    )

    cli.run_operational_lifecycle_cli()

    parsed = json.loads(capsys.readouterr().out)
    assert parsed == payload


def test_run_adaptive_institutional_intelligence_cli(monkeypatch, capsys, tmp_path: Path) -> None:
    payload = {
        "adaptive_memory": {"schema_version": "adaptive-institutional-v1.0.0", "operational_memory": {"summary": {"memory_depth": 2}}},
        "adaptive_timeline": {"schema_version": "adaptive-institutional-v1.0.0", "report": {"summary": {"trend": "estavel"}}},
        "adaptive_insights": {"schema_version": "adaptive-institutional-v1.0.0", "report": {"summary": {"pattern": "recorrencia institucional"}}},
    }

    def fake_publish_adaptive_institutional_intelligence(**kwargs):
        assert kwargs["report_dir"] == tmp_path / "analytics"
        assert kwargs["memory_path"] == tmp_path / "analytics" / "adaptive_institutional_memory.json"
        assert kwargs["timeline_path"] == tmp_path / "analytics" / "adaptive_institutional_timeline.json"
        assert kwargs["insights_path"] == tmp_path / "analytics" / "adaptive_institutional_insights.json"
        return payload

    monkeypatch.setattr(cli, "publish_adaptive_institutional_intelligence", fake_publish_adaptive_institutional_intelligence)
    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self, argv=None: argparse.Namespace(
            report_dir=tmp_path / "analytics",
            memory_path=tmp_path / "analytics" / "adaptive_institutional_memory.json",
            timeline_path=tmp_path / "analytics" / "adaptive_institutional_timeline.json",
            insights_path=tmp_path / "analytics" / "adaptive_institutional_insights.json",
        ),
    )

    cli.run_adaptive_institutional_intelligence_cli()

    parsed = json.loads(capsys.readouterr().out)
    assert parsed == payload
