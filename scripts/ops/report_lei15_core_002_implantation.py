#!/usr/bin/env python3
"""Relatório read-only — implantação Núcleo Soberano LEI15_CORE_002.

Não executa geração, piloto, teste de resultado nem alterações operacionais.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lotoia.governance.analysis_batch_labels import infer_batch_type  # noqa: E402
from lotoia.governance.lei15_core_002_sovereign import (  # noqa: E402
    BATCH_LABEL as SOVEREIGN_LABEL,
    institutional_status_report,
    is_generation_enabled,
    is_sovereign_implanted,
)
from lotoia.governance.lei15_legacy_core_baseline import (  # noqa: E402
    LEGACY_CORE_BASELINE_LABEL,
    SOVEREIGN_CORE_002_ID,
)

GOV_MODULE = ROOT / "src/lotoia/governance/lei15_core_002_sovereign.py"
GEN_MODULE = ROOT / "src/lotoia/generation/lei15_core_002.py"
GENERATOR = ROOT / "src/lotoia/generator/basic_generator.py"
ADR = ROOT / "docs/adr/ADR-046-NUCLEO-LEI15-CANDIDATE-002.md"
REPORT_DOC = ROOT / "docs/governance/RELATORIO_LEI15_CORE_002_IMPLANTACAO_2026_06_17.md"


def _verdict(checks: dict[str, bool]) -> str:
    if all(checks.values()):
        return "NÚCLEO SOBERANO LEI 15 IMPLANTADO"
    if any(checks.get(k) for k in ("governance_module", "generation_module", "generator_hook")) and not all(
        checks.values()
    ):
        return "IMPLANTAÇÃO PARCIAL — NECESSITA AJUSTE"
    if checks.get("generation_executed") or checks.get("result_test_executed"):
        return "RISCO DE GOVERNANÇA IDENTIFICADO"
    return "IMPLANTAÇÃO BLOQUEADA POR CONFLITO"


def build_report() -> dict:
    status = institutional_status_report()
    checks = {
        "governance_module": GOV_MODULE.is_file(),
        "generation_module": GEN_MODULE.is_file(),
        "generator_hook": GENERATOR.is_file() and "should_apply_core_002" in GENERATOR.read_text(encoding="utf-8"),
        "adr_updated": ADR.is_file() and "NÚCLEO SOBERANO IMPLANTADO" in ADR.read_text(encoding="utf-8"),
        "label_registered": infer_batch_type(SOVEREIGN_LABEL) == "LEI15_CORE_002_SOVEREIGN",
        "sovereign_implanted": is_sovereign_implanted(),
        "generation_blocked": not is_generation_enabled(),
        "generation_executed": False,
        "pilot_15d_executed": False,
        "result_test_executed": False,
        "active_public_blocked": status["active_public_blocked"],
        "lei15a_blocked": not status["lei15a"]["open_15a"],
        "legacy_core_frozen": status["legacy_core"]["status"] == "baseline_congelado_read_only",
        "future_execution_adm_panel": status["future_execution"] == "Painel ADM 100% funcional",
    }
    return {
        "registry": "RELATORIO_LEI15_CORE_002_IMPLANTACAO_2026_06_17",
        "generated_at": datetime.now(UTC).isoformat(),
        "core_id": SOVEREIGN_CORE_002_ID,
        "batch_label": SOVEREIGN_LABEL,
        "legacy_baseline_label": LEGACY_CORE_BASELINE_LABEL,
        "verdict": _verdict(checks),
        "confirmations": {
            "no_generation_executed": not checks["generation_executed"],
            "no_result_test_executed": not checks["result_test_executed"],
            "no_pilot_15d": not checks["pilot_15d_executed"],
            "active_public_blocked": checks["active_public_blocked"],
            "lei15a_blocked": checks["lei15a_blocked"],
            "legacy_core_read_only": checks["legacy_core_frozen"],
            "future_execution_requires_adm_panel": checks["future_execution_adm_panel"],
        },
        "architecture_layers": [
            "generation_cand_d",
            "v1_selection_compose",
            "v1_strong_shield",
            "anti_clone_gp",
            "critical_digit_layer",
        ],
        "required_payload_fields": [
            "lei15_core_002_applied",
            "sovereign_core_status",
            "candidate_origin_label",
            "generation_cand_d_applied",
            "v1_selection_compose_applied",
            "v1_strong_shield_applied",
            "anti_clone_gp_applied",
            "critical_digit_layer_applied",
            "perfil_origem_real",
            "perfil_label_final",
            "prefix_signature",
            "suffix_signature",
            "structural_bias_score",
            "relabeling_applied",
            "relabeling_reason",
        ],
        "checks": checks,
        "institutional_status": status,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    report = build_report()
    out_dir = ROOT / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "lei15_core_002_implantation_2026_06_17.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nVeredicto: {report['verdict']}")
    print(f"Arquivo: {out_path}")
    if REPORT_DOC.is_file():
        print(f"Documento: {REPORT_DOC}")
    return 0 if report["verdict"] == "NÚCLEO SOBERANO LEI 15 IMPLANTADO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
