"""Pool Multi-Estratégia — Fase 6.

Combina múltiplas estratégias de geração para criar pools mais diversos:
- FrequencyStrategy: baseado em frequência histórica
- PatternStrategy: baseado em padrões estruturais
- CoverageStrategy: baseado em cobertura de dezenas
- RandomStrategy: diversidade pura
"""

from lotoia.generation.pool_strategies.base_strategy import BasePoolStrategy
from lotoia.generation.pool_strategies.frequency_strategy import FrequencyStrategy
from lotoia.generation.pool_strategies.pattern_strategy import PatternStrategy
from lotoia.generation.pool_strategies.coverage_strategy import CoverageStrategy
from lotoia.generation.pool_strategies.random_strategy import RandomStrategy
from lotoia.generation.pool_strategies.strategy_factory import (
    MultiStrategyPoolGenerator,
    DEFAULT_STRATEGY_WEIGHTS,
)

__all__ = [
    "BasePoolStrategy",
    "FrequencyStrategy",
    "PatternStrategy",
    "CoverageStrategy",
    "RandomStrategy",
    "MultiStrategyPoolGenerator",
    "DEFAULT_STRATEGY_WEIGHTS",
]
