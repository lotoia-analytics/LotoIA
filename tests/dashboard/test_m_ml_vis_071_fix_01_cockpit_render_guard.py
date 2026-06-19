"""M-ML-VIS-071-FIX-01 — proteção de renderização Streamlit na Central ML."""

from __future__ import annotations

import inspect
from pathlib import Path

import dashboard.institutional_ml_calibration_cockpit as cockpit
from dashboard.institutional_ml_cockpit_render_guard import (
    MISSION_ID,
    detect_mixed_format_aggregate,
    render_cockpit_block_safe,
    safe_cockpit_dataframe,
    safe_cockpit_json_display,
    sanitize_for_streamlit_json,
    summarize_coverage_snapshot_for_ui,
)
from dashboard.institutional_operational_structural_coverage import (
    OPERATIONAL_GENERATION_ALL_LABEL,
    resolve_operational_generation_selection,
)
from dashboard.institutional_supervised_ml import build_ml_calibration_cockpit_snapshot
from lotoia.database.database import GeneratedGame, GenerationEvent, create_database, get_session
from lotoia.governance.lei15_core_002_sovereign import resolve_core_002_batch_label


def _seed_gp_event(db_path: Path, *, card_format: int, games_count: int = 20) -> int:
    numbers = list(range(1, int(card_format) + 1))
    batch_label = resolve_core_002_batch_label(int(card_format))
    with get_session(db_path) as session:
        event = GenerationEvent(
            lead_id=None,
            first_name="institutional",
            whatsapp="",
            generated_games=[{"numbers": numbers}],
            context_json={
                "selected_quantity": games_count,
                "ml_scored_games": games_count,
                "selected_card_format": int(card_format),
                "card_format": int(card_format),
                "operational_status": "active",
                "active_reading_scope": True,
            },
            ml_enabled=1,
            seed=42,
            strategy="institutional_clean_hb",
            ranking_score=0.0,
            execution_time_ms=1.0,
            analysis_batch_label=batch_label,
        )
        session.add(event)
        session.flush()
        ge_id = int(event.id or 0)
        for index in range(games_count):
            session.add(
                GeneratedGame(
                    generation_event_id=ge_id,
                    lead_id=None,
                    target_contest=3700,
                    origin="institutional",
                    generation_mode="hb_baseline",
                    game_index=index + 1,
                    numbers=numbers,
                    profile_type="recorrente",
                    final_score={"final_score": 0.5},
                    quadra_score={},
                    context_json={
                        "selected_card_format": int(card_format),
                        "card_format": int(card_format),
                        "final_card_numbers": numbers,
                    },
                )
            )
        session.commit()
        return ge_id


def test_sanitize_breaks_recursion_and_limits_size() -> None:
    nested: dict[str, object] = {}
    nested["self"] = nested
    sanitized = sanitize_for_streamlit_json({"loop": nested, "items": list(range(200))})
    assert sanitized["loop"]["self"] == "<recursive>"
    assert any("truncated" in str(item) for item in sanitized["items"])


def test_safe_json_truncates_huge_payload() -> None:
    payload = {"blob": "x" * 100_000}
    rendered = safe_cockpit_json_display(payload)
    assert rendered.get("truncated") is True or len(str(rendered)) < 100_000


def test_safe_dataframe_limits_rows_and_flattens_nested() -> None:
    rows = [{"a": 1, "nested": {"b": [1, 2, 3]}} for _ in range(150)]
    dataframe = safe_cockpit_dataframe(rows, max_rows=25)
    assert len(dataframe.index) == 25
    assert isinstance(dataframe.iloc[0]["nested"], str)


def test_summarize_coverage_snapshot_omits_raw_games() -> None:
    summary = summarize_coverage_snapshot_for_ui(
        {
            "available": True,
            "summary": {"total_jogos": 40, "formatos_analisados": [15, 17]},
            "evidence_base": {"generation_event_ids": [1, 2]},
            "redundancia_gp": {"similaridade_media_entre_jogos": 0.5},
            "games": [{"numbers": list(range(1, 18))}],
        }
    )
    assert "games" not in summary
    assert summary.get("formatos_analisados") == [15, 17]


def test_detect_mixed_format_aggregate() -> None:
    assert detect_mixed_format_aggregate(
        {
            "aggregate_mode": True,
            "coverage_evidence": {"metrics": {"formatos_analisados": [15, 17]}},
        }
    )
    assert not detect_mixed_format_aggregate(
        {
            "aggregate_mode": False,
            "coverage_evidence": {"metrics": {"formatos_analisados": [15]}},
        }
    )


def test_cockpit_module_uses_render_guard() -> None:
    render_source = inspect.getsource(cockpit.render_ml_calibration_cockpit)
    expander_source = inspect.getsource(cockpit._render_technical_expanders)
    assert "render_cockpit_block_safe" in render_source
    assert "detect_mixed_format_aggregate" in render_source
    assert "display_cockpit_json" in expander_source
    assert "summarize_coverage_snapshot_for_ui" in expander_source
    assert MISSION_ID == "M-ML-VIS-071-FIX-01"


def test_snapshot_renders_for_15d_17d_and_mixed(tmp_path: Path) -> None:
    db_path = tmp_path / "render_guard.db"
    create_database(db_path)
    ge_15 = _seed_gp_event(db_path, card_format=15)
    ge_17 = _seed_gp_event(db_path, card_format=17)
    from dashboard.institutional_operational_structural_coverage import load_operational_core_002_generations

    generations = load_operational_core_002_generations(db_path)
    selection_15 = resolve_operational_generation_selection(
        next(row["dropdown_label"] for row in generations if int(row["generation_event_id"]) == ge_15),
        generations,
    )
    selection_17 = resolve_operational_generation_selection(
        next(row["dropdown_label"] for row in generations if int(row["generation_event_id"]) == ge_17),
        generations,
    )
    selection_all = resolve_operational_generation_selection(OPERATIONAL_GENERATION_ALL_LABEL, generations)

    snap_15 = build_ml_calibration_cockpit_snapshot(db_path, operational_selection=selection_15)
    snap_17 = build_ml_calibration_cockpit_snapshot(db_path, operational_selection=selection_17)
    snap_all = build_ml_calibration_cockpit_snapshot(db_path, operational_selection=selection_all)

    assert dict(snap_15.get("coverage_evidence") or {}).get("metrics", {}).get("formatos_analisados") == [15]
    assert dict(snap_17.get("coverage_evidence") or {}).get("metrics", {}).get("formatos_analisados") == [17]
    assert detect_mixed_format_aggregate(snap_all)


def test_render_block_safe_swallows_errors(monkeypatch) -> None:
    calls: list[str] = []

    class _Stub:
        def warning(self, *_args, **_kwargs) -> None:
            calls.append("warning")

        def caption(self, *_args, **_kwargs) -> None:
            calls.append("caption")

    monkeypatch.setattr("dashboard.institutional_ml_cockpit_render_guard.st", _Stub())

    def _boom() -> None:
        raise RuntimeError("frontend guard")

    assert render_cockpit_block_safe("teste", _boom) is False
    assert calls
