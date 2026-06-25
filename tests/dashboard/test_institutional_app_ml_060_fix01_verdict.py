from __future__ import annotations

import inspect
from typing import Any

import pytest

import dashboard.institutional_app as institutional_app
from lotoia.ml.ml_operational_verdict import VERDICT_BLOQUEADO, VERDICT_REPROVADO


def test_classify_generation_visibility_ml_is_observational_only() -> None:
    """ML é apenas observacional - não bloqueia conferibilidade."""
    payload = institutional_app._classify_generation_visibility(
        generation={
            "batch_id": "batch-ml-observational",
            "status_comandante_saida": "APROVADO",
            "total_jogos_duplicados": 0,
            "ml_verdict": VERDICT_BLOQUEADO,
            "ml_verdict_reason": "Sobreposição máxima 17 em lote com 17D + quase repetidos 3214.",
            "official_release_allowed": True,  # ML não deve afetar isso
        }
    )
    # ML é apenas observacional - não deve bloquear conferibilidade
    assert payload["is_conferible"] is True
    assert payload["ml_verdict"] == VERDICT_BLOQUEADO
    assert payload["ml_verdict_reason"] != ""
    # Não deve mais existir campo is_ml_verdict_blocked
    assert "is_ml_verdict_blocked" not in payload
    # visibility_label não deve mencionar bloqueio por ML
    assert "Bloqueado" not in payload["visibility_label"]


def test_classify_generation_visibility_ml_reprovado_is_observational() -> None:
    """ML REPROVADO é apenas observacional - não bloqueia conferibilidade."""
    payload = institutional_app._classify_generation_visibility(
        generation={
            "batch_id": "batch-ml-reprovado",
            "status_comandante_saida": "APROVADO",
            "total_jogos_duplicados": 0,
            "ml_verdict": VERDICT_REPROVADO,
            "ml_verdict_reason": "similaridade crítica",
            "official_release_allowed": True,
        }
    )
    # ML REPROVADO é apenas observacional
    assert payload["is_conferible"] is True
    assert payload["ml_verdict"] == VERDICT_REPROVADO


def test_load_persisted_groups_exposes_ml_verdict_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    groups = [
        {
            "generation_event_id": 99,
            "official_release_allowed": False,
            "ml_verdict": VERDICT_REPROVADO,
            "ml_verdict_reason": "similaridade crítica",
            "is_conferida": False,
            "games": [],
        }
    ]
    monkeypatch.setattr(
        institutional_app, "_load_persisted_generation_event_groups", lambda **_: groups
    )
    event_id = institutional_app._get_latest_unreconciled_generation_event_id()
    assert event_id is None


def test_persist_clean_law15_includes_ml_verdict_observational(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ML ainda é avaliado, mas apenas como observação."""
    source = inspect.getsource(
        institutional_app._persist_clean_law15_generation_history
    )
    # ML ainda é avaliado (apenas observacional)
    assert "evaluate_batch_ml_verdict_from_games" in source
    assert "ml_verdict" in source
    # official_release_allowed ainda existe, mas não é afetado por ML
    assert "official_release_allowed" in source


def test_conference_filters_official_groups(monkeypatch: pytest.MonkeyPatch) -> None:
    source = inspect.getsource(institutional_app._run_institutional_conference)
    # official_release_allowed ainda é usado para filtrar
    assert "official_release_allowed" in source


def test_analytical_rows_skip_non_official_generations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gerações com official_release_allowed=False são puladas (não por ML)."""
    non_official_generation: dict[str, Any] = {
        "generation_event_id": 1,
        "official_release_allowed": False,
        "games": [
            {"game_index": 1, "numbers": list(range(1, 16)), "generation_context": {}}
        ],
    }
    allowed_generation: dict[str, Any] = {
        "generation_event_id": 2,
        "official_release_allowed": True,
        "seed": 1,
        "strategy": "institutional_clean_hb",
        "created_at": "2026-01-01T00:00:00",
        "batch_id": "b1",
        "games": [
            {"game_index": 1, "numbers": list(range(1, 16)), "generation_context": {}}
        ],
    }
    monkeypatch.setattr(
        institutional_app,
        "_load_generation_history_light",
        lambda limit=25: [non_official_generation, allowed_generation],
    )
    monkeypatch.setattr(
        institutional_app, "_load_sovereign_generation_event_rows", lambda: []
    )
    rows = institutional_app._load_accumulated_analytical_rows_light(limit=10)
    generation_ids = {int(row.get("generation_event_id", 0) or 0) for row in rows}
    # Geração 1 é pulada por official_release_allowed=False (não por ML)
    assert 1 not in generation_ids
    # Geração 2 é incluída
    assert 2 in generation_ids
