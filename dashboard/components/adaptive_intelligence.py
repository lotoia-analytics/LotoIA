from __future__ import annotations

from typing import Any, Mapping

import pandas as pd
import streamlit as st

from .design_system import render_institutional_design_system


def render_adaptive_institutional_intelligence(adaptive_report: Mapping[str, Any]) -> None:
    render_institutional_design_system()
    operational_memory = adaptive_report.get("operational_memory", {})
    temporal_analysis = adaptive_report.get("temporal_analysis", {})
    pattern_detection = adaptive_report.get("pattern_detection", {})
    strategic_memory = adaptive_report.get("strategic_memory", {})
    adaptive_insights = adaptive_report.get("adaptive_insights", {})
    longitudinal_evolution = adaptive_report.get("longitudinal_evolution_v2", {})
    observational_learning = adaptive_report.get("observational_learning", {})
    strategic_timeline = adaptive_report.get("strategic_timeline", {})
    adaptive_presence = adaptive_report.get("adaptive_presence", {})

    st.markdown("### Inteligencia adaptativa")
    st.markdown(
        """
        <div class="lotoia-secondary-shell lotoia-flow-panel" style="margin-bottom: 0.45rem;">
            <div class="lotoia-executive-kicker">Memoria adaptativa</div>
            <div class="lotoia-executive-copy">Memoria operacional, recorrencias e continuidade institucional em leitura executiva consolidada.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    top_cols = st.columns(3, gap="large")
    top_items = [
        ("Memoria", operational_memory.get("summary", {}).get("memory_depth", 0)),
        ("Tendencia", temporal_analysis.get("summary", {}).get("trend", "observacao")),
        ("Pattern", pattern_detection.get("summary", {}).get("pattern", "observacao")),
    ]
    for column, (label, value) in zip(top_cols, top_items, strict=True):
        with column:
            st.markdown(
                f"""
                <div class="lotoia-card-shell" style="padding: 0.8rem 0.9rem;">
                    <div class="lotoia-muted-label">{label}</div>
                    <div style="margin-top: 0.45rem;">
                        <span class="lotoia-analytical-badge">{value}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("### Memoria operacional")
    memory_timeline = pd.DataFrame(operational_memory.get("timeline", []))
    if memory_timeline.empty:
        st.info("Memoria operacional adaptativa ainda depende de snapshots institucionais.")
    else:
        st.dataframe(memory_timeline, hide_index=True, use_container_width=True)

    st.markdown("### Temporal adaptive analysis")
    temporal_cols = st.columns(4)
    temporal_items = [
        ("Trend", temporal_analysis.get("summary", {}).get("trend", "observacao")),
        ("Recurring status", temporal_analysis.get("summary", {}).get("recurring_statuses", 0)),
        ("Persistent changes", temporal_analysis.get("summary", {}).get("persistent_changes", 0)),
        ("Memoria", temporal_analysis.get("summary", {}).get("memory_depth", 0)),
    ]
    for column, (label, value) in zip(temporal_cols, temporal_items, strict=True):
        with column:
            st.metric(label, value)

    st.markdown("### Padroes institucionais")
    pattern_cols = st.columns(3)
    pattern_items = [
        ("Pattern", pattern_detection.get("summary", {}).get("pattern", "observacao")),
        ("Recurring statuses", pattern_detection.get("summary", {}).get("recurring_statuses", 0)),
        ("Persistent changes", pattern_detection.get("summary", {}).get("persistent_changes", 0)),
    ]
    for column, (label, value) in zip(pattern_cols, pattern_items, strict=True):
        with column:
            st.metric(label, value)

    st.markdown("### Memoria estrategica")
    strategic_frame = pd.DataFrame(strategic_memory.get("timeline", []))
    if strategic_frame.empty:
        st.info("Memoria estrategica ainda nao consolidada.")
    else:
        st.dataframe(strategic_frame, hide_index=True, use_container_width=True)

    st.markdown("### Insights adaptativos")
    adaptive_insights_frame = pd.DataFrame(adaptive_insights.get("insights", []))
    if adaptive_insights_frame.empty:
        st.info("Insights adaptativos ainda em consolidacao.")
    else:
        st.dataframe(adaptive_insights_frame, hide_index=True, use_container_width=True)

    st.markdown("### Longitudinal evolution engine v2")
    evolution_cols = st.columns(4)
    evolution_items = [
        ("Trend", longitudinal_evolution.get("summary", {}).get("trend", "observacao")),
        ("Stability evolution", longitudinal_evolution.get("summary", {}).get("stability_evolution", 0.0)),
        ("Drift evolution", longitudinal_evolution.get("summary", {}).get("drift_evolution", 0.0)),
        ("Timeline depth", longitudinal_evolution.get("summary", {}).get("timeline_depth", 0)),
    ]
    for column, (label, value) in zip(evolution_cols, evolution_items, strict=True):
        with column:
            st.metric(label, value)

    st.markdown("### Observational learning layer")
    st.info(
        f"Modo de aprendizado: {observational_learning.get('summary', {}).get('learning_mode', 'observational_governed')}"
    )

    st.markdown("### Strategic analytical timeline")
    strategic_frame = pd.DataFrame(strategic_timeline.get("timeline", []))
    if strategic_frame.empty:
        st.info("Timeline estrategica ainda nao consolidada.")
    else:
        st.dataframe(strategic_frame, hide_index=True, use_container_width=True)

    st.markdown("### Presenca adaptativa")
    presence_cols = st.columns(3)
    presence_items = [
        ("Presenca", adaptive_presence.get("summary", {}).get("presence", "observacional")),
        ("Consistencia", adaptive_presence.get("summary", {}).get("consistency", 0.0)),
        ("Memoria", adaptive_presence.get("summary", {}).get("memory_depth", 0)),
    ]
    for column, (label, value) in zip(presence_cols, presence_items, strict=True):
        with column:
            st.metric(label, value)
