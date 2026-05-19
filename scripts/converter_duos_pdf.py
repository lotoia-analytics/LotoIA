from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from pathlib import Path

PDF_PATH = Path("RELATORIO_DUQUEDEZENAS.pdf")
OUTPUT_CSV_PATH = Path("data/raw/duos_frequentes.csv")
CSV_HEADER = ["duo", "frequency"]


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


def normalize_duo(numbers: list[int]) -> str:
    if len(numbers) != 2:
        raise ValueError("Duo invalido: esperado 2 dezenas.")
    if any(number < 1 or number > 25 for number in numbers):
        raise ValueError("Duo invalido: dezenas devem estar entre 1 e 25.")
    if len(set(numbers)) != 2:
        raise ValueError("Duo invalido: dezenas repetidas.")
    return "-".join(str(number) for number in sorted(numbers))


def parse_line(line: str) -> tuple[str, int] | None:
    values = [int(value) for value in re.findall(r"\d+", line)]
    if len(values) < 3:
        return None

    frequency = values[-1]
    if frequency < 0:
        return None

    for start in range(len(values) - 3, -1, -1):
        duo_numbers = values[start : start + 2]
        try:
            duo = normalize_duo(duo_numbers)
        except ValueError:
            continue
        return duo, frequency

    return None


def extract_duos(text: str) -> list[dict[str, int | str]]:
    duos: dict[str, int] = {}
    invalid_lines = 0

    for line in normalize_text(text).splitlines():
        parsed = parse_line(line)
        if parsed is None:
            if re.search(r"\d", line):
                invalid_lines += 1
            continue

        duo, frequency = parsed
        duos[duo] = max(frequency, duos.get(duo, 0))

    if not duos:
        raise ValueError(
            "Nenhum duo valido foi identificado no PDF. "
            "Verifique se o arquivo contem texto extraivel com duo e frequencia."
        )

    if invalid_lines:
        print(f"Linhas com numeros ignoradas por formato invalido: {invalid_lines}")

    return [
        {"duo": duo, "frequency": frequency}
        for duo, frequency in sorted(duos.items(), key=lambda item: (-item[1], item[0]))
    ]


def write_csv(duos: list[dict[str, int | str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(duos)


def convert_duos_pdf(
    pdf_path: Path = PDF_PATH,
    output_path: Path = OUTPUT_CSV_PATH,
) -> list[dict[str, int | str]]:
    text = extract_text_from_pdf(pdf_path)
    duos = extract_duos(text)
    write_csv(duos, output_path)
    return duos


def print_summary(duos: list[dict[str, int | str]], output_path: Path) -> None:
    print(f"Duos extraidos: {len(duos)}")
    print("Primeiros 10 duos:")
    for duo in duos[:10]:
        print(f"{duo['duo']},{duo['frequency']}")
    print(f"CSV gerado em: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Converte PDF de duos frequentes para CSV.")
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

    duos = convert_duos_pdf(args.pdf, args.output)
    print_summary(duos, args.output)


if __name__ == "__main__":
    main()
