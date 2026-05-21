from __future__ import annotations

import pandas as pd
import streamlit as st


def _status_badge(status: str) -> str:
    palette = {
        "saudavel": ("#eef7f0", "#204c33"),
        "observacao": ("#fff4e8", "#8b4f18"),
        "atencao": ("#fff0f0", "#a12d2d"),
    }
    background, color = palette.get(status, ("#f1f5f9", "#334155"))
    return f"padding: 0.32rem 0.65rem; border-radius: 999px; background: {background}; color: {color}; font-size: 0.82rem; font-weight: 700;"


def render_institutional_timeline(timeline: pd.DataFrame) -> None:
    st.markdown("### Timeline institucional")
    if timeline.empty:
        st.info("Nenhum snapshot institucional disponivel ainda.")
        return

    recent = timeline.head(3)
    cols = st.columns(len(recent))
    for column, (_, row) in zip(cols, recent.iterrows(), strict=True):
        with column:
            st.markdown(
                f"""
                <div style="padding: 0.75rem; border: 1px solid #dbe4ee; border-radius: 0.75rem; background: #ffffff; min-height: 10rem;">
                    <div style="font-size: 0.75rem; letter-spacing: 0.16em; text-transform: uppercase; color: #6b7f93; margin-bottom: 0.35rem;">
                        {row.get("created_at", "-")}
                    </div>
                    <div style="{_status_badge(str(row.get('status', '-')))}">
                        {row.get("status", "-")}
                    </div>
                    <div style="margin-top: 0.6rem; font-size: 0.98rem; font-weight: 700; color: #123456;">
                        {row.get("headline", "-")}
                    </div>
                    <div style="margin-top: 0.35rem; font-size: 0.88rem; color: #4b5f74;">
                        {row.get("status_transition", "-")}
                    </div>
                    <div style="margin-top: 0.35rem; font-size: 0.84rem; color: #6b7f93;">
                        {row.get("recommendation", "-")}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("#### Historical detail")
    st.dataframe(
        timeline,
        hide_index=True,
        use_container_width=True,
        column_config={
            "created_at": "Criado em",
            "status": "Status",
            "previous_status": "Anterior",
            "status_transition": "Transicao",
            "headline": "Headline",
            "recommendation": "Recomendacao",
            "trend": "Tendencia",
            "verdict_count": "Veredictos",
            "confidence": "Confianca",
            "source": "Fonte",
        },
    )
