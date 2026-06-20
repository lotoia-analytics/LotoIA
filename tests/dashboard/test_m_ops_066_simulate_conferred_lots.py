"""M-OPS-066 — Simular Resultados como comparação de lotes conferidos."""

from __future__ import annotations

import inspect
from typing import Any

import pytest

import dashboard.institutional_app as institutional_app
from dashboard import institutional_conferred_lots_runtime as conferred_runtime
from dashboard.institutional_build import BUILD_MARKER


def test_build_marker_v81() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v81"


def test_is_lot_conferred_from_reconciliation() -> None:
    assert conferred_runtime.is_lot_conferred(reconciliation={"id": 7, "games_count": 3}) is True
    assert conferred_runtime.is_lot_conferred(reconciliation={}) is False


def test_is_lot_conferred_from_context_status() -> None:
    assert conferred_runtime.is_lot_conferred(
        context_json={"conference_status": conferred_runtime.CONFERENCE_STATUS_CHECKED}
    ) is True
    assert conferred_runtime.is_lot_conferred(context_json={"conference_status": "pending"}) is False


def test_filter_conferred_and_unconferred_do_not_mix() -> None:
    groups = [
        {
            "generation_event_id": 1,
            "total_games": 2,
            "context_json": {},
            "reconciliation": {},
            "games": [{"numbers": list(range(1, 16))}],
        },
        {
            "generation_event_id": 2,
            "total_games": 2,
            "context_json": {"conference_status": "checked", "checked_at": "2026-06-18"},
            "reconciliation": {"id": 9, "contest_id": 3700, "best_hits": 12},
            "games": [{"numbers": list(range(1, 16))}],
        },
    ]
    conferred = conferred_runtime.filter_conferred_groups(groups)
    unconferred = conferred_runtime.filter_unconferred_groups(groups)
    assert [lot["generation_event_id"] for lot in conferred] == [2]
    assert [lot["generation_event_id"] for lot in unconferred] == [1]


def test_persist_generation_event_conference_mark_updates_context(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    from pathlib import Path

    from lotoia.database.database import GenerationEvent, create_database, get_session

    db_path = Path(tmp_path) / "m_ops_066.db"
    create_database(db_path)
    with get_session(db_path) as session:
        event = GenerationEvent(
            seed=1,
            strategy="test",
            ml_enabled=0,
            generated_games=[{"numbers": list(range(1, 16))}],
            ranking_score=0.0,
            execution_time_ms=0.0,
            context_json={"batch_id": "BATCH-066"},
        )
        session.add(event)
        session.commit()
        event_id = int(event.id or 0)

    summary = conferred_runtime.build_checked_result_summary(
        comparison={"best_hits": 13, "total_hits": 40, "prize_count": 2, "contest_number": 3701, "results": [{}, {}]},
        hit_distribution={13: 1, 11: 1},
    )
    assert conferred_runtime.persist_generation_event_conference_mark(
        db_path=db_path,
        generation_event_id=event_id,
        checked_against_contest=3701,
        checked_result_summary=summary,
        checked_at="2026-06-18T12:00:00+00:00",
    )

    with get_session(db_path) as session:
        stored = session.query(GenerationEvent).filter(GenerationEvent.id == event_id).first()
        context = dict(getattr(stored, "context_json", {}) or {})
    assert context["conference_status"] == "checked"
    assert context["checked_against_contest"] == 3701
    assert context["checked_at"] == "2026-06-18T12:00:00+00:00"
    assert int(context["checked_result_summary"]["best_hits"]) == 13


def test_simulation_page_has_no_lab_generation() -> None:
    source = inspect.getsource(institutional_app._render_simulation_page)
    forbidden = (
        "Quantidade de jogos (lab)",
        "Gerar lote laboratório",
        "_run_simulation_lot_generation",
        "sim_lab_quantity",
        "sim_lab_format",
        "Simulação manual avulsa",
    )
    for token in forbidden:
        assert token not in source


def test_simulation_page_loads_conferred_lots() -> None:
    source = inspect.getsource(institutional_app._render_simulation_page)
    assert "_load_conferred_generation_groups" in source
    assert "Lotes conferidos" in source
    assert "Comparar lote conferido contra concursos selecionados" in source
    assert "SESSION_SIMULATION_SELECTED_GE" in source
    assert "_run_conferred_lot_multicontest_comparison" in source
    assert "não gera jogos" in source.lower() or "não gera jogos" in source


def test_analytical_page_excludes_conferred_queue() -> None:
    source = inspect.getsource(institutional_app._render_analytical_page)
    assert "is_lot_conferred" in source
    assert "ainda não conferidos" in source
    assert 'filtrar por status de conferência' not in source


def test_analytical_rows_loader_skips_conferred(monkeypatch: pytest.MonkeyPatch) -> None:
    generations = [
        {
            "generation_event_id": 10,
            "lot_operational_status": "official",
            "official_release_allowed": True,
            "is_active_reading": True,
            "reconciliation": {"id": 1},
            "games": [{"game_index": 1, "numbers": list(range(1, 16)), "score": 1.0}],
        },
        {
            "generation_event_id": 11,
            "lot_operational_status": "official",
            "official_release_allowed": True,
            "is_active_reading": True,
            "reconciliation": {},
            "strategy": "lei15",
            "created_at": "2026-06-18",
            "games": [{"game_index": 1, "numbers": list(range(1, 16)), "score": 1.0, "generation_context": {}}],
        },
    ]

    monkeypatch.setattr(institutional_app, "_load_generation_history_light", lambda limit=25: generations)
    monkeypatch.setattr(institutional_app, "_load_sovereign_generation_event_rows", lambda limit=50: [])
    monkeypatch.setattr(institutional_app, "is_analytical_history_eligible", lambda payload: True)

    rows = institutional_app._load_accumulated_analytical_rows_light(limit=10)
    ge_ids = {int(row["generation_event_id"]) for row in rows}
    assert ge_ids == {11}


def test_conference_groups_exclude_conferred(monkeypatch: pytest.MonkeyPatch) -> None:
    groups = [
        {"generation_event_id": 1, "context_json": {}, "reconciliation": {}, "official_release_allowed": True},
        {"generation_event_id": 2, "context_json": {}, "reconciliation": {"id": 5}, "official_release_allowed": True},
    ]
    monkeypatch.setattr(
        institutional_app,
        "_load_persisted_generation_event_groups",
        lambda **kwargs: groups,
    )
    loaded = institutional_app._load_official_conference_generation_groups()
    assert [int(group["generation_event_id"]) for group in loaded] == [1]


def test_run_institutional_conference_persists_checked_mark(monkeypatch: pytest.MonkeyPatch) -> None:
    source = inspect.getsource(institutional_app._run_institutional_conference)
    assert "persist_generation_event_conference_mark" in source
    assert "build_checked_result_summary" in source
