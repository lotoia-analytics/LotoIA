"""Validação de métricas estruturais pós-geração — CORE_002.

Detecta automaticamente bugs como triplet cap=0 ou overlap fora do esperado.
Integrado ao basic_generator.py para validação automática após cada geração.

Versão: 1.0.0
Baseline: últimos 300 concursos oficiais
"""

from __future__ import annotations

import logging
from typing import Any, Sequence

logger = logging.getLogger(__name__)

# Limites aceitáveis (baseados em frequência histórica ± tolerância)
STRUCTURAL_LIMITS = {
    "triplet_010203_pct": {
        "min": 0.10,  # mínimo 10%
        "max": 0.35,  # máximo 35%
        "target": 0.21,  # alvo 21%
        "tolerance": 0.06,  # ±6pp
    },
    "avg_overlap": {
        "min": 7.0,
        "max": 13.0,
        "target": 10.0,
    },
    "diversity_score": {
        "min": 0.70,
        "target": 0.78,
    },
}


def compute_structural_metrics(games: Sequence[dict[str, Any]]) -> dict[str, float]:
    """Computa métricas estruturais de um conjunto de jogos.

    Args:
        games: Lista de jogos gerados (cada jogo deve ter "numbers")

    Returns:
        Dicionário com métricas:
        - triplet_010203_pct: % de jogos com triplet 01-02-03
        - triplet_010203_count: quantidade absoluta
        - avg_overlap: overlap médio entre pares de jogos
        - games_count: total de jogos analisados
    """
    if not games:
        return {}

    # Triplet 01-02-03
    triplet_count = sum(
        1
        for game in games
        if 1 in game.get("numbers", [])
        and 2 in game.get("numbers", [])
        and 3 in game.get("numbers", [])
    )
    triplet_pct = triplet_count / len(games)

    # Overlap médio
    overlaps = []
    for i, g1 in enumerate(games):
        nums1 = set(g1.get("numbers", []))
        for g2 in games[i + 1 :]:
            nums2 = set(g2.get("numbers", []))
            overlap = len(nums1 & nums2)
            overlaps.append(overlap)
    avg_overlap = sum(overlaps) / len(overlaps) if overlaps else 0.0

    return {
        "triplet_010203_pct": round(triplet_pct, 4),
        "triplet_010203_count": triplet_count,
        "avg_overlap": round(avg_overlap, 2),
        "games_count": len(games),
    }


def validate_structural_metrics(
    metrics: dict[str, float],
    *,
    strict: bool = False,
) -> dict[str, Any]:
    """Valida métricas estruturais contra limites aceitáveis.

    Args:
        metrics: Dicionário com métricas computadas
        strict: Se True, warnings também são tratados como violações

    Returns:
        Dicionário com:
        - valid: True se não há violações
        - violations: lista de violações críticas
        - warnings: lista de alertas
        - metrics: métricas originais
    """
    violations = []
    warnings = []

    # Valida triplet 01-02-03
    triplet_pct = metrics.get("triplet_010203_pct", 0)
    triplet_limits = STRUCTURAL_LIMITS["triplet_010203_pct"]
    if triplet_pct < triplet_limits["min"]:
        violations.append(
            f"Triplet 01-02-03 muito baixo: {triplet_pct:.1%} "
            f"(mínimo: {triplet_limits['min']:.1%})"
        )
    elif triplet_pct > triplet_limits["max"]:
        violations.append(
            f"Triplet 01-02-03 muito alto: {triplet_pct:.1%} "
            f"(máximo: {triplet_limits['max']:.1%})"
        )
    elif abs(triplet_pct - triplet_limits["target"]) > triplet_limits["tolerance"]:
        warnings.append(
            f"Triplet 01-02-03 fora do alvo: {triplet_pct:.1%} "
            f"(alvo: {triplet_limits['target']:.1%} ±{triplet_limits['tolerance']:.1%})"
        )

    # Valida overlap médio
    avg_overlap = metrics.get("avg_overlap", 0)
    overlap_limits = STRUCTURAL_LIMITS["avg_overlap"]
    if avg_overlap < overlap_limits["min"]:
        violations.append(
            f"Overlap médio muito baixo: {avg_overlap:.1f} "
            f"(mínimo: {overlap_limits['min']:.1f})"
        )
    elif avg_overlap > overlap_limits["max"]:
        violations.append(
            f"Overlap médio muito alto: {avg_overlap:.1f} "
            f"(máximo: {overlap_limits['max']:.1f})"
        )

    # Em modo strict, warnings viram violações
    if strict:
        violations.extend(warnings)
        warnings = []

    return {
        "valid": len(violations) == 0,
        "violations": violations,
        "warnings": warnings,
        "metrics": metrics,
    }
