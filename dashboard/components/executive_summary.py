from __future__ import annotations

from typing import Any, Mapping

import streamlit as st


def render_executive_summary(
    executive_report: Mapping[str, Any],
    historical_summary: Mapping[str, Any],
    snapshot_summary: Mapping[str, Any],
) -> None:
    st.info(
        f"{executive_report.get('headline', '-')}"
        f" | {executive_report.get('recommendation', '-')}"
    )
