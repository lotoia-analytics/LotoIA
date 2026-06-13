from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lotoia.clients.official_result_sync import (
    ensure_official_contest_available,
    get_latest_official_contest,
    sync_latest_official_results,
)
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


def build_resultado_prompt(
    last_contest: int | None = None,
    *,
    latest_official_contest: int | None = None,
) -> str:
    lines = [
        "📊 Conferência de resultado LotoIA!",
        "",
    ]
    if latest_official_contest is not None:
        lines.extend(
            [
                f"📡 Último resultado oficial disponível: {int(latest_official_contest)}",
                "",
            ]
        )
    if last_contest is not None:
        lines.extend(
            [
                f"🎯 Seu último concurso com jogos gerados: {int(last_contest)}",
                "",
            ]
        )
    lines.extend(
        [
            "Qual o número do concurso?",
            "Ex: 3709",
        ]
    )
    return "\n".join(lines)


def _last_contest_hint(last_contest: int | None, *, requested_contest: int) -> list[str]:
    if last_contest is None:
        return []
    last = int(last_contest)
    if last == int(requested_contest):
        return []
    return [
        "",
        f"🎯 Seu último concurso com jogos gerados: {last}",
        f"Digite {last} para conferir seus jogos.",
    ]


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
    normalized = re.sub(r"[*_~`]", "", normalized)
    normalized = normalized.replace("\u200b", "").replace("\ufeff", "")
    normalized = " ".join(normalized.split())
    if re.fullmatch(r"\d{3,5}", normalized):
        return int(normalized)
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
        ensure_official_contest_available(db_path, int(contest_number))
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
    official_numbers: list[int],
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
        for generation in generations:
            for game in list(generation.jogos or []):
                game_index += 1
                numbers = extract_game_numbers(dict(game))
                hits = calculate_hits(numbers, official_numbers)
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
    last_generation_contest: int | None = None,
) -> str:
    official = _load_official_result(db_path, contest_number)
    if official is None:
        lines = [
            f"⚠️ Concurso {contest_number} não encontrado.",
            "",
            "Sincronizamos com a Caixa, mas esse resultado ainda não está disponível.",
            "Tente novamente em alguns minutos ou digite RESULTADO.",
        ]
        lines.extend(_last_contest_hint(last_generation_contest, requested_contest=contest_number))
        return "\n".join(lines)

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
            official_numbers=official.numbers,
        )

    if client_games:
        premiados = [game for game in client_games if game.premiado]
        if premiados:
            total = len(client_games)
            premiados_count = len(premiados)
            if premiados_count < total:
                lines.append(f"🏆 Jogos premiados LotoIA ({premiados_count} de {total}):")
            else:
                lines.append("🏆 Jogos premiados LotoIA:")
            for game in premiados:
                lines.append(f"Jogo {game.index:02d} → ✅ {game.hits:02d} pontos")
            lines.append("")
            lines.extend(
                [
                    "🏆 Parabéns! Você foi premiado!",
                    "Confira o pagamento nas lotéricas ou",
                    "pelo app Loterias Caixa.",
                ]
            )
            return "\n".join(lines)

        lines.extend(
            [
                f"Você gerou {len(client_games)} jogos, mas nenhum atingiu 11 pontos.",
                "",
                "Não foi dessa vez — mas continue com a LotoIA.",
                "A estrutura estatística trabalha no longo prazo. 🎯",
            ]
        )
        return "\n".join(lines)

    lines.append("Você não gerou jogos para esse concurso.")
    lines.extend(_last_contest_hint(last_generation_contest, requested_contest=contest_number))
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
        return build_resultado_prompt()

    def get_prompt_for_client_id(self, client_id: int | None) -> str:
        sync_latest_official_results(self.db_path)
        last_contest = None
        if client_id is not None:
            last_contest = self.repository.get_last_generation_contest(int(client_id))
        latest_official = get_latest_official_contest(self.db_path)
        return build_resultado_prompt(last_contest, latest_official_contest=latest_official)

    def get_prompt_for_phone(self, phone: str) -> str:
        client = self.repository.get_by_phone(phone)
        client_id = int(client["id"]) if client else None
        return self.get_prompt_for_client_id(client_id)

    def get_prompt_for_messenger_psid(self, psid: str) -> str:
        client = self.repository.get_by_messenger_psid(psid)
        client_id = int(client["id"]) if client else None
        return self.get_prompt_for_client_id(client_id)

    def build_message_for_client(
        self,
        *,
        contest_number: int,
        client_id: int | None,
    ) -> str:
        last_generation_contest = None
        if client_id is not None:
            last_generation_contest = self.repository.get_last_generation_contest(int(client_id))
        return build_result_conference_message(
            contest_number=int(contest_number),
            client_id=client_id,
            db_path=self.db_path,
            last_generation_contest=last_generation_contest,
        )

    def build_message_for_messenger_psid(self, *, contest_number: int, psid: str) -> str:
        client = self.repository.get_by_messenger_psid(psid)
        client_id = int(client["id"]) if client else None
        return self.build_message_for_client(contest_number=contest_number, client_id=client_id)

    def build_message_for_phone(self, *, contest_number: int, phone: str) -> str:
        client = self.repository.get_by_phone(phone)
        client_id = int(client["id"]) if client else None
        return self.build_message_for_client(contest_number=contest_number, client_id=client_id)
