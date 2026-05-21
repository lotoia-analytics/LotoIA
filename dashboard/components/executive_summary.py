from __future__ import annotations

from typing import Any, Mapping

import streamlit as st


def render_executive_summary(
    executive_report: Mapping[str, Any],
    historical_summary: Mapping[str, Any],
    snapshot_summary: Mapping[str, Any],
) -> None:
    st.markdown("### Resumo executivo")
    st.markdown(
        """
        <div class="lotoia-secondary-shell lotoia-flow-panel" style="margin-bottom: 0.55rem;">
            <div class="lotoia-executive-kicker">Executive summary</div>
            <div class="lotoia-executive-copy">Resumo curto da leitura institucional, da tendencia e da memoria operacional persistida.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.info(
        f"{executive_report.get('headline', '-')}"
        f" | status={executive_report.get('status', '-')}"
        f" | recomendacao={executive_report.get('recommendation', '-')}"
    )
    st.caption(
        f"Snapshot: {snapshot_summary.get('status', '-')}"
        f" | tendencia: {historical_summary.get('trend', '-')}"
        f" | ultimos vereditos: {historical_summary.get('verdict_count', 0)}"
    )
