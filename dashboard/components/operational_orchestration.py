from __future__ import annotations

from typing import Any, Mapping

import pandas as pd
import streamlit as st

from .design_system import render_institutional_design_system


def render_operational_orchestration(orchestration_report: Mapping[str, Any]) -> None:
    render_institutional_design_system()
    report = orchestration_report.get("report", orchestration_report) if isinstance(orchestration_report, Mapping) else {}
    summary = report.get("summary", {}) if isinstance(report, Mapping) else {}
    decision_context = report.get("decision_context", {}) if isinstance(report, Mapping) else {}
    operational_priority = report.get("operational_priority", {}) if isinstance(report, Mapping) else {}
    storytelling = report.get("storytelling", []) if isinstance(report, Mapping) else []
    events = report.get("events", []) if isinstance(report, Mapping) else []
    live_coordination = report.get("live_coordination", {}) if isinstance(report, Mapping) else {}
    signal_engine = report.get("signal_engine", {}) if isinstance(report, Mapping) else {}
    operational_experience = report.get("operational_experience", {}) if isinstance(report, Mapping) else {}
    institutional_presence = report.get("institutional_presence", {}) if isinstance(report, Mapping) else {}

    with st.container(border=True):
        st.markdown(
            """
            <div class="lotoia-executive-kicker">Orquestracao operacional</div>
            <div class="lotoia-executive-copy">Coordena contexto, continuidade e prioridade operacional sem tocar no motor cientifico.</div>
            """,
            unsafe_allow_html=True,
        )
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Orquestração", summary.get("orchestration_state", "-"))
        col2.metric("Prioridade", summary.get("priority", "-"))
        col3.metric("Memória", summary.get("memory_depth", 0))
        col4.metric("Linha do tempo", summary.get("timeline_depth", 0))

        st.markdown("### Contexto executivo")
        st.info(
            f"{decision_context.get('headline', '-')}"
            f" | {decision_context.get('recommendation', '-')}"
            f" | comparação: {decision_context.get('comparison', '-')}"
        )

        priority_col1, priority_col2, priority_col3, priority_col4 = st.columns(4)
        priority_col1.metric("Critical", "yes" if operational_priority.get("critical_state") else "no")
        priority_col2.metric("Stable", "yes" if operational_priority.get("strong_stability") else "no")
        priority_col3.metric("Drift", "high" if operational_priority.get("elevated_drift") else "controlled")
        priority_col4.metric("Change", "relevant" if operational_priority.get("important_change") else "stable")

        st.markdown("### Evolucao")
        if storytelling:
            st.write(" | ".join(str(item) for item in storytelling))
        else:
            st.info("Narrativa operacional ainda em consolidacao.")

        st.markdown("### Eventos")
        events_frame = pd.DataFrame(events)
        if events_frame.empty:
            st.info("Nenhum evento institucional consolidado.")
        else:
            st.dataframe(events_frame, hide_index=True, use_container_width=True)

        st.markdown("### Situacao atual")
        coordination_frame = pd.DataFrame(live_coordination.get("signals", []))
        if coordination_frame.empty:
            st.info("Coordenacao viva ainda em consolidacao.")
        else:
            col1, col2, col3 = st.columns(3)
            col1.metric("Runtime", live_coordination.get("state", "monitoring"))
            col2.metric("Percepcao", live_coordination.get("runtime_perception", "-"))
            col3.metric("Presenca", institutional_presence.get("presence_state", "adaptativa"))
            st.dataframe(coordination_frame, hide_index=True, use_container_width=True)

        st.markdown("### Tendencia")
        signal_cols = st.columns(4)
        signal_cols[0].metric("Estado", signal_engine.get("state", "observation"))
        signal_cols[1].metric("Padrão", signal_engine.get("pattern", "observacao governada"))
        signal_cols[2].metric("Mudanças", signal_engine.get("persistent_changes", 0))
        signal_cols[3].metric("Recorrência", signal_engine.get("recurring_statuses", 0))

        st.markdown("### Experiencia operacional")
        exp_cols = st.columns(4)
        exp_cols[0].metric("Visao geral", operational_experience.get("cockpit", "-"))
        exp_cols[1].metric("Linha do tempo", operational_experience.get("timeline", "-"))
        exp_cols[2].metric("Memoria", operational_experience.get("adaptive_memory", 0))
        exp_cols[3].metric("Contexto", operational_experience.get("context", "-"))

        st.caption(
            f"Presenca institucional: {institutional_presence.get('narrative', '-')}"
            f" | Profundidade de coordenacao: {institutional_presence.get('coordination_depth', 0)}"
        )
