from __future__ import annotations

from pathlib import Path

from lotoia.database.contest_repository import ContestRepository
from lotoia.models.draw import Draw


def test_import_new_contests_from_csv_imports_only_tail(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "lotoia.db"
    repository = ContestRepository(db_path)
    repository.create_table()
    repository.save_contest(
        {
            "concurso": 3704,
            "data": "06/06/2026",
            "dezenas": [f"{number:02d}" for number in [1, 3, 4, 9, 10, 11, 12, 13, 14, 15, 19, 20, 22, 23, 25]],
            "metadata_json": "{}",
        }
    )

    def _fake_draws() -> list[Draw]:
        return [
            Draw(contest=3704, date="06/06/2026", numbers=[1, 3, 4, 9, 10, 11, 12, 13, 14, 15, 19, 20, 22, 23, 25]),
            Draw(contest=3705, date="08/06/2026", numbers=[1, 3, 4, 6, 8, 10, 14, 15, 16, 18, 20, 21, 22, 24, 25]),
            Draw(contest=3706, date="09/06/2026", numbers=[1, 4, 6, 8, 9, 10, 12, 14, 15, 16, 18, 21, 22, 24, 25]),
        ]

    monkeypatch.setattr("lotoia.database.contest_repository.load_draws_csv", _fake_draws)

    imported = repository.import_new_contests_from_csv()

    assert imported == [3705, 3706]
    assert repository.get_official_history_max_contest() == 3706
    assert repository.get_contest(3706) is not None
