from __future__ import annotations

from typing import Any

import streamlit as st

from dashboard.clean_core import (
    _ensure_official_history_seeded,
    _render_analytical_page,
    _render_clean_law15_generation_page,
    get_clean_snapshot,
)


def _render_home(snapshot: dict[str, Any]) -> None:
    st.subheader("LotoIA Clean")
    st.write("App limpo separado, com núcleo institucional 15/17/18 e sem legado operacional.")
    cols = st.columns(4)
    cols[0].metric("Lei 15", "COMMANDER")
    cols[1].metric("Lei 17", "VALIDADORA 12+")
    cols[2].metric("Lei 18", "VALIDADORA 13+")
    cols[3].metric("Formato", "15 / 17 / 18")
    st.info(
        "Lei 15 gera base 11+ com busca por 14/15. "
        "Lei 17 valida 12+ com busca por 14/15. "
        "Lei 18 valida 13+ com busca por 14/15."
    )
    st.caption("17/18 dezenas são apenas expansão auditada: 15 + 2 reservas auditadas | 15 + 3 reservas auditadas.")


def main() -> None:
    st.set_page_config(page_title="LotoIA Clean", layout="wide")
    snapshot = get_clean_snapshot()
    _ensure_official_history_seeded()

    st.sidebar.title("LotoIA Clean")
    page = st.sidebar.radio(
        "Navegação",
        ["Início", "Gerador Limpo", "Histórico Analítico"],
        index=0,
    )

    if page == "Início":
        _render_home(snapshot)
    elif page == "Gerador Limpo":
        _render_clean_law15_generation_page(snapshot)
    elif page == "Histórico Analítico":
        _render_analytical_page(snapshot)


if __name__ == "__main__":
    main()
