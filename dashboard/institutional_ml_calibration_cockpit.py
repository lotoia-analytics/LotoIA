"""Central ML — cockpit de calibração supervisionada (M-ML-VIS-056 / M-ML-VIS-058)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import streamlit as st

from dashboard.institutional_ml_hierarchy_block import (
    build_central_ml_pre_gp_block_notice,
    format_agent_label,
)
from lotoia.governance.batch_operational_scope import mark_generation_events_superseded_by_calibration
from lotoia.ml.structural_policy_15d import (
    NON_COMPLIANT_PARITY_PAIRS,
    PREFERRED_PARITY_PAIRS,
    normalize_structural_policy_15d_memory,
)
from dashboard.institutional_supervised_ml import (
    AGGREGATE_SCOPE_LABEL,
    CALIBRATION_SUPERVISED_LABEL,
    COCKPIT_WORKFLOW_APPLIED,
    COCKPIT_WORKFLOW_AUTHORIZED,
    COCKPIT_WORKFLOW_PENDING,
    COCKPIT_WORKFLOW_REJECTED,
    CONSTITUTIONAL_BLOCKS,
    EMPTY_ML_EVENTS_MESSAGE,
    build_cockpit_persist_bundle,
    build_ml_calibration_cockpit_snapshot,
    build_ml_six_bases_operational_summary,
    build_supervised_ml_operational_event_detail,
    is_supervised_output_calibration_active,
)
from dashboard.institutional_ml_cockpit_render_guard import (
    MISSION_ID as VIS_COCKPIT_RENDER_GUARD_MISSION_ID,
    detect_mixed_format_aggregate,
    display_cockpit_dataframe,
    display_cockpit_json,
    render_cockpit_block_safe,
    summarize_coverage_snapshot_for_ui,
)
from dashboard.institutional_operational_structural_coverage import (
    build_operational_generation_dropdown_options,
    build_operational_generation_scope_caption,
    is_all_operational_generations_selection,
    load_operational_core_002_generations,
    OPERATIONAL_GENERATION_SELECTOR_KEY,
    resolve_operational_generation_selection,
)

SESSION_WORKFLOW = "central_ml_cockpit_workflow_status"
SESSION_DECISION_AT = "central_ml_cockpit_decision_at"
SESSION_APPLY_NEXT = "central_ml_cockpit_apply_next_generation"
SESSION_PERSIST = "central_ml_cockpit_persist_bundle"

COCKPIT_TITLE = "Central ML — Calibração Supervisionada"
COCKPIT_SUBTITLE = (
    "Cobertura Estrutural → evidência → recomendação → autorização → calibração na próxima geração."
)


def _init_cockpit_session() -> None:
    st.session_state.setdefault(SESSION_WORKFLOW, COCKPIT_WORKFLOW_PENDING)
    st.session_state.setdefault(SESSION_DECISION_AT, "")
    st.session_state.setdefault(SESSION_APPLY_NEXT, False)


def _cockpit_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _render_status_chip(label: str, value: str, *, tone: str = "neutral") -> None:
    st.markdown(
        f'<span class="lotoia-pill lotoia-pill-{tone}">{label}: {value}</span>',
        unsafe_allow_html=True,
    )


def _decision_status_label(workflow_status: str) -> str:
    mapping = {
        COCKPIT_WORKFLOW_PENDING: "Aguardando autorização do operador",
        COCKPIT_WORKFLOW_AUTHORIZED: "Calibração autorizada",
        COCKPIT_WORKFLOW_REJECTED: "Recomendação rejeitada",
        COCKPIT_WORKFLOW_APPLIED: "Validação antes/depois concluída",
    }
    return mapping.get(workflow_status, workflow_status or "pendente")


def _build_persist_bundle(
    snapshot: dict[str, Any],
    *,
    workflow_status: str,
    decision_at: str,
    apply_next_generation: bool,
    operator_decision: str = "",
) -> dict[str, Any]:
    coverage = dict(snapshot.get("coverage_evidence") or {})
    return build_cockpit_persist_bundle(
        workflow_status=workflow_status,
        decision_at=decision_at,
        apply_next_generation=apply_next_generation,
        recommendations=list(snapshot.get("recommendations") or snapshot.get("plan_items") or []),
        coverage_evidence=coverage,
        primary_decision=dict(snapshot.get("primary_decision") or {}),
        calibration_plan=dict(snapshot.get("calibration_plan") or coverage.get("calibration_plan") or {}),
        impacto_detalhado=list(snapshot.get("impacto_detalhado") or coverage.get("impacto_detalhado") or []),
        parametros_sugeridos=dict(
            snapshot.get("parametros_sugeridos") or coverage.get("parametros_sugeridos") or {}
        ),
        operator_decision=operator_decision,
    )


def _render_diagnosis_card(diagnosis: dict[str, Any]) -> None:
    st.markdown("#### 1. Diagnóstico geral da saída")
    scope_label = str(diagnosis.get("scope_label") or AGGREGATE_SCOPE_LABEL)
    st.caption(scope_label)
    if not diagnosis.get("available"):
        st.info(str(diagnosis.get("headline") or "Aguardando gerações ML no PostgreSQL."))
        return
    st.caption(str(diagnosis.get("headline") or ""))
    if diagnosis.get("coverage_source") == "cobertura_estrutural":
        st.caption("Fonte decisória: Cobertura Estrutural / PostgreSQL")
    reading = dict(diagnosis.get("reading") or {})
    if reading:
        st.caption(
            f"Leitura @ `{reading.get('read_at', '—')}` | "
            f"checksum `{reading.get('coverage_snapshot_checksum', '—')}` | "
            f"GEs `{len(reading.get('generation_event_ids') or [])}`"
        )
        filters = dict(reading.get("filters") or diagnosis.get("filters") or {})
        if filters:
            st.caption(
                "Filtros: "
                + ", ".join(
                    f"{key}={value}"
                    for key, value in filters.items()
                    if value not in (None, [], "")
                )
                or "nenhum"
            )
        ge_ids = list(reading.get("generation_event_ids") or diagnosis.get("generation_event_ids") or [])
        if ge_ids:
            preview = ", ".join(str(value) for value in ge_ids[:12])
            suffix = "…" if len(ge_ids) > 12 else ""
            st.caption(f"generation_event_ids: {preview}{suffix}")
    if diagnosis.get("ml_detail_scope_label"):
        st.caption(str(diagnosis.get("ml_detail_scope_label")))
    summary_cols = st.columns(3)
    summary_cols[0].metric("Gerações analisadas", int(diagnosis.get("total_events", 0) or 0))
    summary_cols[1].metric("Jogos agregados", int(diagnosis.get("total_games", 0) or 0))
    summary_cols[2].metric("Com calibração", int(diagnosis.get("calibrated_events", 0) or 0))
    metrics = dict(diagnosis.get("metrics") or {})
    cols = st.columns(3)
    cols[0].metric("Similaridade média", float(metrics.get("similaridade_media", 0.0) or 0.0))
    cols[1].metric("Sobreposição máxima", int(metrics.get("sobreposicao_maxima", 0) or 0))
    cols[2].metric("Quase repetidos críticos", int(metrics.get("quase_repetidos_criticos", metrics.get("quase_repetidos", 0)) or 0))
    cols2 = st.columns(3)
    cols2[0].metric("Dezenas subcobertas", int(metrics.get("dezenas_subcobertas", 0) or 0))
    cols2[1].metric("Score diversidade", float(metrics.get("diversity_score", 0.0) or 0.0))
    cols2[2].metric("Pares em atenção", int(metrics.get("pares_em_atencao", 0) or 0))
    cols2b = st.columns(3)
    cols2b[0].metric("Risco 6 Bases", str(metrics.get("six_bases_risco", "—")))
    cols2b[1].metric("Pares possíveis", int(metrics.get("pares_possiveis", 0) or 0))
    cols2b[2].metric("Formato primário", f"{int(metrics.get('primary_format_size', 0) or 0)}D" if metrics.get("primary_format_size") else "—")
    cols3 = st.columns(3)
    cols3[0].metric("Jogos 13 hits", int(metrics.get("desempenho_13_hits", 0) or 0))
    cols3[1].metric("Jogos 14 hits", int(metrics.get("desempenho_14_hits", 0) or 0))
    cols3[2].metric("Jogos 15 hits", int(metrics.get("desempenho_15_hits", 0) or 0))
    format_breakdown = list(diagnosis.get("format_breakdown") or metrics.get("format_breakdown") or [])
    if format_breakdown:
        st.caption(
            "Formatos: "
            + ", ".join(
                f"{row.get('formato')} ({row.get('geracoes', row.get('jogos', '—'))})"
                for row in format_breakdown
            )
        )


def _render_structural_auto_calibration_card(snapshot: dict[str, Any]) -> None:
    st.markdown("##### Calibração estrutural automática (M-ML-069)")
    plan = dict(
        snapshot.get("structural_auto_calibration_plan")
        or dict(snapshot.get("coverage_evidence") or {}).get("structural_auto_calibration_plan")
        or {}
    )
    actions = list(plan.get("structural_actions") or [])
    if not actions:
        st.caption("Nenhuma ação automática pendente para o formato atual.")
        return
    for row in actions[:8]:
        item = dict(row)
        st.markdown(
            f"**Problema:** {item.get('problema_detectado', '—')}  \n"
            f"**Ação aplicada:** {item.get('acao_aplicada', '—')}  \n"
            f"**Intensidade:** {item.get('intensidade_label', item.get('intensidade', '—'))}  \n"
            f"**Impacto esperado:** {item.get('impacto_esperado', '—')}"
        )


def _format_parity_pairs(pairs: Any) -> str:
    formatted: list[str] = []
    for pair in pairs or []:
        if isinstance(pair, (list, tuple)) and len(pair) >= 2:
            formatted.append(f"{int(pair[0])}/{int(pair[1])}")
    return " • ".join(formatted) if formatted else "—"


def _format_agent_label(agent_id: str) -> str:
    labels = {
        "agent_governanca": "Governança",
        "agent_estatistico": "Estatístico",
        "agent_geracao": "Geração",
        "agent_dados": "Dados",
        "agent_ml": "ML",
        "agent_qualidade": "Qualidade",
        "agent_plataforma": "Plataforma",
        "agent_visual": "Visual",
    }
    return labels.get(str(agent_id or "").strip(), str(agent_id or "—"))


def _render_agent_responsible_card(snapshot: dict[str, Any]) -> None:
    st.markdown("##### Agente responsável (M-GOV-AGENTS-002)")
    coverage = dict(snapshot.get("coverage_evidence") or {})
    primary = str(
        snapshot.get("primary_responsible_agent")
        or coverage.get("primary_responsible_agent")
        or ""
    )
    agents = list(
        dict.fromkeys(
            list(snapshot.get("responsible_agents") or [])
            + list(coverage.get("responsible_agents") or [])
        )
    )
    matrix_version = str(
        snapshot.get("agent_routing_matrix_version")
        or coverage.get("agent_routing_matrix_version")
        or "—"
    )
    if not primary and not agents:
        st.caption("Sem roteamento de agente institucional para o escopo atual.")
        return
    cols = st.columns(3)
    cols[0].metric("Agente principal", _format_agent_label(primary))
    cols[1].metric("Agentes envolvidos", len(agents) or 1)
    cols[2].metric("Matriz", matrix_version)
    if agents:
        st.caption(
            "Roteamento: "
            + " • ".join(_format_agent_label(agent) for agent in agents[:8])
        )
    decision_blocks = list(
        snapshot.get("decision_blocks") or coverage.get("decision_blocks") or []
    )
    routed_blocks = [
        block for block in decision_blocks if isinstance(block, dict) and block.get("responsible_agent")
    ]
    if routed_blocks:
        with st.expander("Problema × agente", expanded=False):
            for block in routed_blocks[:12]:
                st.markdown(
                    f"**{_format_agent_label(str(block.get('responsible_agent') or ''))}** — "
                    f"{block.get('problema_detectado', '—')}"
                )


def _render_ml_operational_hierarchy_card(snapshot: dict[str, Any]) -> None:
    st.markdown("##### Hierarquia Operacional ML (M-ML-073)")
    hierarchy = dict(
        snapshot.get("ml_operational_hierarchy")
        or dict(snapshot.get("coverage_evidence") or {}).get("ml_operational_hierarchy")
        or {}
    )
    if not hierarchy:
        st.caption("Sem evidência de hierarquia operacional ML para o escopo atual.")
        return
    cols = st.columns(4)
    cols[0].metric("Versão", str(hierarchy.get("ml_hierarchy_version", "—")))
    cols[1].metric("Etapa atual", str(hierarchy.get("current_stage", "—")))
    cols[2].metric(
        "Última concluída",
        str(hierarchy.get("last_completed_stage", "—")),
    )
    cols[3].metric(
        "Compliance",
        "SIM" if hierarchy.get("hierarchy_compliance") else "NÃO",
    )
    if hierarchy.get("blocking_reason"):
        st.warning(
            f"Motivo de bloqueio: {hierarchy.get('blocking_reason')} | "
            f"Ação corretiva: {', '.join(hierarchy.get('corrective_action_applied') or []) or '—'}"
        )
    stage_results = dict(hierarchy.get("stage_results") or {})
    if stage_results:
        with st.expander("Etapas da hierarquia", expanded=True):
            for stage_id in (
                "conformidade_estrutural",
                "diversidade",
                "cobertura",
                "fechamento_gp",
                "validacao_final",
            ):
                row = dict(stage_results.get(stage_id) or {})
                if not row:
                    continue
                status = str(row.get("status", "—"))
                label = str(row.get("stage_label", stage_id))
                agent = _format_agent_label(str(row.get("responsible_agent") or ""))
                st.markdown(f"**{label}** — `{status}` | Agente: **{agent}**")
                failures = list(row.get("failures") or [])
                if failures:
                    st.caption("Falhas: " + "; ".join(failures[:3]))


def _render_structural_15d_pool_card(snapshot: dict[str, Any]) -> None:
    st.markdown("##### Pool estrutural ML 15D (M-ML-072)")
    structural_pool = dict(
        snapshot.get("ml_structural_15d_pool")
        or dict(snapshot.get("coverage_evidence") or {}).get("ml_structural_15d_pool")
        or {}
    )
    if not structural_pool:
        st.caption("Sem evidência de pool estrutural ML 15D para o escopo atual.")
        return
    st.caption(
        f"Origem: {structural_pool.get('pool_origin', '—')} | "
        f"Compliance atingido: {'SIM' if structural_pool.get('compliance_met') else 'NÃO'}"
    )
    cols = st.columns(4)
    cols[0].metric("Pool estrutural", int(structural_pool.get("structural_pool_size", 0) or 0))
    cols[1].metric("Conformes", int(structural_pool.get("structural_compliant_pool_size", 0) or 0))
    cols[2].metric("Compliance", f"{float(structural_pool.get('compliance_rate', 0.0) or 0.0):.0%}")
    cols[3].metric(
        "Confronto",
        int(structural_pool.get("reference_contest_window", 10) or 10),
    )
    confronto = dict(structural_pool.get("confronto_recent_contests") or {})
    if confronto.get("available"):
        st.caption(
            f"Média de acertos/concurso: {confronto.get('avg_hits_per_contest', '—')} "
            f"({int(confronto.get('reference_contests_count', 0) or 0)} concursos)"
        )
    metrics_before = dict(structural_pool.get("metrics_before") or {})
    metrics_after = dict(structural_pool.get("metrics_after") or {})
    if metrics_before or metrics_after:
        st.caption(
            "Diversidade estrutural "
            f"{metrics_before.get('diversity_score', '—')} → {metrics_after.get('diversity_score', '—')}"
        )


def _render_pre_final_pool_ml_card(snapshot: dict[str, Any]) -> None:
    st.markdown("##### Pool pré-final calibrado pela ML (M-ML-071)")
    pre_final = dict(
        snapshot.get("pre_final_pool_ml_calibration")
        or dict(snapshot.get("coverage_evidence") or {}).get("pre_final_pool_ml_calibration")
        or {}
    )
    if not pre_final:
        st.caption("Sem evidência de calibração pré-final para o escopo atual.")
        return
    applied = bool(pre_final.get("pre_final_calibration_applied"))
    st.caption(
        f"GP final veio de pool calibrado pela ML: {'SIM' if applied else 'NÃO'} | "
        f"GP alterado pela ML: {'SIM' if pre_final.get('final_gp_changed_by_ml') else 'NÃO'}"
    )
    cols = st.columns(4)
    cols[0].metric("Pool pré-final", int(pre_final.get("pre_final_pool_size", 0) or 0))
    cols[1].metric("Pool deduplicado", int(pre_final.get("pre_final_pool_deduped_size", 0) or 0))
    cols[2].metric("Reordenados", int(pre_final.get("candidates_reordered", 0) or 0))
    cols[3].metric("Substituídos", int(pre_final.get("candidates_replaced", 0) or 0))
    st.caption(
        f"Formato: {pre_final.get('pre_final_calibration_format', '—')} | "
        f"Política: {pre_final.get('pre_final_calibration_policy', '—')}"
    )
    metrics_before = dict(pre_final.get("metrics_before") or {})
    metrics_after = dict(pre_final.get("metrics_after") or {})
    if metrics_before or metrics_after:
        st.caption(
            "Diversidade "
            f"{metrics_before.get('diversity_score', '—')} → {metrics_after.get('diversity_score', '—')} | "
            "Similaridade "
            f"{metrics_before.get('similarity_score', '—')} → {metrics_after.get('similarity_score', '—')}"
        )
    actions = list(pre_final.get("actions_applied") or [])
    if actions:
        with st.expander("Ações aplicadas no pool pré-final", expanded=False):
            for action in actions[:20]:
                st.markdown(f"- {action}")


def _render_structural_policy_15d_card(snapshot: dict[str, Any]) -> None:
    st.markdown("##### Política estrutural soberana 15D (M-ML-070)")
    memory = normalize_structural_policy_15d_memory(
        dict(
            snapshot.get("structural_policy_15d_memory")
            or dict(snapshot.get("coverage_evidence") or {}).get("structural_policy_15d_memory")
            or {}
        )
    )
    application = dict(
        snapshot.get("structural_policy_15d_application")
        or dict(snapshot.get("coverage_evidence") or {}).get("structural_policy_15d_application")
        or {}
    )
    if not memory and not application.get("available"):
        st.caption("Política estrutural 15D não carregada para o formato atual.")
        return
    if memory:
        st.caption(
            f"Versão: {memory.get('policy_version', '—')} | "
            f"Status: {memory.get('status', '—')} | "
            f"Origem: {memory.get('origem_institucional', '—')}"
        )
        rules = list(memory.get("regras_aplicadas") or [])
        if rules:
            st.caption("Regras: " + ", ".join(str(rule) for rule in rules))
        st.markdown(
            f"**Conforme:** {_format_parity_pairs(memory.get('paridade_preferencial') or PREFERRED_PARITY_PAIRS)}"
        )
        st.markdown(f"**Violação:** {_format_parity_pairs(NON_COMPLIANT_PARITY_PAIRS)}")
    applied = bool(
        snapshot.get("structural_policy_applied")
        or application.get("structural_policy_applied")
    )
    st.caption(f"Política aplicada no lote: {'SIM' if applied else 'NÃO'}")
    if application.get("available"):
        st.markdown(
            f"**Conformidade:** {application.get('policy_compliance_status', '—')}  \n"
            f"**Jogos validados:** {application.get('games_validated', 0)}  \n"
            f"**Jogos conformes:** {application.get('games_compliant', 0)}"
        )
        violated = list(
            snapshot.get("policy_violations")
            or application.get("policy_violations")
            or application.get("violated_rules")
            or []
        )
        if violated:
            st.caption("Violações: " + ", ".join(str(item) for item in violated[:6]))


def _render_overlap_composition(metrics: dict[str, Any], *, primary_format: dict[str, Any] | None = None) -> None:
    """Composição de pares por overlap — M-ML-067."""
    rows = list(metrics.get("overlap_composition_rows") or [])
    game_size = int(metrics.get("primary_format_size") or (primary_format or {}).get("game_size") or 0)
    if not rows and game_size > 0:
        from lotoia.ml.overlap_format_thresholds import build_overlap_composition_rows

        distribution = {
            int(key): int(value)
            for key, value in dict(metrics.get("distribuicao_por_overlap") or {}).items()
        }
        rows = build_overlap_composition_rows(game_size, distribution)
    if not rows:
        return
    st.markdown("##### Composição de pares por overlap (M-ML-067)")
    formato = f"{game_size}D" if game_size else str((primary_format or {}).get("formato") or "—")
    st.caption(f"Formato analisado: {formato} | Pares possíveis: {int(metrics.get('pares_possiveis', 0) or 0)}")
    display_cockpit_dataframe(rows, max_rows=64)
    criticos = int(metrics.get("quase_repetidos_criticos", metrics.get("quase_repetidos", 0)) or 0)
    atencao = int(metrics.get("pares_em_atencao", 0) or 0)
    st.caption(f"Quase repetidos críticos (overlap N + N-1): {criticos}")
    st.caption(f"Pares em atenção (overlap N-2): {atencao}")


def _render_overlap_format_verdict(snapshot: dict[str, Any]) -> None:
    st.markdown("##### Limiares de sobreposição por formato (M-ML-060 / M-ML-067)")
    diagnosis = dict(snapshot.get("diagnosis") or {})
    metrics = dict(diagnosis.get("metrics") or snapshot.get("metrics") or {})
    primary = dict(
        snapshot.get("primary_format_analysis")
        or diagnosis.get("primary_format_analysis")
        or {}
    )
    if not primary and not metrics.get("overlap_composition_rows"):
        st.caption("Aguardando leitura soberana com formato identificado.")
        return
    _render_overlap_composition(metrics, primary_format=primary or None)
    if not primary:
        return
    st.markdown(f"**Formato analisado:** {primary.get('formato', '—')}")
    st.markdown(f"**Sobreposição máxima observada:** {primary.get('sobreposicao_maxima', '—')}")
    st.markdown(f"**Faixa ideal para {primary.get('formato', '—')}:** {primary.get('faixa_ideal', '—')}")
    st.markdown(f"**Veredito:** {primary.get('verdict', '—')}")
    if primary.get("cross_check_note"):
        st.caption(f"Cruzamento estrutural: {primary.get('cross_check_note')}")
    if primary.get("recommended_action"):
        st.markdown(f"**Ação recomendada:** {primary.get('recommended_action')}")
    format_analyses = list(snapshot.get("format_analyses") or diagnosis.get("format_analyses") or [])
    if len(format_analyses) > 1:
        with st.expander(f"Outros formatos analisados ({len(format_analyses) - 1})", expanded=False):
            for row in format_analyses:
                item = dict(row)
                st.markdown(
                    f"- **{item.get('formato', '—')}** — overlap {item.get('sobreposicao_maxima', '—')} — "
                    f"{item.get('verdict', '—')}"
                )


def _render_ml_verdict_card(snapshot: dict[str, Any]) -> None:
    st.markdown("#### Veredito ML")
    coverage = dict(snapshot.get("coverage_evidence") or {})
    verdict = str(
        snapshot.get("ml_verdict")
        or coverage.get("ml_verdict")
        or "APROVADO"
    ).strip()
    reason = str(
        snapshot.get("motivo_principal")
        or snapshot.get("ml_verdict_reason")
        or coverage.get("motivo_principal")
        or coverage.get("ml_verdict_reason")
        or "—"
    )
    release_label = str(
        snapshot.get("official_release_label")
        or coverage.get("official_release_label")
        or ("LIBERADA" if snapshot.get("official_release_allowed", True) else "NÃO LIBERADA")
    )
    next_action = str(
        snapshot.get("proxima_acao")
        or snapshot.get("next_action")
        or coverage.get("proxima_acao")
        or coverage.get("next_action")
        or "—"
    )
    if verdict in {"REPROVADO", "BLOQUEADO PARA OFICIALIZAÇÃO"}:
        st.error(f"**{verdict}**")
    elif verdict in {"PRECISA CALIBRAR", "APROVADO COM ALERTA"}:
        st.warning(f"**{verdict}**")
    else:
        st.success(f"**{verdict}**")
    st.markdown(f"**Motivo principal:**  \n{reason}")
    st.markdown(f"**Liberação oficial:**  \n{release_label}")
    st.markdown(f"**Próxima ação:**  \n{next_action}")
    plan_items = list(snapshot.get("plan_items") or [])
    if plan_items:
        st.markdown("**Plano recomendado:**")
        for index, item in enumerate(plan_items[:5], start=1):
            st.markdown(f"{index}. {item}")


def _render_decision_evidence_card(snapshot: dict[str, Any]) -> None:
    st.markdown("#### 2. Evidências e decisão")
    coverage = dict(snapshot.get("coverage_evidence") or {})
    primary = dict(snapshot.get("primary_decision") or coverage.get("primary_decision") or {})
    blocks = list(snapshot.get("decision_blocks") or coverage.get("decision_blocks") or [])
    workflow = str(st.session_state.get(SESSION_WORKFLOW) or COCKPIT_WORKFLOW_PENDING)

    if not coverage.get("available"):
        st.info("Aguardando evidências da Cobertura Estrutural no PostgreSQL.")
        return

    _render_ml_verdict_card(snapshot)

    if primary:
        st.markdown(f"**Problema detectado:**  \n{primary.get('problema_detectado', '—')}")
        st.markdown(f"**Evidência:**  \n{primary.get('evidencia', '—')}")
        st.markdown(f"**Causa provável:**  \n{primary.get('causa_provavel', '—')}")
    elif blocks:
        first = dict(blocks[0])
        st.markdown(f"**Problema detectado:**  \n{first.get('problema_detectado', '—')}")
        st.markdown(f"**Evidência:**  \n{first.get('evidencia', '—')}")
    else:
        st.success("Nenhum problema estrutural crítico detectado na janela recente.")

    if len(blocks) > 1:
        with st.expander(f"Outros problemas detectados ({len(blocks) - 1})", expanded=False):
            for block in blocks[1:]:
                row = dict(block)
                st.markdown(f"- **{row.get('problema_detectado', '—')}** — {row.get('evidencia', '—')}")

    st.markdown(f"**Decisão operador:**  \n{_decision_status_label(workflow)}")
    verdict = str(snapshot.get("ml_verdict") or coverage.get("ml_verdict") or "")
    policy_status = str(
        snapshot.get("policy_compliance_status")
        or coverage.get("policy_compliance_status")
        or ""
    )
    policy_violations = list(snapshot.get("policy_violations") or coverage.get("policy_violations") or [])
    if policy_status in {"non_compliant", "partial"} or policy_violations:
        st.caption(
            f"Política 15D: status={policy_status or '—'} | violações={len(policy_violations)}"
        )
    if verdict in {"PRECISA CALIBRAR", "REPROVADO", "BLOQUEADO PARA OFICIALIZAÇÃO"}:
        st.caption(
            "Veredito ML bloqueia oficialização — aguardando calibração supervisionada autorizada."
        )


def _render_recommendation_card(snapshot: dict[str, Any]) -> None:
    st.markdown("#### 3. Plano de calibração recomendado")
    plan_items = list(snapshot.get("plan_items") or [])
    calibration_plan = dict(snapshot.get("calibration_plan") or {})
    if not plan_items:
        plan_items = list(calibration_plan.get("plan_items") or [])
    if not plan_items:
        plan_items = list(snapshot.get("recommendations") or [])
    policy_plan = dict(snapshot.get("structural_policy_15d_calibration_plan") or {})
    policy_items = list(policy_plan.get("plan_items") or [])
    if not plan_items and policy_items and list(snapshot.get("policy_violations") or []):
        plan_items = policy_items
    if plan_items:
        for index, item in enumerate(plan_items, start=1):
            st.markdown(f"{index}. {item}")
    else:
        st.caption("Nenhum plano pendente — aguardando evidências da Cobertura Estrutural.")


def _render_impact_card(snapshot: dict[str, Any]) -> None:
    st.markdown("#### 4. Impacto esperado")
    impact_items = list(snapshot.get("impacto_detalhado") or [])
    calibration_plan = dict(snapshot.get("calibration_plan") or {})
    if not impact_items:
        impact_items = list(calibration_plan.get("impact_items") or [])
    coverage = dict(snapshot.get("coverage_evidence") or {})
    if not impact_items:
        primary = dict(snapshot.get("primary_decision") or {})
        fallback = str(primary.get("impacto_esperado") or coverage.get("impacto_esperado") or "")
        if fallback:
            impact_items = [fallback]
    if impact_items:
        for item in impact_items:
            st.markdown(f"- {item}")
    else:
        st.caption("Impacto será estimado após diagnóstico com evidências estruturais.")


def _render_command_card(
    snapshot: dict[str, Any],
    *,
    supervised_active: bool,
    db_path: Any,
) -> None:
    st.markdown("#### 5. Comando supervisionado")
    if not supervised_active:
        st.warning("Calibração supervisionada inativa — ative ML operacional CORE_002 (M-ML-054).")
        return
    cmd_cols = st.columns(5)
    if cmd_cols[0].button("Diagnosticar saída geral", key="cockpit_cmd_diagnose", use_container_width=True):
        decision_at = _cockpit_now_iso()
        st.session_state[SESSION_WORKFLOW] = COCKPIT_WORKFLOW_PENDING
        st.session_state[SESSION_DECISION_AT] = decision_at
        st.session_state[SESSION_PERSIST] = _build_persist_bundle(
            snapshot,
            workflow_status=COCKPIT_WORKFLOW_PENDING,
            decision_at=decision_at,
            apply_next_generation=False,
            operator_decision="diagnosticar",
        )
        st.rerun()
    if cmd_cols[1].button("Autorizar calibração", key="cockpit_cmd_authorize", use_container_width=True):
        decision_at = _cockpit_now_iso()
        st.session_state[SESSION_WORKFLOW] = COCKPIT_WORKFLOW_AUTHORIZED
        st.session_state[SESSION_DECISION_AT] = decision_at
        st.session_state[SESSION_PERSIST] = _build_persist_bundle(
            snapshot,
            workflow_status=COCKPIT_WORKFLOW_AUTHORIZED,
            decision_at=decision_at,
            apply_next_generation=False,
            operator_decision="autorizar",
        )
        st.rerun()
    if cmd_cols[2].button("Aplicar na próxima geração", key="cockpit_cmd_apply_next", use_container_width=True):
        decision_at = _cockpit_now_iso()
        latest_event_id = int((snapshot.get("latest_event") or {}).get("generation_event_id", 0) or 0)
        sovereign_ids = [int(value) for value in (snapshot.get("generation_event_ids") or []) if int(value or 0) > 0]
        source_event_ids = [latest_event_id] if latest_event_id > 0 else ([sovereign_ids[-1]] if sovereign_ids else [])
        calibration_plan = dict(snapshot.get("calibration_plan") or {})
        scope_payload = (
            mark_generation_events_superseded_by_calibration(
                source_event_ids,
                db_path=db_path,
                reason="calibração autorizada — lote removido do escopo ativo (M-DADOS-ML-061)",
                evidence=dict(snapshot.get("coverage_evidence") or {}),
                authorized_plan=calibration_plan,
                operator="cockpit_operador_adm",
                calibration_source_only=True,
            )
            if source_event_ids
            else {}
        )
        st.session_state[SESSION_WORKFLOW] = COCKPIT_WORKFLOW_AUTHORIZED
        st.session_state[SESSION_APPLY_NEXT] = True
        st.session_state[SESSION_DECISION_AT] = decision_at
        st.session_state[SESSION_PERSIST] = _build_persist_bundle(
            snapshot,
            workflow_status=COCKPIT_WORKFLOW_AUTHORIZED,
            decision_at=decision_at,
            apply_next_generation=True,
            operator_decision="aplicar_proxima_geracao",
        )
        if scope_payload.get("updated_generation_event_ids"):
            st.success(
                f"{len(scope_payload.get('updated_generation_event_ids') or [])} lote(s) marcado(s) "
                "como calibration_source_only — removidos da leitura ativa."
            )
        st.rerun()
    if cmd_cols[3].button("Rejeitar recomendação", key="cockpit_cmd_reject", use_container_width=True):
        decision_at = _cockpit_now_iso()
        st.session_state[SESSION_WORKFLOW] = COCKPIT_WORKFLOW_REJECTED
        st.session_state[SESSION_APPLY_NEXT] = False
        st.session_state[SESSION_DECISION_AT] = decision_at
        st.session_state[SESSION_PERSIST] = _build_persist_bundle(
            snapshot,
            workflow_status=COCKPIT_WORKFLOW_REJECTED,
            decision_at=decision_at,
            apply_next_generation=False,
            operator_decision="rejeitar",
        )
        st.rerun()
    if cmd_cols[4].button("Validar resultado", key="cockpit_cmd_validate", use_container_width=True):
        decision_at = _cockpit_now_iso()
        st.session_state[SESSION_WORKFLOW] = COCKPIT_WORKFLOW_APPLIED
        st.session_state[SESSION_DECISION_AT] = decision_at
        st.session_state[SESSION_APPLY_NEXT] = False
        st.session_state[SESSION_PERSIST] = _build_persist_bundle(
            snapshot,
            workflow_status=COCKPIT_WORKFLOW_APPLIED,
            decision_at=decision_at,
            apply_next_generation=False,
            operator_decision="validar",
        )
        st.rerun()
    st.caption("Comandos registram decisão supervisionada com evidência da Cobertura Estrutural.")


def _render_result_card(result: dict[str, Any], snapshot: dict[str, Any]) -> None:
    st.markdown("#### 6. Resultado da calibração")
    cols = st.columns(4)
    cols[0].metric("Status calibração", str(result.get("operational_status", "pendente")))
    cols[1].metric("calibration_applied", str(bool(result.get("calibration_applied"))))
    cols[2].metric("Trace persistido", "sim" if result.get("trace_persistido") else "não")
    cols[3].metric("Próx. geração", "sim" if result.get("proxima_geracao_afetada") else "não")
    persist = dict(st.session_state.get(SESSION_PERSIST) or {})
    if persist.get("calibration_authorized") is not None:
        st.caption(f"calibration_authorized: {bool(persist.get('calibration_authorized'))}")
    if result.get("before_after_available") or int(result.get("geracoes_analisadas", 0) or 0) > 0:
        st.caption(
            f"Gerações analisadas: {int(result.get('geracoes_analisadas', 0) or 0)} | "
            f"Diversidade média: {float(result.get('diversity_score', 0.0) or 0.0):.3f} | "
            f"problemas agregados: {int(result.get('issues_count', 0) or 0)}"
        )
    if snapshot.get("coverage_evidence", {}).get("available"):
        st.caption("Validação usa novamente métricas da Cobertura Estrutural (antes/depois).")
    if result.get("decision_at"):
        st.caption(f"Última decisão cockpit: {result.get('decision_at')}")


def _render_technical_expanders(db_path: Any, snapshot: dict[str, Any]) -> None:
    panel = dict(snapshot.get("panel") or {})
    latest_event = dict(snapshot.get("latest_event") or {})
    lot_details = list(snapshot.get("lot_details") or [])
    coverage = dict(snapshot.get("coverage_evidence") or {})

    with st.expander("Auditoria M-ML-068 — Concentração estrutural", expanded=False):
        audit = dict(
            snapshot.get("structural_concentration_audit")
            or dict(coverage.get("structural_concentration_audit") or {})
        )
        if audit.get("available"):
            diag = dict(audit.get("diagnostico") or {})
            st.caption(
                f"GE {audit.get('generation_event_id')} | {audit.get('formato')} | "
                f"similaridade {float(audit.get('similaridade_media', 0) or 0):.4f} | "
                f"diversidade {float(audit.get('diversity_score', 0) or 0):.4f}"
            )
            prefix = dict((audit.get("prefixos_sufixos") or {}).get("prefixo_mais_dominante") or {})
            if prefix:
                st.markdown(
                    f"**Prefixo dominante:** {prefix.get('estrutura')} — "
                    f"{prefix.get('frequencia')}/{prefix.get('total')} ({prefix.get('share_pct')}%)"
                )
            suffix = dict((audit.get("prefixos_sufixos") or {}).get("sufixo_mais_dominante") or {})
            if suffix:
                st.markdown(
                    f"**Sufixo dominante:** {suffix.get('estrutura')} — "
                    f"{suffix.get('frequencia')}/{suffix.get('total')} ({suffix.get('share_pct')}%)"
                )
            coverage_rows = list((audit.get("cobertura_dezenas") or {}).get("tabela_dezenas") or [])[:10]
            if coverage_rows:
                st.markdown("**Top desvios de cobertura (dezenas)**")
                display_cockpit_dataframe(coverage_rows, max_rows=10)
            st.markdown(f"**Causa provável:** {diag.get('problema_detectado', '—')}")
            for action in list(diag.get("acoes_recomendadas") or [])[:5]:
                st.caption(f"→ {action}")
        else:
            st.caption("Auditoria M-ML-068 indisponível para o escopo atual.")

    with st.expander("Memória ML — Limiares format-aware 15D a 23D (M-ML-067)", expanded=False):
        memory = dict(
            snapshot.get("ml_format_aware_memory")
            or snapshot.get("overlap_format_memory")
            or {}
        )
        overlap_memory = dict(memory.get("overlap_memory") or memory)
        thresholds = list(overlap_memory.get("thresholds") or memory.get("thresholds") or [])
        if thresholds:
            display_cockpit_dataframe(thresholds, max_rows=24)
            st.caption(str(overlap_memory.get("rule_summary") or memory.get("rule_summary") or ""))
        similarity_memory = dict(memory.get("similarity_memory") or {})
        if similarity_memory.get("format_thresholds"):
            st.markdown("**Limiares de similaridade média por formato**")
            similarity_rows = [
                {"formato": fmt, **bands}
                for fmt, bands in dict(similarity_memory.get("format_thresholds") or {}).items()
            ]
            display_cockpit_dataframe(similarity_rows, max_rows=24)
        legacy = dict(memory.get("legacy_rule") or {})
        if legacy:
            st.caption(f"Régua legada: overlap fixo >= {legacy.get('near_duplicate_overlap_fixed')} — {legacy.get('status')}")
        else:
            st.caption("Memória de limiares indisponível.")

    with st.expander("Detalhes por lote", expanded=False):
        if lot_details:
            display_cockpit_dataframe(lot_details, max_rows=50)
        else:
            st.caption(EMPTY_ML_EVENTS_MESSAGE)

    with st.expander("Leitura usada da Cobertura Estrutural", expanded=False):
        if coverage.get("available"):
            display_cockpit_json(
                "Resumo seguro da leitura (payload bruto omitido)",
                summarize_coverage_snapshot_for_ui(coverage.get("coverage_evidence_snapshot") or {}),
            )
        else:
            st.caption("Snapshot indisponível.")

    with st.expander("Registro completo da decisão ML", expanded=False):
        blocks = list(snapshot.get("decision_blocks") or [])
        if blocks:
            display_cockpit_dataframe(blocks, max_rows=40)
        else:
            st.caption("Nenhum bloco decisório gerado.")

    with st.expander("Proteções constitucionais ativas", expanded=False):
        display_cockpit_dataframe(
            [{"bloqueio": code} for code in panel.get("constitutional_blocks") or CONSTITUTIONAL_BLOCKS],
            max_rows=20,
        )

    with st.expander("Rastreamento da decisão", expanded=False):
        trace = dict(latest_event.get("decision_trace") or {})
        persist = dict(st.session_state.get(SESSION_PERSIST) or {})
        if persist.get("trace"):
            display_cockpit_json("Trace persistido", dict(persist.get("trace") or {}))
        elif trace.get("status") == "persistido":
            st.caption("Amostra da geração mais recente — visão geral acima.")
            display_cockpit_json("Amostra decision trace", dict(trace.get("sample") or {}))
        else:
            st.caption("Decision trace ausente nas gerações recentes.")

    with st.expander("Pesos e fatores considerados", expanded=False):
        attribution = dict(latest_event.get("feature_attribution") or {})
        if attribution.get("status") == "persistido":
            st.caption("Amostra da geração mais recente — visão geral acima.")
            if attribution.get("sample"):
                display_cockpit_json("Amostra feature attribution", dict(attribution.get("sample") or {}))
            top_factors = list(attribution.get("top_factors") or [])
            if top_factors:
                display_cockpit_dataframe(top_factors, max_rows=20)
        else:
            st.caption("Feature attribution ausente nas gerações recentes.")

    with st.expander("Leitura ML pelas 6 Bases", expanded=False):
        six_bases = list(latest_event.get("ml_six_bases_reading") or build_ml_six_bases_operational_summary())
        display_cockpit_dataframe(six_bases, max_rows=12)

    with st.expander("Histórico e auditoria PostgreSQL", expanded=False):
        events = list(snapshot.get("events") or [])
        if events:
            display_cockpit_dataframe(
                [
                    {
                        "evento": row.get("generation_event_id"),
                        "batch": row.get("batch_label"),
                        "jogos": row.get("persisted_games"),
                        "calibracao": row.get("calibration_applied"),
                        "criado": row.get("created_at"),
                    }
                    for row in events
                ],
                max_rows=50,
            )
        else:
            st.caption(EMPTY_ML_EVENTS_MESSAGE)
        event_id = int(latest_event.get("generation_event_id", 0) or 0)
        if event_id > 0:
            detail = build_supervised_ml_operational_event_detail(db_path, event_id)
            if isinstance(detail, dict):
                cal_trace = dict(detail.get("calibration_decision_trace") or {})
                cal_attr = dict(detail.get("calibration_feature_attribution") or {})
                if cal_trace:
                    st.markdown("**Trace de calibração (geração mais recente)**")
                    display_cockpit_json("Trace calibração", cal_trace)
                if cal_attr:
                    st.markdown("**Feature attribution — calibração (geração mais recente)**")
                    display_cockpit_json("Feature attribution calibração", cal_attr)


def render_ml_calibration_cockpit(db_path: Any) -> dict[str, Any]:
    """Cockpit operacional da Central ML — evidências da Cobertura Estrutural (M-ML-VIS-058)."""
    _init_cockpit_session()
    supervised_active = is_supervised_output_calibration_active()

    st.markdown(f"### {COCKPIT_TITLE}")
    st.caption(COCKPIT_SUBTITLE)

    operational_generations = load_operational_core_002_generations(db_path)
    dropdown_labels = build_operational_generation_dropdown_options(operational_generations)
    default_index = max(0, len(dropdown_labels) - 1) if dropdown_labels else 0
    selected_label = st.selectbox(
        "Geração operacional",
        options=dropdown_labels or ["—"],
        index=default_index,
        key=OPERATIONAL_GENERATION_SELECTOR_KEY,
    )
    operational_selection = resolve_operational_generation_selection(
        selected_label if dropdown_labels else None,
        operational_generations,
    )
    selected_generation = dict(operational_selection.get("selected_generation") or {})
    selected_ge_id = int(operational_selection.get("generation_event_id", 0) or 0)
    selected_card_format = operational_selection.get("card_format")

    try:
        snapshot = build_ml_calibration_cockpit_snapshot(
            db_path,
            operational_selection=operational_selection,
            workflow_status=str(st.session_state.get(SESSION_WORKFLOW) or COCKPIT_WORKFLOW_PENDING),
            decision_at=str(st.session_state.get(SESSION_DECISION_AT) or ""),
            apply_next_generation=bool(st.session_state.get(SESSION_APPLY_NEXT)),
        )
        pre_gp_notice = build_central_ml_pre_gp_block_notice(snapshot)
        if pre_gp_notice.get("available"):
            snapshot = {**snapshot, "pre_gp_hierarchy_block": dict(pre_gp_notice)}
    except Exception as exc:  # noqa: BLE001 — fallback seguro de snapshot
        st.error(
            f"Central ML não pôde montar o snapshot completo ({VIS_COCKPIT_RENDER_GUARD_MISSION_ID}). "
            "Selecione uma Geração operacional específica no seletor acima."
        )
        st.caption(str(exc)[:320])
        snapshot = {
            "mission_id": VIS_COCKPIT_RENDER_GUARD_MISSION_ID,
            "aggregate_mode": bool(operational_selection.get("is_aggregate")),
            "coverage_evidence": {"available": False, "headline": "Snapshot indisponível"},
            "diagnosis": {"available": False, "headline": "Snapshot indisponível"},
            "constitutional_summary": {},
            "recommendations": [],
            "plan_items": [],
            "result": {},
        }

    if supervised_active:
        st.success(CALIBRATION_SUPERVISED_LABEL)
    else:
        st.warning("Calibração supervisionada inativa — verifique ML operacional CORE_002.")

    pre_gp_notice = build_central_ml_pre_gp_block_notice(snapshot)
    if pre_gp_notice.get("available"):
        st.warning(
            f"{pre_gp_notice.get('message')} | "
            f"Etapa: {pre_gp_notice.get('failed_stage') or '—'} | "
            f"Agente: {format_agent_label(str(pre_gp_notice.get('responsible_agent') or ''))}"
        )

    constitutional = dict(snapshot.get("constitutional_summary") or {})
    status_cols = st.columns(4)
    with status_cols[0]:
        _render_status_chip("CORE_002", constitutional.get("core_002", "—"), tone="success")
    with status_cols[1]:
        _render_status_chip("Lei 15", constitutional.get("lei_15", "—"), tone="success")
    with status_cols[2]:
        tone = "success" if constitutional.get("calibracao_supervisionada") == "ATIVA" else "danger"
        _render_status_chip("Calibração ML", constitutional.get("calibracao_supervisionada", "—"), tone=tone)
    with status_cols[3]:
        _render_status_chip("ML livre", "BLOQUEADA", tone="danger")

    chip_cols = st.columns(3)
    chip_cols[0].caption(f"Lei 15A: {constitutional.get('lei_15a', 'INOPERANTE')}")
    chip_cols[1].caption(f"Purge: {constitutional.get('purge', 'PROTEGIDO')}")
    chip_cols[2].caption(f"public_app: {constitutional.get('public_app_ml', 'SEM ML OPERACIONAL')}")
    if operational_generations:
        meta_cols = st.columns(4)
        if is_all_operational_generations_selection(selected_label):
            meta_cols[0].metric(
                "Geração operacional",
                f"Todos ({int(selected_generation.get('generation_events_count', 0) or 0)})",
            )
            meta_cols[1].metric(
                "generation_event_id",
                f"{int(selected_generation.get('generation_events_count', 0) or 0)} IDs",
            )
            meta_cols[2].metric(
                "Formato cartão",
                str(selected_generation.get("card_format_label") or "-"),
            )
            meta_cols[3].metric("Jogos persistidos", int(selected_generation.get("games_count", 0) or 0))
        else:
            meta_cols[0].metric(
                "Geração operacional",
                str(selected_generation.get("operational_generation_label") or "-"),
            )
            meta_cols[1].metric("generation_event_id", str(selected_ge_id or "-"))
            meta_cols[2].metric(
                "Formato cartão",
                f"{int(selected_card_format or 0)}D" if selected_card_format else "-",
            )
            meta_cols[3].metric("Jogos persistidos", int(selected_generation.get("games_count", 0) or 0))

    if operational_selection.get("is_aggregate"):
        st.info(str(snapshot.get("scope_label") or AGGREGATE_SCOPE_LABEL))
    else:
        st.info(build_operational_generation_scope_caption(operational_selection))
    if detect_mixed_format_aggregate(snapshot):
        st.warning(
            "Leitura agregada com múltiplos formatos (ex.: 15D + 17D). "
            "Para evitar lentidão ou falha de renderização, selecione uma "
            "**Geração operacional** específica no seletor acima."
        )
    excluded_count = int(snapshot.get("excluded_batches_count", 0) or 0)
    if excluded_count > 0:
        st.warning(str(snapshot.get("excluded_batches_message") or f"{excluded_count} lotes removidos da leitura ativa."))
        with st.expander("Lotes excluídos da leitura ativa (auditoria técnica)", expanded=False):
            audit_rows = list(snapshot.get("excluded_batches_audit") or [])
            if audit_rows:
                display_cockpit_dataframe(audit_rows, max_rows=40)

    row1_col1, row1_col2 = st.columns(2)
    with row1_col1:
        with st.container(border=True):
            render_cockpit_block_safe(
                "diagnostico",
                lambda: _render_diagnosis_card(dict(snapshot.get("diagnosis") or {})),
            )
            render_cockpit_block_safe(
                "overlap_format",
                lambda: _render_overlap_format_verdict(snapshot),
            )
            render_cockpit_block_safe(
                "agent_responsible",
                lambda: _render_agent_responsible_card(snapshot),
            )
            render_cockpit_block_safe(
                "ml_operational_hierarchy",
                lambda: _render_ml_operational_hierarchy_card(snapshot),
            )
            render_cockpit_block_safe(
                "structural_15d_pool",
                lambda: _render_structural_15d_pool_card(snapshot),
            )
            render_cockpit_block_safe(
                "pre_final_pool_ml",
                lambda: _render_pre_final_pool_ml_card(snapshot),
            )
            render_cockpit_block_safe(
                "politica_15d",
                lambda: _render_structural_policy_15d_card(snapshot),
            )
            render_cockpit_block_safe(
                "auto_calibracao",
                lambda: _render_structural_auto_calibration_card(snapshot),
            )
    with row1_col2:
        with st.container(border=True):
            render_cockpit_block_safe(
                "evidencias_decisao",
                lambda: _render_decision_evidence_card(snapshot),
            )

    row2_col1, row2_col2 = st.columns(2)
    with row2_col1:
        with st.container(border=True):
            render_cockpit_block_safe(
                "recomendacoes",
                lambda: _render_recommendation_card(snapshot),
            )
    with row2_col2:
        with st.container(border=True):
            render_cockpit_block_safe(
                "impacto",
                lambda: _render_impact_card(snapshot),
            )

    row3_col1, row3_col2 = st.columns(2)
    with row3_col1:
        with st.container(border=True):
            render_cockpit_block_safe(
                "comando",
                lambda: _render_command_card(
                    snapshot,
                    supervised_active=supervised_active,
                    db_path=db_path,
                ),
            )
    with row3_col2:
        with st.container(border=True):
            render_cockpit_block_safe(
                "resultado",
                lambda: _render_result_card(dict(snapshot.get("result") or {}), snapshot),
            )

    st.divider()
    st.markdown("### Detalhes técnicos")
    render_cockpit_block_safe(
        "detalhes_tecnicos",
        lambda: _render_technical_expanders(db_path, snapshot),
    )
    return snapshot
