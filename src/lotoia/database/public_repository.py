from __future__ import annotations

from pathlib import Path
from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.public.persistence import (
    CheckEventRepository,
    GenerationEventRepository,
    LeadRepository,
    ReportEventRepository,
    ReconciliationRepository,
    initialize_public_persistence,
)


def save_lead(
    *,
    first_name: str,
    whatsapp: str,
    source: str,
    ip_hash: str,
    user_agent: str,
    db_path: Path = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    initialize_public_persistence(db_path)
    repository = LeadRepository(db_path)
    return repository.insert(
        first_name=first_name,
        whatsapp=whatsapp,
        source=source,
        ip_hash=ip_hash,
        user_agent=user_agent,
    )


def save_generation_event(
    *,
    lead_id: int,
    generated_games: list[dict[str, Any]],
    ml_enabled: bool,
    seed: int,
    strategy: str,
    ranking_score: float,
    execution_time_ms: float,
    target_contest: int | None = None,
    origin: str = "public_api",
    generation_mode: str = "public_hybrid_statistical_v1",
    context: dict[str, Any] | None = None,
    first_name: str = "",
    whatsapp: str = "",
    db_path: Path = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    initialize_public_persistence(db_path)
    repository = GenerationEventRepository(db_path)
    event = repository.insert(
        lead_id=lead_id,
        generated_games=generated_games,
        ml_enabled=ml_enabled,
        seed=seed,
        strategy=strategy,
        ranking_score=ranking_score,
        execution_time_ms=execution_time_ms,
        target_contest=target_contest,
        origin=origin,
        generation_mode=generation_mode,
        context=context,
        first_name=first_name,
        whatsapp=whatsapp,
    )
    return event


def save_check_event(
    *,
    lead_id: int,
    contest_id: int,
    selected_numbers: list[int],
    hits: int,
    result_payload: dict[str, Any],
    db_path: Path = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    initialize_public_persistence(db_path)
    repository = CheckEventRepository(db_path)
    return repository.insert(
        lead_id=lead_id,
        contest_id=contest_id,
        selected_numbers=selected_numbers,
        hits=hits,
        result_payload=result_payload,
    )


def save_reconciliation_run(
    *,
    generation_event_id: int,
    lead_id: int | None,
    contest_id: int,
    source: str,
    status: str,
    prize_count: int,
    total_hits: int,
    best_hits: int,
    payload: dict[str, Any],
    games: list[dict[str, Any]],
    db_path: Path = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    initialize_public_persistence(db_path)
    repository = ReconciliationRepository(db_path)
    return repository.insert(
        generation_event_id=generation_event_id,
        lead_id=lead_id,
        contest_id=contest_id,
        source=source,
        status=status,
        prize_count=prize_count,
        total_hits=total_hits,
        best_hits=best_hits,
        payload=payload,
        games=games,
    )


def save_report_event(
    *,
    lead_id: int | None,
    generation_event_id: int | None,
    report_type: str,
    generation_origin: str,
    runtime_origin: str,
    strategy_profile: str,
    payload: dict[str, Any] | None = None,
    db_path: Path = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    initialize_public_persistence(db_path)
    repository = ReportEventRepository(db_path)
    return repository.insert(
        lead_id=lead_id,
        generation_event_id=generation_event_id,
        report_type=report_type,
        generation_origin=generation_origin,
        runtime_origin=runtime_origin,
        strategy_profile=strategy_profile,
        payload=payload,
    )
