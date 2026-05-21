from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TypeAlias

from lotoia.statistics.combinations import combo_score, rank_component_score
from lotoia.statistics.temporal import (
    build_history_model,
    delay_component,
    frequency_component,
    sequence_component,
    sum_component,
)
from lotoia.statistics.historical_intelligence import classify_profile, profile_score

SCORE_COMPONENTS = (
    "duo_score",
    "terno_score",
    "quadra_score",
    "quina_score",
    "delay_score",
    "frequency_score",
    "sum_score",
    "sequence_score",
)

FINAL_SCORE_WEIGHTS = MappingProxyType({
    "duo_score": 15,
    "terno_score": 20,
    "quadra_score": 25,
    "quina_score": 20,
    "delay_score": 10,
    "frequency_score": 5,
    "sum_score": 3,
    "sequence_score": 2,
})

EMPTY_FINAL_SCORE = {
    "final_score": 0,
    "components": {
        "duo_score": 0,
        "terno_score": 0,
        "quadra_score": 0,
        "quina_score": 0,
        "delay_score": 0,
        "frequency_score": 0,
        "sum_score": 0,
        "sequence_score": 0,
    },
}


ScoreWeightsInput: TypeAlias = "Mapping[str, float] | ScoreConfig"


@dataclass(frozen=True)
class ScoreConfig:
    weights: Mapping[str, float] = field(default_factory=lambda: FINAL_SCORE_WEIGHTS)
    name: str = "official"

    def __post_init__(self) -> None:
        normalized_weights = validate_score_weights(self.weights)
        object.__setattr__(self, "weights", MappingProxyType(normalized_weights))

    @property
    def total_weight(self) -> float:
        return sum(self.weights.values())

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "weights": dict(self.weights),
            "total_weight": self.total_weight,
        }


def validate_score_numbers(numbers: list[int]) -> list[int]:
    if any(number < 1 or number > 25 for number in numbers):
        raise ValueError("As dezenas devem estar entre 1 e 25.")
    return sorted(set(numbers))


def validate_score_weights(weights: Mapping[str, float]) -> dict[str, float]:
    expected_components = set(SCORE_COMPONENTS)
    received_components = set(weights)
    missing_components = sorted(expected_components - received_components)
    extra_components = sorted(received_components - expected_components)
    if missing_components or extra_components:
        details = []
        if missing_components:
            details.append(f"ausentes: {', '.join(missing_components)}")
        if extra_components:
            details.append(f"desconhecidos: {', '.join(extra_components)}")
        raise ValueError(f"Pesos de score invalidos ({'; '.join(details)}).")

    normalized_weights = {name: float(weights[name]) for name in SCORE_COMPONENTS}
    negative_weights = [name for name, value in normalized_weights.items() if value < 0]
    if negative_weights:
        raise ValueError(f"Pesos de score invalidos. Valores negativos: {', '.join(negative_weights)}")
    if sum(normalized_weights.values()) <= 0:
        raise ValueError("A soma dos pesos de score deve ser maior que zero.")

    return normalized_weights


def resolve_score_config(config: ScoreWeightsInput | None = None) -> ScoreConfig:
    if config is None:
        return ScoreConfig()
    if isinstance(config, ScoreConfig):
        return config
    return ScoreConfig(weights=config, name="custom")


def weighted_final_score(
    components: dict[str, float],
    weights: ScoreWeightsInput = FINAL_SCORE_WEIGHTS,
) -> float:
    score_weights = resolve_score_config(weights).weights
    total_weight = sum(score_weights.values())
    weighted_score = sum(components[name] * weight for name, weight in score_weights.items())
    return round(weighted_score / total_weight, 2)


def score_candidate_from_history(
    numbers: list[int],
    history,
    model: dict[str, object] | None = None,
    weights: ScoreWeightsInput = FINAL_SCORE_WEIGHTS,
) -> dict[str, object]:
    score_weights = resolve_score_config(weights).weights
    history_model = model or build_history_model(history)
    combo_scores = {
        "duo": combo_score(numbers, 2, history_model["duos"]),
        "terno": combo_score(numbers, 3, history_model["ternos"]),
        "quadra": combo_score(numbers, 4, history_model["quadras"]),
        "quina": combo_score(numbers, 5, history_model["quinas"]),
    }
    components = {
        "duo_score": rank_component_score(combo_scores["duo"]["average_rank"], 300),
        "terno_score": rank_component_score(combo_scores["terno"]["average_rank"], 2300),
        "quadra_score": rank_component_score(combo_scores["quadra"]["average_rank"], 12650),
        "quina_score": rank_component_score(combo_scores["quina"]["average_rank"], 53130),
        "delay_score": delay_component(numbers, history),
        "frequency_score": frequency_component(numbers, history),
        "sum_score": sum_component(numbers),
        "sequence_score": sequence_component(numbers),
    }
    final_score = sum(
        components[name] * weight for name, weight in score_weights.items()
    ) / sum(
        score_weights.values()
    )
    quadra_score = combo_scores["quadra"]
    profile_type = classify_profile(numbers, history)
    historical_intelligence = profile_score(numbers, history, profile_type)
    return {
        "final_score": {"final_score": round(final_score, 2), "components": components},
        "quadra_score": {
            "found_quadras": quadra_score["found"],
            "total_frequency": quadra_score["total_count"],
            "average_frequency": quadra_score["average_count"],
            "average_rank": quadra_score["average_rank"],
            "top_quadras": [],
        },
        "historical_intelligence": historical_intelligence,
        "profile_type": profile_type,
        "profile_score": historical_intelligence["profile_score"],
    }
