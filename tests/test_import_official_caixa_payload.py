from __future__ import annotations

import json
from pathlib import Path

import pytest

from lotoia.database.contest_repository import ContestRepository


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "lotoia.db"
    repository = ContestRepository(path)
    repository.create_table()
    repository.save_contest(
        {
            "concurso": 3706,
            "data": "09/06/2026",
            "dezenas": ["01", "04", "06", "08", "09", "10", "12", "14", "15", "16", "18", "21", "22", "24", "25"],
            "metadata_json": "{}",
        }
    )
    return path


def test_import_official_caixa_payload_script(db_path: Path) -> None:
    import scripts.import_official_caixa_payload as module

    payload_path = Path("data/external/concurso_3708_caixa.json")
    exit_code = module.main(["--db-path", str(db_path), "--file", str(payload_path)])
    assert exit_code == 0

    repository = ContestRepository(db_path)
    assert repository.get_official_history_max_contest() == 3708
    row = repository.get_official_history_contest(3708)
    assert row is not None
    assert row["data"] == "11/06/2026"
    assert repository.confirm_sync_persistence(3708)["ok"] is True
