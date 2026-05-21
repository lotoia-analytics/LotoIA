from __future__ import annotations

from typing import Any, Mapping

import streamlit as st


def render_executive_panel(
    executive_report: Mapping[str, Any],
    analytical_summary: Mapping[str, Any],
    historical_summary: Mapping[str, Any],
) -> None:
    st.markdown("### Cockpit institucional")
    st.markdown(
        """
        <div class="lotoia-secondary-shell lotoia-flow-panel" style="margin-bottom: 0.55rem;">
            <div class="lotoia-executive-kicker">Executive control panel</div>
            <div class="lotoia-executive-copy">Estado institucional, baseline, confianca, drift e saude estrutural em uma leitura rapida.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Status institucional", executive_report.get("status", "-"))
    col2.metric("Baseline", executive_report.get("baseline_mode", "-"))
    col3.metric("Confianca", analytical_summary.get("confidence", "-"))
    col4.metric("Drift", f"{float(analytical_summary.get('drift', 0.0)):.2f}")
    col5.metric("Saude estrutural", f"{float(analytical_summary.get('structural_health', 0.0)):.2f}")
    st.caption(
        f"{executive_report.get('headline', '-')}"
        f" | {executive_report.get('recommendation', '-')}"
        f" | tendencia={historical_summary.get('trend', '-')}"
    )
