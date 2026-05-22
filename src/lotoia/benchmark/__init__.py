from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["BenchmarkResult", "run_benchmark"]

_EXPORTS: dict[str, tuple[str, str]] = {
    "BenchmarkResult": ("lotoia.benchmark.benchmark_engine", "BenchmarkResult"),
    "run_benchmark": ("lotoia.benchmark.benchmark_engine", "run_benchmark"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
