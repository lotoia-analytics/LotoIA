"""Renderização controlada do bloqueio hierárquico M-ML-073 no Painel ADM (M-ML-073-FIX-01)."""

from __future__ import annotations

from typing import Any, Mapping

import streamlit as st

from lotoia.ml.ml_operational_hierarchy import (
    build_ml_hierarchy_block_operational_payload,
    build_ml_operational_hierarchy_trace,
)

MISSION_ID = "M-ML-073-FIX-01"
SESSION_HIERARCHY_BLOCK_KEY = "adm_ml_hierarchy_block_snapshot"

CENTRAL_ML_PRE_GP_BLOCK_MESSAGE = (
    "Nenhum lote final criado. Bloqueio ocorreu antes do fechamento do GP."
)

_AGENT_LABELS = {
    "agent_governanca": "Governança",
    "agent_estatistico": "Estatístico",
    "agent_geracao": "Geração",
    "agent_dados": "Dados",
    "agent_ml": "ML",
    "agent_qualidade": "Qualidade",
    "agent_plataforma": "Plataforma",
    "agent_visual": "Visual",
}


def format_agent_label(agent_id: str) -> str:
    return _AGENT_LABELS.get(str(agent_id or "").strip(), str(agent_id or "—"))


def build_hierarchy_blocked_generation_result(
    *,
    hierarchy_bundle: Mapping[str, Any],
    exception_message: str,
    requested_count: int,
    seed: int,
    analysis_batch_label: str,
    ml_enabled: bool,
) -> dict[str, Any]:
    hierarchy_block = build_ml_hierarchy_block_operational_payload(
        hierarchy_bundle,
        exception_message=exception_message,
    )
    return {
        "seed": int(seed),
        "batch_id": f"clean-law15-hierarchy-blocked-{seed}",
        "requested_count": int(requested_count),
        "games": [],
        "display_games": [],
        "blocked": True,
        "hierarchy_blocked": True,
        "block_reason": "ML_OPERATIONAL_HIERARCHY_GP_BLOCKED",
        "hierarchy_block": hierarchy_block,
        "ml_operational_hierarchy": dict(hierarchy_block.get("ml_operational_hierarchy_trace") or {}),
        "commander_report": {
            "status_comandante_saida": "BLOQUEADO",
            "motivo_bloqueio": "ML_OPERATIONAL_HIERARCHY_GP_BLOCKED",
            "error_message": str(exception_message or hierarchy_block.get("blocking_reason") or ""),
        },
        "fill_diagnostics": {
            "fill_completed": False,
            "insufficient_reason": "ML_OPERATIONAL_HIERARCHY_GP_BLOCKED",
            "sovereign_generation_path": "generate_best_games",
            "analysis_batch_label": analysis_batch_label,
            "generation_path": "LEI15_CORE_002",
            "ml_enabled": ml_enabled,
            "hierarchy_blocked": True,
            "hierarchy_block": hierarchy_block,
        },
        "analysis_batch_label": analysis_batch_label,
        "generation_mode": "LEI15_CORE_002_HIERARCHY_BLOCKED",
        "policy_mode": "ADR_047_CONSTITUTIONAL",
        "selected_quantity": int(requested_count),
        "dezenas_por_jogo": 15,
        "ml_enabled": ml_enabled,
        "persistence_blocked": True,
        "persistence_block_reason": CENTRAL_ML_PRE_GP_BLOCK_MESSAGE,
        "no_final_lot_created": True,
        "pre_gp_hierarchy_block": True,
    }


def persist_hierarchy_block_session_snapshot(result: Mapping[str, Any]) -> None:
    block = dict(result.get("hierarchy_block") or {})
    if not block:
        return
    st.session_state[SESSION_HIERARCHY_BLOCK_KEY] = dict(block)


def load_hierarchy_block_session_snapshot() -> dict[str, Any]:
    return dict(st.session_state.get(SESSION_HIERARCHY_BLOCK_KEY) or {})


def clear_hierarchy_block_session_snapshot() -> None:
    st.session_state.pop(SESSION_HIERARCHY_BLOCK_KEY, None)


def render_ml_hierarchy_block_panel(result: Mapping[str, Any]) -> None:
    block = dict(result.get("hierarchy_block") or {})
    if not block:
        return

    st.markdown("#### Bloqueio hierárquico ML")
    st.error(str(block.get("status") or "GP BLOQUEADO PELA HIERARQUIA ML"))

    cols = st.columns(3)
    cols[0].metric("Versão hierarquia", str(block.get("ml_hierarchy_version") or "—"))
    cols[1].metric("Etapa que falhou", str(block.get("failed_stage_label") or block.get("failed_stage") or "—"))
    cols[2].metric("Compliance", "NÃO")

    st.warning(
        f"**Motivo:** {block.get('failure_category') or 'hierarquia operacional ML'} — "
        f"{block.get('blocking_reason') or block.get('exception_message') or 'etapas 1–3 reprovadas'}"
    )

    agent_cols = st.columns(2)
    agent_cols[0].markdown(
        f"**Agente responsável:** {format_agent_label(str(block.get('responsible_agent') or ''))}"
    )
    support = [format_agent_label(agent) for agent in list(block.get("supporting_agents") or []) if agent]
    agent_cols[1].markdown(
        f"**Agentes de apoio:** {', '.join(support) if support else '—'}"
    )

    corrective = list(block.get("corrective_action_applied") or [])
    if corrective:
        st.markdown("**Ação corretiva sugerida:** " + ", ".join(corrective[:8]))
    else:
        st.markdown("**Ação corretiva sugerida:** revisar pool e diversidade estrutural.")

    st.info(f"**Próximo passo:** {block.get('next_step') or CENTRAL_ML_PRE_GP_BLOCK_MESSAGE}")

    stage_results = dict(block.get("stage_results") or {})
    if stage_results:
        with st.expander("Etapas da hierarquia (trace)", expanded=True):
            for stage_id, row in stage_results.items():
                if not isinstance(row, dict):
                    continue
                label = str(row.get("stage_label") or stage_id)
                status = str(row.get("status") or ("aprovada" if row.get("passed") else "reprovada"))
                agent = format_agent_label(str(row.get("responsible_agent") or ""))
                st.markdown(f"**{label}** — `{status}` | Agente: **{agent}**")
                failures = list(row.get("failures") or [])
                if failures:
                    st.caption("Falhas: " + "; ".join(failures[:3]))

    trace = dict(block.get("ml_operational_hierarchy_trace") or {})
    if trace:
        with st.expander("Trace técnico M-ML-073", expanded=False):
            st.json(
                {
                    "mission_id": trace.get("mission_id"),
                    "ml_hierarchy_version": trace.get("ml_hierarchy_version"),
                    "current_stage": trace.get("current_stage"),
                    "blocking_reason": trace.get("blocking_reason"),
                    "stage_failures": trace.get("stage_failures"),
                    "corrective_action_applied": trace.get("corrective_action_applied"),
                    "responsible_agent": block.get("responsible_agent"),
                    "supporting_agents": block.get("supporting_agents"),
                }
            )


def build_central_ml_pre_gp_block_notice(snapshot: Mapping[str, Any] | None = None) -> dict[str, Any]:
    block = dict((snapshot or {}).get("pre_gp_hierarchy_block") or load_hierarchy_block_session_snapshot())
    if not block:
        return {}
    return {
        "mission_id": MISSION_ID,
        "available": True,
        "headline": str(block.get("status") or "GP BLOQUEADO PELA HIERARQUIA ML"),
        "message": CENTRAL_ML_PRE_GP_BLOCK_MESSAGE,
        "failed_stage": str(block.get("failed_stage") or ""),
        "responsible_agent": str(block.get("responsible_agent") or ""),
        "corrective_action_applied": list(block.get("corrective_action_applied") or []),
        "ml_operational_hierarchy": build_ml_operational_hierarchy_trace(
            dict(block.get("ml_operational_hierarchy_trace") or block)
        ),
    }
