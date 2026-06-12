from __future__ import annotations

import re
from typing import Any

from lotoia.clients.constants import VALID_QUANTITIES

HELP_MESSAGE = (
    "Olá! Toque em uma opção abaixo para escolher quantos jogos gerar."
)

_VALID_FORMATS = frozenset(range(15, 21))

_QUANTITY_FORMAT_PATTERNS = (
    re.compile(r"(?i)(\d{1,2})\s*[x×]\s*(\d{2})\s*d"),
    re.compile(r"(?i)(\d{1,2})\s+(\d{2})\s*d"),
    re.compile(
        r"(?i)(?:quero\s+|me\s+manda\s+|manda\s+)?(\d{1,2})\s+jogos?\s+(?:de\s+)?(\d{2})\s*d",
    ),
    re.compile(r"(?i)(\d{1,2})\s+jogos?\s+(\d{2})\s*d"),
    re.compile(r"(?i)(\d{1,2})\s+jogos?\s+de\s+(\d{2})\b"),
    re.compile(r"(?i)(\d{1,2})\s+de\s+(\d{2})\s*d"),
    re.compile(r"(?i)(?:me\s+manda\s+|manda\s+)?(\d{1,2})\s+de\s+(\d{2})\b"),
    re.compile(r"(?i)(\d{1,2})\s*[-/]\s*(\d{2})\s*d"),
)
_COMPACT_QUANTITY_FORMAT_PATTERNS = (
    re.compile(r"^(\d{1,2})x(\d{2})d$"),
    re.compile(r"^(\d{1,2})jogos?(\d{2})d$"),
    re.compile(r"^(\d{1,2})jogos?de(\d{2})d$"),
    re.compile(r"^(\d{1,2})(\d{2})d$"),
)
_QUANTITY_ONLY_PATTERN = re.compile(r"(?i)(?:quero\s+|me\s+manda\s+|manda\s+)?(\d{1,2})\s+jogos?\b")


def _normalize_text(text: str) -> tuple[str, str]:
    spaced = " ".join(str(text or "").strip().split())
    compact = re.sub(r"\s+", "", spaced.lower()).replace("×", "x")
    return spaced, compact


def _valid_quantity(quantidade: int) -> bool:
    return int(quantidade) in VALID_QUANTITIES


def _valid_format(formato: int) -> bool:
    return int(formato) in _VALID_FORMATS


def _quantity_format_result(quantidade: int, formato: int) -> dict[str, Any] | None:
    if _valid_quantity(quantidade) and _valid_format(formato):
        return {"quantidade": int(quantidade), "formato": int(formato)}
    return None


def _quantity_only_result(quantidade: int) -> dict[str, Any] | None:
    if _valid_quantity(quantidade):
        return {"quantidade": int(quantidade), "formato": None}
    return None


def parse_whatsapp_message(text: str) -> dict[str, Any] | None:
    """Parse flexible WhatsApp requests into quantidade/formato."""
    spaced, compact = _normalize_text(text)
    if not spaced:
        return None

    for pattern in _QUANTITY_FORMAT_PATTERNS:
        match = pattern.search(spaced)
        if match:
            result = _quantity_format_result(int(match.group(1)), int(match.group(2)))
            if result:
                return result

    for pattern in _COMPACT_QUANTITY_FORMAT_PATTERNS:
        match = pattern.fullmatch(compact)
        if match:
            result = _quantity_format_result(int(match.group(1)), int(match.group(2)))
            if result:
                return result

    quantity_match = _QUANTITY_ONLY_PATTERN.search(spaced)
    if quantity_match:
        return _quantity_only_result(int(quantity_match.group(1)))

    if spaced.isdigit():
        return _quantity_only_result(int(spaced))

    return None
