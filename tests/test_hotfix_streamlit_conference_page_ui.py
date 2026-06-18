from __future__ import annotations

import inspect
import re

import pandas as pd
import pytest

from dashboard import institutional_app as admin_app


def test_normalize_conference_display_df_fixed_schema() -> None:
    df = pd.DataFrame([{"jogo": 1, "hits": 12}])
    normalized = admin_app._normalize_conference_display_df(df, admin_app._CONFERENCE_RESULTS_COLUMNS)
    assert list(normalized.columns) == admin_app._CONFERENCE_RESULTS_COLUMNS
    assert normalized.iloc[0]["jogo"] == 1
    assert normalized.iloc[0]["dezenas"] == "-"


def test_build_conference_generation_detail_df_uses_cartao_final() -> None:
    results = [
        {
            "game_index": 1,
            "formato_cartao": 16,
            "nucleo_lei_15": "01 02 03",
            "reservas_auditadas": "+04",
            "cartao_final": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
            "numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
            "dezenas_conferidas_count": 16,
            "origem_dezenas_conferencia": "cartao_final",
            "expected_card_size": 16,
            "actual_card_size": 16,
            "hits": 13,
            "matched_numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
            "prize_status": "premiado",
        }
    ]
    df = admin_app._build_conference_generation_detail_df(results)
    assert list(df.columns) == admin_app._CONFERENCE_GENERATION_DETAIL_COLUMNS
    assert "16" in str(df.iloc[0]["cartao_final"])
    assert df.iloc[0]["origem_dezenas_conferencia"] == "cartao_final"


def test_build_conference_hit_counts_df_empty_schema() -> None:
    df = admin_app._build_conference_hit_counts_df([])
    assert list(df.columns) == admin_app._CONFERENCE_HIT_COUNTS_COLUMNS
    assert df.empty


def test_no_key_argument_on_streamlit_expander() -> None:
    source = inspect.getsource(admin_app._render_conference_page)
    assert "conference_generation_expander_" not in source
    assert not re.search(r"st\.expander\([\s\S]*?expanded=False,\s*key\s*=", source)


def test_institutional_app_expander_calls_do_not_use_key() -> None:
    source = inspect.getsource(admin_app)
    assert not re.search(r"st\.expander\([^)]*key\s*=", source)


def test_render_conference_page_no_typeerror_on_expander(monkeypatch: pytest.MonkeyPatch) -> None:
    db_result = {
        "status": "checked",
        "source": "reconciliation_runs",
        "generation_results": [
            {
                "generation_event_id": 42,
                "total_games": 10,
                "best_hits": 12,
                "prize_count": 1,
                "seed": 99,
                "contest_number": 3700,
                "results": [
                    {
                        "game_index": 1,
                        "numbers": list(range(1, 16)),
                        "hits": 12,
                        "matched_numbers": list(range(1, 13)),
                        "prize_status": "premiado",
                        "cartao_final": list(range(1, 16)),
                        "formato_cartao": 15,
                        "dezenas_conferidas_count": 15,
                        "origem_dezenas_conferencia": "cartao_final",
                        "expected_card_size": 15,
                        "actual_card_size": 15,
                    }
                ],
            }
        ],
        "contest_number": 3700,
        "best_hits": 12,
        "total_hits": 12,
        "prize_count": 1,
        "formato_cartao": 15,
        "dezenas_conferidas_count": 15,
        "origem_dezenas_conferencia": "cartao_final",
        "expected_card_size": 15,
        "actual_card_size": 15,
        "results": [],
    }

    monkeypatch.setattr(admin_app, "_resolve_institutional_check_result", lambda **_: db_result)
    monkeypatch.setattr(admin_app, "_live_institutional_snapshot", lambda snapshot: snapshot)
    monkeypatch.setattr(admin_app, "_database_snapshot", lambda: {"counts": {}})
    monkeypatch.setattr(admin_app, "_load_persisted_generation_event_groups", lambda **_kwargs: [])
    monkeypatch.setattr(admin_app, "_get_latest_unreconciled_generation_event_id", lambda **_kwargs: None)
    monkeypatch.setattr(admin_app, "get_latest_official_contest", lambda: {"contest_number": 3700, "dezenas": list(range(1, 16))})
    monkeypatch.setattr(admin_app, "_load_latest_generated_games", lambda: {})
    monkeypatch.setattr(admin_app, "_load_official_history_diagnostics", lambda: {"contest_number_min": 3700, "contest_number_max": 3700})
    monkeypatch.setattr(admin_app, "get_official_contest", lambda _contest: {"concurso": 3700, "dezenas": list(range(1, 16))})
    monkeypatch.setattr(admin_app, "_load_official_sync_diagnostics", lambda: None)
    monkeypatch.setattr(admin_app, "_load_reconciliation_history", lambda **_kwargs: [])
    monkeypatch.setattr(admin_app, "_get_engine_cached", lambda: (_ for _ in ()).throw(RuntimeError("skip runtime query")))

    class _StreamlitStub:
        session_state: dict[str, object] = {"active_reconciliation_generation_event_id": 42}

        def subheader(self, *_args, **_kwargs) -> None:
            return None

        def write(self, *_args, **_kwargs) -> None:
            return None

        def columns(self, spec):
            return [self for _ in range(len(spec) if isinstance(spec, list) else spec)]

        def metric(self, *_args, **_kwargs) -> None:
            return None

        def caption(self, *_args, **_kwargs) -> None:
            return None

        def number_input(self, *_args, **_kwargs):
            return 3700

        def selectbox(self, *_args, **_kwargs):
            return 42

        def button(self, *_args, **_kwargs):
            return False

        def markdown(self, *_args, **_kwargs) -> None:
            return None

        def container(self):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def warning(self, *_args, **_kwargs) -> None:
            return None

        def info(self, *_args, **_kwargs) -> None:
            return None

        def error(self, *_args, **_kwargs) -> None:
            return None

        def dataframe(self, *_args, **_kwargs) -> None:
            return None

        def expander(self, *_args, **kwargs):
            if "key" in kwargs:
                raise TypeError("LayoutsMixin.expander() got an unexpected keyword argument 'key'")
            return self

    monkeypatch.setattr(admin_app, "st", _StreamlitStub())

    admin_app._render_conference_page({})


def test_render_conference_page_no_latest_contest_fallback_without_name_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info_messages: list[str] = []

    monkeypatch.setattr(admin_app, "_live_institutional_snapshot", lambda snapshot: snapshot)
    monkeypatch.setattr(
        admin_app,
        "_database_snapshot",
        lambda: {"counts": {"imported_contests": 0, "generated_games": 0, "reconciliation_runs": 0}},
    )
    monkeypatch.setattr(admin_app, "_load_persisted_generation_event_groups", lambda **_kwargs: [])
    monkeypatch.setattr(admin_app, "_get_latest_unreconciled_generation_event_id", lambda **_kwargs: None)
    monkeypatch.setattr(admin_app, "_load_latest_generated_games", lambda: {})
    monkeypatch.setattr(admin_app, "_load_official_history_diagnostics", lambda: {})
    monkeypatch.setattr(admin_app, "_load_official_sync_diagnostics", lambda: None)
    monkeypatch.setattr(admin_app, "_get_engine_cached", lambda: (_ for _ in ()).throw(RuntimeError("skip runtime query")))
    monkeypatch.setattr(
        admin_app,
        "build_imported_contests_selection_context",
        lambda **_kwargs: {
            "valid_contest_numbers": [],
            "min_contest": 0,
            "max_contest": 0,
            "default_contest": 0,
            "latest_record": None,
        },
    )

    class _StreamlitStub:
        session_state: dict[str, object] = {}

        def subheader(self, *_args, **_kwargs) -> None:
            return None

        def divider(self) -> None:
            return None

        def markdown(self, *_args, **_kwargs) -> None:
            return None

        def write(self, *_args, **_kwargs) -> None:
            return None

        def columns(self, spec):
            return [self for _ in range(len(spec) if isinstance(spec, list) else spec)]

        def metric(self, *_args, **_kwargs) -> None:
            return None

        def caption(self, *_args, **_kwargs) -> None:
            return None

        def warning(self, *_args, **_kwargs) -> None:
            return None

        def info(self, message, *_args, **_kwargs) -> None:
            info_messages.append(str(message))

        def button(self, *_args, **_kwargs):
            return False

        def container(self):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(admin_app, "st", _StreamlitStub())
    monkeypatch.setattr(admin_app, "render_conference_governance_section", lambda **_kwargs: None)

    admin_app._render_conference_page({})
    assert any("Último concurso ainda não veio do banco" in message for message in info_messages)


def test_render_conference_page_does_not_reference_undefined_latest_contest() -> None:
    source = inspect.getsource(admin_app._render_conference_page)
    assert "latest_contest_record" in source
    assert not re.search(r"elif not latest_contest[^_]", source)


def test_conference_page_interactive_components_have_keys() -> None:
    source = inspect.getsource(admin_app._render_conference_page)
    required_keys = [
        'key="conference_generation_selectbox"',
        'key="conference_selected_contest"',
        'key="conference_run_button"',
        'key="conference_sync_official_button"',
        'key="conference_import_official_button"',
        'key="conference_hit_counts_df"',
        'key="conference_reconciliation_history_df"',
        'key="conference_combined_results_df"',
    ]
    for key in required_keys:
        assert key in source


def test_conference_page_uses_stable_containers() -> None:
    source = inspect.getsource(admin_app._render_conference_page)
    assert "conference_status_section = st.container()" in source
    assert "conference_summary_section = st.container()" in source
    assert "conference_generations_section = st.container()" in source
    assert "conference_reconciliations_section = st.container()" in source
    assert "conference_results_section = st.container()" in source
    assert "st.empty(" not in source


def test_conference_page_db_reload_still_used(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int | None] = []

    def _tracked_resolve(*, generation_event_id=None):
        calls.append(generation_event_id)
        return {"status": "checked", "generation_results": [], "source": "reconciliation_runs"}

    monkeypatch.setattr(admin_app, "_resolve_institutional_check_result", _tracked_resolve)
    monkeypatch.setattr(admin_app, "_live_institutional_snapshot", lambda snapshot: snapshot)
    monkeypatch.setattr(admin_app, "_database_snapshot", lambda: {"counts": {}})
    monkeypatch.setattr(admin_app, "_load_persisted_generation_event_groups", lambda **_kwargs: [])
    monkeypatch.setattr(admin_app, "_get_latest_unreconciled_generation_event_id", lambda **_kwargs: None)
    monkeypatch.setattr(admin_app, "get_latest_official_contest", lambda: None)
    monkeypatch.setattr(admin_app, "_load_latest_generated_games", lambda: {})
    monkeypatch.setattr(admin_app, "_load_official_history_diagnostics", lambda: {})
    monkeypatch.setattr(admin_app, "get_official_contest", lambda _contest: None)
    monkeypatch.setattr(admin_app, "_load_official_sync_diagnostics", lambda: None)
    monkeypatch.setattr(admin_app, "_load_reconciliation_history", lambda **_kwargs: [])

    class _StreamlitStub:
        session_state: dict[str, object] = {}

        def subheader(self, *_args, **_kwargs) -> None:
            return None

        def write(self, *_args, **_kwargs) -> None:
            return None

        def columns(self, spec):
            return [self for _ in range(len(spec) if isinstance(spec, list) else spec)]

        def metric(self, *_args, **_kwargs) -> None:
            return None

        def caption(self, *_args, **_kwargs) -> None:
            return None

        def number_input(self, *_args, **_kwargs):
            return 0

        def button(self, *_args, **_kwargs):
            return False

        def markdown(self, *_args, **_kwargs) -> None:
            return None

        def container(self):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def warning(self, *_args, **_kwargs) -> None:
            return None

        def info(self, *_args, **_kwargs) -> None:
            return None

        def error(self, *_args, **_kwargs) -> None:
            return None

        def dataframe(self, *_args, **_kwargs) -> None:
            return None

        def expander(self, *_args, **kwargs):
            if "key" in kwargs:
                raise TypeError("LayoutsMixin.expander() got an unexpected keyword argument 'key'")
            return self

    monkeypatch.setattr(admin_app, "st", _StreamlitStub())

    admin_app._render_conference_page({})
    assert calls == [None]
