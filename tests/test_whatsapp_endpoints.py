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


class _FakeEvolutionClient:
    def __init__(self) -> None:
        self.sent_texts: list[tuple[str, str]] = []
        self.sent_games: list[tuple[str, list[dict[str, object]], int]] = []
        self.sent_lists: list[tuple[str, dict[str, object]]] = []
        self.sent_buttons: list[tuple[str, dict[str, object]]] = []
        self.sent_polls: list[tuple[str, dict[str, object]]] = []
        self.sent_menu_bundles: list[tuple[str, dict[str, object]]] = []
        self.last_error_message = ""
        self.should_fail = False

    @property
    def is_configured(self) -> bool:
        return True

    def send_text(self, phone: str, message: str) -> bool:
        if self.should_fail:
            self.last_error_message = "simulated failure"
            return False
        self.sent_texts.append((phone, message))
        return True

    def send_games(self, phone: str, games: list[dict[str, object]], formato: int) -> bool:
        if self.should_fail:
            self.last_error_message = "simulated failure"
            return False
        self.sent_games.append((phone, games, formato))
        return True

    def send_list(self, phone: str, list_payload: dict[str, object]) -> bool:
        if self.should_fail:
            self.last_error_message = "simulated failure"
            return False
        self.sent_lists.append((phone, list_payload))
        return True

    def send_buttons(self, phone: str, buttons_payload: dict[str, object]) -> bool:
        if self.should_fail:
            self.last_error_message = "simulated failure"
            return False
        self.sent_buttons.append((phone, buttons_payload))
        return True

    def send_poll(self, phone: str, poll_payload: dict[str, object]) -> bool:
        if self.should_fail:
            self.last_error_message = "simulated failure"
            return False
        self.sent_polls.append((phone, poll_payload))
        return True

    def send_menu_bundle(self, phone: str, menu_bundle: dict[str, object]) -> bool:
        if self.should_fail:
            self.last_error_message = "simulated failure"
            return False
        self.sent_menu_bundles.append((phone, menu_bundle))
        text_fallback = str(menu_bundle.get("text_fallback") or "")
        delivered = bool(text_fallback and self.send_text(phone, text_fallback))
        buttons_payload = dict(menu_bundle.get("buttons_payload") or {})
        if buttons_payload and self.send_buttons(phone, buttons_payload):
            return True
        if self.send_list(phone, dict(menu_bundle.get("list_payload") or {})):
            return True
        return delivered


_FAKE_EVOLUTION: _FakeEvolutionClient | None = None


@pytest.fixture(autouse=True)
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    global _FAKE_EVOLUTION
    db_path = tmp_path / "lotoia.db"
    create_database(db_path)
    fake_evolution = _FakeEvolutionClient()
    _FAKE_EVOLUTION = fake_evolution
    monkeypatch.setattr("backend.whatsapp.DEFAULT_DATABASE_PATH", db_path)
    monkeypatch.setattr("lotoia.clients.whatsapp_service.DEFAULT_DATABASE_PATH", db_path)
    monkeypatch.setattr("lotoia.clients.client_guard.DEFAULT_DATABASE_PATH", db_path)
    monkeypatch.setattr("lotoia.clients.repository.DEFAULT_DATABASE_PATH", db_path)
    monkeypatch.setattr(
        "lotoia.clients.whatsapp_service.EvolutionApiClient",
        lambda *args, **kwargs: fake_evolution,
    )
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


def test_whatsapp_webhook_resolves_lid_jid_to_registered_phone(isolated_db: Path) -> None:
    _request(
        "POST",
        "/client/activate",
        {"phone": "5566992358330", "plan": "pro", "valor_pago": 49.99, "name": "Kleyson"},
    )
    payload = {
        "data": {
            "key": {
                "remoteJid": "69385314111689@lid",
                "remoteJidAlt": "66992358330@s.whatsapp.net",
                "id": "msg-lid",
            },
            "message": {"conversation": "5 jogos de 15D"},
        }
    }
    status_code, body = _request("POST", "/whatsapp/webhook", payload)
    assert status_code == 200
    assert body["status"] == "ok"
    assert body["quantidade"] == 5


def test_whatsapp_webhook_matches_client_without_country_code(isolated_db: Path) -> None:
    _request(
        "POST",
        "/client/activate",
        {"phone": "5566992358330", "plan": "pro", "valor_pago": 49.99, "name": "Kleyson"},
    )
    payload = {
        "data": {
            "key": {"remoteJid": "66992358330@s.whatsapp.net", "id": "msg-br-no-55"},
            "message": {"conversation": "5 jogos de 15D"},
        }
    }
    status_code, body = _request("POST", "/whatsapp/webhook", payload)
    assert status_code == 200
    assert body["status"] == "ok"
    assert body["quantidade"] == 5


def test_whatsapp_webhook_replies_to_ola_with_menu_text(isolated_db: Path) -> None:
    _request("POST", "/client/activate", {"phone": "5511999999999", "plan": "pro", "valor_pago": 49.99})
    status_code, body = _request(
        "POST",
        "/whatsapp/webhook",
        {
            "data": {
                "key": {"remoteJid": "5511999999999@s.whatsapp.net", "id": "msg-ola"},
                "message": {"conversation": "olá"},
            }
        },
    )
    assert status_code == 200
    assert body["status"] == "menu"
    assert body.get("delivered") is True
    assert _FAKE_EVOLUTION is not None
    assert any("Plano" in text and "Quantos jogos quer gerar?" in text for _, text in _FAKE_EVOLUTION.sent_texts)


def test_whatsapp_webhook_sends_quantity_menu_for_registered_client(isolated_db: Path) -> None:
    _request("POST", "/client/activate", {"phone": "5511999999999", "plan": "pro", "valor_pago": 49.99})
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
    assert body["status"] == "menu"
    assert body.get("delivered") is True
    assert _FAKE_EVOLUTION is not None
    assert len(_FAKE_EVOLUTION.sent_menu_bundles) == 1
    assert any("Digite: 5, 10, 20" in text for _, text in _FAKE_EVOLUTION.sent_texts)


def test_whatsapp_webhook_prompts_custom_quantity(isolated_db: Path) -> None:
    _request("POST", "/client/activate", {"phone": "5511999999999", "plan": "basico", "valor_pago": 15.99})
    status_code, body = _request(
        "POST",
        "/whatsapp/webhook",
        {
            "data": {
                "key": {"remoteJid": "5511999999999@s.whatsapp.net", "id": "msg-custom"},
                "message": {
                    "listResponseMessage": {
                        "title": "Outra quantidade",
                        "singleSelectReply": {"selectedRowId": "qty:custom"},
                    }
                },
            }
        },
    )
    assert status_code == 200
    assert body["status"] == "prompt"
    assert _FAKE_EVOLUTION is not None
    assert any("Outra quantidade" in text for _, text in _FAKE_EVOLUTION.sent_texts)


def test_whatsapp_webhook_generates_games_from_typed_quantity(isolated_db: Path) -> None:
    _request("POST", "/client/activate", {"phone": "5511999999999", "plan": "basico", "valor_pago": 15.99})
    _request(
        "POST",
        "/whatsapp/webhook",
        {
            "data": {
                "key": {"remoteJid": "5511999999999@s.whatsapp.net", "id": "msg-custom"},
                "message": {
                    "listResponseMessage": {
                        "title": "Outra quantidade",
                        "singleSelectReply": {"selectedRowId": "qty:custom"},
                    }
                },
            }
        },
    )
    status_code, body = _request(
        "POST",
        "/whatsapp/webhook",
        {
            "data": {
                "key": {"remoteJid": "5511999999999@s.whatsapp.net", "id": "msg-three"},
                "message": {"conversation": "3"},
            }
        },
    )
    assert status_code == 200
    assert body["status"] == "ok"
    assert body["quantidade"] == 3
    assert body["formato"] == 15


def test_whatsapp_webhook_generates_pro_games_at_plan_format(isolated_db: Path) -> None:
    _request("POST", "/client/activate", {"phone": "5511999999999", "plan": "pro", "valor_pago": 49.99})
    status_code, body = _request(
        "POST",
        "/whatsapp/webhook",
        {
            "data": {
                "key": {"remoteJid": "5511999999999@s.whatsapp.net", "id": "msg-pro-qty"},
                "message": {
                    "buttonsResponseMessage": {
                        "selectedButtonId": "qty:5",
                        "selectedDisplayText": "5 jogos",
                    }
                },
            }
        },
    )
    assert status_code == 200
    assert body["status"] == "ok"
    assert body["quantidade"] == 5
    assert body["formato"] is None
    assert body["formatos"] == [15, 18]
    assert body["targets"] == [{"formato": 15, "quantidade": 3}, {"formato": 18, "quantidade": 2}]


def test_whatsapp_webhook_generates_games_after_quantity_button(isolated_db: Path) -> None:
    _request("POST", "/client/activate", {"phone": "5511999999999", "plan": "basico", "valor_pago": 15.99})
    status_code, body = _request(
        "POST",
        "/whatsapp/webhook",
        {
            "data": {
                "key": {"remoteJid": "5511999999999@s.whatsapp.net", "id": "msg-qty"},
                "message": {
                    "buttonsResponseMessage": {
                        "selectedButtonId": "qty:10",
                        "selectedDisplayText": "10 jogos",
                    }
                },
            }
        },
    )
    assert status_code == 200
    assert body["status"] == "ok"
    assert body["quantidade"] == 10
    assert body["formato"] == 15
    assert _FAKE_EVOLUTION is not None
    assert len(_FAKE_EVOLUTION.sent_texts) == 1
    assert "🎯 *Seus jogos LotoIA — 15D*" in _FAKE_EVOLUTION.sent_texts[0][1]
    assert "✅ Gerado com estatística estrutural" in _FAKE_EVOLUTION.sent_texts[0][1]


def test_whatsapp_webhook_ignores_poll_update(isolated_db: Path) -> None:
    _request("POST", "/client/activate", {"phone": "5511999999999", "plan": "pro", "valor_pago": 49.99})
    status_code, body = _request(
        "POST",
        "/whatsapp/webhook",
        {
            "data": {
                "key": {"remoteJid": "5511999999999@s.whatsapp.net", "id": "msg-poll-update"},
                "message": {"pollUpdateMessage": {"vote": {"encPayload": "x", "encIv": "y"}}},
            }
        },
    )
    assert status_code == 200
    assert body["status"] == "ignored"
    assert body["reason"] == "poll_update"


def test_whatsapp_webhook_generates_games_from_list_selection(isolated_db: Path) -> None:
    _request("POST", "/client/activate", {"phone": "5511999999999", "plan": "pro", "valor_pago": 49.99})
    payload = {
        "data": {
            "key": {"remoteJid": "5511999999999@s.whatsapp.net", "id": "msg-list"},
            "message": {
                "listResponseMessage": {
                    "title": "15 dezenas (15D)",
                    "singleSelectReply": {"selectedRowId": "gen:5:15"},
                }
            },
        }
    }
    status_code, body = _request("POST", "/whatsapp/webhook", payload)
    assert status_code == 200
    assert body["status"] == "ok"
    assert body["quantidade"] == 5
    assert body["formato"] == 15


def test_whatsapp_webhook_generates_games_from_shorthand_format(isolated_db: Path) -> None:
    _request("POST", "/client/activate", {"phone": "5511999999999", "plan": "pro", "valor_pago": 49.99})
    for message, quantidade, formato in (
        ("2x15D", 2, 15),
        ("01 18D", 1, 18),
    ):
        status_code, body = _request(
            "POST",
            "/whatsapp/webhook",
            {
                "data": {
                    "key": {"remoteJid": "5511999999999@s.whatsapp.net", "id": f"msg-{message}"},
                    "message": {"conversation": message},
                }
            },
        )
        assert status_code == 200
        assert body["status"] == "ok"
        assert body["quantidade"] == quantidade
        assert body["formato"] == formato


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


def test_whatsapp_webhook_delivers_games_via_evolution(isolated_db: Path) -> None:
    _request(
        "POST",
        "/client/activate",
        {"phone": "5511999999999", "plan": "elite", "valor_pago": 69.99, "name": "Ana"},
    )
    payload = {
        "data": {
            "key": {"remoteJid": "5511999999999@s.whatsapp.net", "id": "msg-deliver"},
            "message": {"conversation": "2 jogos de 15D"},
        }
    }
    status_code, body = _request("POST", "/whatsapp/webhook", payload)
    assert status_code == 200
    assert body["status"] == "ok"
    assert body.get("delivered") is True
    assert _FAKE_EVOLUTION is not None
    assert len(_FAKE_EVOLUTION.sent_texts) == 1
    assert "🎯 *Seus jogos LotoIA — 15D*" in _FAKE_EVOLUTION.sent_texts[0][1]
    assert "⚠️ Jogue com responsabilidade" in _FAKE_EVOLUTION.sent_texts[0][1]
    games = list(body.get("games") or [])
    assert len(games) == 2
    assert all(game.get("cartao_validado_lei15a") for game in games)


def test_whatsapp_webhook_returns_200_when_evolution_fails(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    failing_client = _FakeEvolutionClient()
    failing_client.should_fail = True
    monkeypatch.setattr(
        "lotoia.clients.whatsapp_service.EvolutionApiClient",
        lambda *args, **kwargs: failing_client,
    )
    _request("POST", "/client/activate", {"phone": "5511999999999", "plan": "elite", "valor_pago": 69.99})
    status_code, body = _request(
        "POST",
        "/whatsapp/webhook",
        {
            "data": {
                "key": {"remoteJid": "5511999999999@s.whatsapp.net", "id": "msg-fail"},
                "message": {"conversation": "1 jogos de 15D"},
            }
        },
    )
    assert status_code == 200
    assert body["status"] == "ok"
    assert body.get("delivered") is False
    assert "delivery_error" in body
