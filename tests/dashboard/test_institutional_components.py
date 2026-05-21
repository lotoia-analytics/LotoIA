from __future__ import annotations

from contextlib import contextmanager

import pandas as pd

import dashboard.components as institutional_components
import dashboard.components.analytical_cards as analytical_cards
import dashboard.components.executive_dashboard as executive_dashboard
import dashboard.components.executive_panel as executive_panel
import dashboard.components.executive_summary as executive_summary
import dashboard.components.generation_context as generation_context
import dashboard.components.hero_banner as hero_banner
import dashboard.components.live_status_header as live_status_header
import dashboard.components.institutional_timeline as institutional_timeline
import dashboard.components.secondary_metrics as secondary_metrics
import dashboard.components.structural_health as structural_health


@contextmanager
def _noop_context():
    yield None


class _DummyColumn:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def metric(self, *args, **kwargs):
        return None


def _patch_streamlit(monkeypatch) -> None:
    for module in [
        hero_banner,
        executive_panel,
        analytical_cards,
        executive_dashboard,
        generation_context,
        live_status_header,
        institutional_timeline,
        secondary_metrics,
        structural_health,
        executive_summary,
    ]:
        monkeypatch.setattr(module.st, "markdown", lambda *args, **kwargs: None)
        monkeypatch.setattr(module.st, "caption", lambda *args, **kwargs: None)
        monkeypatch.setattr(module.st, "info", lambda *args, **kwargs: None)
        monkeypatch.setattr(module.st, "dataframe", lambda *args, **kwargs: None)
        monkeypatch.setattr(module.st, "columns", lambda count: [_DummyColumn() for _ in range(count)])


def test_executive_components_render_without_error(monkeypatch) -> None:
    _patch_streamlit(monkeypatch)
    executive_report = {"status": "saudavel", "baseline_mode": "hard", "headline": "baseline longitudinal consistente", "recommendation": "manter baseline hard e monitorar longitudinalmente"}
    analytical_summary = {"confidence": "alta", "drift": 0.12, "structural_health": 0.93}
    historical_summary = {"trend": "estavel", "verdict_count": 2}
    snapshot_summary = {"status": "saudavel", "trend": "estavel"}

    hero_banner.render_hero_banner(executive_report, analytical_summary, historical_summary)
    executive_panel.render_executive_panel(executive_report, analytical_summary, historical_summary)
    analytical_cards.render_analytical_cards({"coverage_10": 0.5, "coverage_11": 0.2, "drift": 0.12, "structural_health": 0.93})
    structural_health.render_structural_health(analytical_summary, historical_summary)
    executive_summary.render_executive_summary(executive_report, historical_summary, snapshot_summary)


def test_hero_banner_renders_without_error(monkeypatch) -> None:
    _patch_streamlit(monkeypatch)
    executive_report = {"status": "saudavel", "baseline_mode": "hard", "headline": "baseline longitudinal consistente", "recommendation": "manter baseline hard e monitorar longitudinalmente"}
    analytical_summary = {"confidence": "alta", "drift": 0.12, "structural_health": 0.93}
    historical_summary = {"trend": "estavel"}

    hero_banner.render_hero_banner(executive_report, analytical_summary, historical_summary)


def test_executive_dashboard_renders_without_error(monkeypatch) -> None:
    _patch_streamlit(monkeypatch)
    executive_report = {"status": "saudavel", "baseline_mode": "hard", "headline": "baseline longitudinal consistente", "recommendation": "manter baseline hard e monitorar longitudinalmente"}
    analytical_summary = {"confidence": "alta", "drift": 0.12, "structural_health": 0.93, "coverage_10": 0.52, "coverage_11": 0.21}
    historical_summary = {"trend": "estavel", "verdict_count": 2}
    snapshot_summary = {"status": "saudavel", "trend": "estavel"}
    timeline = pd.DataFrame(
        [
            {
                "created_at": "2026-05-21T00:00:00+00:00",
                "status": "saudavel",
                "previous_status": "observacao",
                "status_transition": "observacao -> saudavel",
                "headline": "baseline longitudinal consistente",
                "recommendation": "manter baseline hard e monitorar longitudinalmente",
                "trend": "estavel",
                "verdict_count": 2,
                "confidence": "alta",
                "source": "reports/analytics",
            }
        ]
    )

    observability_summary = {"summary": {"stability_note": "cockpit institucional validado", "institutional_snapshot_ready": True}}
    executive_dashboard.render_executive_dashboard(executive_report, analytical_summary, historical_summary, snapshot_summary, observability_summary, timeline)


def test_live_status_header_renders_without_error(monkeypatch) -> None:
    _patch_streamlit(monkeypatch)
    executive_report = {"status": "saudavel", "baseline_mode": "hard", "drift": 0.12, "confidence": "alta"}
    analytical_summary = {"confidence": "alta", "drift": 0.12}
    historical_summary = {"trend": "estavel"}
    observability_summary = {"summary": {"stability_note": "cockpit institucional validado", "institutional_snapshot_ready": True}}

    live_status_header.render_live_status_header(executive_report, analytical_summary, historical_summary, observability_summary)


def test_institutional_timeline_renders_dataframe(monkeypatch) -> None:
    _patch_streamlit(monkeypatch)
    timeline = pd.DataFrame(
        [
            {
                "created_at": "2026-05-21T00:00:00+00:00",
                "status": "saudavel",
                "previous_status": "observacao",
                "status_transition": "observacao -> saudavel",
                "headline": "baseline longitudinal consistente",
                "recommendation": "manter baseline hard e monitorar longitudinalmente",
                "trend": "estavel",
                "verdict_count": 2,
                "confidence": "alta",
                "source": "reports/analytics",
            }
        ]
    )

    institutional_timeline.render_institutional_timeline(timeline)


def test_secondary_operational_metrics_renders_without_error(monkeypatch) -> None:
    _patch_streamlit(monkeypatch)
    secondary_metrics.render_secondary_operational_metrics(12, 8, "5000", "24")


def test_generation_context_renders_without_error(monkeypatch) -> None:
    _patch_streamlit(monkeypatch)
    executive_report = {"status": "saudavel", "baseline_mode": "hard", "drift": 0.12, "confidence": "alta"}
    historical_summary = {"trend": "estavel"}
    observability_summary = {"counts": {"generation_events": 42}, "summary": {"stability_note": "cockpit institucional validado"}}

    generation_context.render_generation_context(executive_report, historical_summary, observability_summary)


def test_institutional_components_package_exports_are_callable() -> None:
    expected_exports = {
        "render_analytical_cards",
        "render_executive_dashboard",
        "render_hero_banner",
        "render_executive_panel",
        "render_executive_summary",
        "render_generation_context",
        "render_live_status_header",
        "render_institutional_timeline",
        "render_secondary_operational_metrics",
        "render_structural_health",
    }

    assert expected_exports.issubset(set(institutional_components.__all__))
    for export_name in expected_exports:
        assert callable(getattr(institutional_components, export_name))
