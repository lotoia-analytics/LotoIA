from __future__ import annotations

from typing import Any

from lotoia.clients.messenger_evolution_service import MessengerEvolutionService


class _FakeSession:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return _FakeResponse(200, '{"recipient_id":"psid-123","message_id":"mid-1"}')


class _FakeResponse:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text


def test_messenger_graph_api_send_text_success() -> None:
    session = _FakeSession()
    client = MessengerEvolutionService(
        page_access_token="page-token",
        page_id="1487707086436987",
        session=session,
    )

    delivered = client.send_text_sync("psid-123", "Olá LotoIA")

    assert delivered is True
    assert client.uses_graph_api is True
    assert len(session.calls) == 1
    assert session.calls[0]["url"] == "https://graph.facebook.com/v21.0/me/messages"
    assert session.calls[0]["params"] == {"access_token": "page-token"}
    assert session.calls[0]["json"] == {
        "recipient": {"id": "psid-123"},
        "messaging_type": "RESPONSE",
        "message": {"text": "Olá LotoIA"},
    }


def test_messenger_graph_api_unconfigured_error() -> None:
    client = MessengerEvolutionService()

    delivered = client.send_text_sync("psid-123", "teste")

    assert delivered is False
    assert "FACEBOOK_PAGE_ACCESS_TOKEN" in client.last_error_message
