from __future__ import annotations

from pathlib import Path
from statistics import pstdev
from typing import Any

from lotoia.database.database import (
    DEFAULT_DATABASE_PATH,
    BacktestRun,
    BenchmarkRun,
    CalibrationRun,
    get_session,
)

RUN_MODELS = {
    "benchmark": BenchmarkRun,
    "backtest": BacktestRun,
    "calibration": CalibrationRun,
}


def _model_to_dict(model) -> dict[str, Any]:
    return {
        column.name: getattr(model, column.name)
        for column in model.__table__.columns
    }


def _backtest_stability(result) -> dict[str, float | int]:
    hits = [
        int(game["hits"])
        for contest_result in result.contest_results
        for game in contest_result["games"]
    ]
    return {
        "standard_deviation": pstdev(hits) if len(hits) > 1 else 0,
        "min_hits": min(hits) if hits else 0,
        "max_hits": max(hits) if hits else 0,
    }


def save_benchmark_run(
    result,
    seed: int | None = None,
    report_path: str = "",
    db_path: Path = DEFAULT_DATABASE_PATH,
) -> int:
    lotoia_metrics = result.strategies["lotoia_engine"]
    filtered_metrics = result.strategies["filtered_random"]
    random_metrics = result.strategies["pure_random"]
    filtered_comparison = result.comparisons["lotoia_engine_vs_filtered_random"]
    random_comparison = result.comparisons["lotoia_engine_vs_pure_random"]
    average_advantage = (
        float(filtered_comparison["average_hit_difference"])
        + float(random_comparison["average_hit_difference"])
    ) / 2
    superiority_rate = (
        float(filtered_comparison["superiority_rate"])
        + float(random_comparison["superiority_rate"])
    ) / 2

    with get_session(db_path) as session:
        run = BenchmarkRun(
            contests=result.contests_analyzed,
            games_per_contest=result.games_per_contest,
            pool_size=result.pool_size,
            history_window=result.history_window,
            seed=seed,
            lotoia_average_hits=float(lotoia_metrics["average_hits"]),
            filtered_average_hits=float(filtered_metrics["average_hits"]),
            random_average_hits=float(random_metrics["average_hits"]),
            superiority_rate=superiority_rate,
            average_advantage=average_advantage,
            standard_deviation=float(lotoia_metrics["standard_deviation"]),
            report_path=report_path,
            payload=result.to_dict(),
        )
        session.add(run)
        session.commit()
        return int(run.id)


def save_backtest_run(
    result,
    report_path: str = "",
    db_path: Path = DEFAULT_DATABASE_PATH,
) -> int:
    with get_session(db_path) as session:
        run = BacktestRun(
            contests=result.contests_analyzed,
            games_per_contest=result.games_per_contest,
            average_hits=float(result.average_hits),
            hit_distribution=result.hit_distribution,
            correlation=float(result.final_score_hit_correlation),
            stability=_backtest_stability(result),
            best_game=result.best_game,
            worst_game=result.worst_game,
            report_path=report_path,
            payload=result.to_dict(),
        )
        session.add(run)
        session.commit()
        return int(run.id)


def save_calibration_run(
    evaluation: dict[str, Any],
    report_path: str = "",
    db_path: Path = DEFAULT_DATABASE_PATH,
) -> int:
    with get_session(db_path) as session:
        run = CalibrationRun(
            weight_configuration={
                "configuration": evaluation["configuration"],
                "weights": evaluation["weights"],
                "total_weight": evaluation["total_weight"],
            },
            average_hits=float(evaluation["average_hits"]),
            correlation=float(evaluation["final_score_hit_correlation"]),
            stability={
                "standard_deviation": evaluation["hit_standard_deviation"],
            },
            report_path=report_path,
            payload=evaluation,
        )
        session.add(run)
        session.commit()
        return int(run.id)


def list_runs(run_type: str | None = None, db_path: Path = DEFAULT_DATABASE_PATH) -> dict[str, list[dict[str, Any]]] | list[dict[str, Any]]:
    with get_session(db_path) as session:
        if run_type:
            model = RUN_MODELS[run_type]
            return [
                _model_to_dict(run)
                for run in session.query(model).order_by(model.created_at.desc()).all()
            ]

        return {
            name: [
                _model_to_dict(run)
                for run in session.query(model).order_by(model.created_at.desc()).all()
            ]
            for name, model in RUN_MODELS.items()
        }


def get_run_by_id(
    run_type: str,
    run_id: int,
    db_path: Path = DEFAULT_DATABASE_PATH,
) -> dict[str, Any] | None:
    with get_session(db_path) as session:
        model = RUN_MODELS[run_type]
        run = session.get(model, run_id)
        return _model_to_dict(run) if run else None
