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
    st.markdown("### Linha do tempo")
    st.markdown(
        """
        <div class="lotoia-secondary-shell lotoia-flow-panel" style="margin-bottom: 0.55rem;">
            <div class="lotoia-executive-kicker">Linha do tempo</div>
            <div class="lotoia-executive-copy">Snapshots recentes, transicoes de estado e memoria visual para leitura cronologica rapida.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if timeline.empty:
        st.info("Nenhum snapshot institucional disponivel ainda.")
        return

    recent = timeline.head(3)
    cols = st.columns(len(recent))
    for column, (_, row) in zip(cols, recent.iterrows(), strict=True):
        with column:
            st.markdown(
                f"""
                <div class="lotoia-card-shell lotoia-flow-panel" style="min-height: 10rem;">
                    <div class="lotoia-muted-label" style="margin-bottom: 0.35rem;">
                        {row.get("created_at", "-")}
                    </div>
                    <div style="{_status_badge(str(row.get('status', '-')))}" class="lotoia-runtime-badge">
                        {row.get("status", "-")}
                    </div>
                    <div class="lotoia-executive-copy" style="margin-top: 0.6rem; font-weight: 700; color: #123456;">
                        {row.get("headline", "-")}
                    </div>
                    <div class="lotoia-executive-copy" style="margin-top: 0.35rem;">
                        {row.get("status_transition", "-")}
                    </div>
                    <div class="lotoia-muted-label" style="margin-top: 0.35rem;">
                        {row.get("recommendation", "-")}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("#### Detalhe historico")
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
