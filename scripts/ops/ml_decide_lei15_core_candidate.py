#!/usr/bin/env python3
"""Decisão ML assistiva — Núcleo Lei 15 candidato (matriz consolidada).

Agentes: agent_ml + agent_governanca (handoff)
Papel ML: diagnose — interpretável, não preditivo central.

Consolida evidências EPOCH_001 já produzidas. Sem nova geração.

Uso:
  python scripts/ops/ml_decide_lei15_core_candidate.py
  python scripts/ops/ml_decide_lei15_core_candidate.py --json-out reports/ml_lei15_core_candidate_decision_2026_06_17.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from lotoia.governance.lei15_core_six_bases_evaluation import BASE_LABELS_PT, BASE_NAMES
from lotoia.ml.lei15_core_candidate_decision import (
    CANDIDATE_ID,
    CONSOLIDATED_EVIDENCE,
    ML_DECISION_REGISTRY,
    build_ml_decision,
)


def _try_merge_json(path: Path, decision: dict) -> dict:
    """Enriquece com exports ops se existirem (opcional)."""
    if not path.exists():
        return decision
    try:
        extra = json.loads(path.read_text(encoding="utf-8"))
        decision.setdefault("optional_merged_sources", []).append(str(path))
        if "segments" in extra and "v1" in decision.get("consolidated_evidence", {}):
            seg = extra["segments"].get("V1>=13_unique", {})
            if seg:
                decision["consolidated_evidence"]["v1"]["audit_merge"] = {
                    "unique_cards_13_plus": seg.get("unique_cards"),
                    "runs_13_plus": extra.get("summary", {}).get("runs_13_plus"),
                }
    except (json.JSONDecodeError, OSError):
        pass
    return decision


def _print_decision(d: dict) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 88)
    print("DECISÃO ML ASSISTIVA — NÚCLEO LEI 15 CANDIDATO")
    print(f"Registro: {ML_DECISION_REGISTRY} | Candidato proposto: {CANDIDATE_ID}")
    print(f"ML role: {d['ml_role']} | operational_effect: {d['ml_operational_effect']}")
    print("=" * 88)

    print("\n## 1. MATRIZ CONSOLIDADA")
    for k, v in d["matrix_summary"].items():
        print(f"  {k}: {v}")

    print("\n## 2. LEITURA 6 BASES (projeção CAND-002)")
    proj = d["six_bases_reading"]["proposed_cand_002_projected"]
    for name in BASE_NAMES:
        print(f"  {BASE_LABELS_PT[name]}: {proj[name]}")
    print(f"  Balance projetado: {d['six_bases_reading']['projected_balance_score']}")

    arch = d["proposed_architecture"]
    print("\n## 3. ARQUITETURA PROPOSTA")
    for layer in arch["layers"]:
        print(f"  L{layer['order']} {layer['name']}: {layer['role']}")

    print("\n## 4. JUSTIFICATIVA")
    print(f"  {d['decision_rationale']}")

    print("\n## 5. PRESERVAR (V1)")
    for item in arch["preserve_from_v1"]:
        print(f"  • {item}")

    print("\n## 6. INCORPORAR (CAND-D)")
    for item in arch["incorporate_from_cand_d"]:
        print(f"  • {item}")

    print("\n## 7. POLÍTICA DEZENAS CRÍTICAS")
    print(f"  Reforço: {arch['critical_digits']['reinforce']}")
    print(f"  Penalização contextual: {arch['critical_digits']['contextual_discourage']}")

    print("\n## 8. POLÍTICA PREFIXO/SUFIXO")
    print(f"  {arch['prefix_suffix_policy']}")

    print("\n## 9. ANTI-CLONE")
    print(f"  {arch['anti_clone_policy']}")

    print("\n## 10. REDUNDÂNCIA")
    print(f"  {arch['redundancy_policy']}")

    print("\n## 11. RISCOS")
    for r in d["risks_known"]:
        print(f"  • {r}")

    print("\n## 12. CONDIÇÕES TESTE LIMPO 15D")
    for c in d["clean_15d_test_minimum_conditions"]:
        print(f"  • {c}")

    print("\n## 13. 15A")
    print(f"  {d['lei15a_recommendation']['verdict']}")
    print(f"  {d['lei15a_recommendation']['rationale']}")

    print("\n## 14. VEREDICTO FINAL")
    print(f"  {d['final_verdict']}")
    print(f"  Governança: {d['governance_status']}")
    print(f"  Próximo agente: {d['governance_handoff']['next_agent']} → {d['governance_handoff']['action']}")
    print("=" * 88)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json-out",
        default="reports/ml_lei15_core_candidate_decision_2026_06_17.json",
    )
    args = parser.parse_args()

    decision = build_ml_decision(CONSOLIDATED_EVIDENCE)
    decision = _try_merge_json(ROOT / "reports/lei15_v1_strong_cards_6_bases_audit_2026_06_17.json", decision)
    decision = _try_merge_json(ROOT / "reports/lei15_core_6_bases_comparative_2026_06_17.json", decision)

    _print_decision(decision)

    out = Path(args.json_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(decision, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nJSON: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
