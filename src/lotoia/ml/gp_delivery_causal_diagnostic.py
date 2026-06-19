"""Diagnóstico causal read-only — por que GP 15D pode não ser entregue com ML (M-ML-074-DIAG-00)."""

from __future__ import annotations

from typing import Any

MISSION_ID = "M-ML-074-DIAG-00"
DIAG_VERSION = "M-ML-074-DIAG-00-v1"

# Evidência estática — pontos de decisão no código (sem executar geração).
GP_DELIVERY_FLOW: tuple[dict[str, str], ...] = (
    {
        "step": "1",
        "component": "institutional_app._render_clean_law15_generation_page",
        "action": "Clique 'Gerar lote' → pop _clean_law15_generate_clicked",
        "evidence": "dashboard/institutional_app.py — _render_clean_law15_generation_page",
    },
    {
        "step": "2",
        "component": "institutional_app._run_clean_law15_generation",
        "action": "Resolve batch_label, seed, chama _invoke_sovereign_adm_generate_best_games",
        "evidence": "dashboard/institutional_app.py — _run_clean_law15_generation",
    },
    {
        "step": "3",
        "component": "institutional_app._invoke_sovereign_adm_generate_best_games",
        "action": "Chama generate_best_games(ml_enabled=True); captura MlOperationalHierarchyBlockedError",
        "evidence": "dashboard/institutional_app.py — _invoke_sovereign_adm_generate_best_games",
    },
    {
        "step": "4",
        "component": "generate_best_games",
        "action": "build_sovereign_pool → ML pipeline → compose_sovereign_gp → política 15D",
        "evidence": "src/lotoia/generator/basic_generator.py — generate_best_games",
    },
    {
        "step": "5",
        "component": "execute_ml_operational_hierarchy",
        "action": "Pool 15D → conformidade → diversidade → cobertura → gp_closure_allowed",
        "evidence": "src/lotoia/ml/ml_operational_hierarchy.py — execute_ml_operational_hierarchy",
    },
    {
        "step": "6",
        "component": "basic_generator (gate)",
        "action": "Se gp_closure_allowed=False → MlOperationalHierarchyBlockedError ANTES de compose_sovereign_gp",
        "evidence": "basic_generator.py L741-L742",
    },
    {
        "step": "7",
        "component": "compose_sovereign_gp",
        "action": "Só executa se hierarquia liberou; monta N jogos finais",
        "evidence": "src/lotoia/generation/lei15_core_002.py — compose_sovereign_gp",
    },
    {
        "step": "8",
        "component": "apply_structural_policy_15d_to_sovereign_batch",
        "action": "Pós-GP: valida/ajusta lote 15D (não bloqueia pré-GP)",
        "evidence": "src/lotoia/ml/structural_policy_15d.py",
    },
    {
        "step": "9",
        "component": "institutional_app persistência",
        "action": "Persiste generation_event se games válidos; bloqueio hierárquico não persiste lote",
        "evidence": "institutional_app.py — _persist_clean_law15_generation_history",
    },
)

BLOCKING_DECISION_POINTS: tuple[dict[str, Any], ...] = (
    {
        "id": "BLK-HIERARCHY-073",
        "module": "ml_operational_hierarchy + basic_generator",
        "condition": "gp_delivery_blocked is True (pool vazio, overlap crítico — M-ML-073b)",
        "intentional": True,
        "before_compose_gp": True,
        "evidence": "ml_operational_hierarchy.py is_critical_gp_delivery_block, basic_generator.py L766-767",
    },
    {
        "id": "QUALITY-073B",
        "module": "ml_operational_hierarchy",
        "condition": "gp_quality_tier in {ATENÇÃO, REPROVADO} — entrega mantida",
        "intentional": True,
        "before_compose_gp": False,
        "evidence": "ADR-048 M-ML-073b — classificador de qualidade pós-etapas 1-3",
    },
    {
        "id": "BLK-COMPOSE-SHORT",
        "module": "basic_generator",
        "condition": "len(compose_sovereign_gp(...)) < count",
        "intentional": True,
        "before_compose_gp": False,
        "evidence": "basic_generator.py L773-L777",
    },
    {
        "id": "BLK-POOL-GEN",
        "module": "generate_best_games",
        "condition": "build_sovereign_pool não atinge pool_size",
        "intentional": True,
        "before_compose_gp": True,
        "evidence": "basic_generator.py L614-L615",
    },
    {
        "id": "BLK-ENV-GEN",
        "module": "institutional_app",
        "condition": "LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=0",
        "intentional": True,
        "before_compose_gp": True,
        "evidence": "institutional_app.py — _sovereign_generation_blocked_result",
    },
)

ML_CAPABILITIES_BY_MODULE: tuple[dict[str, str], ...] = (
    {
        "module": "structural_pool_15d_generator",
        "generates": "sim — candidatos conformes novos (RNG + validação 15D)",
        "modifies": "sim — enriquece metadados/score estrutural",
        "reorders": "sim — _select_diverse_compliant_pool por structural_pool_score",
        "evaluates": "sim — compliance_rate, métricas pool",
        "evidence": "structural_pool_15d_generator.py — build_ml_structural_15d_pool",
    },
    {
        "module": "pre_final_pool_ml_calibration",
        "generates": "não",
        "modifies": "sim — profile_score via penalidades/boosts",
        "reorders": "sim — sort pós-calibração",
        "evaluates": "sim — metrics_before/after, candidates_reordered",
        "evidence": "pre_final_pool_ml_calibration.py — apply_pre_final_pool_ml_calibration",
    },
    {
        "module": "supervised_output_calibration",
        "generates": "não",
        "modifies": "sim — ajusta profile_score por jogo",
        "reorders": "sim — calibrated.sort(...)",
        "evaluates": "sim — analyze_pool_structural_issues",
        "evidence": "supervised_output_calibration.py L617-L673",
    },
    {
        "module": "ml_operational_hierarchy",
        "generates": "indireto — aciona pool 15D + filtro clones",
        "modifies": "sim — _filter_near_clone_games remove clones do pool",
        "reorders": "indireto — via pre_final dentro de _apply_pool_remediation",
        "evaluates": "sim — hard gates etapas 1–3",
        "evidence": "ml_operational_hierarchy.py — _evaluate_*_stage, MAX_REMEDIATION_ATTEMPTS=5",
    },
    {
        "module": "institutional_agent_routing_matrix",
        "generates": "não",
        "modifies": "não — apenas enriquece metadados responsible_agent",
        "reorders": "não",
        "evaluates": "não — não altera gp_closure_allowed",
        "evidence": "institutional_agent_routing_matrix.py — enrich_* funções",
    },
    {
        "module": "coverage_evidence_interpreter",
        "generates": "não",
        "modifies": "não — read-only diagnóstico Central ML/Cobertura",
        "reorders": "não",
        "evaluates": "sim — interpretação pós-facto",
        "evidence": "coverage_evidence_interpreter.py — interpret_coverage_evidence",
    },
)

COMPONENT_EXPECTATION_TABLE: tuple[dict[str, str], ...] = (
    {
        "component": "generate_best_games",
        "expected": "Entregar dict com N jogos finais CORE_002",
        "actual": "Entrega N jogos OU levanta exceção pré/pós compose",
        "evidence": "basic_generator.py — generate_best_games return payload",
        "correct": "parcial",
        "why": "Contrato de entrega condicionado à hierarquia ML quando habilitada",
    },
    {
        "component": "structural_pool_15d_generator",
        "expected": "Expandir pool com ≥100 conformes diversos",
        "actual": "Gera conformes novos; diversidade no top slice pode permanecer baixa",
        "evidence": "M-STAT-001 — Δ diversity +0.0129 insuficiente",
        "correct": "parcial",
        "why": "Expansão não garante diversidade no slice avaliado (profile_score)",
    },
    {
        "component": "pre_final_pool_ml_calibration",
        "expected": "Melhorar pool pré-GP para fechamento",
        "actual": "Reordena/penaliza; raramente substitui famílias dominantes",
        "evidence": "pre_final_pool_ml_calibration.py — candidates_replaced via compose ou reorder",
        "correct": "parcial",
        "why": "Calibração assistiva, não substituição determinística",
    },
    {
        "component": "ml_operational_hierarchy",
        "expected": "Garantir qualidade antes do GP",
        "actual": "Bloqueia GP se etapas 1–3 falham após 5 tentativas/etapa",
        "evidence": "ml_operational_hierarchy.py L608, L631-634, L741-742",
        "correct": "sim",
        "why": "Comportamento intencional M-ML-073 — fail-closed",
    },
    {
        "component": "structural_policy_15d",
        "expected": "Validar/ajustar lote 15D pós-compose",
        "actual": "Aplica após GP montado; não é gate pré-GP",
        "evidence": "basic_generator.py L794-L801",
        "correct": "sim",
        "why": "Política pós-fechamento conforme M-ML-070",
    },
    {
        "component": "coverage_evidence_interpreter",
        "expected": "Diagnosticar para Central ML",
        "actual": "Read-only; não interfere na geração",
        "evidence": "coverage_evidence_interpreter.py",
        "correct": "sim",
        "why": "Camada observacional",
    },
    {
        "component": "agent_routing_matrix",
        "expected": "Roteamento institucional auditável",
        "actual": "Enriquece payloads com responsible_agent; zero efeito decisório",
        "evidence": "institutional_agent_routing_matrix.py — enrich_hierarchy_bundle",
        "correct": "sim",
        "why": "M-GOV-AGENTS-002 é metadata-only",
    },
    {
        "component": "compose_sovereign_gp",
        "expected": "Fechar exatamente N jogos do pool",
        "actual": "compose_diverse_gp + anti-clone; pode retornar <N",
        "evidence": "lei15_core_002.py L194-L200",
        "correct": "parcial",
        "why": "Anti-clone pode reduzir abaixo de N — erro separado pós-hierarquia",
    },
    {
        "component": "Central ML",
        "expected": "Exibir diagnóstico e plano",
        "actual": "Read-only cockpit; aviso pré-GP se hierarchy_blocked",
        "evidence": "institutional_ml_calibration_cockpit.py, institutional_ml_hierarchy_block.py",
        "correct": "sim",
        "why": "Não participa da decisão de bloqueio",
    },
    {
        "component": "Cobertura Estrutural",
        "expected": "Métricas históricas para decisão ML",
        "actual": "Fonte de evidência; não bloqueia geração em tempo real",
        "evidence": "institutional_operational_structural_coverage.py",
        "correct": "sim",
        "why": "Painel analítico separado do gate runtime",
    },
)

CLASSIFICATION = "B"
CLASSIFICATION_LABEL = "Sistema parcialmente correto; falta mecanismo operacional"
RECOMMENDED_NEXT_MISSION = (
    "M-ML-074 — Recuperação determinística pré-GP: substituição ativa no top slice "
    "antes do bloqueio final da hierarquia (agent_ml + agent_estatistico + agent_geracao)"
)


def build_gp_delivery_causal_report() -> dict[str, Any]:
    return {
        "mission_id": MISSION_ID,
        "diag_version": DIAG_VERSION,
        "central_question": (
            "Por que GP:20 15D com ML habilitado não entrega 20 jogos em alguns cenários?"
        ),
        "answer_summary": (
            "M-ML-073b (ADR-048): a hierarquia M-ML-073 classifica qualidade "
            "(gp_quality_tier) mas não bloqueia entrega por diversidade/cobertura. "
            "Bloqueio duro (gp_delivery_blocked) apenas em pool vazio, overlap crítico "
            "ou falha em compose_sovereign_gp."
        ),
        "divergence_point": {
            "file": "src/lotoia/generator/basic_generator.py",
            "lines": "766-767",
            "condition": "_hierarchy_bundle.get('gp_delivery_blocked')",
            "effect": "MlOperationalHierarchyBlockedError — apenas falhas críticas de entrega",
        },
        "recovery_attempts": {
            "exists": True,
            "max_per_stage": 5,
            "stages": ["diversidade", "cobertura"],
            "evidence": "ml_operational_hierarchy.py — MAX_REMEDIATION_ATTEMPTS=5, while loop L608-626",
        },
        "metrics_are_hard_gates": False,
        "hard_gate_evidence": (
            "M-ML-073b: gp_quality_tier classifica; gp_delivery_blocked apenas crítico. "
            "DIVERSITY_LOW_THRESHOLD=0.55 permanece como observabilidade."
        ),
        "agents_affect_decision": False,
        "agents_evidence": "institutional_agent_routing_matrix.py — enrich only, no branch on responsible_agent",
        "flow_steps": list(GP_DELIVERY_FLOW),
        "blocking_points": list(BLOCKING_DECISION_POINTS),
        "ml_capabilities": list(ML_CAPABILITIES_BY_MODULE),
        "component_table": list(COMPONENT_EXPECTATION_TABLE),
        "classification": CLASSIFICATION,
        "classification_label": CLASSIFICATION_LABEL,
        "recommended_next_mission": RECOMMENDED_NEXT_MISSION,
        "functional_changes": True,
        "purge_executed": False,
    }
