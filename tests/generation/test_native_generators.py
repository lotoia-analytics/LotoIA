"""Testes dos geradores nativos por formato — Fase 3.

Cobre:
- Factory: registro e resolução de geradores
- Cada gerador nativo: tamanho correto, paridade, soma, reprodutibilidade
- Pipeline: integração com geradores nativos
- Config: políticas nativas por formato
"""

from __future__ import annotations

import pytest

from lotoia.generation.native_format_generators import (
    BaseNativeGenerator,
    NativeFormatGeneratorFactory,
    get_native_generator,
)
from lotoia.generation.native_format_generators.generator_factory import (
    list_available_formats,
)
from lotoia.config.core_003_config import (
    CORE_003_CONFIG,
    is_native_format,
    get_native_format_policy,
)


# ============================================================
# FACTORY
# ============================================================


class TestNativeFormatGeneratorFactory:
    """Testes do factory de geradores nativos."""

    def test_factory_returns_generator_for_15d(self):
        gen = get_native_generator("15D")
        assert isinstance(gen, BaseNativeGenerator)
        assert gen.format == "15D"
        assert gen.game_size == 15

    def test_factory_returns_generator_for_17d(self):
        gen = get_native_generator("17D")
        assert isinstance(gen, BaseNativeGenerator)
        assert gen.format == "17D"
        assert gen.game_size == 17

    def test_factory_returns_generator_for_18d(self):
        gen = get_native_generator("18D")
        assert isinstance(gen, BaseNativeGenerator)
        assert gen.format == "18D"
        assert gen.game_size == 18

    def test_factory_returns_generator_for_20d(self):
        gen = get_native_generator("20D")
        assert isinstance(gen, BaseNativeGenerator)
        assert gen.format == "20D"
        assert gen.game_size == 20

    def test_factory_returns_generator_for_23d(self):
        gen = get_native_generator("23D")
        assert isinstance(gen, BaseNativeGenerator)
        assert gen.format == "23D"
        assert gen.game_size == 23

    def test_factory_raises_for_unknown_format(self):
        with pytest.raises(ValueError, match="não tem gerador nativo"):
            get_native_generator("99D")

    def test_available_formats(self):
        formats = list_available_formats()
        assert "15D" in formats
        assert "17D" in formats
        assert "18D" in formats
        assert "20D" in formats
        assert "23D" in formats

    def test_factory_class_supports_format(self):
        factory = NativeFormatGeneratorFactory()
        assert factory.supports_format("15D")
        assert factory.supports_format("20D")
        assert not factory.supports_format("99D")


# ============================================================
# GERADOR 15D
# ============================================================


class TestGenerator15D:
    """Testes do gerador nativo 15D."""

    def test_build_pool_returns_correct_size(self):
        gen = get_native_generator("15D")
        pool = gen.build_pool(50, seed=42)
        assert len(pool) == 50

    def test_build_pool_games_have_15_numbers(self):
        gen = get_native_generator("15D")
        pool = gen.build_pool(30, seed=42)
        for game in pool:
            assert len(game["numbers"]) == 15

    def test_build_pool_numbers_in_range(self):
        gen = get_native_generator("15D")
        pool = gen.build_pool(30, seed=42)
        for game in pool:
            for n in game["numbers"]:
                assert 1 <= n <= 25

    def test_build_pool_reproducible_with_seed(self):
        gen1 = get_native_generator("15D")
        pool1 = gen1.build_pool(20, seed=123)
        gen2 = get_native_generator("15D")
        pool2 = gen2.build_pool(20, seed=123)
        for g1, g2 in zip(pool1, pool2):
            assert g1["numbers"] == g2["numbers"]

    def test_format_policies(self):
        gen = get_native_generator("15D")
        policies = gen.get_format_policies()
        assert policies["game_size"] == 15
        assert (7, 8) in policies["parity_targets"]
        assert policies["overlap_target"] == 10.0


# ============================================================
# GERADOR 17D
# ============================================================


class TestGenerator17D:
    """Testes do gerador nativo 17D."""

    def test_build_pool_returns_correct_size(self):
        gen = get_native_generator("17D")
        pool = gen.build_pool(50, seed=42)
        assert len(pool) > 0
        assert len(pool) <= 50

    def test_build_pool_games_have_17_numbers(self):
        gen = get_native_generator("17D")
        pool = gen.build_pool(30, seed=42)
        for game in pool:
            assert len(game["numbers"]) == 17

    def test_parity_is_balanced(self):
        gen = get_native_generator("17D")
        pool = gen.build_pool(50, seed=42)
        for game in pool:
            odd = sum(1 for n in game["numbers"] if n % 2 != 0)
            even = len(game["numbers"]) - odd
            assert (odd, even) in [(9, 8), (8, 9)]

    def test_sum_in_range(self):
        gen = get_native_generator("17D")
        pool = gen.build_pool(30, seed=42)
        for game in pool:
            assert 200 <= game["sum"] <= 250


# ============================================================
# GERADOR 18D
# ============================================================


class TestGenerator18D:
    """Testes do gerador nativo 18D."""

    def test_build_pool_games_have_18_numbers(self):
        gen = get_native_generator("18D")
        pool = gen.build_pool(30, seed=42)
        for game in pool:
            assert len(game["numbers"]) == 18

    def test_parity_targets(self):
        gen = get_native_generator("18D")
        pool = gen.build_pool(50, seed=42)
        valid_parities = {(9, 9), (10, 8), (8, 10)}
        for game in pool:
            odd = sum(1 for n in game["numbers"] if n % 2 != 0)
            even = len(game["numbers"]) - odd
            assert (odd, even) in valid_parities

    def test_sum_in_range(self):
        gen = get_native_generator("18D")
        pool = gen.build_pool(30, seed=42)
        for game in pool:
            assert 210 <= game["sum"] <= 260


# ============================================================
# GERADOR 20D
# ============================================================


class TestGenerator20D:
    """Testes do gerador nativo 20D."""

    def test_build_pool_games_have_20_numbers(self):
        gen = get_native_generator("20D")
        pool = gen.build_pool(30, seed=42)
        for game in pool:
            assert len(game["numbers"]) == 20

    def test_parity_targets(self):
        gen = get_native_generator("20D")
        pool = gen.build_pool(50, seed=42)
        valid_parities = {(10, 10), (11, 9), (9, 11)}
        for game in pool:
            odd = sum(1 for n in game["numbers"] if n % 2 != 0)
            even = len(game["numbers"]) - odd
            assert (odd, even) in valid_parities

    def test_sum_in_range(self):
        gen = get_native_generator("20D")
        pool = gen.build_pool(30, seed=42)
        for game in pool:
            assert 230 <= game["sum"] <= 280


# ============================================================
# GERADOR 23D
# ============================================================


class TestGenerator23D:
    """Testes do gerador nativo 23D."""

    def test_build_pool_games_have_23_numbers(self):
        gen = get_native_generator("23D")
        pool = gen.build_pool(30, seed=42)
        for game in pool:
            assert len(game["numbers"]) == 23

    def test_23d_excludes_exactly_2_numbers(self):
        gen = get_native_generator("23D")
        pool = gen.build_pool(30, seed=42)
        for game in pool:
            excluded = set(range(1, 26)) - set(game["numbers"])
            assert len(excluded) == 2

    def test_parity_targets(self):
        gen = get_native_generator("23D")
        pool = gen.build_pool(50, seed=42)
        valid_parities = {(12, 11), (11, 12)}
        for game in pool:
            odd = sum(1 for n in game["numbers"] if n % 2 != 0)
            even = len(game["numbers"]) - odd
            assert (odd, even) in valid_parities

    def test_sum_in_range(self):
        gen = get_native_generator("23D")
        pool = gen.build_pool(30, seed=42)
        for game in pool:
            assert 260 <= game["sum"] <= 310


# ============================================================
# CONFIG — POLÍTICAS NATIVAS
# ============================================================


class TestNativeFormatConfig:
    """Testes da configuração de formatos nativos."""

    def test_native_formats_set(self):
        assert "15D" in CORE_003_CONFIG["native_formats"]
        assert "17D" in CORE_003_CONFIG["native_formats"]
        assert "20D" in CORE_003_CONFIG["native_formats"]
        assert "16D" not in CORE_003_CONFIG["native_formats"]

    def test_is_native_format(self):
        assert is_native_format("15D") is True
        assert is_native_format("17D") is True
        assert is_native_format("20D") is True
        assert is_native_format("16D") is False
        assert is_native_format("19D") is False

    def test_native_format_policy_returns_dict(self):
        policy = get_native_format_policy("15D")
        assert policy is not None
        assert "parity_targets" in policy
        assert "sum_range" in policy
        assert "overlap_target" in policy

    def test_native_format_policy_returns_none_for_non_native(self):
        policy = get_native_format_policy("16D")
        assert policy is None

    def test_each_native_format_has_parity_targets(self):
        for fmt in ["15D", "17D", "18D", "20D", "23D"]:
            policy = get_native_format_policy(fmt)
            assert policy is not None, f"{fmt} missing native policy"
            assert len(policy["parity_targets"]) > 0, f"{fmt} has no parity targets"


# ============================================================
# PIPELINE — INTEGRAÇÃO
# ============================================================


class TestPipelineNativeIntegration:
    """Testes de integração pipeline + geradores nativos."""

    def test_pipeline_uses_native_for_15d(self):
        from lotoia.generation.core_003_pipeline import Core003Pipeline

        pipeline = Core003Pipeline(format="15D")
        games = pipeline.generate(count=10, pool_size=50)
        assert len(games) > 0
        metrics = pipeline.get_metrics()
        assert metrics.get("native_generation") is True

    def test_pipeline_uses_native_for_17d(self):
        from lotoia.generation.core_003_pipeline import Core003Pipeline

        pipeline = Core003Pipeline(format="17D")
        games = pipeline.generate(count=10, pool_size=50)
        assert len(games) > 0
        metrics = pipeline.get_metrics()
        assert metrics.get("native_generation") is True

    def test_pipeline_uses_expanded_for_16d(self):
        from lotoia.generation.core_003_pipeline import Core003Pipeline

        pipeline = Core003Pipeline(format="16D")
        games = pipeline.generate(count=10, pool_size=50)
        assert len(games) > 0
        metrics = pipeline.get_metrics()
        assert metrics.get("native_generation") is False

    def test_pipeline_games_have_correct_size_for_native(self):
        from lotoia.generation.core_003_pipeline import Core003Pipeline

        for fmt in ["15D", "17D", "18D", "20D"]:
            pipeline = Core003Pipeline(format=fmt)
            games = pipeline.generate(count=5, pool_size=30)
            expected_size = int(fmt.replace("D", ""))
            for game in games:
                assert len(game["numbers"]) == expected_size, (
                    f"{fmt}: expected {expected_size} numbers, got {len(game['numbers'])}"
                )
