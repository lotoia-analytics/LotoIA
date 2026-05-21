from __future__ import annotations

from typing import Any, Mapping

import streamlit as st


def render_hero_banner(
    executive_report: Mapping[str, Any],
    analytical_summary: Mapping[str, Any],
    historical_summary: Mapping[str, Any],
) -> None:
    st.markdown(
        f"""
        <div style="padding: 0.25rem 0 0.25rem 0;">
            <div style="font-size: 0.78rem; letter-spacing: 0.18em; text-transform: uppercase; color: #6d7f92; margin-bottom: 0.35rem;">
                Institutional cockpit
            </div>
            <div style="font-size: 1.55rem; font-weight: 800; color: #123456; line-height: 1.2; margin-bottom: 0.25rem;">
                {executive_report.get("headline", "baseline longitudinal consistente")}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        f"Baseline {executive_report.get('baseline_mode', '-')}"
        f" | status {executive_report.get('status', '-')}"
        f" | confianca {analytical_summary.get('confidence', '-')}"
        f" | drift {float(analytical_summary.get('drift', 0.0)):.2f}"
        f" | saude {float(analytical_summary.get('structural_health', 0.0)):.2f}"
        f" | tendencia {historical_summary.get('trend', '-')}"
        f" | recomendacao {executive_report.get('recommendation', '-')}"
    )
