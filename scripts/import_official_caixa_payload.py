#!/usr/bin/env python3
"""Import verified Caixa JSON payloads into PostgreSQL (Lei 001 recovery path).

Use when the institutional panel cannot reach the Caixa API but the official
payload is already available (API response, auditor evidence, etc.).

Example (Railway shell with DATABASE_URL set):
  python scripts/import_official_caixa_payload.py --file concurso_3708.json
  python scripts/import_official_caixa_payload.py --fetch 3707 3708
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from lotoia.database.contest_repository import ContestRepository
from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.ingestion.caixa_api_client import CaixaApiClient


def _import_normalized_payload(
    *,
    repository: ContestRepository,
    payload: dict,
    source_url: str,
) -> dict:
    result = CaixaApiClient._normalize(payload, source_url)
    contest_number = int(result.contest_number)
    with repository.transaction() as tx:
        repository.save_contest(result.to_contest_record(), commit=False, session=tx)
    confirmation = repository.confirm_sync_persistence(contest_number)
    return {
        "contest_number": contest_number,
        "draw_date": result.draw_date,
        "numbers": list(result.numbers),
        "postgresql_confirmation": confirmation,
        "status": "ok" if confirmation.get("ok") else "error",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import official Caixa payloads into PostgreSQL.")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DATABASE_PATH)
    parser.add_argument("--file", type=Path, action="append", default=[], help="JSON file with Caixa payload")
    parser.add_argument("--fetch", type=int, nargs="*", default=[], help="Contest numbers to fetch from Caixa API")
    args = parser.parse_args(argv)

    repository = ContestRepository(args.db_path)
    repository.create_table()
    print(f"backend={repository.backend} engine={repository.database_url[:48]}...")
    print(f"BEFORE imported_max={repository.get_last_contest()} official_max={repository.get_official_history_max_contest()}")

    results: list[dict] = []
    client = CaixaApiClient()

    for file_path in args.file:
        payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
        outcome = _import_normalized_payload(
            repository=repository,
            payload=payload,
            source_url=f"manual://caixa-payload/{Path(file_path).name}",
        )
        results.append({"source": str(file_path), **outcome})

    for contest_number in sorted(set(int(value) for value in args.fetch)):
        payload = client.fetch_contest(contest_number).raw_payload
        outcome = _import_normalized_payload(
            repository=repository,
            payload=payload,
            source_url=f"{client.base_url}/{contest_number}",
        )
        results.append({"source": f"fetch:{contest_number}", **outcome})

    if not results:
        parser.error("Provide --file and/or --fetch")

    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(
        f"AFTER imported_max={repository.get_last_contest()} "
        f"official_max={repository.get_official_history_max_contest()}"
    )
    return 0 if all(item.get("status") == "ok" for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
