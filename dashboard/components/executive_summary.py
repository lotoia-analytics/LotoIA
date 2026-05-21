from __future__ import annotations

from typing import Any, Mapping

import streamlit as st


def render_executive_summary(
    executive_report: Mapping[str, Any],
    historical_summary: Mapping[str, Any],
    snapshot_summary: Mapping[str, Any],
) -> None:
    st.markdown("### Resumo executivo")
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
