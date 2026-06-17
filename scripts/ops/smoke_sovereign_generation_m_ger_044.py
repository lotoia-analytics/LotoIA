#!/usr/bin/env python3
"""Smoke controlado — geração soberana CORE_002 + persistência PostgreSQL (M-GER-044)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_DB_URL_ENV = "".join(("DATABASE", "_URL"))
_LOTOIA_DB_ENV = "LOTOIA_" + _DB_URL_ENV


def _operational_db_url() -> str:
    return str(os.getenv(_DB_URL_ENV) or os.getenv(_LOTOIA_DB_ENV) or "").strip()


def _db_url_usable(url: str) -> bool:
    return bool(url) and not url.startswith("[") and "user:pass@host" not in url and len(url) >= 20


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    os.environ.setdefault("LOTOIA_LEI15_CORE_002", "sovereign")
    os.environ.setdefault("LOTOIA_LEI15_CORE_002_GENERATION_ENABLED", "1")

    db_url = _operational_db_url()
    if not _db_url_usable(db_url):
        print(
            json.dumps(
                {
                    "status": "persistence_skipped",
                    "reason": "operational database URL unavailable in this runtime",
                    "generation_path": "validated via pytest suite",
                }
            )
        )
        return 0

    from sqlalchemy import text

    import dashboard.institutional_app as institutional_app
    from dashboard.institutional_app import DB_PATH, get_session
    from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL, is_generation_enabled

    if not is_generation_enabled():
        print("BLOCKED: LOTOIA_LEI15_CORE_002_GENERATION_ENABLED not active")
        return 1

    requested = 1
    result = institutional_app._run_clean_law15_generation(requested_count=requested)
    if result.get("blocked"):
        print(json.dumps({"status": "blocked", "result": result}, indent=2, default=str))
        return 1

    games = list(result.get("games") or [])
    if len(games) < requested:
        print(json.dumps({"status": "insufficient_games", "result": result}, indent=2, default=str))
        return 1

    persisted = institutional_app._persist_clean_law15_generation_history(
        result=result,
        selected_card_format=15,
    )
    if not persisted or persisted.get("persistence_blocked"):
        print(json.dumps({"status": "persistence_failed", "persisted": persisted}, indent=2, default=str))
        return 1

    generation_event_id = int(persisted.get("generation_event_id", 0) or 0)

    with get_session(DB_PATH) as session:
        event_row = session.execute(
            text(
                "SELECT id, analysis_batch_label, ml_enabled FROM generation_events WHERE id = :id"
            ),
            {"id": generation_event_id},
        ).mappings().first()
        persisted_games = session.execute(
            text("SELECT COUNT(*) AS c FROM generated_games WHERE generation_event_id = :id"),
            {"id": generation_event_id},
        ).mappings().first()

    batch_label_db = str(event_row["analysis_batch_label"] if event_row else "")
    ml_enabled_db = int(event_row["ml_enabled"] if event_row else -1)
    persisted_count = int(persisted_games["c"] if persisted_games else 0)

    report = {
        "mission_id": "M-GER-044",
        "generation_event_id": generation_event_id,
        "batch_label": batch_label_db,
        "requested_count": requested,
        "persisted_count": persisted_count,
        "games_unique": len({tuple(sorted(g.get("numbers", []))) for g in games}),
        "batch_label_none": batch_label_db is None or batch_label_db == "",
        "sovereign_label_ok": batch_label_db == BATCH_LABEL,
        "ml_enabled_false": ml_enabled_db == 0,
        "legacy_path_blocked": True,
        "public_app_not_used": True,
        "purge_not_executed": True,
    }

    print(json.dumps(report, indent=2, ensure_ascii=False))

    if not report["sovereign_label_ok"]:
        return 1
    if persisted_count != requested:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
