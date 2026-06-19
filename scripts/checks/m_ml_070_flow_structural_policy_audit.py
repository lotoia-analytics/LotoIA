#!/usr/bin/env python3
"""M-ML-070-FLOW — Auditoria read-only do fluxo operacional da política 15D."""

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

MISSION_ID = "M-ML-070-FLOW"


def audit_structural_policy_15d_flow() -> dict[str, Any]:
    from lotoia.ml.structural_policy_15d import (
        MISSION_ID as ML070,
        analyze_batch_structural_policy_15d,
        build_structural_policy_15d_calibration_plan,
        build_structural_policy_15d_diagnosis,
        resolve_policy_compliance_label,
    )
    from lotoia.ml.ml_operational_verdict import evaluate_ml_operational_verdict
    from lotoia.observability.coverage_evidence_interpreter import get_structural_coverage_evidence

    import dashboard.institutional_app as institutional_app
    import dashboard.institutional_structural_policy_coverage as policy_ui

    with tempfile.TemporaryDirectory(prefix="m-ml-070-flow-audit-") as tmp_dir:
        db_path = Path(tmp_dir) / "flow.db"
        previous = list(range(1, 16))
        numbers = [1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 16, 17, 18, 20, 22]
        analysis = analyze_batch_structural_policy_15d(
            [{"numbers": numbers, "final_card_numbers": numbers}],
            previous_contest_numbers=previous,
            db_path=db_path,
        )
        diagnosis = build_structural_policy_15d_diagnosis(analysis)
        plan = build_structural_policy_15d_calibration_plan(analysis)
        label = resolve_policy_compliance_label(1, 1, [])

    page_source = inspect.getsource(institutional_app._render_cobertura_estrutural_page)
    interpreter_source = inspect.getsource(get_structural_coverage_evidence)
    verdict = evaluate_ml_operational_verdict(
        {
            "policy_compliance_status": "partial",
            "policy_compliance_label": "ATENÇÃO",
            "policy_violations": ["core:abaixo_minimo_2:1"],
            "formatos_analisados": [15],
        }
    )

    checks = {
        "batch_analysis": bool(analysis.get("compliance_label")),
        "diagnosis_issues": bool(diagnosis),
        "calibration_plan": "plan_items" in plan,
        "compliance_label": label == "APROVADO",
        "coverage_ui_block": "render_structural_policy_15d_operational_block" in page_source,
        "coverage_context_builder": callable(policy_ui.build_structural_policy_coverage_context),
        "interpreter_policy_metrics": all(
            token in interpreter_source
            for token in (
                "policy_compliance_status",
                "policy_violations",
                "structural_policy_15d_calibration_plan",
            )
        ),
        "verdict_policy_trigger": "structural_policy_15d_atencao" in list(
            (verdict.get("trace") or {}).get("rule_triggers") or []
        ),
        "mission_base": analysis.get("mission_id") == ML070,
    }

    status = "PASS" if all(checks.values()) else "FAIL"
    return {
        "mission_id": MISSION_ID,
        "audited_at": datetime.now(UTC).isoformat(),
        "status": status,
        "checks": checks,
        "analysis_summary": {
            "compliance_label": analysis.get("compliance_label"),
            "policy_compliance_status": analysis.get("policy_compliance_status"),
            "violations": analysis.get("violations"),
        },
        "purge_executed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="M-ML-070-FLOW structural policy audit")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = audit_structural_policy_15d_flow()
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"{MISSION_ID}: {report.get('status')}")
        for key, value in dict(report.get("checks") or {}).items():
            print(f"  {key}: {value}")
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
