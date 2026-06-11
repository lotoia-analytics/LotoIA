from __future__ import annotations

import logging
import os
import re
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

GENERATION_ERROR_MESSAGE = (
    "⚠️ Erro ao gerar jogos.\n"
    "Tente novamente em alguns minutos."
)


class EvolutionApiClient:
    """Evolution API client for outbound WhatsApp messages."""

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
        self.instance = str(instance or os.getenv("EVOLUTION_INSTANCE_NAME", "") or "").strip()
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()
        self.last_request_url: str = ""
        self.last_http_status: int | None = None
        self.last_error_message: str = ""

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.instance)

    def send_text(self, phone: str, message: str) -> bool:
        if not self.is_configured:
            self.last_error_message = "Evolution API não configurada (EVOLUTION_API_URL/API_KEY/INSTANCE_NAME)."
            logger.error("EVOLUTION_ERROR: %s", self.last_error_message)
            return False
        normalized_phone = re.sub(r"\D", "", str(phone or ""))
        if not normalized_phone or not str(message or "").strip():
            self.last_error_message = "Telefone ou mensagem inválidos para envio Evolution API."
            logger.error("EVOLUTION_ERROR: %s", self.last_error_message)
            return False
        for attempt in range(2):
            if self._send_text_once(normalized_phone, str(message)):
                return True
            if attempt == 0:
                time.sleep(0.5)
        logger.error(
            "EVOLUTION_ERROR: falha ao enviar mensagem para %s (status=%s, error=%s)",
            normalized_phone,
            self.last_http_status,
            self.last_error_message,
        )
        return False

    def send_games(self, phone: str, games: list[dict[str, Any]], formato: int) -> bool:
        message = self.format_games_message(games=games, formato=int(formato))
        return self.send_text(phone, message)

    @staticmethod
    def format_games_message(*, games: list[dict[str, Any]], formato: int) -> str:
        lines = [f"🎯 *Seus jogos LotoIA — {int(formato)}D*", ""]
        for index, game in enumerate(games, start=1):
            numbers = sorted(
                int(number)
                for number in game.get("numbers", []) or game.get("final_card_numbers", [])
            )
            formatted_numbers = " ".join(f"{number:02d}" for number in numbers)
            lines.append(f"Jogo {index:02d}: {formatted_numbers}")
        lines.extend(
            [
                "",
                "✅ Gerado com estatística estrutural",
                "⚠️ Jogue com responsabilidade",
            ]
        )
        return "\n".join(lines)

    def _send_text_once(self, phone: str, message: str) -> bool:
        url = f"{self.base_url}/message/sendText/{self.instance}"
        headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }
        body = {
            "number": phone,
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
