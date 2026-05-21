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

    with st.container(border=True):
        st.markdown(
            """
            <div class="lotoia-executive-kicker">Intelligent orchestration</div>
            <div class="lotoia-executive-copy">Coordena contexto, continuidade e prioridade operacional sem tocar no motor científico.</div>
            """,
            unsafe_allow_html=True,
        )
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Orquestração", summary.get("orchestration_state", "-"))
        col2.metric("Prioridade", summary.get("priority", "-"))
        col3.metric("Memória", summary.get("memory_depth", 0))
        col4.metric("Timeline", summary.get("timeline_depth", 0))

        st.markdown("### Executive decision context")
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

        st.markdown("### Executive storytelling")
        if storytelling:
            st.write(" | ".join(str(item) for item in storytelling))
        else:
            st.info("Narrativa operacional ainda em consolidacao.")

        st.markdown("### Institutional event system")
        events_frame = pd.DataFrame(events)
        if events_frame.empty:
            st.info("Nenhum evento institucional consolidado.")
        else:
            st.dataframe(events_frame, hide_index=True, use_container_width=True)
