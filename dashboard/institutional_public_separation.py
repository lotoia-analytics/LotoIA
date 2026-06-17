"""Governança read-only — separação public_app x ADM (M-PLAT-041)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.entrypoint_inventory import (
    ENV_DASHBOARD_MODE,
    build_entrypoint_inventory_snapshot,
)

SEPARATION_READ_ONLY_ALERT = (
    "Separação public_app x ADM — read-only. Nenhum entrypoint ou rota é alterado nesta seção."
)

PUBLIC_ADM_GUARDS: tuple[str, ...] = (
    "Railway produção: dashboard/institutional_app.py (ADM intacto).",
    "public_app.py default: canal público seguro — sem ADM completo.",
    f"Modo ADM via public_app somente com {ENV_DASHBOARD_MODE}=institutional explícito.",
    "public_app não expõe governança, histórico institucional, área restrita ou ML interno.",
    "public_app não executa geração, purge ou backtesting institucional.",
)


def render_public_adm_separation_section(*, app_build: str, public_build: str) -> None:
    """Bloco institucional — status separação public_app x ADM."""
    payload = build_entrypoint_inventory_snapshot(app_build=app_build, public_build=public_build)

    st.markdown("##### Separação public_app x ADM Institucional (M-PLAT-041)")
    st.info(SEPARATION_READ_ONLY_ALERT)
    st.success(payload["decision"])

    st.dataframe(
        pd.DataFrame(payload["entrypoints"]),
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("##### Guardas de separação")
    for guard in PUBLIC_ADM_GUARDS:
        st.markdown(f"- {guard}")

    st.caption(f"Documento: `{payload['inventory_doc']}`")
