"""RandomStrategy — Geração puramente aleatória.

Diversidade pura sem viés de frequência, padrão ou cobertura.
"""

from __future__ import annotations

import random
from typing import Any

from lotoia.generation.pool_strategies.base_strategy import BasePoolStrategy


class RandomStrategy(BasePoolStrategy):
    """Estratégia de geração puramente aleatória.
    
    Gera jogos sem viés específico, garantindo diversidade pura.
    """

    def generate(
        self,
        pool_size: int,
        *,
        format: str = "15D",
        history: list[Any] | None = None,
        seed: int | None = None,
    ) -> list[dict[str, Any]]:
        """Gera pool puramente aleatório."""
        game_size = int(format.replace("D", ""))
        total_numbers = 25
        
        if seed is not None:
            random.seed(seed)
        
        pool: list[dict[str, Any]] = []
        attempts = 0
        max_attempts = pool_size * 20  # Aleatório falha menos
        
        while len(pool) < pool_size and attempts < max_attempts:
            attempts += 1
            
            # Seleção puramente aleatória
            numbers = sorted(random.sample(range(1, total_numbers + 1), game_size))
            
            game = self._build_game(numbers, format)
            pool.append(game)
        
        return pool

    def get_strategy_name(self) -> str:
        return "random"

    def _build_game(self, numbers: list[int], format: str) -> dict[str, Any]:
        odd = sum(1 for n in numbers if n % 2 != 0)
        return {
            "numbers": numbers,
            "format": format,
            "odd": odd,
            "even": len(numbers) - odd,
            "sum": sum(numbers),
            "pool_strategy": "random",
        }
