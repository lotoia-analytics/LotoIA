from __future__ import annotations

import inspect
from datetime import UTC, datetime
from pathlib import Path

import pytest

import dashboard.institutional_app as institutional_app
from dashboard.institutional_build import BUILD_MARKER
from dashboard.institutional_operational_structural_coverage import (
    EMPTY_OPERATIONAL_MESSAGE,
    HISTORICAL_SECTION_TITLE,
    OPERATIONAL_COVERAGE_TITLE,
    OPERATIONAL_GENERATION_ALL_LABEL,
    OPERATIONAL_SOURCE_CAPTION,
    build_operational_generation_dropdown_options,
    build_operational_generations_aggregate_summary,
    is_all_operational_generations_selection,
    load_operational_core_002_generations,
)
from lotoia.database.database import GeneratedGame, GenerationEvent, create_database, get_session
from lotoia.governance.lei15_core_002_sovereign import resolve_core_002_batch_label
from lotoia.observability.card_structure_diagnostics import (
    OPERATIONAL_TABLES,
    load_operational_card_structure_diagnostics_from_db,
)


def test_build_marker_v31() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v32"
    assert institutional_app.APP_BUILD == BUILD_MARKER


def test_operational_dropdown_includes_todos_option() -> None:
    generations = [
        {
            "dropdown_label": "Geração 001 — GE 1 — 15D — CORE_002 — 10 jogos",
            "generation_event_id": 1,
            "games_count": 10,
            "card_format": 15,
        },
        {
            "dropdown_label": "Geração 002 — GE 2 — 17D — CORE_002 — 20 jogos",
            "generation_event_id": 2,
            "games_count": 20,
            "card_format": 17,
        },
    ]
    options = build_operational_generation_dropdown_options(generations)
    assert options[0] == OPERATIONAL_GENERATION_ALL_LABEL
    assert len(options) == 3
    assert is_all_operational_generations_selection(OPERATIONAL_GENERATION_ALL_LABEL)
    assert not is_all_operational_generations_selection(generations[0]["dropdown_label"])

    aggregate = build_operational_generations_aggregate_summary(generations)
    assert aggregate["operational_generation_label"] == "Todos"
    assert aggregate["generation_events_count"] == 2
    assert aggregate["games_count"] == 30
    assert aggregate["card_format_label"] == "15D, 17D"


def test_cobertura_page_prioritizes_operational_core_002_source() -> None:
    source = inspect.getsource(institutional_app._render_cobertura_estrutural_page)
    assert "OPERATIONAL_COVERAGE_TITLE" in source
    assert "OPERATIONAL_SOURCE_CAPTION" in source
    assert "_cached_operational_core_002_generations" in source
    assert "_cached_operational_card_structure_diagnostics_from_db" in source
    assert "structural_coverage_operational_generation" in source
    assert "build_operational_generation_dropdown_options" in source
    assert "build_operational_generations_aggregate_summary" in source
    assert "is_all_operational_generations_selection" in source
    assert "EMPTY_OPERATIONAL_MESSAGE" in source
    assert "_render_historical_structural_coverage_section" in source
    assert "batch_select_options" not in source
    assert "STRUCT_TEST_15D" not in source


def test_historical_section_uses_reconciliation_source() -> None:
    source = inspect.getsource(institutional_app._render_historical_structural_coverage_section)
    assert "_cached_card_structure_diagnostics_from_db" in source
    assert "historical_reconciliation" in source
    assert "batch_select_options" in source


@pytest.fixture
def sqlite_db_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("LOTOIA_DATABASE_URL", raising=False)
    monkeypatch.delenv("STREAMLIT_DATABASE_URL", raising=False)


@pytest.mark.parametrize("card_format", [15, 17, 23])
def test_operational_loader_reads_generated_games(
    tmp_path: Path,
    card_format: int,
    sqlite_db_env: None,
) -> None:
    db_path = tmp_path / f"operational_{card_format}d.db"
    create_database(db_path)
    batch_label = resolve_core_002_batch_label(card_format)
    numbers = list(range(1, card_format + 1))
    with get_session(db_path) as session:
        event = GenerationEvent(
            first_name="institutional",
            whatsapp="",
            generated_games=[{"numbers": numbers[:15]}],
            context_json={"generation_mode": "LEI15_CORE_002_SOVEREIGN"},
            ml_enabled=0,
            seed=42,
            strategy="institutional_clean_hb",
            ranking_score=0.0,
            execution_time_ms=1.0,
            analysis_batch_label=batch_label,
            analysis_batch_type="LEI15_CORE_002_SOVEREIGN",
            analysis_batch_created_at=datetime.now(UTC),
        )
        session.add(event)
        session.flush()
        ge_id = int(event.id)
        session.add(
            GeneratedGame(
                generation_event_id=ge_id,
                target_contest=3712,
                origin="institutional",
                generation_mode="hb_baseline",
                game_index=1,
                numbers=numbers if card_format == 15 else numbers[:15],
                profile_type="HYBRID",
                final_score={},
                quadra_score={},
                context_json={
                    "selected_card_format": card_format,
                    "core_numbers": numbers[:15],
                    "final_card_numbers": numbers,
                },
            )
        )
        session.commit()

    generations = load_operational_core_002_generations(db_path)
    assert len(generations) == 1
    assert generations[0]["generation_event_id"] == ge_id
    assert generations[0]["card_format"] == card_format
    assert "CORE_002" in generations[0]["dropdown_label"]
    assert "STRUCT_TEST" not in generations[0]["dropdown_label"]

    payload = load_operational_card_structure_diagnostics_from_db(
        db_path,
        generation_event_id=ge_id,
        game_size=card_format,
    )
    assert payload["available"] is True
    assert payload["tables"] == OPERATIONAL_TABLES
    assert payload["coverage_layer"] == "operational_core_002"
    assert int(payload["summary"]["total_jogos"]) == 1


def test_operational_loader_aggregates_all_generations_when_no_filter(
    tmp_path: Path,
    sqlite_db_env: None,
) -> None:
    db_path = tmp_path / "operational_all.db"
    create_database(db_path)
    with get_session(db_path) as session:
        for card_format in (15, 17):
            batch_label = resolve_core_002_batch_label(card_format)
            numbers = list(range(1, card_format + 1))
            event = GenerationEvent(
                first_name="institutional",
                whatsapp="",
                generated_games=[{"numbers": numbers[:15]}],
                context_json={"generation_mode": "LEI15_CORE_002_SOVEREIGN"},
                ml_enabled=0,
                seed=42,
                strategy="institutional_clean_hb",
                ranking_score=0.0,
                execution_time_ms=1.0,
                analysis_batch_label=batch_label,
                analysis_batch_type="LEI15_CORE_002_SOVEREIGN",
                analysis_batch_created_at=datetime.now(UTC),
            )
            session.add(event)
            session.flush()
            session.add(
                GeneratedGame(
                    generation_event_id=int(event.id),
                    target_contest=3712,
                    origin="institutional",
                    generation_mode="hb_baseline",
                    game_index=1,
                    numbers=numbers if card_format == 15 else numbers[:15],
                    profile_type="HYBRID",
                    final_score={},
                    quadra_score={},
                    context_json={
                        "selected_card_format": card_format,
                        "core_numbers": numbers[:15],
                        "final_card_numbers": numbers,
                    },
                )
            )
        session.commit()

    payload = load_operational_card_structure_diagnostics_from_db(db_path)
    assert payload["available"] is True
    assert int(payload["summary"]["total_jogos"]) == 2
    assert int(payload["summary"]["total_geracoes"]) == 2
    assert set(payload["summary"]["formatos_analisados"]) == {15, 17}


def test_operational_loader_empty_without_sovereign_generations(
    tmp_path: Path,
    sqlite_db_env: None,
) -> None:
    db_path = tmp_path / "empty_operational.db"
    create_database(db_path)
    with get_session(db_path) as session:
        event = GenerationEvent(
            first_name="institutional",
            whatsapp="",
            generated_games=[{"numbers": list(range(1, 16))}],
            context_json={},
            ml_enabled=0,
            seed=1,
            strategy="institutional_clean_hb",
            ranking_score=0.0,
            execution_time_ms=1.0,
            analysis_batch_label="STRUCT_TEST_15D_001",
            analysis_batch_created_at=datetime.now(UTC),
        )
        session.add(event)
        session.flush()
        session.add(
            GeneratedGame(
                generation_event_id=int(event.id),
                origin="institutional",
                generation_mode="hb_baseline",
                game_index=1,
                numbers=list(range(1, 16)),
                profile_type="HYBRID",
                final_score={},
                quadra_score={},
                context_json={},
            )
        )
        session.commit()

    assert load_operational_core_002_generations(db_path) == []
    payload = load_operational_card_structure_diagnostics_from_db(db_path)
    assert payload["available"] is False
    assert payload["tables"] == OPERATIONAL_TABLES
