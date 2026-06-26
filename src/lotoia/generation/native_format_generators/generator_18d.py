"""Gerador nativo 18D — Fase 3.

Motor de geração específico para 18 dezenas com políticas próprias:
- Paridade: 9/9, 10/8 ou 8/10
- Overlap esperado: ~12.0
- Repetição: 8-12 com concurso anterior
"""

from __future__ import annotations

import logging
from typing import Any

from lotoia.generation.native_format_generators.base_generator import BaseNativeGenerator
from lotoia.generation.native_format_generators.generator_factory import register_generator

logger = logging.getLogger(__name__)

# Políticas 18D
PARITY_TARGETS_18D: tuple[tuple[int, int], ...] = ((9, 9), (10, 8), (8, 10))
REPEAT_MIN_18D = 8
REPEAT_MAX_18D = 12
SEQUENCE_MAX_18D = 6
CORE_NUMBERS_18D: tuple[int, ...] = (7, 12, 16, 23)
DISCOURAGED_NUMBERS_18D: tuple[int, ...] = (2, 4, 11, 24, 25)


class Generator18D(BaseNativeGenerator):
    """Gerador nativo para formato 18 dezenas."""

    def __init__(self):
        super().__init__(format="18D", game_size=18, total_numbers=25)

    def build_pool(
        self,
        pool_size: int,
        *,
        seed: int | None = None,
        history: list[object] | None = None,
    ) -> list[dict[str, Any]]:
        """Gera pool nativo 18D."""
        self.set_seed(seed)
        previous_numbers = self._extract_previous_numbers(history)
        parity_targets = list(PARITY_TARGETS_18D)

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
                min_repeat=REPEAT_MIN_18D,
                max_repeat=REPEAT_MAX_18D,
            )

            if card is None:
                continue

            card_sum = sum(card)
            if not (210 <= card_sum <= 260):
                continue

            game = self._build_game_dict(card, "18D")
            pool.append(game)
            generated += 1

        self._log_pool_generation(pool, pool_size, generated)
        return pool

    def get_format_policies(self) -> dict[str, Any]:
        return {
            "format": "18D",
            "game_size": 18,
            "total_numbers": 25,
            "parity_targets": list(PARITY_TARGETS_18D),
            "repeat_min": REPEAT_MIN_18D,
            "repeat_max": REPEAT_MAX_18D,
            "sequence_max": SEQUENCE_MAX_18D,
            "core_numbers": list(CORE_NUMBERS_18D),
            "discouraged_numbers": list(DISCOURAGED_NUMBERS_18D),
            "overlap_target": 12.0,
            "overlap_range": (8.5, 16.0),
            "triplet_target": 0.35,
            "triplet_range": (0.10, 0.60),
            "sum_range": (210, 260),
        }

    def _build_game_dict(self, numbers: list[int], format: str) -> dict[str, Any]:
        odd = sum(1 for n in numbers if n % 2 != 0)
        return {
            "numbers": numbers,
            "format": format,
            "odd": odd,
            "even": len(numbers) - odd,
            "sum": sum(numbers),
            "native_generator": "18D",
            "generation_method": "native_format_generator",
        }


register_generator("18D", Generator18D)
