"""Runtime Limpo ADM 15 — geração soberana CORE_002 / 15D (M-VIS-046 / M-VIS-047)."""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd
import streamlit as st

from dashboard.institutional_lei15a_governance import (
    LEI15A_FORMAL_STATUS,
    LEI15A_MANDATORY_QUOTE,
)
from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL

MISSION_ID = "M-VIS-047"

ADM_RUNTIME_ACTIVE_CARD_FORMAT = 15

GENERATOR_PAGE_TITLE = "Gerador ADM CORE_002"

CARD_FORMAT_DISPLAY_LABEL = "15 dezenas — CORE_002 soberano"

SOVEREIGN_RUNTIME_FORMAT_LABEL = CARD_FORMAT_DISPLAY_LABEL

STRATEGY_ML_ACTIVE = "CORE_002 + ML supervisionado"
STRATEGY_ML_INACTIVE = "CORE_002"

GENERATION_SHORT_DISCLAIMER = "Geração não constitui promessa de acerto."

POSTGRESQL_PERSISTENCE_LABEL = "Persistência obrigatória"

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

SIX_BASES_EXPANDER_SUMMARY = (
    "Leitura pelas 6 Bases permanece disponível na página **Cobertura Estrutural**. "
    "Hit isolado não é veredicto — o Núcleo é avaliado pelo conjunto das bases."
)

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
    "16 a 23 dezenas",
    "expansão auditada",
    "15 dezenas — Núcleo Lei 15",
)

REQUIRED_RUNTIME_PHRASES: tuple[str, ...] = (
    GENERATOR_PAGE_TITLE,
    "Geração ativa",
    "Operacional supervisionado",
    "Lei 15A",
    "Inoperante",
    POSTGRESQL_PERSISTENCE_LABEL,
    CARD_FORMAT_DISPLAY_LABEL,
    STRATEGY_ML_ACTIVE,
    GENERATION_SHORT_DISCLAIMER,
    "Detalhes de governança",
    "Detalhes técnicos",
    "Leitura Lei 15 / 6 Bases",
)

SOVEREIGN_RUNTIME_GAMES_COLUMN_LABELS = {
    "jogo": "Jogo",
    "núcleo_core_002": "Núcleo CORE_002 (15D)",
    "cartão_final": "Cartão final (15D)",
}


def render_generation_compact_header(*, ml_active: bool, generation_active: bool) -> None:
    """Cabeçalho compacto — operação primeiro."""
    st.markdown(f"### {GENERATOR_PAGE_TITLE}")
    cols = st.columns(4)
    cols[0].metric("Geração", "Ativa" if generation_active else "Bloqueada")
    cols[1].metric("ML", "Operacional supervisionado" if ml_active else "Inativo")
    cols[2].metric("Lei 15A", "Inoperante")
    cols[3].metric("PostgreSQL", POSTGRESQL_PERSISTENCE_LABEL)


def render_generation_operation_block(*, ml_active: bool) -> int:
    """Bloco principal: quantidade, formato, estratégia e botão."""
    st.markdown("#### Operação")
    op_cols = st.columns([1.2, 1.2, 1.2])
    with op_cols[0]:
        requested_count = int(
            st.selectbox(
                "Quantidade de jogos",
                [10, 20, 30, 50],
                index=1,
                key="clean_law15_requested_count",
            )
        )
    with op_cols[1]:
        st.selectbox(
            "Formato do cartão",
            options=[ADM_RUNTIME_ACTIVE_CARD_FORMAT],
            format_func=lambda _value: CARD_FORMAT_DISPLAY_LABEL,
            key="clean_law15_card_format_display",
        )
    with op_cols[2]:
        st.metric("Estratégia ativa", STRATEGY_ML_ACTIVE if ml_active else STRATEGY_ML_INACTIVE)
    st.caption(GENERATION_SHORT_DISCLAIMER)
    st.caption(f"Persistência: PostgreSQL · Label: `{BATCH_LABEL}`")
    generate_clicked = st.button("Gerar CORE_002 (15D)", type="primary", key="clean_law15_generate_button")
    st.session_state["clean_law15_card_format"] = ADM_RUNTIME_ACTIVE_CARD_FORMAT
    st.session_state["_clean_law15_generate_clicked"] = generate_clicked
    return requested_count


def render_generation_result_summary(
    result: dict[str, Any],
    *,
    diagnostics: dict[str, Any],
) -> None:
    """Resumo operacional pós-geração."""
    games = list(result.get("games") or [])
    persisted_id = result.get("generation_event_id")
    batch_label = str(result.get("analysis_batch_label") or BATCH_LABEL)
    persisted_count = int(result.get("games_count", len(games) if persisted_id else 0) or 0)
    persistence_status = (
        "Persistido"
        if persisted_id and not result.get("persistence_blocked")
        else ("Bloqueado" if result.get("persistence_blocked") else "Pendente")
    )
    st.markdown("#### Resultado da geração")
    summary_cols = st.columns(6)
    summary_cols[0].metric("generation_event_id", str(persisted_id or "-"))
    summary_cols[1].metric("batch_label", batch_label[-20:] if len(batch_label) > 20 else batch_label)
    summary_cols[2].metric("Solicitados", int(result.get("requested_count", 0) or 0))
    summary_cols[3].metric("Persistidos", persisted_count)
    summary_cols[4].metric("Gerados", len(games))
    summary_cols[5].metric("Persistência", persistence_status)
    st.caption(f"batch_label completo: `{batch_label}`")


def render_generation_games_table(
    games: list[dict[str, Any]],
    *,
    format_numbers: Callable[[list[int]], str],
    extract_numbers: Callable[[Any], list[int]],
) -> None:
    if not games:
        return
    rows: list[dict[str, str]] = []
    for index, game in enumerate(games):
        core_numbers = extract_numbers(game.get("core_numbers", game.get("numbers", [])))
        final_card_numbers = extract_numbers(game.get("final_card_numbers", game.get("numbers", [])))
        rows.append(
            {
                "jogo": str(index + 1),
                "núcleo_core_002": format_numbers(core_numbers),
                "cartão_final": format_numbers(final_card_numbers),
            }
        )
    st.dataframe(
        pd.DataFrame(rows).rename(columns=SOVEREIGN_RUNTIME_GAMES_COLUMN_LABELS),
        hide_index=True,
        use_container_width=True,
    )


def render_governance_expander(
    *,
    render_constitutional_panel: Callable[..., None],
) -> None:
    with st.expander("Detalhes de governança", expanded=False):
        render_constitutional_panel(compact=False)
        st.markdown(f"**{LEI15A_STATUS_HEADING}**")
        st.write(LEI15A_INOPERATIVE_NOTICE)
        st.caption(LEI15A_INOPERATIVE_DETAIL)
        st.caption(LEI15A_FUTURE_USE_NOTICE)
        st.caption(f"Status formal: {LEI15A_FORMAL_STATUS}")
        st.caption(LEI15A_MANDATORY_QUOTE)
        st.markdown(
            "- **CORE_002:** Núcleo soberano ativo\n"
            f"- **Label soberano:** `{BATCH_LABEL}`\n"
            "- **public_app:** fora do fluxo operacional\n"
            "- **purge:** bloqueado\n"
            "- **Lei 15A:** futura / subordinada / inoperante"
        )


def render_technical_expander(
    result: dict[str, Any],
    *,
    diagnostics: dict[str, Any],
) -> None:
    with st.expander("Detalhes técnicos", expanded=False):
        st.code(
            "generate_best_games(\n"
            "    count=...,\n"
            "    pool_size=...,\n"
            f"    batch_label={BATCH_LABEL!r},\n"
            f"    ml_enabled={bool(result.get('ml_enabled', False))},\n"
            ")",
            language="python",
        )
        st.json(
            {
                "sovereign_generation_path": result.get("sovereign_generation_path", "generate_best_games"),
                "ml_enabled": bool(result.get("ml_enabled", False)),
                "ml_operational_status": result.get("ml_operational_status"),
                "generation_mode": result.get("generation_mode"),
                "policy_mode": result.get("policy_mode"),
                "generation_event_id": result.get("generation_event_id"),
                "analysis_batch_label": result.get("analysis_batch_label", BATCH_LABEL),
                "fill_diagnostics": diagnostics,
            }
        )
        history = st.session_state.get("clean_law15_generation_history_snapshot") or {}
        ml_bundle_keys = ("decision_trace", "feature_attribution", "generation_lineage")
        for key in ml_bundle_keys:
            if result.get(key):
                st.markdown(f"**{key}**")
                st.json(result.get(key))
        if history:
            st.caption("Último snapshot de persistência (generation_events / generated_games)")
            st.json(history)


def render_six_bases_expander() -> None:
    with st.expander("Leitura Lei 15 / 6 Bases", expanded=False):
        st.write(SIX_BASES_EXPANDER_SUMMARY)
        st.caption("Consulte **Cobertura Estrutural** no menu institucional para drilldown completo.")


def render_lei15a_inoperative_notice(*, compact: bool = False) -> None:
    """Legado M-VIS-046 — usar render_governance_expander na página simplificada."""
    if compact:
        st.caption(LEI15A_INOPERATIVE_NOTICE)
        return
    st.markdown(f"##### {LEI15A_STATUS_HEADING}")
    st.info(LEI15A_INOPERATIVE_NOTICE)
    st.warning(LEI15A_INOPERATIVE_DETAIL)
    st.caption(LEI15A_FUTURE_USE_NOTICE)
    st.caption(f"Status formal: {LEI15A_FORMAL_STATUS}")
    with st.expander("Frase soberana M-GOV-038", expanded=False):
        st.write(LEI15A_MANDATORY_QUOTE)


def render_sovereign_runtime_format_panel() -> None:
    """Legado — substituído por render_generation_operation_block (M-VIS-047)."""
    st.caption(CARD_FORMAT_DISPLAY_LABEL)
    st.caption(SOVEREIGN_RUNTIME_ACTIVE_GENERATION_NOTICE)
