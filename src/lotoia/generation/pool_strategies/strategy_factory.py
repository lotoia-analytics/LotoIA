"""StrategyFactory — Combina múltiplas estratégias de pool.

Factory para gerar pool combinando diferentes estratégias com pesos.
"""

from __future__ import annotations

import logging
from typing import Any

from lotoia.generation.pool_strategies.base_strategy import BasePoolStrategy
from lotoia.generation.pool_strategies.frequency_strategy import FrequencyStrategy
from lotoia.generation.pool_strategies.pattern_strategy import PatternStrategy
from lotoia.generation.pool_strategies.coverage_strategy import CoverageStrategy
from lotoia.generation.pool_strategies.random_strategy import RandomStrategy

logger = logging.getLogger(__name__)

# Pesos padrão para as estratégias
DEFAULT_STRATEGY_WEIGHTS = {
    "frequency": 0.30,  # 30% baseado em frequência
    "pattern": 0.25,    # 25% baseado em padrões
    "coverage": 0.25,   # 25% baseado em cobertura
    "random": 0.20,     # 20% aleatório
}


class MultiStrategyPoolGenerator:
    """Gerador de pool multi-estratégia.
    
    Combina múltiplas estratégias com pesos configuráveis para gerar
    pools mais diversos desde a base.
    
    Uso:
        >>> generator = MultiStrategyPoolGenerator()
        >>> pool = generator.generate(pool_size=100, format="15D")
        
        >>> # Com pesos customizados
        >>> generator = MultiStrategyPoolGenerator(weights={
        ...     "frequency": 0.40,
        ...     "pattern": 0.20,
        ...     "coverage": 0.20,
        ...     "random": 0.20,
        ... })
        >>> pool = generator.generate(pool_size=100)
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        strategies: list[BasePoolStrategy] | None = None,
    ):
        """Inicializa gerador multi-estratégia.
        
        Args:
            weights: Pesos das estratégias (padrão: DEFAULT_STRATEGY_WEIGHTS)
            strategies: Lista de estratégias customizadas (opcional)
        """
        if strategies:
            self.strategies = strategies
        else:
            weights = weights or DEFAULT_STRATEGY_WEIGHTS
            self._validate_weights(weights)
            self.strategies = self._build_strategies(weights)
        
        logger.info(
            "[MultiStrategy] Inicializado com %d estratégias | pesos=%s",
            len(self.strategies),
            {s.get_strategy_name(): s.weight for s in self.strategies},
        )

    def _validate_weights(self, weights: dict[str, float]) -> None:
        """Valida que pesos somam 1.0."""
        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(
                f"Strategy weights must sum to 1.0, got {total:.3f}"
            )

    def _build_strategies(self, weights: dict[str, float]) -> list[BasePoolStrategy]:
        """Constrói lista de estratégias com pesos."""
        strategies: list[BasePoolStrategy] = []
        
        if "frequency" in weights:
            strategies.append(FrequencyStrategy(weight=weights["frequency"]))
        if "pattern" in weights:
            strategies.append(PatternStrategy(weight=weights["pattern"]))
        if "coverage" in weights:
            strategies.append(CoverageStrategy(weight=weights["coverage"]))
        if "random" in weights:
            strategies.append(RandomStrategy(weight=weights["random"]))
        
        return strategies

    def generate(
        self,
        pool_size: int,
        *,
        format: str = "15D",
        history: list[Any] | None = None,
        seed: int | None = None,
    ) -> list[dict[str, Any]]:
        """Gera pool combinando múltiplas estratégias.
        
        Args:
            pool_size: Tamanho total do pool
            format: Formato dos jogos
            history: Histórico de concursos
            seed: Seed para reprodutibilidade
        
        Returns:
            Pool combinado de todas as estratégias
        """
        logger.info(
            "[MultiStrategy] Gerando pool | size=%d format=%s strategies=%d",
            pool_size,
            format,
            len(self.strategies),
        )
        
        combined_pool: list[dict[str, Any]] = []
        
        for strategy in self.strategies:
            # Calcular tamanho do sub-pool para esta estratégia
            strategy_pool_size = int(pool_size * strategy.weight)
            if strategy_pool_size == 0:
                continue
            
            # Gerar sub-pool
            strategy_seed = (seed + hash(strategy.get_strategy_name())) % 1_000_000 if seed else None
            sub_pool = strategy.generate(
                strategy_pool_size,
                format=format,
                history=history,
                seed=strategy_seed,
            )
            
            combined_pool.extend(sub_pool)
            
            logger.debug(
                "[MultiStrategy:%s] Sub-pool gerado | size=%d",
                strategy.get_strategy_name(),
                len(sub_pool),
            )
        
        # Se sobrou espaço (arredondamento), completar com random
        remaining = pool_size - len(combined_pool)
        if remaining > 0:
            random_strategy = RandomStrategy(weight=0)
            filler = random_strategy.generate(
                remaining,
                format=format,
                history=history,
                seed=seed,
            )
            combined_pool.extend(filler)
            logger.debug(
                "[MultiStrategy] Pool preenchido com random | filler=%d",
                len(filler),
            )
        
        # Embarhar pool para não ficar agrupado por estratégia
        import random as rnd
        if seed:
            rnd.seed(seed)
        rnd.shuffle(combined_pool)
        
        logger.info(
            "[MultiStrategy] Pool combinado | total=%d",
            len(combined_pool),
        )
        
        return combined_pool

    def get_strategy_breakdown(self, pool: list[dict[str, Any]]) -> dict[str, int]:
        """Retorna distribuição de estratégias no pool."""
        breakdown: dict[str, int] = {}
        for game in pool:
            strategy = game.get("pool_strategy", "unknown")
            breakdown[strategy] = breakdown.get(strategy, 0) + 1
        return breakdown
