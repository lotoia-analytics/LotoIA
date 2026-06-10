from __future__ import annotations

from datetime import UTC, datetime

import pytest

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
    MIN_GENERATIONS_FOR_CENTRAL,
    VERDICT_ACCEPT_DIAGNOSTIC,
    ACTION_PROMOVER_RESERVA_ADR,
    annotate_alert_routing,
    build_alert_001_cards,
    build_central_ml_diagnostics_payload,
    build_ml_diagnostic_alerts_bundle,
    build_side_leak_panel_payload,
    enrich_alert_card_for_display,
    load_distinct_generation_event_count,
    register_ml_diagnostic_verdict,
)

OFFICIAL_15 = [1, 3, 5, 7, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
LEAK_CARD = sorted([1, 3, 5, 7, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 6])


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


def _leak_games() -> list[dict]:
    return [{"numbers": LEAK_CARD, "hits": 14}] * 3


def _seed_runs(session, count: int, *, generation_event_id: int | None = None) -> None:
    games = _leak_games()
    for suffix in range(1, count + 1):
        if generation_event_id is not None:
            run = ReconciliationRun(
                generation_event_id=generation_event_id,
                contest_id=3700,
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
                        generation_event_id=generation_event_id,
                        contest_id=3700,
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
        else:
            _seed_reconciliation_run(session, games=games, run_suffix=suffix)


def test_alert_1_generation_routes_to_side_leak_not_central(tmp_path) -> None:
    db_path = tmp_path / "route1.db"
    create_database(db_path)
    with get_session(db_path) as session:
        _seed_official_history(session)
        _seed_runs(session, 2, generation_event_id=101)
    bundle = build_ml_diagnostic_alerts_bundle(db_path=db_path)
    central = build_central_ml_diagnostics_payload(db_path=db_path)
    assert load_distinct_generation_event_count(db_path=db_path) == 1
    assert bundle["local_alerts"]
    assert bundle["local_alerts"][0]["evidence_level"] == EVIDENCE_LEVEL_LOCAL
    assert central["alerts"] == []
    assert central["local_alerts_count"] >= 1
    context = bundle["contexts"][0]
    side_leak = build_side_leak_panel_payload(
        context,
        local_alerts=bundle["local_alerts_by_panel"]["side_leak"],
    )
    assert side_leak["local_diagnostics"]
    assert side_leak["local_diagnostics"][0]["tipo_alerta"] == ALERT_001


def test_alert_19_generations_not_in_central(tmp_path) -> None:
    db_path = tmp_path / "route19.db"
    create_database(db_path)
    with get_session(db_path) as session:
        _seed_official_history(session)
        _seed_runs(session, 19)
    central = build_central_ml_diagnostics_payload(db_path=db_path)
    assert load_distinct_generation_event_count(db_path=db_path) == 19
    assert central["alerts"] == []
    assert central["local_alerts_count"] >= 1


def test_alert_20_generations_may_appear_in_central(tmp_path) -> None:
    db_path = tmp_path / "route20.db"
    create_database(db_path)
    with get_session(db_path) as session:
        _seed_official_history(session)
        _seed_runs(session, 20)
    central = build_central_ml_diagnostics_payload(db_path=db_path)
    assert load_distinct_generation_event_count(db_path=db_path) == 20
    assert central["alerts"]
    assert central["alerts"][0]["evidence_level"] == EVIDENCE_LEVEL_RECURRENT
    assert central["alerts"][0]["verdict_buttons_allowed"] is True


def test_local_alert_blocks_verdict_registration(tmp_path) -> None:
    db_path = tmp_path / "block.db"
    create_database(db_path)
    card = enrich_alert_card_for_display(
        annotate_alert_routing(
            build_alert_001_cards(
                [
                    _context_from_games(_leak_games(), run_id=2),
                    _context_from_games(_leak_games(), run_id=1),
                ]
            )[0],
            distinct_generation_events=1,
        )
    )
    with pytest.raises(ValueError, match="20 gerações"):
        register_ml_diagnostic_verdict(
            alert_type=ALERT_001,
            dezena=6,
            ml_proposal={"action": ACTION_PROMOVER_RESERVA_ADR, "drilldown_rows": 1},
            verdict_type=VERDICT_ACCEPT_DIAGNOSTIC,
            reconciliation_run_id=2,
            alert_card=card,
            db_path=db_path,
        )


def test_local_alert_never_sets_adr_candidate() -> None:
    card = annotate_alert_routing(
        {"tipo_alerta": ALERT_001, "ml_proposal": {"action": ACTION_PROMOVER_RESERVA_ADR}},
        distinct_generation_events=5,
    )
    assert card["adr_candidate"] is False
    assert card["verdict_buttons_allowed"] is False
    assert card["min_required_generations"] == MIN_GENERATIONS_FOR_CENTRAL
