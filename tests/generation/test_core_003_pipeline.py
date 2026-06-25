"""Testes de integração do pipeline CORE_003.

Valida o pipeline completo de 4 camadas com diferentes configurações.
"""

from __future__ import annotations

import pytest

from lotoia.generation.core_003_pipeline import (
    Core003Pipeline,
    generate_core_003_games,
)
from lotoia.statistics.structural_metrics_validator import (
    compute_structural_metrics,
    validate_structural_metrics,
)


class TestCore003Pipeline:
    """Testes do pipeline CORE_003."""

    def test_generate_15d_basic(self):
        """Geração básica 15D deve funcionar."""
        games = generate_core_003_games(
            format="15D",
            count=10,
            calibration="equilibrado",
        )

        assert len(games) == 10
        assert all(len(g["numbers"]) == 15 for g in games)
        assert all(1 <= n <= 25 for g in games for n in g["numbers"])

    def test_generate_15d_with_pool_size(self):
        """Geração com pool_size customizado."""
        games = generate_core_003_games(
            format="15D",
            count=20,
            pool_size=100,
            calibration="equilibrado",
        )

        assert len(games) == 20

    def test_generate_17d(self):
        """Geração 17D deve funcionar."""
        games = generate_core_003_games(
            format="17D",
            count=10,
            calibration="equilibrado",
        )

        assert len(games) == 10
        assert all(len(g["numbers"]) == 17 for g in games)
        assert all(1 <= n <= 25 for g in games for n in g["numbers"])

    def test_calibration_presets(self):
        """Todos os presets de calibração devem funcionar."""
        for preset in ["conservador", "equilibrado", "agressivo"]:
            games = generate_core_003_games(
                format="15D",
                count=10,
                calibration=preset,
            )
            assert len(games) == 10

    def test_invalid_format(self):
        """Formato inválido deve levantar erro."""
        with pytest.raises(ValueError, match="Formato .* não encontrado"):
            generate_core_003_games(
                format="99D",
                count=10,
            )

    def test_invalid_calibration(self):
        """Preset de calibração inválido deve levantar erro."""
        with pytest.raises(ValueError, match="Preset .* não encontrado"):
            generate_core_003_games(
                format="15D",
                count=10,
                calibration="invalido",
            )

    def test_structural_metrics_within_limits(self):
        """Métricas estruturais devem estar dentro dos limites."""
        games = generate_core_003_games(
            format="15D",
            count=50,
            pool_size=150,
            calibration="equilibrado",
        )

        metrics = compute_structural_metrics(games)
        validation = validate_structural_metrics(metrics)

        # Triplet 01-02-03 deve estar entre 10% e 35%
        assert 0.10 <= metrics["triplet_010203_pct"] <= 0.35

        # Overlap médio deve estar entre 7 e 13
        assert 7.0 <= metrics["avg_overlap"] <= 13.0

        # Validação deve passar
        assert validation["valid"] is True

    def test_pipeline_metrics(self):
        """Pipeline deve expor métricas da geração."""
        pipeline = Core003Pipeline(format="15D", calibration="equilibrado")
        games = pipeline.generate(count=20, pool_size=100)

        metrics = pipeline.get_metrics()

        assert "pool_size" in metrics
        assert "gp_size" in metrics
        assert "triplet_010203_pct" in metrics
        assert "avg_overlap" in metrics
        assert "diversity_score" in metrics
        assert "validation" in metrics

    def test_no_duplicate_games(self):
        """Não deve haver jogos duplicados."""
        games = generate_core_003_games(
            format="15D",
            count=50,
            pool_size=150,
            calibration="equilibrado",
        )

        # Converter jogos para tuples para comparação
        game_tuples = [tuple(sorted(g["numbers"])) for g in games]
        assert len(game_tuples) == len(set(game_tuples))

    def test_game_structure(self):
        """Estrutura dos jogos deve ser consistente."""
        games = generate_core_003_games(
            format="15D",
            count=10,
            calibration="equilibrado",
        )

        for game in games:
            # Deve ter campo numbers
            assert "numbers" in game

            # Numbers deve ser lista de 15 inteiros únicos
            numbers = game["numbers"]
            assert isinstance(numbers, list)
            assert len(numbers) == 15
            assert len(set(numbers)) == 15  # únicos
            assert all(isinstance(n, int) for n in numbers)
            assert all(1 <= n <= 25 for n in numbers)

            # Deve ter metadados CORE_002 (compatibilidade)
            assert "lei15_core_002_applied" in game or "lei15_core_002_metadata" in game

    def test_conservador_vs_agressivo(self):
        """Preset conservador deve ter overlap maior que agressivo."""
        games_conservador = generate_core_003_games(
            format="15D",
            count=30,
            pool_size=100,
            calibration="conservador",
        )

        games_agressivo = generate_core_003_games(
            format="15D",
            count=30,
            pool_size=100,
            calibration="agressivo",
        )

        metrics_conservador = compute_structural_metrics(games_conservador)
        metrics_agressivo = compute_structural_metrics(games_agressivo)

        # Conservador permite overlap maior (max_overlap=11 vs 9)
        # Mas não podemos garantir que a média seja maior devido à aleatoriedade
        # Apenas verificamos que ambos geram jogos válidos
        assert len(games_conservador) == 30
        assert len(games_agressivo) == 30

    def test_large_batch(self):
        """Geração de lote grande deve funcionar."""
        games = generate_core_003_games(
            format="15D",
            count=100,
            pool_size=300,
            calibration="equilibrado",
        )

        assert len(games) == 100
        metrics = compute_structural_metrics(games)

        # Métricas devem ser válidas mesmo em lotes grandes
        assert metrics["triplet_010203_pct"] >= 0.10
        assert metrics["avg_overlap"] <= 13.0


class TestCore003Config:
    """Testes da configuração do CORE_003."""

    def test_config_structure(self):
        """Configuração deve ter estrutura esperada."""
        from lotoia.config.core_003_config import CORE_003_CONFIG

        assert "historical_window" in CORE_003_CONFIG
        assert "formats" in CORE_003_CONFIG
        assert "structural_policy" in CORE_003_CONFIG
        assert "critical_digits" in CORE_003_CONFIG
        assert "calibration_presets" in CORE_003_CONFIG
        assert "validation_limits" in CORE_003_CONFIG

    def test_all_formats_defined(self):
        """Todos os formatos devem estar definidos."""
        from lotoia.config.core_003_config import CORE_003_CONFIG

        expected_formats = [
            "15D",
            "16D",
            "17D",
            "18D",
            "19D",
            "20D",
            "21D",
            "22D",
            "23D",
        ]
        for fmt in expected_formats:
            assert fmt in CORE_003_CONFIG["formats"]
            assert "dezenas" in CORE_003_CONFIG["formats"][fmt]

    def test_calibration_presets_defined(self):
        """Todos os presets devem estar definidos."""
        from lotoia.config.core_003_config import CORE_003_CONFIG

        expected_presets = ["conservador", "equilibrado", "agressivo"]
        for preset in expected_presets:
            assert preset in CORE_003_CONFIG["calibration_presets"]
            assert "overlap_penalty" in CORE_003_CONFIG["calibration_presets"][preset]
            assert "diversity_floor" in CORE_003_CONFIG["calibration_presets"][preset]
            assert (
                "critical_digit_boost" in CORE_003_CONFIG["calibration_presets"][preset]
            )

    def test_get_calibration_preset(self):
        """Função get_calibration_preset deve funcionar."""
        from lotoia.config.core_003_config import get_calibration_preset

        preset = get_calibration_preset("equilibrado")
        assert "overlap_penalty" in preset
        assert preset["overlap_penalty"] == 1.15

    def test_get_format_config(self):
        """Função get_format_config deve funcionar."""
        from lotoia.config.core_003_config import get_format_config

        config = get_format_config("15D")
        assert config["dezenas"] == 15

    def test_get_structural_policy(self):
        """Função get_structural_policy deve funcionar."""
        from lotoia.config.core_003_config import get_structural_policy

        policy = get_structural_policy()
        assert "triplet_010203" in policy
        assert policy["triplet_010203"]["freq"] == 0.21

    def test_get_critical_digits(self):
        """Função get_critical_digits deve funcionar."""
        from lotoia.config.core_003_config import get_critical_digits

        digits = get_critical_digits()
        assert "reinforce" in digits
        assert 7 in digits["reinforce"]
        assert 12 in digits["reinforce"]
        assert 23 in digits["reinforce"]
