from __future__ import annotations

import streamlit as st

from .design_system import render_institutional_design_system


def render_secondary_operational_metrics(
    gen_count: int,
    check_count: int,
    ml_count: int,
    last_contest: str,
    total_games: str,
    expansion_count: int = 0,
) -> None:
    render_institutional_design_system()
    with st.container(border=True):
        st.markdown("#### Operacao secundaria")
        st.markdown(
            """
            <div class="lotoia-secondary-shell lotoia-flow-panel" style="margin-bottom: 0.45rem;">
                <div class="lotoia-executive-kicker">Operacao secundaria</div>
                <div class="lotoia-executive-copy">Contadores operacionais mantidos em area compacta, sem competir com a visao geral.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        cards = [
            (col1, "Geracoes", gen_count, "Eventos persistidos em generation_events"),
            (col2, "Conferencias", check_count, "Eventos persistidos em check_events"),
            (col3, "ML", ml_count, "Geracoes com ML habilitado"),
            (col4, "Ultimo concurso", last_contest, "Maior concurso conferido"),
            (col5, "Jogos totais", total_games, "Total operacional registrado"),
            (col6, "Expansoes", expansion_count, "Eventos persistidos em expansion_events"),
        ]
        markers = ["◦", "◦", "◦", "◦", "◦", "◦"]
        for (column, label, value, caption), marker in zip(cards, markers, strict=True):
            with column:
                st.markdown(
                    f"""
                    <div class="lotoia-secondary-shell" style="padding: 0.85rem 0.85rem 0.7rem 0.85rem;">
                        <div style="font-size: 0.72rem; letter-spacing: 0.16em; text-transform: uppercase; color: #6b7f93; margin-bottom: 0.3rem;">{marker}</div>
                        <div style="font-size: 0.9rem; font-weight: 700; color: #123456; margin-bottom: 0.18rem;">{label}</div>
                        <div style="font-size: 1.15rem; font-weight: 800; color: #173b63; margin-bottom: 0.18rem;">{value}</div>
                        <div style="font-size: 0.82rem; color: #5a6b7c;">{caption}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
