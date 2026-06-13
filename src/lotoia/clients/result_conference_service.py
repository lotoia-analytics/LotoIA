from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lotoia.clients.conference_utils import (
    calculate_hits,
    extract_game_numbers,
    parse_official_numbers,
    premio_status_from_hits,
)
from lotoia.clients.repository import ClientRepository
from lotoia.database.contest_repository import ContestRepository
from lotoia.database.database import DEFAULT_DATABASE_PATH, LotoiaClientGeneration, get_session


RESULTADO_PROMPT = (
    "📊 Conferência de resultado LotoIA!\n\n"
    "Qual o número do concurso?\n"
    "Ex: 3709"
)


@dataclass(frozen=True)
class _OfficialResult:
    contest: int
    numbers: list[int]
    date: str


@dataclass(frozen=True)
class _ClientGameResult:
    index: int
    hits: int
    premiado: bool


def parse_contest_number(text: str) -> int | None:
    normalized = str(text or "").strip()
    if not normalized:
        return None
    match = re.search(r"\b(\d{3,5})\b", normalized)
    if not match:
        return None
    value = int(match.group(1))
    return value if value > 0 else None


def _format_numbers(numbers: list[int]) -> str:
    return " ".join(f"{number:02d}" for number in sorted(numbers))


def _load_official_result(db_path: Path, contest_number: int) -> _OfficialResult | None:
    repository = ContestRepository(db_path)
    row = repository.get_official_history_contest(contest_number) or repository.get_contest(contest_number)
    if not row:
        return None
    numbers = parse_official_numbers(row)
    if len(numbers) != 15:
        return None
    return _OfficialResult(
        contest=int(row.get("concurso") or contest_number),
        numbers=numbers,
        date=str(row.get("data") or ""),
    )


def _load_client_games(
    db_path: Path,
    *,
    client_id: int,
    concurso_referencia: int,
) -> list[_ClientGameResult]:
    """Lei No 001: consulta jogos do cliente no PostgreSQL (concurso_alvo = concurso vigente)."""
    results: list[_ClientGameResult] = []
    game_index = 0
    with get_session(db_path) as session:
        generations = (
            session.query(LotoiaClientGeneration)
            .filter(
                LotoiaClientGeneration.client_id == int(client_id),
                LotoiaClientGeneration.concurso_alvo == int(concurso_referencia),
            )
            .order_by(LotoiaClientGeneration.created_at.asc(), LotoiaClientGeneration.id.asc())
            .all()
        )
        official = _load_official_result(db_path, concurso_referencia)
        if official is None:
            return []
        for generation in generations:
            for game in list(generation.jogos or []):
                game_index += 1
                numbers = extract_game_numbers(dict(game))
                hits = calculate_hits(numbers, official.numbers)
                results.append(
                    _ClientGameResult(
                        index=game_index,
                        hits=int(hits),
                        premiado=premio_status_from_hits(hits) == "premiado",
                    )
                )
    return results


def build_result_conference_message(
    *,
    contest_number: int,
    client_id: int | None,
    db_path: Path = DEFAULT_DATABASE_PATH,
) -> str:
    official = _load_official_result(db_path, contest_number)
    if official is None:
        return (
            f"⚠️ Concurso {contest_number} não encontrado.\n\n"
            "Verifique o número e tente novamente.\n"
            "Ou digite RESULTADO para consultar outro concurso."
        )

    header = f"📊 Concurso {official.contest}"
    if official.date:
        header += f" — {official.date}"
    lines = [
        header,
        "",
        "Resultado oficial:",
        _format_numbers(official.numbers),
        "",
    ]

    client_games: list[_ClientGameResult] = []
    if client_id is not None:
        client_games = _load_client_games(
            db_path,
            client_id=int(client_id),
            concurso_referencia=int(contest_number),
        )

    if client_games:
        lines.append("Seus jogos LotoIA:")
        for game in client_games:
            marker = "✅ " if game.premiado else ""
            lines.append(f"Jogo {game.index:02d} → {marker}{game.hits:02d} pontos")
        lines.append("")
        if any(game.premiado for game in client_games):
            lines.extend(
                [
                    "🏆 Parabéns! Você foi premiado!",
                    "Confira o pagamento nas lotéricas ou",
                    "pelo app Loterias Caixa.",
                ]
            )
        else:
            lines.extend(
                [
                    "Não foi dessa vez — mas continue com a LotoIA.",
                    "A estrutura estatística trabalha no longo prazo. 🎯",
                ]
            )
        return "\n".join(lines)

    lines.append("Você não gerou jogos para esse concurso.")
    lines.append("")
    lines.extend(
        [
            "Não foi dessa vez — mas continue com a LotoIA.",
            "A estrutura estatística trabalha no longo prazo. 🎯",
        ]
    )
    return "\n".join(lines)


class ResultConferenceService:
    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path
        self.repository = ClientRepository(db_path)

    def get_prompt(self) -> str:
        return RESULTADO_PROMPT

    def build_message_for_client(
        self,
        *,
        contest_number: int,
        client_id: int | None,
    ) -> str:
        return build_result_conference_message(
            contest_number=int(contest_number),
            client_id=client_id,
            db_path=self.db_path,
        )

    def build_message_for_messenger_psid(self, *, contest_number: int, psid: str) -> str:
        client = self.repository.get_by_messenger_psid(psid)
        client_id = int(client["id"]) if client else None
        return self.build_message_for_client(contest_number=contest_number, client_id=client_id)

    def build_message_for_phone(self, *, contest_number: int, phone: str) -> str:
        client = self.repository.get_by_phone(phone)
        client_id = int(client["id"]) if client else None
        return self.build_message_for_client(contest_number=contest_number, client_id=client_id)
