from __future__ import annotations

import csv
import re
from pathlib import Path

PDF_PATH = Path("RELATORIO LOTOFACIL.pdf")
OUTPUT_CSV_PATH = Path("data/raw/historico_lotofacil.csv")
CSV_HEADER = ["concurso", "data", *[f"d{number}" for number in range(1, 16)]]
DATE_PATTERN = r"(?:\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})"
DRAW_ROW_PATTERN = re.compile(
    rf"(?P<contest>\d+)\s+(?P<date>{DATE_PATTERN})(?P<body>.*?)(?=\s+\d+\s+{DATE_PATTERN}|\Z)",
    re.DOTALL,
)


def extract_text_from_pdf(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"PDF nao encontrado: {path}")

    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "Biblioteca pypdf nao encontrada. Instale com: pip install pypdf"
        ) from exc

    reader = PdfReader(path)
    pages_text = [page.extract_text(extraction_mode="layout") or "" for page in reader.pages]
    text = "\n".join(pages_text)
    if not text.strip():
        raise ValueError("Nao foi possivel extrair texto do PDF.")
    return text


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_draws(text: str) -> list[dict[str, object]]:
    draws: list[dict[str, object]] = []
    normalized_text = normalize_text(text)

    for match in DRAW_ROW_PATTERN.finditer(normalized_text):
        contest = int(match.group("contest"))
        draw_date = match.group("date")
        numbers = parse_draw_numbers(match.group("body"))

        validate_draw(contest, numbers)
        draws.append({"concurso": contest, "data": draw_date, "dezenas": numbers})

    if not draws:
        raise ValueError(
            "Nenhum concurso foi identificado no PDF. "
            "Verifique se o arquivo contem texto extraivel e uma tabela com concurso, data e dezenas."
        )

    return sorted(draws, key=lambda draw: int(draw["concurso"]))


def parse_draw_numbers(text: str) -> list[int]:
    token_numbers = [int(value) for value in re.findall(r"\b\d{1,2}\b", text)[:15]]
    if len(token_numbers) == 15 and is_valid_number_set(token_numbers):
        return token_numbers

    digits = re.sub(r"\D", "", text)
    parsed = parse_ordered_numbers(digits, start=0, previous=0, numbers=[])
    if parsed is None:
        return []
    return parsed


def is_valid_number_set(numbers: list[int]) -> bool:
    return (
        len(numbers) == 15
        and len(set(numbers)) == 15
        and all(1 <= number <= 25 for number in numbers)
    )


def parse_ordered_numbers(
    digits: str,
    start: int,
    previous: int,
    numbers: list[int],
) -> list[int] | None:
    if len(numbers) == 15:
        return numbers

    for size in (1, 2):
        end = start + size
        if end > len(digits):
            continue

        number = int(digits[start:end])
        if number <= previous or number < 1 or number > 25:
            continue

        parsed = parse_ordered_numbers(digits, end, number, [*numbers, number])
        if parsed is not None:
            return parsed

    return None


def validate_draw(contest: int, numbers: list[int]) -> None:
    if len(numbers) != 15:
        raise ValueError(f"Concurso {contest} invalido: esperado 15 dezenas, encontrado {len(numbers)}.")
    if any(number < 1 or number > 25 for number in numbers):
        raise ValueError(f"Concurso {contest} invalido: dezenas devem estar entre 1 e 25.")
    if len(set(numbers)) != 15:
        raise ValueError(f"Concurso {contest} invalido: dezenas repetidas no mesmo concurso.")


def write_csv(draws: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(CSV_HEADER)
        for draw in draws:
            writer.writerow([draw["concurso"], draw["data"], *draw["dezenas"]])


def main() -> None:
    text = extract_text_from_pdf(PDF_PATH)
    draws = extract_draws(text)
    write_csv(draws, OUTPUT_CSV_PATH)
    print(f"Concursos convertidos: {len(draws)}")
    print(f"CSV gerado em: {OUTPUT_CSV_PATH}")


if __name__ == "__main__":
    main()
