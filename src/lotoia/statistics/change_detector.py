"""Detector de Mudanças Estatisticamente Significativas.

Este módulo fornece ferramentas para determinar se uma mudança observada
em métricas estatísticas é real (estatisticamente significativa) ou apenas
ruído estatístico normal.

Usa intervalos de confiança para tomar decisões objetivas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from lotoia.statistics.confidence_interval_calculator import (
    ConfidenceInterval,
    ConfidenceIntervalCalculator,
)


@dataclass
class ChangeDetectionResult:
    """Resultado da detecção de mudança."""

    is_significant: bool  # Se a mudança é estatisticamente significativa
    current_rate: float  # Taxa observada no período recente
    historical_rate: float  # Taxa histórica de referência
    difference: float  # Diferença absoluta (current - historical)
    relative_change: float  # Mudança relativa (difference / historical)
    confidence_interval: list[float]  # IC da taxa histórica
    z_score: float  # Estatística Z do teste
    p_value: float  # Valor p aproximado
    confidence_level: float  # Nível de confiança usado
    sample_size_recent: int  # Tamanho da amostra recente
    sample_size_historical: int  # Tamanho da amostra histórica
    detected_at: str  # Timestamp da detecção

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário."""
        return {
            "is_significant": self.is_significant,
            "current_rate": self.current_rate,
            "historical_rate": self.historical_rate,
            "difference": self.difference,
            "relative_change": self.relative_change,
            "confidence_interval": self.confidence_interval,
            "z_score": self.z_score,
            "p_value": self.p_value,
            "confidence_level": self.confidence_level,
            "sample_size_recent": self.sample_size_recent,
            "sample_size_historical": self.sample_size_historical,
            "detected_at": self.detected_at,
        }


class ChangeDetector:
    """Detector de mudanças estatisticamente significativas."""

    def __init__(self, confidence_level: float = 0.95):
        """
        Inicializa o detector.

        Args:
            confidence_level: Nível de confiança para testes (0.90, 0.95 ou 0.99)
        """
        self.confidence_level = confidence_level
        self.calculator = ConfidenceIntervalCalculator(confidence_level)

    def detect_change(
        self,
        current_rate: float,
        historical_rate: float,
        sample_size_recent: int,
        sample_size_historical: int,
    ) -> ChangeDetectionResult:
        """
        Detecta se há mudança estatisticamente significativa.

        Args:
            current_rate: Taxa observada no período recente (0.0 a 1.0)
            historical_rate: Taxa histórica de referência (0.0 a 1.0)
            sample_size_recent: Número de observações recentes
            sample_size_historical: Número de observações históricas

        Returns:
            ChangeDetectionResult com detalhes da análise

        Example:
            >>> detector = ChangeDetector(confidence_level=0.95)
            >>> result = detector.detect_change(
            ...     current_rate=0.15,  # 15% recente
            ...     historical_rate=0.21,  # 21% histórico
            ...     sample_size_recent=50,
            ...     sample_size_historical=300,
            ... )
            >>> if result.is_significant:
            ...     print(f"Mudança significativa: {result.relative_change:.1%}")
        """
        # Validar entradas
        if not (0.0 <= current_rate <= 1.0):
            raise ValueError(f"current_rate deve estar entre 0 e 1, got {current_rate}")
        if not (0.0 <= historical_rate <= 1.0):
            raise ValueError(
                f"historical_rate deve estar entre 0 e 1, got {historical_rate}"
            )
        if sample_size_recent <= 0:
            raise ValueError(
                f"sample_size_recent deve ser > 0, got {sample_size_recent}"
            )
        if sample_size_historical <= 0:
            raise ValueError(
                f"sample_size_historical deve ser > 0, got {sample_size_historical}"
            )

        # Calcular número de sucessos
        successes_recent = int(round(current_rate * sample_size_recent))
        successes_historical = int(round(historical_rate * sample_size_historical))

        # Calcular IC da taxa histórica
        historical_ci = self.calculator.calculate_proportion_interval(
            successes=successes_historical,
            sample_size=sample_size_historical,
        )

        # Calcular IC da taxa recente
        recent_ci = self.calculator.calculate_proportion_interval(
            successes=successes_recent,
            sample_size=sample_size_recent,
        )

        # Verificar se a taxa recente está fora do IC histórico
        is_significant = not historical_ci.contains(current_rate)

        # Calcular diferença
        difference = current_rate - historical_rate
        relative_change = difference / historical_rate if historical_rate > 0 else 0.0

        # Calcular estatística Z para comparação de proporções
        # Z = (p1 - p2) / sqrt(p*(1-p)*(1/n1 + 1/n2))
        # onde p é a proporção pooled
        p_pooled = (successes_recent + successes_historical) / (
            sample_size_recent + sample_size_historical
        )
        se_diff = (
            p_pooled
            * (1 - p_pooled)
            * (1 / sample_size_recent + 1 / sample_size_historical)
        ) ** 0.5

        if se_diff > 0:
            z_score = (current_rate - historical_rate) / se_diff
        else:
            z_score = 0.0

        # Aproximar p-value (two-tailed test)
        # Para Z ~ N(0,1), p-value ≈ 2 * (1 - Φ(|Z|))
        # Usando aproximação simples
        import math

        p_value = 2 * (1 - _normal_cdf(abs(z_score)))

        return ChangeDetectionResult(
            is_significant=is_significant,
            current_rate=current_rate,
            historical_rate=historical_rate,
            difference=difference,
            relative_change=relative_change,
            confidence_interval=[historical_ci.lower_bound, historical_ci.upper_bound],
            z_score=z_score,
            p_value=p_value,
            confidence_level=self.confidence_level,
            sample_size_recent=sample_size_recent,
            sample_size_historical=sample_size_historical,
            detected_at=datetime.now().isoformat(),
        )

    def should_adjust_parameter(
        self,
        metric_name: str,
        current_rate: float,
        historical_config: dict[str, Any],
        sample_size_recent: int,
    ) -> tuple[bool, ChangeDetectionResult | None]:
        """
        Decide se um parâmetro deve ser ajustado.

        Args:
            metric_name: Nome da métrica (ex: 'triplet_010203')
            current_rate: Taxa observada recentemente
            historical_config: Configuração histórica com IC
            sample_size_recent: Tamanho da amostra recente

        Returns:
            Tuple (should_adjust, result)
            - should_adjust: True se deve ajustar
            - result: ChangeDetectionResult ou None se não aplicável

        Example:
            >>> from lotoia.config.core_003_config import get_confidence_interval
            >>> detector = ChangeDetector(confidence_level=0.95)
            >>> triplet_config = get_confidence_interval('triplet_010203')
            >>> should_adjust, result = detector.should_adjust_parameter(
            ...     metric_name='triplet_010203',
            ...     current_rate=0.15,
            ...     historical_config=triplet_config,
            ...     sample_size_recent=50,
            ... )
            >>> if should_adjust:
            ...     print(f"Ajustar triplet_cap: mudança de {result.relative_change:.1%}")
        """
        # Extrair informações da configuração histórica
        historical_rate = historical_config.get("value")
        sample_size_historical = historical_config.get("sample_size", 300)

        if historical_rate is None:
            return False, None

        # Detectar mudança
        result = self.detect_change(
            current_rate=current_rate,
            historical_rate=historical_rate,
            sample_size_recent=sample_size_recent,
            sample_size_historical=sample_size_historical,
        )

        # Decidir se deve ajustar
        # Ajustar apenas se:
        # 1. Mudança é estatisticamente significativa
        # 2. Mudança é substancial (> 5% relativo)
        should_adjust = (
            result.is_significant
            and abs(result.relative_change) > 0.05  # Pelo menos 5% de mudança relativa
        )

        return should_adjust, result


def _normal_cdf(x: float) -> float:
    """
    Função de distribuição cumulativa da normal padrão.

    Aproximação usando função de erro (erf).
    Φ(x) = 0.5 * (1 + erf(x / sqrt(2)))
    """
    import math

    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


# Instância global com configuração padrão
_default_detector = ChangeDetector(confidence_level=0.95)


def is_statistically_significant_change(
    current_rate: float,
    historical_rate: float,
    sample_size_recent: int = 50,
    sample_size_historical: int = 300,
    confidence_level: float = 0.95,
) -> bool:
    """
    Função auxiliar para verificar se mudança é estatisticamente significativa.

    Args:
        current_rate: Taxa observada recentemente
        historical_rate: Taxa histórica de referência
        sample_size_recent: Tamanho da amostra recente (padrão: 50)
        sample_size_historical: Tamanho da amostra histórica (padrão: 300)
        confidence_level: Nível de confiança (padrão: 0.95)

    Returns:
        True se a mudança é estatisticamente significativa

    Example:
        >>> if is_statistically_significant_change(
        ...     current_rate=0.15,
        ...     historical_rate=0.21,
        ...     sample_size_recent=50,
        ...     sample_size_historical=300,
        ... ):
        ...     increase_triplet_cap()
    """
    detector = ChangeDetector(confidence_level=confidence_level)
    result = detector.detect_change(
        current_rate=current_rate,
        historical_rate=historical_rate,
        sample_size_recent=sample_size_recent,
        sample_size_historical=sample_size_historical,
    )
    return result.is_significant


def should_adjust_parameter(
    metric_name: str,
    current_rate: float,
    historical_config: dict[str, Any],
    sample_size_recent: int = 50,
    confidence_level: float = 0.95,
) -> tuple[bool, ChangeDetectionResult | None]:
    """
    Função auxiliar para decidir se parâmetro deve ser ajustado.

    Args:
        metric_name: Nome da métrica
        current_rate: Taxa observada recentemente
        historical_config: Configuração histórica com IC
        sample_size_recent: Tamanho da amostra recente (padrão: 50)
        confidence_level: Nível de confiança (padrão: 0.95)

    Returns:
        Tuple (should_adjust, result)

    Example:
        >>> from lotoia.config.core_003_config import get_confidence_interval
        >>> triplet_config = get_confidence_interval('triplet_010203')
        >>> should_adjust, result = should_adjust_parameter(
        ...     metric_name='triplet_010203',
        ...     current_rate=0.15,
        ...     historical_config=triplet_config,
        ...     sample_size_recent=50,
        ... )
        >>> if should_adjust:
        ...     increase_triplet_cap()
    """
    detector = ChangeDetector(confidence_level=confidence_level)
    return detector.should_adjust_parameter(
        metric_name=metric_name,
        current_rate=current_rate,
        historical_config=historical_config,
        sample_size_recent=sample_size_recent,
    )
