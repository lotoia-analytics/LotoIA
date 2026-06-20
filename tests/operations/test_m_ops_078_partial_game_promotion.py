"""M-OPS-078 — promoção parcial por jogo em lotes GP."""

from __future__ import annotations

import inspect
import random
from typing import Any

import pytest

import dashboard.institutional_app as institutional_app
from dashboard.institutional_build import BUILD_MARKER
from lotoia.ml.ml_operational_verdict import VERDICT_APROVADO, VERDICT_REPROVADO
from lotoia.operations.lot_operational_status import (
    STATUS_APPROVED_FOR_OFFICIALIZATION,
    STATUS_REJECTED,
    is_analytical_history_eligible,
    is_official_conference_eligible,
)
from lotoia.operations.partial_game_promotion import (
    GAME_QUALITY_ACCEPTABLE,
    GAME_QUALITY_ATTENTION,
    GAME_QUALITY_CRITICAL,
    MISSION_ID,
    apply_partial_promotion_to_payload_games,
    classify_individual_game_quality,
    classify_lot_partial_promotion,
    filter_analytical_games,
    filter_conference_games,
)


def _diverse_card(index: int) -> list[int]:
    """Cartão 15D único por índice (15 dezenas distintas)."""
    numbers: list[int] = []
    cursor = index
    while len(numbers) < 15:
        candidate = (cursor % 25) + 1
        if candidate not in numbers:
            numbers.append(candidate)
        cursor += 7
    return sorted(numbers)


def _attention_card(reference: list[int], variant: int) -> list[int]:
    """Sobreposição elevada (13 dezenas) com assinatura distinta por variant."""
    shared = sorted(reference)[:13]
    pool = [number for number in range(1, 26) if number not in shared]
    first = pool[(variant - 1) * 2 % len(pool)]
    second = pool[((variant - 1) * 2 + 1) % len(pool)]
    return sorted(shared + [first, second])


def _build_phantom_card(acceptable_cards: list[list[int]], *, seed: int = 99) -> list[int]:
    rng = random.Random(seed)
    for _ in range(100_000):
        candidate = sorted(rng.sample(range(1, 26), 15))
        if all(len(set(candidate) & set(existing)) <= 12 for existing in acceptable_cards):
            return candidate
    raise RuntimeError("unable to build phantom card for attention/duplicate scenario")


def _policy_compliant_previous() -> list[int]:
    return sorted([2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 1, 3, 5])


def _build_low_overlap_cards(count: int, *, seed: int = 42) -> list[list[int]]:
    rng = random.Random(seed)
    cards: list[list[int]] = []
    attempts = 0
    while len(cards) < count and attempts < 100_000:
        attempts += 1
        candidate = sorted(rng.sample(range(1, 26), 15))
        if all(len(set(candidate) & set(existing)) <= 12 for existing in cards):
            cards.append(candidate)
    if len(cards) < count:
        raise RuntimeError(f"unable to build {count} low-overlap cards")
    return cards


def _build_thirty_game_lot() -> list[dict[str, Any]]:
    games: list[dict[str, Any]] = []
    acceptable_cards = _build_low_overlap_cards(22)
    phantom = _build_phantom_card(acceptable_cards)
    for index, numbers in enumerate(acceptable_cards, start=1):
        games.append({"game_index": index, "numbers": numbers})
    for offset, index in enumerate(range(23, 28), start=1):
        games.append({"game_index": index, "numbers": _attention_card(phantom, offset)})
    duplicate_numbers = list(phantom)
    for index in range(28, 31):
        games.append({"game_index": index, "numbers": duplicate_numbers})
    return games


def _lot_context_with_policy(**overrides: Any) -> dict[str, Any]:
    return _rejected_lot_context(
        previous_contest_numbers=_policy_compliant_previous(),
        **overrides,
    )


def _rejected_lot_context(**overrides: Any) -> dict[str, Any]:
    base = {
        "generation_event_id": 78,
        "ml_verdict": VERDICT_REPROVADO,
        "lot_operational_status": STATUS_REJECTED,
        "official_release_allowed": False,
        "partial_promotion_enabled": True,
    }
    base.update(overrides)
    return base


def _approved_lot_context(**overrides: Any) -> dict[str, Any]:
    base = {
        "generation_event_id": 79,
        "ml_verdict": VERDICT_APROVADO,
        "lot_operational_status": STATUS_APPROVED_FOR_OFFICIALIZATION,
        "official_release_allowed": True,
        "partial_promotion_enabled": True,
    }
    base.update(overrides)
    return base


def test_build_marker_v83() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v83"


def _mock_policy_audit(games: list[dict[str, Any]], **_: Any) -> dict[str, Any]:
    per_game: list[dict[str, Any]] = []
    for index, game in enumerate(games):
        game_index = int(game.get("game_index", index + 1) or index + 1)
        if game_index <= 22:
            validation = {"approved": True, "violations": []}
        elif game_index <= 27:
            validation = {"approved": False, "violations": ["overlap_atencao"]}
        else:
            validation = {"approved": False, "violations": ["crit_duplicate"]}
        per_game.append({"game_index": game_index, "validation": validation})
    return {"per_game": per_game}


@pytest.fixture
def mock_policy_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "lotoia.operations.partial_game_promotion.analyze_batch_structural_policy_15d",
        _mock_policy_audit,
    )


def test_thirty_game_lot_classification_counts(mock_policy_audit: None) -> None:
    games = _build_thirty_game_lot()
    summary = classify_lot_partial_promotion(
        games,
        card_format=15,
        parent_lot_context=_lot_context_with_policy(),
    )
    assert summary["games_total"] == 30
    assert summary["games_acceptable"] == 22
    assert summary["games_attention"] == 5
    assert summary["games_critical"] == 3
    assert summary["games_promoted_to_analytical"] == 27
    assert summary["games_promoted_to_conference"] == 27
    assert summary["partial_promotion_enabled"] is True
    assert summary["partial_promotion_mission_id"] == MISSION_ID
    assert summary["lot_rejected_but_games_promoted"] is True


def test_hits_not_used_in_individual_classification() -> None:
    source = inspect.getsource(classify_individual_game_quality)
    lowered = source.lower()
    assert "desempenho_13" not in source
    assert "desempenho_14" not in source
    assert "desempenho_15" not in source
    assert "hit_histogram" not in lowered
    assert "count_13" not in lowered


def test_exact_duplicate_blocks_individual_game() -> None:
    card = list(range(1, 16))
    games = [
        {"game_index": 1, "numbers": card},
        {"game_index": 2, "numbers": list(card)},
    ]
    summary = classify_lot_partial_promotion(
        games,
        card_format=15,
        parent_lot_context=_rejected_lot_context(),
    )
    statuses = {row["game_quality_status"] for row in summary["per_game"]}
    assert statuses == {GAME_QUALITY_CRITICAL}


def test_game_index_preserved_in_partial_promotion(mock_policy_audit: None) -> None:
    games = _build_thirty_game_lot()
    enriched, patch = apply_partial_promotion_to_payload_games(
        games,
        generation_context=_lot_context_with_policy(),
        card_format=15,
        previous_contest_numbers=_policy_compliant_previous(),
    )
    assert [game["game_index"] for game in enriched] == list(range(1, 31))
    assert patch["games_total"] == 30
    assert patch["partial_promotion_enabled"] is True


def test_filter_analytical_promotes_acceptable_and_attention_only(mock_policy_audit: None) -> None:
    games = _build_thirty_game_lot()
    enriched, _ = apply_partial_promotion_to_payload_games(
        games,
        generation_context=_lot_context_with_policy(),
        card_format=15,
        previous_contest_numbers=_policy_compliant_previous(),
    )
    generation = {"context_json": _lot_context_with_policy()}
    selected = filter_analytical_games(generation, enriched)
    assert len(selected) == 27
    statuses = {game["game_quality_status"] for game in selected}
    assert GAME_QUALITY_CRITICAL not in statuses
    assert GAME_QUALITY_ACCEPTABLE in statuses
    assert GAME_QUALITY_ATTENTION in statuses


def test_filter_conference_excludes_critical(mock_policy_audit: None) -> None:
    games = _build_thirty_game_lot()
    enriched, _ = apply_partial_promotion_to_payload_games(
        games,
        generation_context=_lot_context_with_policy(),
        card_format=15,
        previous_contest_numbers=_policy_compliant_previous(),
    )
    generation = {"context_json": _lot_context_with_policy()}
    selected = filter_conference_games(generation, enriched)
    assert len(selected) == 27
    assert all(game["game_quality_status"] != GAME_QUALITY_CRITICAL for game in selected)


def test_rejected_lot_analytical_loader_receives_promoted_games(
    monkeypatch: pytest.MonkeyPatch,
    mock_policy_audit: None,
) -> None:
    games = _build_thirty_game_lot()
    enriched, patch = apply_partial_promotion_to_payload_games(
        games,
        generation_context=_lot_context_with_policy(),
        card_format=15,
        previous_contest_numbers=_policy_compliant_previous(),
    )
    rejected_generation: dict[str, Any] = {
        "generation_event_id": 78,
        "lot_operational_status": STATUS_REJECTED,
        "official_release_allowed": False,
        "ml_verdict": VERDICT_REPROVADO,
        "is_active_reading": True,
        "reconciliation": {},
        "strategy": "institutional_clean_hb",
        "created_at": "2026-06-18T12:00:00",
        "context_json": {**_lot_context_with_policy(), **patch},
        "partial_promotion_enabled": True,
        "games_promoted_to_analytical": 27,
        "games": enriched,
    }
    approved_generation: dict[str, Any] = {
        "generation_event_id": 79,
        "lot_operational_status": STATUS_APPROVED_FOR_OFFICIALIZATION,
        "official_release_allowed": True,
        "ml_verdict": VERDICT_APROVADO,
        "is_active_reading": True,
        "reconciliation": {},
        "games": [{"game_index": 1, "numbers": list(range(1, 16)), "generation_context": {}}],
        "context_json": _approved_lot_context(),
        "partial_promotion_enabled": True,
    }
    monkeypatch.setattr(
        institutional_app,
        "_load_generation_history_light",
        lambda limit=25: [rejected_generation, approved_generation],
    )
    monkeypatch.setattr(institutional_app, "_load_sovereign_generation_event_rows", lambda: [])

    rows = institutional_app._load_accumulated_analytical_rows_light(limit=10)
    ge_78_rows = [row for row in rows if int(row["generation_event_id"]) == 78]
    assert len(ge_78_rows) == 27
    assert all(row.get("game_quality_status") in {GAME_QUALITY_ACCEPTABLE, GAME_QUALITY_ATTENTION} for row in ge_78_rows)
    assert all(row.get("parent_lot_verdict") == VERDICT_REPROVADO for row in ge_78_rows)
    assert all(row.get("parent_lot_status") == STATUS_REJECTED for row in ge_78_rows)


def test_rejected_lot_conference_groups_receive_promoted_games(
    monkeypatch: pytest.MonkeyPatch,
    mock_policy_audit: None,
) -> None:
    games = _build_thirty_game_lot()
    enriched, patch = apply_partial_promotion_to_payload_games(
        games,
        generation_context=_lot_context_with_policy(),
        card_format=15,
        previous_contest_numbers=_policy_compliant_previous(),
    )
    groups = [
        {
            "generation_event_id": 78,
            "context_json": {**_lot_context_with_policy(), **patch},
            "reconciliation": {},
            "official_release_allowed": False,
            "is_official_conference_eligible": False,
            "games_promoted_to_conference": 27,
            "games": enriched,
        },
        {
            "generation_event_id": 77,
            "context_json": _rejected_lot_context(),
            "reconciliation": {},
            "official_release_allowed": False,
            "games": enriched[:3],
        },
    ]
    monkeypatch.setattr(institutional_app, "_load_persisted_generation_event_groups", lambda **_: groups)
    loaded = institutional_app._load_official_conference_generation_groups()
    ids = {int(group["generation_event_id"]) for group in loaded}
    assert 78 in ids
    promoted_group = next(group for group in loaded if int(group["generation_event_id"]) == 78)
    assert len(promoted_group["games"]) == 27
    assert promoted_group.get("partial_conference_games") is True


def test_approved_lot_keeps_full_promotion_behavior() -> None:
    games = [{"game_index": index, "numbers": _diverse_card(index)} for index in range(1, 6)]
    summary = classify_lot_partial_promotion(
        games,
        card_format=15,
        parent_lot_context=_approved_lot_context(),
    )
    assert summary["games_promoted_to_analytical"] == 5
    assert summary["games_promoted_to_conference"] == 5
    assert summary["lot_rejected_but_games_promoted"] is False
    parent = _approved_lot_context()
    assert is_analytical_history_eligible(parent)
    assert is_official_conference_eligible(parent)


def test_context_json_partial_promotion_fields(mock_policy_audit: None) -> None:
    games = _build_thirty_game_lot()
    _, patch = apply_partial_promotion_to_payload_games(
        games,
        generation_context=_lot_context_with_policy(),
        card_format=15,
        previous_contest_numbers=_policy_compliant_previous(),
    )
    assert patch["partial_promotion_enabled"] is True
    assert patch["partial_promotion_mission_id"] == MISSION_ID
    assert patch["games_total"] == 30
    assert patch["games_acceptable"] == 22
    assert patch["games_attention"] == 5
    assert patch["games_critical"] == 3
    assert patch["games_promoted_to_analytical"] == 27
    assert patch["games_promoted_to_conference"] == 27
    assert patch["lot_rejected_but_games_promoted"] is True


def test_persist_snapshot_copies_game_quality_fields() -> None:
    source = inspect.getsource(institutional_app._persist_generation_snapshot)
    assert "game_quality_status" in source
    assert "game_conference_eligible" in source
    assert "partial_promotion_mission_id" in source


def test_analytical_loader_uses_filter_not_whole_lot_gate() -> None:
    source = inspect.getsource(institutional_app._load_accumulated_analytical_rows_light)
    assert "filter_analytical_games" in source
    assert "is_analytical_history_eligible" not in source


def test_no_csv_duplicate_on_filtered_games(mock_policy_audit: None) -> None:
    games = _build_thirty_game_lot()
    enriched, _ = apply_partial_promotion_to_payload_games(
        games,
        generation_context=_lot_context_with_policy(),
        card_format=15,
        previous_contest_numbers=_policy_compliant_previous(),
    )
    selected = filter_analytical_games({"context_json": _lot_context_with_policy()}, enriched)
    signatures = [
        ",".join(f"{number:02d}" for number in sorted(game["numbers"]))
        for game in selected
    ]
    assert len(signatures) == len(set(signatures))
