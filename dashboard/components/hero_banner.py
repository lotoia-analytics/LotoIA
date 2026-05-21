from __future__ import annotations

from typing import Any, Mapping

import streamlit as st


def render_hero_banner(
    executive_report: Mapping[str, Any],
    analytical_summary: Mapping[str, Any],
    historical_summary: Mapping[str, Any],
) -> None:
    baseline = executive_report.get("baseline_mode", "-")
    status = executive_report.get("status", "-")
    confidence = analytical_summary.get("confidence", "-")
    drift = float(analytical_summary.get("drift", 0.0))
    health = float(analytical_summary.get("structural_health", 0.0))
    trend = historical_summary.get("trend", "-")
    recommendation = executive_report.get("recommendation", "-")
    st.markdown(
        f"""
        <div class="lotoia-card-shell lotoia-flow-panel">
            <div class="lotoia-executive-kicker">
                Institutional cockpit
            </div>
            <div class="lotoia-executive-headline" style="margin-bottom: 0.45rem;">
                {executive_report.get("headline", "baseline longitudinal consistente")}
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 0.55rem;">
                <span class="lotoia-runtime-badge">baseline {baseline}</span>
                <span class="lotoia-runtime-badge">status {status}</span>
                <span class="lotoia-runtime-badge">confidence {confidence}</span>
                <span class="lotoia-runtime-badge">drift {drift:.2f}</span>
                <span class="lotoia-runtime-badge">trend {trend}</span>
                <span class="lotoia-runtime-badge">health {health:.2f}</span>
            </div>
            <div class="lotoia-executive-copy" style="margin-top: 0.85rem;">
                {recommendation}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
