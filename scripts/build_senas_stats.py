import argparse
import json
import re
import unicodedata
from pathlib import Path

DEFAULT_INPUT_PATH = Path("RELATORIO_SENADEZENAS.pdf")
DEFAULT_OUTPUT_PATH = Path("data/stats/senas_stats.json")


def _extract_text_from_pdf(path: Path) -> str:
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


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("\x00", " ")
    normalized = re.sub(r"[^\S\r\n]+", " ", normalized)
    normalized = re.sub(r"\n{2,}", "\n", normalized)
    return normalized.strip()


def _normalize_sena(numbers: list[int]) -> str:
    if len(numbers) != 6:
        raise ValueError("Uma sena deve conter exatamente 6 dezenas.")
    if any(number < 1 or number > 25 for number in numbers):
        raise ValueError("As dezenas da sena devem estar entre 1 e 25.")
    if len(set(numbers)) != 6:
        raise ValueError("As dezenas da sena devem ser unicas.")
    return "-".join(f"{number:02d}" for number in sorted(numbers))


def _parse_line(line: str) -> tuple[str, int] | None:
    values = [int(value) for value in re.findall(r"\d+", line)]
    if len(values) < 8:
        return None

    count = values[-1]
    if count <= 0:
        return None

    for start in range(1, len(values) - 6):
        sena_numbers = values[start : start + 6]
        try:
            sena = _normalize_sena(sena_numbers)
        except ValueError:
            continue
        return sena, count

    return None


def _extract_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return _extract_text_from_pdf(path)

    return path.read_text(encoding="utf-8-sig")


def _parse_senas_text(text: str) -> list[tuple[str, int]]:
    records: dict[str, int] = {}

    for line in _normalize_text(text).splitlines():
        parsed = _parse_line(line)
        if parsed is None:
            continue

        sena, count = parsed
        records[sena] = max(count, records.get(sena, 0))

    return sorted(records.items(), key=lambda item: (-item[1], item[0]))


def build_senas_stats(
    source_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> dict[str, dict[str, float | int]]:
    if not source_path.exists():
        raise FileNotFoundError(f"Relatorio de senas nao encontrado: {source_path}")

    records = _parse_senas_text(_extract_text(source_path))
    if not records:
        raise ValueError("Nenhuma sena valida encontrada no relatorio de origem.")

    max_count = max(count for _, count in records)
    stats = {
        sena: {
            "count": count,
            "rank": rank,
            "relative_strength": round(count / max_count, 3),
        }
        for rank, (sena, count) in enumerate(records, start=1)
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera estatisticas de senas frequentes.")
    parser.add_argument(
        "source",
        nargs="?",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"Relatorio de entrada. Padrao: {DEFAULT_INPUT_PATH}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Arquivo JSON de saida. Padrao: {DEFAULT_OUTPUT_PATH}",
    )
    args = parser.parse_args()

    build_senas_stats(args.source, args.output)


if __name__ == "__main__":
    main()
