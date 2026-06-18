#!/usr/bin/env python3
"""M-ML-069-AUDIT-01 — Auditoria read-only da calibração estrutural automática 16D–23D.

Não altera dados. Não executa purge. Não expõe segredos.
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

MISSION_ID = "M-ML-069-AUDIT-01"
FORMATS_16_23 = tuple(range(16, 24))
OUTSIDE_FORMATS = (15, 24)


def _card(size: int, base: int = 1) -> list[int]:
    return list(range(base, base + size))


def _game(size: int, base: int = 1, *, core: list[int] | None = None) -> dict[str, Any]:
    numbers = _card(size, base)
    payload: dict[str, Any] = {
        "numbers": numbers,
        "final_card_numbers": numbers,
        "score_ml": 55.0,
        "profile_score": 1.0,
    }
    if core is not None:
        payload["core_numbers"] = core
    return payload


def _dominant_prefix_pool(size: int) -> list[dict[str, Any]]:
    return [_game(size, 1)] * 12 + [_game(size, 2)] * 8


def _audit_format(size: int) -> dict[str, Any]:
    from lotoia.ml.structural_auto_calibration import (
        ACTION_EXCESSIVE_DEZENAS,
        ACTION_PREFIX_DOMINANT,
        ACTION_UNDERCOVERED_DEZENAS,
        MISSION_ID as ML069,
        build_auto_calibration_plan_from_pool,
        build_structural_calibration_memory,
        is_structural_auto_calibration_format,
    )
    from lotoia.ml.supervised_output_calibration import apply_supervised_output_calibration

    gate_ok = is_structural_auto_calibration_format(size)
    plan = build_auto_calibration_plan_from_pool(_dominant_prefix_pool(size), game_size=size)
    causes = {row["problema_detectado"] for row in plan.get("structural_actions") or []}
    memory = dict(plan.get("structural_calibration_memory") or {})
    per_format = dict(memory.get("per_format_records") or {}).get(f"{size}D") or []

    games = _dominant_prefix_pool(size)
    for idx, game in enumerate(games):
        game["profile_score"] = 10.0 - (idx * 0.01)
        game["score_ml"] = 90.0 - idx
    calibrated, bundle = apply_supervised_output_calibration(games, game_size=size, ml_enabled=True)

    return {
        "formato": f"{size}D",
        "gate_format_aware": gate_ok,
        "auto_structural_calibration": bool(plan.get("auto_structural_calibration")),
        "plan_items_count": len(plan.get("plan_items") or []),
        "actions_detected": sorted(causes),
        "has_prefix_action": ACTION_PREFIX_DOMINANT in causes,
        "has_undercovered_action": ACTION_UNDERCOVERED_DEZENAS in causes,
        "has_excessive_action": ACTION_EXCESSIVE_DEZENAS in causes,
        "structural_calibration_memory_mission": memory.get("mission_id"),
        "per_format_record_present": bool(per_format),
        "memory_catalog_mission": build_structural_calibration_memory().get("mission_id"),
        "calibration_applied": bool(bundle.get("calibration_applied")),
        "bundle_mission_id": bundle.get("structural_auto_calibration_mission_id"),
        "rerank_executed": len(calibrated) == len(games),
        "ml069_mission_id": ML069,
    }


def audit_structural_auto_calibration_application() -> dict[str, Any]:
    import inspect

    import dashboard.institutional_app as institutional_app
    import dashboard.institutional_ml_calibration_cockpit as cockpit
    from lotoia.ml.structural_auto_calibration import is_structural_auto_calibration_format
    from lotoia.ml.overlap_format_thresholds import classify_overlap_for_format, classify_pair_overlap_level

    per_format = [_audit_format(size) for size in FORMATS_16_23]
    outside = {
        str(size): {
            "gate": is_structural_auto_calibration_format(size),
            "auto_disabled": not is_structural_auto_calibration_format(size),
        }
        for size in OUTSIDE_FORMATS
    }

    cockpit_source = inspect.getsource(cockpit.render_ml_calibration_cockpit)
    observational_source = inspect.getsource(institutional_app._render_central_ml_observational_alerts)

    all_gated = all(row["gate_format_aware"] for row in per_format)
    all_plans = all(row["auto_structural_calibration"] and row["plan_items_count"] > 0 for row in per_format)
    all_prefix = all(row["has_prefix_action"] for row in per_format)
    all_memory = all(
        row["structural_calibration_memory_mission"] == "M-ML-069" and row["per_format_record_present"]
        for row in per_format
    )
    all_applied = all(row["calibration_applied"] and row["bundle_mission_id"] == "M-ML-069" for row in per_format)
    outside_blocked = all(row["gate"] is False and row["auto_disabled"] for row in outside.values())
    central_ml_observability = "_render_structural_auto_calibration_card" in cockpit_source
    no_nested_expander_in_observational = "st.expander(" not in observational_source

    m067_preserved = (
        classify_pair_overlap_level(15, game_size=17) == "atencao"
        and classify_overlap_for_format(17, game_size=17)["level"] == "critico"
    )

    root_causes: list[str] = []
    if not all_gated:
        root_causes.append("gate format-aware falhou para algum formato 16D–23D")
    if not all_plans:
        root_causes.append("plano automático ausente para algum formato com problema estrutural")
    if not all_memory:
        root_causes.append("structural_calibration_memory incompleta")
    if not central_ml_observability:
        root_causes.append("Central ML não expõe card de calibração estrutural automática")
    if not no_nested_expander_in_observational:
        root_causes.append("expander aninhado detectado em observational alerts")

    status = "PASS" if not root_causes and all_applied and outside_blocked and m067_preserved else "WARN"
    if not all_plans or not all_gated:
        status = "FAIL"

    return {
        "mission_id": MISSION_ID,
        "audited_at": datetime.now(UTC).isoformat(),
        "status": status,
        "formats_audited": [f"{size}D" for size in FORMATS_16_23],
        "outside_formats": outside,
        "per_format_results": per_format,
        "central_ml": {
            "structural_auto_calibration_card": central_ml_observability,
            "observational_no_nested_expander": no_nested_expander_in_observational,
        },
        "m_ml_067_preserved": m067_preserved,
        "checks": {
            "all_formats_gate_accepted": all_gated,
            "all_formats_auto_plan": all_plans,
            "all_formats_prefix_action": all_prefix,
            "all_formats_memory_registered": all_memory,
            "all_formats_calibration_applied": all_applied,
            "outside_formats_blocked": outside_blocked,
            "central_ml_observability": central_ml_observability,
            "no_nested_expander": no_nested_expander_in_observational,
        },
        "root_causes_if_missing": root_causes,
        "purge_executed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="M-ML-069-AUDIT-01 structural auto-calibration audit")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = audit_structural_auto_calibration_application()
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"{MISSION_ID}: {report.get('status')}")
        for row in report.get("per_format_results") or []:
            print(
                f"  {row['formato']}: plan={row['plan_items_count']} "
                f"actions={','.join(row['actions_detected'][:4])}"
            )
        if report.get("root_causes_if_missing"):
            for cause in report["root_causes_if_missing"]:
                print(f"  CAUSA: {cause}")
    return 0 if report.get("status") in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
