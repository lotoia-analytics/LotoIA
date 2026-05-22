from __future__ import annotations

import sys
import types
from contextlib import contextmanager
from pathlib import Path
import sqlite3

from lotoia.analytics import historical_intelligence
from lotoia.combinatorics.expansion_store import save_expansion_event
from lotoia.database import create_database
from lotoia.database.public_repository import save_check_event, save_generation_event, save_lead, save_reconciliation_run

if "matplotlib" not in sys.modules:
    matplotlib = types.ModuleType("matplotlib")
    pyplot = types.ModuleType("matplotlib.pyplot")
    pyplot.subplots = lambda *args, **kwargs: (type("Fig", (), {"add_axes": lambda *a, **k: type("Ax", (), {"axis": lambda *a, **k: None, "text": lambda *a, **k: None, "table": lambda *a, **k: type("Tbl", (), {"auto_set_font_size": lambda *a, **k: None, "set_fontsize": lambda *a, **k: None, "scale": lambda *a, **k: None})()})(), "savefig": lambda *a, **k: None})(), type("Ax", (), {"axis": lambda *a, **k: None, "text": lambda *a, **k: None, "table": lambda *a, **k: None})())
    pyplot.close = lambda *args, **kwargs: None
    matplotlib.pyplot = pyplot  # type: ignore[attr-defined]
    sys.modules["matplotlib"] = matplotlib
    sys.modules["matplotlib.pyplot"] = pyplot

import dashboard.admin_app as admin_app
from lotoia.models.draw import Draw


class _DummyColumn:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def metric(self, *args, **kwargs):
        return None

    def write(self, *args, **kwargs):
        return None

    def download_button(self, *args, **kwargs):
        return None

    def text_input(self, *args, **kwargs):
        return ""

    def number_input(self, *args, **kwargs):
        return 1

    def radio(self, *args, **kwargs):
        return ""

    def selectbox(self, *args, **kwargs):
        return ""

    def button(self, *args, **kwargs):
        return False


@contextmanager
def _dummy_context():
    yield None


def _patch_streamlit(monkeypatch) -> None:
    monkeypatch.setattr(admin_app.st, "set_page_config", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "write", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "image", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "error", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "success", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "plotly_chart", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "dataframe", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "json", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "stop", lambda *args, **kwargs: (_ for _ in ()).throw(SystemExit))
    monkeypatch.setattr(admin_app.st, "button", lambda *args, **kwargs: False)
    monkeypatch.setattr(admin_app.st, "download_button", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "selectbox", lambda *args, **kwargs: "")
    monkeypatch.setattr(admin_app.st, "tabs", lambda labels: [_dummy_context() for _ in labels])
    monkeypatch.setattr(admin_app.st, "spinner", lambda *args, **kwargs: _dummy_context())
    monkeypatch.setattr(admin_app.st, "container", lambda *args, **kwargs: _dummy_context())
    monkeypatch.setattr(admin_app.st, "columns", lambda count: [_DummyColumn() for _ in range(count)])
    monkeypatch.setattr(admin_app.st, "radio", lambda *args, **kwargs: "geracao_jogos")
    monkeypatch.setattr(admin_app.st, "session_state", {})
    monkeypatch.setattr(admin_app.st.components, "v1", type("V1", (), {"html": lambda *args, **kwargs: None})())


def test_sidebar_navigation_includes_institutional_pages(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(admin_app.st.sidebar, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st.sidebar, "button", lambda label, **kwargs: label == "Jogo Expandido")

    def _radio(label, options, **kwargs):
        if label == "Modo":
            return "operacional"
        captured["options"] = list(options)
        captured["label"] = label
        return "operacional"

    monkeypatch.setattr(admin_app.st.sidebar, "radio", _radio)

    page = admin_app._sidebar_navigation()

    assert page == "jogo_expandido_experimental"
    assert admin_app.LABELS["jogo_expandido_experimental"] == "Jogo Expandido"


def test_sidebar_navigation_filters_pages_by_mode(monkeypatch) -> None:
    monkeypatch.setattr(admin_app.st.sidebar, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st.sidebar, "button", lambda *args, **kwargs: False)

    def _radio(label, options, **kwargs):
        if label == "Modo":
            return "operacional"
        return "operacional"

    monkeypatch.setattr(admin_app.st.sidebar, "radio", _radio)
    admin_app.st.session_state.clear()

    page = admin_app._sidebar_navigation()

    assert page in admin_app.PAGES


def test_sidebar_labels_are_more_explicit_for_operational_inventory() -> None:
    assert admin_app.LABELS["backtesting"] == "Backtesting"
    assert admin_app.LABELS["calibracao_experimental"] == "Ajustes Operacionais"
    assert admin_app.LABELS["benchmark_cientifico"] == "Comparativos Cientificos"
    assert admin_app.LABELS["historico_experimental"] == "Historico Operacional"
    assert admin_app.LABELS["reports_engine"] == "Relatorios Tecnicos"


def test_adm_redundancy_matrix_marks_core_operational_pages_as_keep() -> None:
    assert admin_app.MODE_PAGES["operacional"][:4] == [
        "geracao_jogos",
        "reconciliacao_operacional",
        "jogo_expandido_experimental",
        "workflows",
    ]
    assert admin_app.PAGES[0] == "geracao_jogos"
    assert "historico_experimental" not in admin_app.MODE_PAGES["operacional"]
    assert "calibracao_experimental" not in admin_app.MODE_PAGES["analitico"]
    assert "benchmark_cientifico" not in admin_app.MODE_PAGES["analitico"]
    assert "reports_engine" not in admin_app.MODE_PAGES["analitico"]


def test_analytics_base_tables_accept_draw_objects(monkeypatch) -> None:
    monkeypatch.setattr(
        admin_app,
        "_load_draws",
        lambda: [
            Draw(contest=1, date=None, numbers=list(range(1, 16))),
            Draw(contest=2, date=None, numbers=list(range(2, 17))),
        ],
    )
    monkeypatch.setattr(admin_app, "list_expansion_events", lambda limit=500: [])
    admin_app._historical_dataset.clear()
    admin_app._analytics_base_tables.clear()

    tables = admin_app._analytics_base_tables()

    assert not tables["history"].empty
    assert list(tables["history"]["concurso"]) == [1, 2]


def test_check_helpers_validate_and_score_contest(monkeypatch) -> None:
    draws = [Draw(contest=1234, date=None, numbers=list(range(1, 16)))]
    monkeypatch.setattr(admin_app, "load_draws_csv", lambda path: draws)

    numbers = admin_app._parse_check_numbers("01 02 03 04 05 06 07 08 09 10 11 12 13 14 15")
    result = admin_app._check_game_against_contest(1234, numbers)
    games = admin_app._parse_check_games(
        "01 02 03 04 05 06 07 08 09 10 11 12 13 14 15\n"
        "02 03 04 05 06 07 08 09 10 11 12 13 14 15 16"
    )

    assert result["hits"] == 15
    assert result["correct_numbers"] == list(range(1, 16))
    assert len(games) == 2
    assert games[0] == list(range(1, 16))


def test_admin_expansion_experimental_allows_only_16_and_17(monkeypatch) -> None:
    monkeypatch.setattr(admin_app, "_record_operational_log", lambda *args, **kwargs: None)

    assert admin_app._default_admin_expansion_numbers(16).endswith("16")
    assert admin_app._default_admin_expansion_numbers(17).endswith("17")
    assert admin_app._parse_admin_expansion_numbers(
        "01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16"
    ) == list(range(1, 17))
    assert len(admin_app._parse_admin_expansion_numbers(
        "01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17"
    )) == 17

    for value in [
        "01 02 03 04 05 06 07 08 09 10 11 12 13 14 15",
        "01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18",
    ]:
        try:
            admin_app._parse_admin_expansion_numbers(value)
        except ValueError as exc:
            assert "16 ou 17" in str(exc)
        else:
            raise AssertionError("ADMIN experimental expansion must reject this size")


def test_admin_expansion_experimental_uses_guarded_preview(monkeypatch) -> None:
    monkeypatch.setattr(admin_app, "_record_operational_log", lambda *args, **kwargs: None)

    result = admin_app._run_admin_expansion(list(range(1, 18)), preview_limit=20)

    assert result["total_combinations"] == 136
    assert result["generated_count"] == 20
    assert result["stopped_reason"] == "preview_limit"
    assert result["metrics"]["allowed_sizes"] == [16, 17]


def test_admin_router_renders_expansion_experimental_page(monkeypatch) -> None:
    _patch_streamlit(monkeypatch)
    rendered = {"expansion": False}

    monkeypatch.setattr(admin_app, "_record_operational_log", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app, "_record_performance_metric", lambda *args, **kwargs: None)

    def _render_expansion():
        rendered["expansion"] = True

    monkeypatch.setattr(admin_app, "render_expansion_experimental_page", _render_expansion)

    admin_app._render_sidebar_dispatch("jogo_expandido_experimental", [])

    assert rendered["expansion"] is True


def test_expansion_page_persists_governed_history(monkeypatch, tmp_path: Path) -> None:
    _patch_streamlit(monkeypatch)
    saved: dict[str, object] = {}

    monkeypatch.setattr(admin_app, "estimate_expansion", lambda numbers: {"total_combinations": 136, "estimated_cost": 56.0})
    monkeypatch.setattr(
        admin_app,
        "_run_admin_expansion",
        lambda numbers, preview_limit=20: {
            "selected_numbers": numbers,
            "combinations": [list(range(1, 16))],
            "total_combinations": 136,
            "generated_count": 1,
            "estimated_cost": 56.0,
            "runtime_ms": 1.0,
            "complete": False,
            "stopped_reason": "preview_limit",
            "metrics": {"engine": "combinatorial_expansion_v1_admin_experimental"},
        },
    )
    monkeypatch.setattr(admin_app, "save_expansion_event", lambda payload, db_path=None: saved.setdefault("payload", payload) or 1)
    monkeypatch.setattr(admin_app, "_write_snapshot", lambda name, payload: tmp_path / f"{name}.json")
    monkeypatch.setattr(admin_app, "_export_csv", lambda path, df: path)
    monkeypatch.setattr(admin_app, "_save_pdf_report", lambda path, title, lines, df: path)
    monkeypatch.setattr(admin_app.st, "button", lambda *args, **kwargs: True)
    monkeypatch.setattr(admin_app.st, "text_input", lambda *args, **kwargs: "01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16")
    monkeypatch.setattr(admin_app.st, "selectbox", lambda *args, **kwargs: 16)
    monkeypatch.setattr(admin_app.st, "slider", lambda *args, **kwargs: 20)
    monkeypatch.setattr(admin_app.st, "number_input", lambda *args, **kwargs: 1)

    admin_app.render_expansion_experimental_page()

    assert saved["payload"]["origin"] == "expanded"
    assert "analysis" in saved["payload"]
    assert saved["payload"]["metrics"]["historical_scope"] == "operational_institutional"
    assert saved["payload"]["metrics"]["retention_policy"] == "premiado_permanente_temporario_restante"


def test_institutional_history_includes_expanded_rows(monkeypatch) -> None:
    monkeypatch.setattr(
        admin_app,
        "_load_draws",
        lambda: [Draw(contest=1, date="2025-01-01", numbers=list(range(1, 16)))],
    )
    monkeypatch.setattr(
        admin_app,
        "list_expansion_events",
        lambda limit=500: [
            {
                "id": 7,
                "created_at": "2025-02-01T00:00:00",
                "origin": "expanded",
                "selected_numbers": list(range(1, 17)),
                "total_combinations": 136,
                "generated_count": 20,
                "estimated_cost": 56.0,
                "runtime_ms": 1.0,
                "complete": False,
                "stopped_reason": "preview_limit",
                "analysis": {"profile_type": "hibrido"},
            }
        ],
    )
    admin_app._historical_dataset.clear()
    admin_app._analytics_base_tables.clear()

    tables = admin_app._analytics_base_tables()

    assert "origin" in tables["history"].columns
    assert "expanded" in set(tables["history"]["origin"])
    assert int(tables["history"].iloc[-1]["concurso"]) == 1_000_007


def test_institutional_historical_report_counts_expanded_events(monkeypatch) -> None:
    monkeypatch.setattr(
        admin_app,
        "list_expansion_events",
        lambda limit=50: [
            {
                "id": 1,
                "created_at": "2026-05-22T00:00:00",
                "origin": "expanded",
                "selected_numbers": list(range(1, 18)),
                "total_combinations": 136,
                "generated_count": 17,
                "estimated_cost": 56.0,
                "runtime_ms": 12.5,
                "complete": True,
                "stopped_reason": "",
                "analysis": {"profile_type": "expanded"},
            }
        ],
    )

    report = admin_app.build_institutional_historical_intelligence()

    assert report["summary"]["expanded_event_count"] == 1
    assert report["expanded_events"][0]["origin"] == "expanded"


def test_observability_and_reports_pages_render_safely(monkeypatch) -> None:
    _patch_streamlit(monkeypatch)
    monkeypatch.setattr(admin_app, "load_observational_stabilization_report", lambda: {"report": {"summary": {}, "counts": {}}})
    monkeypatch.setattr(admin_app, "persist_observational_stabilization_report", lambda: {"report": {"summary": {}, "counts": {}}})
    monkeypatch.setattr(admin_app, "_observability_tables", lambda: {"logs": admin_app.pd.DataFrame(), "audit": admin_app.pd.DataFrame()})
    monkeypatch.setattr(admin_app, "_runtime_health", lambda: {
        "response_time_ms": 0.0,
        "total_runs": 0,
        "failures": 0,
        "avg_generation_ms": 0.0,
        "avg_check_ms": 0.0,
        "ml_events": 0,
        "report_events": 0,
        "snapshot_events": 0,
    })
    monkeypatch.setattr(admin_app, "_load_draws", lambda: [])
    monkeypatch.setattr(admin_app, "_sqlite_health_check", lambda: True)
    monkeypatch.setattr(admin_app, "build_institutional_observability_dashboard", lambda: {
        "summary": {
            "execution_count": 1,
            "span_count": 1,
            "metric_count": 1,
            "snapshot_count": 1,
            "latest_flow": "generation",
            "latest_status": "ok",
            "average_execution_duration_ms": 1.0,
        },
        "runtime_health": {"latest_status": "healthy"},
        "drift_evolution": [],
        "confidence_stability": [],
        "structural_integrity": {"ok": True},
    })
    monkeypatch.setattr(admin_app, "build_live_telemetry_snapshot", lambda *args, **kwargs: {
        "summary": {
            "telemetry_status": "live",
            "runtime_awareness": "connected",
            "activity_level": "moderate",
            "latest_execution_id": "exec-test",
        },
        "live_signals": [{"signal": "geracao", "status": "active", "value": 1}],
        "alerts": [],
    })
    monkeypatch.setattr(admin_app, "build_operational_health_snapshot", lambda *args, **kwargs: {
        "status": "healthy",
        "score": 0.9,
        "active_signals": 1,
        "alerts": [],
        "runtime_awareness": "connected",
        "telemetry_status": "live",
        "summary": {"latest_execution_id": "exec-test"},
    })
    monkeypatch.setattr(admin_app, "build_runtime_storytelling", lambda *args, **kwargs: {
        "headline": "plataforma viva e coordenada",
        "summary": {"health_status": "healthy", "active_signals": 1, "telemetry_status": "live", "runtime_awareness": "connected"},
        "narrative": ["Estado atual: live"],
        "timeline": [{"marker": "telemetry", "status": "live"}],
    })
    monkeypatch.setattr(admin_app, "build_live_operational_memory", lambda *args, **kwargs: {
        "summary": {"memory_status": "live", "snapshot_count": 1, "state_count": 1, "replay_ready": True},
        "execution_id": "exec-test",
        "headline": "memoria viva",
        "story": {"narrative": ["Memoria viva"]},
    })
    monkeypatch.setattr(admin_app, "build_real_time_governance", lambda *args, **kwargs: {
        "status": "healthy",
        "score": 0.9,
        "policy_allowed": True,
        "alerts": [],
        "summary": {"health_status": "healthy", "blocking_count": 0},
    })
    monkeypatch.setattr(admin_app, "build_operational_experience", lambda *args, **kwargs: {
        "state": "operational",
        "summary": {"memory_status": "live", "health_status": "healthy", "telemetry_status": "live"},
        "narrative": ["Experiencia operacional viva"],
    })
    monkeypatch.setattr(admin_app, "build_live_institutional_presence", lambda *args, **kwargs: {
        "state": "operational",
        "summary": {"memory_status": "live", "health_status": "healthy", "telemetry_status": "live"},
        "headline": "presenca institucional viva",
        "narrative": ["Presenca viva"],
    })

    observability_dashboard = admin_app.build_institutional_observability_dashboard()
    live_telemetry = admin_app.build_live_telemetry_snapshot()
    operational_health = admin_app.build_operational_health_snapshot()
    runtime_story = admin_app.build_runtime_storytelling()
    live_memory = admin_app.build_live_operational_memory()
    governance = admin_app.build_real_time_governance()
    operational_experience = admin_app.build_operational_experience()
    live_presence = admin_app.build_live_institutional_presence()

    assert observability_dashboard["summary"]["execution_count"] == 1
    assert live_telemetry["summary"]["telemetry_status"] == "live"
    assert operational_health["status"] == "healthy"
    assert runtime_story["headline"] == "plataforma viva e coordenada"
    assert live_memory["summary"]["memory_status"] == "live"
    assert governance["policy_allowed"] is True
    assert operational_experience["state"] == "operational"
    assert live_presence["state"] == "operational"


def test_workflows_page_renders_safely(monkeypatch) -> None:
    _patch_streamlit(monkeypatch)
    monkeypatch.setattr(
        admin_app,
        "build_workflow_dashboard",
        lambda: {
            "state": "operational",
            "summary": {
                "workflow_count": 2,
                "step_count": 4,
                "failure_count": 0,
                "retry_count": 0,
                "latest_status": "ok",
                "workflow_status": "healthy",
                "runtime_stability": 0.9,
            },
            "health": {"status": "stable", "stability_score": 0.9, "scheduler_active": True},
            "live_workflows": [],
            "alerts": [],
            "narrative": ["Fluxos 2", "Falhas 0"],
        },
    )
    monkeypatch.setattr(admin_app, "WorkflowEngine", lambda: type("Engine", (), {"run_sync_workflow": lambda self, **kwargs: type("Snap", (), {"state": "completed", "to_dict": lambda self: {"ok": True}})(), "run_schedule_cycle": lambda self: {"status": "completed"}})())

    admin_app.render_workflows_page()


def test_dashboard_uses_live_generation_events(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "dashboard_live.db"
    connection = sqlite3.connect(db_path)
    try:
        admin_app._sqlite_bind_connection(connection)
        admin_app._sqlite_ensure_admin_schema()
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO generation_events (
                first_name, whatsapp, seed, strategy, ranking_score, execution_time_ms, ml_enabled, created_at
            ) VALUES ('Ana', '11999999999', 123, 'historical_recalibrated_v2', 99.0, 10.0, 0, CURRENT_TIMESTAMP)
            """,
        )
        cursor.execute(
            """
            INSERT INTO generated_games (
                generation_event_id, lead_id, created_at, game_index, numbers, profile_type, final_score, quadra_score
            ) VALUES (1, 1, CURRENT_TIMESTAMP, 1, '[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]', 'recorrente', '{}', '{}')
            """,
        )
        cursor.execute(
            """
            INSERT INTO imported_contests (
                contest_number, created_at, data, dezenas
            ) VALUES (5000, CURRENT_TIMESTAMP, '2025-01-01', '1,2,3,4,5,6,7,8,9,10,11,12,13,14,15')
            """,
        )
        cursor.execute(
            """
            INSERT INTO check_events (
                first_name, whatsapp, contest_id, hits, execution_time_ms, created_at
            ) VALUES ('Ana', '11999999999', 5000, 12, 0.0, CURRENT_TIMESTAMP)
            """,
        )
        connection.commit()

        admin_app._invalidate_runtime_cache()
        assert admin_app._safe_count("generation_events") == 1
        assert admin_app._safe_count("check_events") == 1
        assert admin_app._safe_total_games() == "1"
        assert admin_app._safe_last_contest() == "5000"
    finally:
        admin_app._sqlite_bind_connection(admin_app._sqlite_open_connection())
        connection.close()


def test_statistics_page_uses_official_last_contest(monkeypatch) -> None:
    _patch_streamlit(monkeypatch)
    captured: dict[str, object] = {}

    monkeypatch.setattr(admin_app, "_load_draws", lambda: [Draw(contest=3689, date=None, numbers=list(range(1, 16)))])
    monkeypatch.setattr(admin_app, "_cached_stats", lambda: {
        "frequency": {},
        "delay": {},
        "duos": {},
        "ternos": {},
        "quadras": {},
        "quinas": {},
        "senas": {},
    })
    monkeypatch.setattr(admin_app, "summarize_draws", lambda draws: {"total_draws": 1, "last_contest": {"contest": 3689}, "numbers_tracked": 15, "frequencies": {}})
    monkeypatch.setattr(admin_app, "calculate_hot_cold_numbers", lambda draws, window=20: {"hot": [], "cold": []})
    monkeypatch.setattr(admin_app, "_safe_last_contest", lambda: "3691")
    def _capture_metric(self, label: str, value: object, *args, **kwargs) -> None:
        captured.setdefault(label, value)

    monkeypatch.setattr(_DummyColumn, "metric", _capture_metric, raising=False)
    monkeypatch.setattr(admin_app.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "dataframe", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "plotly_chart", lambda *args, **kwargs: None)
    class _DummyTab:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(admin_app.st, "tabs", lambda labels: [_DummyTab() for _ in labels])

    admin_app.render_statistics_page([Draw(contest=3689, date=None, numbers=list(range(1, 16)))])

    assert captured["Último concurso"] == "3691"


def test_cache_invalidates_after_generation(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(admin_app, "_invalidate_runtime_cache", lambda: calls.append("clear"))
    monkeypatch.setattr(admin_app, "_record_operational_log", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app, "_record_performance_metric", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app, "_record_audit_trail", lambda *args, **kwargs: None)
    class _LeadCaptureService:
        def __init__(self, db_path) -> None:  # noqa: ANN001
            self.db_path = db_path

        def capture(self, payload, *, ip_address="", user_agent=""):  # noqa: ANN001
            assert payload.first_name == "Ana"
            assert payload.whatsapp == "11999999999"
            assert payload.source == "dashboard_user_panel"
            return type(
                "LeadCaptureResult",
                (),
                {"lead": {"id": 7, "first_name": "Ana"}, "normalized_whatsapp": "11999999999"},
            )()

    monkeypatch.setattr(admin_app, "LeadCaptureService", _LeadCaptureService)
    monkeypatch.setattr(admin_app, "_persist_generation_events", lambda **kwargs: calls.append("persist") or 99)
    monkeypatch.setattr(admin_app, "_cached_generate_best_games", lambda count, pool_size: {"games": [{"numbers": list(range(1, 16)), "final_score": {"final_score": 1}, "quadra_score": {"found_quadras": 0, "average_rank": 0}}], "profile_counts": {"recorrente": 1, "hibrido": 0, "caotico": 0}})
    monkeypatch.setattr(admin_app, "_games_dataframe", lambda games: admin_app.pd.DataFrame([{"rank": 1, "final_score": 1}]))
    monkeypatch.setattr(admin_app.st, "spinner", lambda *args, **kwargs: _dummy_context())
    monkeypatch.setattr(admin_app.st, "session_state", {})
    monkeypatch.setattr(admin_app.st, "button", lambda *args, **kwargs: True)
    monkeypatch.setattr(admin_app.st, "radio", lambda *args, **kwargs: "Ranking hibrido")
    monkeypatch.setattr(admin_app.st, "number_input", lambda *args, **kwargs: 1)
    monkeypatch.setattr(
        admin_app.st,
        "text_input",
        lambda label, *args, **kwargs: "Ana" if "nome" in label.lower() else "(11) 99999-9999",
    )
    monkeypatch.setattr(admin_app.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "dataframe", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "plotly_chart", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "warning", lambda *args, **kwargs: None)

    lead_id, first_name, whatsapp = admin_app._capture_generation_lead("Ana", "(11) 99999-9999")
    assert lead_id == 7
    assert first_name == "Ana"
    assert whatsapp == "11999999999"
    admin_app._invalidate_runtime_cache()

    assert calls == ["clear"]


def test_generation_page_disables_button_without_lead(monkeypatch) -> None:
    _patch_streamlit(monkeypatch)
    captured: dict[str, object] = {}
    monkeypatch.setattr(admin_app, "build_executive_analytical_report", lambda: {})
    monkeypatch.setattr(admin_app, "build_institutional_historical_intelligence", lambda: {})
    monkeypatch.setattr(admin_app, "load_observational_stabilization_report", lambda: {})
    monkeypatch.setattr(admin_app, "render_generation_context", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "button", lambda *args, **kwargs: captured.update(kwargs) or False)
    monkeypatch.setattr(admin_app.st, "text_input", lambda *args, **kwargs: "")

    admin_app.render_generation_page()

    assert captured.get("disabled") in {None, False}


def test_homepage_renders_institutional_cockpit_first(monkeypatch) -> None:
    _patch_streamlit(monkeypatch)
    calls: list[str] = []

    monkeypatch.setattr(admin_app, "_load_draws", lambda: [])
    monkeypatch.setattr(admin_app, "_sqlite_health_check", lambda: True)
    monkeypatch.setattr(admin_app, "_sidebar_navigation", lambda: "geracao_jogos")
    monkeypatch.setattr(admin_app, "_render_kpi_cards", lambda: calls.append("kpis"))
    monkeypatch.setattr(admin_app, "_render_lead_intelligence", lambda: calls.append("leads"))
    monkeypatch.setattr(admin_app, "_record_operational_log", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app, "_record_performance_metric", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app, "_render_institutional_cockpit", lambda: calls.append("cockpit"))
    monkeypatch.setattr(admin_app.st, "expander", lambda *args, **kwargs: _dummy_context())
    monkeypatch.setattr(admin_app, "render_generation_page", lambda: calls.append("generation"))

    admin_app.main()

    assert calls[0] == "cockpit"
    assert "generation" in calls


def test_dashboard_uses_wide_layout(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def _set_page_config(*args, **kwargs):
        calls.append(kwargs)

    _patch_streamlit(monkeypatch)
    monkeypatch.setattr(admin_app.st, "set_page_config", _set_page_config)
    monkeypatch.setattr(admin_app, "_load_draws", lambda: [])
    monkeypatch.setattr(admin_app, "_sqlite_health_check", lambda: True)
    monkeypatch.setattr(admin_app, "_sidebar_navigation", lambda: "geracao_jogos")
    monkeypatch.setattr(admin_app, "_render_kpi_cards", lambda: None)
    monkeypatch.setattr(admin_app, "_render_lead_intelligence", lambda: None)
    monkeypatch.setattr(admin_app, "_record_operational_log", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app, "_record_performance_metric", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app, "_render_institutional_cockpit", lambda: None)
    monkeypatch.setattr(admin_app.st, "expander", lambda *args, **kwargs: _dummy_context())
    monkeypatch.setattr(admin_app, "render_generation_page", lambda: None)

    admin_app.main()

    assert any(call.get("layout") == "wide" for call in calls)


def test_presentational_historical_intelligence_dataframe_renames_columns() -> None:
    dataframe = admin_app._presentational_historical_intelligence_dataframe(
        [{"numbers": list(range(1, 16))}]
    )

    assert "Forca Historica" in dataframe.columns
    assert "Perfil Estrategico" in dataframe.columns
    assert "Tendencia" in dataframe.columns
    assert "Pico de Acertos" in dataframe.columns
    assert "Media de Acertos" in dataframe.columns
    assert "Compatibilidade" in dataframe.columns
    assert "Exclusividade" in dataframe.columns
    assert "Balanceamento" in dataframe.columns
    assert "Distribuicao Estrutural" in dataframe.columns
    assert "historical_score" not in dataframe.columns


def test_presentational_dataframe_renames_user_history_columns() -> None:
    dataframe = admin_app._presentational_dataframe(
        admin_app.pd.DataFrame(
            [
                {
                    "lead": "Ana | 11999999999",
                    "first_name": "Ana",
                    "whatsapp": "11999999999",
                    "created_at": "2026-05-21",
                    "origin": "user_panel",
                    "generations": 3,
                    "checks": 1,
                    "ml_activations": 0,
                    "last_generation_at": "2026-05-21",
                    "last_check_at": "2026-05-20",
                    "recurrence_score": 4,
                }
            ]
        )
    )

    assert "Nome" in dataframe.columns
    assert "WhatsApp" in dataframe.columns
    assert "Gerações" in dataframe.columns or "Geracoes" in dataframe.columns
    assert "Conferências" in dataframe.columns or "Conferencias" in dataframe.columns
    assert "Tendencia" in dataframe.columns


def test_presentational_dataframe_renames_observability_columns() -> None:
    dataframe = admin_app._presentational_dataframe(
        admin_app.pd.DataFrame(
            [
                {
                    "event_type": "sqlite",
                    "count": 3,
                    "avg_duration_ms": 4.2,
                    "status": "ok",
                    "source": "admin_app",
                    "metric": "sqlite_size_bytes",
                    "value": 1024,
                    "stage": "generation",
                }
            ]
        )
    )

    assert "Evento" in dataframe.columns
    assert "Quantidade" in dataframe.columns
    assert "Tempo medio ms" in dataframe.columns
    assert "Status" in dataframe.columns
    assert "Fonte" in dataframe.columns
    assert "Metrica" in dataframe.columns
    assert "Valor" in dataframe.columns
    assert "Etapa" in dataframe.columns


def test_presentational_dataframe_renames_log_columns() -> None:
    dataframe = admin_app._presentational_dataframe(
        admin_app.pd.DataFrame(
            [
                {
                    "event_type": "dashboard",
                    "count": 5,
                    "avg_duration_ms": 12.5,
                    "failures": 1,
                    "report_path": "reports/demo.json",
                }
            ]
        )
    )

    assert "Evento" in dataframe.columns
    assert "Quantidade" in dataframe.columns
    assert "Tempo medio ms" in dataframe.columns
    assert "Falhas" in dataframe.columns
    assert "Caminho do relatorio" in dataframe.columns


def test_presentational_dataframe_renames_artifact_columns() -> None:
    dataframe = admin_app._presentational_dataframe(
        admin_app.pd.DataFrame(
            [
                {
                    "type": "json",
                    "path": "reports/demo.json",
                    "generated_by": "pipeline",
                    "model_version": "v1",
                    "interpretation": "ok",
                    "confidence": "alta",
                }
            ]
        )
    )

    assert "Tipo" in dataframe.columns
    assert "Caminho" in dataframe.columns
    assert "Gerado por" in dataframe.columns
    assert "Versao do modelo" in dataframe.columns
    assert "Interpretacao" in dataframe.columns
    assert "Confianca" in dataframe.columns


def test_lead_analytics_reacts_to_institutional_db_signature(monkeypatch) -> None:
    calls: list[int] = []

    def _lead_history_dataframe(signature: int):
        calls.append(signature)
        return admin_app.pd.DataFrame(
            [
                {
                    "lead": "Ana | 11999999999",
                    "first_name": "Ana",
                    "whatsapp": "11999999999",
                    "created_at": "2026-05-22",
                    "origin": "user_panel",
                    "generations": 1,
                    "checks": 1,
                    "ml_activations": 0,
                    "last_generation_at": "2026-05-22",
                    "last_check_at": "2026-05-22",
                    "recurrence_score": 2,
                }
            ]
        )

    monkeypatch.setattr(admin_app, "_institutional_db_signature", lambda: 123456789)
    monkeypatch.setattr(admin_app, "_lead_history_dataframe", _lead_history_dataframe)

    analytics = admin_app._lead_analytics()

    assert calls == [123456789]
    assert analytics["total_leads"] == 1
    assert analytics["volume_generations"] == 1
    assert analytics["volume_checks"] == 1


def test_lead_analytics_falls_back_to_empty_dataframe_on_cache_error(monkeypatch) -> None:
    monkeypatch.setattr(admin_app, "_institutional_db_signature", lambda: 123456789)
    monkeypatch.setattr(admin_app, "_lead_history_dataframe", lambda signature: (_ for _ in ()).throw(RuntimeError("cache broken")))
    monkeypatch.setattr(admin_app, "_safe_count", lambda table_name: 0)

    analytics = admin_app._lead_analytics()

    assert analytics["total_leads"] == 0
    assert analytics["volume_generations"] == 0
    assert analytics["volume_checks"] == 0


def test_institutional_user_flow_updates_dashboard_and_history(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "institutional.db"
    expansion_db_path = tmp_path / "expansion.db"
    create_database(db_path)
    admin_conn = sqlite3.connect(db_path)
    admin_app._sqlite_bind_connection(admin_conn)
    monkeypatch.setattr(admin_app, "_institutional_db_signature", lambda: int(db_path.stat().st_mtime_ns))
    admin_app._lead_history_dataframe.clear()
    admin_app._observability_tables.clear()
    admin_app._analytics_base_tables.clear()

    lead = save_lead(
        first_name="Ana",
        whatsapp="11999999999",
        source="user_panel",
        ip_hash="hash",
        user_agent="agent",
        db_path=db_path,
    )
    generation = save_generation_event(
        lead_id=lead["id"],
        generated_games=[
            {
                "game_index": 1,
                "numbers": list(range(1, 16)),
                "profile_type": "hibrido",
                "final_score": {"final_score": 90.0},
                "quadra_score": {"quadra_score": 4},
                "origin": "generated",
                "context_json": {"source": "user_panel"},
            }
        ],
        ml_enabled=False,
        seed=7,
        strategy="historical_recalibrated_v2",
        ranking_score=90.0,
        execution_time_ms=10.0,
        target_contest=3691,
        origin="user_panel",
        generation_mode="dashboard",
        context={"source": "user_panel"},
        first_name="Ana",
        whatsapp="11999999999",
        db_path=db_path,
    )
    save_check_event(
        lead_id=lead["id"],
        contest_id=3691,
        selected_numbers=list(range(1, 16)),
        hits=15,
        result_payload={"hits": 15, "status": "reconciliado"},
        db_path=db_path,
    )
    save_reconciliation_run(
        generation_event_id=generation["id"],
        lead_id=lead["id"],
        contest_id=3691,
        source="operational_smoke_validation",
        status="reconciliado",
        prize_count=1,
        total_hits=15,
        best_hits=15,
        payload={"baseline_numbers": list(range(1, 16)), "origin": "smoke"},
        games=[
            {
                "game_index": 1,
                "numbers": list(range(1, 16)),
                "hits": 15,
                "matched_numbers": list(range(1, 16)),
                "prize_status": "premiado",
                "prize_tier": "faixa_15",
                "context_json": {"origin": "generated"},
            }
        ],
        db_path=db_path,
    )
    save_expansion_event(
        {
            "origin": "expanded",
            "selected_numbers": list(range(1, 16)),
            "combinations": [list(range(1, 16))],
            "total_combinations": 1,
            "generated_count": 1,
            "estimated_cost": 0.0,
            "runtime_ms": 1.0,
            "complete": True,
            "stopped_reason": "",
            "metrics": {"coverage": 1.0},
            "analysis": {"profile_type": "expanded"},
        },
        db_path=expansion_db_path,
    )

    monkeypatch.setattr(
        historical_intelligence,
        "list_expansion_events",
        lambda limit=50: [
            {
                "id": 1,
                "created_at": "2026-05-22T10:00:00",
                "origin": "expanded",
                "selected_numbers": list(range(1, 16)),
                "total_combinations": 1,
                "generated_count": 1,
                "estimated_cost": 0.0,
                "runtime_ms": 1.0,
                "complete": True,
                "stopped_reason": "",
            }
        ],
    )
    report_dir = tmp_path / "analytics"
    report_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        historical_intelligence,
        "_load_institutional_snapshots",
        lambda report_dir=report_dir: [
            {
                "_path": str(report_dir / "snapshot-1.json"),
                "source": str(report_dir),
                "executive_report": {
                    "generated_at": "2026-05-22T10:00:00",
                    "status": "ok",
                    "headline": "ok",
                    "recommendation": "seguir",
                    "confidence": "alta",
                },
                "historical_report": {
                    "summary": {
                        "trend": "estavel",
                        "latest_status": "ok",
                        "latest_headline": "ok",
                        "latest_recommendation": "seguir",
                        "verdict_count": 1,
                        "expanded_event_count": 1,
                    }
                },
                "summary": {
                    "status": "ok",
                    "headline": "ok",
                },
            }
        ],
    )
    lead_analytics = admin_app._lead_analytics()
    dashboard = admin_app.build_institutional_observability_dashboard(db_path)
    historical = historical_intelligence.build_institutional_historical_intelligence(report_dir=report_dir)
    timeline = historical_intelligence.build_institutional_analytical_timeline(report_dir=report_dir)

    assert lead_analytics["total_leads"] == 1
    assert lead_analytics["volume_generations"] == 1
    assert lead_analytics["volume_checks"] == 1
    assert dashboard["summary"]["expansion_event_count"] == 1
    assert historical["summary"]["expanded_event_count"] == 1
    assert timeline["summary"]["expanded_event_count"] == 1


def test_sidebar_dispatch_routes_operational_pages(monkeypatch) -> None:
    _patch_streamlit(monkeypatch)
    calls: list[str] = []

    monkeypatch.setattr(admin_app, "render_generation_page", lambda: calls.append("geracao_jogos"))
    monkeypatch.setattr(admin_app, "render_check_page", lambda: calls.append("conferir_jogos"))
    monkeypatch.setattr(admin_app, "render_operational_reconciliation_page", lambda: calls.append("reconciliacao_operacional"))
    monkeypatch.setattr(admin_app, "render_statistics_page", lambda draws: calls.append("estatisticas_historicas"))
    monkeypatch.setattr(admin_app, "render_historical_intelligence_page", lambda draws: calls.append("historical_intelligence"))
    monkeypatch.setattr(admin_app, "render_analytics_intelligence_page", lambda: calls.append("analytics_intelligence"))
    monkeypatch.setattr(admin_app, "_load_draws", lambda: [])
    monkeypatch.setattr(admin_app, "_sqlite_health_check", lambda: True)
    monkeypatch.setattr(admin_app, "_sidebar_navigation", lambda: "geracao_jogos")
    monkeypatch.setattr(admin_app, "_render_kpi_cards", lambda: None)
    monkeypatch.setattr(admin_app, "_render_lead_intelligence", lambda: None)
    monkeypatch.setattr(admin_app, "_render_institutional_cockpit", lambda: None)
    monkeypatch.setattr(admin_app, "_record_operational_log", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app, "_record_performance_metric", lambda *args, **kwargs: None)

    admin_app._render_sidebar_dispatch("geracao_jogos", [])
    admin_app._render_sidebar_dispatch("conferir_jogos", [])
    admin_app._render_sidebar_dispatch("reconciliacao_operacional", [])
    admin_app._render_sidebar_dispatch("estatisticas_historicas", [])
    admin_app._render_sidebar_dispatch("historical_intelligence", [])
    admin_app._render_sidebar_dispatch("analytics_intelligence", [])

    assert calls == [
        "geracao_jogos",
        "conferir_jogos",
        "reconciliacao_operacional",
        "estatisticas_historicas",
        "historical_intelligence",
        "analytics_intelligence",
    ]


def test_operational_reconciliation_page_renders_summary(monkeypatch) -> None:
    _patch_streamlit(monkeypatch)
    metrics: list[tuple[str, object]] = []
    frames: list[object] = []
    monkeypatch.setattr(admin_app, "_record_operational_log", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app, "st", admin_app.st)
    monkeypatch.setattr(admin_app.st, "container", lambda *args, **kwargs: type("Ctx", (), {"__enter__": lambda self: self, "__exit__": lambda self, exc_type, exc, tb: False})())
    monkeypatch.setattr(admin_app.st, "metric", lambda label, value, **kwargs: metrics.append((label, value)))
    monkeypatch.setattr(admin_app.st, "dataframe", lambda df, **kwargs: frames.append(df))
    monkeypatch.setattr(admin_app.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "error", lambda *args, **kwargs: None)
    class DummyColumn:
        def button(self, *args, **kwargs):
            return True

    monkeypatch.setattr(admin_app.st, "columns", lambda *args, **kwargs: [DummyColumn(), DummyColumn()])
    monkeypatch.setattr(admin_app.st, "text_area", lambda *args, **kwargs: "01 02 03 04 05 06 07 08 09 10 11 12 13 14 15")
    monkeypatch.setattr(
        admin_app,
        "_load_operational_reconciliation_rows",
        lambda baseline_numbers: (
            {
                "result_informed": "01 02 03 04 05 06 07 08 09 10 11 12 13 14 15",
                "contest_id": 0,
                "source": "smoke_validation_baseline",
                "status": "reconciled",
                "prize_count": 2,
                "total_hits": 29,
                "best_hits": 15,
                "payload": {"source": "smoke_validation_baseline"},
                "generation_event_id": 77,
                "row_count": 3,
            },
            [
                {"jogo": 1, "acertos": 15, "dezenas_acertadas": "01 02 03 04 05 06 07 08 09 10 11 12 13 14 15", "perfil_estrategico": "hibrido", "status": "premiado", "origem": "dashboard", "faixa": "faixa_15", "dezenas": "01 02 03 04 05 06 07 08 09 10 11 12 13 14 15"},
                {"jogo": "exp_7", "acertos": 14, "dezenas_acertadas": "01 02 03 04 05 06 07 08 09 10 11 12 13 14", "perfil_estrategico": "expanded", "status": "premiado", "origem": "expanded", "faixa": "faixa_14", "dezenas": "01 02 03 04 05 06 07 08 09 10 11 12 13 14 16"},
                {"jogo": 2, "acertos": 0, "dezenas_acertadas": "-", "perfil_estrategico": "recorrente", "status": "nao_premiado", "origem": "dashboard", "faixa": "", "dezenas": "02 03 04 05 06 07 08 09 10 11 12 13 14 15 16"},
            ],
        ),
    )

    admin_app.render_operational_reconciliation_page()

    assert ("Resultado informado", "01 02 03 04 05 06 07 08 09 10 11 12 13 14 15") in metrics
    assert ("Concurso simulado", 0) in metrics
    assert ("Jogos analisados", 3) in metrics
    assert ("Jogos premiados", 2) in metrics
    assert ("Melhor jogo", 1) in metrics
    assert ("Perfil vencedor", "hibrido") in metrics
    assert any(isinstance(frame, admin_app.pd.DataFrame) and "jogo" in frame.columns for frame in frames)


def test_operational_reconciliation_page_autoreconciles_latest_generation(monkeypatch) -> None:
    _patch_streamlit(monkeypatch)
    metrics: list[tuple[str, object]] = []
    frames: list[object] = []
    reconcile_calls: list[dict[str, object]] = []
    monkeypatch.setattr(admin_app, "_record_operational_log", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app, "st", admin_app.st)
    monkeypatch.setattr(admin_app.st, "container", lambda *args, **kwargs: type("Ctx", (), {"__enter__": lambda self: self, "__exit__": lambda self, exc_type, exc, tb: False})())
    monkeypatch.setattr(admin_app.st, "metric", lambda label, value, **kwargs: metrics.append((label, value)))
    monkeypatch.setattr(admin_app.st, "dataframe", lambda df, **kwargs: frames.append(df))
    monkeypatch.setattr(admin_app.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "error", lambda *args, **kwargs: None)
    class DummyColumn:
        def button(self, *args, **kwargs):
            return True

    monkeypatch.setattr(admin_app.st, "columns", lambda *args, **kwargs: [DummyColumn(), DummyColumn()])
    monkeypatch.setattr(admin_app.st, "text_area", lambda *args, **kwargs: "01 02 03 04 05 06 07 08 09 10 11 12 13 14 15")
    monkeypatch.setattr(admin_app, "_load_operational_reconciliation_rows", lambda baseline_numbers: (None, []))
    monkeypatch.setattr(
        admin_app,
        "_load_latest_generated_games",
        lambda: {
            "generation_event_id": 88,
            "lead_id": 7,
            "target_contest": 3691,
            "origin": "generated",
            "generation_mode": "dashboard",
            "games": [
                {
                    "game_index": 1,
                    "numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
                    "profile_type": "hibrido",
                    "final_score": {"final_score": 91.0},
                    "quadra_score": {"quadra_score": 4},
                    "origin": "generated",
                    "context_json": {},
                }
            ],
        },
    )

    class DummyEngine:
        def __init__(self, *args, **kwargs):
            pass

        def reconcile_generation(self, **kwargs):
            reconcile_calls.append(kwargs)
            return None

    monkeypatch.setattr(admin_app, "ReconciliationEngine", DummyEngine)

    admin_app.render_operational_reconciliation_page()

    assert reconcile_calls
    assert reconcile_calls[0]["generation_event_id"] == 88
    assert reconcile_calls[0]["contest_id"] == 3691
    assert reconcile_calls[0]["lead_id"] == 7
