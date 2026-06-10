from __future__ import annotations

import pytest

from dashboard import institutional_app as app
from lotoia.observability.observational_leftover import (
    ML_ROLE_DIAGNOSTIC_ONLY,
    OBSERVATIONAL_SOURCE_CARTAO_FINAL,
    REAL_LEFTOVER_BASIS,
    build_real_post_conference_leftover_payload,
    compute_dezenas_acertadas,
    compute_dezenas_sobrando,
    validate_observational_source,
    validate_real_leftover_guards,
)


def test_real_leftovers() -> None:
    payload = build_real_post_conference_leftover_payload(
        cartao_final=[1, 2, 3, 4, 5],
        resultado_oficial=[1, 3, 5, 7, 9],
    )
    assert payload["dezenas_observadas"] == [1, 2, 3, 4, 5]
    assert payload["cartao_referencia"] == [1, 3, 5, 7, 9]
    assert payload["dezenas_acertadas"] == [1, 3, 5]
    assert payload["dezenas_sobrando"] == [2, 4]
    assert payload["dezenas_sobrando_count"] == 2
    assert payload["leftover_basis"] == REAL_LEFTOVER_BASIS
    assert payload["origem_observacional"] == OBSERVATIONAL_SOURCE_CARTAO_FINAL
    assert payload["ml_role"] == ML_ROLE_DIAGNOSTIC_ONLY


def test_hits_plus_leftovers_equals_card_size() -> None:
    cartao_final = [1, 2, 3, 4, 5]
    resultado_oficial = [1, 3, 5, 7, 9]
    acertadas = compute_dezenas_acertadas(cartao_final, resultado_oficial)
    sobrando = compute_dezenas_sobrando(cartao_final, resultado_oficial)
    assert len(acertadas) + len(sobrando) == len(cartao_final)


def test_dezenas_observadas_equals_cartao_final() -> None:
    payload = build_real_post_conference_leftover_payload(
        cartao_final=[10, 11, 12, 13],
        resultado_oficial=[10, 12, 14, 15, 16],
    )
    assert payload["dezenas_observadas"] == payload["cartao_final"]


def test_validate_observational_source_blocks_nucleo() -> None:
    assert validate_observational_source("nucleo_lei_15")
    assert validate_observational_source("nucleo_lei_15a_congelado")
    assert not validate_observational_source(OBSERVATIONAL_SOURCE_CARTAO_FINAL)


def test_build_observational_leftover_audit_row_uses_cartao_final_not_nucleo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    official_15 = [1, 3, 5, 7, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
    cartao_15d = [1, 2, 3, 4, 6, 8, 10, 11, 12, 13, 14, 16, 17, 18, 21]
    monkeypatch.setattr(
        app,
        "get_official_contest",
        lambda contest_id: {"contest_number": contest_id, "dezenas": official_15},
    )
    row = app._build_observational_leftover_audit_row(
        {
            "game_index": 1,
            "numbers": [1, 2, 3, 5, 7, 8, 10, 11, 13, 14, 18, 20, 22, 23, 25],
            "final_card_numbers": cartao_15d,
            "formato_cartao": 15,
        },
        concurso_analisado=3700,
        generation_event_id=42,
        reconciliation_run_id=9,
    )
    assert row["origem_observacional"] == OBSERVATIONAL_SOURCE_CARTAO_FINAL
    assert row["origem_observacional"] != "nucleo_lei_15"
    assert row["formato_cartao"] == 15
    assert row["dezenas_observadas"] == row["cartao_final"] == "01 02 03 04 06 08 10 11 12 13 14 16 17 18 21"
    assert row["cartao_referencia"] == row["resultado_oficial"]
    assert row["dezenas_acertadas"] == "01 03 11 12 13 14 16 17 18"
    assert row["dezenas sobrando"] == "02 04 06 08 10 21"
    assert row["dezenas faltantes"] == "05 07 09 15 19 20"
    assert row["leftover_basis"] == REAL_LEFTOVER_BASIS
    assert row["ml_role"] == ML_ROLE_DIAGNOSTIC_ONLY


def test_build_observational_leftover_audit_row_blocks_without_cartao_final(
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
            "numbers": [1, 2, 3, 5, 7, 8, 10, 11, 13, 14, 18, 20, 22, 23, 25],
        },
        concurso_analisado=3700,
        generation_event_id=42,
        reconciliation_run_id=9,
    )
    assert "cartao_final_missing" in str(row["observação institucional"])
    assert row["origem_observacional"] == "indisponivel"


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


def test_validate_real_leftover_guards_blocks_missing_inputs() -> None:
    errors = validate_real_leftover_guards(
        cartao_final=[],
        resultado_oficial=[],
        concurso_analisado=None,
        generation_event_id=None,
        origem_observacional="nucleo_lei_15",
    )
    assert "cartao_final_missing" in errors
    assert "resultado_oficial_missing" in errors
    assert "concurso_analisado_missing" in errors
    assert "generation_event_id_missing" in errors
    assert "origem_observacional_invalid" in errors
    assert any("origem_observacional_forbidden" in error for error in errors)
