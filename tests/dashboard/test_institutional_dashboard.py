from __future__ import annotations

import sys
import types
from contextlib import contextmanager
from pathlib import Path
import sqlite3

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


@contextmanager
def _dummy_context():
    yield None


def _patch_streamlit(monkeypatch) -> None:
    monkeypatch.setattr(admin_app.st, "set_page_config", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "caption", lambda *args, **kwargs: None)
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

    def _radio(label, options, **kwargs):
        captured["options"] = list(options)
        captured["label"] = label
        return "jogo_expandido_experimental"

    monkeypatch.setattr(admin_app.st.sidebar, "radio", _radio)

    page = admin_app._sidebar_navigation()

    assert page == "jogo_expandido_experimental"
    assert "jogo_expandido_experimental" in captured["options"]
    assert admin_app.LABELS["jogo_expandido_experimental"] == "Jogo Expandido (Experimental)"


def test_analytics_base_tables_accept_draw_objects(monkeypatch) -> None:
    monkeypatch.setattr(
        admin_app,
        "_load_draws",
        lambda: [
            Draw(contest=1, date=None, numbers=list(range(1, 16))),
            Draw(contest=2, date=None, numbers=list(range(2, 17))),
        ],
    )
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

    monkeypatch.setattr(admin_app, "_load_draws", lambda: [])
    monkeypatch.setattr(admin_app, "_sqlite_health_check", lambda: True)
    monkeypatch.setattr(admin_app, "_sidebar_navigation", lambda: "jogo_expandido_experimental")
    monkeypatch.setattr(admin_app, "_render_kpi_cards", lambda: None)
    monkeypatch.setattr(admin_app, "_render_lead_intelligence", lambda: None)
    monkeypatch.setattr(admin_app, "_record_operational_log", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app, "_record_performance_metric", lambda *args, **kwargs: None)

    def _render_expansion():
        rendered["expansion"] = True

    monkeypatch.setattr(admin_app, "render_expansion_experimental_page", _render_expansion)

    admin_app.main()

    assert rendered["expansion"] is True


def test_observability_and_reports_pages_render_safely(monkeypatch) -> None:
    _patch_streamlit(monkeypatch)
    success_messages = []
    monkeypatch.setattr(admin_app.st, "success", lambda message, *args, **kwargs: success_messages.append(message))
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
    monkeypatch.setattr(admin_app, "_sidebar_navigation", lambda: "observability")

    admin_app.render_observability_page()
    admin_app.render_reports_engine_page()
    admin_app.main()
    assert "INSTITUTIONAL DASHBOARD ACTIVE" in success_messages


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

    assert captured.get("disabled") is True


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


def test_sidebar_dispatch_routes_operational_pages(monkeypatch) -> None:
    _patch_streamlit(monkeypatch)
    calls: list[str] = []

    monkeypatch.setattr(admin_app, "render_generation_page", lambda: calls.append("geracao_jogos"))
    monkeypatch.setattr(admin_app, "render_check_page", lambda: calls.append("conferir_jogos"))
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
    admin_app._render_sidebar_dispatch("estatisticas_historicas", [])
    admin_app._render_sidebar_dispatch("historical_intelligence", [])
    admin_app._render_sidebar_dispatch("analytics_intelligence", [])

    assert calls == [
        "geracao_jogos",
        "conferir_jogos",
        "estatisticas_historicas",
        "historical_intelligence",
        "analytics_intelligence",
    ]
