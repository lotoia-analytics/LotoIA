#!/usr/bin/env python3
"""CLI read-only — M-ML-074-DIAG-00 investigação causal GP 15D."""

from __future__ import annotations

import argparse
import json
import sys

from lotoia.ml.gp_delivery_causal_diagnostic import build_gp_delivery_causal_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="M-ML-074-DIAG-00 — causal GP 15D delivery")
    parser.add_argument("--json", action="store_true", help="Emitir relatório JSON")
    args = parser.parse_args(argv)

    report = build_gp_delivery_causal_report()

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print(f"=== {report['mission_id']} — Investigação causal GP 15D ===\n")
    print(f"Pergunta: {report['central_question']}\n")
    print(f"Resposta: {report['answer_summary']}\n")
    print("Ponto de divergência:")
    div = report["divergence_point"]
    print(f"  {div['file']}:{div['lines']} — {div['condition']}")
    print(f"  Efeito: {div['effect']}\n")
    print("Recuperação interna:")
    rec = report["recovery_attempts"]
    print(f"  Existe: {rec['exists']} | Máx/etapa: {rec['max_per_stage']} | Etapas: {rec['stages']}\n")
    print("Fluxo real:")
    for step in report["flow_steps"]:
        print(f"  {step['step']}. [{step['component']}] {step['action']}")
    print()
    print(f"Classificação: {report['classification']} — {report['classification_label']}")
    print(f"Próxima missão: {report['recommended_next_mission']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
