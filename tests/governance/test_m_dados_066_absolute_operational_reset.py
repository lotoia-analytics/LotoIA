from __future__ import annotations

import pytest

from lotoia.governance.m_dados_066_absolute_operational_reset import (
    CONFIRMATION_TOKEN,
    OPERATIONAL_DELETE_ORDER,
    OPERATIONAL_SEQUENCES,
    PRESERVED_TABLES,
    assert_m_dados_066_confirmation,
    assert_preserved_table_not_in_scope,
    build_dry_run_report,
    build_inventory_report,
    build_post_reset_report,
    validate_post_reset_state,
)


def test_confirmation_token_required_for_execute() -> None:
    with pytest.raises(RuntimeError, match=CONFIRMATION_TOKEN):
        assert_m_dados_066_confirmation(confirmation=None, execute=True)
    assert_m_dados_066_confirmation(confirmation=CONFIRMATION_TOKEN, execute=True)


def test_preserved_tables_not_in_delete_scope() -> None:
    for table in ("imported_contests", "lotofacil_official_history", "scientific_institutional_memory"):
        with pytest.raises(RuntimeError, match="preservada"):
            assert_preserved_table_not_in_scope(table)


def test_operational_delete_order_includes_ml_and_reconciliation() -> None:
    assert "generation_events" in OPERATIONAL_DELETE_ORDER
    assert "generated_games" in OPERATIONAL_DELETE_ORDER
    assert "reconciliation_runs" in OPERATIONAL_DELETE_ORDER
    assert "reconciliation_games" in OPERATIONAL_DELETE_ORDER
    assert "ml_diagnostic_decisions" in OPERATIONAL_DELETE_ORDER
    assert "institutional_output_signatures" in OPERATIONAL_DELETE_ORDER
    assert OPERATIONAL_DELETE_ORDER.index("generated_games") > OPERATIONAL_DELETE_ORDER.index(
        "reconciliation_runs"
    )


def test_dry_run_reports_absolute_reset_without_protected_ges() -> None:
    inventory = build_inventory_report(
        table_counts={
            "generation_events": 486,
            "generated_games": 12000,
            "imported_contests": 3500,
        },
        generation_event_ids=[114, 115, 486],
        batch_labels=["STRUCT_LEI15_CORE_CANDIDATE_002_17D_001"],
    )
    report = build_dry_run_report(inventory=inventory)
    assert report["mode"] == "dry_run"
    assert report["absolute_reset"] is True
    assert report["protected_generation_event_ids"] == []
    assert report["sequence_reset_planned"] is True
    assert "generation_event_id reinicia em 1" in report["operational_numbering"]


def test_post_reset_report_flags_empty_operational_layer() -> None:
    inventory = build_inventory_report(
        table_counts={"generation_events": 10},
        generation_event_ids=[1, 2, 3],
        batch_labels=[],
    )
    after = {table: 0 for table in OPERATIONAL_DELETE_ORDER}
    post = build_post_reset_report(
        inventory_before=inventory,
        table_counts_after=after,
        preserved_counts_after={"imported_contests": 3500},
        deleted_counts={"generation_events": 10},
        sequence_status={"generation_events_id_seq": 1},
        reset_event_id=99,
    )
    assert post["checks"]["operational_tables_empty"] is True
    assert "RESET ABSOLUTO EXECUTADO" in post["verdict"]


def test_validate_post_reset_expects_first_ge_id_one() -> None:
    empty_report = validate_post_reset_state(
        table_counts={table: 0 for table in OPERATIONAL_DELETE_ORDER},
        preserved_counts={"imported_contests": 3500, "lotofacil_official_history": 3500},
        sequence_last_values={"generation_events_id_seq": 1},
        first_generation_event_id=None,
    )
    assert empty_report["checks"]["awaiting_first_generation"] is True
    assert empty_report["checks"]["generation_events_empty"] is True

    first_gen_report = validate_post_reset_state(
        table_counts={**{table: 0 for table in OPERATIONAL_DELETE_ORDER}, "generation_events": 1},
        preserved_counts={"imported_contests": 3500, "lotofacil_official_history": 3500},
        sequence_last_values={"generation_events_id_seq": 1},
        first_generation_event_id=1,
    )
    assert first_gen_report["checks"]["first_generation_event_id_is_one"] is True


def test_imported_contests_in_preserved_tables() -> None:
    assert "imported_contests" in PRESERVED_TABLES
    assert "ml_diagnostic_decisions" not in PRESERVED_TABLES


def test_sequences_include_generation_events() -> None:
    assert "generation_events_id_seq" in OPERATIONAL_SEQUENCES


def test_build_marker_bumped_for_m_dados_066() -> None:
    from dashboard.institutional_build import BUILD_MARKER, DEPRECATED_BUILD_MARKERS

    assert BUILD_MARKER == "institutional-adm-runtime-v51"
    assert BUILD_MARKER not in DEPRECATED_BUILD_MARKERS
    assert "institutional-adm-runtime-v50" in DEPRECATED_BUILD_MARKERS
