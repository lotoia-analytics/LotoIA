"""Smart Orchestrator para CORE_003.

Camada de orquestração inteligente que conecta:
- Sistema de Feedback Automático
- Versionamento de Modelos
- Pipeline de Geração CORE_003

Responsabilidades:
- Consultar feedback system para ajustar parâmetros
- Aplicar ajustes automáticos na configuração
- Selecionar/calibrar preset baseado em histórico
- Registrar versão quando há mudanças significativas
"""

from __future__ import annotations

import logging
from typing import Any

from lotoia.config.core_003_config import CORE_003_CONFIG, CalibrationPreset
from lotoia.generation.post_contest_feedback import (
    PostContestFeedback,
    get_performance_trend,
)
from lotoia.generation.model_versioning import ModelVersioning

logger = logging.getLogger(__name__)


class SmartOrchestrator:
    """Orquestrador inteligente do CORE_003."""

    def __init__(self, format: str = "15D", auto_calibrate: bool = False):
        self.format = format
        self.auto_calibrate = auto_calibrate
        self.feedback = PostContestFeedback()
        self.versioning = ModelVersioning()
        self._adjustments_applied: list[str] = []

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

    def _apply_suggestions(
        self,
        base_preset: CalibrationPreset,
        suggestions: list[dict[str, Any]],
        trend: dict[str, Any],
    ) -> tuple[CalibrationPreset, dict[str, Any]]:
        """Aplica sugestões de ajuste ao preset.

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

        # Aplicar ajustes específicos
        for suggestion in suggestions:
            adj_type = suggestion.get("adjustment")

            if adj_type == "increase_diversity":
                adjustments["diversity_floor"] = "+0.03"
                adjustments["overlap_penalty"] = "-0.05"

            elif adj_type == "increase_triplet_cap":
                current_freq = CORE_003_CONFIG["structural_policy"]["triplet_010203"][
                    "freq"
                ]
                adjustments["triplet_freq"] = f"{current_freq + 0.02:.2f}"

            elif adj_type == "increase_suffix_cap":
                current_freq = CORE_003_CONFIG["structural_policy"]["suffix_232425"][
                    "freq"
                ]
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
        return {
            "format": self.format,
            "auto_calibrate": self.auto_calibrate,
            "adjustments_applied": self._adjustments_applied,
            "feedback_trend": get_performance_trend(last_n=5),
            "latest_version": self.versioning.get_latest_version(),
        }


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
