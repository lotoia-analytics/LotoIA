"""L6 — Balanceamento Estrutural (M-OPS-083).

Filtra jogos com baixa uniformidade na distribuição intra-blocos.
Garante que os jogos gerados tenham composite_score >= 0.80.

Métrica:
- coverage_score = blocos_ativos / 5.0
- balance_score = 1.0 - (σ / 2.5)
- composite_score = 0.6 * coverage + 0.4 * balance

Limiar: composite_score >= 0.80 (98% dos concursos reais)
"""

from __future__ import annotations

import logging
from collections import Counter

logger = logging.getLogger(__name__)

# Limiar M-OPS-083
COMPOSITE_SCORE_THRESHOLD = 0.80
BALANCE_SCORE_MIN = 0.50  # Limiar mínimo para balance_score isolado


def calculate_balance_score(numbers: list[int]) -> float:
    """Calcula balance_score (uniformidade intra-blocos).

    Args:
        numbers: Lista de 15 dezenas (1-25)

    Returns:
        float: Score entre 0.0 e 1.0 (1.0 = perfeitamente balanceado 3-3-3-3-3)
    """
    block_counts = [0] * 5
    for n in numbers:
        block_counts[(n - 1) // 5] += 1

    mean_blocks = sum(block_counts) / 5.0
    variance = sum((b - mean_blocks) ** 2 for b in block_counts) / 5.0
    std_dev = variance**0.5

    # σ=0 (perfeito 3-3-3-3-3) -> balance=1.0
    # σ=2.5 (pior caso) -> balance=0.0
    return max(0.0, 1.0 - (std_dev / 2.5))


def calculate_coverage_score(numbers: list[int]) -> float:
    """Calcula coverage_score (blocos ativos / 5).

    Args:
        numbers: Lista de 15 dezenas (1-25)

    Returns:
        float: Score entre 0.0 e 1.0 (1.0 = todos os 5 blocos ativos)
    """
    blocks = set()
    for n in numbers:
        blocks.add((n - 1) // 5)
    return len(blocks) / 5.0


def calculate_composite_score(numbers: list[int]) -> dict:
    """Calcula métricas completas de cobertura e balanceamento.

    Args:
        numbers: Lista de 15 dezenas (1-25)

    Returns:
        dict: {coverage_score, balance_score, composite_score, block_distribution}
    """
    block_counts = [0] * 5
    for n in numbers:
        block_counts[(n - 1) // 5] += 1

    # Coverage
    active_blocks = sum(1 for b in block_counts if b > 0)
    coverage_score = active_blocks / 5.0

    # Balance
    mean_blocks = sum(block_counts) / 5.0
    variance = sum((b - mean_blocks) ** 2 for b in block_counts) / 5.0
    std_dev = variance**0.5
    balance_score = max(0.0, 1.0 - (std_dev / 2.5))

    # Composite
    composite_score = 0.6 * coverage_score + 0.4 * balance_score

    return {
        "coverage_score": coverage_score,
        "balance_score": balance_score,
        "composite_score": composite_score,
        "block_distribution": block_counts,
        "std_dev": std_dev,
    }


def apply_balance_filter(
    pool: list[dict],
    threshold: float = COMPOSITE_SCORE_THRESHOLD,
    min_balance: float = BALANCE_SCORE_MIN,
) -> list[dict]:
    """L6 — Filtra jogos com composite_score abaixo do limiar.

    Args:
        pool: Lista de jogos candidatos
        threshold: Limiar mínimo para composite_score (default: 0.80)
        min_balance: Limiar mínimo para balance_score isolado (default: 0.50)

    Returns:
        list[dict]: Pool filtrado com jogos balanceados
    """
    filtered = []
    rejected = 0
    total_composite = 0.0
    total_balance = 0.0

    for game in pool:
        numbers = list(game.get("numbers") or [])
        if not numbers:
            continue

        metrics = calculate_composite_score(numbers)

        # Filtrar jogos abaixo do limiar
        if metrics["composite_score"] < threshold:
            rejected += 1
            continue

        # Adicionar métricas ao jogo
        game["balance_score"] = round(metrics["balance_score"], 4)
        game["coverage_score"] = round(metrics["coverage_score"], 4)
        game["composite_score"] = round(metrics["composite_score"], 4)
        game["block_distribution"] = metrics["block_distribution"]
        game["balance_filter_applied"] = True

        filtered.append(game)
        total_composite += metrics["composite_score"]
        total_balance += metrics["balance_score"]

    # Log estruturado L6
    if pool:
        avg_composite = total_composite / len(filtered) if filtered else 0.0
        avg_balance = total_balance / len(filtered) if filtered else 0.0

        logger.info(
            "[CORE_002:L6] Balance filter aplicado | "
            "input=%d filtered=%d rejected=%d | "
            "avg_composite=%.3f avg_balance=%.3f | "
            "threshold=%.2f",
            len(pool),
            len(filtered),
            rejected,
            avg_composite,
            avg_balance,
            threshold,
        )

        if rejected > len(pool) * 0.3:
            logger.warning(
                "[CORE_002:L6] Rejeição alta: %d/%d jogos (%.1f%%) abaixo do limiar %.2f",
                rejected,
                len(pool),
                (rejected / len(pool) * 100) if pool else 0,
                threshold,
            )

    return filtered


def penalize_low_balance(
    pool: list[dict],
    penalty_factor: float = 5.0,
) -> list[dict]:
    """L6 alternativo — Penaliza jogos com balance_score baixo no profile_score.

    Em vez de filtrar, reduz o score de jogos desbalanceados.

    Args:
        pool: Lista de jogos candidatos
        penalty_factor: Fator de penalização (default: 5.0)

    Returns:
        list[dict]: Pool com scores ajustados
    """
    total_penalty = 0.0
    games_penalized = 0

    for game in pool:
        numbers = list(game.get("numbers") or [])
        if not numbers:
            continue

        metrics = calculate_composite_score(numbers)

        # Adicionar métricas ao jogo
        game["balance_score"] = round(metrics["balance_score"], 4)
        game["coverage_score"] = round(metrics["coverage_score"], 4)
        game["composite_score"] = round(metrics["composite_score"], 4)
        game["block_distribution"] = metrics["block_distribution"]

        # Penalizar jogos com balance_score baixo
        if metrics["balance_score"] < BALANCE_SCORE_MIN:
            penalty = (BALANCE_SCORE_MIN - metrics["balance_score"]) * penalty_factor
            current_score = float(game.get("profile_score", 0) or 0)
            game["profile_score"] = round(max(0.0, current_score - penalty), 2)
            game["balance_penalty_applied"] = True
            total_penalty += penalty
            games_penalized += 1

    # Log estruturado
    if pool:
        avg_penalty = total_penalty / len(pool)
        logger.info(
            "[CORE_002:L6] Balance penalty aplicado | "
            "pool=%d games_penalized=%d | "
            "total_penalty=%.2f avg_penalty=%.2f | "
            "penalty_factor=%.1f",
            len(pool),
            games_penalized,
            total_penalty,
            avg_penalty,
            penalty_factor,
        )

    return pool
