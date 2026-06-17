from __future__ import annotations

import inspect

import pytest

import dashboard.institutional_app as institutional_app
import dashboard.institutional_sovereign_generation as sovereign_gen
import dashboard.public_app as public_app
import dashboard.public_surface as public_surface
from dashboard.institutional_build import BUILD_MARKER
from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL, ENV_GENERATION_ENABLED


def test_institutional_app_build_v18() -> None:
    assert institutional_app.APP_BUILD == BUILD_MARKER
    assert BUILD_MARKER == "institutional-adm-runtime-v20"


def test_sovereign_generation_active_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_GENERATION_ENABLED, raising=False)
    assert sovereign_gen.is_adm_sovereign_generation_active() is True
    assert sovereign_gen.sovereign_generation_status_label() == sovereign_gen.SOVEREIGN_GENERATION_STATUS_ACTIVE


def test_sovereign_generation_blocked_when_env_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "0")
    assert institutional_app._is_sovereign_generation_blocked() is True
    assert sovereign_gen.sovereign_generation_status_label() == "BLOQUEADA"


def test_batch_label_none_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "1")
    with pytest.raises(RuntimeError, match="batch_label=None"):
        institutional_app._resolve_adm_sovereign_batch_label(None)


def test_non_sovereign_label_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "1")
    with pytest.raises(RuntimeError, match="Label ADM inválido"):
        institutional_app._resolve_adm_sovereign_batch_label("STRUCT_TEST_15D_001")


def test_legacy_generate_direct_15_still_blocked() -> None:
    with pytest.raises(RuntimeError, match="BLK-LEGACY-GEN-001"):
        institutional_app._generate_direct_15_games(
            total_games=1,
            seed=1,
            history_frequency={},
            latest_numbers=set(),
            batch_number_usage={},
            batch_profile_usage={},
            batch_total_games=1,
            core_numbers=[],
            discouraged_numbers=[],
            max_frequency_ratio=1.0,
            min_frequency_ratio=0.0,
            preferred_profile_ratios={},
            odd_min=5,
            odd_max=10,
            even_min=5,
            even_max=10,
            sequence_max=15,
            coverage_min=0.0,
            entropy_min=0.0,
            repeat_min=0,
            repeat_max=15,
            preferred_parity_pairs=[],
            allowed_parity_pairs=[],
        )


def test_invoke_sovereign_path_uses_generate_best_games(
    monkeypatch: pytest.MonkeyPatch,
    sovereign_generation_enabled,
) -> None:
    captured: dict[str, object] = {}

    def _fake(**kwargs):
        captured.update(kwargs)
        return {"games": [{"numbers": list(range(1, 16))}], "generation_path": "LEI15_CORE_002"}

    monkeypatch.setattr(institutional_app, "_invoke_sovereign_adm_generate_best_games", _fake)
    monkeypatch.setattr(institutional_app.st, "session_state", {})
    monkeypatch.setattr(institutional_app, "get_latest_official_contest", lambda: {"contest_number": 3700, "dezenas": list(range(1, 16))})
    monkeypatch.setattr(institutional_app, "load_all_output_signatures", lambda: [])
    monkeypatch.setattr(
        institutional_app,
        "output_commander_validate_games",
        lambda games, **kwargs: {
            "status_comandante_saida": "APROVADO",
            "quantidade_jogos_rejeitados": 0,
            "quantidade_jogos_aprovados": len(games),
            "quantidade_jogos_unicos": len(games),
        },
    )

    result = institutional_app._run_clean_law15_generation(requested_count=1)

    assert result.get("blocked") is not True
    assert captured["batch_label"] == BATCH_LABEL
    assert result["sovereign_generation_path"] == "generate_best_games"
    assert result["generation_mode"] == "LEI15_CORE_002_SOVEREIGN"


def test_public_app_does_not_generate(monkeypatch: pytest.MonkeyPatch) -> None:
    source = inspect.getsource(public_surface.render_public_app)
    assert "generate_best_games" not in source
    assert "render_institutional_adm" not in source.replace("institutional_app", "")
    monkeypatch.delenv("LOTOIA_DASHBOARD_MODE", raising=False)
    calls: list[str] = []
    monkeypatch.setattr(public_app, "_configure_public_page", lambda: None)
    monkeypatch.setattr(public_app, "_render_public_boot_marker", lambda: None)
    monkeypatch.setattr(public_app, "render_public_app", lambda **k: calls.append("public"))
    monkeypatch.setattr(public_app, "render_institutional_adm", lambda: calls.append("adm"))
    public_app.main()
    assert calls == ["public"]


def test_governance_mission_registry_includes_m_ger_044() -> None:
    from dashboard import institutional_governance

    mission_ids = {row["id"] for row in institutional_governance.MISSION_ROWS}
    assert "M-GER-044" in mission_ids


def test_activation_snapshot_documents_path() -> None:
    payload = sovereign_gen.build_sovereign_generation_activation_snapshot()
    assert payload["batch_label"] == BATCH_LABEL
    assert payload["ml_enabled"] is False
    assert payload["sovereign_path"] == "generate_best_games"
    assert payload["generation_active"] is True


def test_persist_path_includes_sovereign_batch_label(
    monkeypatch: pytest.MonkeyPatch,
    sovereign_generation_enabled,
) -> None:
    monkeypatch.setenv("LOTOIA_ML_CORE_002_OPERATIONAL_ENABLED", "0")
    captured: dict[str, object] = {}

    def _fake_persist(**kwargs):
        captured.update(kwargs)
        return {"generation_event_id": 999, "games_count": 1}

    monkeypatch.setattr(institutional_app, "_persist_generation_snapshot", _fake_persist)
    monkeypatch.setattr(institutional_app, "_load_latest_contest_summary", lambda: {"contest_number": 3700})
    monkeypatch.setattr(institutional_app, "get_latest_official_contest", lambda: {"contest_number": 3700, "dezenas": list(range(1, 16))})
    monkeypatch.setattr(
        institutional_app,
        "validate_lei15_lei15a_runtime_contract",
        lambda **kwargs: {"persistence_allowed": True},
    )
    monkeypatch.setattr(institutional_app, "load_all_output_signatures", lambda: [])
    monkeypatch.setattr(
        institutional_app,
        "output_commander_validate_games",
        lambda games, **kwargs: {
            "status_comandante_saida": "APROVADO",
            "quantidade_jogos_rejeitados": 0,
            "quantidade_jogos_aprovados": len(games),
            "quantidade_jogos_unicos": len(games),
        },
    )
    monkeypatch.setattr(
        institutional_app,
        "_invoke_sovereign_adm_generate_best_games",
        lambda **kwargs: {
            "games": [{"numbers": list(range(1, 16)), "generation_path": "LEI15_CORE_002"}],
            "generation_path": "LEI15_CORE_002",
        },
    )
    monkeypatch.setattr(institutional_app.st, "session_state", {})

    result = institutional_app._run_clean_law15_generation(requested_count=1)
    persisted = institutional_app._persist_clean_law15_generation_history(
        result=result,
        selected_card_format=15,
    )

    assert persisted["generation_event_id"] == 999
    assert captured["analysis_batch_label"] == BATCH_LABEL
    ctx = captured.get("generation_context") or {}
    assert ctx.get("analysis_batch_label") == BATCH_LABEL
    assert ctx.get("ml_enabled") is False
    assert ctx.get("sovereign_generation_path") == "generate_best_games"
