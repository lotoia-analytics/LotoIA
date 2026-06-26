"""CORE_003 — Pipeline Simplificado de Geração Estrutural.

Arquitetura consolidada em 4 camadas:
- L1: Pool Generation (multi-estratégia Fase 6 + nativo Fase 3)
- L2: Structural Policy (políticas estruturais consolidadas)
- L3: Anti-Clone + Diversity (diversidade e anti-duplicação)
- L4: Critical Digits (refinamento de dezenas críticas)

Fase 3: Cada formato (15D, 17D, 18D, 20D, 23D) tem seu próprio
motor de geração nativo.

Fase 6: Pool multi-estratégia combina frequência (30%), padrões (25%),
cobertura (25%) e aleatório (20%) para diversidade real no pool base.
"""

from __future__ import annotations

import logging
from typing import Any

from lotoia.config.core_003_config import CORE_003_CONFIG, CalibrationPreset, is_native_format
from lotoia.generation.pool_strategies import MultiStrategyPoolGenerator
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
        config: dict[str, Any] | None = None,
        use_multi_strategy: bool = True,
        strategy_weights: dict[str, float] | None = None,
    ):
        if format not in CORE_003_CONFIG["formats"]:
            raise ValueError(
                f"Formato '{format}' não encontrado. "
                f"Opções disponíveis: {list(CORE_003_CONFIG['formats'].keys())}"
            )

        if calibration not in CORE_003_CONFIG["calibration_presets"]:
            raise ValueError(
                f"Preset '{calibration}' não encontrado. "
                f"Opções disponíveis: {list(CORE_003_CONFIG['calibration_presets'].keys())}"
            )

        self.format = format
        self.calibration = calibration
        self.config = config or CORE_003_CONFIG
        self._metrics: dict[str, Any] = {}
        self.use_multi_strategy = use_multi_strategy
        self.strategy_weights = strategy_weights
        
        # Inicializar gerador multi-estratégia se habilitado
        self._multi_strategy_generator: MultiStrategyPoolGenerator | None = None
        if use_multi_strategy:
            self._multi_strategy_generator = MultiStrategyPoolGenerator(
                weights=strategy_weights
            )

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
            "[CORE_003] Iniciando geração | format=%s count=%d pool_size=%d calibration=%s native=%s multi_strategy=%s",
            self.format,
            count,
            pool_size,
            self.calibration,
            is_native_format(self.format),
            self.use_multi_strategy,
        )

        # L1: Pool Generation (MULTI-ESTRATÉGIA + NATIVO ou expandido)
        pool = self._l1_pool_generation(pool_size)
        self._metrics["pool_size"] = len(pool)
        self._metrics["native_generation"] = is_native_format(self.format)
        self._metrics["multi_strategy"] = self.use_multi_strategy
        
        # Métricas de estratégia (Fase 6)
        if self._multi_strategy_generator:
            breakdown = self._multi_strategy_generator.get_strategy_breakdown(pool)
            self._metrics["strategy_breakdown"] = breakdown

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
            "[CORE_003] Geração concluída | gp_size=%d diversity=%.2f overlap=%.1f native=%s multi_strategy=%s",
            len(gp),
            self._metrics.get("diversity_score", 0),
            self._metrics.get("avg_overlap", 0),
            self._metrics.get("native_generation"),
            self._metrics.get("multi_strategy"),
        )

        return gp

    def _l1_pool_generation(self, pool_size: int) -> list[dict[str, Any]]:
        """L1: Gera pool base de candidatos.
        
        Fase 6: Se multi-estratégia habilitado, combina:
        - 30% frequency: baseado em frequência histórica
        - 25% pattern: baseado em padrões estruturais
        - 25% coverage: baseado em cobertura de dezenas
        - 20% random: diversidade pura
        
        Para formatos nativos (15D, 17D, 18D, 20D, 23D), usa gerador nativo.
        Para formatos sem nativo, expande a partir do 15D.
        """
        if self.use_multi_strategy and self._multi_strategy_generator:
            return self._l1_multi_strategy_pool(pool_size)
        elif is_native_format(self.format):
            return self._l1_native_pool_generation(pool_size)
        else:
            return self._l1_expanded_pool_generation(pool_size)

    def _l1_multi_strategy_pool(self, pool_size: int) -> list[dict[str, Any]]:
        """L1 multi-estratégia: combina frequência, padrão, cobertura e aleatório."""
        pool = self._multi_strategy_generator.generate(
            pool_size,
            format=self.format,
            history=[],
            seed=42,
        )
        
        logger.debug(
            "[CORE_003:L1] Pool MULTI-ESTRATÉGIA gerado | format=%s size=%d",
            self.format,
            len(pool),
        )
        return pool

    def _l1_native_pool_generation(self, pool_size: int) -> list[dict[str, Any]]:
        """L1 nativo: usa gerador nativo do formato (Fase 3)."""
        from lotoia.generation.native_format_generators import get_native_generator

        generator = get_native_generator(self.format)
        pool = generator.build_pool(pool_size, seed=42, history=[])

        logger.debug(
            "[CORE_003:L1] Pool NATIVO gerado | format=%s size=%d",
            self.format,
            len(pool),
        )
        return pool

    def _l1_expanded_pool_generation(self, pool_size: int) -> list[dict[str, Any]]:
        """L1 expandido: gera 15D e expande para formatos sem gerador nativo."""
        from lotoia.generation.lei15_core_002 import build_sovereign_pool
        from lotoia.governance.lei15_core_002_sovereign import get_core_002_config

        format_config = self.config["formats"][self.format]
        dezenas = format_config["dezenas"]

        batch_label = f"STRUCT_LEI15_CORE_CANDIDATE_003_{self.format}_001"
        config = get_core_002_config(batch_label)

        pool_15d = build_sovereign_pool(pool_size, seed=42, history=[], config=config)

        if dezenas == 15:
            logger.debug("[CORE_003:L1] Pool 15D gerado | size=%d", len(pool_15d))
            return pool_15d

        # Expandir jogos de forma inteligente
        pool = []
        for game_15d in pool_15d:
            base_numbers = set(game_15d.get("numbers", []))
            available = [n for n in range(1, 26) if n not in base_numbers]
            needed = dezenas - len(base_numbers)

            if needed > 0 and len(available) >= needed:
                import random
                random.seed(hash(tuple(sorted(base_numbers))))
                extra_numbers = random.sample(available, needed)
                new_numbers = sorted(list(base_numbers) + extra_numbers)
            else:
                new_numbers = sorted(list(base_numbers))

            new_game = game_15d.copy()
            new_game["numbers"] = new_numbers
            new_game["original_size"] = 15
            new_game["expanded_to"] = dezenas
            new_game["native_generator"] = False

            pool.append(new_game)

        logger.debug(
            "[CORE_003:L1] Pool EXPANDIDO | format=%s base=%d expanded=%d",
            self.format,
            len(pool_15d),
            len(pool),
        )
        return pool

    def _l2_structural_policy(self, pool: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """L2: Aplica políticas estruturais consolidadas."""
        from lotoia.generation.m_core_003_prefix_suffix_policy import (
            enforce_gp_diversity_cap,
            pre_filter_pool_diversity,
        )

        filtered = pre_filter_pool_diversity(pool, gp_size=len(pool) // 3)
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

        gp = apply_anti_clone_gp(
            pool,
            pool,
            count,
            game_size=int(self.format.replace("D", "")),
            fallback_pool=pool,
        )

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

        gp = apply_critical_digit_layer(gp)

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

        format_config = self.config["formats"][self.format]
        game_size = format_config["dezenas"]

        validation_limits = self.config["validation_limits"]

        # Triplet 01-02-03
        triplet_limits = validation_limits["triplet_by_format"].get(
            self.format, validation_limits["triplet_by_format"]["15D"]
        )
        triplet_pct = metrics.get("triplet_010203_pct", 0)
        triplet_valid = triplet_limits["min"] <= triplet_pct <= triplet_limits["max"]

        # Overlap
        overlap_limits = validation_limits["avg_overlap_by_format"].get(
            self.format, validation_limits["avg_overlap_by_format"]["15D"]
        )
        avg_overlap = metrics.get("avg_overlap", 0)
        overlap_valid = overlap_limits["min"] <= avg_overlap <= overlap_limits["max"]

        # Diversity score
        diversity_score = 1.0 - (avg_overlap / game_size) if game_size > 0 else 0.0
        diversity_limits = validation_limits["diversity_score"]
        diversity_valid = diversity_score >= diversity_limits["min"]

        violations = []
        warnings = []

        if not triplet_valid:
            if triplet_pct < triplet_limits["min"]:
                violations.append(
                    f"Triplet 01-02-03 muito baixo: {triplet_pct:.1%} (mínimo: {triplet_limits['min']:.1%})"
                )
            else:
                violations.append(
                    f"Triplet 01-02-03 muito alto: {triplet_pct:.1%} (máximo: {triplet_limits['max']:.1%})"
                )

        if not overlap_valid:
            if avg_overlap < overlap_limits["min"]:
                violations.append(
                    f"Overlap médio muito baixo: {avg_overlap:.1f} (mínimo: {overlap_limits['min']:.1f})"
                )
            else:
                violations.append(
                    f"Overlap médio muito alto: {avg_overlap:.1f} (máximo: {overlap_limits['max']:.1f})"
                )

        if not diversity_valid:
            warnings.append(
                f"Diversity score baixo: {diversity_score:.2f} (mínimo: {diversity_limits['min']:.2f})"
            )

        validation = {
            "valid": len(violations) == 0,
            "violations": violations,
            "warnings": warnings,
            "format": self.format,
            "game_size": game_size,
        }

        self._metrics.update(metrics)
        self._metrics["diversity_score"] = round(diversity_score, 4)
        self._metrics["validation"] = validation

        logger.info(
            "[CORE_003] Métricas finais | format=%s game_size=%d | "
            "triplet=%.1f%% overlap=%.1f diversity=%.2f valid=%s native=%s multi_strategy=%s",
            self.format,
            game_size,
            triplet_pct * 100,
            avg_overlap,
            diversity_score,
            validation.get("valid", False),
            is_native_format(self.format),
            self.use_multi_strategy,
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
    auto_calibrate: bool = False,
    version: str | None = None,
    use_multi_strategy: bool = True,
    strategy_weights: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Função simplificada para gerar jogos CORE_003.

    Fase 3: Formatos nativos (15D, 17D, 18D, 20D, 23D) usam
    geradores dedicados. Demais formatos usam expansão 15D.
    
    Fase 6: Pool multi-estratégia combina frequência, padrões,
    cobertura e aleatório para diversidade real no pool base.

    Args:
        format: Formato do jogo (15D, 17D, etc.)
        count: Quantidade de jogos a gerar
        pool_size: Tamanho do pool de candidatos
        calibration: Preset de calibração
        target_contest: Concurso alvo
        auto_calibrate: Auto-calibrar baseado em feedback
        version: Versão específica do modelo
        use_multi_strategy: Usar pool multi-estratégia (Fase 6)
        strategy_weights: Pesos customizados para estratégias

    Returns:
        Lista de jogos gerados com métricas estruturais
    """
    if auto_calibrate:
        from lotoia.generation.smart_orchestrator import get_orchestrator

        orchestrator = get_orchestrator(format=format, auto_calibrate=True)
        calibrated_preset, adjustments = orchestrator.calibrate_preset(calibration)
        config = orchestrator.apply_adjustments_to_config(adjustments)

        if adjustments:
            orchestrator.register_generation_version(
                preset_used=calibrated_preset,
                adjustments=adjustments,
            )

        pipeline = Core003Pipeline(
            format=format,
            calibration=calibrated_preset,
            config=config,
            use_multi_strategy=use_multi_strategy,
            strategy_weights=strategy_weights,
        )
    else:
        pipeline = Core003Pipeline(
            format=format,
            calibration=calibration,
            use_multi_strategy=use_multi_strategy,
            strategy_weights=strategy_weights,
        )

    return pipeline.generate(
        count=count, pool_size=pool_size, target_contest=target_contest
    )
