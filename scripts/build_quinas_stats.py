import argparse
import csv
import json
import re
from pathlib import Path

DEFAULT_INPUT_PATH = Path("data/raw/quinas_frequentes.csv")
DEFAULT_OUTPUT_PATH = Path("data/stats/quinas_stats.json")
TOTAL_CONTESTS = 3685
COMBINATIONS_PER_CONTEST = 3003
TOTAL_QUINAS = 53130
EXPECTED_QUINA_COUNT = (TOTAL_CONTESTS * COMBINATIONS_PER_CONTEST) / TOTAL_QUINAS


def _normalize_quina(numbers: list[int]) -> str:
    if len(numbers) != 5:
        raise ValueError("Uma quina deve conter exatamente 5 dezenas.")
    if any(number < 1 or number > 25 for number in numbers):
        raise ValueError("As dezenas da quina devem estar entre 1 e 25.")
    if len(set(numbers)) != 5:
        raise ValueError("As dezenas da quina devem ser unicas.")
    return "-".join(str(number) for number in sorted(numbers))


def _extract_numbers(text: str) -> list[int]:
    return [int(value) for value in re.findall(r"\d+", text)]


def _parse_count(text: str) -> int:
    values = _extract_numbers(text)
    if not values:
        raise ValueError("Contagem invalida.")

    count = values[-1]
    if count <= 0:
        raise ValueError("A contagem deve ser maior que zero.")

    return count


def _parse_quinas_csv(source_path: Path) -> list[tuple[str, int]]:
    records: list[tuple[str, int]] = []

    with source_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames:
            return records

        normalized_fields = {
            field.lower().strip(): field for field in reader.fieldnames if field is not None
        }
        quina_field = normalized_fields.get("quina")
        count_field = (
            normalized_fields.get("count")
            or normalized_fields.get("contagem")
            or normalized_fields.get("frequencia")
            or normalized_fields.get("frequência")
            or normalized_fields.get("frequÃªncia")
            or normalized_fields.get("frequÃƒÂªncia")
            or normalized_fields.get("frequency")
        )

        if not quina_field or not count_field:
            return records

        for row in reader:
            quina = _normalize_quina(_extract_numbers(row[quina_field]))
            count = _parse_count(row[count_field])
            records.append((quina, count))

    return records


def _parse_quinas_text(source_path: Path) -> list[tuple[str, int]]:
    records: list[tuple[str, int]] = []

    for line in source_path.read_text(encoding="utf-8-sig").splitlines():
        values = _extract_numbers(line)
        if len(values) < 6:
            continue
        quina = _normalize_quina(values[:5])
        count = values[-1]
        if count <= 0:
            raise ValueError("A contagem deve ser maior que zero.")
        records.append((quina, count))

    return records


def build_quinas_stats(
    source_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> dict[str, dict[str, float | int]]:
    if not source_path.exists():
        raise FileNotFoundError(f"Arquivo de quinas frequentes nao encontrado: {source_path}")

    records = _parse_quinas_csv(source_path) or _parse_quinas_text(source_path)
    if not records:
        raise ValueError("Nenhuma quina valida encontrada no arquivo de origem.")

    ordered_records = sorted(records, key=lambda item: (-item[1], item[0]))
    stats = {
        quina: {
            "count": count,
            "rank": rank,
            "relative_strength": round(count / EXPECTED_QUINA_COUNT, 3),
        }
        for rank, (quina, count) in enumerate(ordered_records, start=1)
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera estatisticas de quinas frequentes.")
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

    build_quinas_stats(args.source, args.output)


if __name__ == "__main__":
    main()
