"""Classe base para geradores nativos por formato — Fase 3.

Interface comum para todos os geradores nativos (15D-23D).
Cada formato implementa suas próprias políticas estruturais.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from random import Random
from typing import Any

logger = logging.getLogger(__name__)


class BaseNativeGenerator(ABC):
    """Interface base para geradores nativos por formato.
    
    Cada formato (15D, 17D, 18D, 20D, 23D) implementa:
    - Paridade específica (ímpar/par)
    - Overlap esperado entre jogos
    - Triplet/suffix caps próprios
    - Distribuição de soma contextual
    """

    def __init__(self, format: str, game_size: int, total_numbers: int = 25):
        self.format = format
        self.game_size = game_size
        self.total_numbers = total_numbers
        self._rng: Random | None = None

    @property
    def rng(self) -> Random:
        """Retorna o gerador de números aleatórios."""
        if self._rng is None:
            self._rng = Random()
        return self._rng

    def set_seed(self, seed: int | None) -> None:
        """Define seed para reprodutibilidade."""
        if seed is not None:
            self._rng = Random(abs(int(seed)) % 1_000_003 + 17)
        else:
            self._rng = Random()

    @abstractmethod
    def build_pool(
        self,
        pool_size: int,
        *,
        seed: int | None = None,
        history: list[object] | None = None,
    ) -> list[dict[str, Any]]:
        """Gera pool nativo de candidatos para este formato.
        
        Args:
            pool_size: Quantidade de jogos no pool
            seed: Seed para reprodutibilidade
            history: Histórico de concursos (opcional)
        
        Returns:
            Lista de jogos (dicts com 'numbers' e metadados)
        """
        pass

    @abstractmethod
    def get_format_policies(self) -> dict[str, Any]:
        """Retorna políticas estruturais específicas deste formato.
        
        Returns:
            Dict com paridade, overlap, triplet, sum_range, etc.
        """
        pass

    def _compute_odd_numbers(self) -> list[int]:
        """Retorna lista de dezenas ímpares disponíveis."""
        return [n for n in range(1, self.total_numbers + 1) if n % 2 != 0]

    def _compute_even_numbers(self) -> list[int]:
        """Retorna lista de dezenas pares disponíveis."""
        return [n for n in range(1, self.total_numbers + 1) if n % 2 == 0]

    def _generate_game_with_parity(
        self,
        odd_count: int,
        even_count: int,
        previous_numbers: set[int] | None = None,
        min_repeat: int | None = None,
        max_repeat: int | None = None,
    ) -> list[int] | None:
        """Gera jogo respeitando paridade e opcionalmente repetição.
        
        Args:
            odd_count: Quantidade de ímpares
            even_count: Quantidade de pares
            previous_numbers: Dezenas do concurso anterior
            min_repeat: Mínimo de repetições com concurso anterior
            max_repeat: Máximo de repetições com concurso anterior
        
        Returns:
            Lista de dezenas ou None se não conseguiu gerar
        """
        odd_pool = self._compute_odd_numbers()
        even_pool = self._compute_even_numbers()

        for _ in range(500):
            try:
                odd_selected = set(self.rng.sample(odd_pool, odd_count))
                even_selected = set(self.rng.sample(even_pool, even_count))
            except ValueError:
                continue

            card = sorted(odd_selected | even_selected)
            if len(card) != self.game_size:
                continue

            # Verificar repetição com concurso anterior
            if previous_numbers and min_repeat is not None and max_repeat is not None:
                repeat_count = len(set(card) & previous_numbers)
                if repeat_count < min_repeat or repeat_count > max_repeat:
                    continue

            # Verificar sequência máxima (regra soberana)
            if self._has_excessive_sequence(card):
                continue

            return card

        return None

    def _has_excessive_sequence(self, numbers: list[int], max_seq: int = 6) -> bool:
        """Verifica se há sequência consecutiva maior que max_seq."""
        if not numbers:
            return False
        sorted_nums = sorted(numbers)
        seq_len = 1
        for i in range(1, len(sorted_nums)):
            if sorted_nums[i] == sorted_nums[i - 1] + 1:
                seq_len += 1
                if seq_len > max_seq:
                    return True
            else:
                seq_len = 1
        return False

    def _extract_previous_numbers(
        self, history: list[object] | None
    ) -> set[int]:
        """Extrai dezenas do último concurso do histórico."""
        if not history:
            return set()
        last = history[-1]
        numbers = getattr(last, "numbers", None)
        if numbers:
            return {int(n) for n in numbers if 1 <= int(n) <= self.total_numbers}
        if isinstance(last, dict):
            raw = last.get("numbers") or last.get("dezenas") or []
            return {int(n) for n in raw if 1 <= int(n) <= self.total_numbers}
        return set()

    def _compute_parity_targets(self) -> list[tuple[int, int]]:
        """Retorna targets de paridade para este formato.
        
        Subclasses devem sobrescrever para definir paridades específicas.
        """
        odd_total = len(self._compute_odd_numbers())
        even_total = len(self._compute_even_numbers())
        
        # Distribuição equilibrada em torno do game_size
        base_odd = self.game_size // 2
        targets = []
        
        for delta in range(0, 3):
            odd = base_odd + delta
            even = self.game_size - odd
            if 0 < odd <= odd_total and 0 < even <= even_total:
                targets.append((odd, even))
            if delta > 0:
                odd = base_odd - delta
                even = self.game_size - odd
                if 0 < odd <= odd_total and 0 < even <= even_total:
                    targets.append((odd, even))
        
        return targets if targets else [(base_odd, self.game_size - base_odd)]

    def _log_pool_generation(
        self,
        pool: list[dict[str, Any]],
        pool_size: int,
        generated_count: int,
    ) -> None:
        """Log estruturado da geração do pool."""
        if not pool:
            logger.warning(
                "[NativeGen:%s] Pool vazio | target=%d",
                self.format,
                pool_size,
            )
            return

        # Calcular métricas
        triplet_count = sum(
            1 for g in pool
            if 1 in g.get("numbers", [])
            and 2 in g.get("numbers", [])
            and 3 in g.get("numbers", [])
        )
        triplet_pct = triplet_count / len(pool) * 100

        # Overlap médio
        overlaps = []
        for i, g1 in enumerate(pool[:50]):  # sample para performance
            for g2 in pool[i + 1:50]:
                overlaps.append(
                    len(set(g1.get("numbers", [])) & set(g2.get("numbers", [])))
                )
        avg_overlap = sum(overlaps) / len(overlaps) if overlaps else 0

        # Paridade
        parity_dist: dict[str, int] = {}
        for g in pool:
            nums = g.get("numbers", [])
            odd = sum(1 for n in nums if n % 2 != 0)
            key = f"{odd}/{len(nums) - odd}"
            parity_dist[key] = parity_dist.get(key, 0) + 1

        logger.info(
            "[NativeGen:%s] Pool gerado | target=%d actual=%d generated=%d | "
            "triplet=%d (%.1f%%) | avg_overlap=%.1f | parity=%s",
            self.format,
            pool_size,
            len(pool),
            generated_count,
            triplet_count,
            triplet_pct,
            avg_overlap,
            dict(sorted(parity_dist.items(), key=lambda x: -x[1])[:3]),
        )
