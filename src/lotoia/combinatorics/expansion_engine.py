from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from itertools import combinations
from math import comb
from time import perf_counter

DEFAULT_STAKE_PRICE = 3.50
SUPPORTED_EXPANDED_SIZES = tuple(range(16, 21))
SIMPLE_GAME_SIZE = 15
MAX_SAFE_COMBINATIONS = 15504


@dataclass(frozen=True)
class ExpansionConfig:
    max_combinations: int = MAX_SAFE_COMBINATIONS
    max_runtime_seconds: float = 2.5
    preview_limit: int = 200
    stake_price: float = DEFAULT_STAKE_PRICE


@dataclass(frozen=True)
class ExpansionResult:
    selected_numbers: tuple[int, ...]
    total_combinations: int
    generated_count: int
    combinations: tuple[tuple[int, ...], ...]
    estimated_cost: float
    runtime_ms: float
    complete: bool
    stopped_reason: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "selected_numbers": list(self.selected_numbers),
            "total_combinations": self.total_combinations,
            "generated_count": self.generated_count,
            "combinations": [list(game) for game in self.combinations],
            "estimated_cost": self.estimated_cost,
            "runtime_ms": self.runtime_ms,
            "complete": self.complete,
            "stopped_reason": self.stopped_reason,
        }


def validate_expanded_numbers(numbers: Sequence[int]) -> tuple[int, ...]:
    normalized = tuple(sorted(int(number) for number in numbers))
    if len(normalized) not in SUPPORTED_EXPANDED_SIZES:
        raise ValueError("Jogo expandido deve conter entre 16 e 20 dezenas.")
    if len(set(normalized)) != len(normalized):
        raise ValueError("As dezenas expandidas nao podem se repetir.")
    if any(number < 1 or number > 25 for number in normalized):
        raise ValueError("As dezenas devem estar entre 1 e 25.")
    return normalized


def estimate_expansion(
    numbers: Sequence[int],
    *,
    stake_price: float = DEFAULT_STAKE_PRICE,
) -> dict[str, object]:
    selected = validate_expanded_numbers(numbers)
    total = comb(len(selected), SIMPLE_GAME_SIZE)
    return {
        "selected_numbers": list(selected),
        "selected_count": len(selected),
        "total_combinations": total,
        "estimated_cost": round(total * stake_price, 2),
        "stake_price": stake_price,
    }


def iter_lotofacil_combinations(numbers: Sequence[int]) -> Iterator[tuple[int, ...]]:
    selected = validate_expanded_numbers(numbers)
    yield from combinations(selected, SIMPLE_GAME_SIZE)


def expand_lotofacil_numbers(
    numbers: Sequence[int],
    *,
    config: ExpansionConfig | None = None,
) -> ExpansionResult:
    active_config = config or ExpansionConfig()
    selected = validate_expanded_numbers(numbers)
    total = comb(len(selected), SIMPLE_GAME_SIZE)
    if total > active_config.max_combinations:
        raise ValueError("Quantidade de combinacoes excede o limite operacional configurado.")

    started = perf_counter()
    games: list[tuple[int, ...]] = []
    stopped_reason = None
    limit = min(active_config.preview_limit, active_config.max_combinations)

    for game in combinations(selected, SIMPLE_GAME_SIZE):
        elapsed = perf_counter() - started
        if elapsed > active_config.max_runtime_seconds:
            stopped_reason = "runtime_limit"
            break
        if len(games) >= limit:
            stopped_reason = "preview_limit"
            break
        games.append(tuple(game))

    runtime_ms = round((perf_counter() - started) * 1000, 3)
    complete = len(games) == total
    if complete:
        stopped_reason = None

    return ExpansionResult(
        selected_numbers=selected,
        total_combinations=total,
        generated_count=len(games),
        combinations=tuple(games),
        estimated_cost=round(total * active_config.stake_price, 2),
        runtime_ms=runtime_ms,
        complete=complete,
        stopped_reason=stopped_reason,
    )
