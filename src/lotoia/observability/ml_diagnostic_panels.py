"""Painéis ML diagnósticos observacionais (PostgreSQL / reconciliation_runs)."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any, Sequence

from lotoia.database.database import (
    DEFAULT_DATABASE_PATH,
    LotofacilOfficialHistory,
    MlDiagnosticDecision,
    ReconciliationGame,
    ReconciliationRun,
    get_session,
)
from lotoia.observability.observational_leftover import ML_ROLE_DIAGNOSTIC_ONLY

NUCLEO_LEI15_15D_CONGELADO: frozenset[int] = frozenset(
    {1, 2, 3, 4, 9, 10, 11, 12, 13, 18, 20, 22, 23, 24, 25}
)
BLIND_SPOTS: frozenset[int] = frozenset({6, 16, 17, 21})
SIDE_LEAK_ALERT_THRESHOLD = 0.50
CONVERSION_ALERT_THRESHOLD = 0.50
MIN_CONSECUTIVE_RUNS_ALERT_001 = 2
SOURCE_POSTGRESQL = "postgresql"
RECONCILIATION_TABLES = "reconciliation_runs / reconciliation_games"
CANDIDATE_FLAG_13_14 = "candidata_conversao_13_14"
CANDIDATE_FLAG_14_15 = "candidata_conversao_14_15"
ALERT_SIDE_LEAK = "vazamento_lateral_detectado"

ALERT_001 = "ALERT_001"
ALERT_002 = "ALERT_002"
ALERT_003 = "ALERT_003"
ALERT_001_LABEL = "vazamento_lateral_recorrente"
ALERT_002_LABEL = "blind_spot_em_evolucao"
ALERT_003_LABEL = "candidata_conversao"

ADM_ACEITO = "ACEITO"
ADM_REJEITADO = "REJEITADO"
STATUS_PENDENTE = "PENDENTE"
STATUS_ACEITO = "ACEITO"
STATUS_REJEITADO = "REJEITADO"

ACTION_PROMOVER_RESERVA_ADR = "propor_promocao_reserva_via_ADR"
ACTION_VIGILANCIA_DEZENA = "propor_vigilancia_dezena"
ACTION_AJUSTE_POOL = "propor_ajuste_pool_candidatos"


def _parse_dezenas(values: Sequence[int | str] | str | None) -> list[int]:
    if not values:
        return []
    if isinstance(values, str):
        raw_items = values.replace(",", " ").replace(";", " ").split()
    else:
        raw_items = list(values)
    numbers: list[int] = []
    for item in raw_items:
        try:
            number = int(str(item).strip().lstrip("+"))
        except (TypeError, ValueError):
            continue
        if 1 <= number <= 25:
            numbers.append(number)
    return sorted(set(numbers))


def _load_official_numbers(session: Any, contest_id: int) -> list[int]:
    if contest_id <= 0:
        return []
    row = (
        session.query(LotofacilOfficialHistory)
        .filter(LotofacilOfficialHistory.contest_number == int(contest_id))
        .limit(1)
        .one_or_none()
    )
    if row is None:
        return []
    numbers = _parse_dezenas(getattr(row, "numbers", "") or "")
    return numbers if len(numbers) == 15 else []


def _empty_context() -> dict[str, Any]:
    return {
        "available": False,
        "source": SOURCE_POSTGRESQL,
        "tables": RECONCILIATION_TABLES,
        "reconciliation_run_id": 0,
        "contest_id": 0,
        "resultado_oficial": [],
        "games": [],
        "ml_role": ML_ROLE_DIAGNOSTIC_ONLY,
        "generation_command": False,
        "recalibration_command": False,
    }


def _serialize_game_row(row: ReconciliationGame) -> dict[str, Any]:
    return {
        "game_index": int(row.game_index or 0),
        "numbers": [int(number) for number in (row.numbers or [])],
        "hits": int(row.hits or 0),
        "matched_numbers": [int(number) for number in (row.matched_numbers or [])],
        "contest_id": int(row.contest_id or 0),
    }


def load_latest_reconciliation_diagnostic_context(
    db_path: str = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    """Carrega última reconciliation_run e jogos do PostgreSQL (Lei 001)."""
    with get_session(db_path) as session:
        run = (
            session.query(ReconciliationRun)
            .order_by(ReconciliationRun.created_at.desc(), ReconciliationRun.id.desc())
            .first()
        )
        if run is None:
            return _empty_context()
        contest_id = int(getattr(run, "contest_id", 0) or 0)
        games_rows = (
            session.query(ReconciliationGame)
            .filter(ReconciliationGame.reconciliation_run_id == run.id)
            .order_by(ReconciliationGame.game_index.asc())
            .all()
        )
        resultado_oficial = _load_official_numbers(session, contest_id)
        games = [_serialize_game_row(row) for row in games_rows]
        return {
            "available": bool(games and resultado_oficial),
            "source": SOURCE_POSTGRESQL,
            "tables": RECONCILIATION_TABLES,
            "reconciliation_run_id": int(run.id or 0),
            "contest_id": contest_id,
            "resultado_oficial": resultado_oficial,
            "games": games,
            "ml_role": ML_ROLE_DIAGNOSTIC_ONLY,
            "generation_command": False,
            "recalibration_command": False,
        }


def load_recent_reconciliation_runs_context(
    *,
    limit: int = 5,
    db_path: str = DEFAULT_DATABASE_PATH,
) -> list[dict[str, Any]]:
    """Carrega reconciliation_runs recentes com jogos e resultado oficial."""
    contexts: list[dict[str, Any]] = []
    with get_session(db_path) as session:
        runs = (
            session.query(ReconciliationRun)
            .order_by(ReconciliationRun.created_at.desc(), ReconciliationRun.id.desc())
            .limit(max(1, int(limit)))
            .all()
        )
        for run in runs:
            contest_id = int(getattr(run, "contest_id", 0) or 0)
            games_rows = (
                session.query(ReconciliationGame)
                .filter(ReconciliationGame.reconciliation_run_id == run.id)
                .order_by(ReconciliationGame.game_index.asc())
                .all()
            )
            resultado_oficial = _load_official_numbers(session, contest_id)
            games = [_serialize_game_row(row) for row in games_rows]
            contexts.append(
                {
                    "available": bool(games and resultado_oficial),
                    "source": SOURCE_POSTGRESQL,
                    "tables": RECONCILIATION_TABLES,
                    "reconciliation_run_id": int(run.id or 0),
                    "contest_id": contest_id,
                    "resultado_oficial": resultado_oficial,
                    "games": games,
                    "ml_role": ML_ROLE_DIAGNOSTIC_ONLY,
                    "generation_command": False,
                    "recalibration_command": False,
                }
            )
    return contexts


def _side_leak_dezenas_for_context(context: dict[str, Any]) -> dict[int, float]:
    games = list(context.get("games") or [])
    nucleo = set(NUCLEO_LEI15_15D_CONGELADO)
    total_games = len(games)
    if not total_games:
        return {}
    dezena_game_counts: Counter[int] = Counter()
    for game in games:
        cartao = set(int(number) for number in (game.get("numbers") or []))
        for dezena in sorted(cartao - nucleo):
            dezena_game_counts[dezena] += 1
    return {
        dezena: round((count / total_games) * 100.0, 2)
        for dezena, count in dezena_game_counts.items()
        if (count / total_games) > SIDE_LEAK_ALERT_THRESHOLD
    }


def _missing_dezena_stats(
    context: dict[str, Any],
    *,
    target_hits: int,
) -> dict[int, dict[str, Any]]:
    games = [game for game in (context.get("games") or []) if int(game.get("hits", 0) or 0) == target_hits]
    resultado_oficial = set(int(number) for number in (context.get("resultado_oficial") or []))
    dezena_counts: Counter[int] = Counter()
    for game in games:
        cartao = set(int(number) for number in (game.get("numbers") or []))
        for dezena in sorted(resultado_oficial - cartao):
            dezena_counts[dezena] += 1
    total_games = len(games)
    stats: dict[int, dict[str, Any]] = {}
    for dezena, frequencia in dezena_counts.items():
        percentual = round((frequencia / total_games) * 100.0, 2) if total_games else 0.0
        stats[dezena] = {
            "frequencia": int(frequencia),
            "percentual": percentual,
            "games_analyzed": total_games,
            "target_hits": target_hits,
        }
    return stats


def _alert_key(alert_type: str, dezena: int, reconciliation_run_id: int) -> str:
    return f"{alert_type}:{dezena:02d}:{reconciliation_run_id}"


def _base_alert_card(
    *,
    alert_type: str,
    tipo_label: str,
    dezena: int,
    ml_diagnosis: dict[str, Any],
    ml_proposal: dict[str, Any],
    reconciliation_run_id: int,
    status: str = STATUS_PENDENTE,
    decision_id: int | None = None,
) -> dict[str, Any]:
    return {
        "alert_key": _alert_key(alert_type, dezena, reconciliation_run_id),
        "tipo_alerta": alert_type,
        "tipo_label": tipo_label,
        "dezena": dezena,
        "dezena_fmt": f"{dezena:02d}",
        "status": status,
        "ml_diagnosis": ml_diagnosis,
        "ml_proposal": ml_proposal,
        "reconciliation_run_id": reconciliation_run_id,
        "decision_id": decision_id,
        "ml_role": ML_ROLE_DIAGNOSTIC_ONLY,
        "generation_command": False,
        "recalibration_command": False,
    }


def build_alert_001_cards(contexts: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(contexts) < MIN_CONSECUTIVE_RUNS_ALERT_001:
        return []
    ordered = list(contexts)
    latest = ordered[0]
    run_id = int(latest.get("reconciliation_run_id", 0) or 0)
    streak_by_dezena: dict[int, int] = {}
    percent_by_dezena: dict[int, float] = {}
    for context in ordered:
        leak_map = _side_leak_dezenas_for_context(context)
        for dezena in list(streak_by_dezena.keys()):
            if dezena not in leak_map:
                streak_by_dezena[dezena] = 0
        for dezena, percentual in leak_map.items():
            streak_by_dezena[dezena] = streak_by_dezena.get(dezena, 0) + 1
            if context is latest:
                percent_by_dezena[dezena] = percentual
    cards: list[dict[str, Any]] = []
    for dezena, consecutivas in sorted(streak_by_dezena.items()):
        if consecutivas < MIN_CONSECUTIVE_RUNS_ALERT_001:
            continue
        frequencia = percent_by_dezena.get(dezena, 0.0)
        ml_diagnosis = {
            "dezena": f"{dezena:02d}",
            "frequencia": frequencia,
            "consecutivas": consecutivas,
        }
        ml_proposal = {
            "action": ACTION_PROMOVER_RESERVA_ADR,
            "target_dezena": f"{dezena:02d}",
            "justificativa": (
                f"Dezena {dezena:02d} fora do núcleo Lei 15 15D com "
                f"{frequencia}% de vazamento em {consecutivas} runs consecutivas."
            ),
        }
        cards.append(
            _base_alert_card(
                alert_type=ALERT_001,
                tipo_label=ALERT_001_LABEL,
                dezena=dezena,
                ml_diagnosis=ml_diagnosis,
                ml_proposal=ml_proposal,
                reconciliation_run_id=run_id,
            )
        )
    return cards


def build_alert_002_cards(context: dict[str, Any]) -> list[dict[str, Any]]:
    if not context.get("available"):
        return []
    run_id = int(context.get("reconciliation_run_id", 0) or 0)
    cards: list[dict[str, Any]] = []
    seen: set[int] = set()
    for target_hits, faixa in ((13, "13->14"), (14, "14->15")):
        stats = _missing_dezena_stats(context, target_hits=target_hits)
        for dezena, payload in stats.items():
            if dezena not in BLIND_SPOTS or dezena in seen:
                continue
            seen.add(dezena)
            ml_diagnosis = {
                "dezena": f"{dezena:02d}",
                "tipo": "blind_spot_confirmado",
                "aparicoes": payload["frequencia"],
                "faixa": faixa,
            }
            ml_proposal = {
                "action": ACTION_VIGILANCIA_DEZENA,
                "target_dezena": f"{dezena:02d}",
                "justificativa": (
                    f"Blind spot {dezena:02d} confirmado como dezena_faltante "
                    f"em {payload['frequencia']} jogos com {target_hits} acertos ({faixa})."
                ),
            }
            cards.append(
                _base_alert_card(
                    alert_type=ALERT_002,
                    tipo_label=ALERT_002_LABEL,
                    dezena=dezena,
                    ml_diagnosis=ml_diagnosis,
                    ml_proposal=ml_proposal,
                    reconciliation_run_id=run_id,
                )
            )
    return cards


def build_alert_003_cards(context: dict[str, Any]) -> list[dict[str, Any]]:
    if not context.get("available"):
        return []
    run_id = int(context.get("reconciliation_run_id", 0) or 0)
    stats_13 = _missing_dezena_stats(context, target_hits=13)
    stats_14 = _missing_dezena_stats(context, target_hits=14)
    all_dezenas = set(stats_13) | set(stats_14)
    cards: list[dict[str, Any]] = []
    for dezena in sorted(all_dezenas):
        taxa_13 = stats_13.get(dezena, {}).get("percentual", 0.0)
        taxa_14 = stats_14.get(dezena, {}).get("percentual", 0.0)
        best_taxa = max(taxa_13, taxa_14)
        if best_taxa <= (CONVERSION_ALERT_THRESHOLD * 100.0):
            continue
        faixa = "14->15" if taxa_14 >= taxa_13 else "13->14"
        ml_diagnosis = {
            "dezena": f"{dezena:02d}",
            "taxa_conversao_13_14": taxa_13,
            "taxa_conversao_14_15": taxa_14,
            "faixa": faixa,
        }
        ml_proposal = {
            "action": ACTION_AJUSTE_POOL,
            "target_dezena": f"{dezena:02d}",
            "formato_sugerido": "16D..20D (expansion layer)",
            "justificativa": (
                f"Dezena {dezena:02d} aparece como faltante em {best_taxa}% dos jogos "
                f"na faixa {faixa}."
            ),
            "constraint": "nucleo_lei15_15D permanece soberano",
        }
        cards.append(
            _base_alert_card(
                alert_type=ALERT_003,
                tipo_label=ALERT_003_LABEL,
                dezena=dezena,
                ml_diagnosis=ml_diagnosis,
                ml_proposal=ml_proposal,
                reconciliation_run_id=run_id,
            )
        )
    return cards


def build_central_ml_diagnostics_payload(
    db_path: str = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    """Monta payload da Central de Diagnósticos ML com os 3 tipos de alerta."""
    contexts = load_recent_reconciliation_runs_context(limit=5, db_path=db_path)
    latest = contexts[0] if contexts else _empty_context()
    alerts = (
        build_alert_001_cards(contexts)
        + build_alert_002_cards(latest)
        + build_alert_003_cards(latest)
    )
    decisions = list_ml_diagnostic_decisions(db_path=db_path, limit=500)
    decision_index = {
        (row["alert_type"], row["dezena"], row["reconciliation_run_id"]): row
        for row in decisions
    }
    active_alerts: list[dict[str, Any]] = []
    for alert in alerts:
        key = (alert["tipo_alerta"], alert["dezena"], alert["reconciliation_run_id"])
        existing = decision_index.get(key)
        if existing:
            alert = dict(alert)
            alert["status"] = existing["adm_decision"]
            alert["decision_id"] = existing["id"]
            alert["adm_reason"] = existing.get("adm_reason")
            alert["adm_user"] = existing.get("adm_user")
            alert["decided_at"] = existing.get("decided_at")
        active_alerts.append(alert)
    pending = [alert for alert in active_alerts if alert["status"] == STATUS_PENDENTE]
    updated_at = datetime.now(UTC).isoformat()
    return {
        "available": bool(contexts),
        "source": SOURCE_POSTGRESQL,
        "tables": RECONCILIATION_TABLES,
        "reconciliation_run_id": int(latest.get("reconciliation_run_id", 0) or 0),
        "ml_role": ML_ROLE_DIAGNOSTIC_ONLY,
        "generation_command": False,
        "recalibration_command": False,
        "total_alertas_ativos": len(pending),
        "ultima_atualizacao": updated_at,
        "alerts": active_alerts,
        "history": decisions,
    }


def list_ml_diagnostic_decisions(
    *,
    db_path: str = DEFAULT_DATABASE_PATH,
    limit: int = 200,
) -> list[dict[str, Any]]:
    with get_session(db_path) as session:
        rows = (
            session.query(MlDiagnosticDecision)
            .order_by(
                MlDiagnosticDecision.decided_at.desc().nullslast(),
                MlDiagnosticDecision.created_at.desc(),
                MlDiagnosticDecision.id.desc(),
            )
            .limit(max(1, int(limit)))
            .all()
        )
        return [_serialize_decision_row(row) for row in rows]


def _serialize_decision_row(row: MlDiagnosticDecision) -> dict[str, Any]:
    decided_at = row.decided_at
    return {
        "id": int(row.id or 0),
        "alert_type": row.alert_type,
        "dezena": int(row.dezena or 0),
        "dezena_fmt": f"{int(row.dezena or 0):02d}",
        "ml_proposal": dict(row.ml_proposal or {}),
        "adm_decision": row.adm_decision,
        "decision": row.adm_decision,
        "adm_reason": row.adm_reason,
        "reason": row.adm_reason or "",
        "adm_user": row.adm_user,
        "reconciliation_run_id": int(row.reconciliation_run_id or 0),
        "created_at": row.created_at.isoformat() if row.created_at else "",
        "decided_at": decided_at.isoformat() if decided_at else "",
        "timestamp": decided_at.isoformat() if decided_at else (row.created_at.isoformat() if row.created_at else ""),
    }


def _build_acceptance_effects(alert_type: str, ml_proposal: dict[str, Any]) -> dict[str, Any]:
    if alert_type == ALERT_001:
        return {
            "effect": "adr_draft_registered",
            "action": ACTION_PROMOVER_RESERVA_ADR,
            "target_dezena": ml_proposal.get("target_dezena"),
            "executed": False,
            "note": "Rascunho ADR registrado; execução aguarda fluxo institucional.",
        }
    if alert_type == ALERT_002:
        return {
            "effect": "vigilancia_layer_updated",
            "action": ACTION_VIGILANCIA_DEZENA,
            "target_dezena": ml_proposal.get("target_dezena"),
            "executed": False,
            "note": "Dezena adicionada à camada de vigilância observacional.",
        }
    return {
        "effect": "candidate_pool_registered",
        "action": ACTION_AJUSTE_POOL,
        "target_dezena": ml_proposal.get("target_dezena"),
        "formato_sugerido": ml_proposal.get("formato_sugerido"),
        "executed": False,
        "note": "Candidata registrada para pool de geração futura; núcleo Lei 15 permanece soberano.",
    }


def register_ml_diagnostic_decision(
    *,
    alert_type: str,
    dezena: int,
    ml_proposal: dict[str, Any],
    adm_decision: str,
    reconciliation_run_id: int,
    adm_reason: str = "",
    adm_user: str = "",
    db_path: str = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    """Persiste decisão ADM (aceita ou rejeitada). ML nunca executa sem ACEITO."""
    normalized_decision = str(adm_decision or "").strip().upper()
    if normalized_decision not in {ADM_ACEITO, ADM_REJEITADO}:
        raise ValueError("adm_decision deve ser ACEITO ou REJEITADO")
    proposal = dict(ml_proposal or {})
    if normalized_decision == ADM_REJEITADO and not str(adm_reason or "").strip():
        raise ValueError("adm_reason é obrigatório para decisão REJEITADO")
    now = datetime.now(UTC)
    with get_session(db_path) as session:
        existing = (
            session.query(MlDiagnosticDecision)
            .filter(
                MlDiagnosticDecision.alert_type == alert_type,
                MlDiagnosticDecision.dezena == int(dezena),
                MlDiagnosticDecision.reconciliation_run_id == int(reconciliation_run_id),
            )
            .order_by(MlDiagnosticDecision.id.desc())
            .first()
        )
        if existing is not None:
            return _serialize_decision_row(existing)
        payload = dict(proposal)
        if normalized_decision == ADM_ACEITO:
            payload["acceptance_effects"] = _build_acceptance_effects(alert_type, proposal)
        else:
            payload["archived"] = True
        row = MlDiagnosticDecision(
            alert_type=alert_type,
            dezena=int(dezena),
            ml_proposal=payload,
            adm_decision=normalized_decision,
            adm_reason=str(adm_reason or "").strip() or None,
            adm_user=str(adm_user or "").strip(),
            reconciliation_run_id=int(reconciliation_run_id),
            created_at=now,
            decided_at=now,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return _serialize_decision_row(row)


def build_side_leak_panel_payload(context: dict[str, Any]) -> dict[str, Any]:
    games = list(context.get("games") or [])
    nucleo = set(NUCLEO_LEI15_15D_CONGELADO)
    total_games = len(games)
    dezena_game_counts: Counter[int] = Counter()
    for game in games:
        cartao = set(int(number) for number in (game.get("numbers") or []))
        for dezena in sorted(cartao - nucleo):
            dezena_game_counts[dezena] += 1
    rows: list[dict[str, Any]] = []
    alert_dezenas: list[int] = []
    for dezena, frequencia in sorted(dezena_game_counts.items()):
        percentual = round((frequencia / total_games) * 100.0, 2) if total_games else 0.0
        rows.append(
            {
                "dezena": f"{dezena:02d}",
                "frequencia_vazamento": int(frequencia),
                "percentual_vazamento": percentual,
            }
        )
        if total_games and (frequencia / total_games) > SIDE_LEAK_ALERT_THRESHOLD:
            alert_dezenas.append(int(dezena))
    return {
        "available": bool(context.get("available")),
        "source": SOURCE_POSTGRESQL,
        "tables": RECONCILIATION_TABLES,
        "reconciliation_run_id": int(context.get("reconciliation_run_id", 0) or 0),
        "ml_role": ML_ROLE_DIAGNOSTIC_ONLY,
        "generation_command": False,
        "recalibration_command": False,
        "rows": rows,
        "total_games": total_games,
        "alert": ALERT_SIDE_LEAK if alert_dezenas else None,
        "alert_dezenas": [f"{dezena:02d}" for dezena in alert_dezenas],
        "nucleo_lei15_15d": sorted(nucleo),
    }


def _build_evolution_panel_payload(
    context: dict[str, Any],
    *,
    target_hits: int,
    candidate_flag: str,
) -> dict[str, Any]:
    games = [game for game in (context.get("games") or []) if int(game.get("hits", 0) or 0) == target_hits]
    resultado_oficial = set(int(number) for number in (context.get("resultado_oficial") or []))
    dezena_counts: Counter[int] = Counter()
    for game in games:
        cartao = set(int(number) for number in (game.get("numbers") or []))
        for dezena in sorted(resultado_oficial - cartao):
            dezena_counts[dezena] += 1
    total_games = len(games)
    rows: list[dict[str, Any]] = []
    for dezena, frequencia in dezena_counts.most_common():
        percentual = round((frequencia / total_games) * 100.0, 2) if total_games else 0.0
        rows.append(
            {
                "dezena_faltante": f"{dezena:02d}",
                "frequencia": int(frequencia),
                "percentual": percentual,
            }
        )
    top_row = rows[0] if rows else None
    return {
        "available": bool(context.get("available") and total_games > 0),
        "source": SOURCE_POSTGRESQL,
        "tables": RECONCILIATION_TABLES,
        "reconciliation_run_id": int(context.get("reconciliation_run_id", 0) or 0),
        "ml_role": ML_ROLE_DIAGNOSTIC_ONLY,
        "generation_command": False,
        "recalibration_command": False,
        "target_hits": target_hits,
        "games_analyzed": total_games,
        "rows": rows,
        "candidate_flag": candidate_flag if top_row else None,
        "candidata_conversao": top_row["dezena_faltante"] if top_row else None,
    }


def build_evolution_13_14_panel_payload(context: dict[str, Any]) -> dict[str, Any]:
    return _build_evolution_panel_payload(
        context,
        target_hits=13,
        candidate_flag=CANDIDATE_FLAG_13_14,
    )


def build_evolution_14_15_panel_payload(context: dict[str, Any]) -> dict[str, Any]:
    return _build_evolution_panel_payload(
        context,
        target_hits=14,
        candidate_flag=CANDIDATE_FLAG_14_15,
    )
