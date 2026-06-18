from pathlib import Path

import pytest

from lotoia.data.loader import load_draws, load_draws_csv, load_draws_from_database


CSV_HEADER = "concurso,data,d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14,d15\n"


def write_csv(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_load_draws_csv_valid_file(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path / "historico_lotofacil.csv",
        CSV_HEADER + "1,2026-01-01,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15\n",
    )

    draws = load_draws_csv(csv_path)

    assert len(draws) == 1
    assert draws[0].contest == 1
    assert draws[0].date == "2026-01-01"
    assert draws[0].numbers == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]


def test_load_draws_csv_missing_column(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path / "historico_lotofacil.csv",
        "concurso,data,d1,d2,d3\n1,2026-01-01,1,2,3\n",
    )

    with pytest.raises(ValueError, match="Colunas obrigatorias ausentes"):
        load_draws_csv(csv_path)


def test_load_draws_csv_repeated_number(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path / "historico_lotofacil.csv",
        CSV_HEADER + "1,2026-01-01,1,1,3,4,5,6,7,8,9,10,11,12,13,14,15\n",
    )

    with pytest.raises(ValueError, match="15 dezenas unicas"):
        load_draws_csv(csv_path)


def test_load_draws_csv_number_out_of_range(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path / "historico_lotofacil.csv",
        CSV_HEADER + "1,2026-01-01,1,2,3,4,5,6,7,8,9,10,11,12,13,14,26\n",
    )

    with pytest.raises(ValueError, match="entre 1 e 25"):
        load_draws_csv(csv_path)


def test_load_draws_from_database_imported_contests(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from lotoia.database.database import ImportedContest, create_database, get_session

    monkeypatch.delenv("DATABASE_URL", raising=False)
    db_path = tmp_path / "draws.db"
    create_database(db_path)
    with get_session(db_path) as session:
        session.add(
            ImportedContest(
                contest_number=3700,
                data="2026-06-01",
                dezenas="1,2,3,4,5,6,7,8,9,10,11,12,13,14,15",
            )
        )
        session.commit()

    draws = load_draws_from_database(db_path)

    assert len(draws) == 1
    assert draws[0].contest == 3700
    assert draws[0].numbers == list(range(1, 16))


def test_load_draws_prefers_database_on_cloud(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from lotoia.database.database import ImportedContest, create_database, get_session

    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    db_path = tmp_path / "cloud.db"
    create_database(db_path)
    with get_session(db_path) as session:
        session.add(
            ImportedContest(
                contest_number=3701,
                data="2026-06-02",
                dezenas="2,3,4,5,6,7,8,9,10,11,12,13,14,15,16",
            )
        )
        session.commit()

    monkeypatch.setattr("lotoia.data.loader.load_draws_from_database", lambda db_path=None: load_draws_from_database(db_path))
    monkeypatch.setattr("lotoia.database.database.DEFAULT_DATABASE_PATH", db_path)

    draws = load_draws()

    assert len(draws) == 1
    assert draws[0].contest == 3701


def test_load_draws_cloud_empty_database_fails_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from lotoia.database.database import create_database

    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    db_path = tmp_path / "empty.db"
    create_database(db_path)
    monkeypatch.setattr("lotoia.database.database.DEFAULT_DATABASE_PATH", db_path)

    with pytest.raises(RuntimeError, match="imported_contests"):
        load_draws()
