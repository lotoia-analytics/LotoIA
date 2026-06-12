from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text

from lotoia.clients.premio_notifier import build_winner_message, notify_winners
from lotoia.clients.repository import ClientRepository
from lotoia.database.database import LotoiaClientConferenceResult, create_database, get_session


class _FakeEvolutionClient:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def send_text(self, phone: str, message: str) -> bool:
        self.messages.append((phone, message))
        return True


def test_build_winner_message_format() -> None:
    assert build_winner_message(contest_number=3708, game_index=1, hits=11) == (
        "Concurso 3708 — Jogo 01: 11 pontos ✅"
    )


def test_notify_winners_sends_and_marks_notified(tmp_path: Path) -> None:
    db_path = tmp_path / "lotoia.db"
    create_database(db_path)
    fake_client = _FakeEvolutionClient()
    client = ClientRepository(db_path).activate_client(
        phone="5566992358330",
        plan="pro",
        valor_pago=49.99,
        name="Kleyson",
    )

    with get_session(db_path) as session:
        session.add(
            LotoiaClientConferenceResult(
                client_id=int(client["id"]),
                phone="5566992358330",
                contest_number=3708,
                game_index=1,
                numbers=list(range(1, 12)),
                hits=11,
                premio_status="premiado",
                notified=False,
                created_at=datetime.now(UTC),
            )
        )
        session.add(
            LotoiaClientConferenceResult(
                client_id=int(client["id"]),
                phone="5566992358330",
                contest_number=3708,
                game_index=2,
                numbers=list(range(1, 13)),
                hits=12,
                premio_status="premiado",
                notified=False,
                created_at=datetime.now(UTC),
            )
        )
        session.commit()

    payload = notify_winners(3708, db_path=db_path, evolution_client=fake_client)

    assert payload["status"] == "completed"
    assert payload["notified_count"] == 2
    assert payload["failed_count"] == 0
    assert fake_client.messages[0] == ("5566992358330", "Concurso 3708 — Jogo 01: 11 pontos ✅")
    assert fake_client.messages[1] == ("5566992358330", "Concurso 3708 — Jogo 02: 12 pontos ✅")

    with get_session(db_path) as session:
        notified_rows = session.execute(
            text("SELECT COUNT(*) FROM lotoia_client_conference_results WHERE notified = 1")
        ).scalar()
    assert int(notified_rows or 0) == 2


def test_notify_winners_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "lotoia.db"
    create_database(db_path)
    fake_client = _FakeEvolutionClient()
    client = ClientRepository(db_path).activate_client(
        phone="5511999999999",
        plan="basico",
        valor_pago=15.99,
        name="Ana",
    )

    with get_session(db_path) as session:
        session.add(
            LotoiaClientConferenceResult(
                client_id=int(client["id"]),
                phone="5511999999999",
                contest_number=3708,
                game_index=1,
                numbers=list(range(1, 12)),
                hits=11,
                premio_status="premiado",
                notified=False,
                created_at=datetime.now(UTC),
            )
        )
        session.commit()

    first = notify_winners(3708, db_path=db_path, evolution_client=fake_client)
    second = notify_winners(3708, db_path=db_path, evolution_client=fake_client)

    assert first["notified_count"] == 1
    assert second["notified_count"] == 0
    assert len(fake_client.messages) == 1
