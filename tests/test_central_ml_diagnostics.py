from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import inspect

from lotoia.database.database import (
    LotofacilOfficialHistory,
    MlDiagnosticDecision,
    ReconciliationGame,
    ReconciliationRun,
    create_database,
    get_engine,
    get_session,
)
from lotoia.observability.ml_diagnostic_panels import (
    ADM_ACEITO,
    ADM_REJEITADO,
    ALERT_001,
    ALERT_002,
    ALERT_003,
    ACTION_AJUSTE_POOL,
    ACTION_PROMOVER_RESERVA_ADR,
    ACTION_VIGILANCIA_DEZENA,
    STATUS_PENDENTE,
    build_alert_001_cards,
    build_alert_002_cards,
    build_alert_003_cards,
    build_central_ml_diagnostics_payload,
    register_ml_diagnostic_decision,
)

OFFICIAL_15 = [1, 3, 5, 7, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
NUCLEO = {1, 2, 3, 4, 9, 10, 11, 12, 13, 18, 20, 22, 23, 24, 25}


def _seed_official_history(session, contest_id: int = 3700) -> None:
    session.add(
        LotofacilOfficialHistory(
            contest_number=contest_id,
            draw_date=datetime.now(UTC).date().isoformat(),
            numbers=" ".join(f"{number:02d}" for number in OFFICIAL_15),
            source="test",
        )
    )


def _seed_reconciliation_run(
    session,
    *,
    contest_id: int = 3700,
    games: list[dict],
    run_suffix: int = 1,
) -> int:
    run = ReconciliationRun(
        generation_event_id=100 + run_suffix,
        contest_id=contest_id,
        prize_count=0,
        total_hits=sum(game["hits"] for game in games),
        best_hits=max(game["hits"] for game in games),
        created_at=datetime.now(UTC),
        payload={},
    )
    session.add(run)
    session.flush()
    for index, game in enumerate(games, start=1):
        numbers = list(game["numbers"])
        matched = sorted(set(numbers) & set(OFFICIAL_15))
        session.add(
            ReconciliationGame(
                reconciliation_run_id=run.id,
                generation_event_id=100 + run_suffix,
                contest_id=contest_id,
                game_index=index,
                numbers=numbers,
                hits=int(game["hits"]),
                matched_numbers=matched,
                prize_status="nao_premiado",
                prize_tier="",
                context_json={},
            )
        )
    session.commit()
    return int(run.id)


def _context_from_games(games: list[dict], run_id: int = 42) -> dict:
    return {
        "available": True,
        "reconciliation_run_id": run_id,
        "resultado_oficial": OFFICIAL_15,
        "games": games,
    }


def test_ml_diagnostic_decisions_table_created(tmp_path) -> None:
    db_path = tmp_path / "ml_diag.db"
    create_database(db_path)
    inspector = inspect(get_engine(db_path))
    assert "ml_diagnostic_decisions" in inspector.get_table_names()
    columns = {column["name"] for column in inspector.get_columns("ml_diagnostic_decisions")}
    assert {
        "id",
        "alert_type",
        "dezena",
        "ml_proposal",
        "adm_decision",
        "adm_reason",
        "reconciliation_run_id",
        "created_at",
        "decided_at",
    } <= columns


def test_alert_001_recurrent_side_leak() -> None:
    leak_card = sorted([1, 3, 5, 7, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 6])
    games = [
        {"numbers": leak_card, "hits": 14},
        {"numbers": leak_card, "hits": 14},
        {"numbers": leak_card, "hits": 14},
    ]
    contexts = [
        _context_from_games(games, run_id=10),
        _context_from_games(games, run_id=9),
    ]
    cards = build_alert_001_cards(contexts)
    assert len(cards) == 1
    card = cards[0]
    assert card["tipo_alerta"] == ALERT_001
    assert card["dezena"] == 6
    assert card["ml_proposal"]["action"] == ACTION_PROMOVER_RESERVA_ADR
    assert card["ml_diagnosis"]["consecutivas"] >= 2
    assert card["status"] == STATUS_PENDENTE
    assert card["leakage_evidence"]["drilldown_per_dezena"]["06"]


def test_alert_002_blind_spot_evolution() -> None:
    games = [
        {"numbers": sorted(NUCLEO), "hits": 13},
        {"numbers": sorted(NUCLEO), "hits": 14},
    ]
    cards = build_alert_002_cards(_context_from_games(games))
    blind_cards = [card for card in cards if card["dezena"] in {6, 16, 17, 21}]
    assert blind_cards
    card = blind_cards[0]
    assert card["tipo_alerta"] == ALERT_002
    assert card["ml_diagnosis"]["tipo"] == "blind_spot_confirmado"
    assert card["ml_proposal"]["action"] == ACTION_VIGILANCIA_DEZENA


def test_alert_003_candidate_conversion() -> None:
    games = [
        {"numbers": sorted(NUCLEO), "hits": 13},
        {"numbers": sorted(NUCLEO), "hits": 13},
        {"numbers": sorted(NUCLEO | {5}), "hits": 12},
    ]
    cards = build_alert_003_cards(_context_from_games(games))
    assert cards
    card = cards[0]
    assert card["tipo_alerta"] == ALERT_003
    assert card["ml_proposal"]["action"] == ACTION_AJUSTE_POOL
    assert card["ml_proposal"]["constraint"] == "nucleo_lei15_15D permanece soberano"
    assert card["ml_diagnosis"]["taxa_conversao_13_14"] > 50.0


def _sample_leakage_evidence() -> dict:
    return {
        "leakage_table": [
            {
                "dezena": "06",
                "frequencia_vazamento": 2,
                "percentual_vazamento": 100.0,
                "sample_size": 2,
                "reconciliation_run_id": 99,
            }
        ],
        "drilldown_per_dezena": {
            "06": [
                {
                    "dezena": "06",
                    "jogo_id": 1,
                    "generation_event_id": 1,
                    "reconciliation_run_id": 99,
                    "concurso_analisado": 3700,
                    "cartao_final": "06 18",
                    "resultado_oficial": "18 20",
                    "hits": 1,
                    "sobra_real": "06",
                    "vazou": True,
                }
            ]
        },
    }


def test_register_ml_diagnostic_decision_persists_accept_and_reject(tmp_path) -> None:
    db_path = tmp_path / "decisions.db"
    create_database(db_path)
    evidence = _sample_leakage_evidence()
    accepted = register_ml_diagnostic_decision(
        alert_type=ALERT_001,
        dezena=6,
        ml_proposal={
            "action": ACTION_PROMOVER_RESERVA_ADR,
            "target_dezena": "06",
            "drilldown_rows": 1,
        },
        adm_decision=ADM_ACEITO,
        reconciliation_run_id=99,
        adm_user="adm@test.local",
        leakage_evidence=evidence,
        db_path=db_path,
    )
    rejected = register_ml_diagnostic_decision(
        alert_type=ALERT_002,
        dezena=16,
        ml_proposal={"action": ACTION_VIGILANCIA_DEZENA, "target_dezena": "16"},
        adm_decision=ADM_REJEITADO,
        adm_reason="evidência insuficiente",
        reconciliation_run_id=99,
        adm_user="adm@test.local",
        db_path=db_path,
    )
    assert accepted["adm_decision"] == ADM_ACEITO
    assert rejected["adm_decision"] == ADM_REJEITADO
    assert rejected["reason"] == "evidência insuficiente"
    with get_session(db_path) as session:
        rows = session.query(MlDiagnosticDecision).order_by(MlDiagnosticDecision.id.asc()).all()
    assert len(rows) == 2
    assert rows[0].adm_decision == ADM_ACEITO
    assert rows[1].adm_reason == "evidência insuficiente"


def test_register_reject_requires_reason(tmp_path) -> None:
    db_path = tmp_path / "reject.db"
    create_database(db_path)
    with pytest.raises(ValueError, match="adm_reason"):
        register_ml_diagnostic_decision(
            alert_type=ALERT_003,
            dezena=5,
            ml_proposal={"action": ACTION_AJUSTE_POOL},
            adm_decision=ADM_REJEITADO,
            reconciliation_run_id=1,
            db_path=db_path,
        )


def test_central_payload_merges_decisions_and_counts_active(tmp_path) -> None:
    db_path = tmp_path / "central.db"
    create_database(db_path)
    with get_session(db_path) as session:
        _seed_official_history(session)
        leak_card = sorted([1, 3, 5, 7, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 6])
        games = [
            {"numbers": leak_card, "hits": 14},
            {"numbers": leak_card, "hits": 14},
            {"numbers": leak_card, "hits": 14},
        ]
        run_id_1 = _seed_reconciliation_run(session, games=games, run_suffix=1)
        run_id_2 = _seed_reconciliation_run(session, games=games, run_suffix=2)
    assert run_id_1 > 0
    assert run_id_2 > 0
    payload = build_central_ml_diagnostics_payload(db_path=db_path)
    assert payload["source"] == "postgresql"
    assert payload["generation_command"] is False
    alert_types = {alert["tipo_alerta"] for alert in payload["alerts"]}
    assert ALERT_001 in alert_types
    register_ml_diagnostic_decision(
        alert_type=ALERT_001,
        dezena=6,
        ml_proposal={"action": ACTION_PROMOVER_RESERVA_ADR, "drilldown_rows": 1},
        adm_decision=ADM_ACEITO,
        reconciliation_run_id=run_id_2,
        adm_user="adm@test.local",
        leakage_evidence=_sample_leakage_evidence(),
        db_path=db_path,
    )
    payload_after = build_central_ml_diagnostics_payload(db_path=db_path)
    assert payload_after["history"]
    assert payload_after["total_alertas_ativos"] == len(
        [alert for alert in payload_after["alerts"] if alert["status"] == STATUS_PENDENTE]
    )


def test_sample_alert_cards_each_type() -> None:
    leak_card = sorted([1, 3, 5, 7, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 6])
    alert_001 = build_alert_001_cards(
        [
            _context_from_games(
                [{"numbers": leak_card, "hits": 14}] * 3,
                run_id=2,
            ),
            _context_from_games(
                [{"numbers": leak_card, "hits": 14}] * 3,
                run_id=1,
            ),
        ]
    )[0]
    alert_002 = build_alert_002_cards(
        _context_from_games(
            [
                {"numbers": sorted(NUCLEO), "hits": 13},
                {"numbers": sorted(NUCLEO), "hits": 14},
            ]
        )
    )[0]
    alert_003 = build_alert_003_cards(
        _context_from_games(
            [
                {"numbers": sorted(NUCLEO), "hits": 13},
                {"numbers": sorted(NUCLEO), "hits": 13},
            ]
        )
    )[0]
    assert alert_001["tipo_alerta"] == ALERT_001
    assert alert_002["tipo_alerta"] == ALERT_002
    assert alert_003["tipo_alerta"] == ALERT_003
    assert alert_001["ml_proposal"]["action"] == ACTION_PROMOVER_RESERVA_ADR
    assert alert_002["ml_proposal"]["action"] == ACTION_VIGILANCIA_DEZENA
    assert alert_003["ml_proposal"]["action"] == ACTION_AJUSTE_POOL
