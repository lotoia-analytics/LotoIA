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
        <div style="padding: 1rem 1.1rem; border-radius: 1rem; border: 1px solid #dce7f2; background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%); box-shadow: 0 12px 28px rgba(18, 52, 86, 0.08); margin-bottom: 0.45rem;">
            <div style="font-size: 0.76rem; letter-spacing: 0.18em; text-transform: uppercase; color: #6d7f92; margin-bottom: 0.55rem;">
                Institutional cockpit
            </div>
            <div style="font-size: 1.9rem; font-weight: 800; color: #123456; line-height: 1.15; margin-bottom: 0.45rem;">
                {executive_report.get("headline", "baseline longitudinal consistente")}
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 0.5rem;">
                <span style="padding: 0.36rem 0.72rem; border-radius: 999px; background: #eef7f0; color: #204c33; font-size: 0.88rem; font-weight: 700;">baseline {baseline}</span>
                <span style="padding: 0.36rem 0.72rem; border-radius: 999px; background: #eef4fb; color: #123456; font-size: 0.88rem; font-weight: 700;">status {status}</span>
                <span style="padding: 0.36rem 0.72rem; border-radius: 999px; background: #f4f1ff; color: #4a3b88; font-size: 0.88rem; font-weight: 700;">confidence {confidence}</span>
                <span style="padding: 0.36rem 0.72rem; border-radius: 999px; background: #fff4e8; color: #8b4f18; font-size: 0.88rem; font-weight: 700;">drift {drift:.2f}</span>
                <span style="padding: 0.36rem 0.72rem; border-radius: 999px; background: #f1f5f9; color: #334155; font-size: 0.88rem; font-weight: 700;">trend {trend}</span>
                <span style="padding: 0.36rem 0.72rem; border-radius: 999px; background: #eef2ff; color: #3949ab; font-size: 0.88rem; font-weight: 700;">health {health:.2f}</span>
            </div>
            <div style="margin-top: 0.8rem; font-size: 0.92rem; color: #4b5f74; line-height: 1.5;">
                {recommendation}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
