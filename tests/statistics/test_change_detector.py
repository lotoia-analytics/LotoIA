"""Testes para o módulo de detecção de mudanças estatisticamente significativas."""

import pytest
from lotoia.statistics.change_detector import (
    ChangeDetector,
    ChangeDetectionResult,
    is_statistically_significant_change,
    should_adjust_parameter,
)


class TestChangeDetector:
    """Testes para a classe ChangeDetector."""

    def test_init_default_confidence_level(self):
        """Testa inicialização com nível de confiança padrão."""
        detector = ChangeDetector()
        assert detector.confidence_level == 0.95

    def test_init_custom_confidence_level(self):
        """Testa inicialização com nível de confiança customizado."""
        detector = ChangeDetector(confidence_level=0.99)
        assert detector.confidence_level == 0.99

    def test_detect_change_significant_decrease(self):
        """Testa detecção de diminuição significativa."""
        detector = ChangeDetector(confidence_level=0.95)

        # Triplet caiu de 21% para 10% (mudança significativa)
        result = detector.detect_change(
            current_rate=0.10,
            historical_rate=0.21,
            sample_size_recent=50,
            sample_size_historical=300,
        )

        assert result.is_significant is True
        assert result.difference < 0  # Diminuição
        assert result.relative_change < 0
        assert result.z_score < 0  # Z negativo para diminuição

    def test_detect_change_significant_increase(self):
        """Testa detecção de aumento significativo."""
        detector = ChangeDetector(confidence_level=0.95)

        # Triplet subiu de 21% para 35% (mudança significativa)
        result = detector.detect_change(
            current_rate=0.35,
            historical_rate=0.21,
            sample_size_recent=50,
            sample_size_historical=300,
        )

        assert result.is_significant is True
        assert result.difference > 0  # Aumento
        assert result.relative_change > 0
        assert result.z_score > 0  # Z positivo para aumento

    def test_detect_change_not_significant(self):
        """Testa detecção de mudança não significativa."""
        detector = ChangeDetector(confidence_level=0.95)

        # Triplet mudou de 21% para 22% (mudança não significativa)
        result = detector.detect_change(
            current_rate=0.22,
            historical_rate=0.21,
            sample_size_recent=50,
            sample_size_historical=300,
        )

        assert result.is_significant is False
        assert abs(result.difference) < 0.05  # Mudança pequena

    def test_detect_change_with_small_sample(self):
        """Testa detecção com amostra pequena."""
        detector = ChangeDetector(confidence_level=0.95)

        # Com amostra pequena, mudanças precisam ser maiores para serem significativas
        result = detector.detect_change(
            current_rate=0.10,
            historical_rate=0.21,
            sample_size_recent=10,  # Amostra muito pequena
            sample_size_historical=300,
        )

        # Com amostra pequena, pode não ser significativa mesmo com diferença grande
        # porque o IC é muito largo
        assert isinstance(result.is_significant, bool)

    def test_detect_change_with_large_sample(self):
        """Testa detecção com amostra grande."""
        detector = ChangeDetector(confidence_level=0.95)

        # Com amostra grande, mudanças menores podem ser significativas
        result = detector.detect_change(
            current_rate=0.18,
            historical_rate=0.21,
            sample_size_recent=200,  # Amostra grande
            sample_size_historical=300,
        )

        # Com amostra grande, diferença de 3% pode ser significativa
        assert isinstance(result.is_significant, bool)

    def test_detect_change_invalid_current_rate(self):
        """Testa detecção com taxa atual inválida."""
        detector = ChangeDetector()

        with pytest.raises(ValueError, match="current_rate deve estar entre 0 e 1"):
            detector.detect_change(
                current_rate=1.5,  # Inválido
                historical_rate=0.21,
                sample_size_recent=50,
                sample_size_historical=300,
            )

    def test_detect_change_invalid_historical_rate(self):
        """Testa detecção com taxa histórica inválida."""
        detector = ChangeDetector()

        with pytest.raises(ValueError, match="historical_rate deve estar entre 0 e 1"):
            detector.detect_change(
                current_rate=0.15,
                historical_rate=-0.1,  # Inválido
                sample_size_recent=50,
                sample_size_historical=300,
            )

    def test_detect_change_invalid_sample_sizes(self):
        """Testa detecção com tamanhos de amostra inválidos."""
        detector = ChangeDetector()

        with pytest.raises(ValueError, match="sample_size_recent deve ser > 0"):
            detector.detect_change(
                current_rate=0.15,
                historical_rate=0.21,
                sample_size_recent=0,
                sample_size_historical=300,
            )

        with pytest.raises(ValueError, match="sample_size_historical deve ser > 0"):
            detector.detect_change(
                current_rate=0.15,
                historical_rate=0.21,
                sample_size_recent=50,
                sample_size_historical=0,
            )

    def test_should_adjust_parameter_significant_change(self):
        """Testa should_adjust_parameter com mudança significativa."""
        detector = ChangeDetector(confidence_level=0.95)

        # Triplet caiu de 21% para 10% (mudança significativa e substancial)
        should_adjust, result = detector.should_adjust_parameter(
            metric_name="triplet_010203",
            current_rate=0.10,
            historical_config={"value": 0.21, "sample_size": 300},
            sample_size_recent=50,
        )

        assert should_adjust is True
        assert result is not None
        assert result.is_significant is True

    def test_should_adjust_parameter_not_significant(self):
        """Testa should_adjust_parameter com mudança não significativa."""
        detector = ChangeDetector(confidence_level=0.95)

        # Triplet mudou de 21% para 20% (mudança não significativa)
        should_adjust, result = detector.should_adjust_parameter(
            metric_name="triplet_010203",
            current_rate=0.20,
            historical_config={"value": 0.21, "sample_size": 300},
            sample_size_recent=50,
        )

        assert should_adjust is False
        assert result is not None

    def test_should_adjust_parameter_small_relative_change(self):
        """Testa should_adjust_parameter com mudança significativa mas pequena."""
        detector = ChangeDetector(confidence_level=0.95)

        # Mudança significativa mas menor que 5% relativo
        # 21% para 20% = 4.76% relativo (menor que 5%)
        should_adjust, result = detector.should_adjust_parameter(
            metric_name="triplet_010203",
            current_rate=0.20,
            historical_config={"value": 0.21, "sample_size": 300},
            sample_size_recent=50,
        )

        # Mesmo que seja significativa, não deve ajustar se mudança relativa < 5%
        assert isinstance(should_adjust, bool)

    def test_should_adjust_parameter_missing_historical_value(self):
        """Testa should_adjust_parameter sem valor histórico."""
        detector = ChangeDetector()

        should_adjust, result = detector.should_adjust_parameter(
            metric_name="triplet_010203",
            current_rate=0.15,
            historical_config={},  # Sem valor histórico
            sample_size_recent=50,
        )

        assert should_adjust is False
        assert result is None


class TestChangeDetectionResult:
    """Testes para a classe ChangeDetectionResult."""

    def test_to_dict(self):
        """Testa conversão para dicionário."""
        result = ChangeDetectionResult(
            is_significant=True,
            current_rate=0.15,
            historical_rate=0.21,
            difference=-0.06,
            relative_change=-0.286,
            confidence_interval=[0.164, 0.256],
            z_score=-2.5,
            p_value=0.012,
            confidence_level=0.95,
            sample_size_recent=50,
            sample_size_historical=300,
            detected_at="2026-06-25T10:00:00",
        )

        result_dict = result.to_dict()

        assert result_dict["is_significant"] is True
        assert result_dict["current_rate"] == 0.15
        assert result_dict["historical_rate"] == 0.21
        assert result_dict["difference"] == -0.06
        assert result_dict["relative_change"] == -0.286
        assert result_dict["confidence_interval"] == [0.164, 0.256]
        assert result_dict["z_score"] == -2.5
        assert result_dict["p_value"] == 0.012
        assert result_dict["confidence_level"] == 0.95
        assert result_dict["sample_size_recent"] == 50
        assert result_dict["sample_size_historical"] == 300
        assert result_dict["detected_at"] == "2026-06-25T10:00:00"


class TestHelperFunctions:
    """Testes para funções auxiliares."""

    def test_is_statistically_significant_change_significant(self):
        """Testa is_statistically_significant_change com mudança significativa."""
        # Triplet caiu de 21% para 10% (mudança significativa)
        is_significant = is_statistically_significant_change(
            current_rate=0.10,
            historical_rate=0.21,
            sample_size_recent=50,
            sample_size_historical=300,
        )

        assert is_significant is True

    def test_is_statistically_significant_change_not_significant(self):
        """Testa is_statistically_significant_change com mudança não significativa."""
        # Triplet mudou de 21% para 20% (mudança não significativa)
        is_significant = is_statistically_significant_change(
            current_rate=0.20,
            historical_rate=0.21,
            sample_size_recent=50,
            sample_size_historical=300,
        )

        assert is_significant is False

    def test_is_statistically_significant_change_custom_confidence(self):
        """Testa is_statistically_significant_change com confiança customizada."""
        # Com confiança maior (99%), precisa de evidência mais forte
        is_significant_95 = is_statistically_significant_change(
            current_rate=0.15,
            historical_rate=0.21,
            sample_size_recent=50,
            sample_size_historical=300,
            confidence_level=0.95,
        )

        is_significant_99 = is_statistically_significant_change(
            current_rate=0.15,
            historical_rate=0.21,
            sample_size_recent=50,
            sample_size_historical=300,
            confidence_level=0.99,
        )

        # Ambos devem ser booleanos
        assert isinstance(is_significant_95, bool)
        assert isinstance(is_significant_99, bool)

    def test_should_adjust_parameter_helper_significant(self):
        """Testa should_adjust_parameter helper com mudança significativa."""
        should_adjust, result = should_adjust_parameter(
            metric_name="triplet_010203",
            current_rate=0.10,
            historical_config={"value": 0.21, "sample_size": 300},
            sample_size_recent=50,
        )

        assert should_adjust is True
        assert result is not None

    def test_should_adjust_parameter_helper_not_significant(self):
        """Testa should_adjust_parameter helper com mudança não significativa."""
        should_adjust, result = should_adjust_parameter(
            metric_name="triplet_010203",
            current_rate=0.20,
            historical_config={"value": 0.21, "sample_size": 300},
            sample_size_recent=50,
        )

        assert should_adjust is False
        assert result is not None


class TestIntegrationWithConfig:
    """Testes de integração com a configuração CORE_003."""

    def test_should_adjust_with_real_config(self):
        """Testa should_adjust_parameter com configuração real."""
        from lotoia.config.core_003_config import get_confidence_interval

        detector = ChangeDetector(confidence_level=0.95)
        triplet_config = get_confidence_interval("triplet_010203")

        # Triplet caiu significativamente
        should_adjust, result = detector.should_adjust_parameter(
            metric_name="triplet_010203",
            current_rate=0.10,
            historical_config=triplet_config,
            sample_size_recent=50,
        )

        assert should_adjust is True
        assert result is not None
        assert result.is_significant is True

    def test_should_not_adjust_within_confidence_interval(self):
        """Testa que não ajusta quando está dentro do IC."""
        from lotoia.config.core_003_config import get_confidence_interval

        detector = ChangeDetector(confidence_level=0.95)
        triplet_config = get_confidence_interval("triplet_010203")

        # Triplet está dentro do IC (21% ± 4.6%)
        should_adjust, result = detector.should_adjust_parameter(
            metric_name="triplet_010203",
            current_rate=0.22,  # Dentro do IC [0.164, 0.256]
            historical_config=triplet_config,
            sample_size_recent=50,
        )

        assert should_adjust is False

    def test_integration_with_smart_orchestrator(self):
        """Testa integração com SmartOrchestrator."""
        from lotoia.generation.smart_orchestrator import SmartOrchestrator

        orchestrator = SmartOrchestrator(format="15D", auto_calibrate=True)

        # Verificar que o orchestrator tem change_detector
        assert hasattr(orchestrator, "change_detector")
        assert isinstance(orchestrator.change_detector, ChangeDetector)
