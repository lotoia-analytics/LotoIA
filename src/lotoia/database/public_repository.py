from __future__ import annotations

from pathlib import Path
from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.public.persistence import (
    CheckEventRepository,
    GenerationEventRepository,
    LeadRepository,
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
    db_path: Path = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    initialize_public_persistence(db_path)
    repository = GenerationEventRepository(db_path)
    return repository.insert(
        lead_id=lead_id,
        generated_games=generated_games,
        ml_enabled=ml_enabled,
        seed=seed,
        strategy=strategy,
        ranking_score=ranking_score,
        execution_time_ms=execution_time_ms,
    )


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
