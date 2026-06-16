from __future__ import annotations

from datetime import UTC, datetime

from lotoia.database.database import (
    LotofacilOfficialHistory,
    ReconciliationGame,
    ReconciliationRun,
    create_database,
    get_session,
)
from lotoia.observability.ml_diagnostic_panels import (
    ALERT_001,
    EVIDENCE_LEVEL_LOCAL,
    EVIDENCE_LEVEL_RECURRENT,
    annotate_alert_routing,
    build_alert_001_cards,
    build_alert_evidence_base,
    build_central_ml_diagnostics_payload,
    build_ml_diagnostic_alerts_bundle,
    build_panel_evidence_base,
    build_side_leak_panel_payload,
    enrich_alert_card_for_display,
    load_recent_reconciliation_runs_context,
)

OFFICIAL_15 = [1, 3, 5, 7, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
LEAK_CARD = sorted([1, 3, 5, 7, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 6])


def _seed_official_history(session, contest_id: int = 3704) -> None:
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
    contest_id: int,
    games: list[dict],
    run_suffix: int,
) -> int:
    run = ReconciliationRun(
        generation_event_id=490 + run_suffix,
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
                generation_event_id=490 + run_suffix,
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


def _leak_games() -> list[dict]:
    return [
        {"numbers": LEAK_CARD, "hits": 14},
        {"numbers": LEAK_CARD, "hits": 14},
    ]


def test_alert_evidence_base_includes_exact_contest_and_generation_ids(tmp_path) -> None:
    db_path = tmp_path / "evidence.db"
    create_database(db_path)
    with get_session(db_path) as session:
        _seed_official_history(session, contest_id=3704)
        _seed_official_history(session, contest_id=3705)
        _seed_reconciliation_run(
            session,
            contest_id=3705,
            games=_leak_games(),
            run_suffix=1,
        )
        _seed_reconciliation_run(
            session,
            contest_id=3704,
            games=_leak_games(),
            run_suffix=2,
        )

    contexts = load_recent_reconciliation_runs_context(limit=5, db_path=db_path)
    cards = build_alert_001_cards(contexts)
    assert cards
    enriched = enrich_alert_card_for_display(
        annotate_alert_routing(cards[0], distinct_generation_events=2)
    )
    evidence_base = dict(enriched["evidence_base"])
    assert evidence_base["concursos_analisados"] == [3704, 3705]
    assert evidence_base["generation_event_ids"] == [491, 492]
    assert len(evidence_base["reconciliation_run_ids"]) == 2
    assert evidence_base["evidence_level"] == EVIDENCE_LEVEL_LOCAL
    assert "base_nao_identificavel" not in enriched["evidence_gaps"]


def test_central_payload_alerts_expose_evidence_base(tmp_path) -> None:
    db_path = tmp_path / "central.db"
    create_database(db_path)
    with get_session(db_path) as session:
        for index, contest in enumerate(range(3704, 3724)):
            _seed_official_history(session, contest_id=contest)
            _seed_reconciliation_run(
                session,
                contest_id=contest,
                games=_leak_games(),
                run_suffix=index + 1,
            )

    payload = build_central_ml_diagnostics_payload(db_path=db_path)
    assert payload["alerts"]
    alert = payload["alerts"][0]
    evidence_base = dict(alert["evidence_base"])
    assert evidence_base["concursos_analisados"]
    assert evidence_base["generation_event_ids"]
    assert evidence_base["reconciliation_run_ids"]
    assert evidence_base["evidence_level"] == EVIDENCE_LEVEL_RECURRENT


def test_side_leak_panel_exposes_evidence_base(tmp_path) -> None:
    db_path = tmp_path / "side_leak.db"
    create_database(db_path)
    with get_session(db_path) as session:
        _seed_official_history(session, contest_id=3706)
        run_id = _seed_reconciliation_run(
            session,
            contest_id=3706,
            games=_leak_games(),
            run_suffix=3,
        )

    contexts = load_recent_reconciliation_runs_context(limit=1, db_path=db_path)
    bundle = build_ml_diagnostic_alerts_bundle(db_path=db_path)
    panel = build_side_leak_panel_payload(
        contexts[0],
        local_alerts=bundle["local_alerts_by_panel"]["side_leak"],
    )
    evidence_base = dict(panel["evidence_base"])
    assert evidence_base["concursos_analisados"] == [3706]
    assert evidence_base["generation_event_ids"] == [493]
    assert evidence_base["reconciliation_run_ids"] == [run_id]
    assert evidence_base["total_geracoes"] == 1
    assert evidence_base["total_concursos"] == 1
    assert evidence_base["total_runs"] == 1


def test_build_alert_evidence_base_marks_unidentifiable_without_ids() -> None:
    alert = {
        "tipo_alerta": ALERT_001,
        "reconciliation_run_id": 0,
        "evidence_level": EVIDENCE_LEVEL_LOCAL,
    }
    evidence_base = build_alert_evidence_base(alert)
    assert evidence_base["concursos_analisados"] == []
    assert evidence_base["generation_event_ids"] == []
    assert evidence_base["reconciliation_run_ids"] == []


def test_build_panel_evidence_base_uses_context_and_local_alerts() -> None:
    context = {
        "available": True,
        "reconciliation_run_id": 10,
        "contest_id": 3704,
        "generation_event_id": 492,
        "resultado_oficial": OFFICIAL_15,
        "games": [
            {
                "game_index": 1,
                "numbers": LEAK_CARD,
                "hits": 14,
                "generation_event_id": 492,
                "contest_id": 3704,
            }
        ],
    }
    local_alert = {
        "evidence_level": EVIDENCE_LEVEL_LOCAL,
        "evidence_contexts": [context],
    }
    evidence_base = build_panel_evidence_base(context, local_alerts=[local_alert])
    assert evidence_base["concursos_analisados"] == [3704]
    assert evidence_base["generation_event_ids"] == [492]
    assert evidence_base["reconciliation_run_ids"] == [10]
    assert evidence_base["evidence_level"] == EVIDENCE_LEVEL_LOCAL
