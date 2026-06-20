"""Testes do monitoramento M-CORE-003 — razão de viés prefixo/sufixo."""

from __future__ import annotations

import inspect

from lotoia.database.database import GeneratedGame, GenerationEvent, create_database, get_session
from lotoia.governance.lei15_core_002_sovereign import resolve_core_002_batch_label
from lotoia.observability.m_core_003_bias_monitoring import (
    build_m_core_003_bias_monitoring_report,
    build_m_core_003_bias_monitoring_report_from_db,
    compute_normalized_pattern_entropy,
)


def _biased_card() -> list[int]:
    return [1, 4, 6, 8, 9, 10, 11, 12, 13, 14, 16, 17, 20, 22, 25]


def _neutral_card(offset: int) -> list[int]:
    return [2 + offset, 5, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 20, 22, 25]


def test_compute_normalized_pattern_entropy_perfect_uniformity() -> None:
    distribution = {"a": 25.0, "b": 25.0, "c": 25.0, "d": 25.0}
    assert compute_normalized_pattern_entropy(distribution) == 1.0


def test_build_report_flags_severe_prefix_bias() -> None:
    cards = [_biased_card() for _ in range(8)] + [_neutral_card(index) for index in range(2)]
    report = build_m_core_003_bias_monitoring_report(cards)
    assert report["available"] is True
    assert report["severe_bias_count"] >= 1
    assert report["compliance"] is False
    assert "01-04-06" in {row["pattern"] for row in report["prefix_patterns_over_severe"]}


def test_build_report_exposes_entropy_and_watchlist_fields() -> None:
    cards = [_neutral_card(index) for index in range(10)]
    report = build_m_core_003_bias_monitoring_report(cards)
    assert report["available"] is True
    assert 0.0 <= float(report["entropy_prefix"]) <= 1.0
    assert 0.0 <= float(report["entropy_suffix"]) <= 1.0
    assert report["watchlist_pattern"] == "03-04-05"
    assert "watchlist_ratio" in report


def test_build_report_from_db_reads_generated_games(tmp_path) -> None:
    db_path = tmp_path / "monitor.db"
    create_database(db_path)
    batch_label = resolve_core_002_batch_label(15)
    numbers = _biased_card()
    with get_session(db_path) as session:
        event = GenerationEvent(
            lead_id=None,
            first_name="institutional",
            whatsapp="",
            generated_games=[{"numbers": numbers}],
            context_json={"operational_status": "pending_structural_review"},
            ml_enabled=0,
            seed=42,
            strategy="institutional_clean_hb",
            ranking_score=0.0,
            execution_time_ms=0.0,
            analysis_batch_label=batch_label,
        )
        session.add(event)
        session.flush()
        ge_id = int(event.id or 0)
        for index in range(6):
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
                    context_json={"final_card_numbers": numbers},
                )
            )
        session.commit()
    report = build_m_core_003_bias_monitoring_report_from_db(db_path, generation_event_ids=[ge_id])
    assert report["available"] is True
    assert report["games_count"] == 6
    assert ge_id in report["generation_event_ids"]


def test_institutional_app_wires_m_core_003_monitoring_panel() -> None:
    import dashboard.institutional_app as institutional_app

    source = inspect.getsource(institutional_app._render_cobertura_estrutural_page)
    assert "render_m_core_003_bias_monitoring_panel" in source
