from pathlib import Path
import sqlite3

import pandas as pd
import streamlit as st


DATABASE_PATH = (
    Path(__file__).resolve().parents[1]
    / "lotoia.db"
)


st.set_page_config(
    page_title="LotoIA Admin",
    layout="wide",
)

st.title(
    "LotoIA • Admin Dashboard"
)


password = st.text_input(
    "Senha Admin",
    type="password",
)

if password != "LotoIAAdmin":

    st.warning(
        "Acesso restrito."
    )

    st.stop()


conn = sqlite3.connect(
    DATABASE_PATH
)


st.header(
    "Gerar Jogos"
)

generation_df = pd.read_sql_query(
    """
    SELECT *
    FROM generation_events
    ORDER BY id DESC
    """,
    conn,
)

st.dataframe(
    generation_df,
    use_container_width=True,
)


st.header(
    "Conferir Concurso"
)

check_df = pd.read_sql_query(
    """
    SELECT *
    FROM check_events
    ORDER BY id DESC
    """,
    conn,
)

st.dataframe(
    check_df,
    use_container_width=True,
)


conn.close()