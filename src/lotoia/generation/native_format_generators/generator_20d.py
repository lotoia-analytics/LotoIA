"""Gerador nativo 20D — Fase 3.

Motor de geração específico para 20 dezenas com políticas próprias:
- Paridade: 10/10, 11/9 ou 9/11
- Overlap esperado: ~13.3
- Repetição: 9-14 com concurso anterior
"""

from __future__ import annotations

import logging
from typing import Any

from lotoia.generation.native_format_generators.base_generator import BaseNativeGenerator
from lotoia.generation.native_format_generators.generator_factory import register_generator

logger = logging.getLogger(__name__)

# Políticas 20D
PARITY_TARGETS_20D: tuple[tuple[int, int], ...] = ((10, 10), (11, 9), (9, 11))
REPEAT_MIN_20D = 9
REPEAT_MAX_20D = 14
SEQUENCE_MAX_20D = 6
CORE_NUMBERS_20D: tuple[int, ...] = (7, 12, 16, 23)
DISCOURAGED_NUMBERS_20D: tuple[int, ...] = (2, 4, 11, 24, 25)


class Generator20D(BaseNativeGenerator):
    """Gerador nativo para formato 20 dezenas."""

    def __init__(self):
        super().__init__(format="20D", game_size=20, total_numbers=25)

    def build_pool(
        self,
        pool_size: int,
        *,
        seed: int | None = None,
        history: list[object] | None = None,
    ) -> list[dict[str, Any]]:
        """Gera pool nativo 20D."""
        self.set_seed(seed)
        previous_numbers = self._extract_previous_numbers(history)
        parity_targets = list(PARITY_TARGETS_20D)

        pool: list[dict[str, Any]] = []
        generated = 0
        max_attempts = pool_size * 60

        for _ in range(max_attempts):
            if len(pool) >= pool_size:
                break

            odd_count, even_count = self.rng.choice(parity_targets)

            card = self._generate_game_with_parity(
                odd_count, even_count,
                previous_numbers=previous_numbers,
                min_repeat=REPEAT_MIN_20D,
                max_repeat=REPEAT_MAX_20D,
            )

            if card is None:
                continue

            card_sum = sum(card)
            if not (230 <= card_sum <= 280):
                continue

            game = self._build_game_dict(card, "20D")
            pool.append(game)
            generated += 1

        self._log_pool_generation(pool, pool_size, generated)
        return pool

    def get_format_policies(self) -> dict[str, Any]:
        return {
            "format": "20D",
            "game_size": 20,
            "total_numbers": 25,
            "parity_targets": list(PARITY_TARGETS_20D),
            "repeat_min": REPEAT_MIN_20D,
            "repeat_max": REPEAT_MAX_20D,
            "sequence_max": SEQUENCE_MAX_20D,
            "core_numbers": list(CORE_NUMBERS_20D),
            "discouraged_numbers": list(DISCOURAGED_NUMBERS_20D),
            "overlap_target": 13.3,
            "overlap_range": (9.5, 18.0),
            "triplet_target": 0.45,
            "triplet_range": (0.10, 0.70),
            "sum_range": (230, 280),
        }

    def _build_game_dict(self, numbers: list[int], format: str) -> dict[str, Any]:
        odd = sum(1 for n in numbers if n % 2 != 0)
        return {
            "numbers": numbers,
            "format": format,
            "odd": odd,
            "even": len(numbers) - odd,
            "sum": sum(numbers),
            "native_generator": "20D",
            "generation_method": "native_format_generator",
        }


register_generator("20D", Generator20D)
