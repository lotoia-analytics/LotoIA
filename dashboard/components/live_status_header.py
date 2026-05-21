from __future__ import annotations

from typing import Any, Mapping

import streamlit as st


def _status_level(status: str, drift: float, stability_note: str) -> tuple[str, str]:
    if status == "saudavel" and drift <= 0.20:
        return "healthy", "Baseline consistente e governanca operacional favoravel."
    if status == "observacao" and drift <= 0.35:
        return "moderate", "Baseline estavel com observacao moderada."
    if "observacao" in stability_note.lower():
        return "attention", "Camada institucional pede monitoramento mais proximo."
    return "degraded", "Atencao reforcada na leitura institucional atual."


def render_live_status_header(
    executive_report: Mapping[str, Any],
    analytical_summary: Mapping[str, Any],
    historical_summary: Mapping[str, Any],
    observability_summary: Mapping[str, Any],
) -> None:
    drift = float(executive_report.get("drift", analytical_summary.get("drift", 0.0)))
    stability_note = str(observability_summary.get("summary", {}).get("stability_note", ""))
    level, note = _status_level(str(executive_report.get("status", "-")), drift, stability_note)
    baseline_mode = executive_report.get("baseline_mode", "-")
    confidence = executive_report.get("confidence", analytical_summary.get("confidence", "-"))
    trend = historical_summary.get("trend", "-")
    obs_ready = "ready" if observability_summary.get("summary", {}).get("institutional_snapshot_ready") else "pending"
    pulse_color = {
        "healthy": "#2f855a",
        "moderate": "#d97706",
        "attention": "#b45309",
        "degraded": "#c2410c",
    }.get(level, "#64748b")

    st.markdown(
        f"""
        <div style="padding: 0.35rem 0 0.25rem 0;">
            <div style="font-size: 0.78rem; letter-spacing: 0.18em; text-transform: uppercase; color: #6d7f92; margin-bottom: 0.35rem;">
                Executive live header
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.35rem;">
                <span style="padding: 0.35rem 0.7rem; border-radius: 999px; background: #eef4fb; color: #123456; font-size: 0.88rem; font-weight: 700;">
                    <span style="display:inline-block; width: 0.55rem; height: 0.55rem; border-radius: 999px; background: {pulse_color}; margin-right: 0.35rem; vertical-align: middle; animation: pulse 1.8s ease-in-out infinite;"></span>{level}
                </span>
                <span style="padding: 0.35rem 0.7rem; border-radius: 999px; background: #eef7f0; color: #204c33; font-size: 0.88rem; font-weight: 700;">baseline {baseline_mode}</span>
                <span style="padding: 0.35rem 0.7rem; border-radius: 999px; background: #f4f1ff; color: #4a3b88; font-size: 0.88rem; font-weight: 700;">confidence {confidence}</span>
                <span style="padding: 0.35rem 0.7rem; border-radius: 999px; background: #fff4e8; color: #8b4f18; font-size: 0.88rem; font-weight: 700;">drift {drift:.2f}</span>
                <span style="padding: 0.35rem 0.7rem; border-radius: 999px; background: #eef4fb; color: #123456; font-size: 0.88rem; font-weight: 700;">trend {trend}</span>
                <span style="padding: 0.35rem 0.7rem; border-radius: 999px; background: #f1f5f9; color: #334155; font-size: 0.88rem; font-weight: 700;">observability {obs_ready}</span>
            </div>
        </div>
        <style>
        @keyframes pulse {{
            0% {{ transform: scale(0.95); opacity: 0.7; }}
            50% {{ transform: scale(1.08); opacity: 1; }}
            100% {{ transform: scale(0.95); opacity: 0.7; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.caption(note)
