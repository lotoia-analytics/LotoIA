"""Governança — Núcleo antigo Lei 15 congelado como baseline read-only.

Registro: NUCLEO_ANTIGO_LEI15_BASELINE_CONGELADO_2026_06_17
Relatório: docs/governance/RELATORIO_NUCLEO_ANTIGO_LEI15_BASELINE_CONGELADO_2026_06_17.md
"""

from __future__ import annotations

from typing import Final

REGISTRY_ID: Final = "NUCLEO_ANTIGO_LEI15_BASELINE_CONGELADO_2026_06_17"

# Motor legado de geração (pool round-robin + R-06 + relabeling histórico)
LEGACY_CORE_BASELINE_LABEL: Final = "STRUCT_TEST_15D_001"

# Realinhamentos sobre o mesmo núcleo legado — congelados como evidência, não evolução
LEGACY_CORE_REALIGN_LABELS: Final = frozenset(
    {
        "STRUCT_CORE_REALIGN_V2_15D_001",
        "STRUCT_CORE_REALIGN_V3_BALANCED_15D_001",
        "STRUCT_LEI15_CORE_V3_1_PROTECTED_15D_001",
        "STRUCT_LEI15_CORE_V4_PATTERN_PROTECTED_15D_001",
    }
)

# Linhagem CDX — candidata evolutiva (shadow_test)
CDX_CANDIDATE_LABEL_A: Final = "STRUCT_LEI15_CORE_CANDIDATE_001_15D_001"
CDX_CANDIDATE_LABEL_D: Final = "STRUCT_LEI15_CORE_CANDIDATE_001_D_15D_001"

# V1 — evidência líder de hits; não confundir com núcleo legado
V1_EVIDENCE_LABEL: Final = "STRUCT_REALIGN_V1_15D_001"

# Núcleo Soberano Lei 15 — LEI15_CORE_002 (ADR-046)
SOVEREIGN_CORE_002_LABEL: Final = "STRUCT_LEI15_CORE_CANDIDATE_002_15D_001"
SOVEREIGN_CORE_002_ID: Final = "LEI15_CORE_002"

FROZEN_LEGACY_LABELS: Final = frozenset({LEGACY_CORE_BASELINE_LABEL, *LEGACY_CORE_REALIGN_LABELS})

# Piloto institucional: proibir novos lotes extensos no motor legado
MAX_NEW_LEGACY_GENERATION_EVENTS: Final = 0


def is_legacy_core_frozen_label(batch_label: str | None) -> bool:
    normalized = str(batch_label or "").strip().upper()
    return normalized in FROZEN_LEGACY_LABELS or normalized.startswith("STRUCT_TEST_15D_")


def is_cdx_candidate_label(batch_label: str | None) -> bool:
    normalized = str(batch_label or "").strip().upper()
    return normalized.startswith("STRUCT_LEI15_CORE_CANDIDATE_001")


def assert_no_new_legacy_extensive_lot(*, batch_label: str | None, new_events: int) -> None:
    """Falha fechada se tentativa de novo lote extenso no núcleo antigo."""
    if not is_legacy_core_frozen_label(batch_label):
        return
    if new_events > MAX_NEW_LEGACY_GENERATION_EVENTS:
        raise RuntimeError(
            f"[{REGISTRY_ID}] Nucleo antigo Lei 15 congelado. "
            f"Novos lotes proibidos para label={batch_label!r}. "
            f"Use linhagem CDX em shadow_test."
        )
