from __future__ import annotations

from dashboard import institutional_app as app
from lotoia.observability.observational_leftover import (
    LEFTOVER_BASIS,
    build_observational_leftover_payload,
    compute_dezenas_sobrando,
)


def test_leftover_set_difference() -> None:
    result = compute_dezenas_sobrando(["01", "02", "03", "04", "05"], ["02", "04", "06"])
    assert result == [1, 3, 5]


def test_no_leftover_when_all_observed_in_reference() -> None:
    result = compute_dezenas_sobrando(["01", "02", "03"], ["01", "02", "03", "04"])
    assert result == []


def test_leftover_not_hardcoded() -> None:
    row_a = build_observational_leftover_payload(
        observadas=[1, 2, 3, 4, 5],
        cartao_referencia=[2, 4, 6],
    )
    row_b = build_observational_leftover_payload(
        observadas=[10, 11, 12],
        cartao_referencia=[10],
    )
    assert row_a["dezenas_sobrando"] != row_b["dezenas_sobrando"]
    assert row_a["dezenas_sobrando_count"] == 3
    assert row_b["dezenas_sobrando_count"] == 2


def test_leftover_payload_includes_basis_and_reference_card() -> None:
    payload = build_observational_leftover_payload(
        observadas=[1, 2, 3],
        cartao_referencia=[2, 4],
    )
    assert payload["leftover_basis"] == LEFTOVER_BASIS
    assert payload["cartao_referencia"] == [2, 4]
    assert payload["dezenas_sobrando"] == [1, 3]
    assert payload["dezenas_sobrando_count"] == 2


def test_build_observational_leftover_audit_row_uses_set_difference() -> None:
    game = {
        "game_index": 1,
        "odd": 8,
        "even": 7,
        "numbers": [1, 2, 3, 5, 7, 8, 10, 11, 13, 14, 18, 20, 22, 23, 25],
        "final_card_numbers": [1, 2, 3, 4, 5, 7, 8, 10, 11, 13, 14, 18, 20, 22, 23, 25],
        "generation_context": {
            "core_numbers": [1, 2, 3, 5, 7, 8, 10, 11, 13, 14, 18, 20, 22, 23, 25],
            "audited_reserve_numbers": [4],
            "final_card_numbers": [1, 2, 3, 4, 5, 7, 8, 10, 11, 13, 14, 18, 20, 22, 23, 25],
            "selected_card_format": 16,
        },
        "formato_cartao": 16,
    }
    row = app._build_observational_leftover_audit_row(game)
    assert row["leftover_basis"] == LEFTOVER_BASIS
    assert row["cartao_referencia"] != "-"
    assert row["dezenas_sobrando_count"] == len(
        [token for token in str(row["dezenas sobrando"]).split() if token and token != "-"]
    )
    assert "01 02 03" not in str(row["dezenas sobrando"]) or row["dezenas_sobrando_count"] == 0


def test_leftover_audit_row_differs_from_fixed_nucleo_slice() -> None:
    game_a = {
        "game_index": 1,
        "numbers": [1, 2, 3, 5, 7, 8, 10, 11, 13, 14, 18, 20, 22, 23, 25],
        "final_card_numbers": [1, 2, 3, 5, 7, 8, 10, 11, 13, 14, 18, 20, 22, 23, 25],
        "generation_context": {
            "core_numbers": [1, 2, 3, 5, 7, 8, 10, 11, 13, 14, 18, 20, 22, 23, 25],
            "audited_reserve_numbers": [4, 6],
            "final_card_numbers": [1, 2, 3, 5, 7, 8, 10, 11, 13, 14, 18, 20, 22, 23, 25],
        },
    }
    game_b = {
        "game_index": 2,
        "numbers": [2, 4, 6, 7, 8, 9, 11, 12, 13, 16, 17, 18, 20, 21, 25],
        "final_card_numbers": [2, 4, 6, 7, 8, 9, 11, 12, 13, 16, 17, 18, 20, 21, 25],
        "generation_context": {
            "core_numbers": [2, 4, 6, 7, 8, 9, 11, 12, 13, 16, 17, 18, 20, 21, 25],
            "audited_reserve_numbers": [1, 15],
            "final_card_numbers": [2, 4, 6, 7, 8, 9, 11, 12, 13, 16, 17, 18, 20, 21, 25],
        },
    }
    row_a = app._build_observational_leftover_audit_row(game_a)
    row_b = app._build_observational_leftover_audit_row(game_b)
    assert row_a["dezenas sobrando"] == "04 06"
    assert row_b["dezenas sobrando"] == "01 15"
    assert row_a["dezenas sobrando"] != " ".join(f"{number:02d}" for number in game_a["numbers"][:5])
