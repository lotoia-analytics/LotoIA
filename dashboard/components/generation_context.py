from __future__ import annotations

from typing import Any, Mapping

import streamlit as st

from .design_system import render_institutional_design_system


def render_generation_context(
    executive_report: Mapping[str, Any],
    historical_summary: Mapping[str, Any],
    observability_summary: Mapping[str, Any],
) -> None:
    render_institutional_design_system()
    baseline_mode = executive_report.get("baseline_mode", "-")
    status = executive_report.get("status", "-")
    drift = float(executive_report.get("drift", 0.0))
    confidence = executive_report.get("confidence", "-")
    pressure = float(observability_summary.get("counts", {}).get("generation_events", 0))
    trend = historical_summary.get("trend", "-")

    if status == "saudavel" and drift <= 0.20:
        headline = "Baseline permanece consistente nas ultimas janelas."
        note = "Pressao estrutural controlada e leitura executiva favoravel."
    elif status == "observacao":
        headline = "Baseline consistente, mas pedindo observacao moderada."
        note = "Drift recente dentro da faixa esperada, com monitoramento recomendado."
    else:
        headline = "Baseline requer atencao antes de ampliar a geracao."
        note = "Leitura executiva aponta cautela e observacao reforcada."

    st.markdown("### Leitura contextual da geracao")
    st.markdown(
        """
        <div class="lotoia-secondary-shell lotoia-flow-panel" style="margin-bottom: 0.35rem;">
            <div class="lotoia-executive-kicker">Acao contextual</div>
            <div class="lotoia-executive-copy">Antes da acao principal, a homepage apresenta o contexto institucional atual com leitura curta e guiada.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns([1.15, 0.85], gap="large")
    with col1:
        st.info(
            f"{headline} "
            f"| Baseline {baseline_mode} "
            f"| confianca {confidence} "
            f"| drift {drift:.2f} "
            f"| tendencia {trend}"
        )
        st.caption(
            f"{note} "
            f"| observability {observability_summary.get('summary', {}).get('stability_note', '-')}"
            f" | eventos monitorados {int(pressure)}"
        )
    with col2:
        st.markdown(
            f"""
            <div style="padding: 0.85rem 0.95rem; border: 1px solid #dbe4ee; border-radius: 0.9rem; background: #ffffff; box-shadow: 0 8px 20px rgba(18, 52, 86, 0.06);">
                <div style="font-size: 0.74rem; letter-spacing: 0.16em; text-transform: uppercase; color: #6b7f93; margin-bottom: 0.35rem;">
                    Acao executiva
                </div>
                <div style="font-size: 0.98rem; font-weight: 700; color: #123456; margin-bottom: 0.35rem;">
                    Action context
                </div>
                <div style="font-size: 0.9rem; color: #4b5f74; line-height: 1.5; margin-bottom: 0.55rem;">
                    A geracao atual deve ser lida como uma acao contextualizada dentro do baseline validado.
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 0.4rem;">
                    <span style="padding: 0.28rem 0.6rem; border-radius: 999px; background: #eef7f0; color: #204c33; font-size: 0.82rem; font-weight: 700;">stable</span>
                    <span style="padding: 0.28rem 0.6rem; border-radius: 999px; background: #eef4fb; color: #123456; font-size: 0.82rem; font-weight: 700;">guided</span>
                    <span style="padding: 0.28rem 0.6rem; border-radius: 999px; background: #fff4e8; color: #8b4f18; font-size: 0.82rem; font-weight: 700;">observed</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
