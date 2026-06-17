"""Identidade de build do painel institucional — fonte única para verificação de deploy."""

from __future__ import annotations

BUILD_MARKER = "institutional-adm-runtime-v17"
APP_BUILD = BUILD_MARKER
CORE_REALIGN_V3_BATCH_LABEL = "STRUCT_CORE_REALIGN_V3_BALANCED_15D_001"
CORE_REALIGN_V3_ENV_VAR = "LOTOIA_LEI15_15A_CORE_REALIGNMENT_V3"

DEPRECATED_BUILD_MARKERS: frozenset[str] = frozenset(
    {
        "institutional-adm-runtime-v1",
        "institutional-adm-runtime-v2",
        "institutional-adm-runtime-v3",
        "institutional-adm-runtime-v4",
        "institutional-adm-runtime-v5",
        "institutional-adm-runtime-v6",
        "institutional-adm-runtime-v7",
        "institutional-adm-runtime-v8",
        "institutional-adm-runtime-v9",
        "institutional-adm-runtime-v10",
        "institutional-adm-runtime-v11",
        "institutional-adm-runtime-v12",
        "institutional-adm-runtime-v13",
        "institutional-adm-runtime-v14",
        "institutional-adm-runtime-v15",
        "institutional-adm-runtime-v16",
    }
)

LOTOIA_PANEL_PRODUCTION_URL = "https://lotoia-production.up.railway.app"
