from pathlib import Path

import pytest

from lotoia.data.loader import load_draws_csv


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
