from __future__ import annotations

import re
from typing import Any

from lotoia.clients.constants import VALID_QUANTITIES

HELP_MESSAGE = (
    "Olá! Toque em uma opção abaixo para escolher quantos jogos gerar."
)

_QUANTITY_FORMAT_PATTERNS = (
    re.compile(
        r"(?i)(?:quero\s+|me\s+manda\s+|manda\s+)?(\d{1,2})\s+jogos?\s+(?:de\s+)?(\d{2})d",
    ),
    re.compile(r"(?i)(\d{1,2})\s+jogos?\s+(\d{2})d"),
    re.compile(r"(?i)(\d{1,2})\s+de\s+(\d{2})d"),
    re.compile(r"(?i)(\d{1,2})\s+jogos?\s+de\s+(\d{2})"),
    re.compile(r"(?i)(?:me\s+manda\s+|manda\s+)?(\d{1,2})\s+de\s+(\d{2})\b"),
)
_QUANTITY_ONLY_PATTERN = re.compile(r"(?i)(?:quero\s+|me\s+manda\s+)?(\d{1,2})\s+jogos?\b")


def parse_whatsapp_message(text: str) -> dict[str, Any] | None:
    """Parse natural-language WhatsApp requests into quantidade/formato."""
    normalized = " ".join(str(text or "").strip().split())
    if not normalized:
        return None

    for pattern in _QUANTITY_FORMAT_PATTERNS:
        match = pattern.search(normalized)
        if match:
            quantidade = int(match.group(1))
            formato = int(match.group(2))
            if 15 <= formato <= 20:
                return {"quantidade": quantidade, "formato": formato}

    quantity_match = _QUANTITY_ONLY_PATTERN.search(normalized)
    if quantity_match:
        return {"quantidade": int(quantity_match.group(1)), "formato": None}

    if normalized.isdigit():
        quantidade = int(normalized)
        if quantidade in VALID_QUANTITIES:
            return {"quantidade": quantidade, "formato": None}

    return None
