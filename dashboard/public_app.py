"""Compatibility entrypoint for Streamlit Cloud deployments.

Some Streamlit Cloud apps may still be configured to execute
`dashboard/public_app.py`. During the institutional cloud deployment, every
dashboard entrypoint must load the complete institutional admin dashboard.
"""


def main() -> None:
    from dashboard.admin_app import main as admin_main

    admin_main()


if __name__ == "__main__":
    main()
