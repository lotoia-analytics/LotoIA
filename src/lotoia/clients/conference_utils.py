from __future__ import annotations

from pathlib import Path
from typing import Any

from lotoia.database.contest_repository import ContestRepository
from lotoia.database.database import DEFAULT_DATABASE_PATH


def resolve_next_target_contest(db_path: Path = DEFAULT_DATABASE_PATH) -> int | None:
    repository = ContestRepository(db_path)
    latest = repository.get_official_history_max_contest()
    if latest is None:
        return None
    return int(latest) + 1


def extract_game_numbers(game: dict[str, Any]) -> list[int]:
    raw = (
        game.get("cartao_validado_lei15a")
        or game.get("numbers")
        or game.get("final_card_numbers")
        or []
    )
    return sorted({int(number) for number in raw})


def parse_official_numbers(contest: dict[str, Any]) -> list[int]:
    dezenas = contest.get("dezenas") or []
    if isinstance(dezenas, str):
        dezenas = [part.strip() for part in dezenas.split(",") if part.strip()]
    return sorted({int(str(number).strip()) for number in dezenas})


def calculate_hits(numbers: list[int], official_numbers: list[int]) -> int:
    if not numbers or not official_numbers:
        return 0
    return len(set(numbers) & set(official_numbers))


def premio_status_from_hits(hits: int) -> str:
    return "premiado" if int(hits) >= 11 else "nao_premiado"
