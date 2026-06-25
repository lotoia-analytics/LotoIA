"""Testes do Smart Orchestrator CORE_003."""

import pytest
from lotoia.generation.smart_orchestrator import SmartOrchestrator, get_orchestrator
from lotoia.generation.core_003_pipeline import generate_core_003_games


class TestSmartOrchestrator:
    """Testes do Smart Orchestrator."""

    def test_orchestrator_creation(self):
        """Testa criação do orquestrador."""
        orchestrator = SmartOrchestrator(format="15D", auto_calibrate=False)
        assert orchestrator.format == "15D"
        assert orchestrator.auto_calibrate is False

    def test_orchestrator_with_auto_calibrate(self):
        """Testa orquestrador com auto-calibração."""
        orchestrator = SmartOrchestrator(format="15D", auto_calibrate=True)
        assert orchestrator.auto_calibrate is True

    def test_calibrate_preset_without_auto_calibrate(self):
        """Testa calibração sem auto-calibração."""
        orchestrator = SmartOrchestrator(format="15D", auto_calibrate=False)
        preset, adjustments = orchestrator.calibrate_preset("equilibrado")

        # Sem auto-calibração, deve retornar preset base sem ajustes
        assert preset == "equilibrado"
        assert adjustments == {}

    def test_calibrate_preset_with_auto_calibrate_no_data(self):
        """Testa calibração com auto-calibração mas sem dados."""
        orchestrator = SmartOrchestrator(format="15D", auto_calibrate=True)
        preset, adjustments = orchestrator.calibrate_preset("equilibrado")

        # Sem dados de feedback, deve retornar preset base
        assert preset == "equilibrado"

    def test_apply_adjustments_to_config(self):
        """Testa aplicação de ajustes à configuração."""
        orchestrator = SmartOrchestrator(format="15D", auto_calibrate=True)

        adjustments = {
            "diversity_floor": "+0.03",
            "overlap_penalty": "-0.05",
            "triplet_freq": "0.23",
        }

        config = orchestrator.apply_adjustments_to_config(adjustments)

        # Verificar se ajustes foram aplicados
        assert (
            config["calibration_presets"]["equilibrado"]["diversity_floor"]
            == 0.78 + 0.03
        )
        assert (
            config["calibration_presets"]["equilibrado"]["overlap_penalty"]
            == 1.15 - 0.05
        )
        assert config["structural_policy"]["triplet_010203"]["freq"] == 0.23

    def test_apply_empty_adjustments(self):
        """Testa aplicação de ajustes vazios."""
        from lotoia.config.core_003_config import CORE_003_CONFIG

        orchestrator = SmartOrchestrator(format="15D", auto_calibrate=True)
        config = orchestrator.apply_adjustments_to_config({})

        # Deve retornar configuração padrão
        assert config == CORE_003_CONFIG.copy()

    def test_get_orchestration_summary(self):
        """Testa resumo da orquestração."""
        orchestrator = SmartOrchestrator(format="15D", auto_calibrate=True)
        summary = orchestrator.get_orchestration_summary()

        assert "format" in summary
        assert "auto_calibrate" in summary
        assert "feedback_trend" in summary
        assert summary["format"] == "15D"
        assert summary["auto_calibrate"] is True

    def test_get_orchestrator_singleton(self):
        """Testa que get_orchestrator retorna instância única."""
        orch1 = get_orchestrator(format="15D", auto_calibrate=False)
        orch2 = get_orchestrator(format="15D", auto_calibrate=False)

        # Deve ser a mesma instância
        assert orch1 is orch2

    def test_get_orchestrator_different_params(self):
        """Testa que get_orchestrator cria nova instância com parâmetros diferentes."""
        orch1 = get_orchestrator(format="15D", auto_calibrate=False)
        orch2 = get_orchestrator(format="17D", auto_calibrate=False)

        # Deve ser instâncias diferentes
        assert orch1 is not orch2
        assert orch1.format == "15D"
        assert orch2.format == "17D"


class TestAutoCalibrateIntegration:
    """Testes de integração com auto_calibrate."""

    def test_generate_without_auto_calibrate(self):
        """Testa geração sem auto-calibração."""
        games = generate_core_003_games(
            format="15D",
            count=10,
            auto_calibrate=False,
        )

        assert len(games) == 10
        assert all(len(g["numbers"]) == 15 for g in games)

    def test_generate_with_auto_calibrate(self):
        """Testa geração com auto-calibração."""
        games = generate_core_003_games(
            format="15D",
            count=10,
            auto_calibrate=True,
        )

        assert len(games) == 10
        assert all(len(g["numbers"]) == 15 for g in games)

    def test_generate_17d_with_auto_calibrate(self):
        """Testa geração 17D com auto-calibração."""
        games = generate_core_003_games(
            format="17D",
            count=10,
            auto_calibrate=True,
        )

        assert len(games) == 10
        assert all(len(g["numbers"]) == 17 for g in games)

    def test_auto_calibrate_with_different_presets(self):
        """Testa auto-calibração com diferentes presets."""
        for preset in ["conservador", "equilibrado", "agressivo"]:
            games = generate_core_003_games(
                format="15D",
                count=10,
                calibration=preset,
                auto_calibrate=True,
            )

            assert len(games) == 10

    def test_auto_calibrate_metrics(self):
        """Testa que auto-calibração produz métricas válidas."""
        games = generate_core_003_games(
            format="15D",
            count=20,
            auto_calibrate=True,
        )

        from lotoia.statistics.structural_metrics_validator import (
            compute_structural_metrics,
        )

        metrics = compute_structural_metrics(games)

        # Métricas devem estar presentes
        assert "triplet_010203_pct" in metrics
        assert "avg_overlap" in metrics
        assert "games_count" in metrics


class TestVersioningIntegration:
    """Testes de integração com versionamento."""

    def test_register_version_with_adjustments(self, tmp_path):
        """Testa registro de versão com ajustes."""
        from lotoia.generation.smart_orchestrator import SmartOrchestrator
        from lotoia.generation.model_versioning import ModelVersioning

        # Criar orquestrador com versionamento temporário
        orchestrator = SmartOrchestrator(format="15D", auto_calibrate=True)
        orchestrator.versioning = ModelVersioning(str(tmp_path / "test_versions.json"))

        adjustments = {
            "diversity_floor": "+0.03",
            "triplet_freq": "0.23",
        }

        version = orchestrator.register_generation_version(
            preset_used="equilibrado",
            adjustments=adjustments,
        )

        # Deve registrar nova versão
        assert version is not None
        assert version.startswith("v")

    def test_no_version_without_adjustments(self, tmp_path):
        """Testa que não registra versão sem ajustes."""
        from lotoia.generation.smart_orchestrator import SmartOrchestrator
        from lotoia.generation.model_versioning import ModelVersioning

        orchestrator = SmartOrchestrator(format="15D", auto_calibrate=True)
        orchestrator.versioning = ModelVersioning(str(tmp_path / "test_versions.json"))

        version = orchestrator.register_generation_version(
            preset_used="equilibrado",
            adjustments={},
        )

        # Não deve registrar versão sem ajustes
        assert version is None


class TestEndToEnd:
    """Testes end-to-end do sistema integrado."""

    def test_full_pipeline_with_auto_calibrate(self):
        """Testa pipeline completo com auto-calibração."""
        # Gerar jogos com auto-calibração
        games = generate_core_003_games(
            format="15D",
            count=30,
            auto_calibrate=True,
        )

        # Verificar jogos
        assert len(games) == 30
        assert all(len(g["numbers"]) == 15 for g in games)

        # Verificar métricas
        from lotoia.statistics.structural_metrics_validator import (
            compute_structural_metrics,
        )

        metrics = compute_structural_metrics(games)

        # Triplet deve estar presente
        assert "triplet_010203_pct" in metrics

        # Overlap deve estar dentro de limites razoáveis
        assert 7.0 <= metrics["avg_overlap"] <= 13.0

    def test_multiple_formats_with_auto_calibrate(self):
        """Testa múltiplos formatos com auto-calibração."""
        formats = ["15D", "17D", "20D"]

        for fmt in formats:
            dezenas = int(fmt.replace("D", ""))
            games = generate_core_003_games(
                format=fmt,
                count=10,
                auto_calibrate=True,
            )

            assert len(games) == 10
            assert all(len(g["numbers"]) == dezenas for g in games)
