from __future__ import annotations

from contextlib import contextmanager

import pandas as pd

import dashboard.components as institutional_components
import dashboard.components.analytical_cards as analytical_cards
import dashboard.components.adaptive_intelligence as adaptive_intelligence
import dashboard.components.design_system as design_system
import dashboard.components.executive_dashboard as executive_dashboard
import dashboard.components.executive_panel as executive_panel
import dashboard.components.executive_summary as executive_summary
import dashboard.components.generation_context as generation_context
import dashboard.components.live_analytical_intelligence as live_analytical_intelligence
import dashboard.components.hero_banner as hero_banner
import dashboard.components.live_status_header as live_status_header
import dashboard.components.institutional_timeline as institutional_timeline
import dashboard.components.operational_orchestration as operational_orchestration
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
        adaptive_intelligence,
        design_system,
        executive_dashboard,
        generation_context,
        live_analytical_intelligence,
        live_status_header,
        institutional_timeline,
        operational_orchestration,
        secondary_metrics,
        structural_health,
        executive_summary,
    ]:
        monkeypatch.setattr(module.st, "markdown", lambda *args, **kwargs: None)
        monkeypatch.setattr(module.st, "caption", lambda *args, **kwargs: None)
        monkeypatch.setattr(module.st, "info", lambda *args, **kwargs: None)
        monkeypatch.setattr(module.st, "dataframe", lambda *args, **kwargs: None)
        monkeypatch.setattr(module.st, "line_chart", lambda *args, **kwargs: None)
        monkeypatch.setattr(module.st, "metric", lambda *args, **kwargs: None)
        monkeypatch.setattr(
            module.st,
            "columns",
            lambda count, *args, **kwargs: [_DummyColumn() for _ in range(count if isinstance(count, int) else len(count))],
        )


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


def test_executive_dashboard_uses_modular_layout(monkeypatch) -> None:
    calls: list[str] = []

    _patch_streamlit(monkeypatch)

    def _mark(*args, **kwargs):
        if args:
            calls.append(str(args[0]))

    monkeypatch.setattr(executive_dashboard.st, "markdown", _mark)
    monkeypatch.setattr(
        executive_dashboard.st,
        "columns",
        lambda widths, *args, **kwargs: [_DummyColumn() for _ in range(widths if isinstance(widths, int) else len(widths))],
    )
    monkeypatch.setattr(executive_dashboard.st, "expander", lambda *args, **kwargs: _noop_context())

    executive_report = {
        "status": "saudavel",
        "baseline_mode": "hard",
        "headline": "baseline longitudinal consistente",
        "recommendation": "manter baseline hard e monitorar longitudinalmente",
        "drift": 0.12,
        "confidence": "alta",
    }
    analytical_summary = {"confidence": "alta", "drift": 0.12, "structural_health": 0.93, "coverage_10": 0.52, "coverage_11": 0.21}
    historical_summary = {"trend": "estavel", "verdict_count": 2}
    snapshot_summary = {"status": "saudavel", "trend": "estavel"}
    observability_summary = {"summary": {"stability_note": "cockpit institucional validado", "institutional_snapshot_ready": True}}
    timeline = pd.DataFrame([{ "created_at": "2026-05-21", "status": "saudavel" }])

    executive_dashboard.render_executive_dashboard(
        executive_report,
        analytical_summary,
        historical_summary,
        snapshot_summary,
        observability_summary,
        timeline,
    )

    assert any("Visao geral" in call for call in calls)


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
    secondary_metrics.render_secondary_operational_metrics(12, 8, 3, "5000", "24")


def test_operational_orchestration_renders_without_error(monkeypatch) -> None:
    _patch_streamlit(monkeypatch)
    operational_orchestration.render_operational_orchestration(
        {
            "report": {
                "summary": {
                    "orchestration_state": "coordenada",
                    "priority": "stable",
                    "critical_state": False,
                    "strong_stability": True,
                    "elevated_drift": False,
                    "important_change": True,
                    "timeline_depth": 2,
                    "memory_depth": 3,
                },
                "decision_context": {
                    "headline": "baseline longitudinal consistente",
                    "recommendation": "manter baseline hard e monitorar longitudinalmente",
                    "comparison": "historical trend and adaptive memory aligned",
                },
                "operational_priority": {
                    "critical_state": False,
                    "strong_stability": True,
                    "elevated_drift": False,
                    "important_change": True,
                },
                "storytelling": ["Contexto executivo: baseline consistente", "Prioridade operacional: stable"],
                "events": [{"layer": "executive", "status": "saudavel"}],
            }
        }
    )


def test_institutional_design_system_renders_without_error(monkeypatch) -> None:
    _patch_streamlit(monkeypatch)
    design_system.render_institutional_design_system()


def test_generation_context_renders_without_error(monkeypatch) -> None:
    _patch_streamlit(monkeypatch)
    executive_report = {"status": "saudavel", "baseline_mode": "hard", "drift": 0.12, "confidence": "alta"}
    historical_summary = {"trend": "estavel"}
    observability_summary = {"counts": {"generation_events": 42}, "summary": {"stability_note": "cockpit institucional validado"}}

    generation_context.render_generation_context(executive_report, historical_summary, observability_summary)


def test_adaptive_institutional_intelligence_renders_without_error(monkeypatch) -> None:
    _patch_streamlit(monkeypatch)
    adaptive_report = {
        "operational_memory": {
            "summary": {"memory_depth": 3},
            "timeline": [
                {
                    "created_at": "2026-05-21",
                    "status": "saudavel",
                    "headline": "baseline consistente",
                    "recommendation": "monitorar",
                    "confidence": "alta",
                    "structural_health": 0.93,
                    "drift": 0.12,
                    "trend": "estavel",
                    "source": "reports/analytics",
                }
            ],
        },
        "temporal_analysis": {
            "summary": {
                "trend": "evolucao estrutural",
                "recurring_statuses": 1,
                "persistent_changes": 1,
                "memory_depth": 3,
                "average_health_delta": 0.02,
                "drift_delta": -0.01,
                "historical_trend": "estavel",
            }
        },
        "pattern_detection": {"summary": {"pattern": "recorrencia institucional", "recurring_statuses": 1, "persistent_changes": 1, "memory_depth": 3}},
        "strategic_memory": {
            "timeline": [{"created_at": "2026-05-21", "headline": "baseline consistente", "recommendation": "monitorar", "status_transition": "inicio", "trend": "estavel"}],
            "summary": {"latest_headline": "baseline consistente", "latest_status": "saudavel", "trend": "estavel", "snapshot_status": "saudavel", "memory_depth": 1},
        },
        "adaptive_insights": {
            "insights": [{"metric": "continuity", "interpretation": "memoria operacional persistente"}],
            "summary": {"pattern": "recorrencia institucional", "trend": "evolucao estrutural", "memory_depth": 3},
        },
        "longitudinal_evolution_v2": {
            "summary": {
                "trend": "evolucao estrutural",
                "stability_evolution": 0.02,
                "drift_evolution": -0.01,
                "confidence_evolution": 0.1,
                "memory_depth": 3,
                "timeline_depth": 1,
            }
        },
        "observational_learning": {"summary": {"learning_mode": "observational_governed", "pattern": "recorrencia institucional", "trend": "evolucao estrutural", "memory_depth": 3}},
        "strategic_timeline": {
            "timeline": [{"created_at": "2026-05-21", "status": "saudavel", "headline": "baseline consistente", "recommendation": "monitorar", "status_transition": "inicio", "trend": "estavel", "source": "reports/analytics"}],
            "summary": {"trend": "evolucao estrutural", "latest_headline": "baseline consistente", "latest_transition": "inicio", "pattern": "recorrencia institucional", "memory_depth": 1},
        },
        "adaptive_presence": {"summary": {"presence": "adaptativa", "consistency": 0.91, "memory_depth": 3, "pattern": "recorrencia institucional", "trend": "evolucao estrutural"}},
    }

    adaptive_intelligence.render_adaptive_institutional_intelligence(adaptive_report)


def test_live_analytical_intelligence_renders_without_error(monkeypatch) -> None:
    _patch_streamlit(monkeypatch)
    analytical_report = {
        "analytical_summary": {
            "structural_health": 0.93,
            "confidence": "alta",
            "drift": 0.12,
            "coverage_10": 0.52,
            "coverage_11": 0.21,
            "interpretation": "baseline longitudinal consistente",
        },
        "insights": [
            {"metric": "stability", "value": 0.93, "interpretation": "baseline estavel", "confidence": "alta"}
        ],
        "comparisons": [
            {"label": "média de acertos", "baseline": 9.0, "compared": 9.2, "delta": 0.2, "interpretation": "crescimento longitudinal"}
        ],
    }
    executive_report = {
        "status": "saudavel",
        "baseline_mode": "hard",
        "headline": "baseline longitudinal consistente",
        "recommendation": "manter baseline hard e monitorar longitudinalmente",
    }
    historical_report = {"summary": {"trend": "estavel", "verdict_count": 3}}
    snapshot_report = {"summary": {"status": "saudavel"}}
    timeline = pd.DataFrame(
        [
            {
                "created_at": "2026-05-21",
                "headline": "baseline longitudinal consistente",
                "status_transition": "inicio",
                "recommendation": "manter baseline hard",
                "structural_health": 0.93,
                "drift": 0.12,
                "coverage_10": 0.52,
                "coverage_11": 0.21,
            },
            {
                "created_at": "2026-05-22",
                "headline": "baseline com cobertura alta",
                "status_transition": "mantido em saudavel",
                "recommendation": "manter baseline hard",
                "structural_health": 0.94,
                "drift": 0.11,
                "coverage_10": 0.53,
                "coverage_11": 0.22,
            },
        ]
    )
    observability_report = {"summary": {"stability_note": "cockpit institucional validado"}}

    live_analytical_intelligence.render_live_analytical_intelligence(
        analytical_report,
        executive_report,
        historical_report,
        snapshot_report,
        timeline,
        observability_report,
    )


def test_live_analytical_intelligence_uses_timeline_context(monkeypatch) -> None:
    captured: list[str] = []
    _patch_streamlit(monkeypatch)

    def _markdown(message, *args, **kwargs):
        captured.append(str(message))

    def _info(message, *args, **kwargs):
        captured.append(str(message))

    monkeypatch.setattr(live_analytical_intelligence.st, "markdown", _markdown)
    monkeypatch.setattr(live_analytical_intelligence.st, "info", _info)
    monkeypatch.setattr(live_analytical_intelligence.st, "line_chart", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_analytical_intelligence.st, "metric", lambda *args, **kwargs: None)

    analytical_report = {"analytical_summary": {"structural_health": 0.93, "confidence": "alta", "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21, "interpretation": "baseline longitudinal consistente"}, "insights": [], "comparisons": []}
    executive_report = {"status": "saudavel", "baseline_mode": "hard", "headline": "baseline longitudinal consistente", "recommendation": "manter baseline hard e monitorar longitudinalmente"}
    historical_report = {"summary": {"trend": "estavel", "verdict_count": 3}}
    snapshot_report = {"summary": {"status": "saudavel"}}
    timeline = pd.DataFrame([{"created_at": "2026-05-21", "headline": "baseline longitudinal consistente", "status_transition": "inicio", "recommendation": "manter baseline hard", "structural_health": 0.93, "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21}])
    observability_report = {"summary": {"stability_note": "cockpit institucional validado"}}

    live_analytical_intelligence.render_live_analytical_intelligence(
        analytical_report,
        executive_report,
        historical_report,
        snapshot_report,
        timeline,
        observability_report,
    )

    assert any("Inteligencia viva" in message or "evolucao" in message.lower() for message in captured)


def test_live_analytical_intelligence_reports_trend_direction(monkeypatch) -> None:
    captured: list[str] = []
    _patch_streamlit(monkeypatch)

    def _markdown(message, *args, **kwargs):
        captured.append(str(message))

    monkeypatch.setattr(live_analytical_intelligence.st, "markdown", _markdown)
    monkeypatch.setattr(live_analytical_intelligence.st, "line_chart", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_analytical_intelligence.st, "metric", lambda *args, **kwargs: None)

    analytical_report = {"analytical_summary": {"structural_health": 0.94, "confidence": "alta", "drift": 0.11, "coverage_10": 0.53, "coverage_11": 0.22, "interpretation": "baseline longitudinal consistente"}, "insights": [], "comparisons": []}
    executive_report = {"status": "saudavel", "baseline_mode": "hard", "headline": "baseline longitudinal consistente", "recommendation": "manter baseline hard e monitorar longitudinalmente"}
    historical_report = {"summary": {"trend": "melhoria controlada", "verdict_count": 3}}
    snapshot_report = {"summary": {"status": "saudavel"}}
    timeline = pd.DataFrame([
        {"created_at": "2026-05-21", "headline": "baseline longitudinal consistente", "status_transition": "inicio", "recommendation": "manter baseline hard", "structural_health": 0.90, "drift": 0.13, "coverage_10": 0.50, "coverage_11": 0.20},
        {"created_at": "2026-05-22", "headline": "baseline com cobertura alta", "status_transition": "mantido em saudavel", "recommendation": "manter baseline hard", "structural_health": 0.94, "drift": 0.11, "coverage_10": 0.53, "coverage_11": 0.22},
    ])
    observability_report = {"summary": {"stability_note": "cockpit institucional validado"}}

    live_analytical_intelligence.render_live_analytical_intelligence(
        analytical_report,
        executive_report,
        historical_report,
        snapshot_report,
        timeline,
        observability_report,
    )

    assert any("melhorou" in message or "cresceu levemente" in message or "ganhou tracao" in message for message in captured)


def test_live_analytical_intelligence_includes_longitudinal_memory(monkeypatch) -> None:
    captured: list[str] = []
    _patch_streamlit(monkeypatch)

    def _markdown(message, *args, **kwargs):
        captured.append(str(message))

    monkeypatch.setattr(live_analytical_intelligence.st, "markdown", _markdown)
    monkeypatch.setattr(live_analytical_intelligence.st, "line_chart", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_analytical_intelligence.st, "metric", lambda *args, **kwargs: None)

    analytical_report = {"analytical_summary": {"structural_health": 0.93, "confidence": "alta", "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21, "interpretation": "baseline longitudinal consistente"}, "insights": [], "comparisons": []}
    executive_report = {"status": "saudavel", "baseline_mode": "hard", "headline": "baseline longitudinal consistente", "recommendation": "manter baseline hard e monitorar longitudinalmente"}
    historical_report = {"summary": {"trend": "estavel", "verdict_count": 3, "latest_status": "saudavel", "latest_transition": "inicio"}}
    snapshot_report = {"summary": {"status": "saudavel"}}
    timeline = pd.DataFrame(
        [
            {"created_at": "2026-05-21", "headline": "baseline longitudinal consistente", "status_transition": "inicio", "recommendation": "manter baseline hard", "structural_health": 0.93, "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21},
        ]
    )
    observability_report = {"summary": {"stability_note": "cockpit institucional validado"}}

    live_analytical_intelligence.render_live_analytical_intelligence(
        analytical_report,
        executive_report,
        historical_report,
        snapshot_report,
        timeline,
        observability_report,
    )

    assert any("Evolucao longitudinal" in message or "Memoria operacional" in message or "Insight" in message for message in captured)


def test_live_analytical_intelligence_renders_executive_graphics(monkeypatch) -> None:
    captured: list[str] = []
    _patch_streamlit(monkeypatch)

    def _markdown(message, *args, **kwargs):
        captured.append(str(message))

    monkeypatch.setattr(live_analytical_intelligence.st, "markdown", _markdown)
    monkeypatch.setattr(live_analytical_intelligence.st, "line_chart", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_analytical_intelligence.st, "metric", lambda *args, **kwargs: None)

    analytical_report = {"analytical_summary": {"structural_health": 0.93, "confidence": "alta", "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21, "interpretation": "baseline longitudinal consistente"}, "insights": [], "comparisons": []}
    executive_report = {"status": "saudavel", "baseline_mode": "hard", "headline": "baseline longitudinal consistente", "recommendation": "manter baseline hard e monitorar longitudinalmente"}
    historical_report = {"summary": {"trend": "estavel", "verdict_count": 3, "latest_status": "saudavel", "latest_transition": "inicio"}}
    snapshot_report = {"summary": {"status": "saudavel"}}
    timeline = pd.DataFrame(
        [
            {"created_at": "2026-05-21", "headline": "baseline longitudinal consistente", "status_transition": "inicio", "recommendation": "manter baseline hard", "structural_health": 0.93, "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21},
        ]
    )
    observability_report = {"summary": {"stability_note": "cockpit institucional validado"}}

    live_analytical_intelligence.render_live_analytical_intelligence(
        analytical_report,
        executive_report,
        historical_report,
        snapshot_report,
        timeline,
        observability_report,
    )

    assert any("Graficos executivos" in message or "Media de acertos" in message or "Score x acertos" in message for message in captured)


def test_live_analytical_intelligence_shows_runtime_memory(monkeypatch) -> None:
    captured: list[str] = []
    _patch_streamlit(monkeypatch)

    def _markdown(message, *args, **kwargs):
        captured.append(str(message))

    def _caption(message, *args, **kwargs):
        captured.append(str(message))

    monkeypatch.setattr(live_analytical_intelligence.st, "markdown", _markdown)
    monkeypatch.setattr(live_analytical_intelligence.st, "caption", _caption)
    monkeypatch.setattr(live_analytical_intelligence.st, "line_chart", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_analytical_intelligence.st, "metric", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_analytical_intelligence.st, "progress", lambda *args, **kwargs: None)

    analytical_report = {"analytical_summary": {"structural_health": 0.93, "confidence": "alta", "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21, "interpretation": "baseline longitudinal consistente"}, "insights": [], "comparisons": []}
    executive_report = {"status": "saudavel", "baseline_mode": "hard", "headline": "baseline longitudinal consistente", "recommendation": "manter baseline hard e monitorar longitudinalmente"}
    historical_report = {"summary": {"trend": "estavel", "verdict_count": 3, "latest_status": "saudavel", "latest_transition": "inicio"}}
    snapshot_report = {"summary": {"status": "saudavel"}}
    timeline = pd.DataFrame(
        [
            {"created_at": "2026-05-21", "headline": "baseline longitudinal consistente", "status_transition": "inicio", "recommendation": "manter baseline hard", "structural_health": 0.93, "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21},
            {"created_at": "2026-05-22", "headline": "baseline longitudinal consistente", "status_transition": "mantido", "recommendation": "manter baseline hard", "structural_health": 0.94, "drift": 0.11, "coverage_10": 0.53, "coverage_11": 0.22},
            {"created_at": "2026-05-23", "headline": "baseline longitudinal consistente", "status_transition": "estavel", "recommendation": "manter baseline hard", "structural_health": 0.95, "drift": 0.10, "coverage_10": 0.54, "coverage_11": 0.23},
        ]
    )
    observability_report = {"summary": {"stability_note": "cockpit institucional validado"}}

    live_analytical_intelligence.render_live_analytical_intelligence(
        analytical_report,
        executive_report,
        historical_report,
        snapshot_report,
        timeline,
        observability_report,
    )

    assert any("runtime" in message.lower() or "Memoria operacional percebida" in message or "Memoria operacional" in message for message in captured)


def test_live_analytical_intelligence_reports_executive_continuity(monkeypatch) -> None:
    captured: list[str] = []
    _patch_streamlit(monkeypatch)

    def _caption(message, *args, **kwargs):
        captured.append(str(message))

    monkeypatch.setattr(live_analytical_intelligence.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_analytical_intelligence.st, "caption", _caption)
    monkeypatch.setattr(live_analytical_intelligence.st, "line_chart", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_analytical_intelligence.st, "metric", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_analytical_intelligence.st, "progress", lambda *args, **kwargs: None)

    analytical_report = {"analytical_summary": {"structural_health": 0.93, "confidence": "alta", "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21, "interpretation": "baseline longitudinal consistente"}, "insights": [], "comparisons": []}
    executive_report = {"status": "saudavel", "baseline_mode": "hard", "headline": "baseline longitudinal consistente", "recommendation": "manter baseline hard e monitorar longitudinalmente"}
    historical_report = {"summary": {"trend": "estavel", "verdict_count": 3, "latest_status": "saudavel", "latest_transition": "inicio"}}
    snapshot_report = {"summary": {"status": "saudavel"}}
    timeline = pd.DataFrame(
        [
            {"created_at": "2026-05-21", "headline": "baseline longitudinal consistente", "status_transition": "inicio", "recommendation": "manter baseline hard", "structural_health": 0.93, "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21},
            {"created_at": "2026-05-22", "headline": "baseline longitudinal consistente", "status_transition": "mantido", "recommendation": "manter baseline hard", "structural_health": 0.94, "drift": 0.11, "coverage_10": 0.53, "coverage_11": 0.22},
            {"created_at": "2026-05-23", "headline": "baseline longitudinal consistente", "status_transition": "estavel", "recommendation": "manter baseline hard", "structural_health": 0.95, "drift": 0.10, "coverage_10": 0.54, "coverage_11": 0.23},
        ]
    )
    observability_report = {"summary": {"stability_note": "cockpit institucional validado"}}

    live_analytical_intelligence.render_live_analytical_intelligence(
        analytical_report,
        executive_report,
        historical_report,
        snapshot_report,
        timeline,
        observability_report,
    )

    assert any("Continuidade executiva" in message or "forte" in message or "em consolidacao" in message for message in captured)


def test_live_analytical_intelligence_shows_live_pulse(monkeypatch) -> None:
    captured: list[str] = []
    _patch_streamlit(monkeypatch)

    def _markdown(message, *args, **kwargs):
        captured.append(str(message))

    monkeypatch.setattr(live_analytical_intelligence.st, "markdown", _markdown)
    monkeypatch.setattr(live_analytical_intelligence.st, "line_chart", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_analytical_intelligence.st, "metric", lambda *args, **kwargs: None)

    analytical_report = {"analytical_summary": {"structural_health": 0.93, "confidence": "alta", "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21, "interpretation": "baseline longitudinal consistente"}, "insights": [], "comparisons": []}
    executive_report = {"status": "saudavel", "baseline_mode": "hard", "headline": "baseline longitudinal consistente", "recommendation": "manter baseline hard e monitorar longitudinalmente"}
    historical_report = {"summary": {"trend": "estavel", "verdict_count": 3, "latest_status": "saudavel", "latest_transition": "inicio"}}
    snapshot_report = {"summary": {"status": "saudavel"}}
    timeline = pd.DataFrame(
        [
            {"created_at": "2026-05-21", "headline": "baseline longitudinal consistente", "status_transition": "inicio", "recommendation": "manter baseline hard", "structural_health": 0.93, "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21},
            {"created_at": "2026-05-22", "headline": "baseline longitudinal consistente", "status_transition": "mantido", "recommendation": "manter baseline hard", "structural_health": 0.94, "drift": 0.11, "coverage_10": 0.53, "coverage_11": 0.22},
            {"created_at": "2026-05-23", "headline": "baseline longitudinal consistente", "status_transition": "estavel", "recommendation": "manter baseline hard", "structural_health": 0.95, "drift": 0.10, "coverage_10": 0.54, "coverage_11": 0.23},
        ]
    )
    observability_report = {"summary": {"stability_note": "cockpit institucional validado"}}

    live_analytical_intelligence.render_live_analytical_intelligence(
        analytical_report,
        executive_report,
        historical_report,
        snapshot_report,
        timeline,
        observability_report,
    )

    assert any("live pulse" in message or "memory" in message.lower() for message in captured)


def test_live_analytical_intelligence_shows_institutional_presence(monkeypatch) -> None:
    captured: list[str] = []
    _patch_streamlit(monkeypatch)

    def _markdown(message, *args, **kwargs):
        captured.append(str(message))

    monkeypatch.setattr(live_analytical_intelligence.st, "markdown", _markdown)
    monkeypatch.setattr(live_analytical_intelligence.st, "line_chart", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_analytical_intelligence.st, "metric", lambda *args, **kwargs: None)

    analytical_report = {"analytical_summary": {"structural_health": 0.93, "confidence": "alta", "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21, "interpretation": "baseline longitudinal consistente"}, "insights": [], "comparisons": []}
    executive_report = {"status": "saudavel", "baseline_mode": "hard", "headline": "baseline longitudinal consistente", "recommendation": "manter baseline hard e monitorar longitudinalmente"}
    historical_report = {"summary": {"trend": "estavel", "verdict_count": 3, "latest_status": "saudavel", "latest_transition": "inicio"}}
    snapshot_report = {"summary": {"status": "saudavel"}}
    timeline = pd.DataFrame(
        [
            {"created_at": "2026-05-21", "headline": "baseline longitudinal consistente", "status_transition": "inicio", "recommendation": "manter baseline hard", "structural_health": 0.93, "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21},
            {"created_at": "2026-05-22", "headline": "baseline longitudinal consistente", "status_transition": "mantido", "recommendation": "manter baseline hard", "structural_health": 0.94, "drift": 0.11, "coverage_10": 0.53, "coverage_11": 0.22},
            {"created_at": "2026-05-23", "headline": "baseline longitudinal consistente", "status_transition": "estavel", "recommendation": "manter baseline hard", "structural_health": 0.95, "drift": 0.10, "coverage_10": 0.54, "coverage_11": 0.23},
        ]
    )
    observability_report = {"summary": {"stability_note": "cockpit institucional validado"}}

    live_analytical_intelligence.render_live_analytical_intelligence(
        analytical_report,
        executive_report,
        historical_report,
        snapshot_report,
        timeline,
        observability_report,
    )

    assert any("Presenca institucional" in message or "memoria ativa" in message or "sistema vivo" in message for message in captured)


def test_live_analytical_intelligence_shows_consistency_seal(monkeypatch) -> None:
    captured: list[str] = []
    _patch_streamlit(monkeypatch)

    def _markdown(message, *args, **kwargs):
        captured.append(str(message))

    monkeypatch.setattr(live_analytical_intelligence.st, "markdown", _markdown)
    monkeypatch.setattr(live_analytical_intelligence.st, "line_chart", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_analytical_intelligence.st, "metric", lambda *args, **kwargs: None)

    analytical_report = {"analytical_summary": {"structural_health": 0.93, "confidence": "alta", "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21, "interpretation": "baseline longitudinal consistente"}, "insights": [], "comparisons": []}
    executive_report = {"status": "saudavel", "baseline_mode": "hard", "headline": "baseline longitudinal consistente", "recommendation": "manter baseline hard e monitorar longitudinalmente"}
    historical_report = {"summary": {"trend": "estavel", "verdict_count": 3, "latest_status": "saudavel", "latest_transition": "inicio"}}
    snapshot_report = {"summary": {"status": "saudavel"}}
    timeline = pd.DataFrame(
        [
            {"created_at": "2026-05-21", "headline": "baseline longitudinal consistente", "status_transition": "inicio", "recommendation": "manter baseline hard", "structural_health": 0.93, "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21},
            {"created_at": "2026-05-22", "headline": "baseline longitudinal consistente", "status_transition": "mantido", "recommendation": "manter baseline hard", "structural_health": 0.94, "drift": 0.11, "coverage_10": 0.53, "coverage_11": 0.22},
            {"created_at": "2026-05-23", "headline": "baseline longitudinal consistente", "status_transition": "estavel", "recommendation": "manter baseline hard", "structural_health": 0.95, "drift": 0.10, "coverage_10": 0.54, "coverage_11": 0.23},
        ]
    )
    observability_report = {"summary": {"stability_note": "cockpit institucional validado"}}

    live_analytical_intelligence.render_live_analytical_intelligence(
        analytical_report,
        executive_report,
        historical_report,
        snapshot_report,
        timeline,
        observability_report,
    )

    assert any("Selo de consistencia" in message or "Traceability" in message or "Consistency" in message for message in captured)


def test_live_analytical_intelligence_shows_institutional_evolution_summary(monkeypatch) -> None:
    captured: list[str] = []
    _patch_streamlit(monkeypatch)

    def _markdown(message, *args, **kwargs):
        captured.append(str(message))

    def _caption(message, *args, **kwargs):
        captured.append(str(message))

    monkeypatch.setattr(live_analytical_intelligence.st, "markdown", _markdown)
    monkeypatch.setattr(live_analytical_intelligence.st, "caption", _caption)
    monkeypatch.setattr(live_analytical_intelligence.st, "line_chart", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_analytical_intelligence.st, "metric", lambda *args, **kwargs: None)

    analytical_report = {"analytical_summary": {"structural_health": 0.93, "confidence": "alta", "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21, "interpretation": "baseline longitudinal consistente"}, "insights": [], "comparisons": []}
    executive_report = {"status": "saudavel", "baseline_mode": "hard", "headline": "baseline longitudinal consistente", "recommendation": "manter baseline hard e monitorar longitudinalmente"}
    historical_report = {"summary": {"trend": "estavel", "verdict_count": 3, "latest_status": "saudavel", "latest_transition": "inicio"}}
    snapshot_report = {"summary": {"status": "saudavel"}}
    timeline = pd.DataFrame(
        [
            {"created_at": "2026-05-21", "headline": "baseline longitudinal consistente", "status_transition": "inicio", "recommendation": "manter baseline hard", "structural_health": 0.93, "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21},
            {"created_at": "2026-05-22", "headline": "baseline longitudinal consistente", "status_transition": "mantido", "recommendation": "manter baseline hard", "structural_health": 0.94, "drift": 0.11, "coverage_10": 0.53, "coverage_11": 0.22},
            {"created_at": "2026-05-23", "headline": "baseline longitudinal consistente", "status_transition": "estavel", "recommendation": "manter baseline hard", "structural_health": 0.95, "drift": 0.10, "coverage_10": 0.54, "coverage_11": 0.23},
        ]
    )
    observability_report = {"summary": {"stability_note": "cockpit institucional validado"}}

    live_analytical_intelligence.render_live_analytical_intelligence(
        analytical_report,
        executive_report,
        historical_report,
        snapshot_report,
        timeline,
        observability_report,
    )

    assert any("Resumo evolutivo" in message or "resumo longitudinal" in message or "Direcao institucional" in message for message in captured)


def test_live_analytical_intelligence_renders_longitudinal_comparison_rail(monkeypatch) -> None:
    captured: list[str] = []
    _patch_streamlit(monkeypatch)

    def _markdown(message, *args, **kwargs):
        captured.append(str(message))

    monkeypatch.setattr(live_analytical_intelligence.st, "markdown", _markdown)
    monkeypatch.setattr(live_analytical_intelligence.st, "line_chart", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_analytical_intelligence.st, "metric", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        live_analytical_intelligence,
        "_load_longitudinal_report",
        lambda: {
            "baseline_mode": "hard",
            "summary": {"coverage_10": 0.0, "coverage_11": 0.0, "stability_index": 0.82},
            "runs": [
                {"checkpoint": 10, "result": {"lotoia": {"average_hits": 9.01, "stability_window_sd": 0.60, "final_score_hit_correlation": 0.01}, "contests_analyzed": 10}},
                {"checkpoint": 25, "result": {"lotoia": {"average_hits": 9.10, "stability_window_sd": 0.58, "final_score_hit_correlation": 0.02}, "contests_analyzed": 25}},
                {"checkpoint": 50, "result": {"lotoia": {"average_hits": 9.14, "stability_window_sd": 0.57, "final_score_hit_correlation": 0.01}, "contests_analyzed": 50}},
                {"checkpoint": 100, "result": {"lotoia": {"average_hits": 9.09, "stability_window_sd": 0.56, "final_score_hit_correlation": 0.00}, "contests_analyzed": 100}},
            ],
        },
    )

    analytical_report = {"analytical_summary": {"structural_health": 0.93, "confidence": "alta", "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21, "interpretation": "baseline longitudinal consistente"}, "insights": [], "comparisons": []}
    executive_report = {"status": "saudavel", "baseline_mode": "hard", "headline": "baseline longitudinal consistente", "recommendation": "manter baseline hard e monitorar longitudinalmente"}
    historical_report = {"summary": {"trend": "estavel", "verdict_count": 3, "latest_status": "saudavel", "latest_transition": "inicio"}}
    snapshot_report = {"summary": {"status": "saudavel"}}
    timeline = pd.DataFrame([{"created_at": "2026-05-21", "headline": "baseline longitudinal consistente", "status_transition": "inicio", "recommendation": "manter baseline hard", "structural_health": 0.93, "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21}])
    observability_report = {"summary": {"stability_note": "cockpit institucional validado"}}

    live_analytical_intelligence.render_live_analytical_intelligence(
        analytical_report,
        executive_report,
        historical_report,
        snapshot_report,
        timeline,
        observability_report,
    )

    assert any("checkpoint 10" in message or "checkpoint 100" in message for message in captured)


def test_live_analytical_intelligence_renders_comparison_summary(monkeypatch) -> None:
    captured: list[str] = []
    _patch_streamlit(monkeypatch)

    def _markdown(message, *args, **kwargs):
        captured.append(str(message))

    monkeypatch.setattr(live_analytical_intelligence.st, "markdown", _markdown)
    monkeypatch.setattr(live_analytical_intelligence.st, "line_chart", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_analytical_intelligence.st, "metric", lambda *args, **kwargs: None)

    analytical_report = {"analytical_summary": {"structural_health": 0.93, "confidence": "alta", "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21, "interpretation": "baseline longitudinal consistente"}, "insights": [], "comparisons": []}
    executive_report = {"status": "saudavel", "baseline_mode": "hard", "headline": "baseline longitudinal consistente", "recommendation": "manter baseline hard e monitorar longitudinalmente"}
    historical_report = {"summary": {"trend": "estavel", "verdict_count": 3, "latest_status": "saudavel", "latest_transition": "inicio"}}
    snapshot_report = {"summary": {"status": "saudavel"}}
    timeline = pd.DataFrame(
        [
            {"created_at": "2026-05-21", "headline": "baseline longitudinal consistente", "status_transition": "inicio", "recommendation": "manter baseline hard", "structural_health": 0.93, "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21},
            {"created_at": "2026-05-22", "headline": "baseline longitudinal consistente", "status_transition": "mantido", "recommendation": "manter baseline hard", "structural_health": 0.94, "drift": 0.11, "coverage_10": 0.53, "coverage_11": 0.22},
        ]
    )
    observability_report = {"summary": {"stability_note": "cockpit institucional validado"}}

    live_analytical_intelligence.render_live_analytical_intelligence(
        analytical_report,
        executive_report,
        historical_report,
        snapshot_report,
        timeline,
        observability_report,
    )

    assert any("Hits delta" in message or "Memory depth" in message or "Stability delta" in message for message in captured)


def test_live_analytical_intelligence_renders_consistency_seal(monkeypatch) -> None:
    captured: list[str] = []
    _patch_streamlit(monkeypatch)

    def _markdown(message, *args, **kwargs):
        captured.append(str(message))

    monkeypatch.setattr(live_analytical_intelligence.st, "markdown", _markdown)
    monkeypatch.setattr(live_analytical_intelligence.st, "line_chart", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_analytical_intelligence.st, "metric", lambda *args, **kwargs: None)

    analytical_report = {"analytical_summary": {"structural_health": 0.93, "confidence": "alta", "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21, "interpretation": "baseline longitudinal consistente"}, "insights": [], "comparisons": []}
    executive_report = {"status": "saudavel", "baseline_mode": "hard", "headline": "baseline longitudinal consistente", "recommendation": "manter baseline hard e monitorar longitudinalmente"}
    historical_report = {"summary": {"trend": "estavel", "verdict_count": 3, "latest_status": "saudavel", "latest_transition": "inicio"}}
    snapshot_report = {"summary": {"status": "saudavel"}}
    timeline = pd.DataFrame(
        [
            {"created_at": "2026-05-21", "headline": "baseline longitudinal consistente", "status_transition": "inicio", "recommendation": "manter baseline hard", "structural_health": 0.93, "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21},
            {"created_at": "2026-05-22", "headline": "baseline longitudinal consistente", "status_transition": "mantido", "recommendation": "manter baseline hard", "structural_health": 0.94, "drift": 0.11, "coverage_10": 0.53, "coverage_11": 0.22},
            {"created_at": "2026-05-23", "headline": "baseline longitudinal consistente", "status_transition": "estavel", "recommendation": "manter baseline hard", "structural_health": 0.95, "drift": 0.10, "coverage_10": 0.54, "coverage_11": 0.23},
        ]
    )
    observability_report = {"summary": {"stability_note": "cockpit institucional validado"}}

    live_analytical_intelligence.render_live_analytical_intelligence(
        analytical_report,
        executive_report,
        historical_report,
        snapshot_report,
        timeline,
        observability_report,
    )

    assert any("Selo de consistencia" in message or "Traceability" in message or "Estado institucional" in message for message in captured)


def test_live_analytical_intelligence_renders_final_institutional_posture(monkeypatch) -> None:
    captured: list[str] = []
    _patch_streamlit(monkeypatch)

    def _markdown(message, *args, **kwargs):
        captured.append(str(message))

    monkeypatch.setattr(live_analytical_intelligence.st, "markdown", _markdown)
    monkeypatch.setattr(live_analytical_intelligence.st, "line_chart", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_analytical_intelligence.st, "metric", lambda *args, **kwargs: None)

    analytical_report = {"analytical_summary": {"structural_health": 0.93, "confidence": "alta", "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21, "interpretation": "baseline longitudinal consistente"}, "insights": [], "comparisons": []}
    executive_report = {"status": "saudavel", "baseline_mode": "hard", "headline": "baseline longitudinal consistente", "recommendation": "manter baseline hard e monitorar longitudinalmente"}
    historical_report = {"summary": {"trend": "estavel", "verdict_count": 3, "latest_status": "saudavel", "latest_transition": "inicio"}}
    snapshot_report = {"summary": {"status": "saudavel"}}
    timeline = pd.DataFrame(
        [
            {"created_at": "2026-05-21", "headline": "baseline longitudinal consistente", "status_transition": "inicio", "recommendation": "manter baseline hard", "structural_health": 0.93, "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21},
            {"created_at": "2026-05-22", "headline": "baseline longitudinal consistente", "status_transition": "mantido", "recommendation": "manter baseline hard", "structural_health": 0.94, "drift": 0.11, "coverage_10": 0.53, "coverage_11": 0.22},
            {"created_at": "2026-05-23", "headline": "baseline longitudinal consistente", "status_transition": "estavel", "recommendation": "manter baseline hard", "structural_health": 0.95, "drift": 0.10, "coverage_10": 0.54, "coverage_11": 0.23},
        ]
    )
    observability_report = {"summary": {"stability_note": "cockpit institucional validado"}}

    live_analytical_intelligence.render_live_analytical_intelligence(
        analytical_report,
        executive_report,
        historical_report,
        snapshot_report,
        timeline,
        observability_report,
    )

    assert any("Final institutional posture" in message or "Posture" in message or "Signal" in message for message in captured)


def test_live_analytical_intelligence_reports_final_message(monkeypatch) -> None:
    captured: list[str] = []
    _patch_streamlit(monkeypatch)

    def _caption(message, *args, **kwargs):
        captured.append(str(message))

    monkeypatch.setattr(live_analytical_intelligence.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_analytical_intelligence.st, "caption", _caption)
    monkeypatch.setattr(live_analytical_intelligence.st, "line_chart", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_analytical_intelligence.st, "metric", lambda *args, **kwargs: None)

    analytical_report = {"analytical_summary": {"structural_health": 0.93, "confidence": "alta", "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21, "interpretation": "baseline longitudinal consistente"}, "insights": [], "comparisons": []}
    executive_report = {"status": "saudavel", "baseline_mode": "hard", "headline": "baseline longitudinal consistente", "recommendation": "manter baseline hard e monitorar longitudinalmente"}
    historical_report = {"summary": {"trend": "estavel", "verdict_count": 3, "latest_status": "saudavel", "latest_transition": "inicio"}}
    snapshot_report = {"summary": {"status": "saudavel"}}
    timeline = pd.DataFrame(
        [
            {"created_at": "2026-05-21", "headline": "baseline longitudinal consistente", "status_transition": "inicio", "recommendation": "manter baseline hard", "structural_health": 0.93, "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21},
            {"created_at": "2026-05-22", "headline": "baseline longitudinal consistente", "status_transition": "mantido", "recommendation": "manter baseline hard", "structural_health": 0.94, "drift": 0.11, "coverage_10": 0.53, "coverage_11": 0.22},
            {"created_at": "2026-05-23", "headline": "baseline longitudinal consistente", "status_transition": "estavel", "recommendation": "manter baseline hard", "structural_health": 0.95, "drift": 0.10, "coverage_10": 0.54, "coverage_11": 0.23},
        ]
    )
    observability_report = {"summary": {"stability_note": "cockpit institucional validado"}}

    live_analytical_intelligence.render_live_analytical_intelligence(
        analytical_report,
        executive_report,
        historical_report,
        snapshot_report,
        timeline,
        observability_report,
    )

    assert any("leitura institucional permanece consistente" in message.lower() or "leitura institucional segue em consolidacao" in message.lower() for message in captured)


def test_live_analytical_intelligence_reports_executive_summary(monkeypatch) -> None:
    captured: list[str] = []
    _patch_streamlit(monkeypatch)

    def _info(message, *args, **kwargs):
        captured.append(str(message))

    monkeypatch.setattr(live_analytical_intelligence.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_analytical_intelligence.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_analytical_intelligence.st, "info", _info)
    monkeypatch.setattr(live_analytical_intelligence.st, "line_chart", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_analytical_intelligence.st, "metric", lambda *args, **kwargs: None)

    analytical_report = {"analytical_summary": {"structural_health": 0.93, "confidence": "alta", "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21, "interpretation": "baseline longitudinal consistente"}, "insights": [], "comparisons": []}
    executive_report = {"status": "saudavel", "baseline_mode": "hard", "headline": "baseline longitudinal consistente", "recommendation": "manter baseline hard e monitorar longitudinalmente"}
    historical_report = {"summary": {"trend": "estavel", "verdict_count": 3, "latest_status": "saudavel", "latest_transition": "inicio"}}
    snapshot_report = {"summary": {"status": "saudavel"}}
    timeline = pd.DataFrame(
        [
            {"created_at": "2026-05-21", "headline": "baseline longitudinal consistente", "status_transition": "inicio", "recommendation": "manter baseline hard", "structural_health": 0.93, "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21},
            {"created_at": "2026-05-22", "headline": "baseline longitudinal consistente", "status_transition": "mantido", "recommendation": "manter baseline hard", "structural_health": 0.94, "drift": 0.11, "coverage_10": 0.53, "coverage_11": 0.22},
            {"created_at": "2026-05-23", "headline": "baseline longitudinal consistente", "status_transition": "estavel", "recommendation": "manter baseline hard", "structural_health": 0.95, "drift": 0.10, "coverage_10": 0.54, "coverage_11": 0.23},
        ]
    )
    observability_report = {"summary": {"stability_note": "cockpit institucional validado"}}

    live_analytical_intelligence.render_live_analytical_intelligence(
        analytical_report,
        executive_report,
        historical_report,
        snapshot_report,
        timeline,
        observability_report,
    )

    assert any("Resumo executivo" in message or "continuidade" in message.lower() or "memoria institucional" in message.lower() for message in captured)


def test_live_analytical_intelligence_reports_timeline_depth(monkeypatch) -> None:
    captured: list[str] = []
    _patch_streamlit(monkeypatch)

    def _caption(message, *args, **kwargs):
        captured.append(str(message))

    monkeypatch.setattr(live_analytical_intelligence.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_analytical_intelligence.st, "caption", _caption)
    monkeypatch.setattr(live_analytical_intelligence.st, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_analytical_intelligence.st, "line_chart", lambda *args, **kwargs: None)
    monkeypatch.setattr(live_analytical_intelligence.st, "metric", lambda *args, **kwargs: None)

    analytical_report = {"analytical_summary": {"structural_health": 0.93, "confidence": "alta", "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21, "interpretation": "baseline longitudinal consistente"}, "insights": [], "comparisons": []}
    executive_report = {"status": "saudavel", "baseline_mode": "hard", "headline": "baseline longitudinal consistente", "recommendation": "manter baseline hard e monitorar longitudinalmente"}
    historical_report = {"summary": {"trend": "estavel", "verdict_count": 3, "latest_status": "saudavel", "latest_transition": "inicio"}}
    snapshot_report = {"summary": {"status": "saudavel"}}
    timeline = pd.DataFrame(
        [
            {"created_at": "2026-05-21", "headline": "baseline longitudinal consistente", "status_transition": "inicio", "recommendation": "manter baseline hard", "structural_health": 0.93, "drift": 0.12, "coverage_10": 0.52, "coverage_11": 0.21},
            {"created_at": "2026-05-22", "headline": "baseline longitudinal consistente", "status_transition": "mantido", "recommendation": "manter baseline hard", "structural_health": 0.94, "drift": 0.11, "coverage_10": 0.53, "coverage_11": 0.22},
            {"created_at": "2026-05-23", "headline": "baseline longitudinal consistente", "status_transition": "estavel", "recommendation": "manter baseline hard", "structural_health": 0.95, "drift": 0.10, "coverage_10": 0.54, "coverage_11": 0.23},
        ]
    )
    observability_report = {"summary": {"stability_note": "cockpit institucional validado"}}

    live_analytical_intelligence.render_live_analytical_intelligence(
        analytical_report,
        executive_report,
        historical_report,
        snapshot_report,
        timeline,
        observability_report,
    )

    assert any("Profundidade da timeline" in message or "3 checkpoints" in message for message in captured)


def test_institutional_components_package_exports_are_callable() -> None:
    expected_exports = {
        "render_analytical_cards",
        "render_institutional_design_system",
        "render_executive_dashboard",
        "render_hero_banner",
        "render_executive_panel",
        "render_executive_summary",
        "render_generation_context",
        "render_live_analytical_intelligence",
        "render_live_status_header",
        "render_institutional_timeline",
        "render_secondary_operational_metrics",
        "render_structural_health",
    }

    assert expected_exports.issubset(set(institutional_components.__all__))
    for export_name in expected_exports:
        assert callable(getattr(institutional_components, export_name))
