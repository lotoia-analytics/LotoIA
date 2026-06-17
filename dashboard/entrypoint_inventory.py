"""Inventário de entrypoints Streamlit — public_app x ADM (M-PLAT-041)."""

from __future__ import annotations

import os
from typing import Any, Literal

DashboardMode = Literal["public", "institutional"]

ENV_DASHBOARD_MODE = "LOTOIA_DASHBOARD_MODE"
INSTITUTIONAL_MODE_ALIASES = frozenset({"institutional", "adm", "admin", "institucional"})
PUBLIC_MODE_ALIASES = frozenset({"public", "publico", "commercial", "comercial"})

ENTRYPOINT_ROWS: tuple[dict[str, str], ...] = (
    {
        "entrypoint": "dashboard/institutional_app.py",
        "papel": "Painel ADM institucional — produção Railway",
        "modo": "institutional",
        "railway": "SIM — startCommand oficial",
    },
    {
        "entrypoint": "dashboard/public_app.py",
        "papel": "Canal público seguro (default) ou ADM via env explícita",
        "modo": "public (default) | institutional (opt-in)",
        "railway": "NÃO — wrapper legado / dev",
    },
    {
        "entrypoint": "dashboard/app.py",
        "papel": "Streamlit Cloud — delega ADM",
        "modo": "institutional",
        "railway": "NÃO",
    },
    {
        "entrypoint": "Procfile / railway.toml",
        "papel": "Config deploy Railway",
        "modo": "institutional_app.py",
        "railway": "SIM",
    },
)

SEPARATION_DECISION = (
    "Opção A aplicada: Railway permanece em institutional_app.py (ADM intacto). "
    "public_app.py default=canal público seguro; modo ADM apenas com "
    f"{ENV_DASHBOARD_MODE}=institutional explícito."
)


def resolve_dashboard_mode(raw: str | None = None) -> DashboardMode:
    """Resolve modo do dashboard — default público para public_app."""
    value = str(raw if raw is not None else os.getenv(ENV_DASHBOARD_MODE, "public")).strip().lower()
    if value in INSTITUTIONAL_MODE_ALIASES:
        return "institutional"
    if value in PUBLIC_MODE_ALIASES:
        return "public"
    return "public"


def build_entrypoint_inventory_snapshot(*, app_build: str, public_build: str) -> dict[str, Any]:
    return {
        "mission_id": "M-PLAT-041",
        "decision": SEPARATION_DECISION,
        "env_var": ENV_DASHBOARD_MODE,
        "default_mode": "public",
        "institutional_build": app_build,
        "public_build": public_build,
        "entrypoints": [dict(row) for row in ENTRYPOINT_ROWS],
        "railway_entrypoint": "dashboard/institutional_app.py",
        "public_app_default": "canal público seguro — sem ADM",
        "inventory_doc": "docs/governance/INVENTARIO_ENTRYPOINTS_PUBLIC_ADM_M_PLAT_041.md",
    }
