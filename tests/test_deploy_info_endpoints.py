from __future__ import annotations

import json
from urllib.parse import urlsplit

import anyio

from backend.main import app
from lotoia.clients.result_conference_service import RESULTADO_CONFERENCE_FORMAT


def _get_json(path: str) -> tuple[int, dict[str, object]]:
    async def run() -> tuple[int, dict[str, object]]:
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
        return int(start["status"]), json.loads(response_body.decode("utf-8"))

    return anyio.run(run)


def test_health_exposes_resultado_conference_format() -> None:
    status_code, body = _get_json("/health")
    assert status_code == 200
    assert body["resultado_conference"] == RESULTADO_CONFERENCE_FORMAT


def test_whatsapp_status_exposes_deploy_info() -> None:
    status_code, body = _get_json("/whatsapp/status")
    assert status_code == 200
    deploy = body.get("deploy")
    assert isinstance(deploy, dict)
    assert deploy.get("resultado_conference") == RESULTADO_CONFERENCE_FORMAT
