from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


def render_institutional_timeline(timeline: pd.DataFrame) -> None:
    st.markdown("### Timeline institucional")
    if timeline.empty:
        st.info("Nenhum snapshot institucional disponivel ainda.")
        return
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
