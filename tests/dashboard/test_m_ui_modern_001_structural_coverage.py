"""M-UI-MODERN-001 — dashboard visual de Cobertura Estrutural."""

from __future__ import annotations

import inspect

import pytest

from lotoia.observability.structural_fidelity_analytics import (
    MISSION_ID,
    build_quadrant_occupancy,
    build_structural_intelligence_bundle,
    compute_structural_fidelity_score,
    dezena_frequency_profile,
    resolve_fidelity_status,
)
from dashboard.institutional_structural_coverage_modern import (
    build_time_travel_options,
    _build_fidelity_gauge,
    _build_dezena_radar_chart,
)


def _sample_cards(count: int = 12) -> list[list[int]]:
    cards: list[list[int]] = []
    for index in range(count):
        base = index % 5
        numbers = sorted({1 + base, 2 + base, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15 + (index % 3)})
        cards.append(numbers[:15])
    return cards


def test_dezena_frequency_profile_normalized() -> None:
    profile = dezena_frequency_profile(_sample_cards(5))
    assert len(profile) == 25
    assert abs(sum(profile.values()) - 1.0) < 0.001


def test_structural_fidelity_score_between_zero_and_hundred() -> None:
    cards = _sample_cards(10)
    result = compute_structural_fidelity_score(cards, cards)
    assert 90.0 <= float(result["structural_fidelity_score"]) <= 100.0
    assert result["status_level"] == "sovereign"


def test_resolve_fidelity_status_thresholds() -> None:
    assert resolve_fidelity_status(95.0)["level"] == "sovereign"
    assert resolve_fidelity_status(80.0)["level"] == "warning"
    assert resolve_fidelity_status(55.0)["level"] == "critical"


def test_build_quadrant_occupancy_sums_to_one() -> None:
    occupancy = build_quadrant_occupancy(_sample_cards(8))
    assert abs(sum(occupancy.values()) - 1.0) < 0.001


def test_build_structural_intelligence_bundle_with_sqlite(tmp_path) -> None:
    from lotoia.database.database import create_database

    db_path = tmp_path / "modern.db"
    create_database(db_path)
    bundle = build_structural_intelligence_bundle(db_path, cards=_sample_cards(6), official_window=10)
    assert bundle.get("available") is True
    assert bundle.get("mission_id") == MISSION_ID
    assert float(bundle.get("fidelity", {}).get("structural_fidelity_score", -1)) >= 0.0


def test_time_travel_options_merge_memory() -> None:
    generations = [
        {"generation_event_id": 10, "dropdown_label": "Geração 10", "created_at": "2026-06-01"},
    ]
    memory = [{"generation_event_id": 10, "recorded_at": "2026-06-01T12:00:00Z"}]
    options = build_time_travel_options(generations, memory)
    assert len(options) == 1
    assert options[0]["memory"] is not None


def test_plotly_chart_builders_return_figures() -> None:
    cards = _sample_cards(4)
    fidelity = compute_structural_fidelity_score(cards, cards)
    gauge = _build_fidelity_gauge(float(fidelity["structural_fidelity_score"]), status_color="#1b8a5a")
    radar = _build_dezena_radar_chart(fidelity["generated_profile"], fidelity["official_profile"])
    assert gauge.data
    assert radar.data


def test_institutional_app_wires_modern_coverage_dashboard() -> None:
    import dashboard.institutional_app as institutional_app

    source = inspect.getsource(institutional_app._render_cobertura_estrutural_page)
    assert "render_modern_structural_coverage_dashboard" in source
    assert "structural_coverage_time_travel_slider" in inspect.getsource(
        __import__("dashboard.institutional_structural_coverage_modern", fromlist=["*"])
    )


def test_build_marker_v97() -> None:
    from dashboard.institutional_build import BUILD_MARKER

    assert BUILD_MARKER == "institutional-adm-runtime-v97"


def test_structural_coverage_legacy_diagnostics_visible_not_collapsed() -> None:
    import dashboard.institutional_app as institutional_app

    modern_source = inspect.getsource(
        __import__("dashboard.institutional_structural_coverage_modern", fromlist=["*"])
    )
    assert "Diagnóstico estrutural detalhado (modo legado)" in modern_source
    assert "st.subheader(\"Diagnóstico estrutural detalhado (modo legado)\")" in modern_source
    assert "with st.expander(\"Diagnóstico estrutural detalhado (modo legado)\"" not in modern_source

    diagnostics_source = inspect.getsource(institutional_app._render_structural_coverage_diagnostics_body)
    assert "_render_active_reading_exclusions_banner" not in diagnostics_source
    assert "_render_excluded_batches_audit_inline" not in diagnostics_source
    assert "st.expander(" not in diagnostics_source
