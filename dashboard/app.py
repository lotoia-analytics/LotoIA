"""Streamlit Cloud entrypoint for the full institutional dashboard.

Keep this file intentionally small: Streamlit Cloud should run
`dashboard/app.py`, which delegates to `dashboard.admin_app.main`.
"""

from dashboard.admin_app import main


if __name__ == "__main__":
    main()
