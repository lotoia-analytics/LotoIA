"""M-GOV-AGENTS-002 — Matriz executável de roteamento dos agentes institucionais."""

from __future__ import annotations

from typing import Any

from dashboard.institutional_build import BUILD_MARKER
from lotoia.governance.institutional_agent_routing_matrix import (
    AGENT_ESTATISTICO,
    AGENT_GERACAO,
    AGENT_ML,
    MATRIX_VERSION,
    MISSION_ID,
    OFFICIAL_AGENTS,
    build_institutional_agent_routing_matrix_memory,
    enrich_calibration_plan,
    enrich_decision_block,
    enrich_hierarchy_bundle,
    resolve_agent_routing,
    summarize_responsible_agents,
)
from lotoia.ml.ml_operational_hierarchy import (
    STAGE_CONFORMITY,
    STAGE_DIVERSITY,
    build_ml_operational_hierarchy_trace,
    finalize_ml_operational_hierarchy_validation,
)
from lotoia.observability.coverage_evidence_interpreter import (
    _build_decision_block,
    interpret_coverage_evidence,
)


def test_official_agents_catalog() -> None:
    memory = build_institutional_agent_routing_matrix_memory()
    assert memory["mission_id"] == MISSION_ID
    assert memory["agent_routing_matrix_version"] == MATRIX_VERSION
    assert len(OFFICIAL_AGENTS) == 8
    assert "agent_core" not in OFFICIAL_AGENTS


def test_resolve_agent_routing_by_issue_and_stage() -> None:
    diversity = resolve_agent_routing(issue_type="diversidade_baixa")
    assert diversity["responsible_agent"] == AGENT_ESTATISTICO

    conformity = resolve_agent_routing(stage_id=STAGE_CONFORMITY)
    assert conformity["responsible_agent"] == AGENT_GERACAO

    calibration = resolve_agent_routing(corrective_action="calibracao_estrutural_multidezena")
    assert calibration["responsible_agent"] == AGENT_ML


def test_enrich_decision_block_adds_responsible_agent() -> None:
    block = enrich_decision_block(
        {
            "issue_type": "sobreposicao_maxima_elevada",
            "problema_detectado": "Overlap alto",
            "trace": {},
        }
    )
    assert block["responsible_agent"] == AGENT_ESTATISTICO
    assert block["agent_routing_matrix_version"] == MATRIX_VERSION
    assert block["trace"]["responsible_agent"] == AGENT_ESTATISTICO


def test_build_decision_block_interpreter_integration() -> None:
    block = _build_decision_block(
        issue_type="pool_estrutural_insuficiente",
        problema_detectado="Pool insuficiente",
        evidencia="n=80",
        causa_provavel="expansao",
        acao_recomendada="expandir pool",
        impacto_esperado="conformidade",
        severidade="alta",
    )
    assert block["responsible_agent"] == AGENT_GERACAO


def test_enrich_calibration_plan_assigns_agents() -> None:
    plan = enrich_calibration_plan(
        {
            "plan_items": [
                "Elevar diversidade mínima da saída",
                "Reranquear candidatos com sobreposição elevada",
            ]
        }
    )
    assignments = list(plan.get("agent_assignments") or [])
    assert len(assignments) == 2
    assert all(row.get("responsible_agent") for row in assignments)
    assert plan.get("primary_responsible_agent") in OFFICIAL_AGENTS


def test_enrich_hierarchy_bundle_stage_agents() -> None:
    bundle = enrich_hierarchy_bundle(
        {
            "gp_closure_allowed": False,
            "current_stage": STAGE_DIVERSITY,
            "stage_results": {
                STAGE_CONFORMITY: {"passed": True, "stage_id": STAGE_CONFORMITY},
                STAGE_DIVERSITY: {
                    "passed": False,
                    "stage_id": STAGE_DIVERSITY,
                    "corrective_actions": ["rerank_diversidade"],
                },
            },
        }
    )
    stages = dict(bundle.get("stage_results") or {})
    assert stages[STAGE_CONFORMITY]["responsible_agent"] == AGENT_GERACAO
    assert stages[STAGE_DIVERSITY]["responsible_agent"] == AGENT_ESTATISTICO
    assert bundle.get("blocking_responsible_agent") == AGENT_ESTATISTICO
    assert bundle.get("agent_routing_matrix_version") == MATRIX_VERSION


def test_finalize_hierarchy_includes_agent_routing() -> None:
    finalized = finalize_ml_operational_hierarchy_validation(
        {
            "gp_closure_allowed": True,
            "stage_results": {
                STAGE_CONFORMITY: {"passed": True, "stage_id": STAGE_CONFORMITY},
            },
        },
        final_gp=[{"numbers": list(range(1, 16))}],
    )
    trace = build_ml_operational_hierarchy_trace(finalized)
    assert trace.get("agent_routing_matrix_version") == MATRIX_VERSION
    assert STAGE_CONFORMITY in dict(trace.get("stage_results") or {})


def test_interpret_coverage_evidence_agent_summary() -> None:
    metrics: dict[str, Any] = {
        "similaridade_media": 0.72,
        "sobreposicao_maxima": 14,
        "quase_repetidos_criticos": 8,
        "diversity_score": 0.42,
        "dezenas_subcobertas": 3,
        "dezenas_subcobertas_list": ["03", "11", "22"],
        "prefixo_mais_gerado": "01-02-03",
        "sufixo_mais_gerado": "23-24-25",
        "prefixo_viciado": True,
        "total_jogos": 20,
        "calibration_applied": False,
    }
    interpretation = interpret_coverage_evidence(metrics)
    assert interpretation.get("agent_routing_mission_id") == MISSION_ID
    assert interpretation.get("primary_responsible_agent")
    blocks = list(interpretation.get("decision_blocks") or [])
    assert blocks
    assert all(block.get("responsible_agent") for block in blocks)
    summary = summarize_responsible_agents(
        decision_blocks=blocks,
        calibration_plan=interpretation.get("calibration_plan"),
    )
    assert summary.get("primary_responsible_agent")


def test_build_marker_v63() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v69"
