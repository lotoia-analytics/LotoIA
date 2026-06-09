from __future__ import annotations

from pathlib import Path

from lotoia.combinatorics import ExpansionConfig, expand_lotofacil_numbers, estimate_expansion
from lotoia.combinatorics.expansion_engine import iter_lotofacil_combinations
from lotoia.combinatorics.expansion_store import list_expansion_events, save_expansion_event
from lotoia.database.public_repository import save_expansion_event as save_institutional_expansion_event
from lotoia.public.persistence.repositories import ExpansionEventRepository


def test_lotofacil_expansion_counts_are_official() -> None:
    expected = {
        16: 16,
        17: 136,
        18: 816,
        19: 3876,
        20: 15504,
    }

    for size, total in expected.items():
        estimate = estimate_expansion(list(range(1, size + 1)))
        assert estimate["total_combinations"] == total


def test_expansion_generates_internal_15_number_games() -> None:
    result = expand_lotofacil_numbers(
        list(range(1, 17)),
        config=ExpansionConfig(preview_limit=20),
    )

    assert result.complete is True
    assert result.generated_count == 16
    assert all(len(game) == 15 for game in result.combinations)
    assert len(set(result.combinations)) == 16


def test_expansion_preview_limit_prevents_full_materialization() -> None:
    result = expand_lotofacil_numbers(
        list(range(1, 21)),
        config=ExpansionConfig(preview_limit=100, max_runtime_seconds=2.5),
    )

    assert result.total_combinations == 15504
    assert result.generated_count == 100
    assert result.complete is False
    assert result.stopped_reason == "preview_limit"


def test_expansion_rejects_invalid_cardinality() -> None:
    try:
        estimate_expansion(list(range(1, 16)))
    except ValueError as exc:
        assert "entre 16 e 20" in str(exc)
    else:
        raise AssertionError("expanded games must reject 15 numbers")


def test_incremental_iterator_does_not_require_list_payload() -> None:
    iterator = iter_lotofacil_combinations(list(range(1, 21)))
    first = next(iterator)

    assert first == tuple(range(1, 16))
    assert len(first) == 15


def test_expansion_store_persists_operational_event(tmp_path: Path) -> None:
    db_path = tmp_path / "expansion.db"
    payload = expand_lotofacil_numbers(
        list(range(1, 17)),
        config=ExpansionConfig(preview_limit=16),
    ).as_dict()
    payload["metrics"] = {"engine": "combinatorial_expansion_v1"}

    event_id = save_expansion_event(payload, db_path=db_path)
    events = list_expansion_events(db_path=db_path)

    assert event_id == 1
    assert events[0]["total_combinations"] == 16
    assert events[0]["estimated_cost"] == 56.0


def test_institutional_expansion_event_persists_operational_payload(tmp_path: Path) -> None:
    db_path = tmp_path / "institutional.db"
    payload = {
        "origin": "expanded",
        "selected_numbers": list(range(1, 17)),
        "combinations": [list(range(1, 16))],
        "total_combinations": 136,
        "generated_count": 20,
        "estimated_cost": 56.0,
        "runtime_ms": 1.0,
        "complete": False,
        "stopped_reason": "preview_limit",
        "metrics": {"profile_type": "hibrido"},
        "analysis": {"profile_type": "hibrido"},
    }

    event = save_institutional_expansion_event(
        lead_id=None,
        generation_event_id=None,
        expansion_type="expanded_preview",
        expansion_size=16,
        runtime_origin="admin_panel",
        strategy_profile="hibrido",
        payload=payload,
        db_path=db_path,
    )

    repository = ExpansionEventRepository(db_path)

    assert event["id"] == 1
    assert repository.count() == 1
    assert event["expansion_type"] == "expanded_preview"
    assert event["expansion_size"] == 16
    assert event["runtime_origin"] == "admin_panel"
