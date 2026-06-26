"""Gerador nativo 23D — Fase 3.

Motor de geração específico para 23 dezenas com políticas próprias:
- Paridade: 12/11 ou 11/12
- Overlap esperado: ~15.3
- Repetição: 10-16 com concurso anterior
- 23D escolhe 23 de 25 dezenas — apenas 2 ficam de fora
"""

from __future__ import annotations

import logging
from typing import Any

from lotoia.generation.native_format_generators.base_generator import BaseNativeGenerator
from lotoia.generation.native_format_generators.generator_factory import register_generator

logger = logging.getLogger(__name__)

# Políticas 23D
PARITY_TARGETS_23D: tuple[tuple[int, int], ...] = ((12, 11), (11, 12))
REPEAT_MIN_23D = 10
REPEAT_MAX_23D = 16
SEQUENCE_MAX_23D = 7  # 23D permite sequência maior (só 2 dezenas excluídas)
CORE_NUMBERS_23D: tuple[int, ...] = (7, 12, 16, 23)
DISCOURAGED_NUMBERS_23D: tuple[int, ...] = (2, 4, 11, 24, 25)


class Generator23D(BaseNativeGenerator):
    """Gerador nativo para formato 23 dezenas.
    
    Em 23D, apenas 2 dezenas de 25 ficam de fora por jogo.
    A estratégia é selecionar as dezenas excluídas e construir o jogo.
    """

    def __init__(self):
        super().__init__(format="23D", game_size=23, total_numbers=25)

    def build_pool(
        self,
        pool_size: int,
        *,
        seed: int | None = None,
        history: list[object] | None = None,
    ) -> list[dict[str, Any]]:
        """Gera pool nativo 23D via estratégia de exclusão.
        
        Em vez de sortear 23 dezenas, sortear 2 para excluir —
        garante paridade correta e diversidade.
        """
        self.set_seed(seed)
        previous_numbers = self._extract_previous_numbers(history)

        pool: list[dict[str, Any]] = []
        generated = 0
        max_attempts = pool_size * 40
        seen: set[tuple[int, ...]] = set()

        for _ in range(max_attempts):
            if len(pool) >= pool_size:
                break

            # Estratégia: sortear 2 dezenas para EXCLUIR
            # Garante que o jogo resultante terá paridade balanceada
            excluded = self.rng.sample(range(1, 26), 2)
            card = sorted(set(range(1, 26)) - set(excluded))

            if len(card) != 23:
                continue

            card_tuple = tuple(card)
            if card_tuple in seen:
                continue
            seen.add(card_tuple)

            # Verificar paridade
            odd_count = sum(1 for n in card if n % 2 != 0)
            even_count = 23 - odd_count
            parity_ok = any(
                odd_count == t[0] and even_count == t[1]
                for t in PARITY_TARGETS_23D
            )
            if not parity_ok:
                continue

            # Verificar repetição com concurso anterior
            if previous_numbers:
                repeat_count = len(set(card) & previous_numbers)
                if repeat_count < REPEAT_MIN_23D or repeat_count > REPEAT_MAX_23D:
                    continue

            # Verificar soma
            card_sum = sum(card)
            if not (260 <= card_sum <= 310):
                continue

            game = self._build_game_dict(card, "23D")
            pool.append(game)
            generated += 1

        self._log_pool_generation(pool, pool_size, generated)
        return pool

    def get_format_policies(self) -> dict[str, Any]:
        return {
            "format": "23D",
            "game_size": 23,
            "total_numbers": 25,
            "parity_targets": list(PARITY_TARGETS_23D),
            "repeat_min": REPEAT_MIN_23D,
            "repeat_max": REPEAT_MAX_23D,
            "sequence_max": SEQUENCE_MAX_23D,
            "core_numbers": list(CORE_NUMBERS_23D),
            "discouraged_numbers": list(DISCOURAGED_NUMBERS_23D),
            "overlap_target": 15.3,
            "overlap_range": (11.0, 22.0),
            "triplet_target": 0.60,
            "triplet_range": (0.10, 0.95),
            "sum_range": (260, 310),
        }

    def _build_game_dict(self, numbers: list[int], format: str) -> dict[str, Any]:
        odd = sum(1 for n in numbers if n % 2 != 0)
        return {
            "numbers": numbers,
            "format": format,
            "odd": odd,
            "even": len(numbers) - odd,
            "sum": sum(numbers),
            "native_generator": "23D",
            "generation_method": "native_format_generator",
        }


register_generator("23D", Generator23D)
