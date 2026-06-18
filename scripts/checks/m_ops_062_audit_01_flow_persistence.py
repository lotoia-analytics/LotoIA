#!/usr/bin/env python3
"""M-OPS-062-AUDIT-01 — Auditoria read-only do fluxo Gerador → Cobertura → Central ML.

Não altera dados. Não executa purge. Não expõe connection strings.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MISSION_ID = "M-OPS-062-AUDIT-01"


def _mask_db_config() -> dict[str, bool]:
    import os

    return {
        "DATABASE_URL": bool(os.getenv("DATABASE_URL", "").strip()),
        "LOTOIA_DATABASE_URL": bool(os.getenv("LOTOIA_DATABASE_URL", "").strip()),
        "DATABASE_PUBLIC_URL": bool(os.getenv("DATABASE_PUBLIC_URL", "").strip()),
    }


def _is_postgres_configured() -> bool:
    from lotoia.database.env_resolution import is_postgresql_database_url, resolve_institutional_database_url_from_env

    url, _source = resolve_institutional_database_url_from_env()
    return bool(url) and is_postgresql_database_url(url)


def _audit_event_row(session, event) -> dict[str, Any]:
    from lotoia.database.database import GeneratedGame
    from lotoia.governance.batch_operational_scope import (
        is_generation_event_active_reading,
        resolve_batch_operational_fields,
        resolve_operational_status_from_context,
    )
    from lotoia.governance.lei15_core_002_sovereign import (
        core_002_batch_label_game_size,
        is_sovereign_core_label,
    )
    from lotoia.observability.card_structure_diagnostics import _event_eligible_for_active_structural_reading
    from lotoia.operations.lot_operational_status import extract_lot_operational_status

    ge_id = int(event.id or 0)
    context = dict(getattr(event, "context_json", {}) or {})
    batch_label = str(getattr(event, "analysis_batch_label", "") or "")
    game_rows = (
        session.query(GeneratedGame)
        .filter(GeneratedGame.generation_event_id == ge_id)
        .order_by(GeneratedGame.game_index.asc())
        .all()
    )
    card_sizes: list[int] = []
    for row in game_rows:
        numbers = list(getattr(row, "numbers", []) or [])
        row_ctx = dict(getattr(row, "context_json", {}) or {})
        final_card = list(row_ctx.get("final_card_numbers") or numbers or [])
        card_sizes.append(len(final_card) if final_card else len(numbers))

    fields = resolve_batch_operational_fields(context)
    lot_status = extract_lot_operational_status(context)
    label_size = core_002_batch_label_game_size(batch_label)
    in_coverage_loader = (
        is_sovereign_core_label(batch_label)
        and is_generation_event_active_reading(event)
        and bool(game_rows)
    )
    in_coverage_metrics = (
        in_coverage_loader and _event_eligible_for_active_structural_reading(context)
    )
    in_central_ml_detail = in_coverage_loader and int(getattr(event, "ml_enabled", 0) or 0) == 1
    conference_eligible = bool(context.get("is_official_conference_eligible"))

    return {
        "generation_event_id": ge_id,
        "created_at": event.created_at.isoformat() if getattr(event, "created_at", None) else "",
        "analysis_batch_label": batch_label,
        "sovereign_batch_label": is_sovereign_core_label(batch_label),
        "label_format_d": label_size,
        "requested_games": int(context.get("selected_quantity", 0) or 0),
        "persisted_games": len(game_rows),
        "card_sizes_observed": sorted(set(card_sizes)) if card_sizes else [],
        "lot_operational_status": lot_status,
        "operational_status": fields["operational_status"],
        "generation_origin": str(context.get("generation_origin") or ""),
        "simulation_mode": bool(context.get("simulation_mode")),
        "validation_flow": list(context.get("validation_flow") or []),
        "ml_enabled": bool(getattr(event, "ml_enabled", 0)),
        "ml_verdict": str(context.get("ml_verdict") or ""),
        "official_release_allowed": bool(context.get("official_release_allowed")),
        "in_coverage_dropdown": in_coverage_loader,
        "in_coverage_metrics": in_coverage_metrics,
        "in_central_ml_detail": in_central_ml_detail,
        "conference_eligible": conference_eligible,
        "active_reading_scope": context.get("active_reading_scope"),
        "lot_status_trace_present": bool(context.get("lot_status_trace")),
    }


def audit_postgresql_flow(
    *,
    card_format: int = 17,
    limit: int = 30,
) -> dict[str, Any]:
    from lotoia.database.database import DEFAULT_DATABASE_PATH, GenerationEvent, get_session
    from lotoia.governance.lei15_core_002_sovereign import core_002_batch_label_game_size, resolve_core_002_batch_label
    from dashboard.institutional_operational_structural_coverage import load_operational_core_002_generations
    from dashboard.institutional_supervised_ml import load_supervised_ml_operational_events_from_db
    from lotoia.observability.coverage_evidence_interpreter import get_structural_coverage_evidence

    if not _is_postgres_configured():
        return {
            "mission_id": MISSION_ID,
            "status": "SKIP",
            "reason": "PostgreSQL não configurado neste runtime",
            "db_config_present": _mask_db_config(),
        }

    target_label = resolve_core_002_batch_label(card_format)
    audited_events: list[dict[str, Any]] = []
    with get_session(DEFAULT_DATABASE_PATH) as session:
        events = (
            session.query(GenerationEvent)
            .order_by(GenerationEvent.created_at.desc(), GenerationEvent.id.desc())
            .limit(max(1, int(limit)) * 10)
            .all()
        )
        for event in events:
            batch_label = str(getattr(event, "analysis_batch_label", "") or "")
            label_size = core_002_batch_label_game_size(batch_label)
            if label_size != card_format:
                continue
            audited_events.append(_audit_event_row(session, event))
            if len(audited_events) >= limit:
                break

    coverage_generations = load_operational_core_002_generations(DEFAULT_DATABASE_PATH)
    ml_events = load_supervised_ml_operational_events_from_db(DEFAULT_DATABASE_PATH, limit=limit)
    coverage_evidence = get_structural_coverage_evidence(DEFAULT_DATABASE_PATH)
    latest = audited_events[0] if audited_events else {}
    latest_ge_id = int(latest.get("generation_event_id", 0) or 0)

    coverage_has_latest = any(
        int(row.get("generation_event_id", 0) or 0) == latest_ge_id for row in coverage_generations
    ) if latest_ge_id else False
    ml_has_latest = any(
        int(row.get("generation_event_id", 0) or 0) == latest_ge_id for row in ml_events
    ) if latest_ge_id else False

    conference_independent = True
    if latest:
        conference_independent = bool(latest.get("in_coverage_dropdown")) and not bool(
            latest.get("conference_eligible")
        ) or bool(latest.get("in_coverage_dropdown"))

    root_causes: list[str] = []
    if latest and not latest.get("in_coverage_dropdown"):
        if not latest.get("sovereign_batch_label"):
            root_causes.append("batch_label não soberano CORE_002")
        if latest.get("lot_operational_status") in {
            "not_officialized",
            "calibration_source_only",
            "rejected",
            "superseded_by_calibration",
            "blocked_for_officialization",
        }:
            root_causes.append(f"status operacional excluído: {latest.get('lot_operational_status')}")
        if latest.get("operational_status") == "needs_calibration":
            root_causes.append("needs_calibration fora do escopo ativo (main sem FIX-04)")
        if latest.get("persisted_games", 0) == 0:
            root_causes.append("sem generated_games persistidos")
        if latest.get("simulation_mode") and not latest.get("in_coverage_metrics"):
            root_causes.append("simulation_mode excluído das métricas de Cobertura (main sem FIX-04)")

    return {
        "mission_id": MISSION_ID,
        "audited_at": datetime.now(UTC).isoformat(),
        "status": "PASS" if latest and coverage_has_latest else ("WARN" if latest else "FAIL"),
        "target_format_d": card_format,
        "target_batch_label": target_label,
        "db_config_present": _mask_db_config(),
        "events_audited_count": len(audited_events),
        "latest_event": latest,
        "coverage_active_count": len(coverage_generations),
        "coverage_has_latest_event": coverage_has_latest,
        "central_ml_detail_count": len(ml_events),
        "central_ml_has_latest_event": ml_has_latest,
        "coverage_evidence_available": bool(coverage_evidence.get("available")),
        "conference_independent": conference_independent,
        "conference_prerequisite_for_coverage": False,
        "root_causes_if_missing": root_causes,
        "events_sample": audited_events[:10],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="M-OPS-062-AUDIT-01 flow persistence audit")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--card-format", type=int, default=17)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    report = audit_postgresql_flow(card_format=args.card_format, limit=args.limit)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"{MISSION_ID}: {report.get('status')}")
        latest = report.get("latest_event") or {}
        if latest:
            print(f"  GE: {latest.get('generation_event_id')}")
            print(f"  persisted_games: {latest.get('persisted_games')}")
            print(f"  lot_operational_status: {latest.get('lot_operational_status')}")
            print(f"  in_coverage: {latest.get('in_coverage_dropdown')}")
            print(f"  in_central_ml: {latest.get('in_central_ml_detail')}")
        if report.get("root_causes_if_missing"):
            for cause in report["root_causes_if_missing"]:
                print(f"  CAUSA: {cause}")
    return 0 if report.get("status") in {"PASS", "SKIP", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
