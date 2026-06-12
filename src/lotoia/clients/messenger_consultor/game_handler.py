from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import func

from lotoia.clients.client_guard import ValidationResult, validate_messenger_request
from lotoia.clients.constants import DAILY_LIMIT, OFFICIAL_LANDING_URL
from lotoia.clients.game_request_parser import parse_game_request
from lotoia.clients.interactive_menu import plan_generation_targets
from lotoia.clients.messenger_consultor.menus import GERAR_CURIOSO_MESSAGE
from lotoia.clients.repository import ClientRepository
from lotoia.clients.whatsapp_service import GENERATION_ERROR_MESSAGE, format_games_whatsapp_message
from lotoia.clients.conference_utils import resolve_next_target_contest
from lotoia.clients.messenger_consultor.generation import generate_messenger_games
from lotoia.database.database import DEFAULT_DATABASE_PATH, LotoiaClientGeneration, get_session


class MessengerGameHandler:
    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path
        self.repository = ClientRepository(db_path)

    def get_global_daily_usage(self, client_id: int) -> int:
        """Limite diário GLOBAL — soma WhatsApp + Messenger."""
        target_date = datetime.now(UTC).date()
        with get_session(self.db_path) as session:
            total = (
                session.query(func.coalesce(func.sum(LotoiaClientGeneration.quantidade), 0))
                .filter(
                    LotoiaClientGeneration.client_id == int(client_id),
                    func.date(LotoiaClientGeneration.created_at) == target_date,
                )
                .scalar()
            )
            return int(total or 0)

    def curioso_generate_message(self) -> str:
        return GERAR_CURIOSO_MESSAGE.replace("www.lotoia.chat", OFFICIAL_LANDING_URL.replace("https://", ""))

    def handle_generation(
        self,
        *,
        psid: str,
        text: str,
        client: dict[str, Any],
        client_status: dict[str, Any] | None,
    ) -> dict[str, Any]:
        parsed = parse_game_request(text, channel="messenger")
        if not parsed:
            return {
                "status": "prompt",
                "psid": psid,
                "message": "🎯 Informe quantos jogos gerar. Ex.: 3 | 5x15D | 2x18D",
            }

        quantidade = int(parsed["quantidade"])
        targets = plan_generation_targets(parsed, client_status=client_status)
        validation_formato = int(targets[0][0]) if len(targets) == 1 else int(parsed.get("formato") or 15)
        validation = validate_messenger_request(psid, validation_formato, quantidade, db_path=self.db_path)
        if not validation.ok:
            return {
                "status": "error",
                "error_code": validation.error_code,
                "psid": psid,
                "message": validation.message,
            }

        global_usage = self.get_global_daily_usage(int(client["id"]))
        restante = max(DAILY_LIMIT - global_usage, 0)
        if quantidade > restante:
            return {
                "status": "error",
                "error_code": "DAILY_LIMIT_PARTIAL",
                "psid": psid,
                "message": (
                    f"Você tem {restante} jogos disponíveis hoje (limite global 30).\n"
                    f"Peça até {restante} jogos."
                ),
            }

        try:
            return self._execute_generation(
                psid=psid,
                validation=validation,
                targets=targets,
            )
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "error",
                "error_code": "GENERATION_ERROR",
                "psid": psid,
                "message": GENERATION_ERROR_MESSAGE,
                "detail": str(exc),
            }

    def _execute_generation(
        self,
        *,
        psid: str,
        validation: ValidationResult,
        targets: list[tuple[int, int]],
    ) -> dict[str, Any]:
        client = dict(validation.client or {})
        quantidade = int(validation.quantidade or 0)
        games, generation_event = generate_messenger_games(
            targets=targets,
            psid=psid,
            client_name=str(client.get("name") or "Cliente"),
            db_path=self.db_path,
        )
        log_formato = max(formato for formato, _ in targets)
        concurso_alvo = resolve_next_target_contest(self.db_path)
        client_generation = self.repository.log_client_generation(
            client_id=int(client["id"]),
            phone=str(client.get("phone") or self.repository.messenger_phone(psid)),
            formato=log_formato,
            quantidade=quantidade,
            jogos=games,
            generation_event_id=int(generation_event.get("id") or 0) or None,
            concurso_alvo=concurso_alvo,
            channel="messenger",
        )
        self.repository.increment_daily_usage(int(client["id"]), quantidade=quantidade)
        response_message = format_games_whatsapp_message(
            quantidade=quantidade,
            games=games,
            targets=targets,
        )
        return {
            "status": "ok",
            "psid": psid,
            "channel": "messenger",
            "message": response_message,
            "games": games,
            "quantidade": quantidade,
            "generation_event_id": generation_event.get("id"),
            "client_generation_id": client_generation.get("id"),
            "trace_id": f"ms-{uuid4().hex[:12]}",
            "global_daily_usage": self.get_global_daily_usage(int(client["id"])),
        }
