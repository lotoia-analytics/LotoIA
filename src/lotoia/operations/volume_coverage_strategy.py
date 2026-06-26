"""
M-OPS-082: Estratégia de Volume + Cobertura para maximizar 14+ acertos

Gera pool massivo (10x), calcula score de cobertura contra histórico oficial,
e seleciona top N jogos com melhor score + diversidade estrutural.
"""

from __future__ import annotations

import logging
import random
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)


def calculate_coverage_score(
    game: list[int],
    official_results: list[list[int]],
) -> tuple[float, float, int]:
    """
    Calcula score de cobertura de um jogo contra resultados oficiais.

    Returns:
        (score, avg_hits, max_hits)
    """
    game_set = set(game)
    total_hits = 0
    max_hits = 0

    for official in official_results:
        official_set = set(official)
        hits = len(game_set & official_set)
        total_hits += hits
        max_hits = max(max_hits, hits)

    avg_hits = total_hits / len(official_results) if official_results else 0
    # Score combina média + bônus por máximo
    score = avg_hits + (max_hits * 0.5)
    return score, avg_hits, max_hits


def generate_diverse_pool(
    pool_size: int,
    game_size: int,
    total_numbers: int = 25,
    seed: int | None = None,
    max_overlap: int | None = None,
) -> list[list[int]]:
    """
    Gera pool diverso com anti-clone.

    Args:
        pool_size: Tamanho do pool a gerar
        game_size: Tamanho de cada jogo (15, 17, 18, etc)
        total_numbers: Total de números disponíveis (25 para Lotofácil)
        seed: Seed para reprodutibilidade
        max_overlap: Overlap máximo permitido entre jogos (default: game_size - 3)

    Returns:
        Lista de jogos diversos
    """
    if seed is not None:
        random.seed(seed)

    if max_overlap is None:
        max_overlap = game_size - 3

    pool: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()

    attempts = 0
    max_attempts = pool_size * 10

    while len(pool) < pool_size and attempts < max_attempts:
        game = sorted(random.sample(range(1, total_numbers + 1), game_size))
        game_tuple = tuple(game)

        # Verificar se já existe
        if game_tuple in seen:
            attempts += 1
            continue

        # Verificar similaridade com últimos jogos
        is_similar = False
        game_set = set(game)
        for existing in pool[-100:]:  # Verificar últimos 100
            overlap = len(game_set & set(existing))
            if overlap > max_overlap:
                is_similar = True
                break

        if not is_similar:
            pool.append(game)
            seen.add(game_tuple)

        attempts += 1

    logger.info(
        f"Pool diverso gerado: {len(pool)} jogos em {attempts} tentativas "
        f"(target={pool_size}, max_overlap={max_overlap})"
    )

    return pool


def select_top_games_by_coverage(
    pool: list[list[int]],
    official_results: list[list[int]],
    target_count: int,
) -> list[dict[str, Any]]:
    """
    Seleciona top N jogos com melhor score de cobertura.

    Args:
        pool: Pool de jogos candidatos
        official_results: Lista de resultados oficiais para conferência
        target_count: Quantidade de jogos a selecionar

    Returns:
        Lista de jogos selecionados com scores
    """
    scored_games = []

    for game in pool:
        score, avg_hits, max_hits = calculate_coverage_score(game, official_results)
        scored_games.append(
            {
                "game": game,
                "score": score,
                "avg_hits": avg_hits,
                "max_hits": max_hits,
            }
        )

    # Ordenar por score (maior primeiro)
    scored_games.sort(key=lambda x: -x["score"])

    # Selecionar top N
    selected = scored_games[:target_count]

    logger.info(
        f"Top {len(selected)} selecionados de {len(pool)} candidatos. "
        f"Score médio: {sum(g['score'] for g in selected) / len(selected):.2f}, "
        f"Avg hits médio: {sum(g['avg_hits'] for g in selected) / len(selected):.2f}"
    )

    return selected


def apply_volume_coverage_strategy(
    target_count: int,
    game_size: int,
    official_results: list[list[int]],
    total_numbers: int = 25,
    pool_multiplier: int = 10,
    seed: int | None = None,
) -> list[dict[str, Any]]:
    """
    Aplica estratégia completa de Volume + Cobertura.

    1. Gera pool massivo (target_count * pool_multiplier)
    2. Calcula score de cobertura contra histórico oficial
    3. Seleciona top N com melhor score
    4. Retorna jogos selecionados com métricas

    Args:
        target_count: Quantidade de jogos desejada
        game_size: Tamanho de cada jogo (15, 17, 18, etc)
        official_results: Lista de resultados oficiais
        total_numbers: Total de números disponíveis
        pool_multiplier: Multiplicador do pool (default: 10x)
        seed: Seed para reprodutibilidade

    Returns:
        Lista de jogos selecionados com métricas de cobertura
    """
    pool_size = target_count * pool_multiplier

    logger.info(
        f"M-OPS-082: Iniciando estratégia Volume+Cobertura | "
        f"target={target_count}, pool_size={pool_size}, game_size={game_size}"
    )

    # 1. Gerar pool massivo
    pool = generate_diverse_pool(
        pool_size=pool_size,
        game_size=game_size,
        total_numbers=total_numbers,
        seed=seed,
    )

    if len(pool) < target_count:
        logger.warning(
            f"Pool insuficiente: {len(pool)} < {target_count}. "
            f"Retornando pool completo."
        )
        return [
            {"game": game, "score": 0, "avg_hits": 0, "max_hits": 0} for game in pool
        ]

    # 2. Selecionar top N por cobertura
    selected = select_top_games_by_coverage(
        pool=pool,
        official_results=official_results,
        target_count=target_count,
    )

    logger.info(
        f"M-OPS-082: Estratégia concluída | "
        f"Selecionados {len(selected)} jogos com score médio "
        f"{sum(g['score'] for g in selected) / len(selected):.2f}"
    )

    return selected
