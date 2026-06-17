"""Compat entrypoint — public_app x ADM separados (M-PLAT-041).

Railway produção usa `dashboard/institutional_app.py` diretamente (Procfile/railway.toml).
Este arquivo default=canal público seguro. Modo ADM somente via LOTOIA_DASHBOARD_MODE=institutional.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

import streamlit as st

from dashboard.entrypoint_inventory import ENV_DASHBOARD_MODE, resolve_dashboard_mode
from dashboard.public_surface import render_public_app


PUBLIC_APP_BUILD = "public-surface-v1-m-plat-041"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _configure_public_page() -> None:
    try:
        st.set_page_config(page_title="LotoIA — Canal Público", page_icon="L", layout="wide")
    except Exception:
        pass


def _render_public_boot_marker() -> None:
    mode = resolve_dashboard_mode()
    st.sidebar.caption(f"public_build={PUBLIC_APP_BUILD}")
    st.sidebar.caption(f"dashboard_mode={mode}")


def _render_institutional_import_failure(exc: BaseException) -> None:
    _configure_public_page()
    _render_public_boot_marker()
    st.sidebar.warning("Modo institucional solicitado — falha ao carregar ADM")
    st.error("Falha ao carregar o painel institucional.")
    st.caption(f"Tipo: {type(exc).__name__}")
    st.code(
        "".join(traceback.format_exception(type(exc), exc, exc.__traceback__, limit=30)),
        language="text",
    )


def render_institutional_adm() -> None:
    """Delegação explícita ao ADM — somente modo institutional autorizado."""
    from dashboard.institutional_app import main as institutional_main

    institutional_main()


def main() -> None:
    mode = resolve_dashboard_mode()
    _configure_public_page()
    _render_public_boot_marker()

    if mode == "institutional":
        st.sidebar.warning(
            f"Modo ADM ativo via `{ENV_DASHBOARD_MODE}=institutional`. "
            "Não use em canal público."
        )
        try:
            render_institutional_adm()
        except Exception as exc:
            _render_institutional_import_failure(exc)
        return

    render_public_app(public_build=PUBLIC_APP_BUILD)


if __name__ == "__main__":
    main()
