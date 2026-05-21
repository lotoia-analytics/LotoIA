from __future__ import annotations

import streamlit as st


def render_secondary_operational_metrics(gen_count: int, check_count: int, last_contest: str, total_games: str) -> None:
    st.markdown("### Operacao secundaria")
    col1, col2, col3, col4 = st.columns(4)
    cards = [
        (col1, "Geracoes", gen_count, "Eventos persistidos em generation_events"),
        (col2, "Conferencias", check_count, "Eventos persistidos em check_events"),
        (col3, "Ultimo concurso", last_contest, "Maior concurso conferido"),
        (col4, "Jogos totais", total_games, "Total operacional registrado"),
    ]
    markers = ["▸", "▸", "▸", "▸"]
    for (column, label, value, caption), marker in zip(cards, markers, strict=True):
        with column:
            st.markdown(
                f"""
                <div class="lotoia-kpi-card">
                    <div class="lotoia-kpi-marker">{marker}</div>
                    <div class="lotoia-kpi-label">{label}</div>
                    <div class="lotoia-kpi-value">{value}</div>
                    <div class="lotoia-kpi-caption">{caption}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
