"""Walk-Forward Validator para CORE_003 — Fase 5.

Validação temporal rigorosa que separa explicitamente:
- Training window: concursos para calibrar políticas
- Validation window: concursos para validar ajustes
- Test window: concursos para teste final (opcional)

Evita overfitting temporal garantindo que dados futuros não influenciem
configurações passadas.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from lotoia.experiments.temporal_governance import (
    TemporalSplit,
    build_walk_forward_splits,
    validate_temporal_integrity,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WalkForwardValidationConfig:
    """Configuração de validação walk-forward.
    
    Atributos:
        all_contests: Lista completa de concursos disponíveis (ordenada)
        training_contests: Concursos para treino/configuração
        validation_contests: Concursos para validação
        test_contests: Concursos para teste final (opcional)
        min_train_size: Tamanho mínimo do conjunto de treino
        validation_size: Tamanho do conjunto de validação
        step_size: Passo para walk-forward (padrão: 1)
    """
    
    all_contests: Sequence[int]
    training_contests: Sequence[int]
    validation_contests: Sequence[int]
    test_contests: Sequence[int] = ()
    min_train_size: int = 200
    validation_size: int = 100
    step_size: int = 1
    
    def __post_init__(self) -> None:
        """Valida configuração."""
        # Validar que listas estão ordenadas
        for name, contests in [
            ("training_contests", self.training_contests),
            ("validation_contests", self.validation_contests),
            ("test_contests", self.test_contests),
        ]:
            if contests != sorted(contests):
                raise ValueError(f"{name} must be sorted")
        
        # Validar que não há sobreposição temporal
        train_set = set(self.training_contests)
        val_set = set(self.validation_contests)
        test_set = set(self.test_contests)
        
        if train_set & val_set:
            raise ValueError("training and validation contests must not overlap")
        if val_set & test_set:
            raise ValueError("validation and test contests must not overlap")
        if train_set & test_set:
            raise ValueError("training and test contests must not overlap")
        
        # Validar ordem temporal
        if self.training_contests and self.validation_contests:
            if max(self.training_contests) >= min(self.validation_contests):
                raise ValueError("training must end before validation starts")
        
        if self.validation_contests and self.test_contests:
            if max(self.validation_contests) >= min(self.test_contests):
                raise ValueError("validation must end before test starts")


@dataclass
class WalkForwardSplitResult:
    """Resultado de validação em um único split temporal."""
    
    split_id: str
    train_contests: list[int]
    validation_contests: list[int]
    test_contests: list[int]
    
    # Métricas calculadas
    train_metrics: dict[str, Any] = field(default_factory=dict)
    validation_metrics: dict[str, Any] = field(default_factory=dict)
    test_metrics: dict[str, Any] = field(default_factory=dict)
    
    # Metadados
    games_generated_train: int = 0
    games_generated_validation: int = 0
    games_generated_test: int = 0
    
    def as_dict(self) -> dict[str, Any]:
        """Converte para dicionário."""
        return {
            "split_id": self.split_id,
            "train_contests": list(self.train_contests),
            "validation_contests": list(self.validation_contests),
            "test_contests": list(self.test_contests),
            "train_metrics": dict(self.train_metrics),
            "validation_metrics": dict(self.validation_metrics),
            "test_metrics": dict(self.test_metrics),
            "games_generated_train": self.games_generated_train,
            "games_generated_validation": self.games_generated_validation,
            "games_generated_test": self.games_generated_test,
        }


@dataclass
class WalkForwardResult:
    """Resultado agregado de validação walk-forward."""
    
    config: WalkForwardValidationConfig
    split_results: list[WalkForwardSplitResult]
    
    # Métricas agregadas
    aggregated_train_metrics: dict[str, Any] = field(default_factory=dict)
    aggregated_validation_metrics: dict[str, Any] = field(default_factory=dict)
    aggregated_test_metrics: dict[str, Any] = field(default_factory=dict)
    
    # Metadados
    total_splits: int = 0
    total_games_generated: int = 0
    
    # Flags de qualidade
    temporal_leakage_detected: bool = False
    performance_degradation: bool = False
    
    def as_dict(self) -> dict[str, Any]:
        """Converte para dicionário."""
        return {
            "total_splits": self.total_splits,
            "total_games_generated": self.total_games_generated,
            "temporal_leakage_detected": self.temporal_leakage_detected,
            "performance_degradation": self.performance_degradation,
            "aggregated_train_metrics": dict(self.aggregated_train_metrics),
            "aggregated_validation_metrics": dict(self.aggregated_validation_metrics),
            "aggregated_test_metrics": dict(self.aggregated_test_metrics),
            "splits": [split.as_dict() for split in self.split_results],
        }
    
    def is_valid(self) -> bool:
        """Verifica se validação passou nos critérios de qualidade."""
        return not self.temporal_leakage_detected and not self.performance_degradation


class WalkForwardValidator:
    """Validador walk-forward para pipeline CORE_003.
    
    Executa validação temporal rigorosa separando explicitamente
    dados de treino, validação e teste.
    
    Uso:
        >>> config = WalkForwardValidationConfig(
        ...     all_contests=list(range(3419, 3720)),
        ...     training_contests=list(range(3419, 3619)),
        ...     validation_contests=list(range(3619, 3719)),
        ... )
        >>> validator = WalkForwardValidator(config)
        >>> result = validator.validate(pipeline_generator_fn)
    """
    
    def __init__(self, config: WalkForwardValidationConfig) -> None:
        """Inicializa validador.
        
        Args:
            config: Configuração de validação walk-forward
        """
        self.config = config
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Valida configuração temporal."""
        # Validar integridade temporal
        validate_temporal_integrity(self.config.all_contests).assert_valid()
        
        if self.config.training_contests:
            validate_temporal_integrity(self.config.training_contests).assert_valid()
        if self.config.validation_contests:
            validate_temporal_integrity(self.config.validation_contests).assert_valid()
        if self.config.test_contests:
            validate_temporal_integrity(self.config.test_contests).assert_valid()
        
        logger.info(
            "[WalkForward] Config validada | "
            "train=%d val=%d test=%d",
            len(self.config.training_contests),
            len(self.config.validation_contests),
            len(self.config.test_contests),
        )
    
    def validate(
        self,
        generator_fn: Callable[[list[int], int], tuple[list[dict], dict[str, Any]]],
        *,
        games_per_contest: int = 10,
        pool_size: int = 100,
    ) -> WalkForwardResult:
        """Executa validação walk-forward.
        
        Args:
            generator_fn: Função que gera jogos dado histórico e target_contest.
                         Assinatura: (history_contests, target_contest) -> (games, metrics)
            games_per_contest: Quantidade de jogos a gerar por concurso
            pool_size: Tamanho do pool de candidatos
        
        Returns:
            Resultado agregado da validação
        """
        logger.info(
            "[WalkForward] Iniciando validação | "
            "games_per_contest=%d pool_size=%d",
            games_per_contest,
            pool_size,
        )
        
        split_results: list[WalkForwardSplitResult] = []
        
        # Validar em cada split temporal
        for split_idx, split in enumerate(self._build_splits()):
            logger.info("[WalkForward] Processando split %d/%d", split_idx + 1, len(list(self._build_splits())))
            
            split_result = self._validate_split(
                split,
                generator_fn,
                games_per_contest=games_per_contest,
                pool_size=pool_size,
            )
            split_results.append(split_result)
        
        # Agregar resultados
        result = WalkForwardResult(
            config=self.config,
            split_results=split_results,
            total_splits=len(split_results),
        )
        
        # Calcular métricas agregadas
        result.aggregated_train_metrics = self._aggregate_metrics(
            [s.train_metrics for s in split_results]
        )
        result.aggregated_validation_metrics = self._aggregate_metrics(
            [s.validation_metrics for s in split_results]
        )
        if split_results[0].test_metrics:
            result.aggregated_test_metrics = self._aggregate_metrics(
                [s.test_metrics for s in split_results]
            )
        
        # Calcular totais
        result.total_games_generated = sum(
            s.games_generated_train + s.games_generated_validation + s.games_generated_test
            for s in split_results
        )
        
        # Detectar problemas
        result.temporal_leakage_detected = self._detect_temporal_leakage(split_results)
        result.performance_degradation = self._detect_performance_degradation(split_results)
        
        logger.info(
            "[WalkForward] Validação concluída | "
            "splits=%d games=%d valid=%s",
            result.total_splits,
            result.total_games_generated,
            result.is_valid(),
        )
        
        return result
    
    def _build_splits(self) -> Sequence[TemporalSplit]:
        """Constrói splits temporais usando configuração.
        
        Se configuração já define windows explicitamente, usa isso.
        Caso contrário, gera splits walk-forward automáticos.
        """
        # Se configuração já define windows, criar split único
        if self.config.training_contests and self.config.validation_contests:
            return [
                TemporalSplit(
                    split_id="wf_explicit_001",
                    train_start=min(self.config.training_contests),
                    train_end=max(self.config.training_contests),
                    test_start=min(self.config.validation_contests),
                    test_end=max(self.config.validation_contests),
                )
            ]
        
        # Gerar splits walk-forward automáticos
        return build_walk_forward_splits(
            self.config.all_contests,
            min_train_size=self.config.min_train_size,
            test_size=self.config.validation_size,
            step_size=self.config.step_size,
        )
    
    def _validate_split(
        self,
        split: TemporalSplit,
        generator_fn: Callable[[list[int], int], tuple[list[dict], dict[str, Any]]],
        *,
        games_per_contest: int,
        pool_size: int,
    ) -> WalkForwardSplitResult:
        """Valida em um único split temporal."""
        # Extrair concursos de cada janela
        train_contests = [c for c in self.config.all_contests 
                         if split.train_start <= c <= split.train_end]
        validation_contests = [c for c in self.config.all_contests 
                              if split.test_start <= c <= split.test_end]
        test_contests = []  # Opcional
        
        result = WalkForwardSplitResult(
            split_id=split.split_id,
            train_contests=train_contests,
            validation_contests=validation_contests,
            test_contests=test_contests,
        )
        
        # === FASE TREINO ===
        # Gerar jogos usando apenas dados de treino
        train_games: list[dict] = []
        for contest in train_contests[:games_per_contest]:  # Limitar para performance
            history = [c for c in train_contests if c < contest]
            if not history:
                continue
            games, metrics = generator_fn(history, contest)
            train_games.extend(games)
            result.games_generated_train += len(games)
        
        # Calcular métricas de treino
        result.train_metrics = self._compute_metrics(train_games)
        
        # === FASE VALIDAÇÃO ===
        # Gerar jogos usando dados de treino + validação
        validation_games: list[dict] = []
        for contest in validation_contests[:games_per_contest]:
            # Histórico inclui treino completo
            history = train_contests + [c for c in validation_contests if c < contest]
            games, metrics = generator_fn(history, contest)
            validation_games.extend(games)
            result.games_generated_validation += len(games)
        
        # Calcular métricas de validação
        result.validation_metrics = self._compute_metrics(validation_games)
        
        # === FASE TESTE (opcional) ===
        if test_contests:
            test_games: list[dict] = []
            for contest in test_contests[:games_per_contest]:
                # Histórico inclui treino + validação
                history = train_contests + validation_contests + [c for c in test_contests if c < contest]
                games, metrics = generator_fn(history, contest)
                test_games.extend(games)
                result.games_generated_test += len(games)
            
            result.test_metrics = self._compute_metrics(test_games)
        
        logger.info(
            "[WalkForward:%s] Split concluído | "
            "train_games=%d val_games=%d test_games=%d",
            split.split_id,
            result.games_generated_train,
            result.games_generated_validation,
            result.games_generated_test,
        )
        
        return result
    
    def _compute_metrics(self, games: list[dict]) -> dict[str, Any]:
        """Computa métricas estruturais de um conjunto de jogos."""
        if not games:
            return {"count": 0}
        
        from lotoia.statistics.structural_metrics_validator import compute_structural_metrics
        
        metrics = compute_structural_metrics(games)
        metrics["count"] = len(games)
        
        return metrics
    
    def _aggregate_metrics(self, metrics_list: list[dict[str, Any]]) -> dict[str, Any]:
        """Agrega métricas de múltiplos splits."""
        if not metrics_list:
            return {}
        
        # Contar jogos totais
        total_count = sum(m.get("count", 0) for m in metrics_list)
        
        # Calcular média ponderada de métricas numéricas
        aggregated: dict[str, Any] = {"count": total_count}
        
        numeric_keys = [
            "avg_overlap",
            "diversity_score",
            "triplet_010203_pct",
            "suffix_232425_pct",
        ]
        
        for key in numeric_keys:
            values = [m.get(key) for m in metrics_list if key in m]
            if values:
                aggregated[key] = sum(values) / len(values)
        
        return aggregated
    
    def _detect_temporal_leakage(self, split_results: list[WalkForwardSplitResult]) -> bool:
        """Detecta vazamento temporal comparando métricas entre splits.
        
        Se métricas de validação são drasticamente melhores que treino,
        pode indicar vazamento de dados futuros.
        """
        for split in split_results:
            train_count = split.train_metrics.get("count", 0)
            val_count = split.validation_metrics.get("count", 0)
            
            if train_count == 0 or val_count == 0:
                continue
            
            # Comparar diversity_score
            train_diversity = split.train_metrics.get("diversity_score", 0)
            val_diversity = split.validation_metrics.get("diversity_score", 0)
            
            # Se validação é 20% melhor que treino, suspeitar vazamento
            if val_diversity > train_diversity * 1.2:
                logger.warning(
                    "[WalkForward:%s] Possível vazamento temporal detectado | "
                    "train_diversity=%.3f val_diversity=%.3f",
                    split.split_id,
                    train_diversity,
                    val_diversity,
                )
                return True
        
        return False
    
    def _detect_performance_degradation(self, split_results: list[WalkForwardSplitResult]) -> bool:
        """Detecta degradação de performance ao longo do tempo.
        
        Se métricas pioram consistentemente ao longo dos splits,
        pode indicar que modelo não está acompanhando mudanças temporais.
        """
        if len(split_results) < 2:
            return False
        
        # Comparar métricas entre splits consecutivos
        degradation_count = 0
        
        for i in range(len(split_results) - 1):
            current = split_results[i]
            next_split = split_results[i + 1]
            
            current_diversity = current.validation_metrics.get("diversity_score", 0)
            next_diversity = next_split.validation_metrics.get("diversity_score", 0)
            
            # Se métrica piorou mais de 10%
            if current_diversity > 0 and next_diversity < current_diversity * 0.9:
                degradation_count += 1
        
        # Se mais de 50% dos splits mostram degradação
        if degradation_count > len(split_results) * 0.5:
            logger.warning(
                "[WalkForward] Degradação de performance detectada | "
                "splits_with_degradation=%d/%d",
                degradation_count,
                len(split_results) - 1,
            )
            return True
        
        return False
