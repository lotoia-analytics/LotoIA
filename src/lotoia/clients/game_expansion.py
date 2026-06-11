from __future__ import annotations

from typing import Any, Sequence

AUDITED_RESERVE_PRIORITY = (7, 22, 4, 11, 12, 15, 16, 19, 21, 2, 17, 23, 13, 1, 9, 5, 6, 8, 14, 18, 20, 24, 25)


def _to_int_list(values: Sequence[Any]) -> list[int]:
    return [int(value) for value in values]


def expand_official_card(
    core_numbers: Sequence[int],
    card_format: int,
    *,
    game_index: int = 0,
) -> tuple[list[int], list[int], list[int]]:
    core = sorted(set(_to_int_list(core_numbers)))
    target_size = int(card_format or 15)
    if target_size <= len(core):
        return core, [], core[:target_size]
    needed = target_size - len(core)
    reserves: list[int] = []
    priority = list(AUDITED_RESERVE_PRIORITY)
    if priority and game_index:
        offset = int(game_index - 1) % len(priority)
        priority = priority[offset:] + priority[:offset]
    for number in priority:
        if number in core or number in reserves:
            continue
        reserves.append(int(number))
        if len(reserves) >= needed:
            break
    if len(reserves) < needed:
        for number in range(1, 26):
            if number in core or number in reserves:
                continue
            reserves.append(int(number))
            if len(reserves) >= needed:
                break
    final_card = sorted(core + reserves[:needed])
    return core, reserves[:needed], final_card


def expand_generation_games_for_format(
    games: Sequence[dict[str, Any]],
    card_format: int,
) -> list[dict[str, Any]]:
    expanded_games: list[dict[str, Any]] = []
    for index, game in enumerate(games, start=1):
        core_numbers = list(game.get("numbers", []) or [])
        core, reserves, final_card = expand_official_card(core_numbers, card_format, game_index=index)
        expanded_games.append(
            {
                **dict(game),
                "card_format": int(card_format or 15),
                "core_numbers": core,
                "audited_reserve_numbers": reserves,
                "final_card_numbers": final_card,
                "numbers": final_card,
            }
        )
    return expanded_games
