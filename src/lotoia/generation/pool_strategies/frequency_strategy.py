"""FrequencyStrategy — Geração baseada em frequência histórica.

Prioriza dezenas mais frequentes no histórico.
"""

from __future__ import annotations

import random
from collections import Counter
from typing import Any

from lotoia.generation.pool_strategies.base_strategy import BasePoolStrategy


class FrequencyStrategy(BasePoolStrategy):
    """Estratégia baseada em frequência histórica.
    
    Analisa histórico e prioriza dezenas mais frequentes na composição.
    """

    def generate(
        self,
        pool_size: int,
        *,
        format: str = "15D",
        history: list[Any] | None = None,
        seed: int | None = None,
    ) -> list[dict[str, Any]]:
        """Gera pool priorizando dezenas frequentes."""
        game_size = int(format.replace("D", ""))
        total_numbers = 25
        
        # Configurar seed
        if seed is not None:
            random.seed(seed)
        
        # Calcular frequência se há histórico
        freq: Counter[int] = Counter()
        if history:
            for contest in history:
                numbers = contest.get("numbers", []) if isinstance(contest, dict) else getattr(contest, "numbers", [])
                freq.update(numbers)
        else:
            # Frequência uniforme se não há histórico
            for n in range(1, total_numbers + 1):
                freq[n] = 1
        
        # Gerar pool
        pool: list[dict[str, Any]] = []
        attempts = 0
        max_attempts = pool_size * 50
        
        while len(pool) < pool_size and attempts < max_attempts:
            attempts += 1
            
            # Selecionar dezenas ponderadas por frequência
            numbers_pool = list(range(1, total_numbers + 1))
            weights = [freq.get(n, 1) for n in numbers_pool]
            
            selected = random.choices(numbers_pool, weights=weights, k=game_size)
            selected = sorted(set(selected))
            
            if len(selected) != game_size:
                continue
            
            game = self._build_game(selected, format)
            pool.append(game)
        
        return pool

    def get_strategy_name(self) -> str:
        return "frequency"

    def _build_game(self, numbers: list[int], format: str) -> dict[str, Any]:
        odd = sum(1 for n in numbers if n % 2 != 0)
        return {
            "numbers": numbers,
            "format": format,
            "odd": odd,
            "even": len(numbers) - odd,
            "sum": sum(numbers),
            "pool_strategy": "frequency",
        }
