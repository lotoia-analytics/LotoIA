"""Gerador nativo 15D — Fase 3.

Reutiliza o motor soberano CORE_002 existente (build_sovereign_pool)
que já é nativo para 15 dezenas.
"""

from __future__ import annotations

import logging
from typing import Any

from lotoia.generation.native_format_generators.base_generator import (
    BaseNativeGenerator,
)
from lotoia.generation.native_format_generators.generator_factory import (
    register_generator,
)

logger = logging.getLogger(__name__)

# Políticas 15D (baseadas em CORE_002 e structural_policy_15d)
# Expandido para cobrir 88.7% dos casos reais (últimos 300 concursos)
# 6/9=9%, 7/8=26.7%, 8/7=34%, 9/6=19%
PARITY_TARGETS_15D: tuple[tuple[int, int], ...] = ((6, 9), (7, 8), (8, 7), (9, 6))
REPEAT_MIN_15D = 7
REPEAT_MAX_15D = 10
SEQUENCE_MAX_15D = 6
CORE_NUMBERS_15D: tuple[int, ...] = (7, 12, 16, 23)
DISCOURAGED_NUMBERS_15D: tuple[int, ...] = (2, 4, 11, 15, 24, 25)


class Generator15D(BaseNativeGenerator):
    """Gerador nativo para formato 15 dezenas.

    Usa o motor soberano CORE_002 (build_sovereign_pool) que já é
    otimizado para 15D com políticas institucionais completas.
    """

    def __init__(self):
        super().__init__(format="15D", game_size=15, total_numbers=25)

    def build_pool(
        self,
        pool_size: int,
        *,
        seed: int | None = None,
        history: list[object] | None = None,
    ) -> list[dict[str, Any]]:
        """Gera pool nativo 15D via CORE_002 soberano + L6 balance filter."""
        from lotoia.generation.lei15_core_002 import build_sovereign_pool
        from lotoia.generation.lei15_core_balance_filter import apply_balance_filter
        from lotoia.governance.lei15_core_002_sovereign import get_core_002_config

        resolved_seed = int(seed) if seed is not None else 42
        resolved_history = list(history or [])

        # Obter configuração soberana CORE_002
        batch_label = "STRUCT_LEI15_CORE_CANDIDATE_003_15D_NATIVE"
        config = get_core_002_config(batch_label)

        # Gerar pool via motor soberano (nativo 15D)
        pool = build_sovereign_pool(
            pool_size, seed=resolved_seed, history=resolved_history, config=config
        )

        # L6: Aplicar filtro de balanceamento estrutural (M-OPS-083)
        # Garante composite_score >= 0.80 (98% dos concursos reais)
        pool = apply_balance_filter(pool, threshold=0.80, min_balance=0.50)

        # Se o filtro reduziu muito o pool, gerar mais candidatos
        if len(pool) < pool_size:
            logger.warning(
                "[15D] Pool reduzido pelo balance filter: %d < %d. "
                "Gerando pool adicional...",
                len(pool),
                pool_size,
            )
            # Gerar pool adicional com seed diferente
            additional_pool = build_sovereign_pool(
                pool_size * 2,
                seed=resolved_seed + 1000,
                history=resolved_history,
                config=config,
            )
            additional_pool = apply_balance_filter(
                additional_pool, threshold=0.80, min_balance=0.50
            )

            # Combinar pools (evitando duplicatas)
            existing_keys = {tuple(g.get("numbers", [])) for g in pool}
            for game in additional_pool:
                key = tuple(game.get("numbers", []))
                if key not in existing_keys:
                    pool.append(game)
                    existing_keys.add(key)
                    if len(pool) >= pool_size:
                        break

        # Log estruturado
        generated_count = len(pool)
        self._log_pool_generation(pool, pool_size, generated_count)

        return pool

    def get_format_policies(self) -> dict[str, Any]:
        """Retorna políticas estruturais 15D."""
        return {
            "format": "15D",
            "game_size": 15,
            "total_numbers": 25,
            "parity_targets": list(PARITY_TARGETS_15D),
            "repeat_min": REPEAT_MIN_15D,
            "repeat_max": REPEAT_MAX_15D,
            "sequence_max": SEQUENCE_MAX_15D,
            "core_numbers": list(CORE_NUMBERS_15D),
            "discouraged_numbers": list(DISCOURAGED_NUMBERS_15D),
            "overlap_target": 10.0,
            "overlap_range": (7.0, 13.0),
            "triplet_target": 0.21,
            "triplet_range": (0.10, 0.35),
            "sum_range": (180, 220),
        }


# Auto-registrar no factory
register_generator("15D", Generator15D)
