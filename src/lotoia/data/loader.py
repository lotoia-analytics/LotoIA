from pathlib import Path

import pandas as pd
from pydantic import ValidationError

from lotoia.models.draw import Draw

DRAW_NUMBER_COLUMNS = [f"d{number}" for number in range(1, 16)]
REQUIRED_COLUMNS = ["concurso", "data", *DRAW_NUMBER_COLUMNS]
BASE_DIR = Path(__file__).resolve().parents[3]
DEFAULT_HISTORY_PATH = BASE_DIR / "data" / "raw" / "historico_lotofacil.csv"


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
