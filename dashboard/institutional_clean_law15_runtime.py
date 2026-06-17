"""Runtime operacional ADM — geração CORE_002 (M-VIS-047)."""

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

GENERATOR_PAGE_TITLE = "Gerador ADM CORE_002"

MIN_REQUESTED_GAMES = 1
MAX_REQUESTED_GAMES = 100

MULTIDEZENA_FORMAT_OPTIONS: tuple[int, ...] = tuple(range(15, 24))
PERSISTENCE_SUPPORTED_FORMATS: frozenset[int] = frozenset({15})

STRATEGY_ML_ACTIVE = "CORE_002 + ML supervisionado"
STRATEGY_ML_INACTIVE = "CORE_002"

MULTIDEZENA_BLOCK_REASON = (
    "Persistência bloqueada para {format}D — motor CORE_002 gera núcleo 15D; "
    "formato multidezena {format}D sem persistência institucional validada nesta fase."
)

PROHIBITED_MAIN_PHRASES: tuple[str, ...] = (
    "Geração soberana controlada. Não constitui promessa de acerto.",
    "Lote rastreável via PostgreSQL",
    "Leitura operacional Lei 15A",
    "Lei 15 + 1 reserva auditada",
    "Lei 15 + 2 reservas auditadas",
    "reserva auditada",
    "15+1",
    "15+2",
    "15+3",
    "16 a 23 dezenas significam",
    "expansão auditada",
    "Lei 15A operacional",
)

REQUIRED_MAIN_PHRASES: tuple[str, ...] = (
    GENERATOR_PAGE_TITLE,
    STRATEGY_ML_ACTIVE,
    "Gerar lote",
    "Quantidade de jogos",
    "Quantidade de dezenas",
)


def multidezena_format_label(card_format: int) -> str:
    return f"{int(card_format)} dezenas — CORE_002"


def is_multidezena_persistence_supported(card_format: int) -> bool:
    return int(card_format) in PERSISTENCE_SUPPORTED_FORMATS


def validate_requested_games_count(raw_value: int | float | str | None) -> tuple[int | None, str | None]:
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None, f"Informe um número inteiro entre {MIN_REQUESTED_GAMES} e {MAX_REQUESTED_GAMES}."
    if value < MIN_REQUESTED_GAMES:
        return None, f"Quantidade mínima: {MIN_REQUESTED_GAMES}."
    if value > MAX_REQUESTED_GAMES:
        return None, f"Quantidade máxima: {MAX_REQUESTED_GAMES}."
    return value, None


def games_column_labels(card_format: int) -> dict[str, str]:
    suffix = f" ({int(card_format)}D)" if int(card_format) != 15 else " (15D)"
    return {
        "jogo": "Jogo",
        "núcleo_core_002": "Núcleo CORE_002",
        "cartão_final": f"Cartão final{suffix}",
    }


def render_compact_status_chips(*, ml_active: bool, generation_active: bool) -> None:
    chips = [
        "CORE_002 ativo" if generation_active else "CORE_002 bloqueado",
        "ML supervisionado ativo" if ml_active else "ML inativo",
        "Lei 15A inoperante",
    ]
    st.markdown(
        " · ".join(f"`{chip}`" for chip in chips),
        help="Status operacional compacto — detalhes em expansores.",
    )


def render_generation_operation_block(*, ml_active: bool) -> tuple[int, int]:
    """Bloco principal limpo — quantidade, dezenas, estratégia, botão."""
    col_qty, col_fmt, col_strategy = st.columns([1.1, 1.1, 1.2])
    with col_qty:
        raw_count = st.number_input(
            "Quantidade de jogos",
            min_value=MIN_REQUESTED_GAMES,
            max_value=MAX_REQUESTED_GAMES,
            value=int(st.session_state.get("clean_law15_requested_count", 20) or 20),
            step=1,
            key="clean_law15_requested_count_input",
        )
        requested_count, count_error = validate_requested_games_count(raw_count)
        if count_error:
            st.caption(count_error)
            requested_count = int(MIN_REQUESTED_GAMES)
    with col_fmt:
        selected_format = int(
            st.selectbox(
                "Quantidade de dezenas",
                options=list(MULTIDEZENA_FORMAT_OPTIONS),
                format_func=multidezena_format_label,
                index=0,
                key="clean_law15_card_format_select",
            )
        )
        if not is_multidezena_persistence_supported(selected_format):
            st.caption(MULTIDEZENA_BLOCK_REASON.format(format=selected_format))
    with col_strategy:
        st.metric("Estratégia ativa", STRATEGY_ML_ACTIVE if ml_active else STRATEGY_ML_INACTIVE)

    st.session_state["clean_law15_requested_count"] = int(requested_count or MIN_REQUESTED_GAMES)
    st.session_state["clean_law15_card_format"] = selected_format
    generate_clicked = st.button("Gerar lote", type="primary", key="clean_law15_generate_button")
    st.session_state["_clean_law15_generate_clicked"] = generate_clicked
    return int(requested_count or MIN_REQUESTED_GAMES), selected_format


def render_generation_result_summary(result: dict[str, Any]) -> None:
    games = list(result.get("games") or [])
    display_games = list(result.get("display_games") or games)
    persisted_id = result.get("generation_event_id")
    batch_label = str(result.get("analysis_batch_label") or BATCH_LABEL)
    requested = int(result.get("requested_count", 0) or 0)
    persisted_count = int(result.get("games_count", len(games) if persisted_id else 0) or 0)
    card_format = int(result.get("selected_card_format", 15) or 15)
    persistence_status = str(result.get("persistence_status_label") or "-")
    if result.get("persistence_blocked"):
        persistence_status = "Bloqueado"
    elif persisted_id:
        persistence_status = "Persistido"

    st.markdown("#### Resultado")
    cols = st.columns(5)
    cols[0].metric("generation_event_id", str(persisted_id or "-"))
    cols[1].metric("batch_label", batch_label[-22:] + "…" if len(batch_label) > 22 else batch_label)
    cols[2].metric("Solicitados", requested)
    cols[3].metric("Persistidos", persisted_count)
    cols[4].metric("Gerados", len(display_games))
    st.caption(
        f"formato={card_format}D | persistência={persistence_status} | "
        f"ml_enabled={bool(result.get('ml_enabled', False))}"
    )
    if result.get("persistence_block_reason"):
        st.warning(str(result.get("persistence_block_reason")))


def render_generation_games_table(
    games: list[dict[str, Any]],
    *,
    card_format: int,
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
        pd.DataFrame(rows).rename(columns=games_column_labels(card_format)),
        hide_index=True,
        use_container_width=True,
    )


def render_governance_expander(*, render_constitutional_panel: Callable[..., None]) -> None:
    with st.expander("Detalhes de governança", expanded=False):
        render_constitutional_panel(compact=True)
        st.caption(f"Lei 15A: inoperante · Status: {LEI15A_FORMAL_STATUS}")
        st.caption(LEI15A_MANDATORY_QUOTE)


def render_technical_expander(result: dict[str, Any], *, diagnostics: dict[str, Any]) -> None:
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
        st.caption("Geração não constitui promessa de acerto. Lote rastreável via PostgreSQL.")
        st.json(
            {
                "generation_mode": result.get("generation_mode"),
                "policy_mode": result.get("policy_mode"),
                "generation_event_id": result.get("generation_event_id"),
                "fill_diagnostics": diagnostics,
                "multidezena_format": result.get("selected_card_format"),
                "persistence_supported": is_multidezena_persistence_supported(
                    int(result.get("selected_card_format", 15) or 15)
                ),
            }
        )


def render_six_bases_expander() -> None:
    with st.expander("Leitura Lei 15 / 6 Bases", expanded=False):
        st.write("Consulte **Cobertura Estrutural** no menu institucional para drilldown completo.")
