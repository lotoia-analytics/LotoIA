from __future__ import annotations

import logging
import os
import time
from typing import Any

import requests

from lotoia.clients.evolution_client import WHATSAPP_GAMES_FOOTER_LINES

logger = logging.getLogger(__name__)


class MessengerEvolutionService:
    """
    Canal: Messenger via Evolution API
    Endpoint base: EVOLUTION_API_URL (mesma instância)
    Instance name: EVOLUTION_MESSENGER_INSTANCE
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        instance: str | None = None,
        timeout_seconds: float = 10.0,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = str(base_url or os.getenv("EVOLUTION_API_URL", "") or "").rstrip("/")
        self.api_key = str(api_key or os.getenv("EVOLUTION_API_KEY", "") or "").strip()
        self.instance = str(
            instance or os.getenv("EVOLUTION_MESSENGER_INSTANCE", "") or ""
        ).strip()
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()
        self.last_request_url: str = ""
        self.last_http_status: int | None = None
        self.last_error_message: str = ""

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.instance)

    async def send_message(self, psid: str, text: str) -> dict[str, Any]:
        """POST /message/sendText/{instance} with PSID as number."""
        delivered = self._send_text(str(psid), str(text))
        return {
            "ok": delivered,
            "psid": str(psid),
            "status_code": self.last_http_status,
            "error": self.last_error_message,
        }

    async def send_card_image(self, psid: str, jogos: list[dict[str, Any]], plano: str) -> dict[str, Any]:
        """Messenger não suporta template WhatsApp — envia texto formatado."""
        _ = plano
        message = self.format_games_message(jogos=jogos)
        return await self.send_message(psid, message)

    def send_text_sync(self, psid: str, text: str) -> bool:
        return self._send_text(str(psid), str(text))

    @staticmethod
    def format_games_message(*, jogos: list[dict[str, Any]]) -> str:
        if not jogos:
            return ""
        formato = int(jogos[0].get("formato_cartao") or 15)
        lines = [f"🎯 Seus jogos LotoIA — {formato}D", ""]
        for index, game in enumerate(jogos, start=1):
            numbers = sorted(
                int(number)
                for number in game.get("cartao_validado_lei15a", [])
                or game.get("numbers", [])
                or game.get("final_card_numbers", [])
            )
            formatted_numbers = " ".join(f"{number:02d}" for number in numbers)
            formato_label = int(game.get("formato_cartao") or formato)
            lines.append(f"Jogo {index:02d} ({formato_label}D): {formatted_numbers}")
        lines.extend(["", *WHATSAPP_GAMES_FOOTER_LINES])
        return "\n".join(lines)

    def _send_text(self, psid: str, message: str) -> bool:
        if not self.is_configured:
            self.last_error_message = (
                "Evolution API Messenger não configurada "
                "(EVOLUTION_API_URL/API_KEY/MESSENGER_INSTANCE)."
            )
            logger.error("MESSENGER_EVOLUTION_ERROR: %s", self.last_error_message)
            return False
        normalized_psid = str(psid or "").strip()
        if not normalized_psid or not str(message or "").strip():
            self.last_error_message = "PSID ou mensagem inválidos para envio Messenger."
            logger.error("MESSENGER_EVOLUTION_ERROR: %s", self.last_error_message)
            return False
        for attempt in range(2):
            if self._send_text_once(normalized_psid, str(message)):
                return True
            if attempt == 0:
                time.sleep(0.5)
        logger.error(
            "MESSENGER_EVOLUTION_ERROR: falha ao enviar para %s (status=%s, error=%s)",
            normalized_psid,
            self.last_http_status,
            self.last_error_message,
        )
        return False

    def _send_text_once(self, psid: str, message: str) -> bool:
        url = f"{self.base_url}/message/sendText/{self.instance}"
        headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }
        body = {
            "number": psid,
            "text": message,
        }
        self.last_request_url = url
        self.last_http_status = None
        self.last_error_message = ""
        try:
            response = self.session.post(
                url,
                json=body,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            self.last_http_status = int(response.status_code)
            if 200 <= self.last_http_status < 300:
                return True
            self.last_error_message = (response.text or "")[:500]
            return False
        except Exception as exc:  # noqa: BLE001 - outbound integration boundary
            self.last_error_message = str(exc)
            return False
