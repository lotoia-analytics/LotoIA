from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import ValidationError

from lotoia.models.draw import Draw

DRAW_NUMBER_COLUMNS = [f"d{number}" for number in range(1, 16)]
REQUIRED_COLUMNS = ["concurso", "data", *DRAW_NUMBER_COLUMNS]
BASE_DIR = Path(__file__).resolve().parents[3]
DEFAULT_HISTORY_PATH = BASE_DIR / "data" / "raw" / "historico_lotofacil.csv"


def _parse_contest_numbers(raw: str) -> list[int]:
    tokens = [
        token.strip()
        for token in str(raw or "").replace(",", " ").split()
        if token.strip()
    ]
    return [int(str(token).lstrip("0") or "0") for token in tokens]


def load_draws_csv(path: str | Path = DEFAULT_HISTORY_PATH) -> list[Draw]:
    """Load and validate historical LOTOFACIL draws from a CSV file."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {file_path}")

    data_frame = pd.read_csv(file_path)
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in data_frame.columns]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"CSV invalido. Colunas obrigatorias ausentes: {missing}")

    draws: list[Draw] = []
    for row_index, row in data_frame.iterrows():
        contest = row["concurso"]
        draw_date = row["data"]
        numbers = [row[column] for column in DRAW_NUMBER_COLUMNS]
        try:
            draws.append(
                Draw(
                    contest=int(contest),
                    date=str(draw_date),
                    numbers=[int(number) for number in numbers],
                )
            )
        except (TypeError, ValueError, ValidationError) as exc:
            line_number = row_index + 2
            raise ValueError(
                f"CSV invalido na linha {line_number}, concurso {contest}: {exc}"
            ) from exc

    return draws


def load_draws_from_database(db_path: Any = None) -> list[Draw]:
    """Carrega concursos operacionais do PostgreSQL (imported_contests / histórico oficial)."""
    from lotoia.database.database import (
        DEFAULT_DATABASE_PATH,
        ImportedContest,
        LotofacilOfficialHistory,
        get_session,
    )

    effective_path = DEFAULT_DATABASE_PATH if db_path is None else db_path
    draws: list[Draw] = []
    with get_session(effective_path) as session:
        official_rows = (
            session.query(LotofacilOfficialHistory)
            .filter(LotofacilOfficialHistory.is_valid == 1)
            .order_by(LotofacilOfficialHistory.contest_number.asc())
            .all()
        )
        if official_rows:
            for row in official_rows:
                numbers = _parse_contest_numbers(str(getattr(row, "numbers", "") or ""))
                if len(numbers) != 15:
                    continue
                draws.append(
                    Draw(
                        contest=int(row.contest_number),
                        date=str(getattr(row, "draw_date", "") or ""),
                        numbers=numbers,
                    )
                )
            if draws:
                return draws

        imported_rows = (
            session.query(ImportedContest)
            .order_by(ImportedContest.contest_number.asc())
            .all()
        )
        for row in imported_rows:
            numbers = _parse_contest_numbers(str(getattr(row, "dezenas", "") or ""))
            if len(numbers) != 15:
                raise ValueError(
                    f"imported_contests inválido no concurso {row.contest_number}: "
                    f"esperadas 15 dezenas, encontradas {len(numbers)}"
                )
            draws.append(
                Draw(
                    contest=int(row.contest_number),
                    date=str(getattr(row, "data", "") or ""),
                    numbers=numbers,
                )
            )
    return draws


def _should_prefer_database_source() -> bool:
    from lotoia.database.env_resolution import (
        is_postgresql_database_url,
        resolve_institutional_database_url_from_env,
    )
    from lotoia.governance.cloud_runtime_policy import is_cloud_production_runtime

    if is_cloud_production_runtime():
        return True
    database_url, _source = resolve_institutional_database_url_from_env()
    return bool(database_url) and is_postgresql_database_url(database_url)


def load_draws(
    path: str | Path = DEFAULT_HISTORY_PATH,
    *,
    db_path: Any = None,
) -> list[Draw]:
    """Fonte operacional para geração: PostgreSQL (Lei 001) com fallback CSV local."""
    from lotoia.governance.cloud_runtime_policy import is_cloud_production_runtime

    if _should_prefer_database_source():
        try:
            draws = load_draws_from_database(db_path)
        except Exception as exc:
            if is_cloud_production_runtime():
                raise RuntimeError(
                    "Histórico operacional indisponível no PostgreSQL. "
                    "Sincronize imported_contests antes de gerar (Lei No 001)."
                ) from exc
            draws = []
        if draws:
            return draws
        if is_cloud_production_runtime():
            raise RuntimeError(
                "Nenhum concurso em imported_contests / lotofacil_official_history. "
                "Execute sincronização oficial antes de gerar."
            )
    return load_draws_csv(path)
