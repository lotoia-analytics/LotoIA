from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["ReportSummary", "generate_backtest_report"]

_EXPORTS: dict[str, tuple[str, str]] = {
    "ReportSummary": ("lotoia.reports.report_generator", "ReportSummary"),
    "generate_backtest_report": ("lotoia.reports.report_generator", "generate_backtest_report"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value

