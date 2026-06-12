from __future__ import annotations

from typing import Any

from lotoia.clients.message_parser import parse_whatsapp_message


def parse_game_request(text: str, channel: str = "whatsapp") -> dict[str, Any] | None:
    """Parse game requests for WhatsApp or Messenger channels."""
    _ = channel  # parser logic is channel-agnostic today
    return parse_whatsapp_message(text)
