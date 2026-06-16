from __future__ import annotations

from datetime import UTC, datetime

import pytest

from lotoia.database.database import (
    GenerationEvent,
    LotofacilOfficialHistory,
    ReconciliationGame,
    ReconciliationRun,
    create_database,
    get_session,
)
from lotoia.governance.analysis_batch_labels import (
    ALLOWED_BATCH_LABELS,
    BATCH_LABEL_UI_OPTIONS,
    RESERVED_BATCH_LABELS,
    build_batch_metadata,
    is_reserved_batch_label,
    validate_batch_label_for_game_size,
)
from lotoia.observability.card_structure_diagnostics import load_card_structure_diagnostics_from_db

OFFICIAL_15 = [1, 3, 5, 7, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
CARD_15D = OFFICIAL_15
CARD_17D = sorted(OFFICIAL_15 + [2, 4])[:17]


def _seed_reconciliation(
    db_path,
    *,
    contest_id: int,
    numbers: list[int],
    batch_label: str | None = None,
) -> tuple[int, int]:
    create_database(db_path)
    with get_session(db_path) as session:
        session.add(
            LotofacilOfficialHistory(
                contest_number=contest_id,
                draw_date=datetime.now(UTC).date().isoformat(),
                numbers=" ".join(f"{number:02d}" for number in OFFICIAL_15),
                source="test",
            )
        )
        event = GenerationEvent(
            lead_id=None,
            first_name="institutional",
            whatsapp="",
            generated_games=[{"numbers": numbers}],
            context_json={},
            ml_enabled=0,
            seed=1,
            strategy="institutional_clean_hb",
            ranking_score=0.0,
            execution_time_ms=0.0,
            analysis_batch_label=batch_label,
            analysis_batch_type="STRUCTURAL_COVERAGE_TEST" if batch_label else None,
            analysis_batch_created_by="test",
            analysis_batch_created_at=datetime.now(UTC) if batch_label else None,
        )
        session.add(event)
        session.flush()
        resolved_generation_event_id = int(event.id or 0)
        event.context_json = {"generation_event_id": resolved_generation_event_id}
        run = ReconciliationRun(
            generation_event_id=resolved_generation_event_id,
            contest_id=contest_id,
            prize_count=0,
            total_hits=13,
            best_hits=13,
            created_at=datetime.now(UTC),
            payload={},
        )
        session.add(run)
        session.flush()
        session.add(
            ReconciliationGame(
                reconciliation_run_id=run.id,
                generation_event_id=resolved_generation_event_id,
                contest_id=contest_id,
                game_index=1,
                numbers=numbers,
                hits=13,
                matched_numbers=sorted(set(numbers) & set(OFFICIAL_15)),
                prize_status="nao_premiado",
                prize_tier="",
                context_json={},
            )
        )
        session.commit()
        return resolved_generation_event_id, int(run.id)


def test_labels_15d_ate_23d_disponiveis() -> None:
    assert len(ALLOWED_BATCH_LABELS) == 9
    assert ALLOWED_BATCH_LABELS[0] == "STRUCT_TEST_15D"
    assert ALLOWED_BATCH_LABELS[-1] == "STRUCT_TEST_23D"
    assert "STRUCT_TEST_21D" in BATCH_LABEL_UI_OPTIONS
    assert RESERVED_BATCH_LABELS == frozenset({"STRUCT_TEST_21D", "STRUCT_TEST_22D", "STRUCT_TEST_23D"})


def test_labels_reservados_nao_liberam_runtime() -> None:
    for label in RESERVED_BATCH_LABELS:
        assert is_reserved_batch_label(label)
        validation = validate_batch_label_for_game_size(label, game_size=batch_label_game_size(label) or 21)
        assert validation["valid"] is False
        assert validation["operational_effect"] is False


def batch_label_game_size(label: str) -> int | None:
    from lotoia.governance.analysis_batch_labels import batch_label_game_size as _batch_label_game_size

    return _batch_label_game_size(label)


def test_format_consistency_struct_test_labels() -> None:
    ok = validate_batch_label_for_game_size("STRUCT_TEST_15D", game_size=15)
    assert ok["valid"] is True
    bad = validate_batch_label_for_game_size("STRUCT_TEST_15D", game_size=17)
    assert bad["valid"] is False
    ok17 = validate_batch_label_for_game_size("STRUCT_TEST_17D", game_size=17)
    assert ok17["valid"] is True


def test_build_batch_metadata_operational_effect_false() -> None:
    metadata = build_batch_metadata("STRUCT_TEST_18D", game_size=18, created_by="adm@test")
    assert metadata["analysis_batch_label"] == "STRUCT_TEST_18D"
    assert metadata["analysis_batch_type"] == "STRUCTURAL_COVERAGE_TEST"
    assert metadata["analysis_batch_created_by"] == "adm@test"
    assert metadata["operational_effect"] is False


def test_generation_event_salva_analysis_batch_label(tmp_path) -> None:
    db_path = tmp_path / "batch_labels.db"
    create_database(db_path)
    metadata = build_batch_metadata("STRUCT_TEST_16D", game_size=16, created_by="institutional")
    with get_session(db_path) as session:
        event = GenerationEvent(
            lead_id=None,
            first_name="institutional",
            whatsapp="",
            generated_games=[{"numbers": CARD_15D}],
            context_json={"analysis_batch_label": metadata["analysis_batch_label"]},
            ml_enabled=0,
            seed=7,
            strategy="institutional_clean_hb",
            ranking_score=0.0,
            execution_time_ms=0.0,
            analysis_batch_label=metadata["analysis_batch_label"],
            analysis_batch_type=metadata["analysis_batch_type"],
            analysis_batch_created_by=metadata["analysis_batch_created_by"],
            analysis_batch_created_at=metadata["analysis_batch_created_at"],
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        assert event.analysis_batch_label == "STRUCT_TEST_16D"
        assert event.analysis_batch_type == "STRUCTURAL_COVERAGE_TEST"
        assert event.analysis_batch_created_by == "institutional"


def test_painel_filtra_por_batch_label(tmp_path) -> None:
    db_path = tmp_path / "batch_filter.db"
    event_15d, _ = _seed_reconciliation(
        db_path,
        contest_id=3701,
        numbers=CARD_15D,
        batch_label="STRUCT_TEST_15D",
    )
    event_17d, _ = _seed_reconciliation(
        db_path,
        contest_id=3702,
        numbers=CARD_17D,
        batch_label="STRUCT_TEST_17D",
    )

    payload_15d = load_card_structure_diagnostics_from_db(
        db_path,
        analysis_batch_label="STRUCT_TEST_15D",
    )
    assert payload_15d["available"] is True
    assert payload_15d["summary"]["analysis_batch_label"] == "STRUCT_TEST_15D"
    assert payload_15d["summary"]["formatos_analisados"] == [15]
    assert payload_15d["evidence_base"]["generation_event_ids"] == [event_15d]

    payload_17d = load_card_structure_diagnostics_from_db(
        db_path,
        analysis_batch_label="STRUCT_TEST_17D",
    )
    assert payload_17d["summary"]["formatos_analisados"] == [17]
    assert payload_17d["evidence_base"]["generation_event_ids"] == [event_17d]


def test_struct_test_15d_nao_mistura_17d(tmp_path) -> None:
    db_path = tmp_path / "batch_no_mix.db"
    _seed_reconciliation(
        db_path,
        contest_id=3801,
        numbers=CARD_15D,
        batch_label="STRUCT_TEST_15D",
    )
    _seed_reconciliation(
        db_path,
        contest_id=3802,
        numbers=CARD_17D,
        batch_label="STRUCT_TEST_15D",
    )

    payload = load_card_structure_diagnostics_from_db(
        db_path,
        analysis_batch_label="STRUCT_TEST_15D",
    )
    assert payload["available"] is True
    assert payload["summary"]["formatos_analisados"] == [15]


def test_struct_test_17d_nao_mistura_15d(tmp_path) -> None:
    db_path = tmp_path / "batch_17_only.db"
    _seed_reconciliation(
        db_path,
        contest_id=3901,
        numbers=CARD_15D,
        batch_label="STRUCT_TEST_17D",
    )
    _seed_reconciliation(
        db_path,
        contest_id=3902,
        numbers=CARD_17D,
        batch_label="STRUCT_TEST_17D",
    )

    payload = load_card_structure_diagnostics_from_db(
        db_path,
        analysis_batch_label="STRUCT_TEST_17D",
    )
    assert payload["summary"]["formatos_analisados"] == [17]


def test_painel_filtra_por_game_size_e_ids(tmp_path) -> None:
    db_path = tmp_path / "batch_ids.db"
    event_id, run_id = _seed_reconciliation(
        db_path,
        contest_id=4001,
        numbers=CARD_17D,
        batch_label="STRUCT_TEST_17D",
    )

    by_size = load_card_structure_diagnostics_from_db(db_path, game_size=17)
    assert by_size["available"] is True
    assert by_size["summary"]["formatos_analisados"] == [17]

    by_event = load_card_structure_diagnostics_from_db(db_path, generation_event_id=event_id)
    assert by_event["evidence_base"]["generation_event_ids"] == [event_id]

    by_run = load_card_structure_diagnostics_from_db(db_path, reconciliation_run_id=run_id)
    assert by_run["evidence_base"]["reconciliation_run_ids"] == [run_id]

    by_contest = load_card_structure_diagnostics_from_db(db_path, concurso_analisado=4001)
    assert by_contest["evidence_base"]["concursos_analisados"] == [4001]


def test_reserved_label_rejeita_persistencia() -> None:
    with pytest.raises(ValueError, match="reservado"):
        build_batch_metadata("STRUCT_TEST_21D", game_size=21)
