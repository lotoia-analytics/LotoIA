from __future__ import annotations

import inspect

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

        def expander(self, *_args, **_kwargs):
            return self

    monkeypatch.setattr(admin_app, "st", _StreamlitStub())

    admin_app._render_conference_page({})
    assert calls == [None]
