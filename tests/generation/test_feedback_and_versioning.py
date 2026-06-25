"""Testes do Sistema de Feedback Automático e Versionamento CORE_003."""

import pytest
from lotoia.generation.post_contest_feedback import (
    PostContestFeedback,
    post_contest_feedback,
    get_feedback_suggestions,
    get_performance_trend,
)
from lotoia.generation.model_versioning import (
    ModelVersioning,
    register_model_version,
    get_model_version,
    get_latest_model_version,
    compare_model_versions,
    list_model_versions,
)


class TestPostContestFeedback:
    """Testes do sistema de feedback pós-concurso."""

    def test_analyze_contest_result_basic(self):
        """Testa análise básica de resultado de concurso."""
        feedback = PostContestFeedback()

        # Simular concurso e jogos gerados
        contest_numbers = [1, 2, 3, 5, 8, 10, 12, 15, 18, 20, 22, 23, 24, 25, 17]
        generated_games = [
            {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]},
            {"numbers": [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 23, 24, 25, 17]},
            {"numbers": [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 24, 25, 18]},
        ]

        result = feedback.analyze_contest_result(
            contest_number=100,
            contest_numbers=contest_numbers,
            generated_games=generated_games,
            format="15D",
        )

        assert "metrics" in result
        assert "suggestions" in result
        assert result["contest_number"] == 100
        assert result["games_analyzed"] == 3

    def test_compute_post_contest_metrics(self):
        """Testa cálculo de métricas pós-concurso."""
        feedback = PostContestFeedback()

        contest_numbers = [1, 2, 3, 5, 8, 10, 12, 15, 18, 20, 22, 23, 24, 25, 17]
        generated_games = [
            {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]},
            {"numbers": [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 23, 24, 25, 17]},
        ]

        metrics = feedback._compute_post_contest_metrics(
            contest_numbers, generated_games, "15D"
        )

        assert "hit_rate_11_13" in metrics
        assert "hit_rate_14_15" in metrics
        assert "triplet_hit_rate" in metrics
        assert "suffix_hit_rate" in metrics
        assert "avg_hits" in metrics
        assert "max_hits" in metrics
        assert 0 <= metrics["hit_rate_11_13"] <= 1
        assert 0 <= metrics["hit_rate_14_15"] <= 1

    def test_generate_suggestions_low_hit_rate(self):
        """Testa geração de sugestões com baixa taxa de acertos."""
        feedback = PostContestFeedback()

        # Métricas com baixa taxa de acertos
        metrics = {
            "hit_rate_11_13": 0.05,  # 5% < 10%
            "hit_rate_14_15": 0.01,
            "triplet_hit_rate": 0.10,  # 10% < 15%
            "suffix_hit_rate": 0.10,  # 10% < 15%
            "avg_hits": 8.5,
            "max_hits": 11,
        }

        suggestions = feedback._generate_suggestions(metrics, "15D")

        assert len(suggestions) > 0
        adjustments = [s["adjustment"] for s in suggestions]
        assert "increase_diversity" in adjustments
        assert "increase_triplet_cap" in adjustments
        assert "increase_suffix_cap" in adjustments

    def test_generate_suggestions_good_performance(self):
        """Testa geração de sugestões com bom desempenho."""
        feedback = PostContestFeedback()

        # Métricas com bom desempenho
        metrics = {
            "hit_rate_11_13": 0.15,  # 15% > 10%
            "hit_rate_14_15": 0.08,  # 8% > 5%
            "triplet_hit_rate": 0.20,  # 20% > 15%
            "suffix_hit_rate": 0.20,  # 20% > 15%
            "avg_hits": 11.5,
            "max_hits": 14,
        }

        suggestions = feedback._generate_suggestions(metrics, "15D")

        # Deve sugerir manter configuração atual
        adjustments = [s["adjustment"] for s in suggestions]
        assert "maintain_current" in adjustments

    def test_performance_trend(self):
        """Testa cálculo de tendência de desempenho."""
        feedback = PostContestFeedback()

        # Adicionar múltiplas análises
        for i in range(5):
            feedback.analyze_contest_result(
                contest_number=100 + i,
                contest_numbers=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
                generated_games=[
                    {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]}
                ],
                format="15D",
            )

        trend = feedback.get_performance_trend(last_n=5)

        assert "trend" in trend
        assert "analyses" in trend
        assert trend["analyses"] == 5
        assert trend["trend"] in [
            "improving",
            "declining",
            "stable",
            "insufficient_data",
        ]

    def test_post_contest_feedback_function(self):
        """Testa função simplificada de feedback."""
        result = post_contest_feedback(
            contest_number=200,
            contest_numbers=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
            generated_games=[
                {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]}
            ],
            format="15D",
        )

        assert "metrics" in result
        assert "suggestions" in result
        assert result["contest_number"] == 200

    def test_get_feedback_suggestions(self):
        """Testa obtenção de sugestões pendentes."""
        # Gerar alguma análise primeiro
        post_contest_feedback(
            contest_number=300,
            contest_numbers=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
            generated_games=[
                {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]}
            ],
            format="15D",
        )

        suggestions = get_feedback_suggestions()

        assert "pending_suggestions" in suggestions
        assert "suggestions" in suggestions
        assert isinstance(suggestions["suggestions"], list)


class TestModelVersioning:
    """Testes do sistema de versionamento de modelos."""

    def test_register_version(self, tmp_path):
        """Testa registro de nova versão."""
        versions_file = tmp_path / "test_versions.json"
        versioning = ModelVersioning(str(versions_file))

        version_info = versioning.register_version(
            version="v3.0.0",
            changes=[
                "Consolidou M-STAT-002 + M-CORE-003",
                "Simplificou calibration plan",
            ],
            backtest_results={"hit_rate_11_13": 0.15, "avg_overlap": 9.5},
        )

        assert version_info["version"] == "v3.0.0"
        assert len(version_info["changes"]) == 2
        assert "backtest_results" in version_info
        assert versions_file.exists()

    def test_get_version(self, tmp_path):
        """Testa obtenção de versão específica."""
        versions_file = tmp_path / "test_versions.json"
        versioning = ModelVersioning(str(versions_file))

        versioning.register_version(
            version="v3.1.0",
            changes=["Ajustou triplet cap para 22%"],
        )

        version = versioning.get_version("v3.1.0")

        assert version is not None
        assert version["version"] == "v3.1.0"
        assert len(version["changes"]) == 1

    def test_get_latest_version(self, tmp_path):
        """Testa obtenção da versão mais recente."""
        versions_file = tmp_path / "test_versions.json"
        versioning = ModelVersioning(str(versions_file))

        versioning.register_version(
            version="v3.0.0",
            changes=["Initial"],
        )
        versioning.register_version(
            version="v3.1.0",
            changes=["Update"],
        )

        latest = versioning.get_latest_version()

        assert latest is not None
        assert latest["version"] == "v3.1.0"

    def test_compare_versions(self, tmp_path):
        """Testa comparação de versões."""
        versions_file = tmp_path / "test_versions.json"
        versioning = ModelVersioning(str(versions_file))

        versioning.register_version(
            version="v3.0.0",
            changes=["Initial"],
            backtest_results={"hit_rate_11_13": 0.15, "avg_overlap": 9.5},
        )
        versioning.register_version(
            version="v3.1.0",
            changes=["Update"],
            backtest_results={"hit_rate_11_13": 0.16, "avg_overlap": 9.3},
        )

        comparison = versioning.compare_versions("v3.0.0", "v3.1.0")

        assert "backtest_comparison" in comparison
        assert "hit_rate_11_13" in comparison["backtest_comparison"]
        assert (
            comparison["backtest_comparison"]["hit_rate_11_13"]["improvement"] is True
        )

    def test_list_versions(self, tmp_path):
        """Testa listagem de versões."""
        versions_file = tmp_path / "test_versions.json"
        versioning = ModelVersioning(str(versions_file))

        versioning.register_version(version="v3.0.0", changes=["v1"])
        versioning.register_version(version="v3.1.0", changes=["v2"])
        versioning.register_version(version="v3.2.0", changes=["v3"])

        versions = versioning.list_versions()

        assert len(versions) == 3
        # Deve estar ordenado por data (mais recente primeiro)
        assert versions[0]["version"] == "v3.2.0"

    def test_update_backtest_results(self, tmp_path):
        """Testa atualização de resultados de backtest."""
        versions_file = tmp_path / "test_versions.json"
        versioning = ModelVersioning(str(versions_file))

        versioning.register_version(
            version="v3.0.0",
            changes=["Initial"],
            backtest_results={"hit_rate_11_13": 0.15},
        )

        success = versioning.update_backtest_results(
            "v3.0.0",
            {"hit_rate_11_13": 0.18, "avg_overlap": 9.2},
        )

        assert success is True

        version = versioning.get_version("v3.0.0")
        assert version["backtest_results"]["hit_rate_11_13"] == 0.18

    def test_register_model_version_function(self, tmp_path):
        """Testa função simplificada de registro."""
        import lotoia.generation.model_versioning as mv

        # Substituir instância global temporariamente
        original = mv._versioning_system
        mv._versioning_system = ModelVersioning(str(tmp_path / "test.json"))

        try:
            result = register_model_version(
                version="v3.3.0",
                changes=["Test version"],
            )

            assert result["version"] == "v3.3.0"
        finally:
            mv._versioning_system = original

    def test_persistence(self, tmp_path):
        """Testa persistência de versões em arquivo."""
        versions_file = tmp_path / "test_versions.json"

        # Criar e registrar versão
        versioning1 = ModelVersioning(str(versions_file))
        versioning1.register_version(
            version="v3.0.0",
            changes=["Initial"],
        )

        # Carregar em nova instância
        versioning2 = ModelVersioning(str(versions_file))
        version = versioning2.get_version("v3.0.0")

        assert version is not None
        assert version["version"] == "v3.0.0"


class TestIntegration:
    """Testes de integração entre feedback e versionamento."""

    def test_feedback_with_versioning(self, tmp_path):
        """Testa integração de feedback com versionamento."""
        # Registrar versão
        versioning = ModelVersioning(str(tmp_path / "versions.json"))
        versioning.register_version(
            version="v3.0.0",
            changes=["Initial CORE_003"],
        )

        # Gerar feedback
        feedback = PostContestFeedback()
        result = feedback.analyze_contest_result(
            contest_number=100,
            contest_numbers=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
            generated_games=[
                {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]}
            ],
            format="15D",
        )

        # Atualizar versão com resultados
        versioning.update_backtest_results(
            "v3.0.0",
            {
                "hit_rate_11_13": result["metrics"]["hit_rate_11_13"],
                "suggestions_count": len(result["suggestions"]),
            },
        )

        version = versioning.get_version("v3.0.0")
        assert "hit_rate_11_13" in version["backtest_results"]
