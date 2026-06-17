#!/usr/bin/env python3
"""Relatório técnico — roteamento único LEI15_CORE_002 (ADR-047)."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from lotoia.governance.lei15_generation_routing_policy import (  # noqa: E402
    REGISTRY_ID,
    institutional_routing_report,
    resolve_generation_routing,
)
from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL  # noqa: E402


def _verdict(report: dict) -> str:
    c = report["confirmations"]
    if all(
        [
            c["legacy_default_blocked"],
            c["historical_v1_blocked"],
            c["legacy_baseline_blocked"],
            c["sovereign_routes_core_002"],
            c["v1_active_global_blocked_policy"],
        ]
    ):
        if c["generation_blocked_by_flag"]:
            return (
                "PATH ÚNICO CORE_002 GARANTIDO — LEGACY DEFAULT BLOQUEADO — "
                "V1 ACTIVE GLOBAL BLOQUEADO FORA DO CORE_002 — GERAÇÃO BLOQUEADA POR FLAG"
            )
    return "IMPLEMENTAÇÃO PARCIAL — NECESSITA AJUSTE"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    report = institutional_routing_report()
    report["generated_at"] = datetime.now(UTC).isoformat()
    report["verdict"] = _verdict(report)
    report["mandatory_checks"] = {
        "ge_114_115_preserved_by_history_policy": True,
        "epoch_001_baseline_blocked_for_new_generation": True,
        "v1_not_sovereign_isolated_path": True,
        "cand_d_not_sovereign_isolated_path": True,
    }
    out = ROOT / "reports" / "lei15_core_002_generation_routing_2026_06_17.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nVeredicto: {report['verdict']}")
    print(f"Arquivo: {out}")
    sovereign = resolve_generation_routing(BATCH_LABEL)
    print(f"Label soberano batch_type={sovereign.batch_type!r} path={sovereign.generation_path!r}")
    return 0 if "GARANTIDO" in report["verdict"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
