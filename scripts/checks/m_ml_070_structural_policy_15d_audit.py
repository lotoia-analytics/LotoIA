#!/usr/bin/env python3
"""M-ML-070 — Auditoria read-only da política estrutural soberana 15D."""

from __future__ import annotations

import argparse
import inspect
import json
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MISSION_ID = "M-ML-070"


def _compliant_numbers() -> list[int]:
    return [1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 16, 17, 18, 20, 22]


def audit_structural_policy_15d_application() -> dict[str, Any]:
    from lotoia.ml.structural_policy_15d import (
        MISSION_ID as ML070,
        POLICY_VERSION,
        apply_structural_policy_15d_to_sovereign_batch,
        build_structural_policy_15d_memory,
        is_structural_policy_15d_format,
        load_active_structural_policy_15d_memory,
        persist_structural_policy_15d_memory,
        validate_game_structural_policy_15d,
    )
    from lotoia.observability.coverage_evidence_interpreter import get_structural_coverage_evidence

    import dashboard.institutional_ml_calibration_cockpit as cockpit

    with tempfile.TemporaryDirectory(prefix="m-ml-070-audit-") as tmp_dir:
        db_path = Path(tmp_dir) / "structural_policy_15d.db"
        memory = build_structural_policy_15d_memory()
        previous = list(range(1, 16))
        validation = validate_game_structural_policy_15d(
            _compliant_numbers(),
            previous_contest_numbers=previous,
        )
        compliant_game = {
            "numbers": _compliant_numbers(),
            "final_card_numbers": _compliant_numbers(),
            "profile_score": 2.0,
            "final_score": {"final_score": 90.0},
        }
        games, bundle = apply_structural_policy_15d_to_sovereign_batch(
            [compliant_game],
            pool_games=[compliant_game],
            history=[{"numbers": previous}],
            required_count=1,
            db_path=db_path,
        )
        persisted = persist_structural_policy_15d_memory(db_path)
        loaded = load_active_structural_policy_15d_memory(db_path, persist_if_missing=False)

    cockpit_source = inspect.getsource(cockpit.render_ml_calibration_cockpit)
    card_source = inspect.getsource(cockpit._render_structural_policy_15d_card)
    interpreter_source = inspect.getsource(get_structural_coverage_evidence)

    checks = {
        "format_gate_15d": is_structural_policy_15d_format(15) and not is_structural_policy_15d_format(16),
        "memory_catalog": memory.get("mission_id") == ML070 and memory.get("policy_version") == POLICY_VERSION,
        "validation_rules": bool(validation.get("applied_rules")),
        "bundle_mission_id": bundle.get("mission_id") == ML070,
        "bundle_memory_loaded": bool(bundle.get("structural_policy_memory_loaded")),
        "games_enriched": bool(games and games[0].get("structural_policy_15d_validation")),
        "central_ml_card": "_render_structural_policy_15d_card" in cockpit_source,
        "card_references_memory": "structural_policy_15d_memory" in card_source,
        "interpreter_exports_fields": all(
            token in interpreter_source
            for token in (
                "structural_policy_15d_memory",
                "structural_policy_15d_application",
                "structural_policy_15d_mission_id",
            )
        ),
        "persist_load_api_present": bool(persisted.get("mission_id")) and bool(loaded.get("mission_id")),
    }

    root_causes: list[str] = []
    if not checks["format_gate_15d"]:
        root_causes.append("gate 15D ausente ou incorreto")
    if not checks["bundle_mission_id"]:
        root_causes.append("bundle soberano sem mission_id M-ML-070")
    if not checks["central_ml_card"]:
        root_causes.append("Central ML não expõe card da política estrutural 15D")
    if not checks["interpreter_exports_fields"]:
        root_causes.append("coverage_evidence_interpreter não exporta campos M-ML-070")

    status = "PASS" if all(checks.values()) else "FAIL"
    if status == "FAIL" and checks["bundle_mission_id"] and checks["central_ml_card"]:
        status = "WARN"

    return {
        "mission_id": MISSION_ID,
        "audited_at": datetime.now(UTC).isoformat(),
        "status": status,
        "checks": checks,
        "bundle_summary": {
            "policy_compliance_status": bundle.get("policy_compliance_status"),
            "games_validated": bundle.get("games_validated"),
            "games_compliant": bundle.get("games_compliant"),
            "applied_rules": bundle.get("applied_rules"),
        },
        "validation_summary": {
            "approved": validation.get("approved"),
            "repeat_count": validation.get("repeat_count"),
            "parity": validation.get("parity"),
            "largest_sequence": validation.get("largest_sequence"),
        },
        "root_causes_if_missing": root_causes,
        "purge_executed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="M-ML-070 structural policy 15D audit")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = audit_structural_policy_15d_application()
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"{MISSION_ID}: {report.get('status')}")
        for key, value in dict(report.get("checks") or {}).items():
            print(f"  {key}: {value}")
        for cause in report.get("root_causes_if_missing") or []:
            print(f"  CAUSA: {cause}")
    return 0 if report.get("status") in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
