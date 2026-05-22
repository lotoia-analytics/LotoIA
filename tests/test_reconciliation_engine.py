from __future__ import annotations

from pathlib import Path

from lotoia.public.reconciliation import ReconciliationEngine
from lotoia.public.persistence import GenerationEventRepository, LeadRepository, initialize_public_persistence
from lotoia.public.persistence.repositories import ReconciliationEventRepository


def test_reconciliation_engine_persists_operational_closure(tmp_path: Path) -> None:
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

    engine = ReconciliationEngine(db_path)
    summary = engine.reconcile_generation(
        generation_event_id=event["id"],
        contest_id=3690,
        generated_games=[
            {"numbers": list(range(1, 16))},
            {"numbers": [1, 2, 3, 4, 5, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]},
        ],
        official_numbers=list(range(1, 16)),
        lead_id=lead["id"],
    )

    assert summary.status == "reconciliado"
    assert summary.prize_count == 1
    assert summary.best_hits == 15
    assert summary.reconciled_games[0].prize_status == "premiado"
    assert summary.reconciled_games[1].prize_status == "nao_premiado"


def test_reconciliation_engine_persists_institutional_event(tmp_path: Path) -> None:
    db_path = tmp_path / "institutional_reconciliation.db"
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

    engine = ReconciliationEngine(db_path)
    summary = engine.reconcile_generation(
        generation_event_id=event["id"],
        contest_id=3690,
        generated_games=[{"numbers": list(range(1, 16))}],
        official_numbers=list(range(1, 16)),
        lead_id=lead["id"],
    )

    repository = ReconciliationEventRepository(db_path)

    assert summary.status == "reconciliado"
    assert summary.best_hits == 15
    assert repository.count() == 1
