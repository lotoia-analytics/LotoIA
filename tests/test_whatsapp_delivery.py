from __future__ import annotations

from pathlib import Path

import pytest

from lotoia.clients.evolution_client import GENERATION_ERROR_MESSAGE
from lotoia.clients.whatsapp_service import deliver_whatsapp_webhook
from lotoia.database.database import create_database


class _RecordingEvolutionClient:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self.last_error_message = ""

    @property
    def is_configured(self) -> bool:
        return True

    def send_text(self, phone: str, message: str) -> bool:
        self.messages.append(message)
        return True

    def send_games(self, phone: str, games: list[dict[str, object]], formato: int) -> bool:
        self.messages.append(f"games:{formato}:{len(games)}")
        return True


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "lotoia.db"
    create_database(path)
    return path


def test_deliver_whatsapp_webhook_sends_generation_error(db_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    evolution = _RecordingEvolutionClient()

    def _boom(*args, **kwargs):
        raise RuntimeError("generation failed")

    monkeypatch.setattr("lotoia.clients.whatsapp_service._execute_valid_generation", _boom)
    from lotoia.clients.repository import ClientRepository

    ClientRepository(db_path).activate_client(
        phone="5511999999999",
        plan="elite",
        valor_pago=69.99,
        name="Ana",
    )
    payload = {
        "data": {
            "key": {"remoteJid": "5511999999999@s.whatsapp.net", "id": "gen-error"},
            "message": {"conversation": "2 jogos de 15D"},
        }
    }

    result = deliver_whatsapp_webhook(payload, db_path=db_path, evolution_client=evolution)

    assert result["status"] == "error"
    assert result["error_code"] == "GENERATION_ERROR"
    assert result.get("delivered") is True
    assert evolution.messages == [GENERATION_ERROR_MESSAGE]
