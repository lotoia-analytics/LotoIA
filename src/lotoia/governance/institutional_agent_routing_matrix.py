"""Matriz executável de roteamento dos 8 agentes institucionais — M-GOV-AGENTS-002."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Mapping, Sequence

from lotoia.database.database import DEFAULT_DATABASE_PATH, ScientificInstitutionalMemory, create_database, get_session

MISSION_ID = "M-GOV-AGENTS-002"
MATRIX_VERSION = "M-GOV-AGENTS-002-v1"
MEMORY_KIND = "institutional_agent_routing_matrix"
MEMORY_STATUS_ACTIVE = "active"

AGENT_GOVERNANCA = "agent_governanca"
AGENT_ESTATISTICO = "agent_estatistico"
AGENT_GERACAO = "agent_geracao"
AGENT_DADOS = "agent_dados"
AGENT_ML = "agent_ml"
AGENT_QUALIDADE = "agent_qualidade"
AGENT_PLATAFORMA = "agent_plataforma"
AGENT_VISUAL = "agent_visual"

OFFICIAL_AGENTS: tuple[str, ...] = (
    AGENT_GOVERNANCA,
    AGENT_ESTATISTICO,
    AGENT_GERACAO,
    AGENT_DADOS,
    AGENT_ML,
    AGENT_QUALIDADE,
    AGENT_PLATAFORMA,
    AGENT_VISUAL,
)

ISSUE_TYPE_ROUTING: dict[str, dict[str, Any]] = {
    "quase_repetidos_alto": {
        "responsible_agent": AGENT_ESTATISTICO,
        "support_agents": [AGENT_ML, AGENT_GERACAO],
        "routing_reason": "Concentração estrutural e overlap entre candidatos",
    },
    "similaridade_media_gp_elevada": {
        "responsible_agent": AGENT_ESTATISTICO,
        "support_agents": [AGENT_ML],
        "routing_reason": "Similaridade média elevada no pool",
    },
    "sobreposicao_maxima_elevada": {
        "responsible_agent": AGENT_ESTATISTICO,
        "support_agents": [AGENT_ML, AGENT_GERACAO],
        "routing_reason": "Overlap máximo acima do limiar institucional",
    },
    "prefixo_excessivo": {
        "responsible_agent": AGENT_ESTATISTICO,
        "support_agents": [AGENT_ML],
        "routing_reason": "Dominância de prefixo estrutural",
    },
    "sufixo_excessivo": {
        "responsible_agent": AGENT_ESTATISTICO,
        "support_agents": [AGENT_ML],
        "routing_reason": "Dominância de sufixo estrutural",
    },
    "dezena_subcoberta": {
        "responsible_agent": AGENT_ESTATISTICO,
        "support_agents": [AGENT_ML, AGENT_GERACAO],
        "routing_reason": "Cobertura insuficiente das 25 dezenas",
    },
    "diversidade_baixa": {
        "responsible_agent": AGENT_ESTATISTICO,
        "support_agents": [AGENT_ML],
        "routing_reason": "Diversidade estrutural abaixo do piso institucional",
    },
    "captura_13_14_ausente": {
        "responsible_agent": AGENT_ESTATISTICO,
        "support_agents": [AGENT_ML, AGENT_QUALIDADE],
        "routing_reason": "Baixa força de captura nas bases 13/14",
    },
    "pool_estrutural_insuficiente": {
        "responsible_agent": AGENT_GERACAO,
        "support_agents": [AGENT_ML],
        "routing_reason": "Matéria-prima/pool conforme insuficiente",
    },
    "conformidade_estrutural": {
        "responsible_agent": AGENT_GERACAO,
        "support_agents": [AGENT_ML, AGENT_GOVERNANCA],
        "routing_reason": "Conformidade estrutural soberana antes do GP",
    },
    "politica_estrutural_15d": {
        "responsible_agent": AGENT_GOVERNANCA,
        "support_agents": [AGENT_ML, AGENT_GERACAO],
        "routing_reason": "Política institucional M-ML-070 / Lei 15",
    },
    "calibracao_ml": {
        "responsible_agent": AGENT_ML,
        "support_agents": [AGENT_QUALIDADE],
        "routing_reason": "Calibração supervisionada e veredito ML",
    },
    "calibracao_pendente": {
        "responsible_agent": AGENT_ML,
        "support_agents": [AGENT_QUALIDADE, AGENT_VISUAL],
        "routing_reason": "Autorização/aplicação de calibração supervisionada pendente",
    },
    "persistencia_trace": {
        "responsible_agent": AGENT_DADOS,
        "support_agents": [AGENT_PLATAFORMA],
        "routing_reason": "Persistência PostgreSQL e context_json",
    },
    "render_cockpit": {
        "responsible_agent": AGENT_VISUAL,
        "support_agents": [AGENT_PLATAFORMA],
        "routing_reason": "Renderização Central ML / Cobertura",
    },
}

STAGE_ROUTING: dict[str, dict[str, Any]] = {
    "conformidade_estrutural": ISSUE_TYPE_ROUTING["conformidade_estrutural"],
    "diversidade": ISSUE_TYPE_ROUTING["diversidade_baixa"],
    "cobertura": {
        "responsible_agent": AGENT_ESTATISTICO,
        "support_agents": [AGENT_ML, AGENT_GERACAO],
        "routing_reason": "Cobertura e distribuição estrutural do pool",
    },
    "fechamento_gp": {
        "responsible_agent": AGENT_GERACAO,
        "support_agents": [AGENT_ML, AGENT_QUALIDADE],
        "routing_reason": "Fechamento do GP soberano CORE_002",
    },
    "validacao_final": ISSUE_TYPE_ROUTING["calibracao_ml"],
}

CORRECTIVE_ACTION_ROUTING: dict[str, dict[str, Any]] = {
    "expandir_pool_estrutural_15d": ISSUE_TYPE_ROUTING["pool_estrutural_insuficiente"],
    "gerar_pool_estrutural_15d": ISSUE_TYPE_ROUTING["pool_estrutural_insuficiente"],
    "pool_estrutural_15d_expandido": ISSUE_TYPE_ROUTING["pool_estrutural_insuficiente"],
    "rerank_diversidade": ISSUE_TYPE_ROUTING["diversidade_baixa"],
    "substituir_quase_clones": ISSUE_TYPE_ROUTING["quase_repetidos_alto"],
    "expansao_pool_diversidade": ISSUE_TYPE_ROUTING["diversidade_baixa"],
    "reforco_dezenas_ausentes": ISSUE_TYPE_ROUTING["dezena_subcoberta"],
    "rebalanceamento_estrutural": ISSUE_TYPE_ROUTING["dezena_subcoberta"],
    "calibracao_estrutural_multidezena": {
        "responsible_agent": AGENT_ML,
        "support_agents": [AGENT_ESTATISTICO, AGENT_GERACAO],
        "routing_reason": "Calibração estrutural multidezena",
    },
    "substituir_clones_multidezena": ISSUE_TYPE_ROUTING["sobreposicao_maxima_elevada"],
}

PLAN_KEYWORD_ROUTING: tuple[tuple[str, str], ...] = (
    ("sobreposição", "sobreposicao_maxima_elevada"),
    ("overlap", "sobreposicao_maxima_elevada"),
    ("quase repetidos", "quase_repetidos_alto"),
    ("clone", "quase_repetidos_alto"),
    ("prefixo", "prefixo_excessivo"),
    ("sufixo", "sufixo_excessivo"),
    ("subcobert", "dezena_subcoberta"),
    ("diversidade", "diversidade_baixa"),
    ("reranquear", "calibracao_ml"),
    ("captura 13/14", "captura_13_14_ausente"),
)


def build_institutional_agent_routing_matrix_memory() -> dict[str, Any]:
    return {
        "memory_kind": MEMORY_KIND,
        "mission_id": MISSION_ID,
        "agent_routing_matrix_version": MATRIX_VERSION,
        "status": MEMORY_STATUS_ACTIVE,
        "official_agents": list(OFFICIAL_AGENTS),
        "issue_type_routing": ISSUE_TYPE_ROUTING,
        "stage_routing": STAGE_ROUTING,
        "corrective_action_routing": CORRECTIVE_ACTION_ROUTING,
        "updated_at": datetime.now(UTC).isoformat(),
    }


def persist_institutional_agent_routing_matrix_memory(
    db_path: Any = DEFAULT_DATABASE_PATH,
    memory: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(memory or build_institutional_agent_routing_matrix_memory())
    payload["updated_at"] = datetime.now(UTC).isoformat()
    create_database(db_path)
    with get_session(db_path) as session:
        session.add(
            ScientificInstitutionalMemory(
                memory_kind=MEMORY_KIND,
                strategy_name="Matriz de roteamento agentes institucionais",
                game_size=0,
                batch_id=f"{MISSION_ID}-{MATRIX_VERSION}",
                generation_range={"mission_id": MISSION_ID, "agents": list(OFFICIAL_AGENTS)},
                total_games=0,
                unique_games=0,
                duplicate_games=0,
                structural_status=MEMORY_STATUS_ACTIVE,
                scientific_status=MEMORY_STATUS_ACTIVE,
                scientific_classification="INSTITUTIONAL_AGENT_ROUTING",
                main_reason="Roteamento executável agente × problema × missão ML",
                recommended_action="resolve_agent_routing",
                policy_applied=dict(payload),
                policy_before={},
                policy_after=dict(payload),
                decision_mode="INSTITUCIONAL",
                approved_for_use=1,
                notes="M-GOV-AGENTS-002 — 8 agentes oficiais",
                source=MISSION_ID,
            )
        )
        session.commit()
    return payload


def resolve_agent_routing(
    *,
    issue_type: str | None = None,
    stage_id: str | None = None,
    corrective_action: str | None = None,
) -> dict[str, Any]:
    if corrective_action and corrective_action in CORRECTIVE_ACTION_ROUTING:
        row = dict(CORRECTIVE_ACTION_ROUTING[corrective_action])
    elif stage_id and stage_id in STAGE_ROUTING:
        row = dict(STAGE_ROUTING[stage_id])
    elif issue_type and issue_type in ISSUE_TYPE_ROUTING:
        row = dict(ISSUE_TYPE_ROUTING[issue_type])
    else:
        row = {
            "responsible_agent": AGENT_ML,
            "support_agents": [AGENT_QUALIDADE],
            "routing_reason": "Fallback ML operacional supervisionado",
        }
    row.setdefault("support_agents", [])
    row["agent_routing_matrix_version"] = MATRIX_VERSION
    return row


def enrich_decision_block(block: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(block)
    routing = resolve_agent_routing(issue_type=str(payload.get("issue_type") or ""))
    payload["responsible_agent"] = routing["responsible_agent"]
    payload["support_agents"] = list(routing.get("support_agents") or [])
    payload["routing_reason"] = str(routing.get("routing_reason") or "")
    payload["agent_routing_matrix_version"] = MATRIX_VERSION
    trace = dict(payload.get("trace") or {})
    trace.update(
        {
            "responsible_agent": payload["responsible_agent"],
            "support_agents": payload["support_agents"],
            "agent_routing_mission_id": MISSION_ID,
        }
    )
    payload["trace"] = trace
    return payload


def enrich_decision_blocks(blocks: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [enrich_decision_block(block) for block in blocks]


def _resolve_plan_item_routing(plan_item: str) -> dict[str, Any]:
    lowered = str(plan_item or "").lower()
    for keyword, issue_type in PLAN_KEYWORD_ROUTING:
        if keyword in lowered:
            return resolve_agent_routing(issue_type=issue_type)
    return resolve_agent_routing(issue_type="calibracao_ml")


def enrich_calibration_plan(plan: Mapping[str, Any] | None) -> dict[str, Any]:
    source = dict(plan or {})
    plan_items = [str(item) for item in list(source.get("plan_items") or []) if str(item).strip()]
    assignments: list[dict[str, Any]] = []
    agent_counts: dict[str, int] = {}
    for item in plan_items:
        routing = _resolve_plan_item_routing(item)
        primary = str(routing.get("responsible_agent") or AGENT_ML)
        agent_counts[primary] = agent_counts.get(primary, 0) + 1
        assignments.append(
            {
                "plan_item": item,
                "responsible_agent": primary,
                "support_agents": list(routing.get("support_agents") or []),
                "routing_reason": str(routing.get("routing_reason") or ""),
            }
        )
    primary_agent = AGENT_ML
    if agent_counts:
        primary_agent = max(agent_counts.items(), key=lambda row: row[1])[0]
    enriched = dict(source)
    enriched["agent_assignments"] = assignments
    enriched["primary_responsible_agent"] = primary_agent
    enriched["agent_routing_matrix_version"] = MATRIX_VERSION
    enriched["agent_routing_mission_id"] = MISSION_ID
    return enriched


def enrich_stage_result(stage_id: str, result: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(result)
    routing = resolve_agent_routing(stage_id=str(stage_id or payload.get("stage_id") or ""))
    payload["responsible_agent"] = routing["responsible_agent"]
    payload["support_agents"] = list(routing.get("support_agents") or [])
    payload["routing_reason"] = str(routing.get("routing_reason") or "")
    payload["agent_routing_matrix_version"] = MATRIX_VERSION
    actions = list(payload.get("corrective_actions") or [])
    if actions:
        action_routing = resolve_agent_routing(corrective_action=str(actions[0]))
        payload["corrective_action_responsible_agent"] = action_routing["responsible_agent"]
    return payload


def enrich_hierarchy_bundle(bundle: Mapping[str, Any] | None) -> dict[str, Any]:
    source = dict(bundle or {})
    if not source:
        return source
    stage_results = dict(source.get("stage_results") or {})
    enriched_stages: dict[str, Any] = {}
    stage_agents: list[str] = []
    for stage_id, row in stage_results.items():
        if not isinstance(row, dict):
            continue
        enriched = enrich_stage_result(str(stage_id), row)
        enriched_stages[str(stage_id)] = enriched
        agent = str(enriched.get("responsible_agent") or "")
        if agent:
            stage_agents.append(agent)
    source["stage_results"] = enriched_stages
    blocking_agent = ""
    current_stage = str(source.get("current_stage") or "")
    if current_stage and not source.get("gp_closure_allowed", True):
        blocking_agent = str(
            (enriched_stages.get(current_stage) or {}).get("responsible_agent") or ""
        )
    source["blocking_responsible_agent"] = blocking_agent
    source["stage_responsible_agents"] = list(dict.fromkeys(stage_agents))
    source["agent_routing_matrix_version"] = MATRIX_VERSION
    source["agent_routing_mission_id"] = MISSION_ID
    source["institutional_agent_routing_matrix"] = build_institutional_agent_routing_matrix_memory()
    return source


def summarize_responsible_agents(
    *,
    decision_blocks: Sequence[Mapping[str, Any]] | None = None,
    calibration_plan: Mapping[str, Any] | None = None,
    hierarchy_bundle: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    agents: list[str] = []
    for block in list(decision_blocks or []):
        agent = str(dict(block).get("responsible_agent") or "")
        if agent:
            agents.append(agent)
    plan = dict(calibration_plan or {})
    primary = str(plan.get("primary_responsible_agent") or "")
    if primary:
        agents.append(primary)
    hierarchy = dict(hierarchy_bundle or {})
    blocking = str(hierarchy.get("blocking_responsible_agent") or "")
    if blocking:
        agents.append(blocking)
    agents.extend(str(value) for value in list(hierarchy.get("stage_responsible_agents") or []) if value)
    unique = list(dict.fromkeys(agents))
    return {
        "primary_responsible_agent": primary or (unique[0] if unique else AGENT_ML),
        "responsible_agents": unique,
        "blocking_responsible_agent": blocking,
        "agent_routing_matrix_version": MATRIX_VERSION,
        "agent_routing_mission_id": MISSION_ID,
    }


def build_agent_routing_trace(bundle: Mapping[str, Any] | None) -> dict[str, Any]:
    source = dict(bundle or {})
    return {
        "mission_id": MISSION_ID,
        "agent_routing_matrix_version": str(
            source.get("agent_routing_matrix_version") or MATRIX_VERSION
        ),
        "primary_responsible_agent": str(source.get("primary_responsible_agent") or ""),
        "responsible_agents": list(source.get("responsible_agents") or []),
        "blocking_responsible_agent": str(source.get("blocking_responsible_agent") or ""),
        "agent_assignments": list(source.get("agent_assignments") or [])[:30],
    }
