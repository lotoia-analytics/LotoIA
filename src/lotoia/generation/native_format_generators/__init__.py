"""Geradores nativos por formato — Fase 3.

Cada formato (15D-23D) tem seu próprio motor de geração com políticas
estruturais específicas (paridade, overlap, triplet, soma).
"""

from lotoia.generation.native_format_generators.generator_factory import (
    NativeFormatGeneratorFactory,
    get_native_generator,
)
from lotoia.generation.native_format_generators.base_generator import (
    BaseNativeGenerator,
)

__all__ = [
    "BaseNativeGenerator",
    "NativeFormatGeneratorFactory",
    "get_native_generator",
]
