from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from lotoia.clients.messenger_consultor.freemium_guard import FreemiumGuard
from lotoia.clients.messenger_consultor.game_handler import MessengerGameHandler
from lotoia.clients.messenger_consultor.intent_parser import MessengerIntentParser
from lotoia.clients.messenger_consultor.menus import (
    CONFERIR_PROMPT,
    MENU_CURIOSO,
    PLANOS_MESSAGE,
    menu_cliente_ativo,
)
from lotoia.clients.messenger_consultor.state_repository import MessengerStateRepository
from lotoia.clients.messenger_consultor.stats_service import MessengerStatsService
from lotoia.clients.result_conference_service import ResultConferenceService, parse_contest_number
from lotoia.clients.messenger_onboarding import handle_new_messenger_lead
from lotoia.clients.repository import ClientRepository
from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.public.persistence import LeadRepository

logger = logging.getLogger(__name__)

_PROCESSED_MESSAGE_IDS: dict[str, datetime] = {}
_IDEMPOTENCY_TTL = timedelta(hours=6)


def _cleanup_processed_message_ids() -> None:
    cutoff = datetime.now(UTC) - _IDEMPOTENCY_TTL
    expired = [message_id for message_id, seen_at in _PROCESSED_MESSAGE_IDS.items() if seen_at < cutoff]
    for message_id in expired:
        _PROCESSED_MESSAGE_IDS.pop(message_id, None)


def _remember_message_id(message_id: str) -> bool:
    if not message_id:
        return False
    _cleanup_processed_message_ids()
    if message_id in _PROCESSED_MESSAGE_IDS:
        return True
    _PROCESSED_MESSAGE_IDS[message_id] = datetime.now(UTC)
    return False


def extract_messenger_payload(payload: dict[str, Any]) -> dict[str, Any]:
    for entry in payload.get("entry", []) or []:
        if not isinstance(entry, dict):
            continue
        for messaging in entry.get("messaging", []) or []:
            if not isinstance(messaging, dict):
                continue
            sender = dict(messaging.get("sender") or {})
            message = dict(messaging.get("message") or {})
            psid = str(sender.get("id") or "").strip()
            text = str(message.get("text") or "").strip()
            message_id = str(message.get("mid") or messaging.get("timestamp") or "")
            if psid:
                return {"psid": psid, "text": text, "message_id": message_id, "from_me": False}

    data = dict(payload.get("data") or payload)
    psid = str(data.get("sender") or payload.get("sender") or data.get("number") or payload.get("number") or "").strip()
    text = str(data.get("text") or payload.get("text") or "").strip()
    message_id = str(data.get("id") or payload.get("message_id") or "")
    return {
        "psid": psid,
        "text": text,
        "message_id": message_id,
        "from_me": bool(data.get("fromMe") or payload.get("fromMe")),
    }


class MessengerConsultorService:
    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path
        self.repository = ClientRepository(db_path)
        self.stats = MessengerStatsService(db_path)
        self.freemium = FreemiumGuard(db_path)
        self.intent_parser = MessengerIntentParser()
        self.state_repo = MessengerStateRepository(db_path)
        self.game_handler = MessengerGameHandler(db_path)
        self.result_conference = ResultConferenceService(db_path)

    def _is_active_client(self, client: dict[str, Any] | None) -> bool:
        return self.freemium.is_active_client("", client)

    def _ensure_curioso(self, psid: str) -> None:
        self.state_repo.ensure_lead_state(psid)
        lead_repo = LeadRepository(self.db_path)
        existing = lead_repo.find_by_first_name_and_whatsapp("Messenger", psid)
        if existing is None:
            handle_new_messenger_lead(psid, db_path=self.db_path)

    def process_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        extracted = extract_messenger_payload(payload)
        psid = str(extracted.get("psid") or "")
        text = str(extracted.get("text") or "")
        message_id = str(extracted.get("message_id") or "")

        if extracted.get("from_me"):
            return {"status": "ignored", "reason": "from_me", "psid": psid}
        if message_id and _remember_message_id(message_id):
            return {"status": "ignored", "reason": "duplicate_message", "psid": psid, "message_id": message_id}
        if not psid:
            return {"status": "error", "error_code": "INVALID_PAYLOAD", "message": "PSID não identificado."}

        client = self.repository.get_by_messenger_psid(psid)
        active = self._is_active_client(client)
        state = self.state_repo.get_state(psid)

        if state.get("state") == "awaiting_check_input":
            return self._handle_check_input(psid=psid, text=text, client=client, active=active)
        if state.get("state") == "awaiting_concurso":
            return self._handle_resultado_concurso(psid=psid, text=text)

        if not client:
            self._ensure_curioso(psid)

        intent = self.intent_parser.parse(text)
        if intent == "unknown" and not text.strip():
            intent = "menu"

        if intent == "menu" or (not client and intent == "unknown"):
            return self._menu_response(psid=psid, client=client, active=active)

        if intent == "resultado":
            return self._start_resultado_conference(psid=psid)
        if intent == "atrasadas":
            return {"status": "ok", "psid": psid, "message": self.stats.get_atrasadas()}
        if intent == "frequentes":
            return {"status": "ok", "psid": psid, "message": self.stats.get_frequentes()}
        if intent == "score":
            return {"status": "ok", "psid": psid, "message": self.stats.get_score()}
        if intent == "planos":
            return {"status": "ok", "psid": psid, "message": PLANOS_MESSAGE}
        if intent == "conferir":
            return self._start_conference(psid=psid, active=active)
        if intent == "gerar":
            if not active or client is None:
                return {"status": "prompt", "psid": psid, "message": self.game_handler.curioso_generate_message()}
            client_status = self.repository.get_client_status_by_psid(psid)
            return self.game_handler.handle_generation(
                psid=psid,
                text=text,
                client=client,
                client_status=client_status,
            )

        return self._menu_response(psid=psid, client=client, active=active)

    def _menu_response(self, *, psid: str, client: dict[str, Any] | None, active: bool) -> dict[str, Any]:
        if active and client is not None:
            status = self.repository.get_client_status_by_psid(psid) or {}
            message = menu_cliente_ativo(
                nome=str(client.get("name") or "Cliente"),
                plano=str(client.get("plan") or "basico"),
                jogos_hoje=int(status.get("jogos_hoje") or 0),
                saldo_hoje=int(status.get("saldo_hoje") or 0),
            )
        else:
            message = MENU_CURIOSO
        return {"status": "menu", "psid": psid, "message": message}

    def _start_resultado_conference(self, *, psid: str) -> dict[str, Any]:
        self.state_repo.set_state(psid, "awaiting_concurso")
        return {"status": "prompt", "psid": psid, "message": self.result_conference.get_prompt()}

    def _handle_resultado_concurso(self, *, psid: str, text: str) -> dict[str, Any]:
        contest_number = parse_contest_number(text)
        if contest_number is None:
            return {
                "status": "prompt",
                "psid": psid,
                "message": (
                    "Não entendi o número do concurso.\n\n"
                    + self.result_conference.get_prompt()
                ),
            }
        message = self.result_conference.build_message_for_messenger_psid(
            contest_number=contest_number,
            psid=psid,
        )
        self.state_repo.reset_state(psid)
        return {"status": "ok", "psid": psid, "message": message}

    def _start_conference(self, *, psid: str, active: bool) -> dict[str, Any]:
        if not active:
            can_check, restantes = self.freemium.can_check(psid)
            if not can_check:
                return {"status": "error", "psid": psid, "message": self.freemium.get_limit_message(0)}
            prefix = self.freemium.get_limit_message(restantes) + "\n\n"
        else:
            prefix = ""
        self.state_repo.set_state(psid, "awaiting_check_input")
        return {"status": "prompt", "psid": psid, "message": prefix + CONFERIR_PROMPT}

    def _handle_check_input(
        self,
        *,
        psid: str,
        text: str,
        client: dict[str, Any] | None,
        active: bool,
    ) -> dict[str, Any]:
        dezenas = self.intent_parser.parse_dezenas(text)
        if not dezenas:
            return {
                "status": "prompt",
                "psid": psid,
                "message": "Não entendi as dezenas. Envie 15 números entre 01 e 25.\n\n" + CONFERIR_PROMPT,
            }

        if not active:
            can_check, _ = self.freemium.can_check(psid)
            if not can_check:
                self.state_repo.reset_state(psid)
                return {"status": "error", "psid": psid, "message": self.freemium.get_limit_message(0)}
            restantes_after = self.freemium.consume_check(psid)
        else:
            restantes_after = 999

        message = self.stats.conferir_jogo(dezenas)
        if not active:
            message += "\n\n" + self.freemium.get_limit_message(restantes_after)
        self.state_repo.reset_state(psid)
        return {"status": "ok", "psid": psid, "message": message}


def process_messenger_consultor_webhook(
    payload: dict[str, Any],
    *,
    db_path: Path = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    service = MessengerConsultorService(db_path)
    return service.process_message(payload)
