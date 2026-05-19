import argparse
import csv
import json
from pathlib import Path

DEFAULT_INPUT_PATH = Path("data/raw/atrasos_dezenas.csv")
DEFAULT_OUTPUT_PATH = Path("data/stats/delay_stats.json")


def _validate_dezena(value: str) -> str:
    dezena = int(value)
    if dezena < 1 or dezena > 25:
        raise ValueError("A dezena deve estar entre 1 e 25.")
    return str(dezena)


def _validate_delay(value: str) -> int:
    delay = int(value)
    if delay < 0:
        raise ValueError("O atraso deve ser maior ou igual a zero.")
    return delay


def _parse_delay_csv(source_path: Path) -> list[tuple[str, int]]:
    records: list[tuple[str, int]] = []

    with source_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames:
            return records

        normalized_fields = {
            field.lower().strip(): field for field in reader.fieldnames if field is not None
        }
        dezena_field = normalized_fields.get("dezena") or normalized_fields.get("number")
        delay_field = (
            normalized_fields.get("atraso")
            or normalized_fields.get("delay")
            or normalized_fields.get("dias")
        )

        if not dezena_field or not delay_field:
            return records

        for row in reader:
            dezena = _validate_dezena(row[dezena_field])
            delay = _validate_delay(row[delay_field])
            records.append((dezena, delay))

    return records


def build_delay_stats(
    source_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> dict[str, dict[str, int]]:
    if not source_path.exists():
        raise FileNotFoundError(f"Arquivo de atrasos nao encontrado: {source_path}")

    records = _parse_delay_csv(source_path)
    if not records:
        raise ValueError("Nenhum atraso valido encontrado no arquivo de origem.")

    ordered_records = sorted(records, key=lambda item: (-item[1], int(item[0])))
    stats = {dezena: {"delay": delay} for dezena, delay in ordered_records}

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera estatisticas de atrasos das dezenas.")
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

    build_delay_stats(args.source, args.output)


if __name__ == "__main__":
    main()
