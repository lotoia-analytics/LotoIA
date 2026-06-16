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
    STATUS_ACEITO,
    STATUS_PENDENTE,
    STATUS_PENDENTE_EVIDENCIA,
    STATUS_REJEITADO,
    VERDICT_ACCEPT_DIAGNOSTIC,
    VERDICT_REJECT,
    VERDICT_REQUEST_MORE_EVIDENCE,
    build_alert_001_cards,
    build_alert_002_cards,
    build_alert_003_cards,
    build_central_ml_diagnostics_payload,
    EVIDENCE_LEVEL_RECURRENT,
    EVIDENCE_STATUS_COMPLETE,
    EVIDENCE_STATUS_INSUFFICIENT,
    EVIDENCE_STATUS_INVALID,
    GOVERNANCE_STATUS_BLOCKED,
    GOVERNANCE_STATUS_SAFE_OBSERVATIONAL,
    build_adm_verdict_guide,
    enrich_alert_card_for_display,
    register_ml_diagnostic_decision,
    register_ml_diagnostic_verdict,
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


def _context_from_games(games: list[dict], run_id: int = 42, contest_id: int = 3704, generation_event_id: int = 492) -> dict:
    enriched_games = []
    for index, game in enumerate(games, start=1):
        enriched_games.append(
            {
                **game,
                "game_index": index,
                "generation_event_id": generation_event_id,
                "contest_id": contest_id,
            }
        )
    return {
        "available": True,
        "reconciliation_run_id": run_id,
        "contest_id": contest_id,
        "generation_event_id": generation_event_id,
        "resultado_oficial": OFFICIAL_15,
        "games": enriched_games,
    }


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
        "verdict_type",
        "status",
        "verdict_reason",
        "missing_evidence",
        "adr_candidate",
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


def test_register_ml_diagnostic_verdict_accept_reject_and_more_evidence(tmp_path) -> None:
    db_path = tmp_path / "decisions.db"
    create_database(db_path)
    evidence = _sample_leakage_evidence()
    alert_card = enrich_alert_card_for_display(
        {
            "tipo_alerta": ALERT_001,
            "dezena": 6,
            "dezena_fmt": "06",
            "ml_proposal": {
                "action": ACTION_PROMOVER_RESERVA_ADR,
                "target_dezena": "06",
                "drilldown_rows": 1,
            },
            "ml_diagnosis": {"sample_size": 2, "drilldown_available": True},
            "leakage_evidence": evidence,
            "generation_command": False,
            "recalibration_command": False,
            "evidence_level": EVIDENCE_LEVEL_RECURRENT,
            "verdict_buttons_allowed": True,
        }
    )
    accepted = register_ml_diagnostic_verdict(
        alert_type=ALERT_001,
        dezena=6,
        ml_proposal=alert_card["ml_proposal"],
        verdict_type=VERDICT_ACCEPT_DIAGNOSTIC,
        reconciliation_run_id=99,
        adm_user="adm@test.local",
        leakage_evidence=evidence,
        alert_card=alert_card,
        db_path=db_path,
    )
    more_evidence = register_ml_diagnostic_verdict(
        alert_type=ALERT_002,
        dezena=16,
        ml_proposal={"action": ACTION_VIGILANCIA_DEZENA, "target_dezena": "16"},
        verdict_type=VERDICT_REQUEST_MORE_EVIDENCE,
        reconciliation_run_id=98,
        verdict_reason="amostra insuficiente para blind spot",
        adm_user="adm@test.local",
        alert_card={
            "tipo_alerta": ALERT_002,
            "ml_proposal": {"action": ACTION_VIGILANCIA_DEZENA},
            "ml_diagnosis": {"aparicoes": 0, "faixa": "13->14"},
            "evidence_level": EVIDENCE_LEVEL_RECURRENT,
            "verdict_buttons_allowed": True,
        },
        missing_evidence=["amostra_insuficiente"],
        db_path=db_path,
    )
    rejected = register_ml_diagnostic_verdict(
        alert_type=ALERT_003,
        dezena=5,
        ml_proposal={"action": ACTION_AJUSTE_POOL},
        verdict_type=VERDICT_REJECT,
        reconciliation_run_id=97,
        verdict_reason="proposta conflita com Lei 15",
        adm_user="adm@test.local",
        alert_card={
            "tipo_alerta": ALERT_003,
            "ml_proposal": {"action": ACTION_AJUSTE_POOL},
            "ml_diagnosis": {"faixa": "13->14", "taxa_conversao_13_14": 60.0},
            "evidence_level": EVIDENCE_LEVEL_RECURRENT,
            "verdict_buttons_allowed": True,
        },
        db_path=db_path,
    )
    assert accepted["verdict_type"] == VERDICT_ACCEPT_DIAGNOSTIC
    assert accepted["status"] == STATUS_ACEITO
    assert accepted["adr_candidate"] is True
    assert more_evidence["verdict_type"] == VERDICT_REQUEST_MORE_EVIDENCE
    assert more_evidence["status"] == STATUS_PENDENTE_EVIDENCIA
    assert more_evidence["missing_evidence"] == ["amostra_insuficiente"]
    assert rejected["verdict_type"] == VERDICT_REJECT
    assert rejected["status"] == STATUS_REJEITADO
    with get_session(db_path) as session:
        rows = session.query(MlDiagnosticDecision).order_by(MlDiagnosticDecision.id.asc()).all()
    assert len(rows) == 3
    assert rows[0].verdict_type == VERDICT_ACCEPT_DIAGNOSTIC
    assert rows[1].status == STATUS_PENDENTE_EVIDENCIA
    assert rows[2].verdict_reason == "proposta conflita com Lei 15"
    assert all(
        dict(row.ml_proposal or {}).get("verdict_effects", {}).get("operational_effect") is False
        for row in rows
    )


def test_register_ml_diagnostic_decision_legacy_wrapper(tmp_path) -> None:
    db_path = tmp_path / "legacy.db"
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
        alert_card={
            "tipo_alerta": ALERT_001,
            "evidence_level": EVIDENCE_LEVEL_RECURRENT,
            "verdict_buttons_allowed": True,
            "ml_proposal": {
                "action": ACTION_PROMOVER_RESERVA_ADR,
                "target_dezena": "06",
                "drilldown_rows": 1,
            },
            "ml_diagnosis": {"sample_size": 2, "drilldown_available": True},
            "leakage_evidence": evidence,
        },
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
        alert_card={
            "tipo_alerta": ALERT_002,
            "ml_proposal": {"action": ACTION_VIGILANCIA_DEZENA},
            "ml_diagnosis": {"aparicoes": 2, "faixa": "13->14"},
            "evidence_level": EVIDENCE_LEVEL_RECURRENT,
            "verdict_buttons_allowed": True,
        },
        db_path=db_path,
    )
    assert accepted["adm_decision"] == STATUS_ACEITO
    assert accepted["verdict_type"] == VERDICT_ACCEPT_DIAGNOSTIC
    assert rejected["adm_decision"] == STATUS_REJEITADO
    assert rejected["verdict_type"] == VERDICT_REJECT


def test_register_reject_requires_reason(tmp_path) -> None:
    db_path = tmp_path / "reject.db"
    create_database(db_path)
    with pytest.raises(ValueError, match="verdict_reason"):
        register_ml_diagnostic_verdict(
            alert_type=ALERT_003,
            dezena=5,
            ml_proposal={"action": ACTION_AJUSTE_POOL},
            verdict_type=VERDICT_REJECT,
            reconciliation_run_id=1,
            alert_card={
                "tipo_alerta": ALERT_003,
                "ml_proposal": {"action": ACTION_AJUSTE_POOL},
                "ml_diagnosis": {"faixa": "13->14"},
                "evidence_level": EVIDENCE_LEVEL_RECURRENT,
                "verdict_buttons_allowed": True,
            },
            db_path=db_path,
        )


def _seed_many_runs(session, count: int) -> int:
    leak_card = sorted([1, 3, 5, 7, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 6])
    games = [{"numbers": leak_card, "hits": 14}] * 3
    last_run_id = 0
    for suffix in range(1, count + 1):
        last_run_id = _seed_reconciliation_run(session, games=games, run_suffix=suffix)
    return last_run_id


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
        run_id_2 = _seed_many_runs(session, 20)
    assert run_id_2 > 0
    payload = build_central_ml_diagnostics_payload(db_path=db_path)
    assert payload["source"] == "postgresql"
    assert payload["generation_command"] is False
    alert_types = {alert["tipo_alerta"] for alert in payload["alerts"]}
    assert ALERT_001 in alert_types
    sample = payload["alerts"][0]
    assert sample.get("evidencia")
    assert sample.get("regra_base")
    assert sample.get("fonte") == "postgresql"
    assert sample.get("generation_cmd") is False
    assert sample.get("recalibration_cmd") is False
    register_ml_diagnostic_decision(
        alert_type=ALERT_001,
        dezena=6,
        ml_proposal={"action": ACTION_PROMOVER_RESERVA_ADR, "drilldown_rows": 1},
        adm_decision=ADM_ACEITO,
        reconciliation_run_id=run_id_2,
        adm_user="adm@test.local",
        leakage_evidence=_sample_leakage_evidence(),
        alert_card={
            "tipo_alerta": ALERT_001,
            "evidence_level": EVIDENCE_LEVEL_RECURRENT,
            "verdict_buttons_allowed": True,
            "ml_proposal": {"action": ACTION_PROMOVER_RESERVA_ADR, "drilldown_rows": 1},
            "ml_diagnosis": {"sample_size": 2, "drilldown_available": True},
            "leakage_evidence": _sample_leakage_evidence(),
        },
        db_path=db_path,
    )
    payload_after = build_central_ml_diagnostics_payload(db_path=db_path)
    assert payload_after["history"]
    assert payload_after["total_alertas_ativos"] == len(
        [alert for alert in payload_after["alerts"] if alert["status"] in {STATUS_PENDENTE, STATUS_PENDENTE_EVIDENCIA}]
    )


def test_adm_guide_visible_and_suggests_accept_for_complete_alert() -> None:
    leak_card = sorted([1, 3, 5, 7, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 6])
    card = enrich_alert_card_for_display(
        build_alert_001_cards(
            [
                _context_from_games([{"numbers": leak_card, "hits": 14}] * 3, run_id=2),
                _context_from_games([{"numbers": leak_card, "hits": 14}] * 3, run_id=1),
            ]
        )[0]
    )
    guide = card["adm_guide"]
    assert guide["title"] == "Guia ADM"
    assert guide["evidence_status"] == EVIDENCE_STATUS_COMPLETE
    assert guide["governance_status"] == GOVERNANCE_STATUS_SAFE_OBSERVATIONAL
    assert guide["suggested_verdict"] == VERDICT_ACCEPT_DIAGNOSTIC
    assert guide["suggested_verdict_display_only"] is True
    assert guide["adm_can_override"] is True
    assert guide["override_requires_reason"] is True
    assert "sem efeito operacional" in guide["reason_hint"].lower() or "Evidência completa" in guide["reason_hint"]


def test_adm_guide_suggests_request_more_for_insufficient_evidence() -> None:
    card = enrich_alert_card_for_display(
        {
            "tipo_alerta": ALERT_002,
            "ml_proposal": {"action": ACTION_VIGILANCIA_DEZENA},
            "ml_diagnosis": {"aparicoes": 0, "faixa": "13->14"},
            "fonte": "postgresql",
            "generation_command": False,
            "recalibration_command": False,
        }
    )
    guide = build_adm_verdict_guide(card)
    assert guide["evidence_status"] == EVIDENCE_STATUS_INSUFFICIENT
    assert guide["governance_status"] == GOVERNANCE_STATUS_SAFE_OBSERVATIONAL
    assert guide["suggested_verdict"] == VERDICT_REQUEST_MORE_EVIDENCE


def test_adm_guide_suggests_reject_for_invalid_governance() -> None:
    card = enrich_alert_card_for_display(
        {
            "tipo_alerta": ALERT_003,
            "ml_proposal": {
                "action": ACTION_AJUSTE_POOL,
                "operational_effect": True,
            },
            "ml_diagnosis": {"faixa": "13->14", "taxa_conversao_13_14": 80.0},
            "fonte": "postgresql",
            "generation_command": False,
            "recalibration_command": False,
        }
    )
    guide = build_adm_verdict_guide(card)
    assert guide["evidence_status"] == EVIDENCE_STATUS_INVALID
    assert guide["governance_status"] == GOVERNANCE_STATUS_BLOCKED
    assert guide["suggested_verdict"] == VERDICT_REJECT


def test_sample_alert_cards_each_type() -> None:
    leak_card = sorted([1, 3, 5, 7, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 6])
    alert_001 = enrich_alert_card_for_display(
        build_alert_001_cards(
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
    )
    alert_002 = enrich_alert_card_for_display(
        build_alert_002_cards(
            _context_from_games(
                [
                    {"numbers": sorted(NUCLEO), "hits": 13},
                    {"numbers": sorted(NUCLEO), "hits": 14},
                ]
            )
        )[0]
    )
    alert_003 = enrich_alert_card_for_display(
        build_alert_003_cards(
            _context_from_games(
                [
                    {"numbers": sorted(NUCLEO), "hits": 13},
                    {"numbers": sorted(NUCLEO), "hits": 13},
                ]
            )
        )[0]
    )
    assert alert_001["tipo_alerta"] == ALERT_001
    assert alert_002["tipo_alerta"] == ALERT_002
    assert alert_003["tipo_alerta"] == ALERT_003
    assert alert_001["ml_proposal"]["action"] == ACTION_PROMOVER_RESERVA_ADR
    assert alert_002["ml_proposal"]["action"] == ACTION_VIGILANCIA_DEZENA
    assert alert_003["ml_proposal"]["action"] == ACTION_AJUSTE_POOL
    for card in (alert_001, alert_002, alert_003):
        assert card["evidencia"]
        assert card["regra_base"]
        assert card["fonte"] == "postgresql"
        assert card["generation_cmd"] is False
        assert card["recalibration_cmd"] is False
        assert card["adm_guide"]["title"] == "Guia ADM"
        assert card["adm_guide"]["suggested_verdict"] in {
            VERDICT_ACCEPT_DIAGNOSTIC,
            VERDICT_REQUEST_MORE_EVIDENCE,
            VERDICT_REJECT,
        }
