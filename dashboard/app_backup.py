def main() -> None:
    try:
        icon = Image.open(FAVICON_PATH)

        st.set_page_config(
            page_title="LotoIA",
            page_icon=icon,
            layout="wide",
        )

    except Exception:
        st.set_page_config(
            page_title="LotoIA",
            layout="wide",
        )

    try:
        if LOGO_PATH.exists():
            st.image(
                str(LOGO_PATH),
                width=700,
            )
    except Exception:
        pass

    st.caption("Plataforma analítica para LOTOFÁCIL")

    try:
        draws = _load_draws()

    except FileNotFoundError:
        st.warning(
            "Arquivo historico da LOTOFACIL nao encontrado. "
            f"Coloque o CSV em `{DEFAULT_HISTORY_PATH}` usando as colunas "
            "`concurso,data,d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14,d15`."
        )
        st.stop()

    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    page = st.sidebar.radio(
        "Navegação",
        options=PAGES,
        format_func=lambda k: LABELS.get(k, k),
    )

    if page == "geracao_jogos":
        render_generation_page()

    elif page == "estatisticas_historicas":
        render_statistics_page(draws)

    elif page == "backtesting":
        render_backtesting_page()

    elif page == "calibracao_experimental":
        render_calibration_page()

    elif page == "benchmark_cientifico":
        render_benchmark_page()

    elif page == "historico_experimental":
        render_history_page()

    elif page == "relatorios":
        render_reports_page()