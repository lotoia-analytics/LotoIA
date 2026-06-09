from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "WeightConfiguration",
    "compare_weight_configurations",
    "evaluate_weight_configuration",
]

_EXPORTS: dict[str, tuple[str, str]] = {
    "WeightConfiguration": ("lotoia.calibration.weight_calibrator", "WeightConfiguration"),
    "compare_weight_configurations": ("lotoia.calibration.weight_calibrator", "compare_weight_configurations"),
    "evaluate_weight_configuration": ("lotoia.calibration.weight_calibrator", "evaluate_weight_configuration"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value

