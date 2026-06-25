"""Lei 15 — Core Realignment V3.1 PROTECTED (12 slots) and P15 (15 slots)."""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from typing import Final

REALIGNMENT_NAME: Final = "LEI15_CORE_REALIGNMENT_V3_1_PROTECTED"
P15_REALIGNMENT_NAME: Final = "LEI15_CORE_REALIGNMENT_V3_1_P15_PROTECTED"
ENV_VAR: Final = "LOTOIA_LEI15_CORE_REALIGNMENT_V3_1"
LABEL_PREFIX: Final = "STRUCT_LEI15_CORE_V3_1_PROTECTED_"
P15_LABEL_PREFIX: Final = "STRUCT_LEI15_CORE_V3_1_P15_PROTECTED_"
P15_BATCH_LABEL: Final = "STRUCT_LEI15_CORE_V3_1_P15_PROTECTED_15D_001"


@dataclass(frozen=True, slots=True)
class CoreRealignmentV3_1Config:
    """Protected-top + balanced remainder — hits-first hypothesis V3.1."""

    mode: str = "shadow_test"

    max_pool_prefix3_ratio: float = 0.48
    min_pool_size_after_filter: int = 40

    max_prefix3_ratio: float = 0.38
    max_prefix4_ratio: float = 0.30
    max_suffix3_ratio: float = 0.30
    max_suffix4_ratio: float = 0.28

    concentration_penalty_weight: float = 42.0

    # 16 and 06 REMOVED (jun/2026): super-represented in generated games
    # See: frequency analysis of last 300 official contests vs LotoIA
    target_coverage_digits: tuple[int, ...] = (17, 23, 20, 8, 10, 4)
    coverage_bonus_per_digit: float = 1.5
    max_coverage_bonus: float = 6.0

    overlap_slack: int = 3
    overlap_penalty_per_digit: float = 8.0
    min_gp_for_concentration_check: int = 5

    base_score_weight: float = 0.01
    protected_top_score_slots: int = 12

    realignment_tag: str = REALIGNMENT_NAME
    evidence_epoch: str = "EPOCH_001_LEI15_V3_1_PROTECTED"


_VALID_MODES: Final = frozenset({"off", "shadow_test", "active"})


def get_v3_1_mode() -> str:
    raw = os.getenv(ENV_VAR, "off").strip().lower()
    return raw if raw in _VALID_MODES else "off"


def is_p15_label(batch_label: str | None) -> bool:
    return str(batch_label or "").strip().upper().startswith(P15_LABEL_PREFIX)


def is_v3_1_label(batch_label: str | None) -> bool:
    normalized = str(batch_label or "").strip().upper()
    if is_p15_label(normalized):
        return True
    return normalized.startswith(LABEL_PREFIX) and not normalized.startswith(
        P15_LABEL_PREFIX
    )


def resolve_v3_1_config(batch_label: str | None = None) -> CoreRealignmentV3_1Config:
    """Resolve compose config from batch label (12-slot default, 15-slot for P15)."""
    base = CoreRealignmentV3_1Config(mode=get_v3_1_mode())
    if is_p15_label(batch_label):
        return replace(
            base,
            protected_top_score_slots=15,
            max_prefix3_ratio=0.38,
            max_suffix3_ratio=0.35,
            realignment_tag=P15_REALIGNMENT_NAME,
            evidence_epoch="EPOCH_001_LEI15_V3_1_P15_PROTECTED",
        )
    return base


def get_v3_1_config(batch_label: str | None = None) -> CoreRealignmentV3_1Config:
    return resolve_v3_1_config(batch_label)


def v3_1_is_observable() -> bool:
    return get_v3_1_mode() in {"shadow_test", "active"}


def should_apply_v3_1(batch_label: str | None = None) -> bool:
    if get_v3_1_mode() != "shadow_test":
        return False
    return is_v3_1_label(batch_label)
