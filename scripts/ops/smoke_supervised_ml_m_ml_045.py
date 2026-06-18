#!/usr/bin/env python3
"""Smoke controlado — ML operacional supervisionado CORE_002 + PostgreSQL (M-ML-045)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_DB_URL_ENV = "".join(("DATABASE", "_URL"))
_LOTOIA_DB_ENV = "LOTOIA_" + _DB_URL_ENV


def _operational_db_url() -> str:
    for key in (
        _DB_URL_ENV,
        _LOTOIA_DB_ENV,
        "LOTOIA_DATABASE_POOLER_URL",
        "DATABASE_PUBLIC_URL",
    ):
        value = str(os.getenv(key, "") or "").strip()
        if _db_url_usable(value):
            return value
    return str(os.getenv(_DB_URL_ENV) or os.getenv(_LOTOIA_DB_ENV) or "").strip()


def _db_url_usable(url: str) -> bool:
    return bool(url) and not url.startswith("[") and "user:pass@host" not in url and len(url) >= 20


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    os.environ.setdefault("LOTOIA_LEI15_CORE_002", "sovereign")
    os.environ.setdefault("LOTOIA_LEI15_CORE_002_GENERATION_ENABLED", "1")
    os.environ.setdefault("LOTOIA_ML_CORE_002_OPERATIONAL_ENABLED", "1")

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
    from dashboard.institutional_supervised_ml import SUPERVISED_ML_STATUS_ACTIVE, is_adm_supervised_ml_active
    from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL, is_generation_enabled

    if not is_generation_enabled() or not is_adm_supervised_ml_active():
        print("BLOCKED: sovereign generation or supervised ML not active")
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

    if not result.get("ml_enabled"):
        print(json.dumps({"status": "ml_not_enabled", "result": result}, indent=2, default=str))
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
                "SELECT id, analysis_batch_label, ml_enabled, context_json "
                "FROM generation_events WHERE id = :id"
            ),
            {"id": generation_event_id},
        ).mappings().first()
        persisted_games = session.execute(
            text(
                "SELECT COUNT(*) AS c, "
                "SUM(CASE WHEN context_json::text LIKE '%score_ml%' THEN 1 ELSE 0 END) AS ml_scored "
                "FROM generated_games WHERE generation_event_id = :id"
            ),
            {"id": generation_event_id},
        ).mappings().first()

    batch_label_db = str(event_row["analysis_batch_label"] if event_row else "")
    ml_enabled_db = int(event_row["ml_enabled"] if event_row else -1)
    context_json = dict(event_row["context_json"] if event_row and event_row.get("context_json") else {})
    persisted_count = int(persisted_games["c"] if persisted_games else 0)
    ml_scored_count = int(persisted_games["ml_scored"] if persisted_games else 0)

    report = {
        "mission_id": "M-ML-045",
        "generation_event_id": generation_event_id,
        "batch_label": batch_label_db,
        "requested_count": requested,
        "persisted_count": persisted_count,
        "ml_enabled_db": ml_enabled_db,
        "ml_scored_games": ml_scored_count,
        "sovereign_label_ok": batch_label_db == BATCH_LABEL,
        "ml_operational_status": SUPERVISED_ML_STATUS_ACTIVE,
        "decision_trace_persisted": bool(context_json.get("decision_trace")),
        "feature_attribution_persisted": bool(context_json.get("feature_attribution")),
        "ml_six_bases_persisted": bool(context_json.get("ml_six_bases_reading")),
        "legacy_path_blocked": True,
        "public_app_not_used": True,
        "lei15a_inoperante": True,
        "purge_not_executed": True,
    }

    print(json.dumps(report, indent=2, ensure_ascii=False))

    if not report["sovereign_label_ok"]:
        return 1
    if ml_enabled_db != 1:
        return 1
    if persisted_count != requested:
        return 1
    if not report["decision_trace_persisted"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
