from __future__ import annotations

import inspect

import pytest

import dashboard.institutional_app as institutional_app
from dashboard.institutional_build import BUILD_MARKER
from lotoia.operations.lot_operational_status import (
    STATUS_APPROVED_WITH_WARNING,
    STATUS_CALIBRATION_SOURCE_ONLY,
    STATUS_NOT_OFFICIALIZED,
    STATUS_OFFICIALIZED,
    STATUS_REJECTED,
    STATUS_SUPERSEDED_BY_CALIBRATION,
    is_official_conference_eligible,
)


def test_build_marker_v45() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v45"


def test_conference_page_initializes_latest_contest_record_before_use() -> None:
    source = inspect.getsource(institutional_app._render_conference_page)
    assert "latest_contest_record: dict[str, Any] | None = None" in source
    assert "latest_contest_record = _resolve_latest_official_conference_contest()" in source
    assert "elif latest_contest_record is None:" in source


def test_conference_page_uses_postgres_resolver() -> None:
    source = inspect.getsource(institutional_app._render_conference_page)
    assert "_resolve_latest_official_conference_contest" in source
    assert "Nenhum concurso oficial disponível para conferência." in source


def test_official_conference_eligibility_filters_non_official_statuses() -> None:
    assert is_official_conference_eligible({"lot_operational_status": STATUS_OFFICIALIZED}) is True
    assert is_official_conference_eligible({"lot_operational_status": STATUS_APPROVED_WITH_WARNING}) is True
    assert is_official_conference_eligible({"lot_operational_status": STATUS_REJECTED}) is False
    assert is_official_conference_eligible({"lot_operational_status": STATUS_NOT_OFFICIALIZED}) is False
    assert is_official_conference_eligible({"lot_operational_status": STATUS_CALIBRATION_SOURCE_ONLY}) is False
    assert is_official_conference_eligible({"lot_operational_status": STATUS_SUPERSEDED_BY_CALIBRATION}) is False


def _conference_streamlit_stub(*, info_messages: list[str] | None = None) -> object:
    messages = info_messages if info_messages is not None else []

    class _Stub:
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
            messages.append(str(message))

        def button(self, *_args, **_kwargs):
            return False

        def expander(self, *_args, **_kwargs):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def json(self, *_args, **_kwargs) -> None:
            return None

    return _Stub()


def test_render_conference_page_with_official_contest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(institutional_app, "_live_institutional_snapshot", lambda snapshot: snapshot)
    monkeypatch.setattr(
        institutional_app,
        "_database_snapshot",
        lambda: {"counts": {"generated_games": 0, "reconciliation_runs": 0}},
    )
    monkeypatch.setattr(institutional_app, "_load_persisted_generation_event_groups", lambda **_kwargs: [])
    monkeypatch.setattr(
        institutional_app,
        "_load_official_conference_generation_groups",
        lambda: [{"generation_event_id": 7, "total_games": 20, "is_official_conference_eligible": True}],
    )
    monkeypatch.setattr(
        institutional_app,
        "_resolve_latest_official_conference_contest",
        lambda: {"concurso": 3700, "dezenas": list(range(1, 16))},
    )
    monkeypatch.setattr(institutional_app, "_load_official_sync_diagnostics", lambda: None)
    monkeypatch.setattr(
        institutional_app,
        "_get_engine_cached",
        lambda: (_ for _ in ()).throw(RuntimeError("skip runtime query")),
    )
    monkeypatch.setattr(institutional_app, "render_conference_governance_section", lambda **_kwargs: None)
    monkeypatch.setattr(institutional_app, "st", _conference_streamlit_stub())

    institutional_app._render_conference_page({})


def test_render_conference_page_without_official_contest(monkeypatch: pytest.MonkeyPatch) -> None:
    info_messages: list[str] = []

    monkeypatch.setattr(institutional_app, "_live_institutional_snapshot", lambda snapshot: snapshot)
    monkeypatch.setattr(
        institutional_app,
        "_database_snapshot",
        lambda: {"counts": {"generated_games": 0, "reconciliation_runs": 0}},
    )
    monkeypatch.setattr(institutional_app, "_load_persisted_generation_event_groups", lambda **_kwargs: [])
    monkeypatch.setattr(institutional_app, "_load_official_conference_generation_groups", lambda: [])
    monkeypatch.setattr(institutional_app, "_resolve_latest_official_conference_contest", lambda: None)
    monkeypatch.setattr(institutional_app, "_load_official_sync_diagnostics", lambda: None)
    monkeypatch.setattr(
        institutional_app,
        "_get_engine_cached",
        lambda: (_ for _ in ()).throw(RuntimeError("skip runtime query")),
    )
    monkeypatch.setattr(institutional_app, "render_conference_governance_section", lambda **_kwargs: None)
    monkeypatch.setattr(institutional_app, "st", _conference_streamlit_stub(info_messages=info_messages))

    institutional_app._render_conference_page({})

    assert any("Nenhum concurso oficial disponível para conferência." in message for message in info_messages)


def test_render_conference_page_resolver_exception_does_not_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    warning_messages: list[str] = []

    class _Stub:
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

        def warning(self, message, *_args, **_kwargs) -> None:
            warning_messages.append(str(message))

        def info(self, *_args, **_kwargs) -> None:
            return None

        def button(self, *_args, **_kwargs):
            return False

        def expander(self, *_args, **_kwargs):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def json(self, *_args, **_kwargs) -> None:
            return None

    monkeypatch.setattr(institutional_app, "_live_institutional_snapshot", lambda snapshot: snapshot)
    monkeypatch.setattr(
        institutional_app,
        "_database_snapshot",
        lambda: {"counts": {"generated_games": 0, "reconciliation_runs": 0}},
    )
    monkeypatch.setattr(institutional_app, "_load_persisted_generation_event_groups", lambda **_kwargs: [])
    monkeypatch.setattr(institutional_app, "_load_official_conference_generation_groups", lambda: [])
    monkeypatch.setattr(
        institutional_app,
        "_resolve_latest_official_conference_contest",
        lambda: (_ for _ in ()).throw(RuntimeError("postgres unavailable")),
    )
    monkeypatch.setattr(institutional_app, "_load_official_sync_diagnostics", lambda: None)
    monkeypatch.setattr(
        institutional_app,
        "_get_engine_cached",
        lambda: (_ for _ in ()).throw(RuntimeError("skip runtime query")),
    )
    monkeypatch.setattr(institutional_app, "render_conference_governance_section", lambda **_kwargs: None)
    monkeypatch.setattr(institutional_app, "st", _Stub())

    institutional_app._render_conference_page({})
    assert any("Falha ao carregar último concurso oficial" in message for message in warning_messages)
