from __future__ import annotations

import pytest

from dashboard import institutional_app as admin_app


def test_rfe_previous_contest_reference_3704_uses_3703(monkeypatch) -> None:
    monkeypatch.setattr(
        admin_app,
        "_load_official_history_contest",
        lambda contest_number: {
            "concurso": contest_number,
            "dezenas": [1, 3, 5, 7, 8, 9, 10, 14, 15, 17, 21, 22, 23, 24, 25],
        }
        if contest_number == 3703
        else None,
    )

    reference = admin_app._load_previous_contest_numbers_for_rfe(3704)

    assert reference.found is True
    assert reference.contest_id == 3703
    assert reference.numbers == [1, 3, 5, 7, 8, 9, 10, 14, 15, 17, 21, 22, 23, 24, 25]
    assert reference.source == "official_lotofacil_history"
    assert reference.message is None


def test_rfe_without_target_uses_latest_official_persisted(monkeypatch) -> None:
    monkeypatch.setattr(
        admin_app,
        "_load_official_history_diagnostics",
        lambda: {
            "contest_number_max": 3703,
        },
    )
    monkeypatch.setattr(
        admin_app,
        "_load_official_history_contest",
        lambda contest_number: {
            "concurso": contest_number,
            "dezenas": [1, 3, 5, 7, 8, 9, 10, 14, 15, 17, 21, 22, 23, 24, 25],
        }
        if contest_number == 3703
        else None,
    )

    reference = admin_app._load_previous_contest_numbers_for_rfe(None)

    assert reference.found is True
    assert reference.contest_id == 3703
    assert reference.numbers == [1, 3, 5, 7, 8, 9, 10, 14, 15, 17, 21, 22, 23, 24, 25]
    assert reference.source == "official_lotofacil_history"


def test_official_contest_gateway_is_shared_between_conference_and_rfe(monkeypatch) -> None:
    monkeypatch.setattr(
        admin_app,
        "_load_official_history_diagnostics",
        lambda: {
            "contest_number_max": 3703,
        },
    )
    monkeypatch.setattr(
        admin_app,
        "_load_official_history_contest",
        lambda contest_number: {
            "concurso": contest_number,
            "dezenas": [1, 3, 5, 7, 8, 9, 10, 14, 15, 17, 21, 22, 23, 24, 25],
        }
        if contest_number == 3703
        else None,
    )

    latest_official = admin_app.get_latest_official_contest()
    previous_reference = admin_app.get_previous_official_contest(3704)

    assert latest_official is not None
    assert latest_official["official_contest_source"] == "official_lotofacil_history"
    assert latest_official["official_contest_id"] == 3703
    assert latest_official["official_contest_numbers"] == "01 03 05 07 08 09 10 14 15 17 21 22 23 24 25"
    assert previous_reference.found is True
    assert previous_reference.contest_id == 3703
    assert previous_reference.source == "official_lotofacil_history"


def test_rfe_previous_contest_numbers_must_have_15_numbers(monkeypatch) -> None:
    monkeypatch.setattr(
        admin_app,
        "_load_official_history_contest",
        lambda contest_number: {"concurso": contest_number, "dezenas": [1, 3, 5, 7, 8, 9, 10, 14, 15, 17]}
        if contest_number == 3703
        else None,
    )

    reference = admin_app._load_previous_contest_numbers_for_rfe(3704)

    assert reference.found is False
    assert reference.contest_id == 3703
    assert reference.numbers == []
    assert reference.source == "official_lotofacil_history"
    assert reference.message is not None


def test_rfe_receives_normalized_previous_numbers_from_string() -> None:
    normalized = admin_app._normalize_official_numbers("01 03 05 07 08 09 10 14 15 17 21 22 23 24 25")

    assert normalized == [1, 3, 5, 7, 8, 9, 10, 14, 15, 17, 21, 22, 23, 24, 25]


@pytest.mark.parametrize("card_format", list(range(15, 24)))
def test_conference_uses_final_card_numbers_for_expanded_formats(card_format: int) -> None:
    official_numbers = [1, 3, 5, 7, 8, 9, 10, 14, 15, 17, 21, 22, 23, 24, 25]
    reserve_numbers = [2, 4, 6, 11, 12, 13, 16, 18, 19, 20]
    final_card_numbers = sorted(official_numbers + reserve_numbers[: max(0, card_format - 15)])
    game = {
        "generation_event_id": 383,
        "game_index": 1,
        "formato_cartao": card_format,
        "numbers": list(official_numbers),
        "core_numbers": list(official_numbers),
        "audited_reserve_numbers": list(reserve_numbers[: max(0, card_format - 15)]),
        "final_card_numbers": list(final_card_numbers),
        "quantidade_nucleo": 15,
        "quantidade_reservas": max(0, card_format - 15),
        "quantidade_final": card_format,
        "game_signature": "signature-383-1",
    }
    contest = {
        "concurso": 3702,
        "data": "03/06/2026",
        "dezenas": list(official_numbers),
    }

    comparison = admin_app._compare_games_against_contest(
        generation_event_id=383,
        games=[game],
        contest=contest,
    )

    diagnostics = dict(comparison.get("diagnostics") or {})
    result = dict(comparison.get("results", [{}])[0] or {})

    assert comparison.get("generation_event_id") == 383
    assert diagnostics.get("generation_event_id") == 383
    assert diagnostics.get("formato_cartao") == card_format
    assert diagnostics.get("dezenas_conferidas_count") == card_format
    assert diagnostics.get("expected_card_size") == card_format
    assert diagnostics.get("actual_card_size") == card_format
    assert result.get("formato_cartao") == card_format
    assert result.get("dezenas_conferidas_count") == card_format
    assert result.get("expected_card_size") == card_format
    assert result.get("actual_card_size") == card_format
    assert result.get("hits") == 15
    assert result.get("numbers") == final_card_numbers
    assert result.get("matched_numbers") == official_numbers
    assert result.get("game_signature") == "signature-383-1"
    assert diagnostics.get("origem_dezenas_conferencia") == "cartao_final"


def test_generation_stops_before_attempts_when_previous_contest_missing() -> None:
    with pytest.raises(RuntimeError, match="BLK-LEGACY-GEN-001"):
        admin_app._generate_direct_15_games(
            total_games=20,
            seed=123,
            history_frequency={},
            latest_numbers=set(),
            batch_number_usage={},
            batch_profile_usage={},
            batch_total_games=20,
            core_numbers=[],
            discouraged_numbers=[],
            max_frequency_ratio=1.0,
            min_frequency_ratio=0.0,
            preferred_profile_ratios={},
            odd_min=0,
            odd_max=15,
            even_min=0,
            even_max=15,
            sequence_max=15,
            coverage_min=0.0,
            entropy_min=0.0,
            repeat_min=0,
            repeat_max=15,
            preferred_parity_pairs=[],
            allowed_parity_pairs=[],
            fill_diagnostics={},
            previous_contest_numbers=[],
        )


def test_clean_law15_generation_preserves_rfe_block_when_attempts_zero(monkeypatch) -> None:
    monkeypatch.setenv("LOTOIA_LEI15_CORE_002_GENERATION_ENABLED", "0")
    monkeypatch.setattr(admin_app.st, "session_state", {})

    result = admin_app._run_clean_law15_generation(requested_count=10)

    assert result["blocked"] is True
    assert result["games"] == []
    assert "SOVEREIGN_GENERATION_BLOCKED" in str(result["commander_report"]["motivo_bloqueio"])


def test_structural_rfe_rejects_invalid_card_before_acceptance() -> None:
    with pytest.raises(RuntimeError, match="BLK-LEGACY-GEN-001"):
        admin_app._generate_direct_15_games(
            total_games=1,
            seed=123,
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
            odd_min=0,
            odd_max=15,
            even_min=0,
            even_max=15,
            sequence_max=15,
            coverage_min=0.0,
            entropy_min=0.0,
            repeat_min=0,
            repeat_max=15,
            preferred_parity_pairs=[],
            allowed_parity_pairs=[],
            fill_diagnostics={},
            previous_contest_numbers=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
        )
