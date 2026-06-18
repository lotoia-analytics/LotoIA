"""Geração soberana controlada CORE_002 — estado institucional (M-GER-044)."""

from __future__ import annotations

from lotoia.governance.lei15_core_002_sovereign import (
    BATCH_LABEL,
    ENV_GENERATION_ENABLED,
    is_generation_enabled,
)

MISSION_ID = "M-GER-044"

SOVEREIGN_GENERATION_STATUS_ACTIVE = "GERAÇÃO SOBERANA CONTROLADA — ATIVA NO ADM"
SOVEREIGN_GENERATION_STATUS_BLOCKED = "BLOQUEADA"

ADM_GENERATOR_LABEL_ACTIVE = "Gerador ADM CORE_002 — Geração Soberana Controlada"
ADM_GENERATOR_LABEL_BLOCKED = "Gerador ADM CORE_002 — BLOQUEADO"

SOVEREIGN_GENERATION_DISCLAIMER = (
    "Geração soberana controlada ativa exclusivamente para LEI15_CORE_002. "
    "Não constitui promessa de acerto. Rastreabilidade por lote via PostgreSQL "
    "(generation_events / generated_games)."
)

SOVEREIGN_GENERATION_GOVERNANCE_ALERT = (
    "Path único: generate_best_games(batch_label=STRUCT_LEI15_CORE_CANDIDATE_002_15D_001, "
    "ml_enabled=False). Lei 15A inoperante. ML operacional proibido."
)


def is_adm_sovereign_generation_active() -> bool:
    return is_generation_enabled()


def sovereign_generation_status_label() -> str:
    if is_adm_sovereign_generation_active():
        return SOVEREIGN_GENERATION_STATUS_ACTIVE
    return SOVEREIGN_GENERATION_STATUS_BLOCKED


def adm_generator_menu_label() -> str:
    if is_adm_sovereign_generation_active():
        return ADM_GENERATOR_LABEL_ACTIVE
    return ADM_GENERATOR_LABEL_BLOCKED


def build_sovereign_generation_activation_snapshot() -> dict[str, object]:
    active = is_adm_sovereign_generation_active()
    return {
        "mission_id": MISSION_ID,
        "core_id": "LEI15_CORE_002",
        "batch_label": BATCH_LABEL,
        "generation_active": active,
        "generation_status": sovereign_generation_status_label(),
        "env_var": ENV_GENERATION_ENABLED,
        "env_value_expected": "1" if active else "0",
        "ml_enabled": False,
        "sovereign_path": "generate_best_games",
        "legacy_path_blocked": "_generate_direct_15_games",
        "persistence": "PostgreSQL — generation_events / generated_games",
    }
