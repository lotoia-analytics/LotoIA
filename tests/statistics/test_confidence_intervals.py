"""Testes para o módulo de cálculo de intervalos de confiança."""

import pytest
from lotoia.statistics.confidence_interval_calculator import (
    ConfidenceInterval,
    ConfidenceIntervalCalculator,
    calculate_proportion_ci,
    calculate_mean_ci,
    compare_proportions,
)


class TestConfidenceInterval:
    """Testes para a classe ConfidenceInterval."""

    def test_contains_value_inside_interval(self):
        """Testa se contains retorna True para valor dentro do intervalo."""
        ci = ConfidenceInterval(
            value=0.21,
            lower_bound=0.164,
            upper_bound=0.256,
            confidence_level=0.95,
            sample_size=300,
            margin_of_error=0.046,
            last_updated="2026-06-25",
        )

        # Valor dentro do intervalo
        assert ci.contains(0.20) is True
        assert ci.contains(0.21) is True
        assert ci.contains(0.25) is True

        # Valor fora do intervalo
        assert ci.contains(0.10) is False
        assert ci.contains(0.30) is False

    def test_is_significantly_different(self):
        """Testa se is_significantly_different funciona corretamente."""
        ci = ConfidenceInterval(
            value=0.21,
            lower_bound=0.164,
            upper_bound=0.256,
            confidence_level=0.95,
            sample_size=300,
            margin_of_error=0.046,
            last_updated="2026-06-25",
        )

        # Valor dentro do intervalo não é significativamente diferente
        assert ci.is_significantly_different(0.20) is False

        # Valor fora do intervalo é significativamente diferente
        assert ci.is_significantly_different(0.10) is True
        assert ci.is_significantly_different(0.30) is True

    def test_to_dict(self):
        """Testa conversão para dicionário."""
        ci = ConfidenceInterval(
            value=0.21,
            lower_bound=0.164,
            upper_bound=0.256,
            confidence_level=0.95,
            sample_size=300,
            margin_of_error=0.046,
            last_updated="2026-06-25",
        )

        result = ci.to_dict()

        assert result["value"] == 0.21
        assert result["confidence_interval"] == [0.164, 0.256]
        assert result["confidence_level"] == 0.95
        assert result["sample_size"] == 300
        assert result["margin_of_error"] == 0.046
        assert result["last_updated"] == "2026-06-25"


class TestConfidenceIntervalCalculator:
    """Testes para a classe ConfidenceIntervalCalculator."""

    def test_init_default_confidence_level(self):
        """Testa inicialização com nível de confiança padrão."""
        calc = ConfidenceIntervalCalculator()

        assert calc.confidence_level == 0.95
        assert calc.z_score == 1.960

    def test_init_custom_confidence_level(self):
        """Testa inicialização com nível de confiança customizado."""
        calc = ConfidenceIntervalCalculator(confidence_level=0.99)

        assert calc.confidence_level == 0.99
        assert calc.z_score == 2.576

    def test_init_invalid_confidence_level(self):
        """Testa inicialização com nível de confiança inválido."""
        with pytest.raises(ValueError, match="não suportado"):
            ConfidenceIntervalCalculator(confidence_level=0.80)

    def test_calculate_proportion_interval_triplet(self):
        """Testa cálculo de IC para triplet 01-02-03 (63 em 300)."""
        calc = ConfidenceIntervalCalculator(confidence_level=0.95)

        ci = calc.calculate_proportion_interval(successes=63, sample_size=300)

        # Verificar valores
        assert abs(ci.value - 0.21) < 0.001
        assert ci.sample_size == 300
        assert ci.confidence_level == 0.95

        # Verificar intervalo (aproximadamente [0.164, 0.256])
        assert abs(ci.lower_bound - 0.164) < 0.01
        assert abs(ci.upper_bound - 0.256) < 0.01

        # Verificar margem de erro (aproximadamente 0.046)
        assert abs(ci.margin_of_error - 0.046) < 0.01

    def test_calculate_proportion_interval_suffix(self):
        """Testa cálculo de IC para suffix 23-24-25 (65 em 300)."""
        calc = ConfidenceIntervalCalculator(confidence_level=0.95)

        ci = calc.calculate_proportion_interval(successes=65, sample_size=300)

        # Verificar valores
        assert abs(ci.value - 0.2167) < 0.001
        assert ci.sample_size == 300

        # Verificar intervalo (aproximadamente [0.170, 0.263])
        assert abs(ci.lower_bound - 0.170) < 0.01
        assert abs(ci.upper_bound - 0.263) < 0.01

    def test_calculate_proportion_interval_small_sample(self):
        """Testa cálculo de IC com amostra pequena."""
        calc = ConfidenceIntervalCalculator(confidence_level=0.95)

        # 10 sucessos em 50 amostras
        ci = calc.calculate_proportion_interval(successes=10, sample_size=50)

        assert ci.value == 0.20
        assert ci.sample_size == 50
        # Margem de erro deve ser maior que com amostra grande
        assert ci.margin_of_error > 0.10

    def test_calculate_proportion_interval_zero_successes(self):
        """Testa cálculo de IC com zero sucessos."""
        calc = ConfidenceIntervalCalculator(confidence_level=0.95)

        ci = calc.calculate_proportion_interval(successes=0, sample_size=300)

        assert ci.value == 0.0
        assert ci.lower_bound == 0.0
        assert ci.upper_bound >= 0.0

    def test_calculate_proportion_interval_all_successes(self):
        """Testa cálculo de IC com todos os sucessos."""
        calc = ConfidenceIntervalCalculator(confidence_level=0.95)

        ci = calc.calculate_proportion_interval(successes=300, sample_size=300)

        assert ci.value == 1.0
        assert ci.upper_bound == 1.0
        assert ci.lower_bound <= 1.0

    def test_calculate_proportion_interval_invalid_sample_size(self):
        """Testa cálculo de IC com sample_size inválido."""
        calc = ConfidenceIntervalCalculator()

        with pytest.raises(ValueError, match="maior que zero"):
            calc.calculate_proportion_interval(successes=10, sample_size=0)

    def test_calculate_proportion_interval_invalid_successes(self):
        """Testa cálculo de IC com successes inválido."""
        calc = ConfidenceIntervalCalculator()

        with pytest.raises(ValueError, match="entre 0 e"):
            calc.calculate_proportion_interval(successes=-5, sample_size=300)

        with pytest.raises(ValueError, match="entre 0 e"):
            calc.calculate_proportion_interval(successes=400, sample_size=300)

    def test_calculate_mean_interval(self):
        """Testa cálculo de IC para média."""
        calc = ConfidenceIntervalCalculator(confidence_level=0.95)

        # Valores simulando overlap médio
        values = [10.0, 10.5, 9.8, 10.2, 9.9, 10.1, 10.3, 9.7, 10.4, 10.0]

        ci = calc.calculate_mean_interval(values)

        # Verificar valores
        assert abs(ci.value - 10.09) < 0.01
        assert ci.sample_size == 10
        assert ci.confidence_level == 0.95

        # Verificar intervalo
        assert ci.lower_bound < ci.value < ci.upper_bound

    def test_calculate_mean_interval_single_value(self):
        """Testa cálculo de IC com um único valor."""
        calc = ConfidenceIntervalCalculator()

        ci = calc.calculate_mean_interval([10.0])

        assert ci.value == 10.0
        assert ci.margin_of_error == 0.0
        assert ci.lower_bound == 10.0
        assert ci.upper_bound == 10.0

    def test_calculate_mean_interval_empty_values(self):
        """Testa cálculo de IC com lista vazia."""
        calc = ConfidenceIntervalCalculator()

        with pytest.raises(ValueError, match="não pode ser vazia"):
            calc.calculate_mean_interval([])

    def test_compare_proportions_significant_difference(self):
        """Testa comparação de proporções com diferença significativa."""
        calc = ConfidenceIntervalCalculator(confidence_level=0.95)

        # Comparar 63/300 (21%) com 90/300 (30%)
        result = calc.compare_proportions(
            successes1=63,
            sample_size1=300,
            successes2=90,
            sample_size2=300,
        )

        assert result["proportion1"] == 0.21
        assert result["proportion2"] == 0.30
        assert result["difference"] < 0  # p1 < p2
        assert result["is_significant"] is True

    def test_compare_proportions_no_significant_difference(self):
        """Testa comparação de proporções sem diferença significativa."""
        calc = ConfidenceIntervalCalculator(confidence_level=0.95)

        # Comparar 63/300 (21%) com 65/300 (21.67%)
        result = calc.compare_proportions(
            successes1=63,
            sample_size1=300,
            successes2=65,
            sample_size2=300,
        )

        assert result["proportion1"] == 0.21
        assert abs(result["proportion2"] - 0.2167) < 0.001  # 65/300 = 0.21666...
        # Diferença pequena, provavelmente não significativa
        assert abs(result["difference"]) < 0.01

    def test_compare_proportions_invalid_sample_size(self):
        """Testa comparação de proporções com sample_size inválido."""
        calc = ConfidenceIntervalCalculator()

        with pytest.raises(ValueError, match="maior que zero"):
            calc.compare_proportions(
                successes1=10,
                sample_size1=0,
                successes2=10,
                sample_size2=100,
            )


class TestHelperFunctions:
    """Testes para funções auxiliares."""

    def test_calculate_proportion_ci(self):
        """Testa função auxiliar calculate_proportion_ci."""
        ci = calculate_proportion_ci(successes=63, sample_size=300)

        assert isinstance(ci, ConfidenceInterval)
        assert abs(ci.value - 0.21) < 0.001

    def test_calculate_proportion_ci_custom_confidence(self):
        """Testa função auxiliar com nível de confiança customizado."""
        ci = calculate_proportion_ci(
            successes=63, sample_size=300, confidence_level=0.99
        )

        assert ci.confidence_level == 0.99
        # IC 99% deve ser mais largo que IC 95%
        ci_95 = calculate_proportion_ci(successes=63, sample_size=300)
        assert ci.margin_of_error > ci_95.margin_of_error

    def test_calculate_mean_ci(self):
        """Testa função auxiliar calculate_mean_ci."""
        values = [10.0, 10.5, 9.8, 10.2, 9.9]

        ci = calculate_mean_ci(values)

        assert isinstance(ci, ConfidenceInterval)
        assert ci.sample_size == 5

    def test_compare_proportions(self):
        """Testa função auxiliar compare_proportions."""
        result = compare_proportions(
            successes1=63,
            sample_size1=300,
            successes2=90,
            sample_size2=300,
        )

        assert isinstance(result, dict)
        assert "is_significant" in result
        assert "confidence_interval" in result


class TestIntegrationWithConfig:
    """Testes de integração com a configuração CORE_003."""

    def test_config_has_confidence_intervals(self):
        """Testa se a configuração tem intervalos de confiança."""
        from lotoia.config.core_003_config import CORE_003_CONFIG

        assert "confidence_intervals" in CORE_003_CONFIG
        assert "triplet_010203" in CORE_003_CONFIG["confidence_intervals"]
        assert "suffix_232425" in CORE_003_CONFIG["confidence_intervals"]

    def test_get_confidence_intervals(self):
        """Testa função get_confidence_intervals."""
        from lotoia.config.core_003_config import get_confidence_intervals

        ci_dict = get_confidence_intervals()

        assert isinstance(ci_dict, dict)
        assert "triplet_010203" in ci_dict
        assert "value" in ci_dict["triplet_010203"]
        assert "confidence_interval" in ci_dict["triplet_010203"]

    def test_get_confidence_interval_specific(self):
        """Testa função get_confidence_interval para métrica específica."""
        from lotoia.config.core_003_config import get_confidence_interval

        ci = get_confidence_interval("triplet_010203")

        assert ci is not None
        assert ci["value"] == 0.21
        assert ci["sample_size"] == 300

    def test_get_confidence_interval_nonexistent(self):
        """Testa função get_confidence_interval para métrica inexistente."""
        from lotoia.config.core_003_config import get_confidence_interval

        ci = get_confidence_interval("metrica_inexistente")

        assert ci is None

    def test_triplet_ci_matches_calculation(self):
        """Testa se o IC do triplet na config corresponde ao cálculo."""
        from lotoia.config.core_003_config import get_confidence_interval

        ci_config = get_confidence_interval("triplet_010203")

        # Calcular IC manualmente
        calc = ConfidenceIntervalCalculator(confidence_level=0.95)
        ci_calc = calc.calculate_proportion_interval(successes=63, sample_size=300)

        # Verificar se correspondem
        assert abs(ci_config["value"] - ci_calc.value) < 0.001
        # confidence_interval é uma lista [lower, upper]
        assert abs(ci_config["confidence_interval"][0] - ci_calc.lower_bound) < 0.01
        assert abs(ci_config["confidence_interval"][1] - ci_calc.upper_bound) < 0.01
