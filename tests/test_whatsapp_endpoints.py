from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

import anyio
import pytest
from sqlalchemy import inspect, text

from backend.main import app
from lotoia.database.database import create_database, get_engine, get_session


def _request(method: str, path: str, payload: dict | None = None) -> tuple[int, dict[str, object]]:
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

        headers = [(b"user-agent", b"pytest")]
        if payload is not None:
            headers.append((b"content-type", b"application/json"))

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
                "headers": headers,
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


@pytest.fixture(autouse=True)
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "lotoia.db"
    create_database(db_path)
    monkeypatch.setattr("backend.whatsapp.DEFAULT_DATABASE_PATH", db_path)
    monkeypatch.setattr("lotoia.clients.whatsapp_service.DEFAULT_DATABASE_PATH", db_path)
    monkeypatch.setattr("lotoia.clients.client_guard.DEFAULT_DATABASE_PATH", db_path)
    monkeypatch.setattr("lotoia.clients.repository.DEFAULT_DATABASE_PATH", db_path)
    return db_path


def test_whatsapp_tables_exist(isolated_db: Path) -> None:
    tables = set(inspect(get_engine(isolated_db)).get_table_names())
    assert {"lotoia_clients", "lotoia_client_daily_usage", "lotoia_client_generations"}.issubset(tables)


def test_client_activate_and_status(isolated_db: Path) -> None:
    status_code, body = _request(
        "POST",
        "/client/activate",
        {"phone": "5511999999999", "plan": "pro", "valor_pago": 49.99, "name": "Ana"},
    )
    assert status_code == 200
    assert body["status"] == "ok"
    assert body["client"]["plan"] == "pro"
    assert body["client"]["formato_maximo"] == 18

    status_code, status_body = _request("GET", "/client/5511999999999/status")
    assert status_code == 200
    assert status_body["name"] == "Ana"
    assert status_body["saldo_hoje"] == 30
    assert status_body["jogos_hoje"] == 0


def test_whatsapp_webhook_generates_games(isolated_db: Path) -> None:
    _request(
        "POST",
        "/client/activate",
        {"phone": "5511999999999", "plan": "elite", "valor_pago": 69.99, "name": "Ana"},
    )
    payload = {
        "data": {
            "key": {"remoteJid": "5511999999999@s.whatsapp.net", "id": "msg-001"},
            "message": {"conversation": "quero 2 jogos de 15D"},
        }
    }
    status_code, body = _request("POST", "/whatsapp/webhook", payload)
    assert status_code == 200
    assert body["status"] == "ok"
    assert body["quantidade"] == 2
    assert body["formato"] == 15
    assert len(body["games"]) == 2

    with get_session(isolated_db) as session:
        generations = session.execute(text("SELECT COUNT(*) FROM lotoia_client_generations")).scalar()
        usage = session.execute(text("SELECT jogos_count FROM lotoia_client_daily_usage")).scalar()
    assert int(generations or 0) == 1
    assert int(usage or 0) == 2


def test_whatsapp_webhook_help_message(isolated_db: Path) -> None:
    _request("POST", "/client/activate", {"phone": "5511999999999", "plan": "basico", "valor_pago": 15.99})
    status_code, body = _request(
        "POST",
        "/whatsapp/webhook",
        {
            "data": {
                "key": {"remoteJid": "5511999999999@s.whatsapp.net", "id": "msg-help"},
                "message": {"conversation": "oi"},
            }
        },
    )
    assert status_code == 200
    assert body["status"] == "help"
    assert "5 jogos de 15D" in str(body["message"])


def test_whatsapp_webhook_idempotency(isolated_db: Path) -> None:
    _request("POST", "/client/activate", {"phone": "5511999999999", "plan": "elite", "valor_pago": 69.99})
    payload = {
        "data": {
            "key": {"remoteJid": "5511999999999@s.whatsapp.net", "id": "dup-001"},
            "message": {"conversation": "5 jogos de 15D"},
        }
    }
    first_status, first_body = _request("POST", "/whatsapp/webhook", payload)
    second_status, second_body = _request("POST", "/whatsapp/webhook", payload)
    assert first_status == 200 and first_body["status"] == "ok"
    assert second_status == 200 and second_body["status"] == "ignored"
