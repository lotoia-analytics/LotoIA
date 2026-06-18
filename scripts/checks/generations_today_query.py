#!/usr/bin/env python3
"""Consulta gerações do dia no PostgreSQL institucional (Lei No 001)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", maxsplit=1)
        key = key.strip()
        if key in os.environ:
            continue
        os.environ[key] = value.strip().strip('"').strip("'")


def run_query(*, target_date: date | None = None) -> dict:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    _load_dotenv()

    from sqlalchemy import text

    from lotoia.database.database import DEFAULT_DATABASE_PATH, get_engine

    day = target_date or date.today()
    engine = get_engine(DEFAULT_DATABASE_PATH)

    with engine.connect() as conn:
        client_rows = conn.execute(
            text(
                """
                SELECT id, phone, formato, quantidade, concurso_alvo, generation_event_id, created_at
                FROM lotoia_client_generations
                WHERE created_at::date = :day
                ORDER BY created_at DESC
                """
            ),
            {"day": day},
        ).mappings().all()

        event_rows = conn.execute(
            text(
                """
                SELECT id, whatsapp, first_name, created_at,
                       COALESCE(jsonb_array_length(generated_games::jsonb), 0) AS qtd_jogos
                FROM generation_events
                WHERE created_at::date = :day
                ORDER BY created_at DESC
                """
            ),
            {"day": day},
        ).mappings().all()

    return {
        "date": day.isoformat(),
        "whatsapp_client_generations": {
            "count": len(client_rows),
            "items": [dict(row) for row in client_rows],
        },
        "institutional_generation_events": {
            "count": len(event_rows),
            "items": [dict(row) for row in event_rows],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Listar gerações do dia no PostgreSQL cloud")
    parser.add_argument("--date", default="", help="YYYY-MM-DD (padrão: hoje)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    target = date.fromisoformat(args.date) if args.date else None
    try:
        report = run_query(target_date=target)
    except Exception as exc:
        payload = {"status": "FAIL", "error": str(exc)}
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(f"generations-today: FAIL")
            print(f"  {exc}")
        return 1

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    else:
        print(f"gerações em {report['date']}")
        print(f"  WhatsApp (lotoia_client_generations): {report['whatsapp_client_generations']['count']}")
        for item in report["whatsapp_client_generations"]["items"]:
            print(
                f"    - id={item.get('id')} phone={item.get('phone')} "
                f"formato={item.get('formato')} qtd={item.get('quantidade')} "
                f"concurso={item.get('concurso_alvo')} at={item.get('created_at')}"
            )
        print(f"  Painel (generation_events): {report['institutional_generation_events']['count']}")
        for item in report["institutional_generation_events"]["items"]:
            print(
                f"    - id={item.get('id')} whatsapp={item.get('whatsapp')} "
                f"jogos={item.get('qtd_jogos')} at={item.get('created_at')}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
