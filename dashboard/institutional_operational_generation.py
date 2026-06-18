"""Numeração operacional de gerações — nova fase CORE_002 (M-DADOS-049)."""

from __future__ import annotations

from typing import Any, Sequence

from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL as SOVEREIGN_BATCH_LABEL

MISSION_ID = "M-DADOS-049"


def format_operational_generation_number(sequence_index: int) -> str:
    """Exibe 001, 002, 003… para leitura operacional."""
    value = max(int(sequence_index or 0), 0)
    if value <= 0:
        return "-"
    return f"{value:03d}"


def _normalize_batch_label(value: Any) -> str:
    return str(value or "").strip().upper()


def build_operational_generation_index(
    events: Sequence[dict[str, Any]],
    *,
    sovereign_batch_label: str = SOVEREIGN_BATCH_LABEL,
) -> dict[int, int]:
    """Mapeia generation_event_id → índice operacional entre lotes soberanos CORE_002."""
    sovereign_label = _normalize_batch_label(sovereign_batch_label)
    eligible: list[tuple[int, str]] = []
    for row in events:
        ge_id = int(row.get("id") or row.get("generation_event_id") or 0)
        if ge_id <= 0:
            continue
        label = _normalize_batch_label(row.get("analysis_batch_label"))
        if label != sovereign_label:
            continue
        created_at = str(row.get("created_at") or "")
        eligible.append((ge_id, created_at))
    eligible.sort(key=lambda item: (item[1], item[0]))
    return {ge_id: index + 1 for index, (ge_id, _created_at) in enumerate(eligible)}


def resolve_operational_generation_label(
    generation_event_id: int | None,
    *,
    events: Sequence[dict[str, Any]] | None = None,
    operational_index: dict[int, int] | None = None,
) -> str:
    ge_id = int(generation_event_id or 0)
    if ge_id <= 0:
        return "-"
    index_map = operational_index or build_operational_generation_index(events or [])
    sequence = int(index_map.get(ge_id, 0) or 0)
    if sequence <= 0:
        return f"GE-{ge_id}"
    return format_operational_generation_number(sequence)
