from __future__ import annotations

import inspect

import pytest

from dashboard import institutional_app as admin_app
from lotoia.governance.structural_rfe import RFEPreviousContestReference, RFEValidationResult


def _approve_rfe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_app,
        "validate_rfe_final_card",
        lambda numbers, previous: RFEValidationResult(
            approved=True,
            blocked_reasons=[],
            repeated_from_previous=0,
            empty_rows=[],
            empty_columns=[],
        ),
    )


def _direct_generation_candidates(quantity: int) -> list[dict[str, list[int]]]:
    return [
        {"numbers": list(range(1, 26))},
        {"numbers": list(range(2, 26)) + [1]},
        {"numbers": list(range(3, 26)) + [1, 2]},
    ] * max(4, quantity)


def test_generation_quantity_allowed_set() -> None:
    assert admin_app.ALLOWED_GENERATION_QUANTITIES == (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 50)


def test_generation_quantity_invalid_rejected() -> None:
    with pytest.raises(ValueError, match="Quantidade de jogos inválida"):
        admin_app._validate_generation_quantity(11)
    with pytest.raises(ValueError, match="Quantidade de jogos inválida"):
        admin_app._validate_generation_quantity(100)


@pytest.mark.parametrize("quantity", [1, 9])
def test_generation_quantity_small_batches(monkeypatch: pytest.MonkeyPatch, quantity: int) -> None:
    _approve_rfe(monkeypatch)
    monkeypatch.setattr(admin_app, "generate_ranked_games", lambda **kwargs: _direct_generation_candidates(quantity))

    games = admin_app._generate_direct_15_games(
        total_games=quantity,
        seed=123,
        history_frequency={},
        latest_numbers=set(),
        batch_number_usage={},
        batch_profile_usage={},
        batch_total_games=quantity,
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
        previous_contest_numbers=list(range(1, 16)),
    )

    assert len(games) == quantity
    assert admin_app._validate_generation_quantity(quantity) == quantity


def test_generation_quantity_1(monkeypatch: pytest.MonkeyPatch) -> None:
    test_generation_quantity_small_batches(monkeypatch, 1)


def test_generation_quantity_9(monkeypatch: pytest.MonkeyPatch) -> None:
    test_generation_quantity_small_batches(monkeypatch, 9)


@pytest.mark.parametrize("quantity", [10, 20, 30, 50])
def test_existing_quantities_10_20_30_50_still_pass(quantity: int) -> None:
    assert admin_app._validate_generation_quantity(quantity) == quantity
    assert quantity in admin_app.ALLOWED_GENERATION_QUANTITIES


def test_conference_respects_generated_quantity() -> None:
    games = [
        {
            "game_index": index,
            "numbers": list(range(1, 16)),
            "cartao_final": list(range(1, 16)),
            "final_card_numbers": list(range(1, 16)),
            "formato_cartao": 15,
        }
        for index in range(1, 6)
    ]
    rows = admin_app._compare_games_against_contest_for_export(games, list(range(1, 16)))
    assert len(rows) == 5
    assert all(row["origem_dezenas_conferencia"] == "cartao_final" for row in rows)


def test_export_respects_generated_quantity() -> None:
    games = [{"numbers": list(range(1, 16)), "formato_cartao": 15} for _ in range(7)]
    export_rows = admin_app._build_generation_export_rows(games)
    assert len(export_rows) == 7
    assert export_rows[0]["jogo"] == 1
    assert export_rows[-1]["jogo"] == 7


def test_generation_page_exposes_allowed_quantities() -> None:
    source = inspect.getsource(admin_app._render_generation_page)
    assert "ALLOWED_GENERATION_QUANTITIES" in source
    assert 'key="institutional_operational_total_games"' in source


def test_run_institutional_generation_rejects_invalid_quantity(monkeypatch: pytest.MonkeyPatch) -> None:
    errors: list[str] = []

    class _SessionState(dict):
        def get(self, key, default=None):
            return super().get(key, default)

    monkeypatch.setattr(admin_app.st, "session_state", _SessionState())
    monkeypatch.setattr(admin_app.st, "error", lambda message: errors.append(str(message)))

    admin_app._run_institutional_generation(
        total_games=11,
        dezenas_per_game=15,
        use_top50=True,
        odd_min=5,
        odd_max=10,
        even_min=5,
        even_max=10,
        sequence_max=15,
        coverage_min=0.0,
        entropy_min=0.0,
        repeat_limit=10,
        snapshot={"counts": {}},
    )

    assert errors
    assert "Quantidade de jogos inválida" in errors[0]


def test_run_institutional_generation_accepts_quantity_one(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_app,
        "_generate_direct_15_games",
        lambda **kwargs: [{"numbers": list(range(1, 16)), "game_index": 1}],
    )
    monkeypatch.setattr(
        admin_app,
        "output_commander_validate_games",
        lambda games, **kwargs: {
            "status_comandante_saida": "APROVADO",
            "quantidade_jogos_unicos": len(games),
            "quantidade_jogos_aprovados": len(games),
            "quantidade_jogos_solicitada": kwargs.get("required_total", len(games)),
            "quantidade_jogos_rejeitados": 0,
            "invalid_games": [],
        },
    )
    monkeypatch.setattr(admin_app, "_load_latest_contest_summary", lambda: {"contest_number": 3700, "dezenas": list(range(1, 16))})
    monkeypatch.setattr(
        admin_app,
        "_load_previous_contest_numbers_for_rfe",
        lambda _target: RFEPreviousContestReference(
            found=True,
            contest_id=3699,
            numbers=list(range(1, 16)),
            source="test",
        ),
    )
    monkeypatch.setattr(admin_app, "_history_number_frequency", lambda: {})
    monkeypatch.setattr(admin_app, "_institutional_generation_policy", lambda _size: {})
    monkeypatch.setattr(admin_app, "_official_15_generation_context", lambda _group: {})
    monkeypatch.setattr(admin_app, "_compact_small_batch_adjustment", lambda **_: {})
    monkeypatch.setattr(admin_app, "load_all_output_signatures", lambda: set())
    monkeypatch.setattr(
        admin_app,
        "_persist_generation_snapshot",
        lambda **kwargs: {"generation_event_id": 1, "games_count": len(kwargs["games"])},
    )

    class _SessionState(dict):
        def get(self, key, default=None):
            return super().get(key, default)

    monkeypatch.setattr(admin_app.st, "session_state", _SessionState())
    monkeypatch.setattr(admin_app.st, "error", lambda *_args, **_kwargs: None)

    admin_app._run_institutional_generation(
        total_games=1,
        dezenas_per_game=15,
        use_top50=True,
        odd_min=5,
        odd_max=10,
        even_min=5,
        even_max=10,
        sequence_max=15,
        coverage_min=0.0,
        entropy_min=0.0,
        repeat_limit=10,
        snapshot={"counts": {}},
    )

    generation_result = admin_app.st.session_state.get("institutional_generation_result") or {}
    assert len(generation_result.get("jogos") or []) == 1
