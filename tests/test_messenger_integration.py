from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import anyio
import pytest
from sqlalchemy import inspect

from backend.main import app
from lotoia.clients.repository import ClientRepository
from lotoia.database.database import GenerationEvent, Lead, create_database, get_engine, get_session


def _request_json(method: str, path: str, payload: dict | None = None) -> tuple[int, dict[str, object]]:
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
        if response_body:
            try:
                parsed: dict[str, object] = json.loads(response_body)
            except json.JSONDecodeError:
                parsed = {"raw": response_body.decode()}
        else:
            parsed = {}
        return start["status"], parsed

    return anyio.run(run)


def _request_text(method: str, path: str) -> tuple[int, str]:
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
                "method": method,
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
        return start["status"], response_body.decode()

    return anyio.run(run)


class _FakeMessengerClient:
    def __init__(self) -> None:
        self.sent_texts: list[tuple[str, str]] = []
        self.last_error_message = ""

    @property
    def is_configured(self) -> bool:
        return True

    def send_text_sync(self, psid: str, text: str) -> bool:
        self.sent_texts.append((psid, text))
        return True


@pytest.fixture(autouse=True)
def isolated_messenger_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, _FakeMessengerClient]:
    db_path = tmp_path / "messenger_test.db"
    create_database(db_path)
    fake = _FakeMessengerClient()
    monkeypatch.setenv("MESSENGER_VERIFY_TOKEN", "test-verify-token")
    monkeypatch.setattr("backend.routers.messenger_webhook.DEFAULT_DATABASE_PATH", db_path)
    monkeypatch.setattr("lotoia.clients.messenger_service.DEFAULT_DATABASE_PATH", db_path)
    monkeypatch.setattr("lotoia.clients.messenger_onboarding.DEFAULT_DATABASE_PATH", db_path)
    monkeypatch.setattr("lotoia.clients.client_guard.DEFAULT_DATABASE_PATH", db_path)
    monkeypatch.setattr("lotoia.clients.repository.DEFAULT_DATABASE_PATH", db_path)
    monkeypatch.setattr(
        "lotoia.clients.messenger_service.MessengerEvolutionService",
        lambda *args, **kwargs: fake,
    )
    return db_path, fake


def test_messenger_webhook_verification(isolated_messenger_db: tuple[Path, _FakeMessengerClient]) -> None:
    _ = isolated_messenger_db
    query = urlencode(
        {
            "hub.mode": "subscribe",
            "hub.verify_token": "test-verify-token",
            "hub.challenge": "123456789",
        }
    )
    status, body = _request_text("GET", f"/messenger/webhook?{query}")
    assert status == 200
    assert body == "123456789"

    bad_query = urlencode(
        {
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong-token",
            "hub.challenge": "123456789",
        }
    )
    bad_status, _ = _request_json("GET", f"/messenger/webhook?{bad_query}")
    assert bad_status == 403


def test_new_lead_capture(isolated_messenger_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, fake = isolated_messenger_db
    payload = {
        "entry": [
            {
                "messaging": [
                    {
                        "sender": {"id": "psid-new-001"},
                        "message": {"text": "olá", "mid": "mid-001"},
                    }
                ]
            }
        ]
    }
    status, result = _request_json("POST", "/messenger/webhook", payload)
    assert status == 200
    assert result.get("status") == "onboarding"
    assert result.get("psid") == "psid-new-001"
    assert result.get("delivered") is True

    with get_session(db_path) as session:
        lead = session.query(Lead).filter(Lead.messenger_psid == "psid-new-001").one()
        assert lead.source == "messenger"
        event = (
            session.query(GenerationEvent)
            .filter(GenerationEvent.strategy == "messenger_lead_captured")
            .one()
        )
        assert event.channel == "messenger"

    assert fake.sent_texts
    assert fake.sent_texts[0][0] == "psid-new-001"


def test_existing_active_client_generates_games(
    isolated_messenger_db: tuple[Path, _FakeMessengerClient],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path, _fake = isolated_messenger_db
    monkeypatch.setattr(
        "lotoia.clients.messenger_service.generate_ranked_games",
        lambda **kwargs: [
            {
                "numbers": list(range(1, 16)),
                "cartao_validado_lei15a": list(range(1, 16)),
                "final_score": {"final_score": 1.0},
            }
            for _ in range(int(kwargs.get("total_games", 1)))
        ],
    )
    monkeypatch.setattr(
        "lotoia.clients.messenger_service.resolve_next_target_contest",
        lambda db_path: 3709,
    )

    repository = ClientRepository(db_path)
    repository.activate_messenger_client(
        psid="psid-active-001",
        plan="basico",
        valor_pago=15.99,
        name="Cliente Messenger",
    )

    payload = {
        "entry": [
            {
                "messaging": [
                    {
                        "sender": {"id": "psid-active-001"},
                        "message": {"text": "3", "mid": "mid-002"},
                    }
                ]
            }
        ]
    }
    status, result = _request_json("POST", "/messenger/webhook", payload)
    assert status == 200
    assert result.get("status") == "ok"
    assert result.get("channel") == "messenger"
    assert result.get("quantidade") == 3
    games = result.get("games") or []
    assert len(games) == 3

    client = repository.get_by_messenger_psid("psid-active-001")
    assert client is not None
    generations = repository.get_client_generations(int(client["id"]))
    assert generations
    assert generations[0]["channel"] == "messenger"
    assert generations[0]["quantidade"] == 3


def test_messenger_schema_migration(isolated_messenger_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_messenger_db
    engine = get_engine(db_path)
    inspector = inspect(engine)
    client_columns = {column["name"] for column in inspector.get_columns("lotoia_clients")}
    assert "messenger_psid" in client_columns
    assert "channel" in client_columns
    generation_columns = {column["name"] for column in inspector.get_columns("lotoia_client_generations")}
    assert "channel" in generation_columns
    event_columns = {column["name"] for column in inspector.get_columns("generation_events")}
    assert "channel" in event_columns
