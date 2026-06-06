from __future__ import annotations

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


def test_generation_stops_before_attempts_when_previous_contest_missing() -> None:
    diagnostics: dict[str, object] = {}

    games = admin_app._generate_direct_15_games(
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
        fill_diagnostics=diagnostics,
        previous_contest_numbers=[],
    )

    assert games == []
    assert int(diagnostics.get("attempts_used", 0) or 0) == 0
    assert diagnostics.get("fill_completed") is False
    assert diagnostics.get("insufficient_reason") == "RFE_PREVIOUS_CONTEST_NOT_FOUND"


def test_clean_law15_generation_preserves_rfe_block_when_attempts_zero(monkeypatch) -> None:
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

    def _generate_stub(**kwargs):
        diagnostics = kwargs.get("fill_diagnostics")
        if isinstance(diagnostics, dict):
            diagnostics.update(
                {
                    "attempts_used": 0,
                    "candidate_pool_generated": 0,
                    "valid_candidates_found": 0,
                    "accepted_games": 0,
                    "rfe_enabled": True,
                    "rfe_previous_contest_found": False,
                    "rfe_previous_contest_id": None,
                    "rfe_previous_contest_numbers": "-",
                    "rfe_previous_contest_source": "indisponivel",
                    "rfe_previous_contest_message": None,
                    "rfe_status": "BLOQUEADO",
                    "fill_completed": False,
                    "insufficient_reason": "RFE_PREVIOUS_CONTEST_NOT_FOUND",
                }
            )
        return []

    monkeypatch.setattr(admin_app, "_generate_direct_15_games", _generate_stub)

    original_output_commander = admin_app.output_commander_validate_games
    try:
        admin_app.output_commander_validate_games = lambda games, **kwargs: {
            "status_comandante_saida": "BLOQUEADO",
            "motivo_bloqueio": "INSUFFICIENT_VALID_CANDIDATES",
            "error_message": "INSUFFICIENT_VALID_CANDIDATES",
            "quantidade_jogos_rejeitados": 10,
            "quantidade_jogos_aprovados": 0,
            "quantidade_jogos_unicos": 0,
        }

        result = admin_app._run_clean_law15_generation(requested_count=10)

        diagnostics = dict(result.get("fill_diagnostics") or {})
        assert diagnostics.get("candidate_pool_generated") == 0
        assert diagnostics.get("valid_candidates_found") == 0
        assert diagnostics.get("attempts_used") == 0
        assert diagnostics.get("rfe_status") == "BLOQUEADO"
        assert diagnostics.get("rejected_by_output_commander") == 0
        assert diagnostics.get("insufficient_reason") == "RFE_PREVIOUS_CONTEST_NOT_FOUND"
        assert result.get("official_contest_source") == "official_lotofacil_history"
        assert result.get("official_contest_id") == 3703
        assert result.get("official_contest_numbers") == "01 03 05 07 08 09 10 14 15 17 21 22 23 24 25"
        assert result.get("rfe_previous_contest_found") is True
        assert result.get("rfe_previous_contest_id") == 3703
        assert result.get("rfe_previous_contest_numbers") == "01 03 05 07 08 09 10 14 15 17 21 22 23 24 25"
        assert result.get("rfe_previous_contest_source") == "official_lotofacil_history"
    finally:
        admin_app.output_commander_validate_games = original_output_commander


def test_structural_rfe_rejects_invalid_card_before_acceptance(monkeypatch) -> None:
    call_counter = {"count": 0}

    monkeypatch.setattr(
        admin_app,
        "generate_ranked_games",
        lambda **kwargs: [{"numbers": [1]}, {"numbers": [2]}],
    )
    def _select_subset_from_candidate(*args, **kwargs):
        if call_counter["count"] == 0:
            call_counter["count"] += 1
            return [1, 2, 3, 4, 5, 6, 16, 17, 18, 19, 20, 21, 22, 23, 24]
        return [1, 2, 3, 4, 5, 6, 11, 16, 17, 18, 19, 20, 21, 22, 23]

    monkeypatch.setattr(admin_app, "_select_subset_from_candidate", _select_subset_from_candidate)
    monkeypatch.setattr(admin_app, "_force_subset_from_universe", lambda *args, **kwargs: [])

    diagnostics: dict[str, object] = {}
    games = admin_app._generate_direct_15_games(
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
        fill_diagnostics=diagnostics,
        previous_contest_numbers=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    )

    assert len(games) == 1
    assert games[0]["numbers"] == [1, 2, 3, 4, 5, 6, 11, 16, 17, 18, 19, 20, 21, 22, 23]
    assert int(diagnostics.get("rfe_rejected_games", 0) or 0) == 1
    assert int(diagnostics.get("rfe_01_rejected_games", 0) or 0) == 1
    assert int(diagnostics.get("rfe_02_rejected_games", 0) or 0) >= 1
    assert diagnostics.get("fill_completed") is True
    assert diagnostics.get("rfe_status") == "OK"
