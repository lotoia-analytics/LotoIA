from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "InstitutionalMemoryRegistry",
    "MemoryComparison",
    "MemoryReplay",
    "MemorySnapshot",
    "MemoryState",
    "MemoryEvolution",
    "MemoryEvolutionStep",
    "build_adaptive_evolution_tracking",
    "InstitutionalStateDiff",
    "MemoryDiffAxis",
    "build_institutional_state_diff",
    "InstitutionalMemoryRepository",
    "MemoryRepositorySummary",
    "MemoryTimeline",
    "MemoryTimelineEntry",
    "build_memory_timeline",
]


_EXPORTS: dict[str, tuple[str, str]] = {
    "InstitutionalMemoryRegistry": ("lotoia.memory.memory_registry", "InstitutionalMemoryRegistry"),
    "MemoryComparison": ("lotoia.memory.memory_registry", "MemoryComparison"),
    "MemoryReplay": ("lotoia.memory.memory_registry", "MemoryReplay"),
    "MemorySnapshot": ("lotoia.memory.memory_registry", "MemorySnapshot"),
    "MemoryState": ("lotoia.memory.memory_registry", "MemoryState"),
    "MemoryEvolution": ("lotoia.memory.memory_evolution", "MemoryEvolution"),
    "MemoryEvolutionStep": ("lotoia.memory.memory_evolution", "MemoryEvolutionStep"),
    "build_adaptive_evolution_tracking": ("lotoia.memory.memory_evolution", "build_adaptive_evolution_tracking"),
    "InstitutionalStateDiff": ("lotoia.memory.memory_diff", "InstitutionalStateDiff"),
    "MemoryDiffAxis": ("lotoia.memory.memory_diff", "MemoryDiffAxis"),
    "build_institutional_state_diff": ("lotoia.memory.memory_diff", "build_institutional_state_diff"),
    "InstitutionalMemoryRepository": ("lotoia.memory.memory_repository", "InstitutionalMemoryRepository"),
    "MemoryRepositorySummary": ("lotoia.memory.memory_repository", "MemoryRepositorySummary"),
    "MemoryTimeline": ("lotoia.memory.memory_timeline", "MemoryTimeline"),
    "MemoryTimelineEntry": ("lotoia.memory.memory_timeline", "MemoryTimelineEntry"),
    "build_memory_timeline": ("lotoia.memory.memory_timeline", "build_memory_timeline"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
