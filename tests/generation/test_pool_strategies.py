"""Testes do Pool Multi-Estratégia — Fase 6.

Cobre:
- Cada estratégia individual: frequência, padrão, cobertura, aleatório
- MultiStrategyPoolGenerator: combinação de estratégias
- Integração com pipeline CORE_003
- Pesos customizados
"""

from __future__ import annotations

import pytest

from lotoia.generation.pool_strategies import (
    BasePoolStrategy,
    FrequencyStrategy,
    PatternStrategy,
    CoverageStrategy,
    RandomStrategy,
    MultiStrategyPoolGenerator,
    DEFAULT_STRATEGY_WEIGHTS,
)


# ============================================================
# FREQUENCY STRATEGY
# ============================================================


class TestFrequencyStrategy:
    """Testes da estratégia de frequência."""

    def test_generate_returns_correct_pool_size(self):
        strategy = FrequencyStrategy()
        pool = strategy.generate(50, format="15D")
        assert len(pool) == 50

    def test_generate_games_have_correct_size(self):
        strategy = FrequencyStrategy()
        pool = strategy.generate(30, format="15D")
        for game in pool:
            assert len(game["numbers"]) == 15

    def test_generate_17d(self):
        strategy = FrequencyStrategy()
        pool = strategy.generate(30, format="17D")
        for game in pool:
            assert len(game["numbers"]) == 17

    def test_generate_with_history(self):
        strategy = FrequencyStrategy()
        history = [
            {"numbers": list(range(1, 16))},
            {"numbers": list(range(5, 20))},
        ]
        pool = strategy.generate(30, format="15D", history=history)
        assert len(pool) == 30

    def test_reproducible_with_seed(self):
        strategy1 = FrequencyStrategy()
        pool1 = strategy1.generate(20, format="15D", seed=42)
        
        strategy2 = FrequencyStrategy()
        pool2 = strategy2.generate(20, format="15D", seed=42)
        
        for g1, g2 in zip(pool1, pool2):
            assert g1["numbers"] == g2["numbers"]

    def test_strategy_name(self):
        strategy = FrequencyStrategy()
        assert strategy.get_strategy_name() == "frequency"

    def test_pool_strategy_metadata(self):
        strategy = FrequencyStrategy()
        pool = strategy.generate(10, format="15D")
        for game in pool:
            assert game.get("pool_strategy") == "frequency"


# ============================================================
# PATTERN STRATEGY
# ============================================================


class TestPatternStrategy:
    """Testes da estratégia de padrões."""

    def test_generate_returns_correct_pool_size(self):
        strategy = PatternStrategy()
        pool = strategy.generate(50, format="15D")
        assert len(pool) == 50

    def test_triplet_pct_respected(self):
        strategy = PatternStrategy(triplet_pct=0.30)
        pool = strategy.generate(100, format="15D")
        triplets = sum(1 for g in pool if g.get("has_triplet"))
        # Deve ter aproximadamente 30% com triplet (margem de 10%)
        assert 20 <= triplets <= 40

    def test_suffix_pct_respected(self):
        strategy = PatternStrategy(suffix_pct=0.25)
        pool = strategy.generate(100, format="15D")
        suffixes = sum(1 for g in pool if g.get("has_suffix"))
        # Deve ter aproximadamente 25% com suffix
        assert 15 <= suffixes <= 35

    def test_strategy_name(self):
        strategy = PatternStrategy()
        assert strategy.get_strategy_name() == "pattern"


# ============================================================
# COVERAGE STRATEGY
# ============================================================


class TestCoverageStrategy:
    """Testes da estratégia de cobertura."""

    def test_generate_returns_correct_pool_size(self):
        strategy = CoverageStrategy()
        pool = strategy.generate(50, format="15D")
        assert len(pool) == 50

    def test_coverage_improves_over_pool(self):
        strategy = CoverageStrategy()
        pool = strategy.generate(50, format="15D")
        
        # Contar cobertura de cada dezena
        coverage = {n: 0 for n in range(1, 26)}
        for game in pool:
            for n in game["numbers"]:
                coverage[n] += 1
        
        # Com 50 jogos de 15 dezenas, total = 750 presenças
        # Média esperada por dezena: 750/25 = 30
        total_presences = sum(coverage.values())
        assert total_presences == 50 * 15
        
        # Todas as dezenas devem estar presentes
        for n in range(1, 26):
            assert coverage[n] > 0, f"Dezena {n} não está presente no pool"

    def test_strategy_name(self):
        strategy = CoverageStrategy()
        assert strategy.get_strategy_name() == "coverage"


# ============================================================
# RANDOM STRATEGY
# ============================================================


class TestRandomStrategy:
    """Testes da estratégia aleatória."""

    def test_generate_returns_correct_pool_size(self):
        strategy = RandomStrategy()
        pool = strategy.generate(50, format="15D")
        assert len(pool) == 50

    def test_generate_17d(self):
        strategy = RandomStrategy()
        pool = strategy.generate(30, format="17D")
        for game in pool:
            assert len(game["numbers"]) == 17

    def test_reproducible_with_seed(self):
        strategy1 = RandomStrategy()
        pool1 = strategy1.generate(20, format="15D", seed=42)
        
        strategy2 = RandomStrategy()
        pool2 = strategy2.generate(20, format="15D", seed=42)
        
        for g1, g2 in zip(pool1, pool2):
            assert g1["numbers"] == g2["numbers"]

    def test_strategy_name(self):
        strategy = RandomStrategy()
        assert strategy.get_strategy_name() == "random"


# ============================================================
# MULTI-STRATEGY GENERATOR
# ============================================================


class TestMultiStrategyPoolGenerator:
    """Testes do gerador multi-estratégia."""

    def test_default_weights_sum_to_one(self):
        total = sum(DEFAULT_STRATEGY_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01

    def test_generate_with_default_weights(self):
        generator = MultiStrategyPoolGenerator()
        pool = generator.generate(100, format="15D")
        assert len(pool) == 100

    def test_generate_with_custom_weights(self):
        weights = {
            "frequency": 0.40,
            "pattern": 0.20,
            "coverage": 0.20,
            "random": 0.20,
        }
        generator = MultiStrategyPoolGenerator(weights=weights)
        pool = generator.generate(100, format="15D")
        assert len(pool) == 100

    def test_invalid_weights_raise_error(self):
        with pytest.raises(ValueError, match="must sum to 1.0"):
            MultiStrategyPoolGenerator(weights={
                "frequency": 0.50,
                "random": 0.50,
                "pattern": 0.50,  # Soma = 1.5
            })

    def test_strategy_breakdown(self):
        generator = MultiStrategyPoolGenerator()
        pool = generator.generate(100, format="15D")
        
        breakdown = generator.get_strategy_breakdown(pool)
        
        assert "frequency" in breakdown
        assert "pattern" in breakdown
        assert "coverage" in breakdown
        assert "random" in breakdown
        
        total = sum(breakdown.values())
        assert total == 100

    def test_reproducible_with_seed(self):
        gen1 = MultiStrategyPoolGenerator()
        pool1 = gen1.generate(50, format="15D", seed=42)
        
        gen2 = MultiStrategyPoolGenerator()
        pool2 = gen2.generate(50, format="15D", seed=42)
        
        for g1, g2 in zip(pool1, pool2):
            assert g1["numbers"] == g2["numbers"]

    def test_different_formats(self):
        generator = MultiStrategyPoolGenerator()
        
        for fmt in ["15D", "17D", "18D", "20D", "23D"]:
            game_size = int(fmt.replace("D", ""))
            pool = generator.generate(30, format=fmt)
            assert len(pool) == 30
            for game in pool:
                assert len(game["numbers"]) == game_size


# ============================================================
# PIPELINE INTEGRATION
# ============================================================


class TestPipelineMultiStrategyIntegration:
    """Testes de integração com pipeline CORE_003."""

    def test_pipeline_with_multi_strategy(self):
        from lotoia.generation.core_003_pipeline import Core003Pipeline
        
        pipeline = Core003Pipeline(format="15D", use_multi_strategy=True)
        games = pipeline.generate(count=10, pool_size=50)
        assert len(games) > 0
        
        metrics = pipeline.get_metrics()
        assert metrics.get("multi_strategy") is True
        assert "strategy_breakdown" in metrics

    def test_pipeline_without_multi_strategy(self):
        from lotoia.generation.core_003_pipeline import Core003Pipeline
        
        pipeline = Core003Pipeline(format="15D", use_multi_strategy=False)
        games = pipeline.generate(count=10, pool_size=50)
        assert len(games) > 0
        
        metrics = pipeline.get_metrics()
        assert metrics.get("multi_strategy") is False

    def test_pipeline_with_custom_weights(self):
        from lotoia.generation.core_003_pipeline import Core003Pipeline
        
        weights = {
            "frequency": 0.50,
            "pattern": 0.20,
            "coverage": 0.20,
            "random": 0.10,
        }
        pipeline = Core003Pipeline(
            format="15D",
            use_multi_strategy=True,
            strategy_weights=weights,
        )
        games = pipeline.generate(count=10, pool_size=50)
        assert len(games) > 0
