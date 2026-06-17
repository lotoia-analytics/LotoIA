from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import streamlit as st
from sqlalchemy import delete, text

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from clean_core import (  # type: ignore
    DB_PATH,
    GeneratedGame,
    GenerationEvent,
    InstitutionalOutputSignature,
    ReconciliationRun,
    _ensure_analytical_games_schema,
    _expand_generation_games_for_format,
    _format_numbers_for_history,
    _load_accumulated_analytical_rows,
    _load_clean_generated_rows,
    _load_clean_institutional_events,
    _load_generated_games_for_reconciliation,
    _load_official_history_rows,
    _parse_numbers_text,
    run_clean_generation,
)

OFFICIAL_CARD_FORMATS = (15, 17, 18)
MENU_ITEMS = [
    "Gerar Jogos",
    "Conferir Resultados",
    "Simular Resultados",
    "Histórico Analítico",
    "Histórico Institucional",
    "Limpar Histórico",
    "Apagar Históricos",
]
OPERATIONS_ITEMS = ["Gerar Jogos", "Conferir Resultados", "Simular Resultados"]
HISTORY_ITEMS = [
    "Históricos Analíticos",
    "Histórico Institucional",
    "Limpar Histórico",
    "Apagar Históricos",
]


def _numbers_to_text(numbers: Iterable[int]) -> str:
    return " ".join(f"{int(number):02d}" for number in numbers)


def _parse_numbers_from_text(value: str | None) -> list[int]:
    return _parse_numbers_text(value)


def _hits(card_numbers: Iterable[int], result_numbers: Iterable[int]) -> int:
    return len(set(int(value) for value in card_numbers) & set(int(value) for value in result_numbers))


def _normalise_games_for_history() -> pd.DataFrame:
    rows = _load_accumulated_analytical_rows()
    df = _ensure_analytical_games_schema(pd.DataFrame(rows))
    if df.empty:
        return df
    return df


def _load_official_results() -> list[dict[str, Any]]:
    try:
        rows = _load_official_history_rows()
    except Exception:
        return []
    if rows:
        return rows
    return []


def _render_header() -> None:
    st.title("LotoIA Clean")
    st.subheader("Gerador limpo 15/17/18")
    st.info(
        "Lei 15 gera base 11+ com busca por 14/15. "
        "Lei 17 valida 12+ com busca por 14/15. "
        "Lei 18 valida 13+ com busca por 14/15."
    )


def _render_generator_block() -> dict[str, Any]:
    st.markdown("### Gerador")
    requested_count = int(st.selectbox("Quantidade de jogos", [10, 20, 30, 50], index=1, key="zero_requested_count"))
    st.session_state.setdefault("zero_card_format", 15)
    current_card_format = int(st.session_state.get("zero_card_format", 15) or 15)
    selected_card_format = int(
        st.selectbox(
            "Formato do cartao",
            options=list(OFFICIAL_CARD_FORMATS),
            index=list(OFFICIAL_CARD_FORMATS).index(current_card_format) if current_card_format in OFFICIAL_CARD_FORMATS else 0,
            format_func=lambda value: {
                15: "15 dezenas - Núcleo Lei 15",
                17: "17 dezenas - Lei 15 + 2 reservas auditadas",
                18: "18 dezenas - Lei 15 + 3 reservas auditadas",
            }.get(int(value), f"{int(value)} dezenas"),
            key="zero_card_format",
        )
    )

    left, right = st.columns(2)
    left.metric("Formato", f"{selected_card_format} dezenas")
    right.metric("Estratégia ativa", "Lei 15")

    if st.button("Gerar com Lei 15", type="primary", key="zero_generate_button"):
        st.session_state["zero_generation_result"] = run_clean_generation(
            requested_count=requested_count,
            selected_card_format=selected_card_format,
        )
        st.rerun()

    result = st.session_state.get("zero_generation_result") or {}
    diagnostics = dict(result.get("fill_diagnostics") or {})
    if result:
        st.success(
            f"Quantidade solicitada={result.get('requested_count', '-')}"
            f" | gerados={len(result.get('games') or [])}"
            f" | dezenas/jogo={result.get('dezenas_por_jogo', '-')}"
            f" | formato_cartao={result.get('selected_card_format', 15)}"
        )
        st.caption(
            " | ".join(
                [
                    f"generation_mode={result.get('generation_mode', '-')}",
                    f"policy_mode={result.get('policy_mode', '-')}",
                    f"scientific_law_role={result.get('scientific_law_role', '-')}",
                    f"clean_adm_runtime_role={result.get('clean_adm_runtime_role', '-')}",
                    f"output_commander_role={result.get('output_commander_role', '-')}",
                ]
            )
        )
        st.caption(
            " | ".join(
                [
                    f"historical_deduplication_mode={result.get('historical_deduplication_mode', '-')}",
                    f"historical_duplicates_removed={result.get('historical_duplicates_removed', '-')}",
                    f"legacy_generation_flow={result.get('legacy_generation_flow', '-')}",
                    f"legacy_dashboard_generation={result.get('legacy_dashboard_generation', '-')}",
                    f"legacy_calibrator_role={result.get('legacy_calibrator_role', '-')}",
                    f"calibration_engine_role={result.get('calibration_engine_role', '-')}",
                ]
            )
        )
        diag_cols = st.columns(4)
        diag_cols[0].metric("accepted_games", int(diagnostics.get("accepted_games", 0) or 0))
        diag_cols[1].metric("valid_candidates", int(diagnostics.get("valid_candidates_found", 0) or 0))
        diag_cols[2].metric("attempts_used", int(diagnostics.get("attempts_used", 0) or 0))
        diag_cols[3].metric("fill_completed", str(bool(diagnostics.get("fill_completed", False))))
        games = list(
            result.get("display_games")
            or _expand_generation_games_for_format(result.get("games") or [], int(result.get("selected_card_format", 15) or 15))
        )
        if games:
            st.markdown("#### Jogos gerados")
            games_df = pd.DataFrame(
                [
                    {
                        "jogo": index + 1,
                        "núcleo_lei_15": _numbers_to_text(game.get("core_numbers", game.get("numbers", []))),
                        "reservas_auditadas": " ".join(f"+{int(number):02d}" for number in game.get("audited_reserve_numbers", [])) or "-",
                        "cartão_final": _numbers_to_text(game.get("final_card_numbers", game.get("numbers", []))),
                    }
                    for index, game in enumerate(games)
                ]
            )
            st.dataframe(games_df, hide_index=True, use_container_width=True)
            st.caption(
                f"núcleo_lei_15=15 | formato_cartao={int(result.get('selected_card_format', 15) or 15)} | "
                f"reservas_auditadas={len(games[0].get('audited_reserve_numbers', []))} | "
                f"cartão_final={len(games[0].get('final_card_numbers', games[0].get('numbers', [])))}"
            )
    return result

def _render_metric_row(metrics: list[tuple[str, Any]]) -> None:
    columns = st.columns(len(metrics))
    for column, (label, value) in zip(columns, metrics, strict=False):
        with column:
            st.metric(label, value)


def _render_conferir_resultados() -> None:
    st.markdown("### Conferir Resultados")
    games = _load_generated_games_for_reconciliation()
    results = _load_official_results()
    reconciliations = _load_clean_institutional_events()
    _render_metric_row(
        [
            ("IMPORTED_CONTESTS", len(results)),
            ("GENERATED_GAMES", len(games)),
            ("RECONCILIATION_RUNS", sum(1 for event in reconciliations if event.get("event_type") == "Conferência institucional")),
        ]
    )
    st.caption("Compare os jogos gerados com o concurso selecionado no banco.")
    result_numbers: list[int] = []
    if results:
        contest_map = {f"{row['contest_number']} - {row.get('data', '')}": row for row in results}
        selected_label = st.selectbox(
            "Selecionar concurso",
            list(contest_map.keys()),
            index=0,
            key="zero_conferir_resultado",
        )
        result_numbers = contest_map[selected_label]["numbers"]
        st.caption(f"Dezenas oficiais: {_numbers_to_text(result_numbers)}")
    else:
        manual = st.text_input("Resultado oficial (15 dezenas)", key="zero_conferir_manual")
        result_numbers = _parse_numbers_from_text(manual)
        if len(result_numbers) != 15:
            st.warning("Resultado indisponível ou incompleto.")
    if st.button("Conferir Resultados", type="primary", key="zero_conferir_button"):
        if len(result_numbers) != 15:
            st.warning("Resultado indisponível ou incompleto.")
            return
        if not games:
            st.info("Ainda não há jogos persistidos no Clean Zero.")
            return
        rows = []
        for index, game in enumerate(games, start=1):
            final_card = list(game.get("final_card_numbers") or game.get("numbers") or [])
            core_numbers = list(game.get("core_numbers") or [])
            reserves = list(game.get("audited_reserve_numbers") or [])
            hits = _hits(final_card, result_numbers)
            rows.append(
                {
                    "jogo": index,
                    "núcleo_lei_15": _numbers_to_text(core_numbers),
                    "reservas_auditadas": " ".join(f"+{int(n):02d}" for n in reserves) or "-",
                    "cartão_final": _numbers_to_text(final_card),
                    "acertos": hits,
                }
            )
        df = pd.DataFrame(rows).sort_values(["acertos", "jogo"], ascending=[False, True])
        st.dataframe(df, hide_index=True, use_container_width=True)
        summary = df["acertos"].value_counts().reindex([11, 12, 13, 14, 15], fill_value=0)
        cards = st.columns(5)
        for column, hits in zip(cards, [11, 12, 13, 14, 15], strict=False):
            with column:
                st.metric(f"{hits} ACERTOS", int(summary.loc[hits]))
        st.caption(
            " | ".join(
                [
                    f"11+={int((df['acertos'] >= 11).sum())}",
                    f"12+={int((df['acertos'] >= 12).sum())}",
                    f"13+={int((df['acertos'] >= 13).sum())}",
                    f"14={int((df['acertos'] == 14).sum())}",
                    f"15={int((df['acertos'] == 15).sum())}",
                ]
            )
        )


def _render_simular_resultados() -> None:
    st.markdown("### Simular Resultados")
    games = _load_generated_games_for_reconciliation()
    reconciliations = _load_clean_institutional_events()
    last_event = reconciliations[0]["headline"] if reconciliations else "-"
    _render_metric_row(
        [
            ("GENERATED_GAMES", len(games)),
            ("IMPORTED_CONTESTS", len(_load_official_results())),
            ("LAST_EVENT", last_event),
            ("RUNTIME", "idle"),
        ]
    )
    st.caption("Digite as dezenas sorteadas para comparar com os jogos persistidos.")
    manual = st.text_area("Simular resultado de 15 dezenas", key="zero_simular_manual", height=80)
    result_numbers = _parse_numbers_from_text(manual)
    if len(result_numbers) != 15:
        st.warning("Digite 15 dezenas válidas para simular.")
    if st.button("Simular Resultados", type="primary", key="zero_simular_button"):
        if len(result_numbers) != 15:
            st.warning("Digite 15 dezenas válidas para simular.")
            return
        if not games:
            st.info("Nenhum jogo encontrado para simulação.")
            return
        rows = []
        for index, game in enumerate(games, start=1):
            final_card = list(game.get("final_card_numbers") or game.get("numbers") or [])
            hits = _hits(final_card, result_numbers)
            rows.append(
                {
                    "jogo": index,
                    "cartão_final": _numbers_to_text(final_card),
                    "acertos": hits,
                }
            )
        df = pd.DataFrame(rows).sort_values(["acertos", "jogo"], ascending=[False, True])
        st.dataframe(df, hide_index=True, use_container_width=True)


def _render_historico_analitico() -> None:
    st.markdown("### Histórico Analítico")
    rows = _load_accumulated_analytical_rows()
    if not rows:
        st.info("Histórico indisponível ou vazio.")
        return
    df = _ensure_analytical_games_schema(pd.DataFrame(rows))
    if df.empty:
        st.info("Histórico indisponível ou vazio.")
        return
    st.dataframe(
        df[
            [
                "data/hora",
                "formato_cartao",
                "núcleo_lei_15",
                "reservas_auditadas",
                "cartão_final",
                "quantidade_final",
                "batch_id",
                "estratégia",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )


def _render_historico_institucional() -> None:
    st.markdown("### Histórico Institucional")
    rows = _load_official_results()
    if not rows:
        st.info("Histórico institucional indisponível ou vazio.")
        return
    df = pd.DataFrame(rows)
    if df.empty:
        st.info("Histórico institucional indisponível ou vazio.")
        return
    df = df.rename(
        columns={
            "contest_number": "concurso",
            "data": "data",
            "dezenas": "dezenas_sorteadas",
            "source": "fonte",
        }
    )
    df["concurso"] = df["concurso"].astype(int)
    st.caption(f"Total de concursos: {len(df)} | Primeiro concurso: {df['concurso'].min()} | Último concurso: {df['concurso'].max()}")
    st.dataframe(
        df[["concurso", "data", "dezenas_sorteadas", "fonte"]],
        hide_index=True,
        use_container_width=True,
    )


def _render_limpar_historico() -> None:
    st.markdown("### Limpar Histórico")
    if st.button("Limpar visualização / filtros", key="zero_clear_session"):
        for key in [
            "zero_generation_result",
            "zero_requested_count",
            "zero_card_format",
            "zero_conferir_resultado",
            "zero_conferir_manual",
            "zero_simular_manual",
        ]:
            st.session_state.pop(key, None)
        st.success("Sessão limpa.")


def _count_rows(table_name: str) -> int:
    try:
        with st.spinner(f"Contando registros de {table_name}..."):
            from clean_core import get_session  # local import to keep startup light

            with get_session(DB_PATH) as session:
                return int(session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar() or 0)
    except Exception:
        return 0


def _delete_history_table(table_name: str) -> int:
    try:
        from clean_core import get_session  # local import to keep startup light
        from lotoia.governance.history_preservation_policy import assert_table_generic_purge_blocked

        assert_table_generic_purge_blocked(
            table_name=table_name,
            source="dashboard.lotoia_clean_zero._delete_history_table",
        )
        with get_session(DB_PATH) as session:
            count = int(session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar() or 0)
            session.execute(text(f"DELETE FROM {table_name}"))
            session.commit()
            return count
    except Exception:
        return 0


def _render_apagar_historicos() -> None:
    st.markdown("### Apagar Históricos")
    scope = st.radio(
        "Escopo",
        ["Histórico Analítico", "Histórico Institucional", "Ambos"],
        horizontal=True,
        key="zero_delete_scope",
    )
    confirmation = st.text_input("Digite APAGAR para confirmar", key="zero_delete_confirm")
    if st.button("Executar apagamento", type="primary", key="zero_delete_button"):
        if confirmation.strip().upper() != "APAGAR":
            st.error("Confirmação invalida.")
            return
        deleted_analytical = 0
        deleted_institutional = 0
        if scope in {"Histórico Analítico", "Ambos"}:
            deleted_analytical = _delete_history_table("generated_games")
            _delete_history_table("generation_events")
            _delete_history_table("institutional_output_signatures")
        if scope in {"Histórico Institucional", "Ambos"}:
            deleted_institutional = _delete_history_table("reconciliation_runs")
            _delete_history_table("reconciliation_games")
        st.warning(
            f"Apagamento executado. Analitico={deleted_analytical} | Institucional={deleted_institutional}"
        )


def _render_navigation() -> str:
    st.sidebar.title("LotoIA Clean Zero")
    if "zero_selected_menu" not in st.session_state:
        st.session_state["zero_selected_menu"] = "Gerar Jogos"

    def _nav_button(label: str, *, active: bool) -> None:
        if st.sidebar.button(
            label,
            key=f"zero_nav_{label}",
            use_container_width=False,
            type="primary" if active else "secondary",
        ):
            st.session_state["zero_selected_menu"] = label

    st.sidebar.markdown("#### OPERAÇÕES")
    for label in OPERATIONS_ITEMS:
        _nav_button(label, active=st.session_state["zero_selected_menu"] == label)
    st.sidebar.markdown("#### HISTÓRICOS")
    for label in HISTORY_ITEMS:
        _nav_button(label, active=st.session_state["zero_selected_menu"] == label)
    return st.session_state["zero_selected_menu"]


def main() -> None:
    st.set_page_config(page_title="LotoIA Clean Zero", layout="wide")
    menu = _render_navigation()
    if menu == "Gerar Jogos":
        _render_header()
        _render_generator_block()
    elif menu == "Conferir Resultados":
        _render_header()
        _render_conferir_resultados()
    elif menu == "Simular Resultados":
        _render_header()
        _render_simular_resultados()
    elif menu == "Históricos Analíticos":
        _render_header()
        _render_historico_analitico()
    elif menu == "Histórico Institucional":
        _render_header()
        _render_historico_institucional()
    elif menu == "Limpar Histórico":
        _render_header()
        _render_limpar_historico()
    elif menu == "Apagar Históricos":
        _render_header()
        _render_apagar_historicos()
    else:
        _render_header()
        _render_generator_block()


if __name__ == "__main__":
    main()
