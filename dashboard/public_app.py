"""Compatibility entrypoint for Streamlit Cloud deployments.

Some Streamlit Cloud apps may still be configured to execute
`dashboard/public_app.py`. During the institutional cloud deployment, every
dashboard entrypoint must load the complete institutional admin dashboard.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

import streamlit as st


PUBLIC_APP_BUILD = "9d35eb2"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _configure_public_page() -> None:
    try:
        st.set_page_config(page_title="LotoIA", page_icon="L", layout="wide")
    except Exception:
        pass


def _render_public_boot_marker() -> None:
    st.sidebar.caption(f"public_build={PUBLIC_APP_BUILD}")


def _render_admin_import_failure(exc: BaseException) -> None:
    _configure_public_page()
    _render_public_boot_marker()
    st.sidebar.warning("Entrypoint publico ativo")
    st.error("Falha ao carregar o painel institucional.")
    st.caption(f"Tipo: {type(exc).__name__}")
    st.code(
        "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__, limit=30)
        ),
        language="text",
    )


def main() -> None:
    _configure_public_page()
    _render_public_boot_marker()
    try:
        from dashboard.admin_app import main as admin_main
    except Exception as exc:
        _render_admin_import_failure(exc)
        return

    admin_main()


if __name__ == "__main__":
    main()
