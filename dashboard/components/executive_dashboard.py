from __future__ import annotations

from typing import Any, Mapping

import pandas as pd
import streamlit as st

from .analytical_cards import render_analytical_cards
from .design_system import render_institutional_design_system
from .executive_panel import render_executive_panel
from .executive_summary import render_executive_summary
from .hero_banner import render_hero_banner
from .live_status_header import render_live_status_header
from .institutional_timeline import render_institutional_timeline
from .structural_health import render_structural_health


def render_executive_dashboard(
    executive_report: Mapping[str, Any],
    analytical_summary: Mapping[str, Any],
    historical_summary: Mapping[str, Any],
    snapshot_summary: Mapping[str, Any],
    observability_summary: Mapping[str, Any],
    timeline: pd.DataFrame,
) -> None:
    render_institutional_design_system()
    render_live_status_header(executive_report, analytical_summary, historical_summary, observability_summary)

    left_col, right_col = st.columns([1.45, 0.95], gap="large")
    with left_col:
        render_hero_banner(executive_report, analytical_summary, historical_summary)
        render_executive_panel(executive_report, analytical_summary, historical_summary)
    with right_col:
        render_analytical_cards(analytical_summary)
        render_structural_health(analytical_summary, historical_summary)

    with st.container(border=True):
        st.markdown("#### Detalhes")
        render_executive_summary(executive_report, historical_summary, snapshot_summary)
        render_institutional_timeline(timeline)
