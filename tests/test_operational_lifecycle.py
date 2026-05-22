from __future__ import annotations

from pathlib import Path

from lotoia.public.operational_lifecycle import OperationalLifecycleEngine, build_retention_policy_preview
from lotoia.public.persistence import GenerationEventRepository, LeadRepository, initialize_public_persistence


def test_operational_lifecycle_builds_dashboard_and_telemetry(tmp_path: Path) -> None:
    db_path = tmp_path / "lotoia.db"
    initialize_public_persistence(db_path)
    leads = LeadRepository(db_path)
    generations = GenerationEventRepository(db_path)

    lead = leads.insert(first_name="Ana", whatsapp="11999999999", source="test", ip_hash="", user_agent="pytest")
    event = generations.insert(
        lead_id=lead["id"],
        generated_games=[
            {"numbers": list(range(1, 16)), "profile_type": "recorrente"},
            {"numbers": [1, 2, 3, 4, 5, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25], "profile_type": "hibrido"},
        ],
        ml_enabled=False,
        seed=42,
        strategy="test",
        ranking_score=0.91,
        execution_time_ms=1.2,
        target_contest=3690,
        origin="public_api",
        generation_mode="public_hybrid_statistical_v1",
        context={"target_contest": 3690},
    )

    engine = OperationalLifecycleEngine(db_path)
    report = engine.close_day(
        contest_id=3690,
        generated_games=[
            {"numbers": list(range(1, 16))},
            {"numbers": [1, 2, 3, 4, 5, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]},
        ],
        official_numbers=list(range(1, 16)),
        generation_event_id=event["id"],
        lead_id=lead["id"],
        cleanup=False,
    )

    dashboard = engine.build_dashboard()
    telemetry = engine.build_telemetry()
    analytics = engine.build_post_draw_analytics(contest_id=3690)

    assert report.prize_count == 1
    assert report.retained_games == 1
    assert report.removed_games == 1
    assert dashboard.status == "operational"
    assert dashboard.prize_count >= 1
    assert telemetry["reconciliation_runs"] >= 1
    assert telemetry["reconciliation_games"] >= 1
    assert analytics is not None
    assert analytics.prize_count == 1
    assert analytics.total_games == 2
    assert analytics.retention_rate == 0.5
    assert analytics.average_hits >= 7.0


def test_operational_lifecycle_persists_reports(tmp_path: Path) -> None:
    db_path = tmp_path / "lotoia.db"
    initialize_public_persistence(db_path)
    leads = LeadRepository(db_path)
    generations = GenerationEventRepository(db_path)

    lead = leads.insert(first_name="Ana", whatsapp="11999999999", source="test", ip_hash="", user_agent="pytest")
    event = generations.insert(
        lead_id=lead["id"],
        generated_games=[{"numbers": list(range(1, 16)), "profile_type": "recorrente"}],
        ml_enabled=False,
        seed=42,
        strategy="test",
        ranking_score=0.91,
        execution_time_ms=1.2,
        target_contest=3690,
        origin="public_api",
        generation_mode="public_hybrid_statistical_v1",
        context={"target_contest": 3690},
    )

    engine = OperationalLifecycleEngine(db_path)
    report = engine.close_day(
        contest_id=3690,
        generated_games=[{"numbers": list(range(1, 16))}],
        official_numbers=list(range(1, 16)),
        generation_event_id=event["id"],
        lead_id=lead["id"],
        cleanup=False,
        report_dir=tmp_path / "reports" / "operational",
    )

    closure_path = tmp_path / "reports" / "operational" / "operational_closure.json"
    telemetry_path = tmp_path / "reports" / "operational" / "operational_telemetry.json"
    analytics_path = tmp_path / "reports" / "operational" / "post_draw_analytics.json"

    assert closure_path.exists()
    assert telemetry_path.exists()
    assert analytics_path.exists()
    assert report.analytics is not None


def test_retention_policy_keeps_prize_and_strategic_games() -> None:
    engine = OperationalLifecycleEngine()
    detections = engine.prize_detection.detect(
        [
            {"hits": 15, "matched_numbers": list(range(1, 16))},
            {"hits": 9, "matched_numbers": [1, 2, 3]},
        ]
    )
    decisions = engine.retention_policy.decide(detections, strategic_games={2})

    assert decisions[0].keep is True
    assert decisions[1].keep is True
    assert decisions[0].reason == "premiado"
    assert decisions[1].reason == "estrategico"


def test_operational_lifecycle_default_cleanup_keeps_only_prizes() -> None:
    engine = OperationalLifecycleEngine()
    detections = engine.prize_detection.detect(
        [
            {"hits": 15, "matched_numbers": list(range(1, 16))},
            {"hits": 10, "matched_numbers": [1, 2, 3, 4, 5]},
            {"hits": 11, "matched_numbers": [1, 2, 3, 4, 5, 6]},
        ]
    )

    decisions = engine.retention_policy.decide(detections)

    assert decisions[0].keep is True
    assert decisions[1].keep is False
    assert decisions[2].keep is True
    assert decisions[1].reason == "abaixo_da_premiacao_minima"


def test_retention_policy_preview_reports_persisted_and_removed_rows() -> None:
    preview = build_retention_policy_preview(
        [
            {"numbers": list(range(1, 16))},
            {"numbers": [1, 2, 3, 4, 5, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]},
        ],
        list(range(1, 16)),
    )

    assert preview["summary"]["total"] == 2
    assert preview["summary"]["persistidos"] == 1
    assert preview["summary"]["removidos"] == 1
    assert preview["rows"][0]["decisao"] == "persistido"
    assert preview["rows"][1]["decisao"] == "removido"
