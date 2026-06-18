from __future__ import annotations

from lotoia.governance.m_ger_dados_051_controlled_ge_removal import (
    REQUESTED_TARGET_IDS,
    resolve_authorized_target_ids,
)


def test_requested_targets_are_114_and_1115() -> None:
    assert REQUESTED_TARGET_IDS == frozenset({114, 1115})


def test_both_targets_when_1115_exists() -> None:
    authorized, _ = resolve_authorized_target_ids([114, 1115], ge_115_exists=True)
    assert authorized == [114, 1115]


def test_no_auto_remove_115_when_1115_missing() -> None:
    authorized, notes = resolve_authorized_target_ids([114], ge_115_exists=True)
    assert authorized == [114]
    assert 115 not in authorized
    assert notes.get("ge_115_preserved_pending_confirmation") is True
