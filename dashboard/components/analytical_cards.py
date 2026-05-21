from __future__ import annotations

from typing import Any, Mapping

import streamlit as st


def render_analytical_cards(analytical_summary: Mapping[str, Any]) -> None:
    st.markdown("### Leitura analitica")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Cobertura 10+", f"{float(analytical_summary.get('coverage_10', 0.0)):.2f}")
    col2.metric("Cobertura 11+", f"{float(analytical_summary.get('coverage_11', 0.0)):.2f}")
    col3.metric("Drift", f"{float(analytical_summary.get('drift', 0.0)):.2f}")
    col4.metric("Recorrencia", f"{float(analytical_summary.get('structural_health', 0.0)):.2f}")
