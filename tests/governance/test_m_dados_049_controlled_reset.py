from __future__ import annotations

import pytest

from lotoia.governance.m_dados_049_controlled_reset import (
    CONFIRMATION_TOKEN,
    GenerationEventRow,
    assert_m_dados_049_confirmation,
    build_dry_run_report,
    partition_generation_events,
)
from lotoia.governance.history_preservation_policy import PROTECTED_GENERATION_EVENT_IDS


def test_confirmation_token_required_for_execute() -> None:
    with pytest.raises(RuntimeError, match=CONFIRMATION_TOKEN):
        assert_m_dados_049_confirmation(confirmation=None, execute=True)
    assert_m_dados_049_confirmation(confirmation=CONFIRMATION_TOKEN, execute=True)


def test_protected_generation_events_are_not_deletable_when_still_protected() -> None:
    rows = [
        GenerationEventRow(999, "STRUCT_LEI15_CORE_CANDIDATE_001_15D_001", "test", "2026-01-01", False),
        GenerationEventRow(200, "STRUCT_LEI15_CORE_CANDIDATE_002_15D_001", "test", "2026-06-01", True),
    ]
    partitioned = partition_generation_events(rows)
    deletable_ids = {row["id"] for row in partitioned["deletable"]}
    assert deletable_ids == {200, 999}
    assert partitioned["protected"] == []


def test_dry_run_report_lists_preserved_tables() -> None:
    report = build_dry_run_report(
        table_counts_before={"generation_events": 10, "generated_games": 100},
        generation_events=[
            GenerationEventRow(200, "STRUCT_LEI15_CORE_CANDIDATE_002_15D_001", "test", "2026-06-01", True),
        ],
        batch_labels=["STRUCT_LEI15_CORE_CANDIDATE_002_15D_001"],
        preserved_table_counts={"imported_contests": 3712, "scientific_institutional_memory": 3},
    )
    assert report["mode"] == "dry_run"
    assert "imported_contests" in report["tables_preserved"]
    assert report["will_preserve"]["imported_contests"] == 3712
    assert report["protected_generation_event_ids"] == []
