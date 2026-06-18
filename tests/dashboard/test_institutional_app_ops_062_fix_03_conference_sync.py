"""M-OPS-062-FIX-03 — Conferir Resultados sincroniza e usa último concurso oficial válido.

Garante que:
- o último concurso oficial vem de PostgreSQL/imported_contests, válido (>0 e 15 dezenas);
- não há fallback fake/incompleto (`_normalize_contest_record` parcial) na conferência;
- a conferência é bloqueada sem concurso oficial válido, orientando sincronização;
- a sincronização exibe mensagem clara de sucesso/falha;
- a tela nunca mostra concurso 0 nem dezenas fake.
"""

from __future__ import annotations

import inspect

import pytest

from dashboard import institutional_app as admin_app


# --------------------------------------------------------------------------- #
# _resolve_latest_official_conference_contest
# --------------------------------------------------------------------------- #
def _valid_record(contest_number: int) -> dict[str, object]:
    return {
        "contest_number": contest_number,
        "data": "01/01/2026",
        "dezenas": list(range(1, 16)),
        "metadata_json": "{}",
    }


def _fake_incomplete_record(contest_number: int) -> dict[str, object]:
    return {
        "contest_number": contest_number,
        "data": "",
        "dezenas": [1, 2, 3],  # incompleto/fake
        "metadata_json": "{}",
    }


def test_resolve_picks_highest_valid_contest(monkeypatch: pytest.MonkeyPatch) -> None:
    records = [
        _valid_record(3699),
        _valid_record(3700),
        _fake_incomplete_record(3710),  # maior número, porém inválido
    ]
    monkeypatch.setattr(admin_app, "_list_all_imported_contest_records", lambda: records)

    resolved = admin_app._resolve_latest_official_conference_contest()

    assert resolved is not None
    assert resolved["concurso"] == 3700  # não 3710 (fake)
    assert len(resolved["dezenas"]) == 15
    assert resolved["source"]  # origem PostgreSQL / imported_contests


def test_resolve_returns_none_without_valid_contest(monkeypatch: pytest.MonkeyPatch) -> None:
    records = [_fake_incomplete_record(3710), {"contest_number": 0, "dezenas": []}]
    monkeypatch.setattr(admin_app, "_list_all_imported_contest_records", lambda: records)

    assert admin_app._resolve_latest_official_conference_contest() is None


def test_resolve_returns_none_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin_app, "_list_all_imported_contest_records", lambda: [])
    assert admin_app._resolve_latest_official_conference_contest() is None


def test_resolve_has_no_fake_normalize_fallback() -> None:
    source = inspect.getsource(admin_app._resolve_latest_official_conference_contest)
    assert "_normalize_contest_record" not in source
    assert "to_conference_contest_payload" in source


# --------------------------------------------------------------------------- #
# _is_valid_conference_contest
# --------------------------------------------------------------------------- #
def test_is_valid_conference_contest_accepts_valid() -> None:
    assert admin_app._is_valid_conference_contest(
        {"concurso": 3700, "dezenas": list(range(1, 16))}
    )
    assert admin_app._is_valid_conference_contest(
        {"contest_number": 3700, "dezenas": list(range(1, 16))}
    )


@pytest.mark.parametrize(
    "contest",
    [
        None,
        {},
        {"concurso": 0, "dezenas": list(range(1, 16))},
        {"concurso": 3700, "dezenas": [1, 2, 3]},
        {"concurso": 3700, "dezenas": []},
        {"concurso": 3700, "dezenas": list(range(1, 15))},
    ],
)
def test_is_valid_conference_contest_rejects_invalid(contest: dict | None) -> None:
    assert admin_app._is_valid_conference_contest(contest) is False


# --------------------------------------------------------------------------- #
# _run_institutional_conference blocking
# --------------------------------------------------------------------------- #
def test_run_conference_blocks_without_valid_contest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin_app, "_resolve_latest_official_conference_contest", lambda: None)
    monkeypatch.setattr(admin_app, "_get_conference_contest_from_imported", lambda _c: None)
    monkeypatch.setattr(admin_app, "_load_official_history_contest", lambda _c: None)

    def _must_not_run(*_args, **_kwargs):  # pragma: no cover - defensive
        raise AssertionError("conferência não pode prosseguir sem concurso válido")

    monkeypatch.setattr(admin_app, "_load_persisted_generation_event_groups", _must_not_run)

    class _SessionState(dict):
        pass

    class _St:
        session_state = _SessionState()

    monkeypatch.setattr(admin_app, "st", _St())

    admin_app._run_institutional_conference(conference_all_official=True)

    result = _St.session_state["institutional_check_result"]
    assert result["status"] == "waiting_contest"
    assert "Sincronize" in result["warning"]


def test_run_conference_source_has_no_fake_fallback() -> None:
    source = inspect.getsource(admin_app._run_institutional_conference)
    assert "_is_valid_conference_contest" in source
    assert "_normalize_contest_record" not in source
    assert "fallback_imported_contest" not in source


# --------------------------------------------------------------------------- #
# Page rendering / sync feedback
# --------------------------------------------------------------------------- #
class _StreamlitRecorder:
    def __init__(self) -> None:
        self.session_state: dict[str, object] = {}
        self.warnings: list[str] = []
        self.infos: list[str] = []
        self.successes: list[str] = []
        self.errors: list[str] = []
        self.buttons: list[dict[str, object]] = []

    def subheader(self, *_a, **_k) -> None:
        return None

    def markdown(self, *_a, **_k) -> None:
        return None

    def caption(self, *_a, **_k) -> None:
        return None

    def divider(self, *_a, **_k) -> None:
        return None

    def write(self, *_a, **_k) -> None:
        return None

    def json(self, *_a, **_k) -> None:
        return None

    def dataframe(self, *_a, **_k) -> None:
        return None

    def metric(self, *_a, **_k) -> None:
        return None

    def columns(self, spec):
        return [self for _ in range(len(spec) if isinstance(spec, list) else spec)]

    def warning(self, message, *_a, **_k) -> None:
        self.warnings.append(str(message))

    def info(self, message, *_a, **_k) -> None:
        self.infos.append(str(message))

    def success(self, message, *_a, **_k) -> None:
        self.successes.append(str(message))

    def error(self, message, *_a, **_k) -> None:
        self.errors.append(str(message))

    def button(self, label, *_a, **kwargs):
        self.buttons.append({"label": str(label), "disabled": bool(kwargs.get("disabled", False))})
        return False

    def container(self):
        return self

    def expander(self, *_a, **kwargs):
        if "key" in kwargs:
            raise TypeError("expander does not accept key")
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False


def _patch_conference_page_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin_app, "_live_institutional_snapshot", lambda snapshot: snapshot)
    monkeypatch.setattr(
        admin_app,
        "_database_snapshot",
        lambda: {"counts": {"generated_games": 0, "reconciliation_runs": 0}},
    )
    monkeypatch.setattr(admin_app, "_load_persisted_generation_event_groups", lambda **_k: [])
    monkeypatch.setattr(admin_app, "_load_official_conference_generation_groups", lambda: [])
    monkeypatch.setattr(admin_app, "render_conference_governance_section", lambda **_k: None)
    monkeypatch.setattr(admin_app, "_load_official_sync_diagnostics", lambda: None)
    monkeypatch.setattr(
        admin_app,
        "_get_engine_cached",
        lambda: (_ for _ in ()).throw(RuntimeError("skip runtime query")),
    )


def test_render_conference_blocks_without_valid_contest(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_conference_page_dependencies(monkeypatch)
    monkeypatch.setattr(admin_app, "_resolve_latest_official_conference_contest", lambda: None)
    recorder = _StreamlitRecorder()
    monkeypatch.setattr(admin_app, "st", recorder)

    admin_app._render_conference_page({})

    assert any(
        "Nenhum concurso oficial válido encontrado no PostgreSQL" in message
        for message in recorder.warnings
    )
    conferir = next(button for button in recorder.buttons if button["label"] == "Conferir Resultados")
    assert conferir["disabled"] is True


def test_render_conference_no_concurso_zero_caption() -> None:
    source = inspect.getsource(admin_app._render_conference_page)
    # Concurso 0 / dezenas fake não podem aparecer — não usar mais "Concurso automático".
    assert "Concurso automático" not in source
    assert "has_valid_official_contest" in source
    assert "_render_official_sync_feedback" in source


def test_render_sync_feedback_success(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder = _StreamlitRecorder()
    recorder.session_state["institutional_last_official_sync_summary"] = {
        "status": "ok",
        "synced_contests_count": 1,
        "persisted_contests": 1,
        "latest_contest": 3700,
        "latest_contest_record": {"contest_number": 3700, "dezenas": list(range(1, 16))},
    }
    monkeypatch.setattr(admin_app, "st", recorder)

    admin_app._render_official_sync_feedback()

    assert recorder.successes
    assert "3700" in recorder.successes[0]
    assert not recorder.errors


def test_render_sync_feedback_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder = _StreamlitRecorder()
    recorder.session_state["institutional_last_official_sync_summary"] = {
        "status": "error",
        "error_message": "timeout caixa",
    }
    monkeypatch.setattr(admin_app, "st", recorder)

    admin_app._render_official_sync_feedback()

    assert recorder.errors
    assert "timeout caixa" in recorder.errors[0]
    assert not recorder.successes


def test_build_marker_bumped() -> None:
    from dashboard.institutional_build import BUILD_MARKER, DEPRECATED_BUILD_MARKERS

    assert BUILD_MARKER == "institutional-adm-runtime-v48"
    assert BUILD_MARKER not in DEPRECATED_BUILD_MARKERS
    assert "institutional-adm-runtime-v46" in DEPRECATED_BUILD_MARKERS
