from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

import anyio
import pytest

from backend.main import app
from lotoia.database.database import create_database
from lotoia.clients import asaas_webhook as asaas_webhook_module


def _request(
    method: str,
    path: str,
    payload: dict | None = None,
    *,
    headers: list[tuple[bytes, bytes]] | None = None,
) -> tuple[int, dict[str, object]]:
    async def run() -> tuple[int, dict[str, object]]:
        messages: list[dict[str, object]] = []
        received = False
        url = urlsplit(path)
        body = b"" if payload is None else json.dumps(payload).encode()

        async def receive() -> dict[str, object]:
            nonlocal received
            if received:
                return {"type": "http.disconnect"}
            received = True
            if method == "GET":
                return {"type": "http.request", "body": b"", "more_body": False}
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        request_headers = [(b"user-agent", b"pytest")]
        if payload is not None:
            request_headers.append((b"content-type", b"application/json"))
        if headers:
            request_headers.extend(headers)

        await app(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": method,
                "scheme": "http",
                "path": url.path,
                "raw_path": url.path.encode(),
                "query_string": url.query.encode(),
                "headers": request_headers,
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
        return start["status"], json.loads(response_body) if response_body else {}

    return anyio.run(run)


class _FakeEvolutionClient:
    def __init__(self) -> None:
        self.sent_texts: list[tuple[str, str]] = []

    @property
    def is_configured(self) -> bool:
        return True

    def send_text(self, phone: str, message: str) -> bool:
        self.sent_texts.append((phone, message))
        return True


@pytest.fixture(autouse=True)
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "lotoia.db"
    create_database(db_path)
    fake_evolution = _FakeEvolutionClient()
    monkeypatch.setattr("backend.asaas_webhook.DEFAULT_DATABASE_PATH", db_path)
    monkeypatch.setattr("backend.whatsapp.DEFAULT_DATABASE_PATH", db_path)
    monkeypatch.setattr("lotoia.clients.asaas_webhook.DEFAULT_DATABASE_PATH", db_path)
    monkeypatch.setattr("lotoia.clients.whatsapp_service.DEFAULT_DATABASE_PATH", db_path)
    monkeypatch.setattr("lotoia.clients.repository.DEFAULT_DATABASE_PATH", db_path)
    monkeypatch.setattr(
        "lotoia.clients.asaas_webhook.EvolutionApiClient",
        lambda *args, **kwargs: fake_evolution,
    )
    monkeypatch.setenv("ASAAS_WEBHOOK_TOKEN", "")
    asaas_webhook_module._PROCESSED_PAYMENTS.clear()
    return db_path


def test_parse_external_reference() -> None:
    assert asaas_webhook_module.parse_external_reference("lotoia:pro:5566992358330") == (
        "pro",
        "5566992358330",
    )
    assert asaas_webhook_module.parse_external_reference("other:pro:5566992358330") is None


def test_asaas_webhook_activates_client_on_payment_received(isolated_db: Path) -> None:
    payload = {
        "event": "PAYMENT_RECEIVED",
        "payment": {
            "id": "pay_test_001",
            "value": 99.90,
            "externalReference": "lotoia:completo:5566992358330",
            "customer": "cus_test",
        },
    }
    status_code, body = _request("POST", "/asaas/webhook", payload)
    assert status_code == 200
    assert body["status"] == "ok"
    assert body["phone"] == "5566992358330"
    assert body["plan"] == "completo"
    assert body["welcome_delivered"] is True

    status_code, status_body = _request("GET", "/client/5566992358330/status")
    assert status_code == 200
    assert status_body["plan"] == "completo"
    assert status_body["status"] == "ativo"
    assert status_body["formato_maximo_efetivo"] == 15


def test_asaas_webhook_ignores_unrelated_events() -> None:
    status_code, body = _request(
        "POST",
        "/asaas/webhook",
        {"event": "PAYMENT_CREATED", "payment": {"id": "pay_x"}},
    )
    assert status_code == 200
    assert body["status"] == "ignored"


def test_asaas_webhook_is_idempotent_by_payment_id(isolated_db: Path) -> None:
    payload = {
        "event": "PAYMENT_RECEIVED",
        "payment": {
            "id": "pay_test_dup",
            "value": 99.90,
            "externalReference": "lotoia:basico:5566996158937",
        },
    }
    first_status, first_body = _request("POST", "/asaas/webhook", payload)
    second_status, second_body = _request("POST", "/asaas/webhook", payload)
    assert first_status == 200 and first_body["status"] == "ok"
    assert second_status == 200 and second_body["status"] == "ignored"
    assert second_body["reason"] == "duplicate_payment"


def test_asaas_webhook_rejects_invalid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASAAS_WEBHOOK_TOKEN", "secure-webhook-token-32chars-minimum-ok")
    status_code, body = _request(
        "POST",
        "/asaas/webhook",
        {"event": "PAYMENT_RECEIVED", "payment": {"id": "pay_auth"}},
        headers=[(b"asaas-access-token", b"wrong-token")],
    )
    assert status_code == 401
    assert "Token" in str(body.get("detail", ""))
