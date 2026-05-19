from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from pathlib import Path

PDF_PATH = Path("RELATORIO_ATRASODEZENAS.pdf")
OUTPUT_CSV_PATH = Path("data/raw/atrasos_dezenas.csv")
CSV_HEADER = ["dezena", "delay"]


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


def normalize_delay_record(dezena: int, delay: int) -> dict[str, int]:
    if dezena < 1 or dezena > 25:
        raise ValueError("Dezena invalida: deve estar entre 1 e 25.")
    if delay < 0:
        raise ValueError("Atraso invalido: deve ser maior ou igual a zero.")
    return {"dezena": dezena, "delay": delay}


def parse_line(line: str) -> dict[str, int] | None:
    match = re.match(r"^\s*(\d{1,2})\s+(\d+)\s*$", line)
    if not match:
        return None

    dezena, delay = (int(value) for value in match.groups())
    try:
        return normalize_delay_record(dezena, delay)
    except ValueError:
        return None


def extract_atrasos(text: str) -> list[dict[str, int]]:
    delays: dict[int, int] = {}
    invalid_lines = 0

    for line in normalize_text(text).splitlines():
        parsed = parse_line(line)
        if parsed is None:
            if re.search(r"\d", line):
                invalid_lines += 1
            continue

        dezena = parsed["dezena"]
        delay = parsed["delay"]
        delays[dezena] = max(delay, delays.get(dezena, 0))

    if not delays:
        raise ValueError(
            "Nenhum atraso valido foi identificado no PDF. "
            "Verifique se o arquivo contem texto extraivel com dezena e atraso."
        )

    if invalid_lines:
        print(f"Linhas com numeros ignoradas por formato invalido: {invalid_lines}")

    return [
        {"dezena": dezena, "delay": delay}
        for dezena, delay in sorted(delays.items(), key=lambda item: (-item[1], item[0]))
    ]


def write_csv(atrasos: list[dict[str, int]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(atrasos)


def convert_atrasos_pdf(
    pdf_path: Path = PDF_PATH,
    output_path: Path = OUTPUT_CSV_PATH,
) -> list[dict[str, int]]:
    text = extract_text_from_pdf(pdf_path)
    atrasos = extract_atrasos(text)
    write_csv(atrasos, output_path)
    return atrasos


def print_summary(atrasos: list[dict[str, int]], output_path: Path) -> None:
    print(f"Dezenas extraidas: {len(atrasos)}")
    print("Top dezenas atrasadas:")
    for atraso in atrasos[:10]:
        print(f"{atraso['dezena']},{atraso['delay']}")
    print(f"CSV gerado em: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Converte PDF de atrasos de dezenas para CSV.")
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

    atrasos = convert_atrasos_pdf(args.pdf, args.output)
    print_summary(atrasos, args.output)


if __name__ == "__main__":
    main()
