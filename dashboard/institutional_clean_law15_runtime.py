"""Runtime Limpo ADM 15 — geração soberana CORE_002 / 15D (M-VIS-046)."""

from __future__ import annotations

import streamlit as st

from dashboard.institutional_lei15a_governance import (
    LEI15A_FORMAL_STATUS,
    LEI15A_MANDATORY_QUOTE,
)
from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL

MISSION_ID = "M-VIS-046"

ADM_RUNTIME_ACTIVE_CARD_FORMAT = 15

SOVEREIGN_RUNTIME_FORMAT_LABEL = (
    "15D — CORE_002 soberano (label STRUCT_LEI15_CORE_CANDIDATE_002_15D_001)"
)

SOVEREIGN_RUNTIME_ACTIVE_GENERATION_NOTICE = (
    "A geração ativa nesta fase é exclusivamente CORE_002 / 15D / label soberano."
)

LEI15A_INOPERATIVE_NOTICE = (
    "Lei 15A — camada futura subordinada ao CORE_002, inoperante no momento."
)

LEI15A_INOPERATIVE_DETAIL = (
    "Lei 15A não gera, não expande, não altera Núcleo e não ativa 15+1/15+2."
)

LEI15A_FUTURE_USE_NOTICE = (
    "Qualquer uso futuro da Lei 15A exige missão própria, ADR/governança, testes "
    "e autorização institucional."
)

LEI15A_STATUS_HEADING = "Status Lei 15A — futura e inoperante"

PROHIBITED_RUNTIME_PHRASES: tuple[str, ...] = (
    "Leitura operacional Lei 15A",
    "Lei 15 + 1 reserva auditada",
    "Lei 15 + 2 reservas auditadas",
    "Lei 15 + 3 reservas auditadas",
    "Lei 15 + 4 reservas auditadas",
    "Lei 15 + 5 reservas auditadas",
    "Lei 15 + 6 reservas auditadas",
    "15+1",
    "15+2",
    "15+3",
    "Lei 15A operacional",
    "Lei 15A = operação GP",
)

REQUIRED_RUNTIME_PHRASES: tuple[str, ...] = (
    LEI15A_INOPERATIVE_NOTICE,
    SOVEREIGN_RUNTIME_ACTIVE_GENERATION_NOTICE,
    LEI15A_INOPERATIVE_DETAIL,
    LEI15A_FUTURE_USE_NOTICE,
    SOVEREIGN_RUNTIME_FORMAT_LABEL,
)

SOVEREIGN_RUNTIME_GAMES_COLUMN_LABELS = {
    "jogo": "Jogo",
    "núcleo_core_002": "Núcleo CORE_002 (15D)",
    "cartão_final": "Cartão final (15D)",
}


def render_lei15a_inoperative_notice(*, compact: bool = False) -> None:
    """Bloco constitucional read-only — Lei 15A futura/inoperante."""
    st.markdown(f"##### {LEI15A_STATUS_HEADING}")
    st.info(LEI15A_INOPERATIVE_NOTICE)
    st.warning(LEI15A_INOPERATIVE_DETAIL)
    st.caption(LEI15A_FUTURE_USE_NOTICE)
    if not compact:
        st.caption(f"Status formal: {LEI15A_FORMAL_STATUS}")
        with st.expander("Frase soberana M-GOV-038", expanded=False):
            st.write(LEI15A_MANDATORY_QUOTE)


def render_sovereign_runtime_format_panel() -> None:
    """Painel fixo 15D — sem selectbox operacional Lei 15A."""
    st.markdown("##### Formato do cartão — fase CORE_002")
    st.success(SOVEREIGN_RUNTIME_FORMAT_LABEL)
    st.caption(SOVEREIGN_RUNTIME_ACTIVE_GENERATION_NOTICE)
    st.caption(f"Label soberano obrigatório: `{BATCH_LABEL}`")
    st.caption("Formatos 16D–23D indisponíveis nesta fase — expansão Lei 15A inoperante.")
