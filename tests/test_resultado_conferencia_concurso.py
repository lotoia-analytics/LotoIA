from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import anyio
import pytest
from sqlalchemy import inspect, text

from backend.main import app
from lotoia.clients.repository import ClientRepository
from lotoia.clients.result_conference_service import (
    RESULTADO_PROMPT,
    ResultConferenceService,
    build_result_conference_message,
)
from lotoia.database.database import (
    LotofacilOfficialHistory,
    MessengerConversationState,
    create_database,
    get_engine,
    get_session,
)
from tests.test_messenger_consultor import OFFICIAL_NUMBERS, _FakeMessengerClient, _payload, _request_json


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
def isolated_resultado_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, _FakeMessengerClient]:
    db_path = tmp_path / "resultado.db"
    create_database(db_path)
    seed_official_history(db_path)
    fake = _FakeMessengerClient()
    monkeypatch.setenv("MESSENGER_VERIFY_TOKEN", "test-verify-token")
    monkeypatch.setattr("backend.routers.messenger_webhook.DEFAULT_DATABASE_PATH", db_path)
    monkeypatch.setattr("lotoia.clients.messenger_consultor.consultor_service.DEFAULT_DATABASE_PATH", db_path)
    monkeypatch.setattr("lotoia.clients.client_guard.DEFAULT_DATABASE_PATH", db_path)
    monkeypatch.setattr("lotoia.clients.repository.DEFAULT_DATABASE_PATH", db_path)
    monkeypatch.setattr("lotoia.clients.whatsapp_service.DEFAULT_DATABASE_PATH", db_path)
    monkeypatch.setattr(
        "lotoia.clients.messenger_service.MessengerEvolutionService",
        lambda *args, **kwargs: fake,
    )
    monkeypatch.setattr(
        "lotoia.clients.result_conference_service.sync_latest_official_results",
        lambda db_path: [],
    )
    monkeypatch.setattr(
        "lotoia.clients.result_conference_service.ensure_official_contest_available",
        lambda db_path, contest_number, sync_latest_first=True: False,
    )
    return db_path, fake


def test_state_awaiting_concurso_apos_resultado(isolated_resultado_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_resultado_db
    psid = "psid-resultado-001"
    status, result = _request_json("POST", "/messenger/webhook", _payload(psid, "resultado", "mid-res-1"))
    assert status == 200
    assert result.get("status") == "prompt"
    assert "Qual o número do concurso?" in str(result.get("message") or "")
    with get_session(db_path) as session:
        row = session.get(MessengerConversationState, psid)
        assert row is not None
        assert row.state == "awaiting_concurso"


def test_concurso_valido_retorna_resultado_oficial(isolated_resultado_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_resultado_db
    message = build_result_conference_message(contest_number=3709, client_id=None, db_path=db_path)
    assert "Concurso 3709" in message
    assert "12/06/2026" in message
    assert "01 03 05 07 09 11 13 15 17 19 20 21 22 23 24" in message


def test_cliente_com_jogos_e_premiado_celebra(isolated_resultado_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_resultado_db
    repository = ClientRepository(db_path)
    client = repository.activate_messenger_client(
        psid="psid-premiado",
        plan="basico",
        valor_pago=15.99,
        name="Premiado",
    )
    repository.log_client_generation(
        client_id=int(client["id"]),
        phone=str(client["phone"]),
        formato=15,
        quantidade=3,
        concurso_alvo=3709,
        channel="messenger",
        jogos=[
            {"cartao_validado_lei15a": OFFICIAL_NUMBERS},
            {"cartao_validado_lei15a": OFFICIAL_NUMBERS[:11] + [2, 4, 6, 8]},
            {"cartao_validado_lei15a": list(range(1, 16))},
        ],
    )
    message = build_result_conference_message(contest_number=3709, client_id=int(client["id"]), db_path=db_path)
    assert "✅ 13 pontos" in message or "✅ 15 pontos" in message
    assert "✅ 11 pontos" in message
    assert "Jogos premiados LotoIA" in message
    assert "07 pontos" not in message
    assert "🏆 Parabéns! Você foi premiado!" in message
    assert "lotéricas" in message.lower()


def test_cliente_com_jogos_sem_premio_encoraja(isolated_resultado_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_resultado_db
    repository = ClientRepository(db_path)
    client = repository.activate_messenger_client(
        psid="psid-sem-premio",
        plan="basico",
        valor_pago=15.99,
        name="Sem Premio",
    )
    repository.log_client_generation(
        client_id=int(client["id"]),
        phone=str(client["phone"]),
        formato=15,
        quantidade=3,
        concurso_alvo=3709,
        channel="messenger",
        jogos=[
            {"cartao_validado_lei15a": OFFICIAL_NUMBERS[:10] + [2, 4, 6, 8, 10]},
            {"cartao_validado_lei15a": OFFICIAL_NUMBERS[:9] + [2, 4, 6, 8, 10, 12]},
            {"cartao_validado_lei15a": OFFICIAL_NUMBERS[:10] + [2, 4, 6, 8, 25]},
        ],
    )
    message = build_result_conference_message(contest_number=3709, client_id=int(client["id"]), db_path=db_path)
    assert "3 jogos, mas nenhum atingiu 11 pontos" in message
    assert "10 pontos" not in message
    assert "09 pontos" not in message
    assert "Não foi dessa vez" in message
    assert "Parabéns" not in message


def test_cliente_com_jogos_lista_apenas_premiados(isolated_resultado_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_resultado_db
    repository = ClientRepository(db_path)
    client = repository.activate_messenger_client(
        psid="psid-misto",
        plan="basico",
        valor_pago=15.99,
        name="Misto",
    )
    repository.log_client_generation(
        client_id=int(client["id"]),
        phone=str(client["phone"]),
        formato=15,
        quantidade=4,
        concurso_alvo=3709,
        channel="messenger",
        jogos=[
            {"cartao_validado_lei15a": OFFICIAL_NUMBERS[:10] + [2, 4, 6, 8, 10]},
            {"cartao_validado_lei15a": OFFICIAL_NUMBERS[:11] + [2, 4, 6, 8]},
            {"cartao_validado_lei15a": OFFICIAL_NUMBERS[:12] + [2, 4, 6]},
            {"cartao_validado_lei15a": OFFICIAL_NUMBERS[:9] + [2, 4, 6, 8, 10, 12]},
        ],
    )
    message = build_result_conference_message(contest_number=3709, client_id=int(client["id"]), db_path=db_path)
    assert "Jogos premiados LotoIA (2 de 4)" in message
    assert "✅ 11 pontos" in message
    assert "✅ 12 pontos" in message
    assert "10 pontos" not in message
    assert "09 pontos" not in message


def test_cliente_sem_jogos_no_concurso_encoraja(isolated_resultado_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_resultado_db
    repository = ClientRepository(db_path)
    client = repository.activate_messenger_client(
        psid="psid-sem-jogos",
        plan="basico",
        valor_pago=15.99,
        name="Sem Jogos",
    )
    message = build_result_conference_message(contest_number=3709, client_id=int(client["id"]), db_path=db_path)
    assert "Você não gerou jogos para esse concurso." in message
    assert "Não foi dessa vez" in message


def test_concurso_inexistente_retorna_erro_amigavel(isolated_resultado_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_resultado_db
    message = build_result_conference_message(contest_number=9999, client_id=None, db_path=db_path)
    assert "⚠️ Concurso 9999 não encontrado." in message
    assert "Sincronizamos com a Caixa" in message


def test_state_reset_apos_conferencia(isolated_resultado_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_resultado_db
    psid = "psid-reset-resultado"
    _request_json("POST", "/messenger/webhook", _payload(psid, "resultado", "mid-reset-1"))
    _request_json("POST", "/messenger/webhook", _payload(psid, "3709", "mid-reset-2"))
    with get_session(db_path) as session:
        row = session.get(MessengerConversationState, psid)
        assert row is not None
        assert row.state == "initial"


def test_lei_001_query_sempre_no_postgres(isolated_resultado_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_resultado_db
    repository = ClientRepository(db_path)
    client = repository.activate_messenger_client(
        psid="psid-lei001",
        plan="basico",
        valor_pago=15.99,
        name="Lei001",
    )
    repository.log_client_generation(
        client_id=int(client["id"]),
        phone=str(client["phone"]),
        formato=15,
        quantidade=1,
        concurso_alvo=3709,
        channel="messenger",
        jogos=[{"cartao_validado_lei15a": OFFICIAL_NUMBERS}],
    )

    from lotoia.database.contest_repository import ContestRepository

    original = ContestRepository.get_official_history_contest

    def _tracked(self: ContestRepository, contest_number: int) -> dict[str, object] | None:
        tracked_calls.append(int(contest_number))
        return original(self, contest_number)

    tracked_calls: list[int] = []
    with patch.object(ContestRepository, "get_official_history_contest", _tracked):
        message = build_result_conference_message(contest_number=3709, client_id=int(client["id"]), db_path=db_path)

    assert tracked_calls == [3709]
    assert "Concurso 3709" in message
    assert "✅ 15 pontos" in message
    with get_session(db_path) as session:
        rows = session.execute(
            text(
                """
                SELECT id
                FROM lotoia_client_generations
                WHERE client_id = :client_id AND concurso_alvo = :concurso
                """
            ),
            {"client_id": int(client["id"]), "concurso": 3709},
        ).all()
        assert len(rows) == 1


def test_resultado_prompt_inclui_ultimo_concurso_gerado(isolated_resultado_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_resultado_db
    repository = ClientRepository(db_path)
    client = repository.activate_client(phone="5566992358330", plan="pro", valor_pago=49.99, name="Kleyson")
    repository.log_client_generation(
        client_id=int(client["id"]),
        phone=str(client["phone"]),
        formato=15,
        quantidade=2,
        concurso_alvo=3710,
        jogos=[{"cartao_validado_lei15a": list(range(1, 16))}],
    )
    prompt = ResultConferenceService(db_path).get_prompt_for_phone(str(client["phone"]))
    assert "3710" in prompt
    assert "último concurso com jogos gerados" in prompt


def test_conferencia_sem_jogos_indica_ultimo_concurso_gerado(isolated_resultado_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_resultado_db
    repository = ClientRepository(db_path)
    client = repository.activate_client(phone="5566992358331", plan="pro", valor_pago=49.99, name="Cliente")
    repository.log_client_generation(
        client_id=int(client["id"]),
        phone=str(client["phone"]),
        formato=15,
        quantidade=1,
        concurso_alvo=3710,
        jogos=[{"cartao_validado_lei15a": list(range(1, 16))}],
    )
    message = build_result_conference_message(
        contest_number=3709,
        client_id=int(client["id"]),
        db_path=db_path,
        last_generation_contest=3710,
    )
    assert "Você não gerou jogos para esse concurso." in message
    assert "3710" in message
    assert "Digite 3710" in message


def test_resultado_prompt_constant() -> None:
    assert "Conferência de resultado LotoIA" in RESULTADO_PROMPT
    assert "3709" in RESULTADO_PROMPT


def test_messenger_fluxo_completo_premiado(isolated_resultado_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_resultado_db
    psid = "psid-fluxo-premiado"
    repository = ClientRepository(db_path)
    client = repository.activate_messenger_client(
        psid=psid,
        plan="basico",
        valor_pago=15.99,
        name="Fluxo",
    )
    repository.log_client_generation(
        client_id=int(client["id"]),
        phone=str(client["phone"]),
        formato=15,
        quantidade=1,
        concurso_alvo=3709,
        channel="messenger",
        jogos=[{"cartao_validado_lei15a": OFFICIAL_NUMBERS}],
    )
    _request_json("POST", "/messenger/webhook", _payload(psid, "resultado", "mid-fluxo-1"))
    status, result = _request_json("POST", "/messenger/webhook", _payload(psid, "3709", "mid-fluxo-2"))
    assert status == 200
    assert result.get("status") == "ok"
    assert "Parabéns" in str(result.get("message") or "")


def test_whatsapp_resultado_fluxo(isolated_resultado_db: tuple[Path, _FakeMessengerClient]) -> None:
    from lotoia.clients.whatsapp_service import process_whatsapp_webhook
    from lotoia.database.database import WhatsAppConversationState

    db_path, _ = isolated_resultado_db
    phone = "5566992358330"
    repository = ClientRepository(db_path)
    client = repository.activate_client(phone=phone, plan="basico", valor_pago=15.99, name="Whats")
    repository.log_client_generation(
        client_id=int(client["id"]),
        phone=phone,
        formato=15,
        quantidade=1,
        concurso_alvo=3709,
        jogos=[{"cartao_validado_lei15a": OFFICIAL_NUMBERS[:11] + [2, 4, 6, 8]}],
    )
    prompt = process_whatsapp_webhook(
        {"data": {"key": {"remoteJid": f"{phone}@s.whatsapp.net", "id": "wa-1"}, "message": {"conversation": "resultado"}}},
        db_path=db_path,
    )
    assert prompt.get("status") == "prompt"
    assert RESULTADO_PROMPT.splitlines()[0] in str(prompt.get("message") or "")
    with get_session(db_path) as session:
        row = session.get(WhatsAppConversationState, phone)
        assert row is not None
        assert row.state == "awaiting_concurso"
    result = process_whatsapp_webhook(
        {"data": {"key": {"remoteJid": f"{phone}@s.whatsapp.net", "id": "wa-2"}, "message": {"conversation": "3709"}}},
        db_path=db_path,
    )
    assert result.get("status") == "ok"
    assert "✅ 11 pontos" in str(result.get("message") or "")
    with get_session(db_path) as session:
        row = session.get(WhatsAppConversationState, phone)
        assert row is not None
        assert row.state == "initial"


def test_whatsapp_resultado_lid_usa_telefone_cadastrado(isolated_resultado_db: tuple[Path, _FakeMessengerClient]) -> None:
    from lotoia.clients.whatsapp_service import process_whatsapp_webhook

    db_path, _ = isolated_resultado_db
    phone = "5566992358330"
    repository = ClientRepository(db_path)
    repository.activate_client(phone=phone, plan="pro", valor_pago=49.99, name="Kleyson")
    result = process_whatsapp_webhook(
        {
            "data": {
                "key": {
                    "remoteJid": "69385314111689@lid",
                    "remoteJidAlt": "66992358330@s.whatsapp.net",
                    "id": "wa-lid-resultado",
                },
                "message": {"conversation": "3709"},
            }
        },
        db_path=db_path,
    )
    assert result.get("status") == "ok"
    assert result.get("phone") == phone
    assert "Concurso 3709" in str(result.get("message") or "")


def test_whatsapp_resultado_numero_concurso_sem_estado_em_memoria(isolated_resultado_db: tuple[Path, _FakeMessengerClient]) -> None:
    from lotoia.clients.whatsapp_service import process_whatsapp_webhook

    db_path, _ = isolated_resultado_db
    phone = "5566992358331"
    result = process_whatsapp_webhook(
        {"data": {"key": {"remoteJid": f"{phone}@s.whatsapp.net", "id": "wa-direct"}, "message": {"conversation": "3709"}}},
        db_path=db_path,
    )
    assert result.get("status") == "ok"
    assert "Concurso 3709" in str(result.get("message") or "")


def test_whatsapp_resultado_repetido_mantem_prompt_sem_erro(isolated_resultado_db: tuple[Path, _FakeMessengerClient]) -> None:
    from lotoia.clients.whatsapp_service import process_whatsapp_webhook

    db_path, _ = isolated_resultado_db
    phone = "5566992358332"
    process_whatsapp_webhook(
        {"data": {"key": {"remoteJid": f"{phone}@s.whatsapp.net", "id": "wa-r1"}, "message": {"conversation": "resultado"}}},
        db_path=db_path,
    )
    result = process_whatsapp_webhook(
        {"data": {"key": {"remoteJid": f"{phone}@s.whatsapp.net", "id": "wa-r2"}, "message": {"conversation": "Resultado"}}},
        db_path=db_path,
    )
    assert result.get("status") == "prompt"
    assert "Não entendi" not in str(result.get("message") or "")
    assert "Qual o número do concurso?" in str(result.get("message") or "")


def test_whatsapp_extract_nested_ephemeral_message_text() -> None:
    from lotoia.clients.whatsapp_service import extract_evolution_payload

    payload = {
        "data": {
            "key": {"remoteJid": "5566992358330@s.whatsapp.net", "id": "wa-ephemeral"},
            "message": {
                "ephemeralMessage": {
                    "message": {
                        "extendedTextMessage": {"text": "3704"},
                    }
                }
            },
        }
    }
    extracted = extract_evolution_payload(payload)
    assert extracted["text"] == "3704"


def test_concurso_alvo_index_exists(isolated_resultado_db: tuple[Path, _FakeMessengerClient]) -> None:
    db_path, _ = isolated_resultado_db
    indexes = inspect(get_engine(db_path)).get_indexes("lotoia_client_generations")
    index_names = {index["name"] for index in indexes}
    assert "ix_lotoia_client_generations_concurso_alvo" in index_names
    assert "idx_generations_concurso" in index_names
