from __future__ import annotations

from pathlib import Path
from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH, LotofacilOfficialHistory, get_session

# Concursos placeholder/fantasma — nunca persistir como target_contest (PR #280 / Lei 001).
PHANTOM_TARGET_CONTEST_NUMBERS: frozenset[int] = frozenset({5000})


def _max_valid_official_contest_number(db_path: Path) -> int | None:
    with get_session(db_path) as session:
        row = (
            session.query(LotofacilOfficialHistory.contest_number)
            .filter(LotofacilOfficialHistory.is_valid == 1)
            .order_by(LotofacilOfficialHistory.contest_number.desc())
            .first()
        )
        return int(row[0]) if row else None


def is_valid_generation_target_contest(
    contest: int | None,
    *,
    latest_drawn_contest: int | None = None,
) -> bool:
    """True quando o concurso alvo é prospectivo real (próximo após o último sorteado válido)."""
    if contest is None:
        return False
    value = int(contest)
    if value <= 0 or value in PHANTOM_TARGET_CONTEST_NUMBERS:
        return False
    if latest_drawn_contest is not None and int(latest_drawn_contest) > 0:
        return value == int(latest_drawn_contest) + 1
    return True


def resolve_next_target_contest(db_path: Path = DEFAULT_DATABASE_PATH) -> int | None:
    latest = _max_valid_official_contest_number(db_path)
    if latest is None:
        return None
    return int(latest) + 1


def coerce_generation_target_contest(
    candidate: int | None,
    *,
    db_path: Path = DEFAULT_DATABASE_PATH,
    latest_drawn_contest: int | None = None,
) -> int | None:
    """Normaliza target_contest para o próximo concurso real, rejeitando placeholder/fantasma."""
    latest = latest_drawn_contest
    if latest is None:
        latest = _max_valid_official_contest_number(db_path)
    if is_valid_generation_target_contest(candidate, latest_drawn_contest=latest):
        return int(candidate)
    if latest is not None and int(latest) > 0:
        return int(latest) + 1
    return resolve_next_target_contest(db_path)


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
