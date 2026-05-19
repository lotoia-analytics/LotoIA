from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

STATS_DIR = Path("data/stats")
EXPECTED_FILES = {
    "delay_stats.json": {"kind": "single", "fields": {"delay"}, "count": 25},
    "frequency_stats.json": {
        "kind": "single",
        "fields": {"count", "delta", "relative_strength"},
        "count": 25,
    },
    "duos_stats.json": {"kind": "combo", "size": 2, "fields": {"frequency", "rank"}},
    "ternos_stats.json": {"kind": "combo", "size": 3, "fields": {"frequency", "rank"}},
    "quadras_stats.json": {"kind": "combo", "size": 4, "fields": {"frequency", "rank"}},
    "quinas_stats.json": {
        "kind": "combo",
        "size": 5,
        "fields": {"count", "rank", "relative_strength"},
    },
    "senas_stats.json": {
        "kind": "combo",
        "size": 6,
        "fields": {"count", "rank", "relative_strength"},
    },
}


def _load_json(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    if not path.exists():
        return None, [f"arquivo ausente: {path}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [f"JSON invalido em {path}: {exc}"]
    if not isinstance(payload, dict):
        return None, [f"raiz deve ser objeto JSON: {path}"]
    return payload, []


def _parse_key_numbers(key: str) -> list[int] | None:
    try:
        return [int(part) for part in key.split("-")]
    except ValueError:
        return None


def _validate_number_range(numbers: list[int]) -> bool:
    return all(1 <= number <= 25 for number in numbers)


def _validate_single_file(name: str, payload: dict[str, Any], spec: dict[str, Any]) -> list[str]:
    errors = []
    expected_count = spec["count"]
    if len(payload) != expected_count:
        errors.append(f"{name}: esperado {expected_count} dezenas, encontrado {len(payload)}")

    for key, values in payload.items():
        numbers = _parse_key_numbers(key)
        if numbers is None or len(numbers) != 1 or not _validate_number_range(numbers):
            errors.append(f"{name}: dezena invalida: {key}")
            continue
        if not isinstance(values, dict):
            errors.append(f"{name}: valor deve ser objeto em {key}")
            continue
        missing = spec["fields"] - set(values)
        if missing:
            errors.append(f"{name}: campos ausentes em {key}: {sorted(missing)}")
        if "delay" in values and int(values["delay"]) < 0:
            errors.append(f"{name}: delay negativo em {key}")
        if "count" in values and int(values["count"]) <= 0:
            errors.append(f"{name}: count invalido em {key}")
        if "relative_strength" in values and float(values["relative_strength"]) < 0:
            errors.append(f"{name}: relative_strength negativo em {key}")
    return errors


def _validate_combo_file(name: str, payload: dict[str, Any], spec: dict[str, Any]) -> list[str]:
    errors = []
    previous_rank = 0
    previous_frequency = None

    for key, values in payload.items():
        numbers = _parse_key_numbers(key)
        if (
            numbers is None
            or len(numbers) != spec["size"]
            or len(set(numbers)) != spec["size"]
            or not _validate_number_range(numbers)
            or numbers != sorted(numbers)
        ):
            errors.append(f"{name}: combinacao invalida: {key}")
            continue

        if not isinstance(values, dict):
            errors.append(f"{name}: valor deve ser objeto em {key}")
            continue
        missing = spec["fields"] - set(values)
        if missing:
            errors.append(f"{name}: campos ausentes em {key}: {sorted(missing)}")

        frequency = int(values.get("frequency", values.get("count", 0)))
        rank = int(values.get("rank", 0))
        if frequency <= 0:
            errors.append(f"{name}: frequencia/count invalido em {key}")
        if rank <= 0:
            errors.append(f"{name}: rank invalido em {key}")
        if previous_rank and rank < previous_rank:
            errors.append(f"{name}: ranks fora de ordem em {key}")
        if previous_frequency is not None and frequency > previous_frequency:
            errors.append(f"{name}: frequencias fora de ordem em {key}")
        if "relative_strength" in values and float(values["relative_strength"]) < 0:
            errors.append(f"{name}: relative_strength negativo em {key}")
        previous_rank = rank
        previous_frequency = frequency
    return errors


def audit_stats(stats_dir: Path = STATS_DIR) -> dict[str, Any]:
    summary = {"stats_dir": str(stats_dir), "files": {}, "errors": []}
    for filename, spec in EXPECTED_FILES.items():
        payload, errors = _load_json(stats_dir / filename)
        if payload is None:
            summary["files"][filename] = {"entries": 0, "status": "ERROR"}
            summary["errors"].extend(errors)
            continue

        if spec["kind"] == "single":
            errors.extend(_validate_single_file(filename, payload, spec))
        else:
            errors.extend(_validate_combo_file(filename, payload, spec))

        summary["files"][filename] = {
            "entries": len(payload),
            "status": "OK" if not errors else "ERROR",
        }
        summary["errors"].extend(errors)
    return summary


def main() -> None:
    summary = audit_stats()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
