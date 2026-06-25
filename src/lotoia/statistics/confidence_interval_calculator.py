"""Calculadora de Intervalos de Confiança para Políticas Estruturais.

Calcula intervalos de confiança estatística para métricas da Lotofácil,
permitindo distinguir variações reais de ruído estatístico.

Baseado em distribuição binomial para proporções e normal para médias.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ConfidenceInterval:
    """Resultado do cálculo de intervalo de confiança."""

    value: float  # Valor pontual (proporção ou média)
    lower_bound: float  # Limite inferior do intervalo
    upper_bound: float  # Limite superior do intervalo
    confidence_level: float  # Nível de confiança (ex: 0.95)
    sample_size: int  # Tamanho da amostra
    margin_of_error: float  # Margem de erro
    last_updated: str  # Data da última atualização

    def contains(self, test_value: float) -> bool:
        """Verifica se um valor está dentro do intervalo de confiança."""
        return self.lower_bound <= test_value <= self.upper_bound

    def is_significantly_different(self, other_value: float) -> bool:
        """Verifica se um valor é significativamente diferente do valor observado."""
        return not self.contains(other_value)

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário."""
        return {
            "value": self.value,
            "confidence_interval": [self.lower_bound, self.upper_bound],
            "confidence_level": self.confidence_level,
            "sample_size": self.sample_size,
            "margin_of_error": self.margin_of_error,
            "last_updated": self.last_updated,
        }


class ConfidenceIntervalCalculator:
    """Calculadora de intervalos de confiança para métricas da Lotofácil."""

    # Valores Z para diferentes níveis de confiança
    Z_SCORES = {
        0.90: 1.645,
        0.95: 1.960,
        0.99: 2.576,
    }

    def __init__(self, confidence_level: float = 0.95):
        """
        Inicializa a calculadora.

        Args:
            confidence_level: Nível de confiança (0.90, 0.95 ou 0.99)
        """
        if confidence_level not in self.Z_SCORES:
            raise ValueError(
                f"Nível de confiança {confidence_level} não suportado. "
                f"Use um dos valores: {list(self.Z_SCORES.keys())}"
            )
        self.confidence_level = confidence_level
        self.z_score = self.Z_SCORES[confidence_level]

    def calculate_proportion_interval(
        self,
        successes: int,
        sample_size: int,
    ) -> ConfidenceInterval:
        """
        Calcula intervalo de confiança para uma proporção.

        Usa a aproximação normal para distribuição binomial.

        Args:
            successes: Número de sucessos (ex: concursos com triplet 01-02-03)
            sample_size: Tamanho total da amostra (ex: total de concursos)

        Returns:
            ConfidenceInterval com o intervalo calculado

        Example:
            >>> calc = ConfidenceIntervalCalculator(confidence_level=0.95)
            >>> # Triplet 01-02-03 apareceu 63 vezes em 300 concursos
            >>> ci = calc.calculate_proportion_interval(63, 300)
            >>> print(f"Proporção: {ci.value:.2%} ± {ci.margin_of_error:.2%}")
            Proporção: 21.00% ± 4.64%
        """
        if sample_size <= 0:
            raise ValueError("sample_size deve ser maior que zero")

        if successes < 0 or successes > sample_size:
            raise ValueError(
                f"successes ({successes}) deve estar entre 0 e sample_size ({sample_size})"
            )

        # Proporção observada
        p_hat = successes / sample_size

        # Erro padrão da proporção
        standard_error = math.sqrt((p_hat * (1 - p_hat)) / sample_size)

        # Margem de erro
        margin_of_error = self.z_score * standard_error

        # Intervalo de confiança
        lower_bound = max(0.0, p_hat - margin_of_error)
        upper_bound = min(1.0, p_hat + margin_of_error)

        return ConfidenceInterval(
            value=p_hat,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            confidence_level=self.confidence_level,
            sample_size=sample_size,
            margin_of_error=margin_of_error,
            last_updated=datetime.now().isoformat(),
        )

    def calculate_mean_interval(
        self,
        values: list[float],
    ) -> ConfidenceInterval:
        """
        Calcula intervalo de confiança para uma média.

        Assume distribuição normal dos dados.

        Args:
            values: Lista de valores observados

        Returns:
            ConfidenceInterval com o intervalo calculado

        Example:
            >>> calc = ConfidenceIntervalCalculator(confidence_level=0.95)
            >>> # Overlap médio de 50 jogos
            >>> overlaps = [9.2, 10.1, 9.8, 10.5, 9.9, ...]
            >>> ci = calc.calculate_mean_interval(overlaps)
            >>> print(f"Média: {ci.value:.2f} ± {ci.margin_of_error:.2f}")
        """
        if not values:
            raise ValueError("values não pode ser vazia")

        sample_size = len(values)

        # Média amostral
        mean = sum(values) / sample_size

        # Desvio padrão amostral
        if sample_size > 1:
            variance = sum((x - mean) ** 2 for x in values) / (sample_size - 1)
            std_dev = math.sqrt(variance)
        else:
            std_dev = 0.0

        # Erro padrão da média
        standard_error = std_dev / math.sqrt(sample_size)

        # Margem de erro
        margin_of_error = self.z_score * standard_error

        # Intervalo de confiança
        lower_bound = mean - margin_of_error
        upper_bound = mean + margin_of_error

        return ConfidenceInterval(
            value=mean,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            confidence_level=self.confidence_level,
            sample_size=sample_size,
            margin_of_error=margin_of_error,
            last_updated=datetime.now().isoformat(),
        )

    def compare_proportions(
        self,
        successes1: int,
        sample_size1: int,
        successes2: int,
        sample_size2: int,
    ) -> dict[str, Any]:
        """
        Compara duas proporções para verificar se são significativamente diferentes.

        Usa teste Z para diferença de proporções.

        Args:
            successes1: Sucessos na amostra 1
            sample_size1: Tamanho da amostra 1
            successes2: Sucessos na amostra 2
            sample_size2: Tamanho da amostra 2

        Returns:
            Dicionário com resultado da comparação

        Example:
            >>> calc = ConfidenceIntervalCalculator(confidence_level=0.95)
            >>> # Comparar triplet em dois períodos
            >>> result = calc.compare_proportions(
            ...     successes1=63, sample_size1=300,  # Período 1: 21%
            ...     successes2=45, sample_size2=200,  # Período 2: 22.5%
            ... )
            >>> print(f"Diferença significativa: {result['is_significant']}")
        """
        if sample_size1 <= 0 or sample_size2 <= 0:
            raise ValueError("sample_size deve ser maior que zero")

        # Proporções
        p1 = successes1 / sample_size1
        p2 = successes2 / sample_size2

        # Proporção pooled
        p_pooled = (successes1 + successes2) / (sample_size1 + sample_size2)

        # Erro padrão da diferença
        se_diff = math.sqrt(
            p_pooled * (1 - p_pooled) * (1 / sample_size1 + 1 / sample_size2)
        )

        # Estatística Z
        z_stat = (p1 - p2) / se_diff if se_diff > 0 else 0.0

        # Valor crítico
        z_critical = self.z_score

        # Verificar significância
        is_significant = abs(z_stat) > z_critical

        # Intervalo de confiança para a diferença
        diff_ci_lower = (p1 - p2) - z_critical * se_diff
        diff_ci_upper = (p1 - p2) + z_critical * se_diff

        return {
            "proportion1": p1,
            "proportion2": p2,
            "difference": p1 - p2,
            "z_statistic": z_stat,
            "is_significant": is_significant,
            "confidence_interval": [diff_ci_lower, diff_ci_upper],
            "confidence_level": self.confidence_level,
        }


# Instância global com configuração padrão
_default_calculator = ConfidenceIntervalCalculator(confidence_level=0.95)


def calculate_proportion_ci(
    successes: int,
    sample_size: int,
    confidence_level: float = 0.95,
) -> ConfidenceInterval:
    """
    Função auxiliar para calcular intervalo de confiança de proporção.

    Args:
        successes: Número de sucessos
        sample_size: Tamanho da amostra
        confidence_level: Nível de confiança (padrão: 0.95)

    Returns:
        ConfidenceInterval calculado
    """
    calc = ConfidenceIntervalCalculator(confidence_level=confidence_level)
    return calc.calculate_proportion_interval(successes, sample_size)


def calculate_mean_ci(
    values: list[float],
    confidence_level: float = 0.95,
) -> ConfidenceInterval:
    """
    Função auxiliar para calcular intervalo de confiança de média.

    Args:
        values: Lista de valores
        confidence_level: Nível de confiança (padrão: 0.95)

    Returns:
        ConfidenceInterval calculado
    """
    calc = ConfidenceIntervalCalculator(confidence_level=confidence_level)
    return calc.calculate_mean_interval(values)


def compare_proportions(
    successes1: int,
    sample_size1: int,
    successes2: int,
    sample_size2: int,
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    """
    Função auxiliar para comparar duas proporções.

    Args:
        successes1: Sucessos na amostra 1
        sample_size1: Tamanho da amostra 1
        successes2: Sucessos na amostra 2
        sample_size2: Tamanho da amostra 2
        confidence_level: Nível de confiança (padrão: 0.95)

    Returns:
        Dicionário com resultado da comparação
    """
    calc = ConfidenceIntervalCalculator(confidence_level=confidence_level)
    return calc.compare_proportions(successes1, sample_size1, successes2, sample_size2)
