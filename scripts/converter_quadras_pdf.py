from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from pathlib import Path

PDF_PATH = Path("RELATORIO_QUADRAS.pdf")
OUTPUT_CSV_PATH = Path("data/raw/quadras_frequentes.csv")
CSV_HEADER = ["quadra", "frequency"]


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
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("\x00", " ")
    normalized = re.sub(r"[^\S\r\n]+", " ", normalized)
    normalized = re.sub(r"\n{2,}", "\n", normalized)
    return normalized.strip()


def normalize_quadra(numbers: list[int]) -> str:
    if len(numbers) != 4:
        raise ValueError("Quadra invalida: esperado 4 dezenas.")
    if any(number < 1 or number > 25 for number in numbers):
        raise ValueError("Quadra invalida: dezenas devem estar entre 1 e 25.")
    if len(set(numbers)) != 4:
        raise ValueError("Quadra invalida: dezenas repetidas.")
    return "-".join(str(number) for number in sorted(numbers))


def parse_line(line: str) -> tuple[str, int] | None:
    values = [int(value) for value in re.findall(r"\d+", line)]
    if len(values) < 5:
        return None

    frequency = values[-1]
    if frequency < 0:
        return None

    for start in range(len(values) - 5, -1, -1):
        quadra_numbers = values[start : start + 4]
        try:
            quadra = normalize_quadra(quadra_numbers)
        except ValueError:
            continue
        return quadra, frequency

    return None


def extract_quadras(text: str) -> list[dict[str, int | str]]:
    quadras: dict[str, int] = {}
    invalid_lines = 0

    for line in normalize_text(text).splitlines():
        parsed = parse_line(line)
        if parsed is None:
            if re.search(r"\d", line):
                invalid_lines += 1
            continue

        quadra, frequency = parsed
        quadras[quadra] = max(frequency, quadras.get(quadra, 0))

    if not quadras:
        raise ValueError(
            "Nenhuma quadra valida foi identificada no PDF. "
            "Verifique se o arquivo contem texto extraivel com quadra e frequencia."
        )

    if invalid_lines:
        print(f"Linhas com numeros ignoradas por formato invalido: {invalid_lines}")

    return [
        {"quadra": quadra, "frequency": frequency}
        for quadra, frequency in sorted(quadras.items(), key=lambda item: (-item[1], item[0]))
    ]


def write_csv(quadras: list[dict[str, int | str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(quadras)


def convert_quadras_pdf(
    pdf_path: Path = PDF_PATH,
    output_path: Path = OUTPUT_CSV_PATH,
) -> list[dict[str, int | str]]:
    text = extract_text_from_pdf(pdf_path)
    quadras = extract_quadras(text)
    write_csv(quadras, output_path)
    return quadras


def print_summary(quadras: list[dict[str, int | str]], output_path: Path) -> None:
    print(f"Quadras extraidas: {len(quadras)}")
    print("Primeiras 10 quadras:")
    for quadra in quadras[:10]:
        print(f"{quadra['quadra']},{quadra['frequency']}")
    print(f"CSV gerado em: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Converte PDF de quadras frequentes para CSV.")
    parser.add_argument(
        "pdf",
        nargs="?",
        type=Path,
        default=PDF_PATH,
        help=f"PDF de entrada. Padrao: {PDF_PATH}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_CSV_PATH,
        help=f"CSV de saida. Padrao: {OUTPUT_CSV_PATH}",
    )
    args = parser.parse_args()

    quadras = convert_quadras_pdf(args.pdf, args.output)
    print_summary(quadras, args.output)


if __name__ == "__main__":
    main()
