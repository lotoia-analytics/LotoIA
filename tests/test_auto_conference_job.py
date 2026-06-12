from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import text

from lotoia.clients.auto_conference_job import run_auto_conference
from lotoia.clients.repository import ClientRepository
from lotoia.database.contest_repository import ContestRepository
from lotoia.database.database import LotoiaClient, create_database, get_session


def _seed_official_contest(db_path: Path, contest_number: int, numbers: list[int]) -> None:
    repository = ContestRepository(db_path)
    repository.create_table()
    repository.save_contest(
        {
            "concurso": contest_number,
            "data": "11/06/2026",
            "dezenas": [f"{number:02d}" for number in numbers],
            "metadata_json": {"numero": contest_number},
        }
    )
    assert repository.confirm_sync_persistence(contest_number)["ok"] is True


def test_run_auto_conference_persists_results_and_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "lotoia.db"
    create_database(db_path)
    official_numbers = list(range(1, 16))
    contest_number = 3708
    _seed_official_contest(db_path, contest_number, official_numbers)

    client_repo = ClientRepository(db_path)
    client = client_repo.activate_client(
        phone="5566992358330",
        plan="pro",
        valor_pago=49.99,
        name="Kleyson",
        duration_days=30,
    )
    client_repo.log_client_generation(
        client_id=int(client["id"]),
        phone=str(client["phone"]),
        formato=15,
        quantidade=2,
        concurso_alvo=contest_number,
        jogos=[
            {"cartao_validado_lei15a": official_numbers},
            {"cartao_validado_lei15a": list(range(1, 12))},
        ],
    )

    first = run_auto_conference(db_path=db_path)
    second = run_auto_conference(db_path=db_path)

    assert first["status"] == "completed"
    assert first["contest_number"] == contest_number
    assert first["results_persisted"] == 2
    assert second["results_persisted"] == 0
    assert second["skipped_clients"] == 1

    with get_session(db_path) as session:
        rows = session.execute(
            text(
                """
                SELECT game_index, hits, premio_status, notified
                FROM lotoia_client_conference_results
                WHERE contest_number = :contest_number
                ORDER BY game_index
                """
            ),
            {"contest_number": contest_number},
        ).all()

    assert len(rows) == 2
    assert int(rows[0][0]) == 1
    assert int(rows[0][1]) == 15
    assert str(rows[0][2]) == "premiado"
    assert bool(rows[0][3]) is False
    assert int(rows[1][0]) == 2
    assert int(rows[1][1]) == 11
    assert str(rows[1][2]) == "premiado"


def test_run_auto_conference_skips_without_sync_confirmation(tmp_path: Path) -> None:
    db_path = tmp_path / "lotoia.db"
    create_database(db_path)
    repository = ContestRepository(db_path)
    repository.create_table()
    repository.save_contest(
        {
            "concurso": 3708,
            "data": "11/06/2026",
            "dezenas": [f"{n:02d}" for n in range(1, 16)],
            "metadata_json": {"numero": 3708},
        }
    )
    assert repository.confirm_sync_persistence(3708)["ok"] is True

    from lotoia.database.database import ImportedContest

    with get_session(db_path) as session:
        session.query(ImportedContest).filter(ImportedContest.contest_number == 3708).delete()
        session.commit()

    payload = run_auto_conference(db_path=db_path)
    assert payload["status"] == "skipped"
    assert payload["reason"] == "sync_not_confirmed"


def test_run_auto_conference_skips_expired_clients(tmp_path: Path) -> None:
    db_path = tmp_path / "lotoia.db"
    create_database(db_path)
    contest_number = 3708
    _seed_official_contest(db_path, contest_number, list(range(1, 16)))

    client_repo = ClientRepository(db_path)
    client = client_repo.activate_client(
        phone="5511999999999",
        plan="basico",
        valor_pago=15.99,
        name="Expirado",
        duration_days=1,
    )
    with get_session(db_path) as session:
        row = session.get(LotoiaClient, int(client["id"]))
        assert row is not None
        row.data_expiracao = datetime.now(UTC) - timedelta(days=2)
        row.status = "ativo"
        session.commit()

    client_repo.log_client_generation(
        client_id=int(client["id"]),
        phone=str(client["phone"]),
        formato=15,
        quantidade=1,
        concurso_alvo=contest_number,
        jogos=[{"cartao_validado_lei15a": list(range(1, 16))}],
    )

    payload = run_auto_conference(db_path=db_path)
    assert payload["status"] == "completed"
    assert payload["clients_processed"] == 0

    with get_session(db_path) as session:
        count = session.execute(text("SELECT COUNT(*) FROM lotoia_client_conference_results")).scalar()
    assert int(count or 0) == 0
