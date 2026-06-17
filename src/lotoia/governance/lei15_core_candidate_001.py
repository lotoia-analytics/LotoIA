"""Lei 15 — Core Candidate 001 ablation (shadow_test only).

ADR: ADR-NUCLEO-LEI15-CANDIDATE-001
Variants:
  A = N-C4 + N-C5
  B = A + N-C1
  C = B + N-C6
  D = C + N-C3
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, replace
from typing import Final

REALIGNMENT_NAME: Final = "LEI15_CORE_CANDIDATE_001"
ENV_VAR: Final = "LOTOIA_LEI15_CORE_CANDIDATE_001"
LABEL_PREFIX: Final = "STRUCT_LEI15_CORE_CANDIDATE_001_"
BATCH_LABEL_A: Final = "STRUCT_LEI15_CORE_CANDIDATE_001_15D_001"
BATCH_LABEL_B: Final = "STRUCT_LEI15_CORE_CANDIDATE_001_B_15D_001"
BATCH_LABEL_C: Final = "STRUCT_LEI15_CORE_CANDIDATE_001_C_15D_001"
BATCH_LABEL_D: Final = "STRUCT_LEI15_CORE_CANDIDATE_001_D_15D_001"

_LABEL_PATTERN = re.compile(r"^STRUCT_LEI15_CORE_CANDIDATE_001(?:_([ABCD]))?_15D_\d+$")

_VALID_MODES: Final = frozenset({"off", "shadow_test", "active"})


@dataclass(frozen=True, slots=True)
class CoreCandidate001Config:
    """Ablation toggles for Núcleo Lei 15 candidate."""

    mode: str = "shadow_test"
    variant: str = "A"

    pool_sampling_by_quota: bool = False
    disable_profile_relabeling: bool = False

    cap_last_draw_overlap: bool = False
    max_last_draw_overlap: int = 8
    block_prefix_triplet_123: bool = False

    hybrid_reduced_inheritance: bool = False
    hybrid_inherit_min: int = 4
    hybrid_inherit_max: int = 7
    blind_spot_injection: bool = False
    blind_spot_digits: tuple[int, ...] = (6, 16, 17)
    blind_spot_slots: int = 2

    adjusted_recurrence_scoring: bool = False
    recurrence_weight_scale: float = 0.75

    structural_bias_penalty: bool = False
    structural_bias_weight: float = 8.0
    suffix_hot_cap: bool = False
    max_high_suffix_digits: int = 4

    realignment_tag: str = REALIGNMENT_NAME
    evidence_epoch: str = "EPOCH_001_LEI15_CORE_CANDIDATE_001"


def get_candidate_mode() -> str:
    raw = os.getenv(ENV_VAR, "off").strip().lower()
    return raw if raw in _VALID_MODES else "off"


def is_candidate_label(batch_label: str | None) -> bool:
    normalized = str(batch_label or "").strip().upper()
    return normalized.startswith(LABEL_PREFIX)


def resolve_variant(batch_label: str | None) -> str:
    normalized = str(batch_label or "").strip().upper()
    m = _LABEL_PATTERN.match(normalized)
    if not m:
        return "A"
    suffix = m.group(1)
    return suffix if suffix in {"A", "B", "C", "D"} else "A"


def resolve_candidate_config(batch_label: str | None = None) -> CoreCandidate001Config:
    base = CoreCandidate001Config(mode=get_candidate_mode(), variant=resolve_variant(batch_label))
    variant = base.variant
    cfg_a = replace(
        base,
        variant="A",
        pool_sampling_by_quota=True,
        disable_profile_relabeling=True,
    )
    if variant == "A":
        return cfg_a
    cfg_b = replace(
        cfg_a,
        variant="B",
        cap_last_draw_overlap=True,
        block_prefix_triplet_123=True,
        structural_bias_penalty=True,
    )
    if variant == "B":
        return cfg_b
    if variant == "C":
        return replace(cfg_b, variant="C", adjusted_recurrence_scoring=True)
    if variant == "D":
        return replace(
            replace(cfg_b, variant="C", adjusted_recurrence_scoring=True),
            variant="D",
            hybrid_reduced_inheritance=True,
            blind_spot_injection=True,
            suffix_hot_cap=True,
        )
    return cfg_a


def get_candidate_config(batch_label: str | None = None) -> CoreCandidate001Config:
    return resolve_candidate_config(batch_label)


def should_apply_core_candidate_001(batch_label: str | None = None) -> bool:
    if get_candidate_mode() != "shadow_test":
        return False
    return is_candidate_label(batch_label)
