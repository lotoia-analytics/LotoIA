from __future__ import annotations

import csv
from dataclasses import dataclass
import json
from pathlib import Path
from statistics import pstdev
from typing import Any

import plotly.graph_objects as go

from lotoia.backtesting import BacktestResult, run_backtest

DEFAULT_REPORTS_DIR = Path("reports")


@dataclass(frozen=True)
class ReportSummary:
    output_dir: Path
    json_path: Path
    csv_paths: dict[str, Path]
    chart_paths: dict[str, Path]
    metrics: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "output_dir": str(self.output_dir),
            "json_path": str(self.json_path),
            "csv_paths": {name: str(path) for name, path in self.csv_paths.items()},
            "chart_paths": {name: str(path) for name, path in self.chart_paths.items()},
            "metrics": self.metrics,
        }


def _all_games(result: BacktestResult) -> list[dict[str, object]]:
    return [
        game
        for contest_result in result.contest_results
        for game in contest_result["games"]
    ]


def _score(game: dict[str, object]) -> float:
    return float(game["final_score"]["final_score"])


def _hits(game: dict[str, object]) -> int:
    return int(game["hits"])


def _build_metrics(
    result: BacktestResult,
    calibration_result: dict[str, object] | None,
) -> dict[str, object]:
    games = _all_games(result)
    hits = [_hits(game) for game in games]
    best_games = sorted(games, key=lambda game: (-_hits(game), -_score(game)))[:10]
    worst_games = sorted(games, key=lambda game: (_hits(game), _score(game)))[:10]
    return {
        "summary": {
            "contests_analyzed": result.contests_analyzed,
            "games_per_contest": result.games_per_contest,
            "pool_size": result.pool_size,
            "history_window": result.history_window,
            "total_games": result.total_games,
        },
        "average_hits": result.average_hits,
        "hit_distribution": result.hit_distribution,
        "final_score_hit_correlation": result.final_score_hit_correlation,
        "best_games": best_games,
        "worst_games": worst_games,
        "stability": {
            "hit_standard_deviation": pstdev(hits) if len(hits) > 1 else 0,
            "min_hits": min(hits) if hits else 0,
            "max_hits": max(hits) if hits else 0,
        },
        "contest_history": [
            {
                "contest": contest_result["contest"],
                "best_hits": contest_result["best_hits"],
                "average_hits": contest_result["average_hits"],
                "best_final_score": max(
                    (_score(game) for game in contest_result["games"]),
                    default=0,
                ),
            }
            for contest_result in result.contest_results
        ],
        "configuration_metrics": (
            calibration_result.get("evaluations", []) if calibration_result else []
        ),
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_summary_csv(path: Path, metrics: dict[str, object]) -> None:
    summary = metrics["summary"]
    rows = [
        {"metric": "contests_analyzed", "value": summary["contests_analyzed"]},
        {"metric": "games_per_contest", "value": summary["games_per_contest"]},
        {"metric": "pool_size", "value": summary["pool_size"]},
        {"metric": "history_window", "value": summary["history_window"]},
        {"metric": "total_games", "value": summary["total_games"]},
        {"metric": "average_hits", "value": metrics["average_hits"]},
        {
            "metric": "final_score_hit_correlation",
            "value": metrics["final_score_hit_correlation"],
        },
        {
            "metric": "hit_standard_deviation",
            "value": metrics["stability"]["hit_standard_deviation"],
        },
    ]
    _write_csv(path, rows, ["metric", "value"])


def _write_games_csv(path: Path, result: BacktestResult) -> None:
    rows = []
    for contest_result in result.contest_results:
        for game in contest_result["games"]:
            rows.append(
                {
                    "contest": contest_result["contest"],
                    "numbers": "-".join(str(number) for number in game["numbers"]),
                    "hits": game["hits"],
                    "final_score": _score(game),
                    "found_quadras": game["quadra_score"]["found_quadras"],
                    "quadra_average_rank": game["quadra_score"]["average_rank"],
                }
            )
    _write_csv(
        path,
        rows,
        ["contest", "numbers", "hits", "final_score", "found_quadras", "quadra_average_rank"],
    )


def _write_contests_csv(path: Path, result: BacktestResult) -> None:
    rows = [
        {
            "contest": contest_result["contest"],
            "best_hits": contest_result["best_hits"],
            "average_hits": contest_result["average_hits"],
            "games": len(contest_result["games"]),
        }
        for contest_result in result.contest_results
    ]
    _write_csv(path, rows, ["contest", "best_hits", "average_hits", "games"])


def _write_configurations_csv(path: Path, calibration_result: dict[str, object] | None) -> None:
    evaluations = calibration_result.get("evaluations", []) if calibration_result else []
    rows = [
        {
            "configuration": evaluation["configuration"],
            "average_hits": evaluation["average_hits"],
            "correlation": evaluation["final_score_hit_correlation"],
            "hit_standard_deviation": evaluation["hit_standard_deviation"],
            "total_weight": evaluation["total_weight"],
        }
        for evaluation in evaluations
    ]
    _write_csv(
        path,
        rows,
        [
            "configuration",
            "average_hits",
            "correlation",
            "hit_standard_deviation",
            "total_weight",
        ],
    )


def _plot_hit_distribution(path: Path, result: BacktestResult) -> None:
    labels = list(result.hit_distribution)
    values = [result.hit_distribution[label] for label in labels]
    figure = go.Figure(data=[go.Bar(x=labels, y=values, marker_color="#2f6f9f")])
    figure.update_layout(
        title="Distribuicao de acertos",
        xaxis_title="Pontos",
        yaxis_title="Quantidade",
    )
    figure.write_html(path)


def _plot_final_score_evolution(path: Path, result: BacktestResult) -> None:
    contests = [item["contest"] for item in result.contest_results]
    scores = [
        max((_score(game) for game in item["games"]), default=0)
        for item in result.contest_results
    ]
    figure = go.Figure(data=[go.Scatter(x=contests, y=scores, mode="lines+markers")])
    figure.update_layout(
        title="Evolucao do final_score",
        xaxis_title="Concurso",
        yaxis_title="Melhor final_score",
    )
    figure.write_html(path)


def _plot_correlation(path: Path, result: BacktestResult) -> None:
    games = _all_games(result)
    figure = go.Figure(
        data=[
            go.Scatter(
                x=[_score(game) for game in games],
                y=[_hits(game) for game in games],
                mode="markers",
                marker={"color": "#7f4f7f"},
            )
        ]
    )
    figure.update_layout(
        title="Correlacao final_score x acertos",
        xaxis_title="final_score",
        yaxis_title="Acertos",
    )
    figure.write_html(path)


def _plot_weight_comparison(
    path: Path,
    result: BacktestResult,
    calibration_result: dict[str, object] | None,
) -> None:
    evaluations = calibration_result.get("evaluations", []) if calibration_result else []
    labels = [evaluation["configuration"] for evaluation in evaluations] or ["backtest"]
    values = [evaluation["average_hits"] for evaluation in evaluations] or [result.average_hits]
    figure = go.Figure(data=[go.Bar(x=labels, y=values, marker_color="#9f6f2f")])
    figure.update_layout(
        title="Comparacao de pesos",
        xaxis_title="Configuracao",
        yaxis_title="Media de acertos",
    )
    figure.write_html(path)


def _plot_hits_by_contest(path: Path, result: BacktestResult) -> None:
    contests = [item["contest"] for item in result.contest_results]
    best_hits = [item["best_hits"] for item in result.contest_results]
    average_hits = [item["average_hits"] for item in result.contest_results]
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=contests, y=best_hits, mode="lines+markers", name="Melhor jogo"))
    figure.add_trace(go.Scatter(x=contests, y=average_hits, mode="lines+markers", name="Media"))
    figure.update_layout(
        title="Acertos por concurso",
        xaxis_title="Concurso",
        yaxis_title="Acertos",
    )
    figure.write_html(path)


def _export_charts(
    output_dir: Path,
    result: BacktestResult,
    calibration_result: dict[str, object] | None,
) -> dict[str, Path]:
    chart_paths = {
        "hit_distribution": output_dir / "hit_distribution.html",
        "final_score_evolution": output_dir / "final_score_evolution.html",
        "correlation": output_dir / "correlation.html",
        "weight_comparison": output_dir / "weight_comparison.html",
        "hits_by_contest": output_dir / "hits_by_contest.html",
    }
    _plot_hit_distribution(chart_paths["hit_distribution"], result)
    _plot_final_score_evolution(chart_paths["final_score_evolution"], result)
    _plot_correlation(chart_paths["correlation"], result)
    _plot_weight_comparison(chart_paths["weight_comparison"], result, calibration_result)
    _plot_hits_by_contest(chart_paths["hits_by_contest"], result)
    return chart_paths


def generate_backtest_report(
    result: BacktestResult | None = None,
    calibration_result: dict[str, Any] | None = None,
    output_dir: Path = DEFAULT_REPORTS_DIR,
    report_name: str = "lotoia_backtest_report",
) -> ReportSummary:
    output_dir.mkdir(parents=True, exist_ok=True)
    backtest_result = result or run_backtest()
    metrics = _build_metrics(backtest_result, calibration_result)

    json_path = output_dir / f"{report_name}.json"
    csv_paths = {
        "summary": output_dir / f"{report_name}_summary.csv",
        "games": output_dir / f"{report_name}_games.csv",
        "contests": output_dir / f"{report_name}_contests.csv",
        "configurations": output_dir / f"{report_name}_configurations.csv",
    }
    chart_paths = _export_charts(output_dir, backtest_result, calibration_result)

    payload = {
        "metrics": metrics,
        "backtest": backtest_result.to_dict(),
        "calibration": calibration_result,
        "charts": {name: str(path) for name, path in chart_paths.items()},
        "csv": {name: str(path) for name, path in csv_paths.items()},
    }
    _write_json(json_path, payload)
    _write_summary_csv(csv_paths["summary"], metrics)
    _write_games_csv(csv_paths["games"], backtest_result)
    _write_contests_csv(csv_paths["contests"], backtest_result)
    _write_configurations_csv(csv_paths["configurations"], calibration_result)

    return ReportSummary(
        output_dir=output_dir,
        json_path=json_path,
        csv_paths=csv_paths,
        chart_paths=chart_paths,
        metrics=metrics,
    )
