"""Testes do Walk-Forward Validator — Fase 5.

Cobre:
- WalkForwardValidationConfig: validação de configuração temporal
- WalkForwardValidator: execução de validação walk-forward
- WalkForwardResult: resultados agregados
- Integração com SmartOrchestrator
- Detecção de vazamento temporal
- Detecção de degradação de performance
"""

from __future__ import annotations

import pytest
from typing import Any

from lotoia.validation.walk_forward_validator import (
    WalkForwardResult,
    WalkForwardSplitResult,
    WalkForwardValidationConfig,
    WalkForwardValidator,
)


# ============================================================
# CONFIGURAÇÃO
# ============================================================


class TestWalkForwardValidationConfig:
    """Testes de configuração de validação walk-forward."""

    def test_valid_config(self):
        """Configuração válida deve ser aceita."""
        config = WalkForwardValidationConfig(
            all_contests=list(range(3419, 3720)),
            training_contests=list(range(3419, 3619)),
            validation_contests=list(range(3619, 3719)),
        )
        assert len(config.training_contests) == 200
        assert len(config.validation_contests) == 100

    def test_config_with_test_contests(self):
        """Configuração com testes deve ser aceita."""
        config = WalkForwardValidationConfig(
            all_contests=list(range(3419, 3720)),
            training_contests=list(range(3419, 3619)),
            validation_contests=list(range(3619, 3700)),
            test_contests=list(range(3700, 3720)),
        )
        assert len(config.test_contests) == 20

    def test_overlapping_train_val_raises(self):
        """Sobreposição entre treino e validação deve levantar erro."""
        with pytest.raises(ValueError, match="must not overlap"):
            WalkForwardValidationConfig(
                all_contests=list(range(3419, 3720)),
                training_contests=list(range(3419, 3650)),
                validation_contests=list(range(3640, 3720)),  # Sobrepõe!
            )

    def test_train_after_val_raises(self):
        """Treino após validação deve levantar erro."""
        with pytest.raises(ValueError, match="must end before"):
            WalkForwardValidationConfig(
                all_contests=list(range(3419, 3720)),
                training_contests=list(range(3600, 3720)),  # Após validação!
                validation_contests=list(range(3419, 3600)),
            )

    def test_unsorted_contests_raises(self):
        """Concursos não ordenados devem levantar erro."""
        with pytest.raises(ValueError, match="must be sorted"):
            WalkForwardValidationConfig(
                all_contests=list(range(3419, 3720)),
                training_contests=[3419, 3420, 3418],  # Não ordenado!
                validation_contests=list(range(3619, 3719)),
            )


# ============================================================
# VALIDADOR
# ============================================================


class TestWalkForwardValidator:
    """Testes do validador walk-forward."""

    def test_validator_initialization(self):
        """Validador deve inicializar com configuração válida."""
        config = WalkForwardValidationConfig(
            all_contests=list(range(3419, 3720)),
            training_contests=list(range(3419, 3619)),
            validation_contests=list(range(3619, 3719)),
        )
        validator = WalkForwardValidator(config)
        assert validator.config == config

    def test_validator_with_empty_contests(self):
        """Validador deve levantar erro com configuração vazia."""
        with pytest.raises(ValueError):
            WalkForwardValidationConfig(
                all_contests=[],
                training_contests=[],
                validation_contests=[],
            )

    def test_validate_with_mock_generator(self):
        """Validação deve executar com gerador mock."""
        config = WalkForwardValidationConfig(
            all_contests=list(range(3419, 3520)),  # 101 concursos
            training_contests=list(range(3419, 3499)),  # 80 concursos
            validation_contests=list(range(3499, 3520)),  # 21 concursos
        )
        
        # Gerador mock que retorna jogos fictícios
        def mock_generator(history: list[int], target: int) -> tuple[list[dict], dict]:
            games = [
                {"numbers": list(range(1, 16)), "format": "15D"},
                {"numbers": list(range(2, 17)), "format": "15D"},
            ]
            metrics = {"diversity_score": 0.75}
            return games, metrics
        
        validator = WalkForwardValidator(config)
        result = validator.validate(
            mock_generator,
            games_per_contest=2,
            pool_size=10,
        )
        
        assert isinstance(result, WalkForwardResult)
        assert result.total_splits >= 1
        assert result.total_games_generated > 0

    def test_validate_detects_temporal_leakage(self):
        """Validador deve detectar vazamento temporal."""
        config = WalkForwardValidationConfig(
            all_contests=list(range(3419, 3520)),
            training_contests=list(range(3419, 3499)),
            validation_contests=list(range(3499, 3520)),
        )
        
        # Gerador que simula vazamento (validação muito melhor que treino)
        call_count = [0]
        def leaking_generator(history: list[int], target: int) -> tuple[list[dict], dict]:
            call_count[0] += 1
            games = [{"numbers": list(range(1, 16))}]
            
            # Simular vazamento: validação tem diversidade artificialmente alta
            if call_count[0] > 50:  # Validação começa após treino
                metrics = {"diversity_score": 0.95}  # Muito melhor que treino
            else:
                metrics = {"diversity_score": 0.60}  # Treino normal
            
            return games, metrics
        
        validator = WalkForwardValidator(config)
        result = validator.validate(leaking_generator, games_per_contest=1)
        
        # Deve detectar vazamento temporal
        assert result.temporal_leakage_detected is True
        assert result.is_valid() is False


# ============================================================
# RESULTADOS
# ============================================================


class TestWalkForwardResult:
    """Testes de resultados de validação."""

    def test_result_is_valid(self):
        """Resultado sem problemas deve ser válido."""
        config = WalkForwardValidationConfig(
            all_contests=list(range(3419, 3520)),
            training_contests=list(range(3419, 3499)),
            validation_contests=list(range(3499, 3520)),
        )
        
        result = WalkForwardResult(
            config=config,
            split_results=[],
            total_splits=0,
            total_games_generated=0,
            temporal_leakage_detected=False,
            performance_degradation=False,
        )
        
        assert result.is_valid() is True

    def test_result_with_leakage_invalid(self):
        """Resultado com vazamento deve ser inválido."""
        config = WalkForwardValidationConfig(
            all_contests=list(range(3419, 3520)),
            training_contests=list(range(3419, 3499)),
            validation_contests=list(range(3499, 3520)),
        )
        
        result = WalkForwardResult(
            config=config,
            split_results=[],
            total_splits=0,
            total_games_generated=0,
            temporal_leakage_detected=True,  # Vazamento detectado!
            performance_degradation=False,
        )
        
        assert result.is_valid() is False

    def test_result_as_dict(self):
        """Resultado deve converter para dicionário."""
        config = WalkForwardValidationConfig(
            all_contests=list(range(3419, 3520)),
            training_contests=list(range(3419, 3499)),
            validation_contests=list(range(3499, 3520)),
        )
        
        result = WalkForwardResult(
            config=config,
            split_results=[],
            total_splits=1,
            total_games_generated=100,
            temporal_leakage_detected=False,
            performance_degradation=False,
        )
        
        result_dict = result.as_dict()
        assert result_dict["total_splits"] == 1
        assert result_dict["total_games_generated"] == 100
        assert result_dict["temporal_leakage_detected"] is False


# ============================================================
# INTEGRAÇÃO COM SMART ORCHESTRATOR
# ============================================================


class TestSmartOrchestratorWalkForward:
    """Testes de integração com SmartOrchestrator."""

    def test_calibrate_preset_temporal(self):
        """calibrate_preset_temporal deve executar validação."""
        from lotoia.generation.smart_orchestrator import SmartOrchestrator
        
        orchestrator = SmartOrchestrator(format="15D", auto_calibrate=False)
        
        # Gerador mock
        def mock_generator(history: list[int], target: int) -> tuple[list[dict], dict]:
            games = [{"numbers": list(range(1, 16))}]
            metrics = {"diversity_score": 0.75}
            return games, metrics
        
        preset, adjustments, wf_result = orchestrator.calibrate_preset_temporal(
            base_preset="equilibrado",
            all_contests=list(range(3419, 3520)),
            training_contests=list(range(3419, 3499)),
            validation_contests=list(range(3499, 3520)),
            generator_fn=mock_generator,
            games_per_contest=1,
        )
        
        assert preset in ["conservador", "equilibrado", "agressivo"]
        assert isinstance(adjustments, dict)
        assert wf_result is not None
        assert isinstance(wf_result, WalkForwardResult)

    def test_validate_with_walk_forward(self):
        """validate_with_walk_forward deve executar validação."""
        from lotoia.generation.smart_orchestrator import SmartOrchestrator
        
        orchestrator = SmartOrchestrator(format="15D")
        
        def mock_generator(history: list[int], target: int) -> tuple[list[dict], dict]:
            games = [{"numbers": list(range(1, 16))}]
            metrics = {"diversity_score": 0.75}
            return games, metrics
        
        result = orchestrator.validate_with_walk_forward(
            all_contests=list(range(3419, 3520)),
            generator_fn=mock_generator,
            games_per_contest=1,
        )
        
        assert isinstance(result, WalkForwardResult)
        assert orchestrator.get_last_walk_forward_result() == result

    def test_orchestration_summary_includes_walk_forward(self):
        """Resumo da orquestração deve incluir info de walk-forward."""
        from lotoia.generation.smart_orchestrator import SmartOrchestrator
        
        orchestrator = SmartOrchestrator(format="15D")
        
        # Sem walk-forward executado
        summary = orchestrator.get_orchestration_summary()
        assert "walk_forward_validation" in summary
        assert summary["walk_forward_validation"]["executed"] is False
        
        # Executar walk-forward
        def mock_generator(history: list[int], target: int) -> tuple[list[dict], dict]:
            games = [{"numbers": list(range(1, 16))}]
            return games, {"diversity_score": 0.75}
        
        orchestrator.validate_with_walk_forward(
            all_contests=list(range(3419, 3520)),
            generator_fn=mock_generator,
        )
        
        # Com walk-forward executado
        summary = orchestrator.get_orchestration_summary()
        assert summary["walk_forward_validation"]["executed"] is True
        assert "total_splits" in summary["walk_forward_validation"]
