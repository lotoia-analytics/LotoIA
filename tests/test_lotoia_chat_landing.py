from __future__ import annotations

import json
from urllib.parse import urlsplit

import anyio

from backend.main import app
from lotoia.clients.constants import PLANS


def _html_request(path: str) -> tuple[int, str]:
    async def run() -> tuple[int, str]:
        messages: list[dict[str, object]] = []
        received = False
        url = urlsplit(path)

        async def receive() -> dict[str, object]:
            nonlocal received
            if received:
                return {"type": "http.disconnect"}
            received = True
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        await app(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "GET",
                "scheme": "http",
                "path": url.path,
                "raw_path": url.path.encode(),
                "query_string": url.query.encode(),
                "headers": [(b"user-agent", b"pytest")],
                "client": ("testclient", 50000),
                "server": ("testserver", 80),
                "root_path": "",
            },
            receive,
            send,
        )

        start = next(message for message in messages if message["type"] == "http.response.start")
        response_body = b"".join(
            message.get("body", b"")
            for message in messages
            if message["type"] == "http.response.body"
        )
        return int(start["status"]), response_body.decode("utf-8")

    return anyio.run(run)


def test_lotoia_chat_landing_returns_html() -> None:
    status_code, body = _html_request("/")
    assert status_code == 200
    assert "LotoIA" in body
    assert 'meta name="facebook-domain-verification" content="fub5vywq8iouvfqkl1n4qe4bk5ayom"' in body
    assert "Continuar com PIX" in body
    assert "Começar assinatura" in body


def test_lotoia_chat_landing_lists_all_plans() -> None:
    _, body = _html_request("/")
    for plan_key in PLANS:
        assert f'value="{plan_key}"' in body
