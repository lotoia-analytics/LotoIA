from __future__ import annotations

from lotoia.clients.message_parser import HELP_MESSAGE, parse_whatsapp_message


def test_parse_whatsapp_message_examples() -> None:
    assert parse_whatsapp_message("quero 10 jogos de 17D") == {"quantidade": 10, "formato": 17}
    assert parse_whatsapp_message("10 jogos 17d") == {"quantidade": 10, "formato": 17}
    assert parse_whatsapp_message("me manda 5 de 15") == {"quantidade": 5, "formato": 15}
    assert parse_whatsapp_message("30 jogos") == {"quantidade": 30, "formato": None}


def test_parse_whatsapp_message_unrecognized() -> None:
    assert parse_whatsapp_message("bom dia") is None
    assert parse_whatsapp_message("") is None


def test_help_message_mentions_touch() -> None:
    assert "toque" in HELP_MESSAGE.lower()
