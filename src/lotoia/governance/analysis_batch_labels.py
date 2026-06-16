"""Metadados de lotes de análise para generation_events (sem efeito operacional)."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

STRUCTURAL_COVERAGE_TEST = "STRUCTURAL_COVERAGE_TEST"
STRUCTURAL_REALIGNMENT_TEST = "STRUCTURAL_REALIGNMENT_TEST"
STRUCTURAL_CORE_REALIGNMENT_TEST = "STRUCTURAL_CORE_REALIGNMENT_TEST"
ADM_DIAGNOSTIC_TEST = "ADM_DIAGNOSTIC_TEST"
GENERAL_ANALYSIS = "GENERAL_ANALYSIS"

BATCH_TYPE_VALUES: tuple[str, ...] = (
    STRUCTURAL_COVERAGE_TEST,
    STRUCTURAL_REALIGNMENT_TEST,
    STRUCTURAL_CORE_REALIGNMENT_TEST,
    ADM_DIAGNOSTIC_TEST,
    GENERAL_ANALYSIS,
)

# Labels legados EPOCH_000 — mantidos apenas para compatibilidade com registros antigos
LEGACY_BATCH_LABELS: tuple[str, ...] = (
    "STRUCT_TEST_15D",
    "STRUCT_TEST_16D",
    "STRUCT_TEST_17D",
    "STRUCT_TEST_18D",
    "STRUCT_TEST_19D",
    "STRUCT_TEST_20D",
    "STRUCT_TEST_21D",
    "STRUCT_TEST_22D",
    "STRUCT_TEST_23D",
)

# Labels ativos EPOCH_001 — fase auditável (baseline)
_EPOCH_001_BASELINE: tuple[str, ...] = (
    "STRUCT_TEST_15D_001",
    "STRUCT_TEST_16D_001",
    "STRUCT_TEST_17D_001",
    "STRUCT_TEST_18D_001",
    "STRUCT_TEST_19D_001",
    "STRUCT_TEST_20D_001",
)

# Labels REALIGN_V1 — fase shadow_test / comparativa
# ADR: IMPLEMENTAR_REALINHAMENTO_ESTRUTURAL_LEI15_V1
_REALIGN_V1_LABELS: tuple[str, ...] = (
    "STRUCT_REALIGN_V1_15D_001",
    "STRUCT_REALIGN_V1_16D_001",
    "STRUCT_REALIGN_V1_17D_001",
    "STRUCT_REALIGN_V1_18D_001",
)

# Labels CORE_REALIGN_V2 — fase shadow_test / comparativa V2
# ADR: ADR-044-REAVALIACAO-NUCLEOS-LEI15-15A
# Mission: MISSAO_DA_VITORIA_REAVALIAR_NUCLEOS_LEI15_15A
_CORE_REALIGN_V2_LABELS: tuple[str, ...] = (
    "STRUCT_CORE_REALIGN_V2_15D_001",
    "STRUCT_CORE_REALIGN_V2_16D_001",
    "STRUCT_CORE_REALIGN_V2_17D_001",
    "STRUCT_CORE_REALIGN_V2_18D_001",
)

ALLOWED_BATCH_LABELS: tuple[str, ...] = (
    *_EPOCH_001_BASELINE,
    *_REALIGN_V1_LABELS,
    *_CORE_REALIGN_V2_LABELS,
)

RESERVED_BATCH_LABELS: frozenset[str] = frozenset(
    {
        # EPOCH_001 reservados sem ADR
        "STRUCT_TEST_21D_001",
        "STRUCT_TEST_22D_001",
        "STRUCT_TEST_23D_001",
        # EPOCH_000 legados reservados
        "STRUCT_TEST_21D",
        "STRUCT_TEST_22D",
        "STRUCT_TEST_23D",
    }
)

# UI mostra labels baseline + realinhamento + CUSTOM
BATCH_LABEL_UI_OPTIONS: tuple[str, ...] = (*ALLOWED_BATCH_LABELS, "CUSTOM")

OPERATIONAL_EFFECT = False

# Pattern: STRUCT_REALIGN_V1_<size>D_<epoch>
_REALIGN_PATTERN = re.compile(r"^STRUCT_REALIGN_V\d+_(\d+)D_\d+$")
# Pattern: STRUCT_CORE_REALIGN_V2_<size>D_<epoch>
_CORE_V2_PATTERN = re.compile(r"^STRUCT_CORE_REALIGN_V2_(\d+)D_\d+$")
# Pattern: STRUCT_TEST_<size>D[_<epoch>]
_TEST_PATTERN = re.compile(r"^STRUCT_TEST_(\d+)D(?:_\d+)?$")


def batch_label_game_size(label: str | None) -> int | None:
    normalized = str(label or "").strip().upper()
    m = _REALIGN_PATTERN.match(normalized)
    if m:
        return int(m.group(1))
    m = _CORE_V2_PATTERN.match(normalized)
    if m:
        return int(m.group(1))
    m = _TEST_PATTERN.match(normalized)
    if m:
        return int(m.group(1))
    return None


def is_reserved_batch_label(label: str | None) -> bool:
    return str(label or "").strip().upper() in RESERVED_BATCH_LABELS


def infer_batch_type(label: str | None) -> str:
    normalized = str(label or "").strip().upper()
    if normalized.startswith("STRUCT_CORE_REALIGN_V2_"):
        return STRUCTURAL_CORE_REALIGNMENT_TEST
    if normalized.startswith("STRUCT_REALIGN_"):
        return STRUCTURAL_REALIGNMENT_TEST
    if normalized.startswith("STRUCT_TEST_"):
        return STRUCTURAL_COVERAGE_TEST
    if normalized.startswith("ADM_"):
        return ADM_DIAGNOSTIC_TEST
    return GENERAL_ANALYSIS


def normalize_batch_label(label: str | None, *, custom_label: str | None = None) -> str:
    normalized = str(label or "").strip().upper()
    if normalized == "CUSTOM":
        custom = str(custom_label or "").strip().upper()
        if not custom:
            raise ValueError("Informe um rótulo personalizado quando selecionar CUSTOM.")
        return custom
    if normalized in ALLOWED_BATCH_LABELS:
        return normalized
    if normalized in LEGACY_BATCH_LABELS:
        return normalized
    raise ValueError(
        f"Rótulo de lote inválido: {label!r}. Permitidos: {', '.join(BATCH_LABEL_UI_OPTIONS)}."
    )


def validate_batch_label_for_game_size(
    label: str | None,
    *,
    game_size: int,
    runtime_max_format: int = 20,
) -> dict[str, Any]:
    """Valida consistência formato × label. Metadado only — não altera cartões."""
    normalized = normalize_batch_label(label)
    expected_size = batch_label_game_size(normalized)
    resolved_game_size = int(game_size or 0)
    errors: list[str] = []

    if expected_size is not None and expected_size != resolved_game_size:
        errors.append(
            f"O lote {normalized} exige game_size={expected_size}, recebido={resolved_game_size}."
        )

    if is_reserved_batch_label(normalized):
        errors.append(
            f"O lote reservado {normalized} permanece apenas como metadado; "
            f"a geração {expected_size}D ainda não foi liberada no runtime (máx. {runtime_max_format}D)."
        )
    elif expected_size is not None and expected_size > runtime_max_format:
        errors.append(
            f"O lote {normalized} exige formato {expected_size}D, acima do runtime liberado ({runtime_max_format}D)."
        )

    return {
        "valid": not errors,
        "label": normalized,
        "batch_type": infer_batch_type(normalized),
        "game_size": resolved_game_size,
        "expected_game_size": expected_size,
        "reserved_label": is_reserved_batch_label(normalized),
        "operational_effect": OPERATIONAL_EFFECT,
        "errors": errors,
    }


def build_batch_metadata(
    label: str | None,
    *,
    game_size: int,
    created_by: str | None = None,
    custom_label: str | None = None,
    runtime_max_format: int = 20,
) -> dict[str, Any]:
    validation = validate_batch_label_for_game_size(
        label,
        game_size=game_size,
        runtime_max_format=runtime_max_format,
    )
    if not validation["valid"]:
        raise ValueError("; ".join(validation["errors"]))
    created_at = datetime.now(UTC)
    return {
        "analysis_batch_label": validation["label"],
        "analysis_batch_type": validation["batch_type"],
        "analysis_batch_created_by": str(created_by or "institutional").strip() or "institutional",
        "analysis_batch_created_at": created_at.isoformat(),
        "operational_effect": OPERATIONAL_EFFECT,
    }
