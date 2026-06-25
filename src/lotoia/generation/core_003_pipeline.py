"""CORE_003 — Pipeline Simplificado de Geração Estrutural.

Arquitetura consolidada em 4 camadas:
- L1: Pool Generation (geração base)
- L2: Structural Policy (políticas estruturais consolidadas)
- L3: Anti-Clone + Diversity (diversidade e anti-duplicação)
- L4: Critical Digits (reforço de dezenas críticas)

Objetivo: Reduzir complexidade de 10 módulos para 4 camadas claras.
"""

from __future__ import annotations

import logging
from typing import Any

from lotoia.config.core_003_config import CORE_003_CONFIG, CalibrationPreset
from lotoia.statistics.structural_metrics_validator import (
    compute_structural_metrics,
    validate_structural_metrics,
)

logger = logging.getLogger(__name__)

__all__ = [
    "generate_core_003_games",
    "Core003Pipeline",
]


class Core003Pipeline:
    """Pipeline simplificado de geração estrutural."""

    def __init__(
        self,
        format: str = "15D",
        calibration: CalibrationPreset = "equilibrado",
    ):
        # Validar formato
        if format not in CORE_003_CONFIG["formats"]:
            raise ValueError(
                f"Formato '{format}' não encontrado. "
                f"Opções disponíveis: {list(CORE_003_CONFIG['formats'].keys())}"
            )

        # Validar preset de calibração
        if calibration not in CORE_003_CONFIG["calibration_presets"]:
            raise ValueError(
                f"Preset '{calibration}' não encontrado. "
                f"Opções disponíveis: {list(CORE_003_CONFIG['calibration_presets'].keys())}"
            )

        self.format = format
        self.calibration = calibration
        self.config = CORE_003_CONFIG
        self._metrics: dict[str, Any] = {}

    def generate(
        self,
        count: int,
        pool_size: int | None = None,
        target_contest: int | None = None,
    ) -> list[dict[str, Any]]:
        """Gera jogos usando pipeline simplificado de 4 camadas."""
        if pool_size is None:
            pool_size = max(count * 3, 100)

        logger.info(
            "[CORE_003] Iniciando geração | format=%s count=%d pool_size=%d calibration=%s",
            self.format,
            count,
            pool_size,
            self.calibration,
        )

        # L1: Pool Generation
        pool = self._l1_pool_generation(pool_size)
        self._metrics["pool_size"] = len(pool)

        # L2: Structural Policy
        pool = self._l2_structural_policy(pool)
        self._metrics["post_policy_size"] = len(pool)

        # L3: Anti-Clone + Diversity
        gp = self._l3_anti_clone_diversity(pool, count)
        self._metrics["gp_size"] = len(gp)

        # L4: Critical Digits
        gp = self._l4_critical_digits(gp)

        # Computar métricas finais
        self._compute_final_metrics(gp)

        logger.info(
            "[CORE_003] Geração concluída | gp_size=%d diversity=%.2f overlap=%.1f",
            len(gp),
            self._metrics.get("diversity_score", 0),
            self._metrics.get("avg_overlap", 0),
        )

        return gp

    def _l1_pool_generation(self, pool_size: int) -> list[dict[str, Any]]:
        """L1: Gera pool base de candidatos."""
        from lotoia.generation.lei15_core_002 import build_sovereign_pool
        from lotoia.governance.lei15_core_002_sovereign import get_core_002_config

        # Obter configuração do formato
        format_config = self.config["formats"][self.format]
        dezenas = format_config["dezenas"]

        # Gerar label do batch baseado no formato
        batch_label = f"STRUCT_LEI15_CORE_CANDIDATE_003_{self.format}_001"
        config = get_core_002_config(batch_label)

        # Gerar pool
        pool = build_sovereign_pool(pool_size, seed=42, history=[], config=config)

        # Ajustar tamanho dos jogos se necessário (para formatos > 15D)
        if dezenas != 15:
            for game in pool:
                if len(game.get("numbers", [])) != dezenas:
                    # Ajustar jogo para o tamanho correto
                    numbers = game.get("numbers", [])
                    if len(numbers) > dezenas:
                        game["numbers"] = numbers[:dezenas]
                    elif len(numbers) < dezenas:
                        # Adicionar dezenas aleatórias
                        import random

                        available = [n for n in range(1, 26) if n not in numbers]
                        needed = dezenas - len(numbers)
                        game["numbers"] = numbers + random.sample(
                            available, min(needed, len(available))
                        )

        logger.debug(
            "[CORE_003:L1] Pool gerado | size=%d format=%s dezenas=%d",
            len(pool),
            self.format,
            dezenas,
        )
        return pool

    def _l2_structural_policy(self, pool: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """L2: Aplica políticas estruturais consolidadas."""
        from lotoia.generation.m_core_003_prefix_suffix_policy import (
            enforce_gp_diversity_cap,
            pre_filter_pool_diversity,
        )

        # Pré-filtro de diversidade
        filtered = pre_filter_pool_diversity(pool, gp_size=len(pool) // 3)

        # Aplica caps de diversidade
        capped = enforce_gp_diversity_cap(
            filtered,
            pool,
            len(pool) // 3,
            fallback_pool=pool,
        )

        logger.debug("[CORE_003:L2] Políticas aplicadas | size=%d", len(capped))
        return capped

    def _l3_anti_clone_diversity(
        self,
        pool: list[dict[str, Any]],
        count: int,
    ) -> list[dict[str, Any]]:
        """L3: Anti-clone e diversidade."""
        from lotoia.generation.lei15_core_002 import apply_anti_clone_gp

        preset = self.config["calibration_presets"][self.calibration]
        max_overlap = preset.get("max_overlap", 10)

        gp = apply_anti_clone_gp(
            pool,
            pool,
            count,
            game_size=int(self.format.replace("D", "")),
            fallback_pool=pool,
        )

        # Aplica diversidade adicional se necessário
        if len(gp) < count:
            logger.warning(
                "[CORE_003:L3] GP incompleto | expected=%d actual=%d",
                count,
                len(gp),
            )

        logger.debug("[CORE_003:L3] Anti-clone aplicado | gp_size=%d", len(gp))
        return gp

    def _l4_critical_digits(self, gp: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """L4: Reforço de dezenas críticas."""
        from lotoia.generation.lei15_core_002 import apply_critical_digit_layer

        preset = self.config["calibration_presets"][self.calibration]
        boost_multiplier = preset.get("critical_digit_boost_multiplier", 1.0)

        # Aplica camada crítica
        gp = apply_critical_digit_layer(gp)

        # Ajusta boost conforme preset
        if boost_multiplier != 1.0:
            for game in gp:
                meta = game.get("lei15_core_002_metadata", {})
                current_boost = meta.get("critical_digit_boost", 0)
                meta["critical_digit_boost"] = current_boost * boost_multiplier
                game["lei15_core_002_metadata"] = meta

        logger.debug(
            "[CORE_003:L4] Critical digits aplicados | boost_multiplier=%.2f",
            boost_multiplier,
        )
        return gp

    def _compute_final_metrics(self, gp: list[dict[str, Any]]) -> None:
        """Computa métricas estruturais finais."""
        metrics = compute_structural_metrics(gp)
        validation = validate_structural_metrics(metrics)

        # Calcular diversity_score (1 - similaridade média)
        # Similaridade média é avg_overlap / game_size
        format_config = self.config["formats"][self.format]
        game_size = format_config["dezenas"]
        avg_overlap = metrics.get("avg_overlap", 0)
        diversity_score = 1.0 - (avg_overlap / game_size) if game_size > 0 else 0.0

        self._metrics.update(metrics)
        self._metrics["diversity_score"] = round(diversity_score, 4)
        self._metrics["validation"] = validation

        # Log de métricas
        logger.info(
            "[CORE_003] Métricas finais | "
            "triplet=%.1f%% overlap=%.1f diversity=%.2f valid=%s",
            metrics.get("triplet_010203_pct", 0) * 100,
            metrics.get("avg_overlap", 0),
            diversity_score,
            validation.get("valid", False),
        )

        if not validation.get("valid"):
            logger.warning(
                "[CORE_003] Validação falhou | violations=%s",
                validation.get("violations", []),
            )

    def get_metrics(self) -> dict[str, Any]:
        """Retorna métricas da última geração."""
        return self._metrics.copy()


def generate_core_003_games(
    format: str = "15D",
    count: int = 50,
    pool_size: int | None = None,
    calibration: CalibrationPreset = "equilibrado",
    target_contest: int | None = None,
) -> list[dict[str, Any]]:
    """Função simplificada para gerar jogos CORE_003.

    Args:
        format: Formato do jogo (15D, 17D, etc.)
        count: Quantidade de jogos a gerar
        pool_size: Tamanho do pool de candidatos (padrão: count * 3)
        calibration: Preset de calibração (conservador, equilibrado, agressivo)
        target_contest: Concurso alvo (opcional)

    Returns:
        Lista de jogos gerados com métricas estruturais

    Example:
        >>> games = generate_core_003_games(format="15D", count=50, calibration="equilibrado")
        >>> len(games)
        50
    """
    pipeline = Core003Pipeline(format=format, calibration=calibration)
    return pipeline.generate(
        count=count, pool_size=pool_size, target_contest=target_contest
    )
