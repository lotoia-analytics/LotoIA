from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import dataclass
import json
from pathlib import Path
from random import Random
from statistics import pstdev

import plotly.graph_objects as go

from lotoia.backtesting.backtester import (
    _build_history_model,
    _hybrid_sort_key,
    _pearson_correlation,
    _score_candidate,
    _select_targets,
)
from lotoia.data.loader import load_draws_csv
from lotoia.database import save_benchmark_run
from lotoia.generator.basic_generator import _build_game, _is_valid_game
from lotoia.models.draw import Draw
from lotoia.statistics.temporal import build_features

STRATEGY_LOTOIA = "lotoia_engine"
STRATEGY_FILTERED_RANDOM = "filtered_random"
STRATEGY_PURE_RANDOM = "pure_random"
STRATEGIES = (STRATEGY_LOTOIA, STRATEGY_FILTERED_RANDOM, STRATEGY_PURE_RANDOM)
DEFAULT_BENCHMARK_DIR = Path("reports/benchmark")


@dataclass(frozen=True)
class BenchmarkResult:
    contests_analyzed: int
    games_per_contest: int
    pool_size: int
    history_window: int | None
    strategies: dict[str, dict[str, object]]
    comparisons: dict[str, dict[str, object]]
    contest_results: list[dict[str, object]]
    report_paths: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return {
            "contests_analyzed": self.contests_analyzed,
            "games_per_contest": self.games_per_contest,
            "pool_size": self.pool_size,
            "history_window": self.history_window,
            "strategies": self.strategies,
            "comparisons": self.comparisons,
            "contest_results": self.contest_results,
            "report_paths": self.report_paths,
        }


def _hits(game: dict[str, object]) -> int:
    return int(game["hits"])


def _score(game: dict[str, object]) -> float:
    final_score = game.get("final_score")
    if isinstance(final_score, dict):
        return float(final_score.get("final_score", 0))
    return 0


def _history_for_target(
    draws: list[Draw],
    target: Draw,
    history_window: int | None,
) -> list[Draw]:
    feature_context = build_features(draws, target.contest)
    history = feature_context.history
    return history[-history_window:] if history_window is not None else history


def _generate_filtered_candidates(pool_size: int, random: Random) -> list[list[int]]:
    candidates: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()
    attempts = 0
    max_attempts = pool_size * 10000

    while len(candidates) < pool_size and attempts < max_attempts:
        attempts += 1
        game = _build_game(random.sample(range(1, 26), 15))
        game_key = tuple(game["numbers"])
        if game_key in seen or not _is_valid_game(game):
            continue
        candidates.append(game["numbers"])
        seen.add(game_key)

    if len(candidates) < pool_size:
        raise RuntimeError("Nao foi possivel gerar candidatos filtrados suficientes.")

    return candidates


def _generate_pure_candidates(games_count: int, random: Random) -> list[list[int]]:
    candidates: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()
    attempts = 0
    max_attempts = games_count * 1000

    while len(candidates) < games_count and attempts < max_attempts:
        attempts += 1
        numbers = sorted(random.sample(range(1, 26), 15))
        game_key = tuple(numbers)
        if game_key in seen:
            continue
        candidates.append(numbers)
        seen.add(game_key)

    if len(candidates) < games_count:
        raise RuntimeError("Nao foi possivel gerar jogos aleatorios puros suficientes.")

    return candidates


def _score_lotoia_games(
    candidates: list[list[int]],
    target: Draw,
    history: list[Draw],
) -> list[dict[str, object]]:
    history_model = _build_history_model(history)
    games = []
    for numbers in candidates:
        score_data = _score_candidate(sorted(numbers), history, history_model)
        games.append(
            {
                "contest": target.contest,
                "numbers": sorted(numbers),
                "strategy": STRATEGY_LOTOIA,
                **score_data,
            }
        )
    return games


def _build_unscored_games(
    candidates: list[list[int]],
    target: Draw,
    strategy: str,
) -> list[dict[str, object]]:
    return [
        {
            "contest": target.contest,
            "numbers": sorted(numbers),
            "strategy": strategy,
        }
        for numbers in candidates
    ]


def _apply_hits(games: list[dict[str, object]], target: Draw) -> list[dict[str, object]]:
    target_numbers = set(target.numbers)
    for game in games:
        game["hits"] = len(set(game["numbers"]) & target_numbers)
    return games


def _hit_distribution(games: list[dict[str, object]]) -> dict[str, int]:
    distribution = {str(points): 0 for points in range(11, 16)}
    for game in games:
        hits = _hits(game)
        if 11 <= hits <= 15:
            distribution[str(hits)] += 1
    return distribution


def _rolling_windows(values: list[float], window_size: int) -> list[dict[str, float | int]]:
    if not values:
        return []
    window_size = max(1, window_size)
    windows = []
    for start in range(0, len(values), window_size):
        chunk = values[start : start + window_size]
        windows.append(
            {
                "start_index": start + 1,
                "end_index": start + len(chunk),
                "average_hits": sum(chunk) / len(chunk),
                "standard_deviation": pstdev(chunk) if len(chunk) > 1 else 0,
            }
        )
    return windows


def _strategy_metrics(
    strategy: str,
    games: list[dict[str, object]],
    contest_results: list[dict[str, object]],
    stability_window: int,
) -> dict[str, object]:
    hits = [_hits(game) for game in games]
    scores = [_score(game) for game in games]
    contest_averages = [
        float(contest_result["strategy_results"][strategy]["average_hits"])
        for contest_result in contest_results
    ]
    return {
        "total_games": len(games),
        "average_hits": sum(hits) / len(hits) if hits else 0,
        "hit_distribution": _hit_distribution(games),
        "standard_deviation": pstdev(hits) if len(hits) > 1 else 0,
        "stability": {
            "min_hits": min(hits) if hits else 0,
            "max_hits": max(hits) if hits else 0,
            "contest_average_standard_deviation": (
                pstdev(contest_averages) if len(contest_averages) > 1 else 0
            ),
            "windows": _rolling_windows(contest_averages, stability_window),
        },
        "final_score_hit_correlation": _pearson_correlation(scores, [float(hit) for hit in hits])
        if any(scores)
        else 0,
        "best_game": max(games, key=lambda game: (_hits(game), _score(game)), default=None),
        "worst_game": min(games, key=lambda game: (_hits(game), _score(game)), default=None),
    }


def _average_ranks(contest_results: list[dict[str, object]]) -> dict[str, float]:
    rank_totals = {strategy: 0.0 for strategy in STRATEGIES}
    for contest_result in contest_results:
        ranked = sorted(
            STRATEGIES,
            key=lambda strategy: (
                -float(contest_result["strategy_results"][strategy]["average_hits"]),
                strategy,
            ),
        )
        for rank, strategy in enumerate(ranked, start=1):
            rank_totals[strategy] += rank
    return {
        strategy: rank_totals[strategy] / len(contest_results) if contest_results else 0
        for strategy in STRATEGIES
    }


def _comparison_metrics(contest_results: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    comparisons = {}
    average_ranks = _average_ranks(contest_results)
    for competitor in (STRATEGY_FILTERED_RANDOM, STRATEGY_PURE_RANDOM):
        differences = []
        wins = 0
        for contest_result in contest_results:
            lotoia_average = float(
                contest_result["strategy_results"][STRATEGY_LOTOIA]["average_hits"]
            )
            competitor_average = float(
                contest_result["strategy_results"][competitor]["average_hits"]
            )
            difference = lotoia_average - competitor_average
            differences.append(difference)
            if difference > 0:
                wins += 1

        comparison_name = f"{STRATEGY_LOTOIA}_vs_{competitor}"
        comparisons[comparison_name] = {
            "average_hit_difference": (
                sum(differences) / len(differences) if differences else 0
            ),
            "superiority_rate": wins / len(differences) if differences else 0,
            "lotoia_average_rank": average_ranks[STRATEGY_LOTOIA],
            "competitor_average_rank": average_ranks[competitor],
        }
    return comparisons


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _export_csv(output_dir: Path, result: BenchmarkResult) -> dict[str, str]:
    summary_rows = [
        {
            "strategy": strategy,
            "average_hits": metrics["average_hits"],
            "standard_deviation": metrics["standard_deviation"],
            "correlation": metrics["final_score_hit_correlation"],
            "total_games": metrics["total_games"],
        }
        for strategy, metrics in result.strategies.items()
    ]
    contests_rows = []
    for contest_result in result.contest_results:
        for strategy in STRATEGIES:
            strategy_result = contest_result["strategy_results"][strategy]
            contests_rows.append(
                {
                    "contest": contest_result["contest"],
                    "strategy": strategy,
                    "average_hits": strategy_result["average_hits"],
                    "best_hits": strategy_result["best_hits"],
                    "worst_hits": strategy_result["worst_hits"],
                }
            )

    summary_path = output_dir / "benchmark_summary.csv"
    contests_path = output_dir / "benchmark_contests.csv"
    _write_csv(
        summary_path,
        summary_rows,
        ["strategy", "average_hits", "standard_deviation", "correlation", "total_games"],
    )
    _write_csv(
        contests_path,
        contests_rows,
        ["contest", "strategy", "average_hits", "best_hits", "worst_hits"],
    )
    return {"summary_csv": str(summary_path), "contests_csv": str(contests_path)}


def _comparison_chart(path: Path, result: BenchmarkResult) -> None:
    figure = go.Figure(
        data=[
            go.Bar(
                x=list(result.strategies),
                y=[metrics["average_hits"] for metrics in result.strategies.values()],
                marker_color=["#2563eb", "#0f766e", "#9f6f2f"],
            )
        ]
    )
    figure.update_layout(
        title="Media de acertos por estrategia",
        xaxis_title="Estrategia",
        yaxis_title="Media de acertos",
    )
    figure.write_html(path)


def _evolution_chart(path: Path, result: BenchmarkResult) -> None:
    figure = go.Figure()
    contests = [contest_result["contest"] for contest_result in result.contest_results]
    for strategy in STRATEGIES:
        figure.add_trace(
            go.Scatter(
                x=contests,
                y=[
                    contest_result["strategy_results"][strategy]["average_hits"]
                    for contest_result in result.contest_results
                ],
                mode="lines+markers",
                name=strategy,
            )
        )
    figure.update_layout(
        title="Evolucao historica por estrategia",
        xaxis_title="Concurso",
        yaxis_title="Media de acertos",
    )
    figure.write_html(path)


def _export_report(output_dir: Path, result: BenchmarkResult) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "benchmark_result.json"
    comparison_chart_path = output_dir / "benchmark_comparison.html"
    evolution_chart_path = output_dir / "benchmark_evolution.html"

    _write_json(json_path, result.to_dict())
    csv_paths = _export_csv(output_dir, result)
    _comparison_chart(comparison_chart_path, result)
    _evolution_chart(evolution_chart_path, result)
    return {
        "json": str(json_path),
        "comparison_chart": str(comparison_chart_path),
        "evolution_chart": str(evolution_chart_path),
        **csv_paths,
    }


def run_benchmark(
    draws: list[Draw] | None = None,
    contests_analyzed: int | Sequence[int] = 10,
    games_count: int = 10,
    pool_size: int = 30,
    history_window: int | None = 200,
    seed: int | None = 42,
    stability_window: int = 5,
    output_dir: Path = DEFAULT_BENCHMARK_DIR,
    write_report: bool = True,
    persist: bool = True,
) -> BenchmarkResult:
    if games_count < 1:
        raise ValueError("A quantidade de jogos deve ser maior que zero.")
    if pool_size < games_count:
        raise ValueError("O pool deve ser maior ou igual a quantidade de jogos.")
    if history_window is not None and history_window < 1:
        raise ValueError("A janela historica deve ser maior que zero.")
    if stability_window < 1:
        raise ValueError("A janela de estabilidade deve ser maior que zero.")

    ordered_draws = sorted(draws or load_draws_csv(), key=lambda draw: draw.contest)
    targets = _select_targets(ordered_draws, contests_analyzed)
    contest_results: list[dict[str, object]] = []
    all_games = {strategy: [] for strategy in STRATEGIES}

    for target in targets:
        history = _history_for_target(ordered_draws, target, history_window)
        if not history:
            continue

        base_seed = seed + target.contest if seed is not None else None
        lotoia_pool = _generate_filtered_candidates(pool_size, Random(base_seed))
        filtered_pool = _generate_filtered_candidates(games_count, Random(None if base_seed is None else base_seed + 1))
        pure_pool = _generate_pure_candidates(games_count, Random(None if base_seed is None else base_seed + 2))

        lotoia_scored = _score_lotoia_games(lotoia_pool, target, history)
        lotoia_selected = sorted(lotoia_scored, key=_hybrid_sort_key)[:games_count]
        filtered_selected = _build_unscored_games(
            filtered_pool,
            target,
            STRATEGY_FILTERED_RANDOM,
        )
        pure_selected = _build_unscored_games(pure_pool, target, STRATEGY_PURE_RANDOM)

        selected_by_strategy = {
            STRATEGY_LOTOIA: _apply_hits(lotoia_selected, target),
            STRATEGY_FILTERED_RANDOM: _apply_hits(filtered_selected, target),
            STRATEGY_PURE_RANDOM: _apply_hits(pure_selected, target),
        }

        strategy_results = {}
        for strategy, games in selected_by_strategy.items():
            hits = [_hits(game) for game in games]
            strategy_results[strategy] = {
                "average_hits": sum(hits) / len(hits) if hits else 0,
                "best_hits": max(hits) if hits else 0,
                "worst_hits": min(hits) if hits else 0,
                "games": games,
            }
            all_games[strategy].extend(games)

        contest_results.append(
            {
                "contest": target.contest,
                "cutoff_contest": target.contest,
                "history_size": len(history),
                "history_first_contest": history[0].contest,
                "history_last_contest": history[-1].contest,
                "target_numbers": target.numbers,
                "strategy_results": strategy_results,
            }
        )

    strategies = {
        strategy: _strategy_metrics(
            strategy,
            all_games[strategy],
            contest_results,
            stability_window,
        )
        for strategy in STRATEGIES
    }
    comparisons = _comparison_metrics(contest_results)

    result = BenchmarkResult(
        contests_analyzed=len(contest_results),
        games_per_contest=games_count,
        pool_size=pool_size,
        history_window=history_window,
        strategies=strategies,
        comparisons=comparisons,
        contest_results=contest_results,
        report_paths={},
    )

    if write_report:
        report_paths = _export_report(output_dir, result)
        result = BenchmarkResult(
            contests_analyzed=result.contests_analyzed,
            games_per_contest=result.games_per_contest,
            pool_size=result.pool_size,
            history_window=result.history_window,
            strategies=result.strategies,
            comparisons=result.comparisons,
            contest_results=result.contest_results,
            report_paths=report_paths,
        )
        _write_json(output_dir / "benchmark_result.json", result.to_dict())

    if persist:
        save_benchmark_run(
            result,
            seed=seed,
            report_path=result.report_paths.get("json", ""),
        )

    return result
