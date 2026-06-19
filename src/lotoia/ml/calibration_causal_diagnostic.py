"""Diagnóstico causal read-only — impacto da calibração na geração seguinte (M-ML-075-DIAG-00)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

MISSION_ID = "M-ML-075-DIAG-00"
DIAG_VERSION = "M-ML-075-DIAG-00-v1"
CLASSIFICATION = "D"
CLASSIFICATION_LABEL = "Calibração desconectada — plano não chega ao gerador na geração seguinte"

RECOMMENDED_NEXT_MISSION = (
    "M-ML-075-FIX-01 — Persistir e reler plano autorizado do PostgreSQL na geração N+1 "
    "(agent_ml + agent_dados + agent_plataforma); retroalimentar M-STAT-002 / M-ML-072 "
    "com parametros_sugeridos"
)

CALIBRATION_FLOW_STEPS: tuple[dict[str, str], ...] = (
    {
        "step": "1",
        "component": "Cobertura Estrutural + coverage_evidence_interpreter",
        "action": "build_calibration_plan() → plan_items + parametros_sugeridos",
        "evidence": "src/lotoia/observability/coverage_evidence_interpreter.py — build_calibration_plan",
    },
    {
        "step": "2",
        "component": "Central ML Cockpit",
        "action": "Operador autoriza / 'Aplicar na próxima geração' → session_state",
        "evidence": "dashboard/institutional_ml_calibration_cockpit.py — SESSION_PERSIST",
    },
    {
        "step": "3",
        "component": "resolve_authorized_calibration_plan",
        "action": "Lê cockpit_apply_next_generation + calibration_authorized da sessão Streamlit",
        "evidence": "dashboard/institutional_supervised_ml.py — resolve_authorized_calibration_plan",
    },
    {
        "step": "4",
        "component": "_invoke_sovereign_adm_generate_best_games",
        "action": "Passa calibration_plan para generate_best_games (somente se sessão ativa)",
        "evidence": "dashboard/institutional_app.py — _invoke_sovereign_adm_generate_best_games",
    },
    {
        "step": "5",
        "component": "generate_best_games",
        "action": "Hierarquia M-ML-073 / recuperação M-ML-074 / pré-final M-ML-071",
        "evidence": "src/lotoia/generator/basic_generator.py — execute_ml_operational_hierarchy",
    },
    {
        "step": "6",
        "component": "apply_pre_final_pool_ml_calibration",
        "action": "apply_supervised_output_calibration(plan_params se authorized=True)",
        "evidence": "src/lotoia/ml/pre_final_pool_ml_calibration.py",
    },
    {
        "step": "7",
        "component": "Persistência generation_events",
        "action": "cockpit_calibration_workflow snapshot em context_json (histórico)",
        "evidence": "dashboard/institutional_app.py — _persist_clean_law15_generation_history",
    },
    {
        "step": "8",
        "component": "Geração N+1",
        "action": "NÃO relê plano do PostgreSQL — exige nova sessão cockpit",
        "evidence": "resolve_authorized_calibration_plan — ausência de loader DB",
    },
)

COMPONENT_CALIBRATION_TABLE: tuple[dict[str, str], ...] = (
    {
        "item": "penalidade de similaridade",
        "recomendado": "redundancy_penalty_boost ≥ 1.2 (build_calibration_plan)",
        "persistido": "parametros_sugeridos em cockpit_calibration_workflow / calibration_bundle",
        "lido_proxima_geracao": "não — somente st.session_state se operador repetir cockpit",
        "aplicado_gerador": "sim intra-geração se plan.authorized=True (M-ML-071)",
        "efeito_observado": "reordena profile_score; similaridade estrutural do pool inalterada se cartões iguais",
        "evidence": "supervised_output_calibration.py — _plan_scale(redundancy_penalty_boost)",
    },
    {
        "item": "penalidade de sobreposição",
        "recomendado": "max_overlap_penalty ≥ 1.15",
        "persistido": "parametros_sugeridos.max_overlap_penalty",
        "lido_proxima_geracao": "não (sessão)",
        "aplicado_gerador": "sim intra-geração com plano autorizado",
        "efeito_observado": "penalidade em jogos com overlap alto; não gera cartões novos",
        "evidence": "supervised_output_calibration.py L216-L218",
    },
    {
        "item": "penalidade trinca/prefixo/sufixo",
        "recomendado": "prefix_penalty / suffix_penalty + prefixo_alvo / sufixo_alvo",
        "persistido": "parametros_sugeridos + plan_items texto",
        "lido_proxima_geracao": "não (sessão)",
        "aplicado_gerador": "sim se estrutura detectada em diagnostics.issues",
        "efeito_observado": "penalidade pontual; M-STAT-002 não recebe calibration_plan",
        "evidence": "diverse_top_slice_selection.py — sem parâmetro calibration_plan",
    },
    {
        "item": "reforço dezenas subcobertas",
        "recomendado": "missing_numbers_boost + dezenas_subcobertas",
        "persistido": "parametros_sugeridos",
        "lido_proxima_geracao": "não (sessão)",
        "aplicado_gerador": "boost em jogos que contêm dezena subcoberta",
        "efeito_observado": "fraco se pool não contém dezenas alvo no top slice",
        "evidence": "supervised_output_calibration.py L250-L269",
    },
    {
        "item": "rerank diversidade",
        "recomendado": "diversity_floor_boost + rerank_before_persist",
        "persistido": "parametros_sugeridos (texto plan_items)",
        "lido_proxima_geracao": "não",
        "aplicado_gerador": "diversity_floor_boost só se scale>1 e plan autorizado",
        "efeito_observado": "não altera métricas estruturais do pool (score-only)",
        "evidence": "pre_final_pool_ml_calibration.py — metrics_before/after sobre mesmos cartões",
    },
    {
        "item": "seleção top slice (M-STAT-002)",
        "recomendado": "implícito em plano diversidade",
        "persistido": "diverse_top_slice_m_stat_002 bundle pós-geração",
        "lido_proxima_geracao": "não",
        "aplicado_gerador": "apply_diverse_top_slice_pre_gp sem calibration_plan",
        "efeito_observado": "swaps estruturais intra-geração; sem memória cross-gen",
        "evidence": "ml_operational_hierarchy.py L642-L648",
    },
    {
        "item": "recuperação pré-GP (M-ML-074)",
        "recomendado": "escala parametros_sugeridos em falha de diversidade/cobertura",
        "persistido": "pre_gp_recovery bundle",
        "lido_proxima_geracao": "não",
        "aplicado_gerador": "sim intra-geração com calibration_plan da sessão",
        "efeito_observado": "até 5 tentativas/etapa; não persiste plano para N+1",
        "evidence": "pre_gp_deterministic_recovery.py — _escalate_calibration_plan",
    },
    {
        "item": "classificação M-ML-073b",
        "recomendado": "gp_quality_tier observacional",
        "persistido": "ml_hierarchy_bundle / gp_quality_tier em context_json",
        "lido_proxima_geracao": "não — sem loader automático",
        "aplicado_gerador": "classifica REPROVADO mas entrega GP (ADR-048)",
        "efeito_observado": "reprovação não retroalimenta parâmetros na geração seguinte",
        "evidence": "ml_operational_hierarchy.py — build_gp_quality_classification",
    },
)


def _synthetic_high_redundancy_pool(size: int = 30) -> list[dict[str, Any]]:
    """Pool sintético com alta similaridade — reproduz cenário operacional reportado."""
    base = sorted(list(range(1, 16)))
    games: list[dict[str, Any]] = []
    for index in range(size):
        numbers = list(base)
        if index % 3 == 1:
            numbers[0] = 16
            numbers[1] = 17
        elif index % 3 == 2:
            numbers[-1] = 25
            numbers[-2] = 24
        games.append(
            {
                "numbers": sorted(numbers),
                "final_card_numbers": sorted(numbers),
                "profile_score": 50.0 - index * 0.1,
                "score_ml": 45.0,
            }
        )
    return games


def _replay_calibration_penalty_experiment() -> dict[str, Any]:
    """Experimento controlado: calibração base vs plano autorizado (mesmo pool)."""
    import tempfile
    from pathlib import Path

    from lotoia.ml.supervised_output_calibration import apply_supervised_output_calibration
    from lotoia.observability.coverage_evidence_interpreter import build_calibration_plan

    games = _synthetic_high_redundancy_pool()
    metrics_operational = {
        "similaridade_media": 0.6663,
        "sobreposicao_maxima": 14,
        "quase_repetidos": 25,
        "diversity_score": 0.3337,
        "dezenas_subcobertas": 3,
        "dezenas_subcobertas_list": ["07", "11", "23"],
        "prefixo_viciado": True,
        "sufixo_viciado": True,
        "prefixo_mais_gerado": "01-02-03",
        "sufixo_mais_gerado": "23-24-25",
        "total_jogos": 20,
    }
    plan = build_calibration_plan(metrics_operational)
    authorized = {**plan, "authorized": True, "operador": "diag_replay", "timestamp": "diag"}

    with tempfile.TemporaryDirectory(prefix="m_ml_075_diag_") as tmp_dir:
        db_path = Path(tmp_dir) / "policy.db"
        event_ctx = {"db_path": db_path, "batch_label": "STRUCT_LEI15_CORE_CANDIDATE_002_15D_001"}
        _, bundle_base = apply_supervised_output_calibration(
            deepcopy(games),
            game_size=15,
            ml_enabled=True,
            calibration_plan=None,
            event_context=event_ctx,
        )
        _, bundle_auth = apply_supervised_output_calibration(
            deepcopy(games),
            game_size=15,
            ml_enabled=True,
            calibration_plan=authorized,
            event_context=event_ctx,
        )

    base_pen = float(bundle_base.get("redundancy_penalty", 0) or 0)
    auth_pen = float(bundle_auth.get("redundancy_penalty", 0) or 0)
    base_prefix = int(bundle_base.get("prefix_penalty", 0) or 0)
    auth_prefix = int(bundle_auth.get("prefix_penalty", 0) or 0)
    base_boost = int(bundle_base.get("missing_numbers_boost", 0) or 0)
    auth_boost = int(bundle_auth.get("missing_numbers_boost", 0) or 0)

    return {
        "pool_size": len(games),
        "operational_reference": metrics_operational,
        "parametros_recomendados": dict(plan.get("parametros_sugeridos") or {}),
        "without_authorized_plan": {
            "calibration_applied": bool(bundle_base.get("calibration_applied")),
            "redundancy_penalty": base_pen,
            "prefix_penalty": base_prefix,
            "missing_numbers_boost": base_boost,
            "plan_params_active": False,
        },
        "with_authorized_plan": {
            "calibration_applied": bool(bundle_auth.get("calibration_applied")),
            "redundancy_penalty": auth_pen,
            "prefix_penalty": auth_prefix,
            "missing_numbers_boost": auth_boost,
            "plan_params_active": True,
            "authorized_calibration_plan": dict(bundle_auth.get("authorized_calibration_plan") or {}),
        },
        "deltas": {
            "redundancy_penalty": round(auth_pen - base_pen, 4),
            "prefix_penalty": auth_prefix - base_prefix,
            "missing_numbers_boost": auth_boost - base_boost,
        },
        "structural_metrics_unchanged": (
            "Calibração M-ML-054/071 ajusta scores dos mesmos cartões; "
            "diversity_score do pool só muda se compose_sovereign_gp selecionar cartões diferentes."
        ),
    }


def extract_generation_calibration_evidence(
    context_json: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Extrai evidências de calibração de um generation_events.context_json."""
    payload = dict(context_json or {})
    cockpit = dict(payload.get("cockpit_calibration_workflow") or {})
    hierarchy = dict(payload.get("ml_hierarchy_bundle") or payload.get("hierarchy_bundle") or {})
    pre_final = dict(
        payload.get("pre_final_pool_ml_calibration")
        or payload.get("calibration_bundle")
        or {}
    )
    recovery = dict(payload.get("pre_gp_recovery") or {})
    diverse = dict(payload.get("diverse_top_slice_m_stat_002") or {})

    return {
        "calibration_applied": bool(payload.get("calibration_applied")),
        "calibration_authorized": bool(
            cockpit.get("calibration_authorized")
            or (payload.get("lot_status_trace") or {}).get("calibration_authorized")
        ),
        "calibration_trace_id": str(
            (cockpit.get("trace") or {}).get("mission_id")
            or payload.get("ml_verdict_mission_id")
            or ""
        ),
        "cockpit_apply_next_generation": bool(cockpit.get("cockpit_apply_next_generation")),
        "parametros_sugeridos": dict(
            cockpit.get("parametros_sugeridos")
            or (pre_final.get("authorized_calibration_plan") or {}).get("parametros_sugeridos")
            or {}
        ),
        "parametros_efetivos_usados": dict(
            (pre_final.get("authorized_calibration_plan") or {}).get("parametros_sugeridos")
            or pre_final.get("supervised_calibration_bundle", {}).get("authorized_calibration_plan", {})
            or {}
        ),
        "redundancy_penalty": float(pre_final.get("redundancy_penalty", payload.get("redundancy_penalty", 0)) or 0),
        "prefix_penalty": int(pre_final.get("prefix_penalty", payload.get("prefix_penalty", 0)) or 0),
        "suffix_penalty": int(pre_final.get("suffix_penalty", payload.get("suffix_penalty", 0)) or 0),
        "missing_numbers_boost": int(
            pre_final.get("missing_numbers_boost", payload.get("missing_numbers_boost", 0)) or 0
        ),
        "diversity_score": float(
            pre_final.get("final_diversity_score")
            or payload.get("diversity_score")
            or 0.0
        ),
        "similarity_score": float(pre_final.get("final_similarity_score", 0.0) or 0.0),
        "sobreposicao_maxima": int(
            ((pre_final.get("metrics_after") or {}).get("redundancy") or {}).get("sobreposicao_maxima", 0) or 0
        ),
        "gp_quality_tier": str(hierarchy.get("gp_quality_tier") or ""),
        "ml_verdict": str(payload.get("ml_verdict") or ""),
        "diversity_delta_intra": float(pre_final.get("diversity_delta", 0.0) or 0.0),
        "pre_gp_recovery_applied": bool(recovery.get("recovery_applied")),
        "diverse_top_slice_applied": bool(diverse.get("diverse_top_slice_applied")),
        "generation_event_id": int(payload.get("generation_event_id", 0) or 0),
    }


def compare_consecutive_generations(
    generation_n: Mapping[str, Any],
    generation_n1: Mapping[str, Any],
) -> dict[str, Any]:
    """Compara geração N (calibração) vs N+1 (seguinte)."""
    ctx_n = dict(generation_n.get("context_json") or generation_n)
    ctx_n1 = dict(generation_n1.get("context_json") or generation_n1)
    ev_n = extract_generation_calibration_evidence(ctx_n)
    ev_n1 = extract_generation_calibration_evidence(ctx_n1)

    return {
        "generation_n": {
            "generation_event_id": int(generation_n.get("id", ev_n.get("generation_event_id", 0)) or 0),
            "evidence": ev_n,
        },
        "generation_n1": {
            "generation_event_id": int(generation_n1.get("id", ev_n1.get("generation_event_id", 0)) or 0),
            "evidence": ev_n1,
        },
        "deltas": {
            "diversity_score": round(ev_n1["diversity_score"] - ev_n["diversity_score"], 4),
            "similarity_score": round(ev_n1["similarity_score"] - ev_n["similarity_score"], 4),
            "redundancy_penalty": round(ev_n1["redundancy_penalty"] - ev_n["redundancy_penalty"], 4),
            "plan_carried_forward": bool(
                ev_n1.get("parametros_efetivos_usados")
                and ev_n.get("parametros_sugeridos")
                and ev_n1["parametros_efetivos_usados"] == ev_n["parametros_sugeridos"]
            ),
            "calibration_authorized_n1": ev_n1["calibration_authorized"],
            "cockpit_apply_next_n": ev_n["cockpit_apply_next_generation"],
        },
        "n1_used_n_calibration": bool(
            ev_n.get("cockpit_apply_next_generation")
            and ev_n.get("calibration_authorized")
            and ev_n1.get("parametros_efetivos_usados")
        ),
    }


def build_calibration_causal_report(
    *,
    generation_pair: Mapping[str, Any] | None = None,
    operational_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Relatório causal read-only M-ML-075-DIAG-00."""
    replay = _replay_calibration_penalty_experiment()
    pair_analysis = generation_pair or {}
    ops = dict(
        operational_evidence
        or {
            "source": "relato_operacional",
            "diversity_n": 0.365,
            "diversity_n1": 0.3337,
            "similarity_n1": 0.6663,
            "ml_verdict_n1": "REPROVADO",
            "plan_recommended": [
                "Aumentar penalidade de similaridade/overlap",
                "Penalizar estruturas viciadas",
                "Reforçar dezenas subcobertas",
            ],
        }
    )

    effect_strength = "nulo"
    if replay["deltas"]["redundancy_penalty"] > 0 and not pair_analysis:
        effect_strength = "fraco_intra_geracao"
    if pair_analysis:
        deltas = dict(pair_analysis.get("deltas") or {})
        if deltas.get("diversity_score", 0) < -0.01:
            effect_strength = "nulo_ou_negativo_cross_gen"

    root_causes = [
        "Plano autorizado persiste em context_json mas não é relido na geração N+1 (sessão Streamlit only).",
        "M-STAT-002 (diverse_top_slice) e M-ML-072 (structural pool) não recebem calibration_plan.",
        "M-ML-073b classifica gp_quality_tier REPROVADO sem retroalimentação automática de parâmetros.",
        "Calibração M-ML-071 é score-only no pool — métricas estruturais (similaridade) invariantes se cartões iguais.",
        "Remediação intra-geração M-ML-073 força authorized=True com boosts default, mascarando ausência do plano cockpit.",
    ]

    return {
        "mission_id": MISSION_ID,
        "diag_version": DIAG_VERSION,
        "verdict": "M-ML-075-DIAG-00 CONCLUÍDA — IMPACTO REAL DA CALIBRAÇÃO NA GERAÇÃO SEGUINTE MEDIDO COM EVIDÊNCIA",
        "central_question": (
            "A calibração registrada altera materialmente a geração seguinte ou apenas persiste/exibe?"
        ),
        "answer_summary": (
            "Cross-geração: plano cockpit não chega ao gerador (classificação D). "
            "Intra-geração: calibração M-ML-071 altera scores e pode reordenar pool, "
            "mas métricas estruturais de diversidade/similaridade do pool permanecem iguais "
            "enquanto os cartões forem os mesmos. Evidência operacional reportada "
            f"(diversidade {ops.get('diversity_n')}→{ops.get('diversity_n1')}) é consistente com desconexão + efeito fraco."
        ),
        "mandatory_answers": {
            "1_onde_registrada": "generation_events.context_json + generated_games.context_json; cockpit_calibration_workflow; calibration_bundle/pre_final_pool_ml_calibration",
            "2_onde_lida_proxima": "resolve_authorized_calibration_plan → st.session_state central_ml_cockpit_persist_bundle (NÃO PostgreSQL)",
            "3_parametros_alterados": "redundancy_penalty_boost, max_overlap_penalty, near_duplicate_penalty, prefix/suffix_penalty, missing_numbers_boost, dezenas_subcobertas, diversity_floor_boost",
            "4_chega_build_sovereign_pool": "NÃO — upstream de calibração; M-ML-072/M-STAT-002 sem calibration_plan; M-ML-074/073 recebem plan na mesma geração",
            "5_n1_usou_calibracao_anterior": "Somente se sessão cockpit manteve cockpit_apply_next_generation=True; não há prova automática via DB",
            "6_plano_vira_parametro": "Parcial — parametros_sugeridos viram plan_params só com authorized=True na mesma sessão; plan_items são texto",
            "7_penalidade_similaridade_aumenta": f"Sim intra-geração com plano: delta replay={replay['deltas']['redundancy_penalty']}",
            "8_prefixo_sufixo_altera_score": f"Sim se detectado: prefix_penalty delta replay={replay['deltas']['prefix_penalty']}",
            "9_dezenas_subcobertas_reforco": f"Sim pontual: missing_numbers_boost delta replay={replay['deltas']['missing_numbers_boost']}",
            "10_delta_antes_depois": pair_analysis.get("deltas") if pair_analysis else ops,
            "11_efeito": effect_strength,
            "12_causa_raiz": root_causes,
        },
        "flow_steps": list(CALIBRATION_FLOW_STEPS),
        "component_table": list(COMPONENT_CALIBRATION_TABLE),
        "replay_experiment": replay,
        "generation_pair_analysis": pair_analysis,
        "operational_evidence": ops,
        "classification": CLASSIFICATION,
        "classification_label": CLASSIFICATION_LABEL,
        "recommended_next_mission": RECOMMENDED_NEXT_MISSION,
        "functional_changes": False,
        "purge_executed": False,
        "agents": {
            "lider": "agent_ml",
            "obrigatorios": ["agent_estatistico", "agent_geracao", "agent_qualidade", "agent_governanca"],
            "apoio": ["agent_dados", "agent_plataforma", "agent_visual"],
        },
    }
