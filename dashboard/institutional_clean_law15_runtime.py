"""Runtime operacional ADM — geração CORE_002 (M-VIS-047)."""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd
import streamlit as st

from dashboard.institutional_lei15a_governance import (
    LEI15A_FORMAL_STATUS,
    LEI15A_MANDATORY_QUOTE,
)
from lotoia.governance.lei15_core_002_sovereign import (
    BATCH_LABEL,
    resolve_core_002_batch_label,
)

MISSION_ID = "M-VIS-047"

GENERATOR_PAGE_TITLE = "Gerador ADM CORE_002"

MIN_REQUESTED_GAMES = 1
MAX_REQUESTED_GAMES = 100

MULTIDEZENA_FORMAT_OPTIONS: tuple[int, ...] = tuple(range(15, 24))
PERSISTENCE_SUPPORTED_FORMATS: frozenset[int] = frozenset(range(15, 24))

STRATEGY_ML_ACTIVE = "CORE_002 + ML supervisionado"
STRATEGY_ML_INACTIVE = "CORE_002 soberano direto"

MULTIDEZENA_PERSISTENCE_INFO = "Formato {format}D — persistência CORE_002 multidezena subordinada ao núcleo 15D (PostgreSQL)."

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


def multidezena_batch_label(card_format: int) -> str:
    return resolve_core_002_batch_label(int(card_format))


def validate_requested_games_count(
    raw_value: int | float | str | None,
) -> tuple[int | None, str | None]:
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return (
            None,
            f"Informe um número inteiro entre {MIN_REQUESTED_GAMES} e {MAX_REQUESTED_GAMES}.",
        )
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
        "CORE_002 soberano" if generation_active else "CORE_002 bloqueado",
        "ML analítico" if not ml_active else "ML supervisionado",
    ]
    st.markdown(
        " · ".join(f"`{chip}`" for chip in chips),
        help="Status operacional compacto — detalhes em expansores.",
    )


def render_generation_operation_block(
    *,
    ml_active: bool,
    latest_contest_number: int | None = None,
) -> tuple[int, int, int | None]:
    """Bloco principal limpo — quantidade, dezenas, concurso alvo, estratégia, botão.

    Returns (requested_count, selected_format, user_target_contest).
    user_target_contest é None quando o usuário escolheu "Automático (próximo)".
    """
    col_qty, col_fmt, col_target = st.columns([1.1, 1.1, 1.2])
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
        if is_multidezena_persistence_supported(selected_format):
            st.caption(MULTIDEZENA_PERSISTENCE_INFO.format(format=selected_format))
    with col_target:
        default_target = (
            int(latest_contest_number) + 1
            if latest_contest_number and latest_contest_number > 0
            else 1
        )
        target_min = max(1, int(latest_contest_number or 0) - 300)
        target_max = max(default_target, int(latest_contest_number or 0) + 10)
        target_options = ["Automático (próximo)"] + [
            f"Concurso {i}" for i in range(target_min, target_max + 1)
        ]
        target_choice = st.selectbox(
            "Concurso alvo",
            options=target_options,
            key="clean_law15_target_contest_select",
            help=(
                "Automático: gera para o próximo concurso (latest+1). "
                "Ou escolha um concurso específico (passado ou futuro) para gerar e conferir imediatamente."
            ),
        )
        if target_choice == "Automático (próximo)":
            user_target_contest = None
        else:
            user_target_contest = int(target_choice.replace("Concurso ", ""))
        st.metric(
            "Estratégia ativa",
            STRATEGY_ML_ACTIVE if ml_active else STRATEGY_ML_INACTIVE,
        )

    st.session_state["clean_law15_requested_count"] = int(
        requested_count or MIN_REQUESTED_GAMES
    )
    st.session_state["clean_law15_card_format"] = selected_format
    st.session_state["clean_law15_user_target_contest"] = user_target_contest
    generate_clicked = st.button(
        "Gerar lote", type="primary", key="clean_law15_generate_button"
    )
    st.session_state["_clean_law15_generate_clicked"] = generate_clicked
    return (
        int(requested_count or MIN_REQUESTED_GAMES),
        selected_format,
        user_target_contest,
    )


def render_agent_operador_ml_summary(result: dict[str, Any]) -> None:
    """Resumo discreto do agent_operador_ml após geração GP (M-AGENT-002)."""
    from lotoia.ml.agent_operador_ml_executor import build_agent_operador_ml_ui_summary

    summary = build_agent_operador_ml_ui_summary(
        dict(result.get("agent_operador_ml") or {})
    )
    if not summary.get("visible"):
        return

    st.markdown("#### Agent Operador ML")
    cols = st.columns(5)
    cols[0].metric("Status entrega", str(summary.get("status") or "-"))
    cols[1].metric("Solicitados", int(summary.get("requested", 0) or 0))
    cols[2].metric("Entregues", int(summary.get("delivered", 0) or 0))
    cols[3].metric("Ação corretiva", str(summary.get("primary_action") or "-")[:18])
    cols[4].metric("trace_id", str(summary.get("trace_id") or "-")[-12:])
    st.caption(str(summary.get("improvement") or ""))
    with st.expander("Detalhes técnicos — agent_operador_ml", expanded=False):
        trace = dict(summary.get("trace") or {})
        st.json(
            {
                "gp_delivery_status": trace.get("gp_delivery_status"),
                "agent_attempts_count": trace.get("agent_attempts_count"),
                "agent_actions_applied": trace.get("agent_actions_applied"),
                "agent_before_metrics": trace.get("agent_before_metrics"),
                "agent_after_metrics": trace.get("agent_after_metrics"),
                "agent_improvement_summary": trace.get("agent_improvement_summary"),
                "gp_failure_evidence": trace.get("gp_failure_evidence"),
            }
        )


def render_generation_result_summary(result: dict[str, Any]) -> None:
    games = list(result.get("games") or [])
    display_games = list(result.get("display_games") or games)
    persisted_id = result.get("generation_event_id")
    batch_label = str(result.get("analysis_batch_label") or BATCH_LABEL)
    requested = int(result.get("requested_count", 0) or 0)
    persisted_count = int(
        result.get("games_count", len(games) if persisted_id else 0) or 0
    )
    card_format = int(result.get("selected_card_format", 15) or 15)
    persistence_status = str(result.get("persistence_status_label") or "-")
    if result.get("persistence_blocked"):
        persistence_status = "Bloqueado"
    elif persisted_id:
        persistence_status = "Persistido"

    st.markdown("#### Resultado")
    cols = st.columns(6)
    operational_label = str(result.get("operational_generation_label") or "-")
    cols[0].metric("Geração operacional", operational_label)
    cols[1].metric("generation_event_id", str(persisted_id or "-"))
    cols[2].metric(
        "batch_label", batch_label[-22:] + "…" if len(batch_label) > 22 else batch_label
    )
    cols[3].metric("Solicitados", requested)
    cols[4].metric("Persistidos", persisted_count)
    cols[5].metric("Gerados", len(display_games))
    st.caption(
        f"formato={card_format}D | persistência={persistence_status} | "
        f"ml_enabled={bool(result.get('ml_enabled', False))}"
    )
    if result.get("persistence_block_reason"):
        st.warning(str(result.get("persistence_block_reason")))
    elif int(card_format) > 15 and persisted_id:
        st.caption(
            f"Multidezena {card_format}D persistida — subordinada ao CORE_002, não Lei 15A."
        )


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
        core_numbers = extract_numbers(
            game.get("core_numbers", game.get("numbers", []))
        )
        final_card_numbers = extract_numbers(
            game.get("final_card_numbers", game.get("numbers", []))
        )
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


def render_governance_expander(
    *, render_constitutional_panel: Callable[..., None]
) -> None:
    with st.expander("Detalhes de governança", expanded=False):
        render_constitutional_panel(compact=True)
        st.caption(f"Lei 15A: inoperante · Status: {LEI15A_FORMAL_STATUS}")
        st.caption(LEI15A_MANDATORY_QUOTE)


def render_technical_expander(
    result: dict[str, Any], *, diagnostics: dict[str, Any]
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
        st.caption(
            "Geração não constitui promessa de acerto. Lote rastreável via PostgreSQL."
        )
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
        st.write(
            "Consulte **Cobertura Estrutural** no menu institucional para drilldown completo."
        )
