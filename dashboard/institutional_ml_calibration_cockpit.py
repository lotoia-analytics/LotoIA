"""Central ML — cockpit de calibração supervisionada (M-ML-VIS-056 / M-ML-VIS-058)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd
import streamlit as st

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
    return build_cockpit_persist_bundle(
        workflow_status=workflow_status,
        decision_at=decision_at,
        apply_next_generation=apply_next_generation,
        recommendations=list(snapshot.get("recommendations") or []),
        coverage_evidence=dict(snapshot.get("coverage_evidence") or {}),
        primary_decision=dict(snapshot.get("primary_decision") or {}),
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
        st.caption("Fonte decisória: Cobertura Estrutural (PostgreSQL)")
    summary_cols = st.columns(3)
    summary_cols[0].metric("Gerações analisadas", int(diagnosis.get("total_events", 0) or 0))
    summary_cols[1].metric("Jogos agregados", int(diagnosis.get("total_games", 0) or 0))
    summary_cols[2].metric("Com calibração", int(diagnosis.get("calibrated_events", 0) or 0))
    metrics = dict(diagnosis.get("metrics") or {})
    cols = st.columns(3)
    cols[0].metric("Similaridade média", float(metrics.get("similaridade_media", 0.0) or 0.0))
    cols[1].metric("Sobreposição máxima", int(metrics.get("sobreposicao_maxima", 0) or 0))
    cols[2].metric("Quase repetidos", int(metrics.get("quase_repetidos", 0) or 0))
    cols2 = st.columns(3)
    cols2[0].metric("Dezenas subcobertas", int(metrics.get("dezenas_subcobertas", 0) or 0))
    cols2[1].metric("Score diversidade", float(metrics.get("diversity_score", 0.0) or 0.0))
    cols2[2].metric("Risco 6 Bases", str(metrics.get("six_bases_risco", "—")))
    format_breakdown = list(diagnosis.get("format_breakdown") or metrics.get("format_breakdown") or [])
    if format_breakdown:
        st.caption(
            "Formatos: "
            + ", ".join(
                f"{row.get('formato')} ({row.get('geracoes', row.get('jogos', '—'))})"
                for row in format_breakdown
            )
        )


def _render_decision_evidence_card(snapshot: dict[str, Any]) -> None:
    st.markdown("#### 2. Evidências e decisão")
    coverage = dict(snapshot.get("coverage_evidence") or {})
    primary = dict(snapshot.get("primary_decision") or coverage.get("primary_decision") or {})
    blocks = list(snapshot.get("decision_blocks") or coverage.get("decision_blocks") or [])
    workflow = str(st.session_state.get(SESSION_WORKFLOW) or COCKPIT_WORKFLOW_PENDING)

    if not coverage.get("available"):
        st.info("Aguardando evidências da Cobertura Estrutural no PostgreSQL.")
        return

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

    st.markdown(f"**Decisão:**  \n{_decision_status_label(workflow)}")


def _render_recommendation_card(snapshot: dict[str, Any]) -> None:
    st.markdown("#### 3. Ação recomendada")
    primary = dict(snapshot.get("primary_decision") or {})
    recommendations = list(snapshot.get("recommendations") or [])
    if primary.get("acao_recomendada"):
        st.markdown(primary["acao_recomendada"])
    elif recommendations:
        for item in recommendations:
            st.markdown(f"- {item}")
    else:
        st.caption("Nenhuma recomendação pendente — aguardando evidências.")


def _render_impact_card(snapshot: dict[str, Any]) -> None:
    st.markdown("#### 4. Impacto esperado")
    primary = dict(snapshot.get("primary_decision") or {})
    coverage = dict(snapshot.get("coverage_evidence") or {})
    impact = str(primary.get("impacto_esperado") or coverage.get("impacto_esperado") or "")
    if impact:
        st.markdown(impact)
    else:
        st.caption("Impacto será estimado após diagnóstico com evidências estruturais.")


def _render_command_card(
    snapshot: dict[str, Any],
    *,
    supervised_active: bool,
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

    with st.expander("Detalhes por lote", expanded=False):
        if lot_details:
            st.dataframe(pd.DataFrame(lot_details), hide_index=True, use_container_width=True)
        else:
            st.caption(EMPTY_ML_EVENTS_MESSAGE)

    with st.expander("Snapshot Cobertura Estrutural (técnico)", expanded=False):
        if coverage.get("available"):
            st.json(dict(coverage.get("coverage_evidence_snapshot") or {}))
        else:
            st.caption("Snapshot indisponível.")

    with st.expander("Blocos decisórios completos", expanded=False):
        blocks = list(snapshot.get("decision_blocks") or [])
        if blocks:
            st.dataframe(pd.DataFrame(blocks), hide_index=True, use_container_width=True)
        else:
            st.caption("Nenhum bloco decisório gerado.")

    with st.expander("Bloqueios constitucionais", expanded=False):
        st.dataframe(
            pd.DataFrame([{"bloqueio": code} for code in panel.get("constitutional_blocks") or CONSTITUTIONAL_BLOCKS]),
            hide_index=True,
            use_container_width=True,
        )

    with st.expander("Decision trace", expanded=False):
        trace = dict(latest_event.get("decision_trace") or {})
        persist = dict(st.session_state.get(SESSION_PERSIST) or {})
        if persist.get("trace"):
            st.json(dict(persist.get("trace") or {}))
        elif trace.get("status") == "persistido":
            st.caption("Amostra da geração mais recente — visão geral acima.")
            st.json(dict(trace.get("sample") or {}))
        else:
            st.caption("Decision trace ausente nas gerações recentes.")

    with st.expander("Feature attribution", expanded=False):
        attribution = dict(latest_event.get("feature_attribution") or {})
        if attribution.get("status") == "persistido":
            st.caption("Amostra da geração mais recente — visão geral acima.")
            if attribution.get("sample"):
                st.json(dict(attribution.get("sample") or {}))
            top_factors = list(attribution.get("top_factors") or [])
            if top_factors:
                st.dataframe(pd.DataFrame(top_factors), hide_index=True, use_container_width=True)
        else:
            st.caption("Feature attribution ausente nas gerações recentes.")

    with st.expander("ML × 6 Bases (detalhado)", expanded=False):
        six_bases = list(latest_event.get("ml_six_bases_reading") or build_ml_six_bases_operational_summary())
        st.dataframe(pd.DataFrame(six_bases), hide_index=True, use_container_width=True)

    with st.expander("Histórico de decisões / auditoria PostgreSQL", expanded=False):
        events = list(snapshot.get("events") or [])
        if events:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "evento": row.get("generation_event_id"),
                            "batch": row.get("batch_label"),
                            "jogos": row.get("persisted_games"),
                            "calibracao": row.get("calibration_applied"),
                            "criado": row.get("created_at"),
                        }
                        for row in events
                    ]
                ),
                hide_index=True,
                use_container_width=True,
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
                    st.json(cal_trace)
                if cal_attr:
                    st.markdown("**Feature attribution — calibração (geração mais recente)**")
                    st.json(cal_attr)


def render_ml_calibration_cockpit(db_path: Any) -> dict[str, Any]:
    """Cockpit operacional da Central ML — evidências da Cobertura Estrutural (M-ML-VIS-058)."""
    _init_cockpit_session()
    supervised_active = is_supervised_output_calibration_active()

    st.markdown(f"### {COCKPIT_TITLE}")
    st.caption(COCKPIT_SUBTITLE)

    snapshot = build_ml_calibration_cockpit_snapshot(
        db_path,
        workflow_status=str(st.session_state.get(SESSION_WORKFLOW) or COCKPIT_WORKFLOW_PENDING),
        decision_at=str(st.session_state.get(SESSION_DECISION_AT) or ""),
        apply_next_generation=bool(st.session_state.get(SESSION_APPLY_NEXT)),
    )

    if supervised_active:
        st.success(CALIBRATION_SUPERVISED_LABEL)
    else:
        st.warning("Calibração supervisionada inativa — verifique ML operacional CORE_002.")

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
    st.info(str(snapshot.get("scope_label") or AGGREGATE_SCOPE_LABEL))

    row1_col1, row1_col2 = st.columns(2)
    with row1_col1:
        with st.container(border=True):
            _render_diagnosis_card(dict(snapshot.get("diagnosis") or {}))
    with row1_col2:
        with st.container(border=True):
            _render_decision_evidence_card(snapshot)

    row2_col1, row2_col2 = st.columns(2)
    with row2_col1:
        with st.container(border=True):
            _render_recommendation_card(snapshot)
    with row2_col2:
        with st.container(border=True):
            _render_impact_card(snapshot)

    row3_col1, row3_col2 = st.columns(2)
    with row3_col1:
        with st.container(border=True):
            _render_command_card(snapshot, supervised_active=supervised_active)
    with row3_col2:
        with st.container(border=True):
            _render_result_card(dict(snapshot.get("result") or {}), snapshot)

    st.divider()
    st.markdown("### Detalhes técnicos")
    _render_technical_expanders(db_path, snapshot)
    return snapshot
