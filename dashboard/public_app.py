from __future__ import annotations

try:
    from . import _bootstrap  # type: ignore[import-not-found]  # noqa: F401
except ImportError:
    import _bootstrap  # type: ignore[no-redef]  # noqa: F401

import re
import sqlite3
from pathlib import Path

import streamlit as st

from lotoia.public import (
    PublicCheckRequest,
    PublicGenerationRequest,
)
from lotoia.public.service import (
    PublicContestNotFoundError,
    PublicRateLimitError,
    check_public_contest,
    generate_public_games,
)

DB_PATH = Path("lotoia.db")
LOGO_PATH = Path("assets/logo.png")

conn = sqlite3.connect(
    DB_PATH,
    check_same_thread=False,
)

cursor = conn.cursor()

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        whatsapp TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS generation_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        whatsapp TEXT NOT NULL,
        seed INTEGER,
        strategy TEXT,
        ranking_score REAL,
        generated_numbers TEXT,
        execution_time_ms REAL,
        ml_enabled INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS check_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        whatsapp TEXT NOT NULL,
        contest_id INTEGER,
        checked_numbers TEXT,
        correct_numbers TEXT,
        hits INTEGER,
        execution_time_ms REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
)

conn.commit()


def _format_numbers(numbers: list[int]) -> str:
    return " ".join(
        f"{number:02d}"
        for number in numbers
    )


def validate_name(name: str) -> bool:

    cleaned = name.strip()

    if len(cleaned) < 3:
        return False

    if not re.fullmatch(
        r"[A-Za-zÀ-ÿ\s]+",
        cleaned,
    ):
        return False

    blocked_names = {
        "teste",
        "test",
        "admin",
        "usuario",
        "user",
        "aaa",
        "abc",
        "qwe",
        "xxx",
        "asdf",
    }

    if cleaned.lower() in blocked_names:
        return False

    return True


def validate_whatsapp(
    whatsapp: str,
) -> bool:

    if not whatsapp.isdigit():
        return False

    return len(whatsapp) in [10, 11]


def validate_numbers(
    numbers: list[int],
) -> tuple[bool, str]:

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

    invalid = [
        n
        for n in numbers
        if n < 1 or n > 25
    ]

    if invalid:
        return (
            False,
            "As dezenas devem estar entre 1 e 25.",
        )

    return True, ""


def persist_lead(
    first_name: str,
    whatsapp: str,
) -> None:
    cursor.execute(
        """
        INSERT INTO leads (
            first_name,
            whatsapp
        )
        VALUES (?, ?)
        """,
        (
            first_name,
            whatsapp,
        ),
    )

    conn.commit()


def render_logo() -> None:
    try:
        if LOGO_PATH.exists():
            st.image(
                str(LOGO_PATH),
                width=220,
            )
    except Exception:
        pass


def main() -> None:

    st.set_page_config(
        page_title="LotoIA",
        page_icon="assets/favicon.ico",
        layout="centered",
    )

    render_logo()

    tab_generate, tab_check = st.tabs(
        [
            "Gerar Jogos",
            "Conferir Concurso",
        ]
    )

    with tab_generate:

        first_name = st.text_input(
            "Primeiro nome",
            key="generate_first_name",
        )

        whatsapp = st.text_input(
            "WhatsApp",
            key="generate_whatsapp",
        )

        ml_enabled = st.toggle(
            "Ativar LotoIA",
            value=False,
        )

        if st.button(
            "Gerar",
            type="primary",
        ):

            if not validate_name(
                first_name
            ):
                st.warning(
                    "Digite um nome válido."
                )
                st.stop()

            if not validate_whatsapp(
                whatsapp
            ):
                st.warning(
                    "WhatsApp inválido."
                )
                st.stop()

            try:

                response = (
                    generate_public_games(
                        PublicGenerationRequest(
                            first_name=(
                                first_name.strip()
                            ),
                            whatsapp=(
                                whatsapp.strip()
                            ),
                            ml_enabled=(
                                ml_enabled
                            ),
                        ),
                        source=(
                            "public_streamlit"
                        ),
                        user_agent="streamlit",
                        limiter_key=(
                            f"streamlit:generate:{whatsapp}"
                        ),
                    )
                )

            except (
                PublicRateLimitError,
                ValueError,
            ) as exc:

                st.warning(str(exc))

            except Exception as exc:

                st.error(
                    f"Erro interno na geração: {exc}"
                )

            else:

                persist_lead(
                    first_name,
                    whatsapp,
                )

                metadata = response[
                    "metadata"
                ]

                for game in response["games"]:

                    generated_numbers = (
                        _format_numbers(
                            game["numbers"]
                        )
                    )

                    cursor.execute(
                        """
                        INSERT INTO generation_events (
                            first_name,
                            whatsapp,
                            seed,
                            strategy,
                            ranking_score,
                            generated_numbers,
                            execution_time_ms,
                            ml_enabled
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            first_name,
                            whatsapp,
                            metadata.get("seed"),
                            metadata.get(
                                "strategy"
                            ),
                            metadata.get(
                                "ranking_score"
                            ),
                            generated_numbers,
                            metadata.get(
                                "execution_time_ms"
                            ),
                            int(
                                metadata.get(
                                    "ml_enabled",
                                    False,
                                )
                            ),
                        ),
                    )

                conn.commit()

                for index, game in enumerate(
                    response["games"],
                    start=1,
                ):

                    st.subheader(
                        f"Jogo {index}"
                    )

                    st.write(
                        _format_numbers(
                            game["numbers"]
                        )
                    )

    with tab_check:

        first_name = st.text_input(
            "Primeiro nome",
            key="check_first_name",
        )

        whatsapp = st.text_input(
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
            placeholder="01 02 03 ... 15",
        )

        if st.button(
            "Conferir",
            type="primary",
        ):

            if not validate_name(
                first_name
            ):
                st.warning(
                    "Digite um nome válido."
                )
                st.stop()

            if not validate_whatsapp(
                whatsapp
            ):
                st.warning(
                    "WhatsApp inválido."
                )
                st.stop()

            try:

                numbers = [
                    int(item)
                    for item in (
                        numbers_text
                        .replace(",", " ")
                        .split()
                    )
                ]

            except ValueError:

                st.warning(
                    "Digite apenas números válidos."
                )
                st.stop()

            valid, message = (
                validate_numbers(
                    numbers
                )
            )

            if not valid:

                st.warning(message)
                st.stop()

            try:

                response = (
                    check_public_contest(
                        PublicCheckRequest(
                            first_name=(
                                first_name.strip()
                            ),
                            whatsapp=(
                                whatsapp.strip()
                            ),
                            contest_id=int(
                                contest_id
                            ),
                            numbers=numbers,
                        ),
                        source=(
                            "public_streamlit"
                        ),
                        user_agent="streamlit",
                        limiter_key=(
                            f"streamlit:check:{whatsapp}"
                        ),
                    )
                )

            except (
                PublicContestNotFoundError
            ) as exc:

                st.error(str(exc))

            except (
                PublicRateLimitError,
                ValueError,
            ) as exc:

                st.warning(str(exc))

            except Exception as exc:

                st.error(
                    f"Erro interno na conferência: {exc}"
                )

            else:

                result = response["result"]

                checked_numbers = (
                    _format_numbers(numbers)
                )

                correct_numbers = (
                    _format_numbers(
                        response[
                            "correct_numbers"
                        ]
                    )
                )

                cursor.execute(
                    """
                    INSERT INTO check_events (
                        first_name,
                        whatsapp,
                        contest_id,
                        checked_numbers,
                        correct_numbers,
                        hits,
                        execution_time_ms
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        first_name,
                        whatsapp,
                        result.get(
                            "contest_id"
                        ),
                        checked_numbers,
                        correct_numbers,
                        response.get(
                            "hits"
                        ),
                        result.get(
                            "execution_time_ms",
                            0,
                        ),
                    ),
                )

                conn.commit()

                st.metric(
                    "Acertos",
                    response["hits"],
                )

                st.success(
                    f'Você fez {response["hits"]} acertos.'
                )

                st.write(
                    f"Dezenas acertadas: {correct_numbers}"
                )


if __name__ == "__main__":
    main()
