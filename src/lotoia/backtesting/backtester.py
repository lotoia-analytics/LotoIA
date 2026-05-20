from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from random import Random

from lotoia.data.loader import load_draws_csv
from lotoia.database import save_backtest_run
from lotoia.generator.basic_generator import _build_game, _is_valid_game
from lotoia.models.draw import Draw
from lotoia.statistics.combinations import combo_score, combo_stats, rank_component_score
from lotoia.statistics.scoring import (
    FINAL_SCORE_WEIGHTS,
    ScoreConfig,
    score_candidate_from_history,
    resolve_score_config,
)
from lotoia.statistics.temporal import (
    build_features,
    build_history_model,
    delay_component,
    frequency_component,
    sequence_component,
    sum_component,
)

CandidateProvider = Callable[[list[Draw], Draw, int, int, int | None], list[list[int]]]


@dataclass(frozen=True)
class BacktestResult:
    contests_analyzed: int
    games_per_contest: int
    pool_size: int
    history_window: int | None
    total_games: int
    average_hits: float
    hit_distribution: dict[str, int]
    best_game: dict[str, object] | None
    worst_game: dict[str, object] | None
    average_winner_final_score: float
    final_score_hit_correlation: float
    contest_results: list[dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        return {
            "contests_analyzed": self.contests_analyzed,
            "games_per_contest": self.games_per_contest,
            "pool_size": self.pool_size,
            "history_window": self.history_window,
            "total_games": self.total_games,
            "average_hits": self.average_hits,
            "hit_distribution": self.hit_distribution,
            "best_game": self.best_game,
            "worst_game": self.worst_game,
            "average_winner_final_score": self.average_winner_final_score,
            "final_score_hit_correlation": self.final_score_hit_correlation,
            "contest_results": self.contest_results,
        }


def _rank_component_score(average_rank: float, rank_count: int) -> float:
    return rank_component_score(average_rank, rank_count)


def _combo_stats(draws: list[Draw], combo_size: int) -> dict[tuple[int, ...], dict[str, float | int]]:
    return combo_stats(draws, combo_size)


def _combo_score(
    numbers: list[int],
    combo_size: int,
    stats: dict[tuple[int, ...], dict[str, float | int]],
) -> dict[str, float | int]:
    return combo_score(numbers, combo_size, stats)


def _delay_component(numbers: list[int], history: list[Draw]) -> float:
    return delay_component(numbers, history)


def _frequency_component(numbers: list[int], history: list[Draw]) -> float:
    return frequency_component(numbers, history)


def _sum_component(numbers: list[int]) -> float:
    return sum_component(numbers)


def _sequence_component(numbers: list[int]) -> float:
    return sequence_component(numbers)


def _build_history_model(history: list[Draw]) -> dict[str, object]:
    return build_history_model(history)


def _score_candidate(
    numbers: list[int],
    history: list[Draw],
    model: dict[str, object],
    score_config: Mapping[str, float] | ScoreConfig = FINAL_SCORE_WEIGHTS,
) -> dict[str, object]:
    return score_candidate_from_history(numbers, history, model, score_config)


def _generate_candidate_pool(
    history: list[Draw],
    target_draw: Draw,
    games_count: int,
    pool_size: int,
    seed: int | None,
) -> list[list[int]]:
    history_games = [tuple(draw.numbers) for draw in history]
    random = Random(seed + target_draw.contest if seed is not None else None)
    candidates: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()
    attempts = 0
    target_pool_size = max(pool_size, games_count)
    max_attempts = max(target_pool_size * 1000, 5000)

    while len(candidates) < target_pool_size and attempts < max_attempts:
        attempts += 1
        game = _build_game(random.sample(range(1, 26), 15))
        game_key = tuple(game["numbers"])
        if game_key in seen or not _is_valid_game(game):
            continue
        candidates.append(game["numbers"])
        seen.add(game_key)

    if len(candidates) < games_count:
        for game_key in reversed(history_games):
            if game_key in seen:
                continue
            candidates.append(sorted(game_key))
            seen.add(game_key)
            if len(candidates) >= games_count:
                break

    fallback_templates = (
        (1, 2, 4, 5, 7, 8, 10, 11, 13, 14, 16, 18, 20, 22, 24),
        (1, 3, 4, 6, 7, 9, 10, 12, 13, 15, 17, 19, 21, 23, 25),
        (2, 3, 5, 6, 8, 9, 11, 12, 14, 15, 17, 18, 20, 22, 25),
    )
    for fallback_key in fallback_templates:
        if len(candidates) >= games_count:
            break
        if fallback_key not in seen:
            candidates.append(list(fallback_key))
            seen.add(fallback_key)

    if len(candidates) < games_count:
        raise RuntimeError(
            "Nao foi possivel gerar o minimo operacional de candidatos para o backtest."
        )

    return candidates


def _hybrid_sort_key(game: dict[str, object]) -> tuple[float, int, float]:
    final_score = game["final_score"]
    quadra_score = game["quadra_score"]
    return (
        -float(final_score["final_score"]),
        -int(quadra_score["found_quadras"]),
        float(quadra_score["average_rank"]),
    )


def _pearson_correlation(first_values: list[float], second_values: list[float]) -> float:
    if len(first_values) < 2 or len(second_values) < 2:
        return 0

    first_average = sum(first_values) / len(first_values)
    second_average = sum(second_values) / len(second_values)
    numerator = sum(
        (first - first_average) * (second - second_average)
        for first, second in zip(first_values, second_values, strict=True)
    )
    first_variance = sum((value - first_average) ** 2 for value in first_values)
    second_variance = sum((value - second_average) ** 2 for value in second_values)
    denominator = (first_variance * second_variance) ** 0.5
    return numerator / denominator if denominator else 0


def _select_targets(draws: list[Draw], contests_analyzed: int | Sequence[int]) -> list[Draw]:
    ordered_draws = sorted(draws, key=lambda draw: draw.contest)
    if isinstance(contests_analyzed, int):
        if contests_analyzed < 1:
            raise ValueError("A quantidade de concursos analisados deve ser maior que zero.")
        return ordered_draws[-contests_analyzed:]

    contest_set = set(contests_analyzed)
    return [draw for draw in ordered_draws if draw.contest in contest_set]


def run_backtest(
    draws: list[Draw] | None = None,
    contests_analyzed: int | Sequence[int] = 10,
    games_count: int = 10,
    pool_size: int = 30,
    history_window: int | None = 200,
    seed: int | None = 42,
    candidate_provider: CandidateProvider | None = None,
    score_config: Mapping[str, float] | ScoreConfig | None = None,
    score_weights: Mapping[str, float] | None = None,
    persist: bool = True,
    report_path: str = "",
) -> BacktestResult:
    if games_count < 1:
        raise ValueError("A quantidade de jogos deve ser maior que zero.")
    if pool_size < games_count:
        raise ValueError("O pool de jogos deve ser maior ou igual a quantidade de jogos.")
    if history_window is not None and history_window < 1:
        raise ValueError("A janela historica deve ser maior que zero.")

    ordered_draws = sorted(draws or load_draws_csv(), key=lambda draw: draw.contest)
    targets = _select_targets(ordered_draws, contests_analyzed)
    provider = candidate_provider or _generate_candidate_pool
    resolved_score_config = resolve_score_config(score_config or score_weights)
    contest_results: list[dict[str, object]] = []
    all_games: list[dict[str, object]] = []

    for target in targets:
        feature_context = build_features(ordered_draws, target.contest)
        previous_history = feature_context.history
        if history_window is not None:
            previous_history = previous_history[-history_window:]
        if not previous_history:
            continue

        history_model = (
            feature_context.history_model
            if history_window is None
            else _build_history_model(previous_history)
        )
        candidates = provider(previous_history, target, games_count, pool_size, seed)
        scored_games = []
        for candidate_numbers in candidates:
            score_data = _score_candidate(
                sorted(candidate_numbers),
                previous_history,
                history_model,
                resolved_score_config,
            )
            scored_games.append(
                {
                    "contest": target.contest,
                    "numbers": sorted(candidate_numbers),
                    **score_data,
                }
            )

        selected_games = sorted(scored_games, key=_hybrid_sort_key)[:games_count]
        target_numbers = set(target.numbers)
        for game in selected_games:
            hits = len(set(game["numbers"]) & target_numbers)
            game["hits"] = hits
            all_games.append(game)

        contest_results.append(
            {
                "contest": target.contest,
                "cutoff_contest": feature_context.cutoff_contest,
                "history_first_contest": previous_history[0].contest,
                "history_last_contest": previous_history[-1].contest,
                "history_size": len(previous_history),
                "target_numbers": target.numbers,
                "games": selected_games,
                "best_hits": max(game["hits"] for game in selected_games),
                "average_hits": sum(game["hits"] for game in selected_games) / len(selected_games),
            }
        )

    hit_distribution = {str(points): 0 for points in range(11, 16)}
    for game in all_games:
        hits = int(game["hits"])
        if 11 <= hits <= 15:
            hit_distribution[str(hits)] += 1

    total_games = len(all_games)
    average_hits = (
        sum(int(game["hits"]) for game in all_games) / total_games if total_games else 0
    )
    best_game = max(all_games, key=lambda game: (game["hits"], game["final_score"]["final_score"]), default=None)
    worst_game = min(
        all_games,
        key=lambda game: (game["hits"], game["final_score"]["final_score"]),
        default=None,
    )
    winner_scores = [
        float(game["final_score"]["final_score"]) for game in all_games if int(game["hits"]) >= 11
    ]
    final_scores = [float(game["final_score"]["final_score"]) for game in all_games]
    hits = [float(game["hits"]) for game in all_games]

    result = BacktestResult(
        contests_analyzed=len(contest_results),
        games_per_contest=games_count,
        pool_size=pool_size,
        history_window=history_window,
        total_games=total_games,
        average_hits=average_hits,
        hit_distribution=hit_distribution,
        best_game=best_game,
        worst_game=worst_game,
        average_winner_final_score=(
            sum(winner_scores) / len(winner_scores) if winner_scores else 0
        ),
        final_score_hit_correlation=_pearson_correlation(final_scores, hits),
        contest_results=contest_results,
    )
    if persist:
        save_backtest_run(result, report_path=report_path)
    return result
