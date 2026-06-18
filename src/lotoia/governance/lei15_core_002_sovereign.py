"""Lei 15 — Núcleo Soberano LEI15_CORE_002 (síntese V1 + CAND-D).

ADR: ADR-046-NUCLEO-LEI15-CANDIDATE-002
Status institucional: NÚCLEO SOBERANO DA LEI 15

Label técnico rastreável: STRUCT_LEI15_CORE_CANDIDATE_002_15D_001
Geração soberana controlada ativa por padrão (M-GER-044) — desativável via
LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=0.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Final

REALIGNMENT_NAME: Final = "LEI15_CORE_002"
ENV_VAR: Final = "LOTOIA_LEI15_CORE_002"
ENV_GENERATION_ENABLED: Final = "LOTOIA_LEI15_CORE_002_GENERATION_ENABLED"
BATCH_LABEL: Final = "STRUCT_LEI15_CORE_CANDIDATE_002_15D_001"
LABEL_PREFIX: Final = "STRUCT_LEI15_CORE_CANDIDATE_002_"
SOVEREIGN_STATUS: Final = "NUCLEO_SOBERANO_LEI15"
CANDIDATE_ORIGIN_LABEL: Final = BATCH_LABEL
ADR_ID: Final = "ADR-046"

_LABEL_PATTERN = re.compile(r"^STRUCT_LEI15_CORE_CANDIDATE_002_15D_\d+$")
_MULTIDEZENA_LABEL_PATTERN = re.compile(r"^STRUCT_LEI15_CORE_CANDIDATE_002_(\d+)D_\d+$")
_VALID_MODES: Final = frozenset({"off", "sovereign"})
_VALID_MULTIDEZENA_FORMATS: Final = frozenset(range(15, 24))


@dataclass(frozen=True, slots=True)
class Core002SovereignConfig:
    """Configuração institucional do Núcleo Soberano LEI15_CORE_002."""

    mode: str = "sovereign"
    sovereign_core_status: str = SOVEREIGN_STATUS
    candidate_origin_label: str = CANDIDATE_ORIGIN_LABEL
    generation_blocked: bool = True
    lei15a_blocked: bool = True
    legacy_core_frozen: bool = True
    active_public_blocked: bool = True
    adr: str = ADR_ID
    evidence_epoch: str = "EPOCH_001_LEI15_CORE_002"


def get_sovereign_mode() -> str:
    raw = os.getenv(ENV_VAR, "sovereign").strip().lower()
    return raw if raw in _VALID_MODES else "off"


def is_sovereign_implanted() -> bool:
    return get_sovereign_mode() == "sovereign"


def resolve_core_002_batch_label(card_format: int, *, sequence: int = 1) -> str:
    """Label derivada CORE_002 por formato multidezena (15D–23D) — não é Lei 15A."""
    fmt = int(card_format or 15)
    if fmt not in _VALID_MULTIDEZENA_FORMATS:
        raise ValueError(f"Formato CORE_002 inválido: {fmt}D (permitido 15–23).")
    return f"{LABEL_PREFIX}{fmt}D_{int(sequence):03d}"


def core_002_batch_label_game_size(batch_label: str | None) -> int | None:
    normalized = str(batch_label or "").strip().upper()
    if normalized == BATCH_LABEL or _LABEL_PATTERN.match(normalized):
        return 15
    match = _MULTIDEZENA_LABEL_PATTERN.match(normalized)
    if match:
        return int(match.group(1))
    return None


def is_sovereign_core_label(batch_label: str | None) -> bool:
    normalized = str(batch_label or "").strip().upper()
    return (
        normalized == BATCH_LABEL
        or bool(_LABEL_PATTERN.match(normalized))
        or bool(_MULTIDEZENA_LABEL_PATTERN.match(normalized))
    )


def is_generation_enabled() -> bool:
    raw = os.getenv(ENV_GENERATION_ENABLED, "1").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def get_core_002_config(batch_label: str | None = None) -> Core002SovereignConfig:
    _ = batch_label
    return Core002SovereignConfig(
        mode=get_sovereign_mode(),
        generation_blocked=not is_generation_enabled(),
    )


def should_apply_core_002(batch_label: str | None = None) -> bool:
    if not is_sovereign_implanted():
        return False
    return is_sovereign_core_label(batch_label)


def enforce_generation_policy(batch_label: str | None = None) -> None:
    """Falha fechada: geração CAND-002 requer flag explícita quando desativada."""
    if not is_sovereign_core_label(batch_label):
        return
    if not is_generation_enabled():
        raise RuntimeError(
            f"[{REALIGNMENT_NAME}] Geração bloqueada para label={batch_label!r}. "
            f"Núcleo Soberano implantado — execução futura somente via Painel ADM "
            f"com {ENV_GENERATION_ENABLED}=1."
        )


def lei15a_operational_gate() -> dict[str, object]:
    """Lei 15A permanece bloqueada até ordem institucional posterior."""
    return {
        "open_15a": False,
        "blocked_by": REALIGNMENT_NAME,
        "condition": "Ordem institucional posterior à validação operacional do Núcleo Soberano",
        "sequence": [
            "LEI15_CORE_002 soberano implantado",
            "Painel ADM 100% funcional",
            "Geração autorizada via ADM",
            "Validação multi-GE / 6 bases",
            "Ordem explícita para Lei 15A",
        ],
    }


def institutional_status_report() -> dict[str, object]:
    """Snapshot read-only do status institucional pós-implantação."""
    return {
        "core_id": REALIGNMENT_NAME,
        "sovereign_core_status": SOVEREIGN_STATUS if is_sovereign_implanted() else "off",
        "candidate_origin_label": CANDIDATE_ORIGIN_LABEL,
        "batch_label": BATCH_LABEL,
        "implanted": is_sovereign_implanted(),
        "generation_enabled": is_generation_enabled(),
        "generation_blocked": not is_generation_enabled(),
        "active_public_blocked": True,
        "lei15a": lei15a_operational_gate(),
        "legacy_core": {
            "status": "baseline_congelado_read_only",
            "label": "STRUCT_TEST_15D_001",
        },
        "v1_evidence": {
            "status": "preservada_historica_nao_soberana_isolada",
            "label": "STRUCT_REALIGN_V1_15D_001",
        },
        "cand_d_evidence": {
            "status": "preservada_estrutural_nao_soberana_isolada",
            "label": "STRUCT_LEI15_CORE_CANDIDATE_001_D_15D_001",
        },
        "future_execution": "Painel ADM 100% funcional",
        "adr": ADR_ID,
    }
