from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "PublicCheckRequest",
    "PublicGenerationRequest",
    "PublicLimiter",
    "check_public_contest",
    "generate_public_games",
    "ReconciliationEngine",
    "OperationalLifecycleEngine",
]


_EXPORTS: dict[str, tuple[str, str]] = {
    "PublicCheckRequest": ("lotoia.public.models", "PublicCheckRequest"),
    "PublicGenerationRequest": ("lotoia.public.models", "PublicGenerationRequest"),
    "PublicLimiter": ("lotoia.public.service", "PublicLimiter"),
    "check_public_contest": ("lotoia.public.service", "check_public_contest"),
    "generate_public_games": ("lotoia.public.service", "generate_public_games"),
    "ReconciliationEngine": ("lotoia.public.reconciliation", "ReconciliationEngine"),
    "OperationalLifecycleEngine": ("lotoia.public.operational_lifecycle", "OperationalLifecycleEngine"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
