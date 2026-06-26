"""Classe base para estratégias de pool — Fase 6.

Define a interface comum para todas as estratégias de geração de pool.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BasePoolStrategy(ABC):
    """Classe base para estratégias de geração de pool.
    
    Cada estratégia gera uma parte do pool com características específicas:
    - FrequencyStrategy: prioriza dezenas mais frequentes
    - PatternStrategy: prioriza padrões estruturais (triplet, suffix, etc)
    - CoverageStrategy: maximiza cobertura de dezenas
    - RandomStrategy: geração puramente aleatória
    """
    
    def __init__(self, weight: float = 1.0):
        """Inicializa estratégia com peso.
        
        Args:
            weight: Peso da estratégia na composição do pool (0.0 a 1.0)
        """
        if not 0.0 <= weight <= 1.0:
            raise ValueError(f"Weight must be between 0.0 and 1.0, got {weight}")
        self.weight = weight
    
    @abstractmethod
    def generate(
        self,
        pool_size: int,
        *,
        format: str = "15D",
        history: list[Any] | None = None,
        seed: int | None = None,
    ) -> list[dict[str, Any]]:
        """Gera pool usando esta estratégia.
        
        Args:
            pool_size: Tamanho do pool a gerar
            format: Formato dos jogos (15D, 17D, etc)
            history: Histórico de concursos para análise
            seed: Seed para reprodutibilidade
        
        Returns:
            Lista de jogos gerados
        """
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Retorna nome da estratégia."""
        pass
    
    def get_strategy_metadata(self) -> dict[str, Any]:
        """Retorna metadados da estratégia."""
        return {
            "strategy": self.get_strategy_name(),
            "weight": self.weight,
        }
