from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from dashboard.clean_core import (
    _database_snapshot,
    _ensure_analytical_games_schema,
    _ensure_official_history_seeded,
    _expand_generation_games_for_format,
    _load_accumulated_analytical_rows,
    get_clean_snapshot,
    run_clean_generation,
)


OFFICIAL_CARD_FORMATS = (15, 17, 18)


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
    st.caption(f"Backend: {snapshot.get('backend', '-')}")


def _render_clean_generator_page(snapshot: dict[str, Any]) -> None:
    st.subheader("Gerador LotoIA Clean")
    st.caption("Página independente do app atual, focada apenas no núcleo institucional aprovado.")
    st.markdown("##### Runtime Limpo ADM 15")
    requested_count = int(st.selectbox("Quantidade de jogos", [10, 20, 30, 50], index=1, key="clean_law15_requested_count"))
    st.session_state.setdefault("clean_law15_card_format", 15)
    current_card_format = int(st.session_state.get("clean_law15_card_format", 15) or 15)
    selected_card_format = int(
        st.selectbox(
            "Formato do cartão",
            options=list(OFFICIAL_CARD_FORMATS),
            index=list(OFFICIAL_CARD_FORMATS).index(current_card_format) if current_card_format in OFFICIAL_CARD_FORMATS else 0,
            format_func=lambda value: {
                15: "15 dezenas — Núcleo Lei 15",
                17: "17 dezenas — Lei 15 + 2 reservas auditadas",
                18: "18 dezenas — Lei 15 + 3 reservas auditadas",
            }.get(int(value), f"{int(value)} dezenas"),
            key="clean_law15_card_format",
        )
    )
    left, right = st.columns(2)
    left.metric("Formato", f"{selected_card_format} dezenas")
    right.metric("Estratégia ativa", "Lei 15")
    st.info(
        "Lei 15 gera base 11+ com busca por 14/15. "
        "Lei 17 valida 12+ com busca por 14/15. "
        "Lei 18 valida 13+ com busca por 14/15."
    )
    st.caption(
        "17/18 dezenas significam apenas expansão auditada do núcleo: 15 + 2 reservas auditadas | 15 + 3 reservas auditadas."
    )

    if st.button("Gerar com Lei 15", type="primary", key="clean_law15_generate_button"):
        st.session_state["clean_law15_generation_result"] = run_clean_generation(
            requested_count=requested_count,
            selected_card_format=selected_card_format,
        )
        st.rerun()

    result = st.session_state.get("clean_law15_generation_result") or {}
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
                    f"batch_fill_strategy={result.get('batch_fill_strategy', '-')}",
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

        games = list(result.get("display_games") or _expand_generation_games_for_format(result.get("games") or [], int(result.get("selected_card_format", 15) or 15)))
        if games:
            st.markdown("#### Jogos gerados")
            games_df = pd.DataFrame(
                [
                    {
                        "jogo": index + 1,
                        "núcleo_lei_15": " ".join(f"{int(number):02d}" for number in game.get("core_numbers", game.get("numbers", []))),
                        "reservas_auditadas": " ".join(f"+{int(number):02d}" for number in game.get("audited_reserve_numbers", [])) or "-",
                        "cartão_final": " ".join(f"{int(number):02d}" for number in game.get("final_card_numbers", game.get("numbers", []))),
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


def _render_analytical_page(snapshot: dict[str, Any]) -> None:
    st.subheader("Histórico Analítico")
    st.write("Visão acumulativa dos jogos persistidos no histórico do novo app limpo.")

    rows = _load_accumulated_analytical_rows()
    if not rows:
        st.info("Ainda não há gerações persistidas para reconstruir o histórico analítico.")
        return

    df = _ensure_analytical_games_schema(pd.DataFrame(rows))
    if df.empty:
        st.info("Ainda não há jogos persistidos para reconstruir o histórico analítico.")
        return

    st.caption(f"Total de linhas: {len(df)} | backend: {snapshot.get('backend', '-')}")
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
                "score",
                "status de conferência",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )


def main() -> None:
    st.set_page_config(page_title="LotoIA Clean", layout="wide")
    _ensure_official_history_seeded()
    snapshot = get_clean_snapshot()

    st.sidebar.title("LotoIA Clean")
    page = st.sidebar.radio(
        "Navegação",
        ["Início", "Gerador Limpo", "Histórico Analítico"],
        index=0,
    )

    if page == "Início":
        _render_home(snapshot)
    elif page == "Gerador Limpo":
        _render_clean_generator_page(snapshot)
    elif page == "Histórico Analítico":
        _render_analytical_page(snapshot)


if __name__ == "__main__":
    main()
