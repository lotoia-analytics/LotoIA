from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from dashboard import institutional_app as app
from lotoia.observability.observational_leftover import (
    REAL_LEFTOVER_BASIS,
    build_real_post_conference_leftover_payload,
    compute_dezenas_acertadas,
    compute_dezenas_sobrando,
    validate_real_leftover_guards,
)


def test_real_leftovers() -> None:
    payload = build_real_post_conference_leftover_payload(
        cartao_final=[1, 2, 3, 4, 5],
        resultado_oficial=[1, 3, 5, 7, 9],
    )
    assert payload["dezenas_acertadas"] == [1, 3, 5]
    assert payload["dezenas_sobrando"] == [2, 4]
    assert payload["dezenas_sobrando_count"] == 2
    assert payload["dezenas_faltando"] == [7, 9]
    assert payload["leftover_basis"] == REAL_LEFTOVER_BASIS


def test_hits_plus_leftovers_equals_card_size() -> None:
    cartao_final = [1, 2, 3, 4, 5]
    resultado_oficial = [1, 3, 5, 7, 9]
    acertadas = compute_dezenas_acertadas(cartao_final, resultado_oficial)
    sobrando = compute_dezenas_sobrando(cartao_final, resultado_oficial)
    assert len(acertadas) + len(sobrando) == len(cartao_final)


def test_no_leftover_when_all_card_numbers_hit() -> None:
    payload = build_real_post_conference_leftover_payload(
        cartao_final=[1, 2, 3],
        resultado_oficial=[1, 2, 3, 4, 5],
    )
    assert payload["dezenas_sobrando"] == []
    assert payload["dezenas_sobrando_count"] == 0
    assert payload["dezenas_acertadas"] == [1, 2, 3]


def test_leftover_not_hardcoded_for_different_rows() -> None:
    row_a = build_real_post_conference_leftover_payload(cartao_final=[1, 2, 3, 4, 5], resultado_oficial=[1, 3, 5])
    row_b = build_real_post_conference_leftover_payload(cartao_final=[10, 11, 12], resultado_oficial=[10])
    assert row_a["dezenas_sobrando"] != row_b["dezenas_sobrando"]


def test_validate_real_leftover_guards_blocks_missing_inputs() -> None:
    errors = validate_real_leftover_guards(
        cartao_final=[],
        resultado_oficial=[],
        concurso_analisado=None,
        generation_event_id=None,
    )
    assert "cartao_final_missing" in errors
    assert "resultado_oficial_missing" in errors
    assert "concurso_analisado_missing" in errors
    assert "generation_event_id_missing" in errors


def test_build_observational_leftover_audit_row_uses_official_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    official_15 = [1, 3, 5, 7, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
    monkeypatch.setattr(
        app,
        "get_official_contest",
        lambda contest_id: {"contest_number": contest_id, "dezenas": official_15},
    )
    row = app._build_observational_leftover_audit_row(
        {
            "game_index": 1,
            "final_card_numbers": [1, 2, 3, 4, 5],
            "formato_cartao": 5,
        },
        concurso_analisado=3700,
        generation_event_id=42,
        reconciliation_run_id=9,
    )
    assert row["leftover_basis"] == REAL_LEFTOVER_BASIS
    assert row["resultado_oficial"] == "01 03 05 07 09 11 12 13 14 15 16 17 18 19 20"
    assert row["cartao_final"] == "01 02 03 04 05"
    assert row["dezenas_acertadas"] == "01 03 05"
    assert row["dezenas sobrando"] == "02 04"
    assert row["dezenas_sobrando_count"] == 2
    assert row["generation_event_id"] == 42
    assert row["reconciliation_run_id"] == 9
    assert row["concurso analisado"] == 3700


def test_build_observational_leftover_audit_row_blocks_without_official(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app, "get_official_contest", lambda _contest_id: None)
    row = app._build_observational_leftover_audit_row(
        {"game_index": 1, "final_card_numbers": [1, 2, 3, 4, 5]},
        concurso_analisado=3700,
        generation_event_id=42,
        reconciliation_run_id=9,
    )
    assert "resultado_oficial_missing" in str(row["observação institucional"])
    assert row["dezenas sobrando"] == "-"
