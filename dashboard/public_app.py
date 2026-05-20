from __future__ import annotations

try:
    from . import _bootstrap
except ImportError:
    import _bootstrap

import sqlite3
from pathlib import Path

import streamlit as st

from lotoia.public import (
    PublicCheckRequest,
    PublicGenerationRequest,
)

from lotoia.public.service import (
    PublicContestNotFoundError,
    check_public_contest,
    find_historical_matches,
    generate_public_games,
)

DB_PATH = Path("lotoia.db")

conn = sqlite3.connect(
    DB_PATH,
    check_same_thread=False,
)

cursor = conn.cursor()


def _format_numbers(
    numbers: list[int],
) -> str:

    return " ".join(
        f"{number:02d}"
        for number in numbers
    )


def validate_numbers(
    numbers: list[int],
):

    if len(numbers) != 15:

        return (
            False,
            "Digite exatamente 15 dezenas.",
        )

    if len(set(numbers)) != 15:

        return (
            False,
            "Existem dezenas repetidas.",
        )

    return True, ""


st.set_page_config(
    page_title="LotoIA",
    layout="centered",
)

st.title("LotoIA")

tab_generate, tab_check = st.tabs(
    [
        "Gerar Jogos",
        "Conferir Concurso",
    ]
)

# =========================================================
# GERAR JOGOS
# =========================================================

with tab_generate:

    first_name = st.text_input(
        "Primeiro nome",
        key="generate_name",
    )

    whatsapp = st.text_input(
        "WhatsApp",
        key="generate_whatsapp",
    )

    ml_enabled = st.toggle(
        "Ativar LotoIA",
        value=False,
    )

    generate_clicked = st.button(
        "Gerar",
        type="primary",
    )

    if generate_clicked:

        try:

            response = (
                generate_public_games(
                    PublicGenerationRequest(
                        first_name=first_name,
                        whatsapp=whatsapp,
                        ml_enabled=ml_enabled,
                    ),
                    source="streamlit",
                    user_agent="browser",
                    limiter_key=whatsapp,
                )
            )

            games = response["games"]

            for index, game in enumerate(
                games,
                start=1,
            ):

                with st.container():

                    st.divider()

                    st.subheader(
                        f"Jogo {index}"
                    )

                    formatted_numbers = (
                        _format_numbers(
                            game["numbers"]
                        )
                    )

                    st.code(
                        formatted_numbers
                    )

                    history_result = (
                        find_historical_matches(
                            game["numbers"]
                        )
                    )

                    if history_result[
                        "is_repeated"
                    ]:

                        st.warning(
                            (
                                f"⚠ Esta combinação "
                                f"já ocorreu "
                                f"{history_result['total_matches']} "
                                f"vez(es)."
                            )
                        )

                        for match in history_result[
                            "matches"
                        ]:

                            st.write(
                                (
                                    f"Concurso "
                                    f"{match['contest']} "
                                    f"- "
                                    f"{match['date']}"
                                )
                            )

                    else:

                        st.success(
                            "✔ Combinação inédita."
                        )

        except Exception as exc:

            st.error(
                f"Erro interno: {exc}"
            )

# =========================================================
# CONFERIR CONCURSO
# =========================================================

with tab_check:

    first_name_check = st.text_input(
        "Primeiro nome",
        key="check_name",
    )

    whatsapp_check = st.text_input(
        "WhatsApp",
        key="check_whatsapp",
    )

    contest_id = st.number_input(
        "Concurso",
        min_value=1,
        step=1,
    )

    numbers_text = st.text_input(
        "Dezenas",
        placeholder="01 02 03 04 ...",
    )

    check_clicked = st.button(
        "Conferir",
        type="primary",
    )

    if check_clicked:

        try:

            numbers = [
                int(item)
                for item in (
                    numbers_text
                    .replace(",", " ")
                    .split()
                )
            ]

            valid, message = (
                validate_numbers(
                    numbers
                )
            )

            if not valid:

                st.warning(message)

            else:

                response = (
                    check_public_contest(
                        PublicCheckRequest(
                            first_name=(
                                first_name_check
                            ),
                            whatsapp=(
                                whatsapp_check
                            ),
                            contest_id=int(
                                contest_id
                            ),
                            numbers=numbers,
                        ),
                        source="streamlit",
                        user_agent="browser",
                        limiter_key=(
                            f"check:{whatsapp_check}"
                        ),
                    )
                )

                st.metric(
                    "Acertos",
                    response["hits"],
                )

                st.success(
                    (
                        f"Você fez "
                        f"{response['hits']} "
                        f"acertos."
                    )
                )

                st.write(
                    (
                        "Dezenas sorteadas: "
                        f"{_format_numbers(response['correct_numbers'])}"
                    )
                )

        except (
            PublicContestNotFoundError
        ) as exc:

            st.error(str(exc))

        except Exception as exc:

            st.error(
                f"Erro interno: {exc}"
            )
