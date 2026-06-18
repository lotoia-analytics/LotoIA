from __future__ import annotations

from dashboard.institutional_build import BUILD_MARKER
from lotoia.ml.ml_operational_verdict import (
    MISSION_ID,
    VERDICT_APROVADO,
    VERDICT_APROVADO_COM_ALERTA,
    VERDICT_BLOQUEADO,
    VERDICT_PRECISA_CALIBRAR,
    VERDICT_REPROVADO,
    evaluate_batch_ml_verdict_from_games,
    evaluate_ml_operational_verdict,
    is_ml_official_release_allowed,
    is_ml_verdict_blocking,
)
from lotoia.ml.overlap_format_thresholds import evaluate_format_overlap_verdict


def test_build_marker_v56() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v57"


def test_mission_id() -> None:
    assert MISSION_ID == "M-ML-060-FIX-01"


def test_real_world_critical_batch_example() -> None:
    """Cenário M-ML-060-FIX-01: similaridade 0.6182, overlap 17, quase repetidos 3214, 17D."""
    format_analyses = [
        evaluate_format_overlap_verdict(
            17,
            17,
            {
                "similaridade_media": 0.6182,
                "quase_repetidos": 3214,
                "diversity_score": 0.38,
            },
        ),
        evaluate_format_overlap_verdict(
            15,
            13,
            {
                "similaridade_media": 0.6182,
                "quase_repetidos": 3214,
                "diversity_score": 0.38,
            },
        ),
    ]
    payload = evaluate_ml_operational_verdict(
        {
            "similaridade_media": 0.6182,
            "sobreposicao_maxima": 17,
            "quase_repetidos": 3214,
            "desempenho_13_hits": 0,
            "desempenho_14_hits": 0,
            "desempenho_15_hits": 0,
            "total_jogos": 50,
            "formatos_analisados": [15, 17],
        },
        format_analyses=format_analyses,
        calibration_applied=False,
        calibration_authorized=False,
    )
    assert payload["ml_verdict"] in {VERDICT_BLOQUEADO, VERDICT_REPROVADO}
    assert is_ml_verdict_blocking(payload["ml_verdict"])
    assert not payload["official_release_allowed"]
    assert payload["official_release_label"] == "NÃO LIBERADA"
    assert "3214" in payload["ml_verdict_reason"] or "17" in payload["ml_verdict_reason"]
    assert payload["next_action"] == "Autorizar calibração supervisionada."
    assert payload["trace"]["mission_id"] == MISSION_ID


def test_approved_batch_without_critical_risk() -> None:
    payload = evaluate_ml_operational_verdict(
        {
            "similaridade_media": 0.42,
            "sobreposicao_maxima": 10,
            "quase_repetidos": 2,
            "desempenho_13_hits": 1,
            "desempenho_14_hits": 0,
            "desempenho_15_hits": 0,
            "total_jogos": 20,
        },
        format_analyses=[
            evaluate_format_overlap_verdict(15, 10, {"similaridade_media": 0.42, "quase_repetidos": 2}),
        ],
        calibration_applied=False,
    )
    assert payload["ml_verdict"] == VERDICT_APROVADO
    assert payload["official_release_allowed"] is True
    assert is_ml_official_release_allowed(payload)


def test_similarity_attention_range_generates_alert() -> None:
    payload = evaluate_ml_operational_verdict(
        {
            "similaridade_media": 0.61,
            "sobreposicao_maxima": 11,
            "quase_repetidos": 5,
            "total_jogos": 20,
        },
        format_analyses=[
            evaluate_format_overlap_verdict(15, 11, {"similaridade_media": 0.61, "quase_repetidos": 5}),
        ],
    )
    assert payload["ml_verdict"] in {VERDICT_APROVADO_COM_ALERTA, VERDICT_PRECISA_CALIBRAR}
    if payload["ml_verdict"] == VERDICT_APROVADO_COM_ALERTA:
        assert payload["official_release_allowed"] is True


def test_similarity_above_070_reproved() -> None:
    payload = evaluate_ml_operational_verdict(
        {"similaridade_media": 0.72, "sobreposicao_maxima": 12, "quase_repetidos": 3, "total_jogos": 20},
        format_analyses=[
            evaluate_format_overlap_verdict(15, 12, {"similaridade_media": 0.72, "quase_repetidos": 3}),
        ],
    )
    assert payload["ml_verdict"] == VERDICT_REPROVADO
    assert not payload["official_release_allowed"]


def test_high_near_dup_with_attention_similarity_needs_calibration() -> None:
    payload = evaluate_ml_operational_verdict(
        {
            "similaridade_media": 0.6182,
            "sobreposicao_maxima": 13,
            "quase_repetidos": 3214,
            "total_jogos": 50,
        },
        format_analyses=[
            evaluate_format_overlap_verdict(
                15,
                13,
                {"similaridade_media": 0.6182, "quase_repetidos": 3214},
            ),
        ],
        calibration_applied=False,
    )
    assert payload["ml_verdict"] in {VERDICT_PRECISA_CALIBRAR, VERDICT_BLOQUEADO, VERDICT_REPROVADO}
    assert not payload["official_release_allowed"]


def test_evaluate_batch_from_games_empty_returns_approved() -> None:
    payload = evaluate_batch_ml_verdict_from_games([])
    assert payload["ml_verdict"] == VERDICT_APROVADO


def test_evaluate_batch_from_games_with_cards() -> None:
    games = [
        {
            "core_numbers": list(range(1, 16)),
            "final_card_numbers": list(range(1, 18)),
            "numbers": list(range(1, 18)),
        },
        {
            "core_numbers": list(range(2, 17)),
            "final_card_numbers": list(range(2, 19)),
            "numbers": list(range(2, 19)),
        },
    ]
    payload = evaluate_batch_ml_verdict_from_games(games)
    assert "ml_verdict" in payload
    assert "trace" in payload
