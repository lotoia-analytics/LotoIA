from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import anyio
import pytest
from sqlalchemy import inspect

from backend.main import app
from lotoia.clients.messenger_consultor.freemium_guard import FREE_CHECK_LIMIT
from lotoia.clients.messenger_consultor.game_handler import MessengerGameHandler
from lotoia.clients.messenger_consultor.intent_parser import MessengerIntentParser
from lotoia.clients.messenger_consultor.stats_service import MessengerStatsService
from lotoia.clients.repository import ClientRepository
from lotoia.database.database import (
    Lead,
    LotofacilOfficialHistory,
    MessengerConversationState,
    create_database,
    get_engine,
    get_session,
)
from lotoia.governance.lei15a_operational import NUCLEO_LEI15_15D_CONGELADO


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


class _FakeMessengerClient:
    def __init__(self) -> None:
        self.sent_texts: list[tuple[str, str]] = []

    @property
    def is_configured(self) -> bool:
        return True

    def send_text_sync(self, psid: str, text: str) -> bool:
        self.sent_texts.append((psid, text))
        return True


OFFICIAL_NUMBERS = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 20, 21, 22, 23, 24]


def seed_official_history(db_path: Path, *, contest: int = 3709) -> None:
    with get_session(db_path) as session:
        session.merge(
            LotofacilOfficialHistory(
                contest_number=int(contest),
                draw_date="12/06/2026",
                numbers=",".join(str(number) for number in OFFICIAL_NUMBERS),
                numbers_signature="test",
            )
        )
        session.commit()


@pytest.fixture(autouse=True)
def isolated_consultor_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, _FakeMessengerClient]:
    db_path = tmp_path / "consultor.db"
    create_database(db_path)
    seed_official_history(db_path)
    fake = _FakeMessengerClient()
    monkeypatch.setenv("MESSENGER_VERIFY_TOKEN", "test-verify-token")
    monkeypatch.setattr("backend.routers.messenger_webhook.DEFAULT_DATABASE_PATH", db_path)
    monkeypatch.setattr("lotoia.clients.messenger_consultor.consultor_service.DEFAULT_DATABASE_PATH", db_path)
    monkeypatch.setattr("lotoia.clients.client_guard.DEFAULT_DATABASE_PATH", db_path)
    monkeypatch.setattr("lotoia.clients.repository.DEFAULT_DATABASE_PATH", db_path)
    monkeypatch.setattr(
        "lotoia.clients.messenger_service.MessengerEvolutionService",
        lambda *args, **kwargs: fake,
    )
    return db_path, fake


def _payload(psid: str, text: str, mid: str) -> dict[str, object]:
    return {
        "entry": [
            {
                "messaging": [
                    {
                        "sender": {"id": psid},
                        "message": {"text": text, "mid": mid},
                    }
                ]
            }
        ]
    }


def test_resultado_retorna_dados_reais_postgres(isolated_consultor_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_consultor_db
    message = MessengerStatsService(db_path).get_resultado()
    assert "3709" in message
    assert "01" in message and "24" in message


def test_atrasadas_top10_ordenadas_corretamente(isolated_consultor_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_consultor_db
    message = MessengerStatsService(db_path).get_atrasadas()
    assert "Top 10" in message
    assert "Dezena" in message


def test_frequentes_top10_com_percentual(isolated_consultor_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_consultor_db
    message = MessengerStatsService(db_path).get_frequentes()
    assert "%" in message
    assert "Top 10" in message


def test_score_retorna_historico_nucleo_lei15(isolated_consultor_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_consultor_db
    message = MessengerStatsService(db_path).get_score()
    assert "Núcleo" in message
    assert str(sorted(NUCLEO_LEI15_15D_CONGELADO)[0]).zfill(2) in message


def test_curioso_3_conferencias_gratis(isolated_consultor_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_consultor_db
    psid = "psid-free-001"
    dezenas_text = "01 03 05 07 09 11 13 15 17 19 20 21 22 23 24 25"
    for index in range(FREE_CHECK_LIMIT):
        status, result = _request_json("POST", "/messenger/webhook", _payload(psid, "conferir", f"mid-c-{index}"))
        assert status == 200
        assert result.get("status") == "prompt"
        status, result = _request_json("POST", "/messenger/webhook", _payload(psid, dezenas_text, f"mid-d-{index}"))
        assert status == 200
        assert result.get("status") == "ok"
        assert "Pontos" in str(result.get("message") or "")


def test_curioso_bloqueado_na_4a_com_link(isolated_consultor_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_consultor_db
    psid = "psid-free-002"
    dezenas_text = "01 03 05 07 09 11 13 15 17 19 20 21 22 23 24 25"
    for index in range(FREE_CHECK_LIMIT):
        _request_json("POST", "/messenger/webhook", _payload(psid, "conferir", f"mid-e-{index}"))
        _request_json("POST", "/messenger/webhook", _payload(psid, dezenas_text, f"mid-f-{index}"))
    status, result = _request_json("POST", "/messenger/webhook", _payload(psid, "conferir", "mid-g-4"))
    assert status == 200
    assert result.get("status") == "error"
    assert "www.lotoia.chat" in str(result.get("message") or "")


def test_conferencia_retorna_pontos_corretos(isolated_consultor_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_consultor_db
    message = MessengerStatsService(db_path).conferir_jogo(OFFICIAL_NUMBERS, concurso=3709)
    assert "15/15" in message


def test_conferencia_rodape_compara_nucleo_lei15(isolated_consultor_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_consultor_db
    message = MessengerStatsService(db_path).conferir_jogo(OFFICIAL_NUMBERS, concurso=3709)
    assert "núcleo LotoIA" in message


def test_parse_dezenas_15_numeros_valido() -> None:
    parser = MessengerIntentParser()
    numbers = parser.parse_dezenas("01 03 05 07 09 11 13 15 17 19 20 21 22 23 24 25")
    assert numbers is not None
    assert len(numbers) == 15


def test_parse_dezenas_invalido_retorna_erro_amigavel(isolated_consultor_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_consultor_db
    message = MessengerStatsService(db_path).conferir_jogo([1, 2, 3])
    assert "15 dezenas" in message


def test_curioso_gera_recebe_link_site(isolated_consultor_db: tuple[Path, _FakeMessengerClient]) -> None:
    _db, _ = isolated_consultor_db
    status, result = _request_json("POST", "/messenger/webhook", _payload("psid-gen-001", "gerar 3 jogos", "mid-gen"))
    assert status == 200
    assert "www.lotoia.chat" in str(result.get("message") or "")


def test_cliente_ativo_gera_jogos_lei15_intacto(
    isolated_consultor_db: tuple[Path, _FakeMessengerClient],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path, _ = isolated_consultor_db
    monkeypatch.setattr(
        "lotoia.clients.messenger_consultor.generation.generate_ranked_games",
        lambda **kwargs: [
            {
                "numbers": list(range(1, 16)),
                "cartao_validado_lei15a": list(NUCLEO_LEI15_15D_CONGELADO),
                "final_score": {"final_score": 1.0},
            }
            for _ in range(int(kwargs.get("total_games", 1)))
        ],
    )
    monkeypatch.setattr(
        "lotoia.clients.messenger_consultor.game_handler.resolve_next_target_contest",
        lambda db_path: 3710,
    )
    repository = ClientRepository(db_path)
    repository.activate_messenger_client(psid="psid-active-100", plan="basico", valor_pago=15.99, name="Cliente")
    status, result = _request_json("POST", "/messenger/webhook", _payload("psid-active-100", "3", "mid-active"))
    assert status == 200
    assert result.get("status") == "ok"
    assert result.get("channel") == "messenger"
    games = result.get("games") or []
    assert len(games) == 3
    assert len(games[0].get("cartao_validado_lei15a") or []) == 15


def test_limite_global_30_whatsapp_mais_messenger(isolated_consultor_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_consultor_db
    repository = ClientRepository(db_path)
    client = repository.activate_messenger_client(psid="psid-limit", plan="basico", valor_pago=15.99, name="Cliente")
    handler = MessengerGameHandler(db_path)
    repository.log_client_generation(
        client_id=int(client["id"]),
        phone=str(client["phone"]),
        formato=15,
        quantidade=20,
        jogos=[{"numbers": list(range(1, 16))}],
        channel="whatsapp",
    )
    repository.log_client_generation(
        client_id=int(client["id"]),
        phone=str(client["phone"]),
        formato=15,
        quantidade=10,
        jogos=[{"numbers": list(range(1, 16))}],
        channel="messenger",
    )
    assert handler.get_global_daily_usage(int(client["id"])) == 30


def test_state_awaiting_check_input(isolated_consultor_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_consultor_db
    psid = "psid-state-001"
    _request_json("POST", "/messenger/webhook", _payload(psid, "conferir", "mid-state-1"))
    with get_session(db_path) as session:
        row = session.get(MessengerConversationState, psid)
        assert row is not None
        assert row.state == "awaiting_check_input"


def test_state_reset_apos_conferencia(isolated_consultor_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_consultor_db
    psid = "psid-state-002"
    dezenas = "01 03 05 07 09 11 13 15 17 19 20 21 22 23 24 25"
    _request_json("POST", "/messenger/webhook", _payload(psid, "conferir", "mid-state-2"))
    _request_json("POST", "/messenger/webhook", _payload(psid, dezenas, "mid-state-3"))
    with get_session(db_path) as session:
        row = session.get(MessengerConversationState, psid)
        assert row is not None
        assert row.state == "initial"


def test_novo_psid_cria_estado_e_lead_postgres(isolated_consultor_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_consultor_db
    psid = "psid-new-lead-001"
    status, result = _request_json("POST", "/messenger/webhook", _payload(psid, "olá", "mid-new-1"))
    assert status == 200
    assert result.get("status") == "menu"
    with get_session(db_path) as session:
        assert session.get(MessengerConversationState, psid) is not None
        lead = session.query(Lead).filter(Lead.messenger_psid == psid).one_or_none()
        assert lead is not None
        assert lead.source == "messenger"


def test_messenger_consultor_schema(isolated_consultor_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_consultor_db
    tables = set(inspect(get_engine(db_path)).get_table_names())
    assert "messenger_conversation_state" in tables
