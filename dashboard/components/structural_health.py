from __future__ import annotations

from typing import Any, Mapping

import streamlit as st


def render_structural_health(
    analytical_summary: Mapping[str, Any],
    historical_summary: Mapping[str, Any],
) -> None:
    st.markdown("### Saude estrutural")
    st.markdown(
        """
        <div class="lotoia-secondary-shell lotoia-flow-panel" style="margin-bottom: 0.35rem;">
            <div class="lotoia-executive-kicker">Saude atual</div>
            <div class="lotoia-executive-copy">Sinaliza estabilidade, tendencia e confianca historica em um bloco executivo de leitura curta.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Baseline", analytical_summary.get("confidence", "-"))
    col2.metric("Tendencia", historical_summary.get("trend", "-"))
    col3.metric("Drift historico", f"{float(historical_summary.get('drift_trend', 0.0)):.2f}")
    col4.metric("Confianca historica", f"{float(historical_summary.get('confidence_trend', 0.0)):.2f}")
