import argparse
import csv
import json
import re
from pathlib import Path

DEFAULT_INPUT_PATH = Path("data/raw/duos_frequentes.csv")
DEFAULT_OUTPUT_PATH = Path("data/stats/duos_stats.json")


def _normalize_duo(numbers: list[int]) -> str:
    if len(numbers) != 2:
        raise ValueError("Um duo deve conter exatamente 2 dezenas.")
    if any(number < 1 or number > 25 for number in numbers):
        raise ValueError("As dezenas do duo devem estar entre 1 e 25.")
    if len(set(numbers)) != 2:
        raise ValueError("As dezenas do duo devem ser unicas.")
    return "-".join(str(number) for number in sorted(numbers))


def _extract_numbers(text: str) -> list[int]:
    return [int(value) for value in re.findall(r"\d+", text)]


def _parse_frequency(text: str) -> int:
    values = _extract_numbers(text)
    if not values:
        raise ValueError("Frequencia invalida.")

    frequency = values[-1]
    if frequency <= 0:
        raise ValueError("A frequencia deve ser maior que zero.")

    return frequency


def _parse_duos_csv(source_path: Path) -> list[tuple[str, int]]:
    records: list[tuple[str, int]] = []

    with source_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames:
            return records

        normalized_fields = {
            field.lower().strip(): field for field in reader.fieldnames if field is not None
        }
        duo_field = normalized_fields.get("duo") or normalized_fields.get("dupla")
        frequency_field = (
            normalized_fields.get("frequencia")
            or normalized_fields.get("frequÃªncia")
            or normalized_fields.get("frequency")
        )

        if not duo_field or not frequency_field:
            return records

        for row in reader:
            duo = _normalize_duo(_extract_numbers(row[duo_field]))
            frequency = _parse_frequency(row[frequency_field])
            records.append((duo, frequency))

    return records


def _parse_duos_text(source_path: Path) -> list[tuple[str, int]]:
    records: list[tuple[str, int]] = []

    for line in source_path.read_text(encoding="utf-8-sig").splitlines():
        values = _extract_numbers(line)
        if len(values) < 3:
            continue
        duo = _normalize_duo(values[:2])
        frequency = values[-1]
        if frequency <= 0:
            raise ValueError("A frequencia deve ser maior que zero.")
        records.append((duo, frequency))

    return records


def build_duos_stats(
    source_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> dict[str, dict[str, int]]:
    if not source_path.exists():
        raise FileNotFoundError(f"Arquivo de duos frequentes nao encontrado: {source_path}")

    records = _parse_duos_csv(source_path) or _parse_duos_text(source_path)
    if not records:
        raise ValueError("Nenhum duo valido encontrado no arquivo de origem.")

    ordered_records = sorted(records, key=lambda item: (-item[1], item[0]))
    stats = {
        duo: {"frequency": frequency, "rank": rank}
        for rank, (duo, frequency) in enumerate(ordered_records, start=1)
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera estatisticas de duos frequentes.")
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

    build_duos_stats(args.source, args.output)


if __name__ == "__main__":
    main()
