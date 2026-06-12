from __future__ import annotations

from typing import Any

import pytest

from lotoia.clients.evolution_client import EvolutionApiClient, GENERATION_ERROR_MESSAGE


class FakeResponse:
    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, json: dict[str, Any], headers: dict[str, str], timeout: float) -> FakeResponse:  # noqa: ARG002
        self.calls.append({"url": url, "json": json, "headers": headers})
        if not self.responses:
            raise RuntimeError("no fake responses left")
        return self.responses.pop(0)


def test_evolution_client_send_text_success() -> None:
    session = FakeSession([FakeResponse(200, '{"status":"ok"}')])
    client = EvolutionApiClient(
        base_url="https://evolution.example.app",
        api_key="secret-key",
        instance="lotoia-main",
        session=session,
    )

    assert client.send_text("5511999999999", "Olá") is True
    assert len(session.calls) == 1
    assert session.calls[0]["url"] == "https://evolution.example.app/message/sendText/lotoia-main"
    assert session.calls[0]["headers"]["apikey"] == "secret-key"
    assert session.calls[0]["json"] == {"number": "5511999999999", "text": "Olá"}


def test_evolution_client_send_text_retries_once() -> None:
    session = FakeSession([FakeResponse(500, "temporary"), FakeResponse(201, "ok")])
    client = EvolutionApiClient(
        base_url="https://evolution.example.app",
        api_key="secret-key",
        instance="lotoia-main",
        session=session,
    )

    assert client.send_text("5511999999999", "retry me") is True
    assert len(session.calls) == 2


def test_evolution_client_send_text_returns_false_when_unconfigured() -> None:
    client = EvolutionApiClient(base_url="", api_key="", instance="")
    assert client.send_text("5511999999999", "test") is False


def test_evolution_client_send_games_formats_message() -> None:
    session = FakeSession([FakeResponse(200)])
    client = EvolutionApiClient(
        base_url="https://evolution.example.app",
        api_key="secret-key",
        instance="lotoia-main",
        session=session,
    )
    games = [{"numbers": [1, 2, 3, 4, 9, 10, 11, 12, 13, 18, 20, 22, 23, 24, 25]}]

    assert client.send_games("5511999999999", games, 15) is True
    sent_text = session.calls[0]["json"]["text"]
    assert "🎯 *Seus jogos LotoIA — 15D*" in sent_text
    assert "Jogo 01: 01 02 03 04 09 10 11 12 13 18 20 22 23 24 25" in sent_text
    assert "✅ Gerado com estatística estrutural" in sent_text
    assert "⚠️ Jogue com responsabilidade" in sent_text


def test_generation_error_message_defined() -> None:
    assert "Erro ao gerar jogos" in GENERATION_ERROR_MESSAGE


def test_evolution_client_send_poll_success() -> None:
    session = FakeSession([FakeResponse(200, '{"status":"ok"}')])
    client = EvolutionApiClient(
        base_url="https://evolution.example.app",
        api_key="secret-key",
        instance="lotoia-main",
        session=session,
    )
    poll_payload = {
        "name": "Quantos jogos?",
        "selectableCount": 1,
        "values": ["5 jogos", "10 jogos"],
    }

    assert client.send_poll("5511999999999", poll_payload) is True
    assert session.calls[0]["url"] == "https://evolution.example.app/message/sendPoll/lotoia-main"
    assert session.calls[0]["json"]["values"] == ["5 jogos", "10 jogos"]


def test_evolution_client_send_menu_bundle_text_only() -> None:
    session = FakeSession([FakeResponse(200, '{"status":"ok"}')])
    client = EvolutionApiClient(
        base_url="https://evolution.example.app",
        api_key="secret-key",
        instance="lotoia-main",
        session=session,
    )
    bundle = {
        "text_only": True,
        "text_fallback": "👋 Olá! Plano Básico — até 15D",
    }

    assert client.send_menu_bundle("5511999999999", bundle) is True
    assert len(session.calls) == 1
    assert "/sendText/" in session.calls[0]["url"]


def test_evolution_client_send_menu_bundle_sends_text_before_list() -> None:
    session = FakeSession(
        [
            FakeResponse(200, '{"status":"ok"}'),
            FakeResponse(200, '{"status":"ok"}'),
        ]
    )
    client = EvolutionApiClient(
        base_url="https://evolution.example.app",
        api_key="secret-key",
        instance="lotoia-main",
        session=session,
    )
    bundle = {
        "prefer_list": True,
        "list_payload": {
            "title": "LotoIA",
            "description": "Escolha",
            "buttonText": "Escolher quantidade",
            "footerText": "LotoIA",
            "sections": [{"title": "Qtd", "rows": [{"title": "05 Jogos", "rowId": "qty:5"}]}],
        },
        "buttons_payload": {
            "title": "LotoIA",
            "description": "Escolha",
            "footer": "LotoIA",
            "buttons": [{"type": "reply", "displayText": "05 Jogos", "id": "qty:5"}],
        },
        "text_fallback": "fallback",
    }

    assert client.send_menu_bundle("5511999999999", bundle) is True
    assert len(session.calls) == 2
    assert "/sendText/" in session.calls[0]["url"]
    assert "/sendList/" in session.calls[1]["url"]


def test_evolution_client_send_list_success() -> None:
    session = FakeSession([FakeResponse(200, '{"status":"ok"}')])
    client = EvolutionApiClient(
        base_url="https://evolution.example.app",
        api_key="secret-key",
        instance="lotoia-main",
        session=session,
    )
    list_payload = {
        "title": "LotoIA",
        "description": "Escolha",
        "buttonText": "Escolher",
        "footerText": "Footer",
        "sections": [{"title": "Qtd", "rows": [{"title": "5 jogos", "rowId": "qty:5"}]}],
    }

    assert client.send_list("5511999999999", list_payload) is True
    assert session.calls[0]["url"] == "https://evolution.example.app/message/sendList/lotoia-main"
    assert session.calls[0]["json"]["buttonText"] == "Escolher"
    assert session.calls[0]["json"]["sections"][0]["rows"][0]["rowId"] == "qty:5"
