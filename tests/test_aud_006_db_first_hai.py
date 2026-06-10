from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from dashboard import institutional_app as admin_app


def test_load_hai_latest_contest_summary_is_db_first(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_app,
        "get_latest_official_contest",
        lambda: {"contest_number": 3701, "dezenas": list(range(1, 16)), "data": "01/06/2026"},
    )

    def _forbidden_csv() -> dict[str, object]:
        raise AssertionError("CSV must not be used as HAI operational source")

    monkeypatch.setattr(admin_app, "_load_csv_latest_contest_summary", _forbidden_csv)
    monkeypatch.setattr(admin_app, "_load_latest_contest_summary", _forbidden_csv)
    monkeypatch.setattr(admin_app, "_load_imported_contest", lambda *_args, **_kwargs: {"contest_number": 1})

    result = admin_app._load_hai_latest_contest_summary()
    assert result is not None
    assert int(result.get("contest_number", 0) or 0) == 3701
    assert result.get("source") == "lotofacil_official_history"


def test_institutional_source_map_hai_does_not_read_csv_operationally(monkeypatch: pytest.MonkeyPatch) -> None:
    def _forbidden_csv() -> dict[str, object]:
        raise AssertionError("load_draws_csv must not be used as HAI operational source")

    monkeypatch.setattr(admin_app, "load_draws_csv", _forbidden_csv)
    monkeypatch.setattr(admin_app, "_load_csv_latest_contest_summary", _forbidden_csv)
    monkeypatch.setattr(
        admin_app,
        "_load_hai_latest_contest_summary",
        lambda: {"contest_number": 3700, "source": "lotofacil_official_history"},
    )
    monkeypatch.setattr(
        admin_app,
        "_load_official_history_diagnostics",
        lambda: {
            "total_lotofacil_official_history": 4,
            "contest_number_min": 3697,
            "contest_number_max": 3700,
            "total_concursos_faltantes": 0,
            "ultimo_concurso_lotofacil_official_history": 3700,
            "status_base_oficial": "OK",
        },
    )
    monkeypatch.setattr(admin_app, "_load_latest_generated_games", lambda: {})
    monkeypatch.setattr(admin_app, "_load_latest_reconciliation_summary", lambda: {})
    monkeypatch.setattr(admin_app, "_load_official_sync_contest_summary", lambda: {"contest_number": 3700})

    source_map = admin_app._institutional_source_map({"counts": {"imported_contests": 4}})
    source_by_layer = {row["camada"]: row for row in source_map}

    assert "export/auditoria/migração" in source_by_layer["CSV histórico versionado"]["uso"]
    assert "último concurso persistido=3700" in source_by_layer["Banco persistido"]["uso"]


def test_post_draw_monitoring_reads_postgresql_not_static_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_app,
        "_load_hai_latest_contest_summary",
        lambda: {"contest_number": 3700, "dezenas": list(range(1, 16)), "source": "lotofacil_official_history"},
    )
    monkeypatch.setattr(
        admin_app,
        "_load_latest_reconciliation_summary",
        lambda: {"created_at": "2026-06-01T12:00:00", "generation_event_id": 9, "best_hits": 12},
    )
    monkeypatch.setattr(
        admin_app,
        "_load_official_history_diagnostics",
        lambda: {"total_lotofacil_official_history": 100},
    )
    monkeypatch.setattr(
        admin_app,
        "_database_snapshot",
        lambda: {"counts": {"generation_events": 7}},
    )

    payload = admin_app._load_post_draw_monitoring_from_db()
    assert payload.get("source") == "postgresql"
    assert int(payload.get("latest_contest", 0) or 0) == 3700
    assert int(payload.get("analyzed_generations", 0) or 0) == 7
    assert payload.get("accepted_signatures")
    assert payload.get("block_distribution")


def test_scientific_memory_block_does_not_seed_from_csv_on_render(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin_app, "_ensure_official_history_seeded", lambda: (_ for _ in ()).throw(AssertionError("CSV bootstrap forbidden on HAI render")))
    monkeypatch.setattr(
        admin_app,
        "_load_official_history_diagnostics",
        lambda: {"status_base_oficial": "OK", "total_lotofacil_official_history": 1, "total_concursos_faltantes": 0},
    )
    monkeypatch.setattr(admin_app, "_ensure_scientific_batch_memory_from_history", lambda: None)
    monkeypatch.setattr(admin_app, "_load_latest_scientific_memory", lambda **_kwargs: [])
    monkeypatch.setattr(admin_app, "_load_official_history_rows", lambda **_kwargs: [])
    monkeypatch.setattr(admin_app.st, "markdown", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(admin_app.st, "columns", lambda _n: [MagicMock() for _ in range(_n)])
    monkeypatch.setattr(admin_app.st, "caption", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(admin_app.st, "info", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(admin_app.st, "session_state", {})

    admin_app._render_scientific_memory_block()


def test_load_accumulated_institutional_rows_avoids_nested_db_session(monkeypatch: pytest.MonkeyPatch) -> None:
    admin_app._load_accumulated_institutional_rows.clear()
    generation = {
        "generation_event_id": 42,
        "created_at": "2026-06-01",
        "strategy": "institutional",
        "total_games": 3,
        "games": [{"game_index": 1, "numbers": list(range(1, 16)), "score": 0.5, "generation_context": {}}],
        "reconciliation": {},
    }
    monkeypatch.setattr(admin_app, "_load_generation_history", lambda **_kwargs: [generation])

    def _forbidden_nested_count(_generation_event_id: int) -> int:
        raise AssertionError("_count_generated_games_for_event must not open nested session in HAI rows")

    monkeypatch.setattr(admin_app, "_count_generated_games_for_event", _forbidden_nested_count)

    rows = admin_app._load_accumulated_institutional_rows()
    assert len(rows) == 1
    assert int(rows[0]["quantidade persistida"]) == 3


def test_build_hai_official_history_export_rows_reads_db(monkeypatch: pytest.MonkeyPatch) -> None:
    export_rows = [{"concurso": 3700, "dezenas_sorteadas": "01 02 03"}]
    monkeypatch.setattr(admin_app, "_load_official_history_rows", lambda: export_rows)

    def _forbidden_csv() -> list[object]:
        raise AssertionError("CSV must not be used for HAI export rows")

    monkeypatch.setattr(admin_app, "load_draws_csv", _forbidden_csv)

    assert admin_app._build_hai_official_history_export_rows() == export_rows


def test_discover_scientific_generation_policy_hai_disables_csv_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class _FakeCore:
        def __init__(self, *args, **kwargs):
            captured["use_csv_fallback"] = kwargs.get("use_csv_fallback")

        def discover_scientific_generation_policy(self, game_size: int, *, candidate_limit: int = 120):
            captured["game_size"] = game_size
            return {"policy": {}, "selection_status": "OK"}

    monkeypatch.setattr("lotoia.analytics.lotofacil_scientific_core.LotofacilScientificCore", _FakeCore)

    from lotoia.analytics.lotofacil_scientific_core import discover_scientific_generation_policy

    discover_scientific_generation_policy(15, use_csv_fallback=False)
    assert captured["use_csv_fallback"] is False


def test_hai_monitoring_does_not_use_session_as_truth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_app,
        "_load_hai_latest_contest_summary",
        lambda: {"contest_number": 3700, "dezenas": list(range(1, 16)), "source": "lotofacil_official_history"},
    )
    monkeypatch.setattr(admin_app, "_load_latest_reconciliation_summary", lambda: {})
    monkeypatch.setattr(admin_app, "_load_official_history_diagnostics", lambda: {"total_lotofacil_official_history": 1})
    monkeypatch.setattr(admin_app, "_database_snapshot", lambda: {"counts": {"generation_events": 1}})

    class _SessionState(dict):
        def get(self, key, default=None):
            if key == "institutional_post_reconciliation_memory":
                return {"contest_number": 1, "best_hit": 15}
            return super().get(key, default)

    monkeypatch.setattr(admin_app.st, "session_state", _SessionState())

    payload = admin_app._load_post_draw_monitoring_from_db()
    assert int(payload.get("latest_contest", 0) or 0) == 3700
