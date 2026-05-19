from functools import lru_cache
from itertools import combinations
import json
import logging
from pathlib import Path
from typing import Protocol

from lotoia.statistics.combinations import rank_component_score
from lotoia.statistics.scoring import (
    EMPTY_FINAL_SCORE,
    FINAL_SCORE_WEIGHTS,
    validate_score_numbers,
    weighted_final_score,
)
from lotoia.statistics.temporal import (
    CENTER_NUMBERS,
    calculate_delays,
    calculate_hot_cold_numbers,
    calculate_repeated_numbers,
    calculate_sequence_stats,
    find_sequences,
)

logger = logging.getLogger(__name__)

__all__ = [
    "CENTER_NUMBERS",
    "EMPTY_FINAL_SCORE",
    "FINAL_SCORE_WEIGHTS",
    "calculate_column_distribution",
    "calculate_delay_score",
    "calculate_delays",
    "calculate_duo_score",
    "calculate_final_score",
    "calculate_frame_center_distribution",
    "calculate_hot_cold_numbers",
    "calculate_line_distribution",
    "calculate_quadra_score",
    "calculate_quina_score",
    "calculate_repeated_numbers",
    "calculate_sena_score",
    "calculate_sequence_stats",
    "calculate_sum",
    "calculate_terno_score",
    "find_sequences",
    "load_delay_stats",
    "load_duos_stats",
    "load_frequency_stats",
    "load_quadras_stats",
    "load_quinas_stats",
    "load_senas_stats",
    "load_ternos_stats",
]

DEFAULT_QUADRAS_STATS_PATH = Path("data/stats/quadras_stats.json")
DEFAULT_QUINAS_STATS_PATH = Path("data/stats/quinas_stats.json")
DEFAULT_SENAS_STATS_PATH = Path("data/stats/senas_stats.json")
DEFAULT_DUOS_STATS_PATH = Path("data/stats/duos_stats.json")
DEFAULT_TERNOS_STATS_PATH = Path("data/stats/ternos_stats.json")
DEFAULT_DELAY_STATS_PATH = Path("data/stats/delay_stats.json")
DEFAULT_FREQUENCY_STATS_PATH = Path("data/stats/frequency_stats.json")


class DrawLike(Protocol):
    contest: int
    numbers: list[int]


def calculate_sum(draw: DrawLike) -> dict[str, int]:
    return {"total": sum(draw.numbers)}


@lru_cache(maxsize=None)
def load_quadras_stats(
    path: Path = DEFAULT_QUADRAS_STATS_PATH,
) -> dict[str, dict[str, int]]:
    if not path.exists():
        logger.warning("Arquivo de estatisticas nao encontrado: %s", path)
        return {}

    return json.loads(path.read_text(encoding="utf-8"))


def calculate_quadra_score(numbers: list[int]) -> dict[str, object]:
    quadras_stats = load_quadras_stats()
    found_quadras = []

    for quadra_numbers in combinations(sorted(numbers), 4):
        quadra_key = "-".join(str(number) for number in quadra_numbers)
        quadra_stats = quadras_stats.get(quadra_key)
        if not quadra_stats:
            continue

        found_quadras.append(
            {
                "quadra": quadra_key,
                "frequency": quadra_stats["frequency"],
                "rank": quadra_stats["rank"],
            }
        )

    found_count = len(found_quadras)
    total_frequency = sum(quadra["frequency"] for quadra in found_quadras)
    total_rank = sum(quadra["rank"] for quadra in found_quadras)
    top_quadras = sorted(
        (quadra for quadra in found_quadras if quadra["rank"] <= 50),
        key=lambda quadra: (quadra["rank"], quadra["quadra"]),
    )

    return {
        "found_quadras": found_count,
        "total_frequency": total_frequency,
        "average_frequency": total_frequency / found_count if found_count else 0,
        "average_rank": total_rank / found_count if found_count else 0,
        "top_quadras": top_quadras,
    }


@lru_cache(maxsize=None)
def load_quinas_stats(
    path: Path = DEFAULT_QUINAS_STATS_PATH,
) -> dict[str, dict[str, int]]:
    if not path.exists():
        logger.warning("Arquivo de estatisticas nao encontrado: %s", path)
        return {}

    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def load_senas_stats(
    path: Path = DEFAULT_SENAS_STATS_PATH,
) -> dict[str, dict[str, float | int]]:
    if not path.exists():
        logger.warning("Arquivo de estatisticas nao encontrado: %s", path)
        return {}

    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def load_duos_stats(
    path: Path = DEFAULT_DUOS_STATS_PATH,
) -> dict[str, dict[str, int]]:
    if not path.exists():
        logger.warning("Arquivo de estatisticas nao encontrado: %s", path)
        return {}

    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def load_ternos_stats(
    path: Path = DEFAULT_TERNOS_STATS_PATH,
) -> dict[str, dict[str, int]]:
    if not path.exists():
        logger.warning("Arquivo de estatisticas nao encontrado: %s", path)
        return {}

    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def load_delay_stats(
    path: Path = DEFAULT_DELAY_STATS_PATH,
) -> dict[str, dict[str, int]]:
    if not path.exists():
        logger.warning("Arquivo de estatisticas nao encontrado: %s", path)
        return {}

    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def load_frequency_stats(
    path: Path = DEFAULT_FREQUENCY_STATS_PATH,
) -> dict[str, dict[str, float | int]]:
    if not path.exists():
        logger.warning("Arquivo de estatisticas nao encontrado: %s", path)
        return {}

    return json.loads(path.read_text(encoding="utf-8"))


def calculate_duo_score(numbers: list[int]) -> dict[str, object]:
    duos_stats = load_duos_stats()
    found_duos = []

    for duo_numbers in combinations(sorted(numbers), 2):
        duo_key = "-".join(str(number) for number in duo_numbers)
        duo_stats = duos_stats.get(duo_key)
        if not duo_stats:
            continue

        found_duos.append(
            {
                "duo": duo_key,
                "frequency": duo_stats["frequency"],
                "rank": duo_stats["rank"],
            }
        )

    found_count = len(found_duos)
    total_frequency = sum(duo["frequency"] for duo in found_duos)
    total_rank = sum(duo["rank"] for duo in found_duos)
    top_duos = sorted(
        (duo for duo in found_duos if duo["rank"] <= 50),
        key=lambda duo: (duo["rank"], duo["duo"]),
    )

    return {
        "found_duos": found_count,
        "total_frequency": total_frequency,
        "average_frequency": total_frequency / found_count if found_count else 0,
        "average_rank": total_rank / found_count if found_count else 0,
        "top_duos": top_duos,
    }


def _delay_weight(delay: int) -> float:
    if delay < 0:
        raise ValueError("O atraso deve ser maior ou igual a zero.")

    target_delay = 3
    tolerance = 3
    distance = abs(delay - target_delay)
    return max(0, 1 - (distance / tolerance))


def calculate_delay_score(numbers: list[int]) -> dict[str, object]:
    if any(number < 1 or number > 25 for number in numbers):
        raise ValueError("As dezenas devem estar entre 1 e 25.")

    delay_stats = load_delay_stats()
    found_delays = []

    for number in sorted(set(numbers)):
        number_stats = delay_stats.get(str(number))
        if not number_stats:
            continue

        delay = number_stats["delay"]
        weight = _delay_weight(delay)
        found_delays.append(
            {
                "number": number,
                "delay": delay,
                "score": round(weight * 100, 2),
            }
        )

    found_count = len(found_delays)
    total_score = sum(item["score"] for item in found_delays)
    score = total_score / found_count if found_count else 0

    return {
        "found_delays": found_count,
        "score": round(score, 2),
        "average_delay": (
            sum(item["delay"] for item in found_delays) / found_count if found_count else 0
        ),
        "delays": found_delays,
    }


def calculate_terno_score(numbers: list[int]) -> dict[str, object]:
    ternos_stats = load_ternos_stats()
    found_ternos = []

    for terno_numbers in combinations(sorted(numbers), 3):
        terno_key = "-".join(str(number) for number in terno_numbers)
        terno_stats = ternos_stats.get(terno_key)
        if not terno_stats:
            continue

        found_ternos.append(
            {
                "terno": terno_key,
                "frequency": terno_stats["frequency"],
                "rank": terno_stats["rank"],
            }
        )

    found_count = len(found_ternos)
    total_frequency = sum(terno["frequency"] for terno in found_ternos)
    total_rank = sum(terno["rank"] for terno in found_ternos)
    top_ternos = sorted(
        (terno for terno in found_ternos if terno["rank"] <= 50),
        key=lambda terno: (terno["rank"], terno["terno"]),
    )

    return {
        "found_ternos": found_count,
        "total_frequency": total_frequency,
        "average_frequency": total_frequency / found_count if found_count else 0,
        "average_rank": total_rank / found_count if found_count else 0,
        "top_ternos": top_ternos,
    }


def calculate_quina_score(numbers: list[int]) -> dict[str, object]:
    if any(number < 1 or number > 25 for number in numbers):
        raise ValueError("As dezenas devem estar entre 1 e 25.")

    quinas_stats = load_quinas_stats()
    found_quinas = []

    for quina_numbers in combinations(sorted(set(numbers)), 5):
        quina_key = "-".join(str(number) for number in quina_numbers)
        quina_stats = quinas_stats.get(quina_key)
        if not quina_stats:
            continue

        count = quina_stats.get("count", quina_stats.get("frequency", 0))
        found_quinas.append(
            {
                "quina": quina_key,
                "count": count,
                "rank": quina_stats["rank"],
                "relative_strength": quina_stats.get("relative_strength", 0),
            }
        )

    found_count = len(found_quinas)
    total_count = sum(quina["count"] for quina in found_quinas)
    total_rank = sum(quina["rank"] for quina in found_quinas)
    total_relative_strength = sum(quina["relative_strength"] for quina in found_quinas)
    top_quinas = sorted(
        (quina for quina in found_quinas if quina["rank"] <= 50),
        key=lambda quina: (quina["rank"], quina["quina"]),
    )

    return {
        "found_quinas": found_count,
        "total_count": total_count,
        "average_count": total_count / found_count if found_count else 0,
        "average_rank": total_rank / found_count if found_count else 0,
        "average_relative_strength": (
            total_relative_strength / found_count if found_count else 0
        ),
        "top_quinas": top_quinas,
    }


def calculate_sena_score(numbers: list[int]) -> dict[str, object]:
    if any(number < 1 or number > 25 for number in numbers):
        raise ValueError("As dezenas devem estar entre 1 e 25.")

    senas_stats = load_senas_stats()
    found_senas = []

    for sena_numbers in combinations(sorted(set(numbers)), 6):
        sena_key = "-".join(f"{number:02d}" for number in sena_numbers)
        sena_stats = senas_stats.get(sena_key)
        if not sena_stats:
            continue

        found_senas.append(
            {
                "sena": sena_key,
                "count": sena_stats["count"],
                "rank": sena_stats["rank"],
                "relative_strength": sena_stats["relative_strength"],
            }
        )

    found_count = len(found_senas)
    total_count = sum(sena["count"] for sena in found_senas)
    total_rank = sum(sena["rank"] for sena in found_senas)
    total_relative_strength = sum(sena["relative_strength"] for sena in found_senas)
    average_relative_strength = total_relative_strength / found_count if found_count else 0
    score = round(max(0, min(100, average_relative_strength * 100)), 2)
    top_senas = sorted(
        (sena for sena in found_senas if sena["rank"] <= 50),
        key=lambda sena: (sena["rank"], sena["sena"]),
    )

    return {
        "found_senas": found_count,
        "total_count": total_count,
        "average_count": total_count / found_count if found_count else 0,
        "average_rank": total_rank / found_count if found_count else 0,
        "average_relative_strength": average_relative_strength,
        "score": score,
        "top_senas": top_senas,
    }


def calculate_line_distribution(draw: DrawLike) -> dict[str, int]:
    distribution = {f"line_{line}": 0 for line in range(1, 6)}

    for number in draw.numbers:
        line = ((number - 1) // 5) + 1
        distribution[f"line_{line}"] += 1

    return distribution


def calculate_column_distribution(draw: DrawLike) -> dict[str, int]:
    distribution = {f"column_{column}": 0 for column in range(1, 6)}

    for number in draw.numbers:
        column = ((number - 1) % 5) + 1
        distribution[f"column_{column}"] += 1

    return distribution


def calculate_frame_center_distribution(draw: DrawLike) -> dict[str, int]:
    center = sum(1 for number in draw.numbers if number in CENTER_NUMBERS)
    return {"frame": len(draw.numbers) - center, "center": center}


def _validate_score_numbers(numbers: list[int]) -> list[int]:
    return validate_score_numbers(numbers)


def _rank_component_score(score_data: dict[str, object], rank_count: int) -> float:
    average_rank = float(score_data.get("average_rank") or 0)
    return round(rank_component_score(average_rank, rank_count), 2)


def _calculate_frequency_component(numbers: list[int]) -> float:
    if any(number < 1 or number > 25 for number in numbers):
        raise ValueError("As dezenas devem estar entre 1 e 25.")

    frequency_stats = load_frequency_stats()
    strengths = [
        float(frequency_stats[str(number)]["relative_strength"])
        for number in sorted(set(numbers))
        if str(number) in frequency_stats
    ]
    if not strengths:
        return 0

    average_strength = sum(strengths) / len(strengths)
    normalized_strength = (average_strength - 0.95) / 0.10
    base_score = max(0, min(100, normalized_strength * 100))

    average_deviation = sum(abs(strength - average_strength) for strength in strengths) / len(
        strengths
    )
    balance_factor = max(0, min(1, 1 - (average_deviation / 0.25)))

    return round(base_score * balance_factor, 2)


def _calculate_sum_component(numbers: list[int]) -> float:
    target_sum = 195
    tolerance = 45
    distance = abs(sum(numbers) - target_sum)
    return round(max(0, min(100, (1 - (distance / tolerance)) * 100)), 2)


def _calculate_sequence_component(numbers: list[int]) -> float:
    sequence_stats = calculate_sequence_stats(numbers)
    sequence_count = int(sequence_stats["sequence_count"])
    largest_sequence = int(sequence_stats["largest_sequence"])
    penalty = (sequence_count * 12) + (max(0, largest_sequence - 2) * 16)
    return round(max(0, 100 - penalty), 2)


def _weighted_final_score(components: dict[str, float]) -> float:
    return weighted_final_score(components, FINAL_SCORE_WEIGHTS)


def calculate_final_score(numbers: list[int]) -> dict[str, object]:
    score_numbers = _validate_score_numbers(numbers)

    duo_score = calculate_duo_score(score_numbers)
    terno_score = calculate_terno_score(score_numbers)
    quadra_score = calculate_quadra_score(score_numbers)
    quina_score = calculate_quina_score(score_numbers)
    delay_score = calculate_delay_score(score_numbers)

    components = {
        "duo_score": _rank_component_score(duo_score, 300),
        "terno_score": _rank_component_score(terno_score, 2300),
        "quadra_score": _rank_component_score(quadra_score, 12650),
        "quina_score": _rank_component_score(quina_score, 53130),
        "delay_score": float(delay_score["score"]),
        "frequency_score": _calculate_frequency_component(score_numbers),
        "sum_score": _calculate_sum_component(score_numbers),
        "sequence_score": _calculate_sequence_component(score_numbers),
    }

    return {
        "final_score": _weighted_final_score(components),
        "components": components,
    }
