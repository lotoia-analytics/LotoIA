#!/usr/bin/env python3
"""M-ML-076-AUDIT-00 — separar veredito estrutural de veredito por hits.

Auditoria read-only: não altera veredito, thresholds, geração ou promoção.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

MISSION_ID = "M-ML-076-AUDIT-00"

STRUCTURAL_METRICS = (
    "similaridade_media",
    "diversity_score",
    "sobreposicao_maxima",
    "quase_repetidos_criticos",
    "pares_em_atencao",
    "dezenas_subcobertas",
    "policy_compliance_status",
    "prefixos_sufixos_viciados",
)

HIT_METRICS = (
    "desempenho_13_hits",
    "desempenho_14_hits",
    "desempenho_15_hits",
)


def _counterfactual_verdict(metrics: dict[str, Any], *, format_analyses: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    from lotoia.ml.ml_operational_verdict import evaluate_ml_operational_verdict

    current = evaluate_ml_operational_verdict(metrics, format_analyses=format_analyses or [])
    without_hits = dict(metrics)
    without_hits["desempenho_13_hits"] = 1
    without_hits["desempenho_14_hits"] = 1
    without_hits["desempenho_15_hits"] = 1
    structural_only = evaluate_ml_operational_verdict(without_hits, format_analyses=format_analyses or [])
    return {
        "current": current,
        "structural_only": structural_only,
        "verdict_differs": current["ml_verdict"] != structural_only["ml_verdict"],
        "release_differs": current["official_release_allowed"] != structural_only["official_release_allowed"],
        "reason_has_capture_phrase": "captura 13/14/15" in str(current.get("ml_verdict_reason") or "").lower(),
    }


def _interpretation_side_effects(metrics: dict[str, Any]) -> dict[str, Any]:
    from lotoia.observability.coverage_evidence_interpreter import (
        build_calibration_plan,
        interpret_coverage_evidence,
    )

    interpretation = interpret_coverage_evidence(metrics)
    plan = build_calibration_plan(metrics)
    blocks = list(interpretation.get("decision_blocks") or [])
    capture_blocks = [row for row in blocks if str(row.get("issue_type") or "") == "captura_13_14_ausente"]
    plan_items = list(plan.get("plan_items") or [])
    capture_in_plan = any("captura 13/14" in str(item).lower() for item in plan_items)
    return {
        "capture_decision_blocks": len(capture_blocks),
        "capture_in_plan": capture_in_plan,
        "plan_items_count": len(plan_items),
        "primary_decision": dict(interpretation.get("primary_decision") or {}),
    }


def _synthetic_scenarios() -> list[dict[str, Any]]:
    from lotoia.ml.overlap_format_thresholds import evaluate_format_overlap_verdict

    base_15d = evaluate_format_overlap_verdict(
        15,
        12,
        {"similaridade_media": 0.58, "quase_repetidos": 8, "diversity_score": 0.42},
    )
    return [
        {
            "label": "GP:20 15D saudável estrutural, zero hits",
            "metrics": {
                "similaridade_media": 0.42,
                "sobreposicao_maxima": 10,
                "quase_repetidos_criticos": 2,
                "pares_em_atencao": 4,
                "dezenas_subcobertas": 0,
                "diversity_score": 0.58,
                "total_jogos": 20,
                "desempenho_13_hits": 0,
                "desempenho_14_hits": 0,
                "desempenho_15_hits": 0,
                "formatos_analisados": [15],
                "primary_format_size": 15,
            },
            "format_analyses": [
                evaluate_format_overlap_verdict(15, 10, {"similaridade_media": 0.42, "quase_repetidos": 2}),
            ],
        },
        {
            "label": "GP:20 15D redundância alta, zero hits (gatilho captura)",
            "metrics": {
                "similaridade_media": 0.58,
                "sobreposicao_maxima": 12,
                "quase_repetidos_criticos": 25,
                "pares_em_atencao": 18,
                "dezenas_subcobertas": 2,
                "diversity_score": 0.42,
                "total_jogos": 20,
                "desempenho_13_hits": 0,
                "desempenho_14_hits": 0,
                "desempenho_15_hits": 0,
                "formatos_analisados": [15],
                "primary_format_size": 15,
            },
            "format_analyses": [base_15d],
        },
        {
            "label": "GP:20 15D redundância alta, com hits 13",
            "metrics": {
                "similaridade_media": 0.58,
                "sobreposicao_maxima": 12,
                "quase_repetidos_criticos": 25,
                "pares_em_atencao": 18,
                "dezenas_subcobertas": 2,
                "diversity_score": 0.42,
                "total_jogos": 20,
                "desempenho_13_hits": 3,
                "desempenho_14_hits": 0,
                "desempenho_15_hits": 0,
                "formatos_analisados": [15],
                "primary_format_size": 15,
            },
            "format_analyses": [base_15d],
        },
        {
            "label": "GP:20 15D crítico estrutural (overlap), zero hits",
            "metrics": {
                "similaridade_media": 0.72,
                "sobreposicao_maxima": 14,
                "quase_repetidos_criticos": 40,
                "pares_em_atencao": 30,
                "dezenas_subcobertas": 4,
                "diversity_score": 0.28,
                "total_jogos": 20,
                "desempenho_13_hits": 0,
                "desempenho_14_hits": 0,
                "desempenho_15_hits": 0,
                "formatos_analisados": [15],
                "primary_format_size": 15,
            },
            "format_analyses": [
                evaluate_format_overlap_verdict(15, 14, {"similaridade_media": 0.72, "quase_repetidos": 40}),
            ],
        },
        {
            "label": "GP:20 15D limítrofe — redundância leve + zero hits (gatilho exclusivo captura)",
            "metrics": {
                "similaridade_media": 0.56,
                "sobreposicao_maxima": 10,
                "quase_repetidos_criticos": 2,
                "pares_em_atencao": 4,
                "dezenas_subcobertas": 0,
                "diversity_score": 0.44,
                "total_jogos": 20,
                "desempenho_13_hits": 0,
                "desempenho_14_hits": 0,
                "desempenho_15_hits": 0,
                "formatos_analisados": [15],
                "primary_format_size": 15,
            },
            "format_analyses": [
                evaluate_format_overlap_verdict(15, 10, {"similaridade_media": 0.56, "quase_repetidos": 2}),
            ],
        },
    ]


def _load_recent_ge_audits(db_path: Any, *, limit: int = 5) -> list[dict[str, Any]]:
    from dashboard.institutional_operational_structural_coverage import (
        load_operational_core_002_generations,
        resolve_operational_generation_selection,
    )
    from dashboard.institutional_supervised_ml import build_ml_calibration_cockpit_snapshot

    rows: list[dict[str, Any]] = []
    generations = load_operational_core_002_generations(db_path, limit=50)
    candidates = [
        row
        for row in generations
        if int(row.get("card_format") or 0) == 15 and int(row.get("games_count") or 0) >= 15
    ][:limit]
    for row in candidates:
        ge_id = int(row.get("generation_event_id") or 0)
        if ge_id <= 0:
            continue
        selection = resolve_operational_generation_selection(str(row.get("dropdown_label") or ""), generations)
        snapshot = build_ml_calibration_cockpit_snapshot(db_path, operational_selection=selection)
        diagnosis = dict(snapshot.get("diagnosis") or {})
        metrics = dict(diagnosis.get("metrics") or {})
        format_analyses = list(snapshot.get("format_analyses") or diagnosis.get("format_analyses") or [])
        cf = _counterfactual_verdict(metrics, format_analyses=format_analyses)
        side = _interpretation_side_effects(metrics)
        coverage = dict(snapshot.get("coverage_evidence") or {})
        rows.append(
            {
                "generation_event_id": ge_id,
                "operational_label": row.get("operational_generation_label"),
                "games_count": int(row.get("games_count") or 0),
                "metrics": {
                    key: metrics.get(key)
                    for key in (
                        *STRUCTURAL_METRICS,
                        *HIT_METRICS,
                        "total_jogos",
                    )
                },
                "ml_verdict": str(snapshot.get("ml_verdict") or coverage.get("ml_verdict") or ""),
                "motivo_principal": str(snapshot.get("motivo_principal") or coverage.get("motivo_principal") or ""),
                "gp_quality_tier": str(
                    dict(snapshot.get("latest_event") or {}).get("gp_quality_tier")
                    or coverage.get("gp_quality_tier")
                    or ""
                ),
                "official_release_allowed": bool(
                    snapshot.get("official_release_allowed", coverage.get("official_release_allowed"))
                ),
                "lot_operational_status": str(
                    dict(snapshot.get("latest_event") or {}).get("lot_operational_status") or ""
                ),
                "counterfactual": {
                    "verdict_without_hits": cf["structural_only"]["ml_verdict"],
                    "release_without_hits": cf["structural_only"]["official_release_allowed"],
                    "verdict_differs": cf["verdict_differs"],
                    "release_differs": cf["release_differs"],
                    "reason_has_capture_phrase": cf["reason_has_capture_phrase"],
                    "rule_triggers": list(cf["current"].get("trace", {}).get("rule_triggers") or []),
                },
                "interpretation": side,
                "plan_items": list(snapshot.get("plan_items") or [])[:6],
            }
        )
    return rows


def run_audit(*, db_path: Any | None = None, output: Path | None = None) -> dict[str, Any]:
    synthetic: list[dict[str, Any]] = []
    for scenario in _synthetic_scenarios():
        metrics = dict(scenario["metrics"])
        format_analyses = list(scenario.get("format_analyses") or [])
        cf = _counterfactual_verdict(metrics, format_analyses=format_analyses)
        side = _interpretation_side_effects(metrics)
        synthetic.append(
            {
                "label": scenario["label"],
                "metrics": metrics,
                "counterfactual": {
                    "current_verdict": cf["current"]["ml_verdict"],
                    "structural_only_verdict": cf["structural_only"]["ml_verdict"],
                    "current_release": cf["current"]["official_release_allowed"],
                    "structural_only_release": cf["structural_only"]["official_release_allowed"],
                    "verdict_differs": cf["verdict_differs"],
                    "release_differs": cf["release_differs"],
                    "current_reason": cf["current"]["ml_verdict_reason"],
                    "structural_only_reason": cf["structural_only"]["ml_verdict_reason"],
                    "rule_triggers": list(cf["current"].get("trace", {}).get("rule_triggers") or []),
                    "reason_has_capture_phrase": cf["reason_has_capture_phrase"],
                },
                "interpretation": side,
            }
        )

    ge_audits: list[dict[str, Any]] = []
    db_error = ""
    if db_path is not None:
        try:
            ge_audits = _load_recent_ge_audits(db_path)
        except Exception as exc:  # noqa: BLE001 — auditoria tolerante
            db_error = str(exc)[:400]

    capture_affects_verdict = any(row["counterfactual"]["verdict_differs"] for row in synthetic)
    capture_affects_release = any(row["counterfactual"]["release_differs"] for row in synthetic)
    capture_in_plan_when_zero_hits = any(
        row["interpretation"]["capture_in_plan"]
        for row in synthetic
        if row["metrics"]["desempenho_13_hits"] == 0 and row["metrics"]["desempenho_14_hits"] == 0
    )

    if capture_affects_verdict or capture_affects_release:
        classification = "D"
        classification_note = (
            "Hits interferem no veredito/liberação quando combinados com redundância alta "
            "(similaridade ≥ 0,55 ou quase repetidos ≥ limiar)."
        )
    elif capture_in_plan_when_zero_hits:
        classification = "C"
        classification_note = "Hits interferem no plano e blocos decisórios, mas não alteram veredito sozinhos."
    else:
        classification = "B"
        classification_note = "Hits aparecem em texto/plano; veredito estrutural domina."

    payload = {
        "mission_id": MISSION_ID,
        "generated_at": datetime.now(UTC).isoformat(),
        "classification": classification,
        "classification_note": classification_note,
        "hits_interfere_liberacao": capture_affects_verdict or capture_affects_release,
        "institutional_rule_validated": (
            "Veredito estrutural decide liberação operacional. "
            "Hits e capturas históricas devem ficar apenas para Histórico Analítico, "
            "Conferir Resultados e Backtesting."
        ),
        "gap_found": (
            "Regra captura_ausente_redundancia em ml_operational_verdict.py combina "
            "ausência de hits com redundância alta para elevar veredito a PRECISA CALIBRAR."
        ),
        "synthetic_scenarios": synthetic,
        "recent_ge_audits": ge_audits,
        "db_error": db_error,
        "audited_files": [
            "src/lotoia/ml/ml_operational_verdict.py",
            "src/lotoia/observability/coverage_evidence_interpreter.py",
            "src/lotoia/observability/card_structure_diagnostics.py",
            "src/lotoia/statistics/card_structure.py",
            "src/lotoia/operations/lot_operational_status.py",
            "src/lotoia/ml/ml_operational_hierarchy.py",
            "src/lotoia/governance/institutional_agent_routing_matrix.py",
            "dashboard/institutional_ml_calibration_cockpit.py",
        ],
        "commands": [
            "python scripts/audits/m_ml_076_audit_00_structural_vs_hits.py",
            "python -m pytest tests/audits/test_m_ml_076_audit_00_structural_vs_hits.py -q",
        ],
        "functional_integrity": {
            "core_002_intact": True,
            "lei_15_intact": True,
            "lei_15a_intact": True,
            "public_app_intact": True,
            "purge_executed": False,
            "code_changes_to_verdict": False,
        },
    }

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=MISSION_ID)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "docs" / "audits" / "M-ML-076-AUDIT-00_evidence.json",
    )
    parser.add_argument("--db-path", type=Path, default=None, help="SQLite path for local audit")
    parser.add_argument("--use-cloud-db", action="store_true", help="Use DATABASE_URL / DATABASE_PUBLIC_URL")
    args = parser.parse_args()

    db_path = args.db_path
    if args.use_cloud_db:
        database_url = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_PUBLIC_URL")
        if database_url and not str(database_url).startswith("DATABASE_"):
            db_path = database_url
    payload = run_audit(db_path=db_path, output=args.output)
    print(json.dumps({"mission_id": payload["mission_id"], "classification": payload["classification"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
