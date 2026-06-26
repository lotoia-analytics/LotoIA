"""PatternStrategy — Geração baseada em padrões estruturais.

Prioriza padrões como triplet 01-02-03, suffix 23-24-25, paridade, etc.
"""

from __future__ import annotations

import random
from typing import Any

from lotoia.generation.pool_strategies.base_strategy import BasePoolStrategy


class PatternStrategy(BasePoolStrategy):
    """Estratégia baseada em padrões estruturais.
    
    Gera jogos priorizando padrões específicos:
    - Triplet 01-02-03 (~21% dos jogos)
    - Suffix 23-24-25 (~21% dos jogos)
    - Paridade balanceada
    - Soma no range esperado
    """

    def __init__(self, weight: float = 1.0, triplet_pct: float = 0.21, suffix_pct: float = 0.21):
        super().__init__(weight)
        self.triplet_pct = triplet_pct
        self.suffix_pct = suffix_pct

    def generate(
        self,
        pool_size: int,
        *,
        format: str = "15D",
        history: list[Any] | None = None,
        seed: int | None = None,
    ) -> list[dict[str, Any]]:
        """Gera pool priorizando padrões estruturais."""
        game_size = int(format.replace("D", ""))
        total_numbers = 25
        
        if seed is not None:
            random.seed(seed)
        
        # Calcular quantos jogos devem ter cada padrão
        triplet_count = int(pool_size * self.triplet_pct)
        suffix_count = int(pool_size * self.suffix_pct)
        pattern_count = max(triplet_count, suffix_count)
        
        pool: list[dict[str, Any]] = []
        attempts = 0
        max_attempts = pool_size * 50
        
        while len(pool) < pool_size and attempts < max_attempts:
            attempts += 1
            
            # Determinar qual padrão priorizar
            remaining = pool_size - len(pool)
            remaining_triplets = max(0, triplet_count - sum(1 for g in pool if g.get("has_triplet")))
            remaining_suffixes = max(0, suffix_count - sum(1 for g in pool if g.get("has_suffix")))
            
            if remaining_triplets > 0 and random.random() < 0.5:
                # Forçar triplet
                numbers = self._generate_with_triplet(game_size, total_numbers)
            elif remaining_suffixes > 0:
                # Forçar suffix
                numbers = self._generate_with_suffix(game_size, total_numbers)
            else:
                # Paridade balanceada
                numbers = self._generate_balanced(game_size, total_numbers)
            
            if numbers is None:
                continue
            
            game = self._build_game(numbers, format)
            pool.append(game)
        
        return pool

    def _generate_with_triplet(self, game_size: int, total: int) -> list[int] | None:
        """Gera jogo com triplet 01-02-03."""
        base = {1, 2, 3}
        remaining = game_size - len(base)
        
        available = [n for n in range(4, total + 1)]
        extras = random.sample(available, remaining)
        return sorted(list(base | set(extras)))

    def _generate_with_suffix(self, game_size: int, total: int) -> list[int] | None:
        """Gera jogo com suffix 23-24-25."""
        base = {23, 24, 25}
        remaining = game_size - len(base)
        
        available = [n for n in range(1, 23)]
        extras = random.sample(available, remaining)
        return sorted(list(base | set(extras)))

    def _generate_balanced(self, game_size: int, total: int) -> list[int] | None:
        """Gera jogo com paridade balanceada."""
        odd_total = (total + 1) // 2  # 13 ímpares (1,3,5...25)
        even_total = total // 2  # 12 pares (2,4,6...24)
        
        # Paridade balanceada
        odd_needed = game_size // 2
        even_needed = game_size - odd_needed
        
        if odd_needed > odd_total or even_needed > even_total:
            return None
        
        odds = random.sample(range(1, total + 1, 2), odd_needed)
        evens = random.sample(range(2, total + 1, 2), even_needed)
        
        return sorted(odds + evens)

    def get_strategy_name(self) -> str:
        return "pattern"

    def _build_game(self, numbers: list[int], format: str) -> dict[str, Any]:
        odd = sum(1 for n in numbers if n % 2 != 0)
        has_triplet = all(n in numbers for n in [1, 2, 3])
        has_suffix = all(n in numbers for n in [23, 24, 25])
        
        return {
            "numbers": numbers,
            "format": format,
            "odd": odd,
            "even": len(numbers) - odd,
            "sum": sum(numbers),
            "has_triplet": has_triplet,
            "has_suffix": has_suffix,
            "pool_strategy": "pattern",
        }
