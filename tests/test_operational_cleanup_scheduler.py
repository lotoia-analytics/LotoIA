from __future__ import annotations

from datetime import datetime
from pathlib import Path

from lotoia.database.database import get_session
from lotoia.database.database import GeneratedGame, ReconciliationGame, ReconciliationRun, Lead, create_database
from lotoia.scheduling.daily_cleanup_scheduler import DailyOperationalCleanupScheduler


def test_daily_cleanup_scheduler_keeps_only_prized_games(tmp_path: Path) -> None:
    db_path = tmp_path / "lotoia.db"
    create_database(db_path)

    with get_session(db_path) as session:
        lead = Lead(first_name="Ana", whatsapp="11999999999", source="test", ip_hash="", user_agent="pytest")
        session.add(lead)
        session.commit()
        run = ReconciliationRun(
            generation_event_id=1,
            lead_id=lead.id,
            contest_id=3690,
            source="official_result",
            status="reconciled",
            prize_count=1,
            total_hits=15,
            best_hits=15,
            payload={"contest_id": 3690},
        )
        session.add(run)
        session.commit()
        session.add_all(
            [
                GeneratedGame(
                    generation_event_id=1,
                    lead_id=lead.id,
                    target_contest=3690,
                    origin="public_api",
                    generation_mode="public_hybrid_statistical_v1",
                    game_index=1,
                    numbers=list(range(1, 16)),
                    profile_type="recorrente",
                    final_score={},
                    quadra_score={},
                    context_json={},
                ),
                GeneratedGame(
                    generation_event_id=1,
                    lead_id=lead.id,
                    target_contest=3690,
                    origin="public_api",
                    generation_mode="public_hybrid_statistical_v1",
                    game_index=2,
                    numbers=[1, 2, 3, 4, 5, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25],
                    profile_type="hibrido",
                    final_score={},
                    quadra_score={},
                    context_json={},
                ),
                ReconciliationGame(
                    reconciliation_run_id=run.id,
                    generation_event_id=1,
                    lead_id=lead.id,
                    contest_id=3690,
                    game_index=1,
                    numbers=list(range(1, 16)),
                    hits=15,
                    matched_numbers=list(range(1, 16)),
                    prize_status="premiado",
                    prize_tier="faixa_15",
                    context_json={},
                ),
                ReconciliationGame(
                    reconciliation_run_id=run.id,
                    generation_event_id=1,
                    lead_id=lead.id,
                    contest_id=3690,
                    game_index=2,
                    numbers=[1, 2, 3, 4, 5, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25],
                    hits=5,
                    matched_numbers=[1, 2, 3, 4, 5],
                    prize_status="nao_premiado",
                    prize_tier="",
                    context_json={},
                ),
            ]
        )
        session.commit()

    scheduler = DailyOperationalCleanupScheduler(db_path=db_path, now_provider=lambda: datetime(2026, 5, 22, 0, 5))
    payload = scheduler.run_due_cleanup()

    with get_session(db_path) as session:
        generated_remaining = session.query(GeneratedGame).count()
        reconciliation_remaining = session.query(ReconciliationGame).count()

    assert payload["status"] == "completed"
    assert payload["cleanup"][0]["retained_indexes"] == [1]
    assert generated_remaining == 1
    assert reconciliation_remaining == 1
