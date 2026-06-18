"""Central ML — cockpit de calibração supervisionada (M-ML-VIS-056)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd
import streamlit as st

from dashboard.institutional_supervised_ml import (
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
SESSION_EVENT_ID = "central_ml_cockpit_selected_event_id"
SESSION_PERSIST = "central_ml_cockpit_persist_bundle"

COCKPIT_TITLE = "Central ML — Calibração Supervisionada"
COCKPIT_SUBTITLE = "Diagnosticar, autorizar, aplicar calibração e validar resultado."


def _init_cockpit_session() -> None:
    st.session_state.setdefault(SESSION_WORKFLOW, COCKPIT_WORKFLOW_PENDING)
    st.session_state.setdefault(SESSION_DECISION_AT, "")
    st.session_state.setdefault(SESSION_APPLY_NEXT, False)
    st.session_state.setdefault(SESSION_EVENT_ID, 0)


def _cockpit_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _render_status_chip(label: str, value: str, *, tone: str = "neutral") -> None:
    st.markdown(
        f'<span class="lotoia-pill lotoia-pill-{tone}">{label}: {value}</span>',
        unsafe_allow_html=True,
    )


def _render_diagnosis_card(diagnosis: dict[str, Any]) -> None:
    st.markdown("#### 1. Diagnóstico do último lote")
    if not diagnosis.get("available"):
        st.info(str(diagnosis.get("headline") or "Aguardando lote ML no PostgreSQL."))
        return
    st.caption(str(diagnosis.get("headline") or ""))
    metrics = dict(diagnosis.get("metrics") or {})
    cols = st.columns(3)
    cols[0].metric("Redundância", str(metrics.get("redundancia", "—")))
    cols[1].metric("Quase repetidos", int(metrics.get("quase_repetidos", 0) or 0))
    cols[2].metric("Similaridade média", str(metrics.get("similaridade_media", "—")))
    cols2 = st.columns(3)
    cols2[0].metric("Prefixos/sufixos", str(metrics.get("prefixos_sufixos", "—")))
    cols2[1].metric("Dezenas subcobertas", int(metrics.get("dezenas_subcobertas", 0) or 0))
    cols2[2].metric("Diversidade", str(metrics.get("diversidade", "—")))
    cols3 = st.columns(2)
    cols3[0].metric("Score diversidade", float(metrics.get("diversity_score", 0.0) or 0.0))
    cols3[1].metric("Risco 6 Bases", str(metrics.get("six_bases_risco", "—")))
    issues = list(diagnosis.get("issues_preview") or [])
    if issues:
        for issue in issues:
            st.markdown(f"- {issue}")


def _render_recommendation_card(recommendations: list[str]) -> None:
    st.markdown("#### 2. Recomendação ML")
    if not recommendations:
        st.caption("Nenhuma recomendação pendente.")
        return
    for item in recommendations:
        st.markdown(f"- {item}")


def _render_command_card(
    snapshot: dict[str, Any],
    *,
    supervised_active: bool,
) -> None:
    st.markdown("#### 3. Comando supervisionado")
    if not supervised_active:
        st.warning("Calibração supervisionada inativa — ative ML operacional CORE_002 (M-ML-054).")
        return
    event_id = int(snapshot.get("panel", {}).get("selected_generation_event_id", 0) or 0)
    recommendations = list(snapshot.get("recommendations") or [])
    cmd_cols = st.columns(5)
    if cmd_cols[0].button("Diagnosticar último lote", key="cockpit_cmd_diagnose", use_container_width=True):
        st.session_state[SESSION_WORKFLOW] = COCKPIT_WORKFLOW_PENDING
        st.session_state[SESSION_DECISION_AT] = _cockpit_now_iso()
        st.session_state[SESSION_EVENT_ID] = event_id
        st.session_state[SESSION_PERSIST] = build_cockpit_persist_bundle(
            workflow_status=COCKPIT_WORKFLOW_PENDING,
            decision_at=st.session_state[SESSION_DECISION_AT],
            apply_next_generation=False,
            authorized_event_id=event_id or None,
            recommendations=recommendations,
        )
        st.rerun()
    if cmd_cols[1].button("Autorizar calibração", key="cockpit_cmd_authorize", use_container_width=True):
        st.session_state[SESSION_WORKFLOW] = COCKPIT_WORKFLOW_AUTHORIZED
        st.session_state[SESSION_DECISION_AT] = _cockpit_now_iso()
        st.session_state[SESSION_PERSIST] = build_cockpit_persist_bundle(
            workflow_status=COCKPIT_WORKFLOW_AUTHORIZED,
            decision_at=st.session_state[SESSION_DECISION_AT],
            apply_next_generation=False,
            authorized_event_id=event_id or None,
            recommendations=recommendations,
        )
        st.rerun()
    if cmd_cols[2].button("Aplicar na próxima geração", key="cockpit_cmd_apply_next", use_container_width=True):
        st.session_state[SESSION_WORKFLOW] = COCKPIT_WORKFLOW_AUTHORIZED
        st.session_state[SESSION_APPLY_NEXT] = True
        st.session_state[SESSION_DECISION_AT] = _cockpit_now_iso()
        st.session_state[SESSION_PERSIST] = build_cockpit_persist_bundle(
            workflow_status=COCKPIT_WORKFLOW_AUTHORIZED,
            decision_at=st.session_state[SESSION_DECISION_AT],
            apply_next_generation=True,
            authorized_event_id=event_id or None,
            recommendations=recommendations,
        )
        st.rerun()
    if cmd_cols[3].button("Rejeitar recomendação", key="cockpit_cmd_reject", use_container_width=True):
        st.session_state[SESSION_WORKFLOW] = COCKPIT_WORKFLOW_REJECTED
        st.session_state[SESSION_APPLY_NEXT] = False
        st.session_state[SESSION_DECISION_AT] = _cockpit_now_iso()
        st.session_state[SESSION_PERSIST] = build_cockpit_persist_bundle(
            workflow_status=COCKPIT_WORKFLOW_REJECTED,
            decision_at=st.session_state[SESSION_DECISION_AT],
            apply_next_generation=False,
            authorized_event_id=event_id or None,
            recommendations=recommendations,
        )
        st.rerun()
    if cmd_cols[4].button("Validar resultado", key="cockpit_cmd_validate", use_container_width=True):
        st.session_state[SESSION_WORKFLOW] = COCKPIT_WORKFLOW_APPLIED
        st.session_state[SESSION_DECISION_AT] = _cockpit_now_iso()
        st.session_state[SESSION_APPLY_NEXT] = False
        st.session_state[SESSION_PERSIST] = build_cockpit_persist_bundle(
            workflow_status=COCKPIT_WORKFLOW_APPLIED,
            decision_at=st.session_state[SESSION_DECISION_AT],
            apply_next_generation=False,
            authorized_event_id=event_id or None,
            recommendations=recommendations,
        )
        st.rerun()
    st.caption("Comandos registram decisão supervisionada — calibração automática ocorre no path CORE_002.")


def _render_result_card(result: dict[str, Any]) -> None:
    st.markdown("#### 4. Resultado")
    cols = st.columns(4)
    cols[0].metric("Status calibração", str(result.get("operational_status", "pendente")))
    cols[1].metric("calibration_applied", str(bool(result.get("calibration_applied"))))
    cols[2].metric("Trace persistido", "sim" if result.get("trace_persistido") else "não")
    cols[3].metric("Próx. geração", "sim" if result.get("proxima_geracao_afetada") else "não")
    if result.get("before_after_available"):
        st.caption(
            f"Diversidade pós-calibração: {float(result.get('diversity_score', 0.0) or 0.0):.3f} | "
            f"problemas detectados: {int(result.get('issues_count', 0) or 0)} | "
            f"ações: {int(result.get('actions_count', 0) or 0)}"
        )
    if result.get("decision_at"):
        st.caption(f"Última decisão cockpit: {result.get('decision_at')}")


def _render_technical_expanders(db_path: Any, snapshot: dict[str, Any]) -> None:
    panel = dict(snapshot.get("panel") or {})
    selected_event = dict(snapshot.get("selected_event") or {})
    event_id = int(panel.get("selected_generation_event_id", 0) or 0)

    with st.expander("Bloqueios constitucionais", expanded=False):
        st.dataframe(
            pd.DataFrame([{"bloqueio": code} for code in panel.get("constitutional_blocks") or CONSTITUTIONAL_BLOCKS]),
            hide_index=True,
            use_container_width=True,
        )

    with st.expander("Decision trace", expanded=False):
        trace = dict(selected_event.get("decision_trace") or {})
        if trace.get("status") == "persistido":
            st.json(dict(trace.get("sample") or {}))
        else:
            st.caption("Decision trace ausente neste evento.")

    with st.expander("Feature attribution", expanded=False):
        attribution = dict(selected_event.get("feature_attribution") or {})
        if attribution.get("status") == "persistido":
            if attribution.get("sample"):
                st.json(dict(attribution.get("sample") or {}))
            top_factors = list(attribution.get("top_factors") or [])
            if top_factors:
                st.dataframe(pd.DataFrame(top_factors), hide_index=True, use_container_width=True)
        else:
            st.caption("Feature attribution ausente neste evento.")

    with st.expander("ML × 6 Bases (detalhado)", expanded=False):
        six_bases = list(selected_event.get("ml_six_bases_reading") or build_ml_six_bases_operational_summary())
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
        if event_id > 0:
            detail = build_supervised_ml_operational_event_detail(db_path, event_id)
            if isinstance(detail, dict):
                cal_trace = dict(detail.get("calibration_decision_trace") or {})
                cal_attr = dict(detail.get("calibration_feature_attribution") or {})
                if cal_trace:
                    st.markdown("**Trace de calibração**")
                    st.json(cal_trace)
                if cal_attr:
                    st.markdown("**Feature attribution — calibração**")
                    st.json(cal_attr)


def render_ml_calibration_cockpit(db_path: Any) -> dict[str, Any]:
    """Cockpit operacional da Central ML — visual institucional (M-ML-VIS-056)."""
    _init_cockpit_session()
    supervised_active = is_supervised_output_calibration_active()

    st.markdown(f"### {COCKPIT_TITLE}")
    st.caption(COCKPIT_SUBTITLE)

    snapshot = build_ml_calibration_cockpit_snapshot(
        db_path,
        generation_event_id=int(st.session_state.get(SESSION_EVENT_ID, 0) or 0) or None,
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

    events = list(snapshot.get("events") or [])
    if events:
        event_labels = [
            (
                f"Lote {int(row.get('generation_event_id', 0) or 0)} — "
                f"{int(row.get('persisted_games', 0) or 0)} jogos — "
                f"{'calibrado' if row.get('calibration_applied') else 'sem calibração'}"
            )
            for row in events
        ]
        label_to_id = {
            label: int(row.get("generation_event_id", 0) or 0)
            for label, row in zip(event_labels, events, strict=True)
        }
        selected_label = st.selectbox(
            "Lote analisado",
            options=event_labels,
            key="cockpit_event_select",
        )
        resolved_id = int(label_to_id.get(selected_label, 0) or 0)
        if resolved_id != int(st.session_state.get(SESSION_EVENT_ID, 0) or 0):
            st.session_state[SESSION_EVENT_ID] = resolved_id
            snapshot = build_ml_calibration_cockpit_snapshot(
                db_path,
                generation_event_id=resolved_id,
                workflow_status=str(st.session_state.get(SESSION_WORKFLOW) or COCKPIT_WORKFLOW_PENDING),
                decision_at=str(st.session_state.get(SESSION_DECISION_AT) or ""),
                apply_next_generation=bool(st.session_state.get(SESSION_APPLY_NEXT)),
            )

    row1_col1, row1_col2 = st.columns(2)
    with row1_col1:
        with st.container(border=True):
            _render_diagnosis_card(dict(snapshot.get("diagnosis") or {}))
    with row1_col2:
        with st.container(border=True):
            _render_recommendation_card(list(snapshot.get("recommendations") or []))

    row2_col1, row2_col2 = st.columns(2)
    with row2_col1:
        with st.container(border=True):
            _render_command_card(snapshot, supervised_active=supervised_active)
    with row2_col2:
        with st.container(border=True):
            _render_result_card(dict(snapshot.get("result") or {}))

    st.divider()
    _render_technical_expanders(db_path, snapshot)
    return snapshot
