from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from lotoia.analytics import load_institutional_analytical_timeline, load_institutional_analytics_snapshot
from lotoia.database.database import (
    DEFAULT_DATABASE_PATH,
    CheckEvent,
    GeneratedGame,
    GenerationEvent,
    ImportedContest,
    get_session,
)

DEFAULT_OBSERVATIONAL_STABILIZATION_REPORT = Path("reports") / "observability" / "observational_stabilization.json"
OBSERVATIONAL_STABILIZATION_SCHEMA_VERSION = "observational-stabilization-v1.0.0"


def _safe_count(session, model) -> int:
    return int(session.execute(select(func.count()).select_from(model)).scalar_one())


def build_observational_stabilization_report(db_path: Path = DEFAULT_DATABASE_PATH) -> dict[str, Any]:
    with get_session(db_path) as session:
        counts = {
            "generation_events": _safe_count(session, GenerationEvent),
            "check_events": _safe_count(session, CheckEvent),
            "generated_games": _safe_count(session, GeneratedGame),
            "imported_contests": _safe_count(session, ImportedContest),
        }

    snapshot = load_institutional_analytics_snapshot()
    timeline = load_institutional_analytical_timeline()
    cockpit_enabled = bool(snapshot)
    timeline_ready = bool(timeline.get("timeline"))
    homepage_priority = "institutional_first" if cockpit_enabled and timeline_ready else "mixed"
    stability_note = "cockpit institucional validado" if cockpit_enabled and timeline_ready else "homepage em observacao"

    return {
        "source": str(db_path),
        "schema_version": OBSERVATIONAL_STABILIZATION_SCHEMA_VERSION,
        "generated_by": "build_observational_stabilization_report",
        "summary": {
            "homepage_priority": homepage_priority,
            "stability_note": stability_note,
            "institutional_snapshot_ready": cockpit_enabled,
            "institutional_timeline_ready": timeline_ready,
        },
        "counts": counts,
        "institutional_snapshot": snapshot.get("summary", {}),
        "institutional_timeline": timeline.get("summary", {}),
    }


def persist_observational_stabilization_report(
    report_path: Path = DEFAULT_OBSERVATIONAL_STABILIZATION_REPORT,
    *,
    db_path: Path = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    report = build_observational_stabilization_report(db_path)
    payload = {
        "source": str(db_path),
        "schema_version": OBSERVATIONAL_STABILIZATION_SCHEMA_VERSION,
        "generated_by": "persist_observational_stabilization_report",
        "report": report,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def load_observational_stabilization_report(
    report_path: Path = DEFAULT_OBSERVATIONAL_STABILIZATION_REPORT,
) -> dict[str, Any]:
    if not report_path.exists():
        return {}
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return dict(payload) if isinstance(payload, dict) else {}
