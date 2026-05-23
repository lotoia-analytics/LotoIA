from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "BacktestRun",
    "BenchmarkRun",
    "CalibrationRun",
    "InstitutionalDatabaseAdapter",
    "SQLiteInstitutionalAdapter",
    "CheckEvent",
    "ContestRepository",
    "DEFAULT_DATABASE_PATH",
    "GenerationEvent",
    "Lead",
    "create_database",
    "get_run_by_id",
    "list_runs",
    "save_backtest_run",
    "save_benchmark_run",
    "save_calibration_run",
]

_EXPORTS: dict[str, tuple[str, str]] = {
    "BacktestRun": ("lotoia.database.database", "BacktestRun"),
    "BenchmarkRun": ("lotoia.database.database", "BenchmarkRun"),
    "CalibrationRun": ("lotoia.database.database", "CalibrationRun"),
    "InstitutionalDatabaseAdapter": ("lotoia.database.adapter", "InstitutionalDatabaseAdapter"),
    "SQLiteInstitutionalAdapter": ("lotoia.database.adapter", "SQLiteInstitutionalAdapter"),
    "CheckEvent": ("lotoia.database.database", "CheckEvent"),
    "DEFAULT_DATABASE_PATH": ("lotoia.database.database", "DEFAULT_DATABASE_PATH"),
    "GenerationEvent": ("lotoia.database.database", "GenerationEvent"),
    "Lead": ("lotoia.database.database", "Lead"),
    "create_database": ("lotoia.database.database", "create_database"),
    "ContestRepository": ("lotoia.database.contest_repository", "ContestRepository"),
    "get_run_by_id": ("lotoia.database.repository", "get_run_by_id"),
    "list_runs": ("lotoia.database.repository", "list_runs"),
    "save_backtest_run": ("lotoia.database.repository", "save_backtest_run"),
    "save_benchmark_run": ("lotoia.database.repository", "save_benchmark_run"),
    "save_calibration_run": ("lotoia.database.repository", "save_calibration_run"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
