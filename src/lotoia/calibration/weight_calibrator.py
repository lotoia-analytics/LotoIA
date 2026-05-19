from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from statistics import pstdev

from lotoia.backtesting import BacktestResult, run_backtest
from lotoia.backtesting.backtester import CandidateProvider
from lotoia.database import save_calibration_run
from lotoia.models.draw import Draw
from lotoia.statistics.scoring import ScoreConfig

CALIBRATABLE_COMPONENTS = {
    "duo_score": "duo",
    "terno_score": "terno",
    "quadra_score": "quadra",
    "quina_score": "quina",
    "delay_score": "delay",
    "frequency_score": "frequency",
    "sum_score": "sum",
    "sequence_score": "sequence",
}


@dataclass(frozen=True)
class WeightConfiguration:
    name: str
    duo: float
    terno: float
    quadra: float
    quina: float
    delay: float
    frequency: float
    sum: float
    sequence: float

    def to_score_weights(self) -> dict[str, float]:
        return {
            "duo_score": self.duo,
            "terno_score": self.terno,
            "quadra_score": self.quadra,
            "quina_score": self.quina,
            "delay_score": self.delay,
            "frequency_score": self.frequency,
            "sum_score": self.sum,
            "sequence_score": self.sequence,
        }

    @property
    def total_weight(self) -> float:
        return sum(self.to_score_weights().values())


def _validate_configuration(configuration: WeightConfiguration) -> None:
    weights = configuration.to_score_weights()
    negative_weights = [name for name, value in weights.items() if value < 0]
    if negative_weights:
        joined_names = ", ".join(negative_weights)
        raise ValueError(f"Pesos invalidos. Valores negativos: {joined_names}")
    if configuration.total_weight <= 0:
        raise ValueError("A soma total dos pesos deve ser maior que zero.")


def _hits_standard_deviation(result: BacktestResult) -> float:
    hits = [
        float(game["hits"])
        for contest_result in result.contest_results
        for game in contest_result["games"]
    ]
    return pstdev(hits) if len(hits) > 1 else 0


def _best_game_scores_average(result: BacktestResult) -> float:
    best_scores = [
        float(max(contest_result["games"], key=lambda game: game["hits"])["final_score"]["final_score"])
        for contest_result in result.contest_results
        if contest_result["games"]
    ]
    return sum(best_scores) / len(best_scores) if best_scores else 0


def _metrics_from_result(
    configuration: WeightConfiguration,
    result: BacktestResult,
) -> dict[str, object]:
    return {
        "configuration": configuration.name,
        "weights": configuration.to_score_weights(),
        "total_weight": configuration.total_weight,
        "contests_analyzed": result.contests_analyzed,
        "total_games": result.total_games,
        "average_hits": result.average_hits,
        "hit_distribution": result.hit_distribution,
        "final_score_hit_correlation": result.final_score_hit_correlation,
        "average_best_game_final_score": _best_game_scores_average(result),
        "hit_standard_deviation": _hits_standard_deviation(result),
        "backtest": result.to_dict(),
    }


def evaluate_weight_configuration(
    configuration: WeightConfiguration,
    draws: list[Draw] | None = None,
    contests_analyzed: int | Sequence[int] = 10,
    games_count: int = 10,
    pool_size: int = 30,
    history_window: int | None = 200,
    seed: int | None = 42,
    candidate_provider: CandidateProvider | None = None,
    persist: bool = True,
    report_path: str = "",
) -> dict[str, object]:
    _validate_configuration(configuration)
    result = run_backtest(
        draws=draws,
        contests_analyzed=contests_analyzed,
        games_count=games_count,
        pool_size=pool_size,
        history_window=history_window,
        seed=seed,
        candidate_provider=candidate_provider,
        score_config=ScoreConfig(
            weights=configuration.to_score_weights(),
            name=configuration.name,
        ),
        persist=False,
    )
    metrics = _metrics_from_result(configuration, result)
    if persist:
        save_calibration_run(metrics, report_path=report_path)
    return metrics


def compare_weight_configurations(
    configurations: Sequence[WeightConfiguration],
    draws: list[Draw] | None = None,
    contests_analyzed: int | Sequence[int] = 10,
    games_count: int = 10,
    pool_size: int = 30,
    history_window: int | None = 200,
    seed: int | None = 42,
    candidate_provider: CandidateProvider | None = None,
    persist: bool = True,
    report_path: str = "",
) -> dict[str, object]:
    if not configurations:
        raise ValueError("Informe ao menos uma configuracao de pesos.")

    evaluations = [
        evaluate_weight_configuration(
            configuration=configuration,
            draws=draws,
            contests_analyzed=contests_analyzed,
            games_count=games_count,
            pool_size=pool_size,
            history_window=history_window,
            seed=seed,
            candidate_provider=candidate_provider,
            persist=persist,
            report_path=report_path,
        )
        for configuration in configurations
    ]
    best_evaluation = max(
        evaluations,
        key=lambda evaluation: (
            evaluation["average_hits"],
            evaluation["hit_distribution"]["15"],
            evaluation["hit_distribution"]["14"],
            evaluation["hit_distribution"]["13"],
            evaluation["final_score_hit_correlation"],
        ),
    )

    return {
        "evaluations": evaluations,
        "best_configuration": best_evaluation["configuration"],
        "best_metrics": best_evaluation,
    }
