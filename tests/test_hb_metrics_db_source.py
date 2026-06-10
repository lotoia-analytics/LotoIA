from __future__ import annotations

from dashboard import institutional_app as app


def test_build_hb_metrics_payload_from_reconciliation_sample() -> None:
    games = [
        {
            "numbers": [1, 2, 3, 4, 6, 8, 10, 11, 12, 13, 14, 16, 17, 18, 21],
            "hits": 11,
            "contest_id": 3700,
        },
        {
            "numbers": [1, 2, 3, 5, 7, 8, 10, 11, 13, 14, 18, 20, 22, 23, 25],
            "hits": 10,
            "contest_id": 3700,
        },
        {
            "numbers": [2, 4, 6, 7, 8, 9, 11, 12, 13, 16, 17, 18, 20, 21, 25],
            "hits": 12,
            "contest_id": 3700,
        },
    ]
    payload = app._build_hb_metrics_payload_from_reconciliation(
        reconciliation_run_id=99,
        contest_id=3700,
        games_rows=games,
    )
    assert payload["available"] is True
    assert payload["source"] == "postgresql"
    assert payload["reconciliation_run_id"] == 99
    assert payload["media_acertos"] == 11.0
    assert payload["jogos_11_mais"] == 2
    assert payload["jogos_12_mais"] == 1
    assert payload["jogos_analisados"] == 3
    assert payload["concursos_analisados"] == 1
    assert payload["tamanho_conjunto"] > 0
    assert payload["entropia_estrutural"] > 0.0
    assert payload["media_sobreposicao"] >= 0.0
    assert payload["dezenas_dominantes"]


def test_empty_hb_metrics_payload_defaults() -> None:
    payload = app._empty_hb_metrics_payload()
    assert payload["available"] is False
    assert payload["source"] == "postgresql"
    assert payload["media_acertos"] == 0.0
    assert payload["jogos_analisados"] == 0
