"""Smart Orchestrator para CORE_003.

Camada de orquestração inteligente que conecta:
- Sistema de Feedback Automático
- Versionamento de Modelos
- Pipeline de Geração CORE_003
- Validação Walk-Forward (Fase 5)

Responsabilidades:
- Consultar feedback system para ajustar parâmetros
- Aplicar ajustes automáticos na configuração
- Selecionar/calibrar preset baseado em histórico
- Registrar versão quando há mudanças significativas
- Validar calibração com walk-forward temporal (Fase 5)
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Sequence

from lotoia.config.core_003_config import (
    CORE_003_CONFIG,
    CalibrationPreset,
    get_confidence_interval,
)
from lotoia.generation.post_contest_feedback import (
    PostContestFeedback,
    get_performance_trend,
)
from lotoia.generation.model_versioning import ModelVersioning
from lotoia.statistics.change_detector import ChangeDetector
from lotoia.validation.walk_forward_validator import (
    WalkForwardResult,
    WalkForwardValidationConfig,
    WalkForwardValidator,
)

logger = logging.getLogger(__name__)


class SmartOrchestrator:
    """Orquestrador inteligente do CORE_003."""

    def __init__(self, format: str = "15D", auto_calibrate: bool = False):
        self.format = format
        self.auto_calibrate = auto_calibrate
        self.feedback = PostContestFeedback()
        self.versioning = ModelVersioning()
        self.change_detector = ChangeDetector(confidence_level=0.95)
        self._adjustments_applied: list[str] = []
        self._last_walk_forward_result: WalkForwardResult | None = None

    def calibrate_preset(
        self,
        base_preset: CalibrationPreset = "equilibrado",
    ) -> tuple[CalibrationPreset, dict[str, Any]]:
        """Calibra preset baseado em feedback histórico.

        Args:
            base_preset: Preset base sugerido pelo usuário

        Returns:
            Tuple com (preset_calibrado, ajustes_aplicados)
        """
        if not self.auto_calibrate:
            logger.debug("[Orchestrator] Auto-calibrate desativado, usando preset base")
            return base_preset, {}

        # Consultar tendência de desempenho
        trend = get_performance_trend(last_n=5)
        logger.info("[Orchestrator] Tendência detectada: %s", trend.get("trend"))

        # Se não há dados suficientes, usar preset base
        if trend.get("trend") == "insufficient_data":
            logger.info("[Orchestrator] Dados insuficientes, usando preset base")
            return base_preset, {}

        # Obter sugestões pendentes
        suggestions = self.feedback.get_suggestions_summary()
        pending = suggestions.get("suggestions", [])

        if not pending:
            logger.info("[Orchestrator] Sem sugestões pendentes, usando preset base")
            return base_preset, {}

        # Aplicar ajustes baseado nas sugestões
        calibrated_preset, adjustments = self._apply_suggestions(
            base_preset, pending, trend
        )

        self._adjustments_applied = adjustments
        logger.info(
            "[Orchestrator] Preset calibrado: %s → %s | ajustes=%d",
            base_preset,
            calibrated_preset,
            len(adjustments),
        )

        return calibrated_preset, adjustments

    def calibrate_preset_temporal(
        self,
        base_preset: CalibrationPreset,
        all_contests: Sequence[int],
        *,
        training_contests: Sequence[int] | None = None,
        validation_contests: Sequence[int] | None = None,
        generator_fn: Callable | None = None,
        games_per_contest: int = 10,
    ) -> tuple[CalibrationPreset, dict[str, Any], WalkForwardResult | None]:
        """Calibra preset usando validação walk-forward temporal (Fase 5).
        
        Este método garante que a calibração não sofra de overfitting temporal,
        separando explicitamente dados de treino e validação.
        
        Args:
            base_preset: Preset base sugerido pelo usuário
            all_contests: Lista completa de concursos disponíveis
            training_contests: Concursos para treino (opcional, usa walk-forward automático)
            validation_contests: Concursos para validação (opcional)
            generator_fn: Função para gerar jogos (opcional, usa pipeline CORE_003)
            games_per_contest: Jogos a gerar por concurso para validação
        
        Returns:
            Tuple com (preset_calibrado, ajustes_aplicados, walk_forward_result)
        """
        logger.info(
            "[Orchestrator] Iniciando calibração temporal | "
            "base_preset=%s all_contests=%d",
            base_preset,
            len(all_contests),
        )
        
        # 1. Calibrar preset base (método existente)
        calibrated_preset, adjustments = self.calibrate_preset(base_preset)
        
        # 2. Executar validação walk-forward se possível
        walk_forward_result = None
        if generator_fn is not None:
            walk_forward_result = self.validate_with_walk_forward(
                all_contests=all_contests,
                generator_fn=generator_fn,
                training_contests=training_contests,
                validation_contests=validation_contests,
                games_per_contest=games_per_contest,
            )
            
            # 3. Se validação detectou problemas, ajustar preset
            if walk_forward_result and not walk_forward_result.is_valid():
                logger.warning(
                    "[Orchestrator] Walk-forward detectou problemas | "
                    "leakage=%s degradation=%s",
                    walk_forward_result.temporal_leakage_detected,
                    walk_forward_result.performance_degradation,
                )
                
                # Ajustar para preset mais conservador
                if calibrated_preset == "agressivo":
                    calibrated_preset = "equilibrado"
                    adjustments["walk_forward_adjustment"] = "agressivo → equilibrado"
                elif calibrated_preset == "equilibrado":
                    calibrated_preset = "conservador"
                    adjustments["walk_forward_adjustment"] = "equilibrado → conservador"
                
                logger.info(
                    "[Orchestrator] Preset ajustado por walk-forward: %s",
                    calibrated_preset,
                )
        
        return calibrated_preset, adjustments, walk_forward_result

    def validate_with_walk_forward(
        self,
        all_contests: Sequence[int],
        generator_fn: Callable,
        *,
        training_contests: Sequence[int] | None = None,
        validation_contests: Sequence[int] | None = None,
        test_contests: Sequence[int] | None = None,
        games_per_contest: int = 10,
        pool_size: int = 100,
    ) -> WalkForwardResult:
        """Executa validação walk-forward no pipeline CORE_003.
        
        Este método implementa a Fase 5: validação temporal rigorosa que
        separa explicitamente dados de treino, validação e teste.
        
        Args:
            all_contests: Lista completa de concursos disponíveis
            generator_fn: Função que gera jogos dado histórico e target_contest
            training_contests: Concursos para treino (opcional)
            validation_contests: Concursos para validação (opcional)
            test_contests: Concursos para teste (opcional)
            games_per_contest: Jogos a gerar por concurso
            pool_size: Tamanho do pool de candidatos
        
        Returns:
            Resultado da validação walk-forward
        """
        logger.info(
            "[Orchestrator] Executando validação walk-forward | "
            "all_contests=%d format=%s",
            len(all_contests),
            self.format,
        )
        
        # Construir configuração
        config = WalkForwardValidationConfig(
            all_contests=list(all_contests),
            training_contests=list(training_contests or all_contests[:int(len(all_contests) * 0.7)]),
            validation_contests=list(validation_contests or all_contests[int(len(all_contests) * 0.7):]),
            test_contests=list(test_contests or []),
        )
        
        # Executar validação
        validator = WalkForwardValidator(config)
        result = validator.validate(
            generator_fn,
            games_per_contest=games_per_contest,
            pool_size=pool_size,
        )
        
        self._last_walk_forward_result = result
        
        logger.info(
            "[Orchestrator] Walk-forward concluído | "
            "splits=%d games=%d valid=%s",
            result.total_splits,
            result.total_games_generated,
            result.is_valid(),
        )
        
        return result
    
    def get_last_walk_forward_result(self) -> WalkForwardResult | None:
        """Retorna último resultado de validação walk-forward."""
        return self._last_walk_forward_result

    def _apply_suggestions(
        self,
        base_preset: CalibrationPreset,
        suggestions: list[dict[str, Any]],
        trend: dict[str, Any],
    ) -> tuple[CalibrationPreset, dict[str, Any]]:
        """Aplica sugestões de ajuste ao preset com detecção estatística.

        Usa ChangeDetector para verificar se mudanças são estatisticamente
        significativas antes de aplicar ajustes, evitando overfitting.

        Returns:
            Tuple com (preset_ajustado, dicionario_de_ajustes)
        """
        adjustments = {}
        preset = base_preset

        # Analisar sugestões de alta prioridade
        high_priority = [s for s in suggestions if s.get("priority") == "high"]

        if high_priority:
            # Se há sugestões de alta prioridade, mudar para preset mais agressivo
            if base_preset == "conservador":
                preset = "equilibrado"
                adjustments["preset_changed"] = "conservador → equilibrado"
            elif base_preset == "equilibrado":
                preset = "agressivo"
                adjustments["preset_changed"] = "equilibrado → agressivo"

        # Aplicar ajustes específicos com detecção estatística
        for suggestion in suggestions:
            adj_type = suggestion.get("adjustment")
            current_rate = suggestion.get("current_rate")
            sample_size = suggestion.get("sample_size", 50)

            if adj_type == "increase_diversity":
                # Para diversidade, verificar se hit_rate está significativamente baixo
                if current_rate is not None:
                    should_adjust, result = (
                        self.change_detector.should_adjust_parameter(
                            metric_name="hit_rate_11_13",
                            current_rate=current_rate,
                            historical_config={"value": 0.15, "sample_size": 300},
                            sample_size_recent=sample_size,
                        )
                    )
                    if should_adjust:
                        adjustments["diversity_floor"] = "+0.03"
                        adjustments["overlap_penalty"] = "-0.05"
                        logger.info(
                            "[Orchestrator] Ajuste de diversidade aplicado (mudança significativa)"
                        )
                    else:
                        logger.debug(
                            "[Orchestrator] Ajuste de diversidade ignorado (mudança não significativa)"
                        )
                else:
                    # Fallback: aplicar sem detecção se não há dados
                    adjustments["diversity_floor"] = "+0.03"
                    adjustments["overlap_penalty"] = "-0.05"

            elif adj_type == "increase_triplet_cap":
                # Verificar se triplet_rate está significativamente baixo
                if current_rate is not None:
                    triplet_config = get_confidence_interval("triplet_010203")
                    should_adjust, result = (
                        self.change_detector.should_adjust_parameter(
                            metric_name="triplet_010203",
                            current_rate=current_rate,
                            historical_config=triplet_config,
                            sample_size_recent=sample_size,
                        )
                    )
                    if should_adjust:
                        current_freq = CORE_003_CONFIG["structural_policy"][
                            "triplet_010203"
                        ]["freq"]
                        adjustments["triplet_freq"] = f"{current_freq + 0.02:.2f}"
                        logger.info(
                            "[Orchestrator] Ajuste de triplet aplicado (mudança significativa)"
                        )
                    else:
                        logger.debug(
                            "[Orchestrator] Ajuste de triplet ignorado (mudança não significativa)"
                        )
                else:
                    # Fallback: aplicar sem detecção se não há dados
                    current_freq = CORE_003_CONFIG["structural_policy"][
                        "triplet_010203"
                    ]["freq"]
                    adjustments["triplet_freq"] = f"{current_freq + 0.02:.2f}"

            elif adj_type == "increase_suffix_cap":
                # Verificar se suffix_rate está significativamente baixo
                if current_rate is not None:
                    suffix_config = get_confidence_interval("suffix_232425")
                    should_adjust, result = (
                        self.change_detector.should_adjust_parameter(
                            metric_name="suffix_232425",
                            current_rate=current_rate,
                            historical_config=suffix_config,
                            sample_size_recent=sample_size,
                        )
                    )
                    if should_adjust:
                        current_freq = CORE_003_CONFIG["structural_policy"][
                            "suffix_232425"
                        ]["freq"]
                        adjustments["suffix_freq"] = f"{current_freq + 0.02:.2f}"
                        logger.info(
                            "[Orchestrator] Ajuste de suffix aplicado (mudança significativa)"
                        )
                    else:
                        logger.debug(
                            "[Orchestrator] Ajuste de suffix ignorado (mudança não significativa)"
                        )
                else:
                    # Fallback: aplicar sem detecção se não há dados
                    current_freq = CORE_003_CONFIG["structural_policy"][
                        "suffix_232425"
                    ]["freq"]
                    adjustments["suffix_freq"] = f"{current_freq + 0.02:.2f}"

        # Se tendência é declining, ser mais conservador
        if trend.get("trend") == "declining":
            if preset == "agressivo":
                preset = "equilibrado"
                adjustments["trend_adjustment"] = "declining → equilibrado"
            elif preset == "equilibrado":
                preset = "conservador"
                adjustments["trend_adjustment"] = "declining → conservador"

        return preset, adjustments

    def apply_adjustments_to_config(
        self,
        adjustments: dict[str, Any],
    ) -> dict[str, Any]:
        """Aplica ajustes à configuração do CORE_003.

        Args:
            adjustments: Dicionário com ajustes a aplicar

        Returns:
            Configuração ajustada
        """
        if not adjustments:
            return CORE_003_CONFIG.copy()

        # Criar cópia da configuração
        config = CORE_003_CONFIG.copy()

        # Aplicar ajustes de diversidade
        if "diversity_floor" in adjustments:
            delta = float(adjustments["diversity_floor"])
            current = config["calibration_presets"]["equilibrado"]["diversity_floor"]
            config["calibration_presets"]["equilibrado"]["diversity_floor"] = (
                current + delta
            )

        # Aplicar ajustes de overlap
        if "overlap_penalty" in adjustments:
            delta = float(adjustments["overlap_penalty"])
            current = config["calibration_presets"]["equilibrado"]["overlap_penalty"]
            config["calibration_presets"]["equilibrado"]["overlap_penalty"] = (
                current + delta
            )

        # Aplicar ajustes de triplet
        if "triplet_freq" in adjustments:
            new_freq = float(adjustments["triplet_freq"])
            config["structural_policy"]["triplet_010203"]["freq"] = new_freq

        # Aplicar ajustes de suffix
        if "suffix_freq" in adjustments:
            new_freq = float(adjustments["suffix_freq"])
            config["structural_policy"]["suffix_232425"]["freq"] = new_freq

        logger.info(
            "[Orchestrator] Configuração ajustada com %d parâmetros", len(adjustments)
        )
        return config

    def register_generation_version(
        self,
        preset_used: CalibrationPreset,
        adjustments: dict[str, Any],
        metrics: dict[str, Any] | None = None,
    ) -> str | None:
        """Registra versão da geração se houve ajustes significativos.

        Args:
            preset_used: Preset utilizado
            adjustments: Ajustes aplicados
            metrics: Métricas da geração (opcional)

        Returns:
            Versão registrada ou None se não houve mudanças significativas
        """
        if not adjustments:
            return None

        # Obter última versão
        latest = self.versioning.get_latest_version()
        current_version = latest["version"] if latest else "v3.0.0"

        # Incrementar versão (semver simples)
        parts = current_version.replace("v", "").split(".")
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        new_version = f"v{major}.{minor}.{patch + 1}"

        # Registrar nova versão
        changes = [f"Auto-calibração: {adj}" for adj in adjustments.values()]

        self.versioning.register_version(
            version=new_version,
            changes=changes,
            backtest_results=metrics,
            config_changes=adjustments,
        )

        logger.info("[Orchestrator] Versão registrada: %s", new_version)
        return new_version

    def get_orchestration_summary(self) -> dict[str, Any]:
        """Retorna resumo da orquestração.

        Returns:
            Dicionário com informações da orquestração
        """
        summary = {
            "format": self.format,
            "auto_calibrate": self.auto_calibrate,
            "adjustments_applied": self._adjustments_applied,
            "feedback_trend": get_performance_trend(last_n=5),
            "latest_version": self.versioning.get_latest_version(),
        }
        
        # Adicionar informações de walk-forward se disponível
        if self._last_walk_forward_result:
            summary["walk_forward_validation"] = {
                "executed": True,
                "total_splits": self._last_walk_forward_result.total_splits,
                "total_games": self._last_walk_forward_result.total_games_generated,
                "is_valid": self._last_walk_forward_result.is_valid(),
                "temporal_leakage": self._last_walk_forward_result.temporal_leakage_detected,
                "performance_degradation": self._last_walk_forward_result.performance_degradation,
            }
        else:
            summary["walk_forward_validation"] = {"executed": False}
        
        return summary


# Instância global
_orchestrator: SmartOrchestrator | None = None


def get_orchestrator(
    format: str = "15D",
    auto_calibrate: bool = False,
) -> SmartOrchestrator:
    """Retorna instância do orquestrador.

    Args:
        format: Formato dos jogos
        auto_calibrate: Se deve auto-calibrar

    Returns:
        Instância do SmartOrchestrator
    """
    global _orchestrator

    # Recriar se parâmetros mudaram
    if (
        _orchestrator is None
        or _orchestrator.format != format
        or _orchestrator.auto_calibrate != auto_calibrate
    ):
        _orchestrator = SmartOrchestrator(format=format, auto_calibrate=auto_calibrate)

    return _orchestrator
