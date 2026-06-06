from __future__ import annotations

from dashboard import institutional_app as admin_app


def test_conferencia_19d_usa_cartao_final_para_acertar_15_no_concurso_3700() -> None:
    game = {
        "generation_event_id": 999,
        "formato_cartao": 19,
        "nucleo_lei_15": "01 03 07 08 09 10 12 13 14 17 18 20 22 23 24",
        "reservas_auditadas": "19 25 04 05",
        "cartao_final": "01 03 04 05 07 08 09 10 12 13 14 17 18 19 20 22 23 24 25",
    }

    official_3700 = [1, 3, 7, 8, 9, 10, 12, 13, 14, 17, 18, 19, 20, 23, 25]

    info = admin_app._select_conference_numbers(game)

    assert info["formato_cartao"] == 19
    assert info["origem_dezenas_conferencia"] == "cartao_final"
    assert info["dezenas_conferidas_count"] == 19
    assert info["expected_card_size"] == 19
    assert info["actual_card_size"] == 19

    hits = len(set(info["conference_numbers"]) & set(official_3700))

    assert hits == 15
