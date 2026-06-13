from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from lotoia.clients.official_result_sync import ensure_official_contest_available
from lotoia.clients.result_conference_service import (
    ResultConferenceService,
    build_result_conference_message,
)
from lotoia.database.contest_repository import ContestRepository
from lotoia.database.database import LotofacilOfficialHistory, create_database, get_session
from lotoia.ingestion.result_sync_service import ResultSyncSummary


OFFICIAL_NUMBERS = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 20, 21, 22, 23, 24]


def _summary(*, contests: list[int], ok: bool = True) -> ResultSyncSummary:
    return ResultSyncSummary(
        latest_contest=contests[-1] if contests else None,
        synced_contests=contests,
        synced_contests_count=len(contests),
        persisted_contests=len(contests),
        provider_payload_count=len(contests),
        contest_ids=contests,
        db_backend="sqlite",
        engine_url="sqlite://",
        commit_state="ok" if ok else "failed",
        source="test",
    )


def test_build_message_indica_sync_quando_concurso_ausente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "message.db"
    create_database(db_path)
    monkeypatch.setattr(
        "lotoia.clients.result_conference_service.ensure_official_contest_available",
        lambda db_path, contest_number, sync_latest_first=True: False,
    )
    message = build_result_conference_message(contest_number=3709, client_id=None, db_path=db_path)
    assert "3709 não encontrado" in message
    assert "Sincronizamos com a Caixa" in message


def test_prompt_inclui_ultimo_resultado_oficial(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "prompt.db"
    create_database(db_path)
    with get_session(db_path) as session:
        session.merge(
            LotofacilOfficialHistory(
                contest_number=3708,
                draw_date="11/06/2026",
                numbers=",".join(str(n) for n in OFFICIAL_NUMBERS),
                numbers_signature="test",
            )
        )
        session.commit()
    monkeypatch.setattr(
        "lotoia.clients.result_conference_service.sync_latest_official_results",
        lambda db_path: [],
    )
    prompt = ResultConferenceService(db_path).get_prompt_for_client_id(None)
    assert "3708" in prompt
    assert "Último resultado oficial disponível" in prompt


def test_ensure_official_contest_available_after_sync_contests(tmp_path: Path) -> None:
    db_path = tmp_path / "ensure.db"
    create_database(db_path)
    repository = ContestRepository(db_path)

    def _fake_sync_contests(contest_numbers: list[int]) -> ResultSyncSummary:
        repository.create_table()
        with repository.transaction() as tx:
            repository.save_contest(
                {
                    "concurso": 3709,
                    "data": "12/06/2026",
                    "dezenas": [f"{n:02d}" for n in OFFICIAL_NUMBERS],
                    "metadata_json": {},
                },
                commit=False,
                session=tx,
            )
        return _summary(contests=[3709])

    with patch("lotoia.clients.official_result_sync.ResultSyncService") as service_cls:
        service_cls.return_value.sync_latest.return_value = _summary(contests=[])
        service_cls.return_value.sync_contests.side_effect = _fake_sync_contests
        found = ensure_official_contest_available(db_path, 3709)
    assert found is True
    assert repository.get_official_history_contest(3709) is not None


def test_ensure_official_contest_available_falls_back_to_csv(tmp_path: Path) -> None:
    db_path = tmp_path / "ensure_csv.db"
    create_database(db_path)
    repository = ContestRepository(db_path)
    repository.create_table()
    repository.save_contest(
        {
            "concurso": 3706,
            "data": "09/06/2026",
            "dezenas": [f"{n:02d}" for n in [1, 4, 6, 8, 9, 10, 12, 14, 15, 16, 18, 21, 22, 24, 25]],
            "metadata_json": {},
        }
    )

    failed_summary = _summary(contests=[], ok=False)

    with patch("lotoia.clients.official_result_sync.ResultSyncService") as service_cls:
        service_cls.return_value.sync_latest.return_value = failed_summary
        service_cls.return_value.sync_contests.return_value = failed_summary
        found = ensure_official_contest_available(db_path, 3709)

    assert found is True
    assert repository.get_contest(3709) is not None
    numbers = [int(value) for value in repository.get_contest(3709)["dezenas"]]
    assert numbers == [1, 4, 6, 7, 9, 10, 11, 14, 15, 18, 19, 20, 23, 24, 25]
