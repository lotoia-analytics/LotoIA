import argparse
import csv
import json
from pathlib import Path

DEFAULT_INPUT_PATH = Path("data/raw/historico_lotofacil.csv")
DEFAULT_OUTPUT_PATH = Path("data/stats/frequency_stats.json")
DRAW_NUMBER_COLUMNS = [f"d{number}" for number in range(1, 16)]
TOTAL_CONTESTS = 3685
NUMBERS_PER_CONTEST = 15
TOTAL_NUMBERS = 25
EXPECTED_FREQUENCY = (TOTAL_CONTESTS * NUMBERS_PER_CONTEST) / TOTAL_NUMBERS


def _validate_number(value: str) -> int:
    number = int(value)
    if number < 1 or number > 25:
        raise ValueError("As dezenas devem estar entre 1 e 25.")
    return number


def _load_frequency_counts(source_path: Path) -> dict[int, int]:
    counts = {number: 0 for number in range(1, TOTAL_NUMBERS + 1)}

    with source_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames:
            return {}

        missing_columns = [column for column in DRAW_NUMBER_COLUMNS if column not in reader.fieldnames]
        if missing_columns:
            missing = ", ".join(missing_columns)
            raise ValueError(f"CSV invalido. Colunas obrigatorias ausentes: {missing}")

        for row_index, row in enumerate(reader, start=2):
            row_numbers = [_validate_number(row[column]) for column in DRAW_NUMBER_COLUMNS]
            if len(set(row_numbers)) != len(row_numbers):
                raise ValueError(f"CSV invalido na linha {row_index}: dezenas repetidas.")

            for number in row_numbers:
                counts[number] += 1

    return counts


def _build_stats_from_counts(counts: dict[int, int]) -> dict[str, dict[str, float | int]]:
    return {
        str(number): {
            "count": count,
            "delta": int(count - EXPECTED_FREQUENCY),
            "relative_strength": round(count / EXPECTED_FREQUENCY, 3),
        }
        for number, count in sorted(counts.items())
    }


def build_frequency_stats(
    source_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> dict[str, dict[str, float | int]]:
    if not source_path.exists():
        raise FileNotFoundError(f"Arquivo historico nao encontrado: {source_path}")

    counts = _load_frequency_counts(source_path)
    if not counts:
        raise ValueError("Nenhuma frequencia valida encontrada no arquivo de origem.")

    stats = _build_stats_from_counts(counts)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera estatisticas de frequencia das dezenas.")
    parser.add_argument(
        "source",
        nargs="?",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"Arquivo de entrada. Padrao: {DEFAULT_INPUT_PATH}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Arquivo JSON de saida. Padrao: {DEFAULT_OUTPUT_PATH}",
    )
    args = parser.parse_args()

    build_frequency_stats(args.source, args.output)


if __name__ == "__main__":
    main()
