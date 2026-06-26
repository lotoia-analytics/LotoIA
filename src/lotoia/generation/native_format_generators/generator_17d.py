"""Gerador nativo 17D — Fase 3.

Motor de geração específico para 17 dezenas com políticas próprias:
- Paridade: 9/8 ou 8/9
- Overlap esperado: ~11.3
- Repetição: 8-11 com concurso anterior
- Triplet/suffix caps próprios
"""

from __future__ import annotations

import logging
from typing import Any

from lotoia.generation.native_format_generators.base_generator import BaseNativeGenerator
from lotoia.generation.native_format_generators.generator_factory import register_generator

logger = logging.getLogger(__name__)

# Políticas 17D
PARITY_TARGETS_17D: tuple[tuple[int, int], ...] = ((9, 8), (8, 9))
REPEAT_MIN_17D = 8
REPEAT_MAX_17D = 11
SEQUENCE_MAX_17D = 6
CORE_NUMBERS_17D: tuple[int, ...] = (7, 12, 16, 23)
DISCOURAGED_NUMBERS_17D: tuple[int, ...] = (2, 4, 11, 24, 25)


class Generator17D(BaseNativeGenerator):
    """Gerador nativo para formato 17 dezenas.
    
    Gera jogos nativamente respeitando:
    - Paridade preferencial 9/8 ou 8/9
    - Overlap médio esperado ~11.3
    - Repetição 8-11 com concurso anterior
    - Soma no range 200-250
    """

    def __init__(self):
        super().__init__(format="17D", game_size=17, total_numbers=25)

    def build_pool(
        self,
        pool_size: int,
        *,
        seed: int | None = None,
        history: list[object] | None = None,
    ) -> list[dict[str, Any]]:
        """Gera pool nativo 17D."""
        self.set_seed(seed)
        previous_numbers = self._extract_previous_numbers(history)
        parity_targets = list(PARITY_TARGETS_17D)

        pool: list[dict[str, Any]] = []
        generated = 0
        max_attempts = pool_size * 60

        for _ in range(max_attempts):
            if len(pool) >= pool_size:
                break

            # Selecionar target de paridade
            odd_count, even_count = self.rng.choice(parity_targets)

            card = self._generate_game_with_parity(
                odd_count, even_count,
                previous_numbers=previous_numbers,
                min_repeat=REPEAT_MIN_17D,
                max_repeat=REPEAT_MAX_17D,
            )

            if card is None:
                continue

            # Verificar soma
            card_sum = sum(card)
            if not (200 <= card_sum <= 250):
                continue

            # Construir jogo
            game = self._build_game_dict(card, "17D")
            pool.append(game)
            generated += 1

        self._log_pool_generation(pool, pool_size, generated)
        return pool

    def get_format_policies(self) -> dict[str, Any]:
        """Retorna políticas estruturais 17D."""
        return {
            "format": "17D",
            "game_size": 17,
            "total_numbers": 25,
            "parity_targets": list(PARITY_TARGETS_17D),
            "repeat_min": REPEAT_MIN_17D,
            "repeat_max": REPEAT_MAX_17D,
            "sequence_max": SEQUENCE_MAX_17D,
            "core_numbers": list(CORE_NUMBERS_17D),
            "discouraged_numbers": list(DISCOURAGED_NUMBERS_17D),
            "overlap_target": 11.3,
            "overlap_range": (8.0, 15.0),
            "triplet_target": 0.30,
            "triplet_range": (0.10, 0.60),
            "sum_range": (200, 250),
        }

    def _build_game_dict(self, numbers: list[int], format: str) -> dict[str, Any]:
        """Constrói dict de jogo com metadados."""
        odd = sum(1 for n in numbers if n % 2 != 0)
        return {
            "numbers": numbers,
            "format": format,
            "odd": odd,
            "even": len(numbers) - odd,
            "sum": sum(numbers),
            "native_generator": "17D",
            "generation_method": "native_format_generator",
        }


register_generator("17D", Generator17D)
