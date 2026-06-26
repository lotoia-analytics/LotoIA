"""CoverageStrategy — Geração baseada em cobertura de dezenas.

Maximiza a cobertura de todas as dezenas no pool.
"""

from __future__ import annotations

import random
from typing import Any

from lotoia.generation.pool_strategies.base_strategy import BasePoolStrategy


class CoverageStrategy(BasePoolStrategy):
    """Estratégia baseada em cobertura de dezenas.
    
    Gera jogos maximizando a presença de todas as dezenas no pool.
    Útil para garantir que dezenas menos frequentes apareçam.
    """

    def generate(
        self,
        pool_size: int,
        *,
        format: str = "15D",
        history: list[Any] | None = None,
        seed: int | None = None,
    ) -> list[dict[str, Any]]:
        """Gera pool maximizando cobertura."""
        game_size = int(format.replace("D", ""))
        total_numbers = 25
        
        if seed is not None:
            random.seed(seed)
        
        pool: list[dict[str, Any]] = []
        coverage = {n: 0 for n in range(1, total_numbers + 1)}
        attempts = 0
        max_attempts = pool_size * 50
        
        while len(pool) < pool_size and attempts < max_attempts:
            attempts += 1
            
            # Priorizar dezenas menos cobertas
            sorted_by_coverage = sorted(coverage.keys(), key=lambda n: (coverage[n], random.random()))
            
            # Selecionar dezenas priorizando as menos cobertas
            selected = set()
            for num in sorted_by_coverage:
                if len(selected) >= game_size:
                    break
                selected.add(num)
            
            # Se ainda faltam, completar aleatoriamente
            if len(selected) < game_size:
                available = [n for n in range(1, total_numbers + 1) if n not in selected]
                needed = game_size - len(selected)
                selected.update(random.sample(available, needed))
            
            numbers = sorted(list(selected))
            
            # Atualizar cobertura
            for n in numbers:
                coverage[n] += 1
            
            game = self._build_game(numbers, format)
            pool.append(game)
        
        return pool

    def get_strategy_name(self) -> str:
        return "coverage"

    def _build_game(self, numbers: list[int], format: str) -> dict[str, Any]:
        odd = sum(1 for n in numbers if n % 2 != 0)
        return {
            "numbers": numbers,
            "format": format,
            "odd": odd,
            "even": len(numbers) - odd,
            "sum": sum(numbers),
            "pool_strategy": "coverage",
        }
