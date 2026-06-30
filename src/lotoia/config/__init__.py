"""Módulo de configuração centralizada do LotoIA."""

from lotoia.config.settings import settings
from lotoia.config.structural_policy_config import (
    CONFIG_VERSION,
    CRITICAL_DIGITS,
    DEFAULT_PREFIX_SHARE_LIMIT,
    HISTORICAL_WINDOW,
    MAX_PREFIX_SUFFIX_SHARE,
    STRUCTURAL_POLICY,
)

__all__ = [
    "settings",
    "CONFIG_VERSION",
    "CRITICAL_DIGITS",
    "DEFAULT_PREFIX_SHARE_LIMIT",
    "HISTORICAL_WINDOW",
    "MAX_PREFIX_SUFFIX_SHARE",
    "STRUCTURAL_POLICY",
]
