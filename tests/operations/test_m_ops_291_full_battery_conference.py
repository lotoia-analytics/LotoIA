from __future__ import annotations

from lotoia.operations.partial_game_promotion import filter_conference_games


def _game(index: int, eligible: bool) -> dict[str, object]:
    return {
        "game_index": index,
        "numbers": list(range(1, 16)),
        "context_json": {
            "game_quality_status": "critical" if not eligible else "acceptable",
            "game_conference_eligible": eligible,
        },
    }


def test_official_lot_conference_uses_all_persisted_games_even_with_partial_promotion_flags() -> None:
    generation = {
        "lot_operational_status": "approved_with_warning",
        "official_release_allowed": True,
        "partial_promotion_enabled": True,
        "games_promoted_to_conference": 35,
    }
    games = [_game(index, eligible=index <= 35) for index in range(1, 191)]

    selected = filter_conference_games(generation, games)

    assert len(selected) == 190


def test_rejected_lot_still_uses_only_promoted_games() -> None:
    generation = {
        "lot_operational_status": "rejected",
        "official_release_allowed": False,
        "partial_promotion_enabled": True,
        "games_promoted_to_conference": 35,
    }
    games = [_game(index, eligible=index <= 35) for index in range(1, 191)]

    selected = filter_conference_games(generation, games)

    assert len(selected) == 35
