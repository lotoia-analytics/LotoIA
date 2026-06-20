"""Testes M-AUDIT-077 — classificação por lote vs jogo."""

from __future__ import annotations

from lotoia.audits.m_audit_077_generation_promotion import (
    MISSION_ID,
    audit_generation_event_record,
    build_operational_index,
    classify_games_in_lot,
    resolve_generation_event_ids_for_operational_range,
)


def _games_from_template(offset: int, count: int = 5) -> list[dict]:
    rows: list[dict] = []
    for index in range(count):
        base = ((offset + index) % 10) + 1
        numbers = sorted({((base + step) % 25) + 1 for step in range(15)})
        while len(numbers) < 15:
            numbers.append((len(numbers) + offset) % 25 + 1)
        numbers = sorted(set(numbers))[:15]
        rows.append({"game_index": index + 1, "numbers": numbers, "final_card_numbers": numbers})
    return rows


def test_operational_index_maps_sequence_to_ge_id() -> None:
    events = [
        {"id": 10, "analysis_batch_label": "STRUCT_LEI15_CORE_CANDIDATE_002_15D_001", "created_at": "t1"},
        {"id": 11, "analysis_batch_label": "STRUCT_LEI15_CORE_CANDIDATE_002_15D_001", "created_at": "t2"},
        {"id": 12, "analysis_batch_label": "STRUCT_LEI15_CORE_CANDIDATE_002_15D_001", "created_at": "t3"},
    ]
    index = build_operational_index(events)
    assert index == {10: 1, 11: 2, 12: 3}
    assert resolve_generation_event_ids_for_operational_range(events, operational_start=2, operational_end=3) == [11, 12]


def test_classify_games_counts_acceptable_attention_critical() -> None:
    games = _games_from_template(0, count=6)
    payload = classify_games_in_lot(games, card_format=15)
    assert payload["total_games"] == 6
    assert payload["acceptable"] + payload["attention"] + payload["critical"] == 6
    assert payload["individual_promotion_supported"] is False


def test_audit_generation_event_record_marks_lot_discarded_when_not_eligible() -> None:
    games = _games_from_template(3, count=4)

    class _Row:
        def __init__(self, game: dict) -> None:
            self.game_index = game["game_index"]
            self.numbers = game["numbers"]
            self.context_json = {"final_card_numbers": game["numbers"]}
            self.profile_type = "recorrente"

    row = audit_generation_event_record(
        event={
            "id": 99,
            "analysis_batch_label": "STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
            "created_at": "2026-06-18",
            "context_json": {
                "ml_verdict": "PRECISA CALIBRAR",
                "lot_operational_status": "needs_calibration",
                "official_release_allowed": False,
                "promotion_block_reason": "ml_verdict_precisa_calibrar_not_releasable",
            },
        },
        game_rows=[_Row(game) for game in games],
        operational_sequence=28,
    )
    assert row["mission_id"] == MISSION_ID
    assert row["lot_discarded_entirely"] is True
    assert row["is_analytical_history_eligible"] is False
    assert row["is_official_conference_eligible"] is False
    assert int(row["games_that_could_have_been_promoted_individually"]) >= 0
