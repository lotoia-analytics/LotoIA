"""Lei 15 — Structural Realignment V1.

Governance configuration and feature flag for GP-level structural diversity
enforcement. This module carries NO generation logic — it only declares the
authorised thresholds, the evidence base and the operational mode.

ADM Authorization
-----------------
  Mission : IMPLEMENTAR_REALINHAMENTO_ESTRUTURAL_LEI15_V1
  Evidence: EPOCH_001 audit (STRUCT_TEST_15D_001 … STRUCT_TEST_20D_001)
  Status  : AUTORIZADO_PELO_ADM

Feature flag
------------
  Env var : LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1
  Values  :
    "off"          — disabled (default)
    "shadow_test"  — score & tag games; selection unchanged; metrics logged
    "active"       — full realignment applied to GP composition

Constraints (immutable)
-----------------------
  - Does NOT alter Law 15 game-generation rules.
  - Does NOT replace structural statistical analysis with ML.
  - Does NOT produce games without traceability.
  - Rollback: set env var to "off" or unset; no DB migration required.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Final

# ---------------------------------------------------------------------------
# Evidence base — EPOCH_001 confirmed biases
# ---------------------------------------------------------------------------

EPOCH_001_EVIDENCE: Final[dict[str, object]] = {
    "batches_audited": [
        "STRUCT_TEST_15D_001",
        "STRUCT_TEST_16D_001",
        "STRUCT_TEST_17D_001",
        "STRUCT_TEST_18D_001",
        "STRUCT_TEST_19D_001",
        "STRUCT_TEST_20D_001",
    ],
    "over_represented_prefix_3": ["01-02-03"],
    "over_represented_prefix_4": ["01-02-03-04", "01-03-04-05"],
    "over_represented_suffix_3": ["22-24-25"],
    "over_represented_suffix_4": ["21-22-24-25"],
    "under_covered_prefix_3": ["01-05-06", "01-04-06", "01-03-07", "02-04-05", "02-05-06"],
    "recurrently_missing_digits": [16, 6, 17, 23, 20, 8, 10, 4],
    "redundancy_similarity_range": (0.799, 0.838),
    "adr_authorization": "IMPLEMENTAR_REALINHAMENTO_ESTRUTURAL_LEI15_V1",
}


# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class StructuralRealignmentConfig:
    """Authorised thresholds for Realignment V1.

    All parameters are expressed as ratios (0.0–1.0) or absolute counts.
    Tuning requires a new ADR; these values reflect EPOCH_001 evidence only.
    """

    mode: str = "shadow_test"

    # Maximum fraction of GP games that may share the same prefix_3 / prefix_4
    max_prefix3_ratio: float = 0.25
    max_prefix4_ratio: float = 0.30

    # Maximum fraction of GP games that may share the same suffix_3 / suffix_4
    max_suffix3_ratio: float = 0.25
    max_suffix4_ratio: float = 0.30

    # Weight of concentration penalty per excess point (ratio unit)
    concentration_penalty_weight: float = 40.0

    # Digits recurrently missing from GP; their presence earns a coverage bonus
    target_coverage_digits: tuple[int, ...] = (16, 6, 17, 23, 20, 8, 10, 4)

    # Bonus per target digit present in a game (capped at max_coverage_bonus)
    coverage_bonus_per_digit: float = 1.5
    max_coverage_bonus: float = 6.0

    # Maximum number of shared digits between any two GP games before penalty
    # (expressed as game_size − slack; slack resolved at runtime)
    overlap_slack: int = 3

    # Penalty per shared digit above the allowed overlap
    overlap_penalty_per_digit: float = 8.0

    # Minimum GP size required to activate concentration enforcement
    # (small GPs of <5 games skip prefix/suffix balancing)
    min_gp_for_concentration_check: int = 5

    # Metadata tag added to every game processed under this realignment
    realignment_tag: str = "REALIGNMENT_V1"

    # Evidence reference stored in generated-game metadata
    evidence_epoch: str = "EPOCH_001"


# ---------------------------------------------------------------------------
# Feature flag resolver
# ---------------------------------------------------------------------------

_ENV_VAR: Final = "LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1"
_VALID_MODES: Final = frozenset({"off", "shadow_test", "active"})


def get_realignment_mode() -> str:
    """Read the operational mode from the environment.

    Returns one of: "off", "shadow_test", "active".
    Unknown values are treated as "off" (fail-safe).
    """
    raw = os.getenv(_ENV_VAR, "off").strip().lower()
    return raw if raw in _VALID_MODES else "off"


def get_realignment_config() -> StructuralRealignmentConfig:
    """Return the active StructuralRealignmentConfig for the current runtime."""
    return StructuralRealignmentConfig(mode=get_realignment_mode())


def realignment_is_active() -> bool:
    """True when the feature flag is set to 'active' (full realignment)."""
    return get_realignment_mode() == "active"


def realignment_is_observable() -> bool:
    """True when shadow_test or active mode (metrics are logged either way)."""
    return get_realignment_mode() in {"shadow_test", "active"}
