"""Validação temporal e walk-forward para CORE_003.

Módulos de validação rigorosa que garantem separação temporal
entre configuração e teste, evitando overfitting temporal.
"""

from lotoia.validation.walk_forward_validator import (
    WalkForwardValidator,
    WalkForwardValidationConfig,
    WalkForwardResult,
)

__all__ = [
    "WalkForwardValidator",
    "WalkForwardValidationConfig",
    "WalkForwardResult",
]
