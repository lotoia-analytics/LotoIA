from __future__ import annotations

import pytest

from lotoia.clients.message_parser import HELP_MESSAGE, parse_whatsapp_message


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("quero 10 jogos de 17D", {"quantidade": 10, "formato": 17}),
        ("10 jogos 17d", {"quantidade": 10, "formato": 17}),
        ("me manda 5 de 15", {"quantidade": 5, "formato": 15}),
        ("30 jogos", {"quantidade": 30, "formato": None}),
        ("3", {"quantidade": 3, "formato": None}),
        ("03", {"quantidade": 3, "formato": None}),
        ("2x15D", {"quantidade": 2, "formato": 15}),
        ("2 x 15d", {"quantidade": 2, "formato": 15}),
        ("01 18D", {"quantidade": 1, "formato": 18}),
        ("1 18d", {"quantidade": 1, "formato": 18}),
        ("1 Jogo 18D", {"quantidade": 1, "formato": 18}),
        ("3 Jogo  18D", {"quantidade": 3, "formato": 18}),
        ("3 Jogo 18D", {"quantidade": 3, "formato": 18}),
        ("2x18D", {"quantidade": 2, "formato": 18}),
        ("2 x 18D", {"quantidade": 2, "formato": 18}),
        ("3jogo18d", {"quantidade": 3, "formato": 18}),
        ("3 jogos18d", {"quantidade": 3, "formato": 18}),
        ("5-18d", {"quantidade": 5, "formato": 18}),
        ("4/15D", {"quantidade": 4, "formato": 15}),
        ("1015D", {"quantidade": 10, "formato": 15}),
        ("1015d", {"quantidade": 10, "formato": 15}),
        ("5", {"quantidade": 5, "formato": None}),
    ],
)
def test_parse_whatsapp_message_flexible_inputs(text: str, expected: dict[str, int | None]) -> None:
    assert parse_whatsapp_message(text) == expected


def test_parse_whatsapp_message_unrecognized() -> None:
    assert parse_whatsapp_message("bom dia") is None
    assert parse_whatsapp_message("") is None
    assert parse_whatsapp_message("18D") is None
    assert parse_whatsapp_message("jogo 18d") is None


def test_help_message_mentions_quantity() -> None:
    assert "jogos" in HELP_MESSAGE.lower()
