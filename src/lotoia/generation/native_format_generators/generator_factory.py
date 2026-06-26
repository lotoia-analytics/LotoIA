"""Factory para resolver gerador nativo por formato — Fase 3.

Centraliza o mapeamento formato → gerador nativo.
"""

from __future__ import annotations

import logging
from typing import Any

from lotoia.generation.native_format_generators.base_generator import BaseNativeGenerator

logger = logging.getLogger(__name__)

# Registry de geradores nativos por formato
_GENERATOR_REGISTRY: dict[str, type[BaseNativeGenerator]] = {}


def register_generator(format: str, generator_class: type[BaseNativeGenerator]) -> None:
    """Registra um gerador nativo para um formato."""
    _GENERATOR_REGISTRY[format] = generator_class
    logger.debug("[NativeGenFactory] Registrado: %s → %s", format, generator_class.__name__)


def get_native_generator(format: str) -> BaseNativeGenerator:
    """Retorna o gerador nativo para o formato especificado.
    
    Args:
        format: Formato do jogo (15D, 17D, 18D, 20D, 23D)
    
    Returns:
        Instância do gerador nativo
    
    Raises:
        ValueError: Se formato não tiver gerador nativo registrado
    """
    # Lazy import para evitar circular dependency
    _ensure_registry_loaded()

    generator_class = _GENERATOR_REGISTRY.get(format)
    if generator_class is None:
        available = sorted(_GENERATOR_REGISTRY.keys())
        raise ValueError(
            f"Formato '{format}' não tem gerador nativo. "
            f"Formatos disponíveis: {available}"
        )
    
    return generator_class()


def list_available_formats() -> list[str]:
    """Retorna lista de formatos com geradores nativos registrados."""
    _ensure_registry_loaded()
    return sorted(_GENERATOR_REGISTRY.keys())


_registry_loaded = False


def _ensure_registry_loaded() -> None:
    """Carrega registry na primeira chamada (lazy loading)."""
    global _registry_loaded
    if _registry_loaded:
        return
    
    # Importar geradores (eles se auto-registram)
    from lotoia.generation.native_format_generators.generator_15d import Generator15D
    from lotoia.generation.native_format_generators.generator_17d import Generator17D
    from lotoia.generation.native_format_generators.generator_18d import Generator18D
    from lotoia.generation.native_format_generators.generator_20d import Generator20D
    from lotoia.generation.native_format_generators.generator_23d import Generator23D

    _registry_loaded = True
    logger.debug("[NativeGenFactory] Registry carregado: %d formatos", len(_GENERATOR_REGISTRY))


class NativeFormatGeneratorFactory:
    """Factory para criar geradores nativos por formato.
    
    Uso:
        >>> factory = NativeFormatGeneratorFactory()
        >>> gen = factory.create("17D")
        >>> pool = gen.build_pool(pool_size=100, seed=42)
    """

    def create(self, format: str) -> BaseNativeGenerator:
        """Cria gerador nativo para o formato."""
        return get_native_generator(format)

    def available_formats(self) -> list[str]:
        """Lista formatos disponíveis."""
        return list_available_formats()

    def supports_format(self, format: str) -> bool:
        """Verifica se formato tem gerador nativo."""
        _ensure_registry_loaded()
        return format in _GENERATOR_REGISTRY
