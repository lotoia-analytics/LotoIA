admin = st.sidebar.checkbox(
    "Modo Admin"
)

if admin:

    st.subheader(
        "generation_events"
    )

    cursor.execute(
        "SELECT * FROM generation_events ORDER BY id DESC LIMIT 20"
    )

    st.dataframe(
        cursor.fetchall()
    )

    st.subheader(
        "check_events"
    )

    cursor.execute(
        "SELECT * FROM check_events ORDER BY id DESC LIMIT 20"
    )

    st.dataframe(
        cursor.fetchall()
    )
