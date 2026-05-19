from __future__ import annotations

try:
    from . import _bootstrap  # type: ignore[import-not-found]  # noqa: F401
except ImportError:
    import _bootstrap  # type: ignore[no-redef]  # noqa: F401

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
            try:
                response = generate_public_games(
                    PublicGenerationRequest(
                        first_name=first_name.strip(),
                        whatsapp=whatsapp.strip(),
                        ml_enabled=ml_enabled,
                    ),
                    source="public_streamlit",
                    user_agent="streamlit",
                    limiter_key=(
                        f"streamlit:generate:{whatsapp}"
                    ),
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

                metadata = response["metadata"]

                cursor.execute(
                    """
                    INSERT INTO generation_events (
                        first_name,
                        whatsapp,
                        seed,
                        strategy,
                        ranking_score,
                        execution_time_ms,
                        ml_enabled
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        first_name,
                        whatsapp,
                        metadata.get("seed"),
                        metadata.get("strategy"),
                        metadata.get(
                            "ranking_score"
                        ),
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

                st.json(metadata)

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
            try:
                numbers = [
                    int(item)
                    for item in (
                        numbers_text
                        .replace(",", " ")
                        .split()
                    )
                ]

                response = check_public_contest(
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
                    source="public_streamlit",
                    user_agent="streamlit",
                    limiter_key=(
                        f"streamlit:check:{whatsapp}"
                    ),
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

                cursor.execute(
                    """
                    INSERT INTO check_events (
                        first_name,
                        whatsapp,
                        contest_id,
                        hits,
                        execution_time_ms
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        first_name,
                        whatsapp,
                        result.get(
                            "contest_id"
                        ),
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

                st.write(
                    _format_numbers(
                        response[
                            "correct_numbers"
                        ]
                    )
                )

            st.success(f'Você fez {response["hits"]} acertos.')

acertos = " • ".join(response["correct_numbers"])

st.write(f"Dezenas acertadas: {acertos}")


if __name__ == "__main__":
    main()
