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
from lotoia.analytics.lotofacil_scientific_core import validation_threshold_by_game_size
from lotoia.observability.observational_leftover import (
    ML_ROLE_DIAGNOSTIC_ONLY,
    compute_dezenas_sobrando,
    format_dezenas,
)

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
VERDICT_ACCEPT_DIAGNOSTIC = "ACCEPT_DIAGNOSTIC"
VERDICT_REQUEST_MORE_EVIDENCE = "REQUEST_MORE_EVIDENCE"
VERDICT_REJECT = "REJECT"
VERDICT_OPTIONS = (
    VERDICT_ACCEPT_DIAGNOSTIC,
    VERDICT_REQUEST_MORE_EVIDENCE,
    VERDICT_REJECT,
)
STATUS_PENDENTE = "PENDENTE"
STATUS_PENDENTE_EVIDENCIA = "PENDENTE_EVIDENCIA"
STATUS_ACEITO = "ACEITO"
STATUS_REJEITADO = "REJEITADO"
ACTIVE_ALERT_STATUSES = frozenset({STATUS_PENDENTE, STATUS_PENDENTE_EVIDENCIA})
VERDICT_STATUS_BY_TYPE = {
    VERDICT_ACCEPT_DIAGNOSTIC: STATUS_ACEITO,
    VERDICT_REQUEST_MORE_EVIDENCE: STATUS_PENDENTE_EVIDENCIA,
    VERDICT_REJECT: STATUS_REJEITADO,
}
EVIDENCE_STATUS_COMPLETE = "COMPLETE"
EVIDENCE_STATUS_INSUFFICIENT = "INSUFFICIENT"
EVIDENCE_STATUS_INVALID = "INVALID"
GOVERNANCE_STATUS_SAFE_OBSERVATIONAL = "SAFE_OBSERVATIONAL"
GOVERNANCE_STATUS_BLOCKED = "BLOCKED"
INSUFFICIENT_EVIDENCE_MARKERS = frozenset(
    {
        "amostra_insuficiente",
        "poucas_geracoes",
        "drilldown_incompleto",
        "falta_cartao_final_ou_resultado_oficial",
    }
)
INVALID_EVIDENCE_MARKERS = frozenset(
    {
        "regra_nao_identificada",
        "fonte_nao_auditavel",
        "conflito_com_Lei_15_ou_Lei_15A",
        "proposta_tenta_efeito_operacional",
    }
)
VERDICT_REASON_HINTS = {
    VERDICT_ACCEPT_DIAGNOSTIC: "Evidência completa e sem efeito operacional.",
    VERDICT_REQUEST_MORE_EVIDENCE: "Falta amostra, gerações, concursos ou drilldown suficiente.",
    VERDICT_REJECT: "Conflito de governança, fonte inválida ou tentativa operacional.",
}
MIN_GENERATIONS_FOR_CENTRAL = 20
EVIDENCE_LEVEL_LOCAL = "LOCAL_DIAGNOSTIC"
EVIDENCE_LEVEL_RECURRENT = "RECURRENT_DIAGNOSTIC"
LOCAL_DIAGNOSTIC_LABEL = "Diagnóstico local — não elegível para veredito ADM"
CENTRAL_EMPTY_NO_RECURRENT_MESSAGE = (
    "Nenhum alerta recorrente elegível. Alertas locais permanecem nos painéis analíticos."
)

ACTION_PROMOVER_RESERVA_ADR = "propor_promocao_reserva_via_ADR"
ACTION_VIGILANCIA_DEZENA = "propor_vigilancia_dezena"
ACTION_AJUSTE_POOL = "propor_ajuste_pool_candidatos"


def get_evolution_target_hits(game_size: int = 15) -> list[int]:
    """Hit bands for evolution diagnostics: two steps below max, anchored at schema base."""
    base = validation_threshold_by_game_size.get(game_size, 11)
    offset_low = game_size - base - 2
    offset_high = game_size - base - 1
    return [base + offset_low, base + offset_high]


def _evolution_faixa_label(lower_target: int) -> str:
    return f"{lower_target}->{lower_target + 1}"


def _infer_game_size_from_context(context: dict[str, Any], *, default: int = 15) -> int:
    for game in context.get("games") or []:
        numbers = game.get("numbers") or []
        if numbers:
            return len(numbers)
    return default


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
        "generation_event_id": int(row.generation_event_id or 0),
    }


def _resolve_diagnostic_game_hits(
    game: dict[str, Any],
    resultado_oficial: Sequence[int],
) -> int:
    hits = int(game.get("hits") or 0)
    if hits > 0:
        return hits
    matched = [int(number) for number in (game.get("matched_numbers") or [])]
    if matched:
        return len(matched)
    cartao = [int(number) for number in (game.get("numbers") or [])]
    official = [int(number) for number in resultado_oficial]
    if cartao and official:
        return len(set(cartao) & set(official))
    return 0


def build_lateral_leakage_evidence(context: dict[str, Any]) -> dict[str, Any]:
    """Evidência auditável de vazamento lateral: cartao_final − resultado_oficial."""
    games = list(context.get("games") or [])
    resultado_oficial = [int(number) for number in (context.get("resultado_oficial") or [])]
    reconciliation_run_id = int(context.get("reconciliation_run_id", 0) or 0)
    contest_id = int(context.get("contest_id", 0) or 0)
    default_generation_event_id = int(context.get("generation_event_id", 0) or 0)
    sample_size = len(games)
    dezena_game_counts: Counter[int] = Counter()
    drilldown_per_dezena: dict[str, list[dict[str, Any]]] = {}

    for game in games:
        cartao = [int(number) for number in (game.get("numbers") or [])]
        sobra_real = compute_dezenas_sobrando(cartao, resultado_oficial)
        hits = _resolve_diagnostic_game_hits(game, resultado_oficial)
        jogo_id = int(game.get("game_index", 0) or 0)
        generation_event_id = int(game.get("generation_event_id", 0) or default_generation_event_id)
        resultado_fmt = format_dezenas(resultado_oficial)
        cartao_fmt = format_dezenas(cartao)
        sobra_fmt = format_dezenas(sobra_real)
        for dezena in sobra_real:
            dezena_game_counts[dezena] += 1
            drilldown_row = {
                "dezena": f"{dezena:02d}",
                "jogo_id": jogo_id,
                "generation_event_id": generation_event_id,
                "reconciliation_run_id": reconciliation_run_id,
                "concurso_analisado": contest_id,
                "cartao_final": cartao_fmt,
                "resultado_oficial": resultado_fmt,
                "hits": hits,
                "sobra_real": sobra_fmt,
                "vazou": True,
            }
            drilldown_per_dezena.setdefault(f"{dezena:02d}", []).append(drilldown_row)

    leakage_table: list[dict[str, Any]] = []
    alert_dezenas: list[str] = []
    for dezena, frequencia in sorted(dezena_game_counts.items()):
        percentual = round((frequencia / sample_size) * 100.0, 2) if sample_size else 0.0
        leakage_table.append(
            {
                "dezena": f"{dezena:02d}",
                "frequencia_vazamento": int(frequencia),
                "percentual_vazamento": percentual,
                "sample_size": sample_size,
                "reconciliation_run_id": reconciliation_run_id,
            }
        )
        if sample_size and (frequencia / sample_size) > SIDE_LEAK_ALERT_THRESHOLD:
            alert_dezenas.append(f"{dezena:02d}")

    return {
        "available": bool(context.get("available") and games and resultado_oficial),
        "source": SOURCE_POSTGRESQL,
        "tables": RECONCILIATION_TABLES,
        "reconciliation_run_id": reconciliation_run_id,
        "contest_id": contest_id,
        "generation_event_id": default_generation_event_id,
        "ml_role": ML_ROLE_DIAGNOSTIC_ONLY,
        "generation_command": False,
        "recalibration_command": False,
        "leakage_table": leakage_table,
        "drilldown_per_dezena": drilldown_per_dezena,
        "sample_size": sample_size,
        "alert": ALERT_SIDE_LEAK if alert_dezenas else None,
        "alert_dezenas": alert_dezenas,
        "vazamento_definition": "dezena in cartao_final and dezena not in resultado_oficial",
        "sobra_real_definition": "cartao_final - resultado_oficial",
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
            "generation_event_id": int(getattr(run, "generation_event_id", 0) or 0),
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
                    "generation_event_id": int(getattr(run, "generation_event_id", 0) or 0),
                    "resultado_oficial": resultado_oficial,
                    "games": games,
                    "ml_role": ML_ROLE_DIAGNOSTIC_ONLY,
                    "generation_command": False,
                    "recalibration_command": False,
                }
            )
    return contexts


def _side_leak_dezenas_for_context(context: dict[str, Any]) -> dict[int, float]:
    evidence = build_lateral_leakage_evidence(context)
    return {
        int(row["dezena"]): float(row["percentual_vazamento"])
        for row in evidence.get("leakage_table", [])
        if float(row.get("percentual_vazamento", 0) or 0) > (SIDE_LEAK_ALERT_THRESHOLD * 100.0)
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


def _format_alert_regra_base(alert_type: str) -> str:
    if alert_type == ALERT_001:
        return (
            f"vazamento_lateral > {SIDE_LEAK_ALERT_THRESHOLD * 100:.0f}% "
            f"em {MIN_CONSECUTIVE_RUNS_ALERT_001}+ runs consecutivas"
        )
    if alert_type == ALERT_002:
        blind = ", ".join(f"{dezena:02d}" for dezena in sorted(BLIND_SPOTS))
        return f"blind_spot confirmado em evolução ({blind})"
    return f"taxa_conversao > {CONVERSION_ALERT_THRESHOLD * 100:.0f}%"


def _format_alert_threshold_used(alert_type: str) -> str:
    if alert_type == ALERT_001:
        return f"{SIDE_LEAK_ALERT_THRESHOLD * 100:.0f}% / {MIN_CONSECUTIVE_RUNS_ALERT_001} runs"
    if alert_type == ALERT_002:
        return "blind_spot + dezena_faltante"
    return f"{CONVERSION_ALERT_THRESHOLD * 100:.0f}%"


def _format_alert_evidencia(alert: dict[str, Any]) -> str:
    diagnosis = dict(alert.get("ml_diagnosis") or {})
    proposal = dict(alert.get("ml_proposal") or {})
    alert_type = str(alert.get("tipo_alerta") or "")
    dezena = alert.get("dezena_fmt") or f"{int(alert.get('dezena', 0) or 0):02d}"
    if alert_type == ALERT_001:
        frequencia = diagnosis.get("frequencia", 0)
        consecutivas = diagnosis.get("consecutivas", 0)
        return (
            f"Dezena {dezena} em sobra_real com {frequencia}% de vazamento "
            f"em {consecutivas} runs consecutivas."
        )
    if alert_type == ALERT_002:
        return (
            f"Blind spot {dezena} como dezena_faltante em {diagnosis.get('aparicoes', 0)} "
            f"jogos na faixa {diagnosis.get('faixa', '')}."
        )
    faixa = diagnosis.get("faixa", "")
    best_taxa = max(
        float(diagnosis.get("taxa_conversao_13_14", 0) or 0),
        float(diagnosis.get("taxa_conversao_14_15", 0) or 0),
    )
    return (
        f"Dezena {dezena} faltante em {best_taxa}% dos jogos na faixa {faixa}. "
        f"Proposta: {proposal.get('action', '')}."
    )


def assess_alert_evidence_gaps(
    alert: dict[str, Any],
    *,
    leakage_evidence: dict[str, Any] | None = None,
) -> list[str]:
    gaps: list[str] = []
    diagnosis = dict(alert.get("ml_diagnosis") or {})
    alert_type = str(alert.get("tipo_alerta") or "")
    evidence = dict(leakage_evidence or alert.get("leakage_evidence") or {})
    if alert_type == ALERT_001:
        sample_size = int(diagnosis.get("sample_size", 0) or 0)
        leakage_table = list(evidence.get("leakage_table") or [])
        if not sample_size and leakage_table:
            sample_size = int(leakage_table[0].get("sample_size", 0) or 0)
        if sample_size < 2:
            gaps.append("amostra_insuficiente")
        drilldown_map = dict(evidence.get("drilldown_per_dezena") or {})
        drilldown_rows = int((alert.get("ml_proposal") or {}).get("drilldown_rows", 0) or 0)
        if not drilldown_map and drilldown_rows <= 0:
            gaps.append("drilldown_incompleto")
        for row in evidence.get("leakage_table") or []:
            for drill_row in drilldown_map.get(str(row.get("dezena", "")), []) or []:
                if not drill_row.get("cartao_final") or not drill_row.get("resultado_oficial"):
                    gaps.append("falta_cartao_final_ou_resultado_oficial")
                    break
    elif alert_type == ALERT_002:
        if int(diagnosis.get("aparicoes", 0) or 0) < 1:
            gaps.append("amostra_insuficiente")
    elif alert_type == ALERT_003:
        if not diagnosis.get("faixa"):
            gaps.append("amostra_insuficiente")
    if not alert.get("ml_proposal", {}).get("action"):
        gaps.append("regra_nao_identificada")
    if alert_type == ALERT_001:
        consecutivas = int(diagnosis.get("consecutivas", 0) or 0)
        if 0 < consecutivas < MIN_CONSECUTIVE_RUNS_ALERT_001:
            gaps.append("poucas_geracoes")
    return sorted(set(gaps))


def _detect_invalid_evidence_markers(alert: dict[str, Any]) -> list[str]:
    markers: list[str] = []
    proposal = dict(alert.get("ml_proposal") or {})
    fonte = str(alert.get("fonte") or SOURCE_POSTGRESQL)
    if fonte != SOURCE_POSTGRESQL:
        markers.append("fonte_nao_auditavel")
    if not proposal.get("action"):
        markers.append("regra_nao_identificada")
    if proposal.get("operational_effect") or proposal.get("executed"):
        markers.append("proposta_tenta_efeito_operacional")
    if proposal.get("mutates_lei15") or proposal.get("lei15_mutation"):
        markers.append("conflito_com_Lei_15_ou_Lei_15A")
    if proposal.get("mutates_lei15a") or proposal.get("lei15a_mutation"):
        markers.append("conflito_com_Lei_15_ou_Lei_15A")
    if proposal.get("generation_command") or proposal.get("recalibration_command"):
        markers.append("proposta_tenta_efeito_operacional")
    return sorted(set(markers))


def _detect_governance_blockers(alert: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    proposal = dict(alert.get("ml_proposal") or {})
    if bool(alert.get("generation_command") or alert.get("generation_cmd")):
        blockers.append("generation_command_true")
    if bool(alert.get("recalibration_command") or alert.get("recalibration_cmd")):
        blockers.append("recalibration_command_true")
    if proposal.get("operational_effect") or proposal.get("executed"):
        blockers.append("operational_effect_true")
    if proposal.get("mutates_lei15") or proposal.get("lei15_mutation"):
        blockers.append("Lei_15_mutation_detected")
    if proposal.get("mutates_lei15a") or proposal.get("lei15a_mutation"):
        blockers.append("Lei_15A_mutation_detected")
    return sorted(set(blockers))


def _has_auditable_drilldown(alert: dict[str, Any]) -> bool:
    alert_type = str(alert.get("tipo_alerta") or "")
    if alert_type != ALERT_001:
        return bool(alert.get("ml_diagnosis"))
    evidence = dict(alert.get("leakage_evidence") or {})
    drilldown_map = dict(evidence.get("drilldown_per_dezena") or {})
    if not drilldown_map:
        return int((alert.get("ml_proposal") or {}).get("drilldown_rows", 0) or 0) > 0
    for rows in drilldown_map.values():
        for row in rows or []:
            if row.get("cartao_final") and row.get("resultado_oficial"):
                return True
    return False


def _evidence_complete_checks(alert: dict[str, Any], gaps: Sequence[str]) -> dict[str, bool]:
    alert_type = str(alert.get("tipo_alerta") or "")
    proposal = dict(alert.get("ml_proposal") or {})
    insufficient = set(gaps) & INSUFFICIENT_EVIDENCE_MARKERS
    return {
        "regra_ML_existente_identificada": bool(proposal.get("action")),
        "threshold_usado_exibido": bool(_format_alert_threshold_used(alert_type)),
        "evidencia_completa": not insufficient,
        "drilldown_auditavel": _has_auditable_drilldown(alert),
        "cartao_final_presente": "falta_cartao_final_ou_resultado_oficial" not in gaps,
        "resultado_oficial_presente": "falta_cartao_final_ou_resultado_oficial" not in gaps,
        "source_PostgreSQL": str(alert.get("fonte") or SOURCE_POSTGRESQL) == SOURCE_POSTGRESQL,
    }


def build_adm_verdict_guide(alert: dict[str, Any]) -> dict[str, Any]:
    """Guia ADM: elegibilidade observacional para veredito (display-only, sem efeito operacional)."""
    gaps = list(alert.get("evidence_gaps") or assess_alert_evidence_gaps(alert))
    invalid_markers = _detect_invalid_evidence_markers(alert)
    invalid_from_gaps = sorted(set(gaps) & INVALID_EVIDENCE_MARKERS)
    all_invalid = sorted(set(invalid_markers) | set(invalid_from_gaps))
    insufficient = sorted(set(gaps) & INSUFFICIENT_EVIDENCE_MARKERS)
    governance_blockers = _detect_governance_blockers(alert)
    complete_checks = _evidence_complete_checks(alert, gaps)

    if all_invalid:
        evidence_status = EVIDENCE_STATUS_INVALID
    elif insufficient:
        evidence_status = EVIDENCE_STATUS_INSUFFICIENT
    elif all(complete_checks.values()):
        evidence_status = EVIDENCE_STATUS_COMPLETE
    else:
        evidence_status = EVIDENCE_STATUS_INSUFFICIENT

    governance_status = (
        GOVERNANCE_STATUS_BLOCKED
        if governance_blockers
        else GOVERNANCE_STATUS_SAFE_OBSERVATIONAL
    )

    if evidence_status == EVIDENCE_STATUS_INVALID or governance_status == GOVERNANCE_STATUS_BLOCKED:
        suggested_verdict = VERDICT_REJECT
    elif evidence_status == EVIDENCE_STATUS_INSUFFICIENT:
        suggested_verdict = VERDICT_REQUEST_MORE_EVIDENCE
    else:
        suggested_verdict = VERDICT_ACCEPT_DIAGNOSTIC

    return {
        "title": "Guia ADM",
        "evidence_status": evidence_status,
        "governance_status": governance_status,
        "suggested_verdict": suggested_verdict,
        "reason_hint": VERDICT_REASON_HINTS[suggested_verdict],
        "suggested_verdict_display_only": True,
        "adm_can_override": True,
        "override_requires_reason": True,
        "evidence_checks": complete_checks,
        "insufficient_markers": insufficient,
        "invalid_markers": all_invalid,
        "governance_blockers": governance_blockers,
    }


def enrich_alert_card_for_display(alert: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(alert)
    alert_type = str(alert.get("tipo_alerta") or "")
    enriched["evidencia"] = _format_alert_evidencia(alert)
    enriched["regra_base"] = _format_alert_regra_base(alert_type)
    enriched["threshold_usado"] = _format_alert_threshold_used(alert_type)
    enriched["fonte"] = SOURCE_POSTGRESQL
    enriched["generation_cmd"] = False
    enriched["recalibration_cmd"] = False
    enriched["evidence_gaps"] = assess_alert_evidence_gaps(alert)
    enriched["adm_guide"] = build_adm_verdict_guide(enriched)
    return enriched


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
        latest_evidence = build_lateral_leakage_evidence(latest)
        dezena_key = f"{dezena:02d}"
        leakage_row = next(
            (row for row in latest_evidence.get("leakage_table", []) if row.get("dezena") == dezena_key),
            None,
        )
        drilldown_rows = list(latest_evidence.get("drilldown_per_dezena", {}).get(dezena_key, []) or [])
        ml_diagnosis["sample_size"] = int((leakage_row or {}).get("sample_size", 0) or 0)
        ml_diagnosis["frequencia_vazamento"] = int((leakage_row or {}).get("frequencia_vazamento", 0) or 0)
        ml_diagnosis["drilldown_available"] = bool(drilldown_rows)
        ml_proposal = {
            "action": ACTION_PROMOVER_RESERVA_ADR,
            "target_dezena": dezena_key,
            "justificativa": (
                f"Dezena {dezena_key} em sobra_real (cartao_final − resultado_oficial) com "
                f"{frequencia}% de vazamento em {consecutivas} runs consecutivas."
            ),
            "requires_drilldown": True,
            "drilldown_rows": len(drilldown_rows),
        }
        card = _base_alert_card(
            alert_type=ALERT_001,
            tipo_label=ALERT_001_LABEL,
            dezena=dezena,
            ml_diagnosis=ml_diagnosis,
            ml_proposal=ml_proposal,
            reconciliation_run_id=run_id,
        )
        card["leakage_evidence"] = {
            "leakage_table": [leakage_row] if leakage_row else [],
            "drilldown_per_dezena": {dezena_key: drilldown_rows},
            "vazamento_definition": latest_evidence.get("vazamento_definition"),
            "sobra_real_definition": latest_evidence.get("sobra_real_definition"),
        }
        cards.append(card)
    return cards


def build_alert_002_cards(context: dict[str, Any]) -> list[dict[str, Any]]:
    if not context.get("available"):
        return []
    run_id = int(context.get("reconciliation_run_id", 0) or 0)
    game_size = _infer_game_size_from_context(context)
    evolution_targets = get_evolution_target_hits(game_size)
    cards: list[dict[str, Any]] = []
    seen: set[int] = set()
    for target_hits in evolution_targets:
        faixa = _evolution_faixa_label(target_hits)
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
    game_size = _infer_game_size_from_context(context)
    lower_target, upper_target = get_evolution_target_hits(game_size)
    stats_lower = _missing_dezena_stats(context, target_hits=lower_target)
    stats_upper = _missing_dezena_stats(context, target_hits=upper_target)
    all_dezenas = set(stats_lower) | set(stats_upper)
    cards: list[dict[str, Any]] = []
    for dezena in sorted(all_dezenas):
        taxa_lower = stats_lower.get(dezena, {}).get("percentual", 0.0)
        taxa_upper = stats_upper.get(dezena, {}).get("percentual", 0.0)
        best_taxa = max(taxa_lower, taxa_upper)
        if best_taxa <= (CONVERSION_ALERT_THRESHOLD * 100.0):
            continue
        faixa_upper = _evolution_faixa_label(upper_target)
        faixa_lower = _evolution_faixa_label(lower_target)
        faixa = faixa_upper if taxa_upper >= taxa_lower else faixa_lower
        ml_diagnosis = {
            "dezena": f"{dezena:02d}",
            "taxa_conversao_13_14": taxa_lower,
            "taxa_conversao_14_15": taxa_upper,
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


def load_distinct_generation_event_count(
    db_path: str = DEFAULT_DATABASE_PATH,
) -> int:
    """Conta generation_event_id distintos persistidos em reconciliation_runs."""
    with get_session(db_path) as session:
        values = session.query(ReconciliationRun.generation_event_id).distinct().all()
        return len({int(row[0]) for row in values if int(row[0] or 0) > 0})


def annotate_alert_routing(
    alert: dict[str, Any],
    *,
    distinct_generation_events: int,
) -> dict[str, Any]:
    routed = dict(alert)
    count = int(distinct_generation_events)
    alert_type = str(routed.get("tipo_alerta") or "")
    routed["distinct_generation_events"] = count
    routed["min_required_generations"] = MIN_GENERATIONS_FOR_CENTRAL
    routed["formula"] = _format_alert_regra_base(alert_type)
    routed["operational_effect"] = False
    if count < MIN_GENERATIONS_FOR_CENTRAL:
        routed["evidence_level"] = EVIDENCE_LEVEL_LOCAL
        routed["routing_reason"] = "base inferior a 20 gerações"
        routed["verdict_buttons_allowed"] = False
        routed["adr_candidate"] = False
        routed["local_diagnostic_label"] = LOCAL_DIAGNOSTIC_LABEL
    else:
        routed["evidence_level"] = EVIDENCE_LEVEL_RECURRENT
        routed["routing_reason"] = ""
        routed["verdict_buttons_allowed"] = True
    return routed


def is_central_eligible_alert(alert: dict[str, Any]) -> bool:
    if alert.get("evidence_level") != EVIDENCE_LEVEL_RECURRENT:
        return False
    if int(alert.get("distinct_generation_events", 0) or 0) < MIN_GENERATIONS_FOR_CENTRAL:
        return False
    if str(alert.get("fonte") or SOURCE_POSTGRESQL) != SOURCE_POSTGRESQL:
        return False
    guide = dict(alert.get("adm_guide") or {})
    return guide.get("evidence_status") == EVIDENCE_STATUS_COMPLETE


def build_ml_diagnostic_alerts_bundle(
    db_path: str = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    """Monta todos os alertas ML com roteamento local vs recorrente."""
    contexts = load_recent_reconciliation_runs_context(limit=5, db_path=db_path)
    latest = contexts[0] if contexts else _empty_context()
    distinct_generation_events = load_distinct_generation_event_count(db_path=db_path)
    raw_alerts = (
        build_alert_001_cards(contexts)
        + build_alert_002_cards(latest)
        + build_alert_003_cards(latest)
    )
    all_alerts: list[dict[str, Any]] = []
    for raw in raw_alerts:
        routed = annotate_alert_routing(raw, distinct_generation_events=distinct_generation_events)
        enriched = enrich_alert_card_for_display(routed)
        if enriched.get("evidence_level") == EVIDENCE_LEVEL_LOCAL:
            enriched["verdict_buttons_allowed"] = False
            enriched["adr_candidate"] = False
        all_alerts.append(enriched)
    local_alerts = [alert for alert in all_alerts if alert.get("evidence_level") == EVIDENCE_LEVEL_LOCAL]
    central_alerts = [alert for alert in all_alerts if is_central_eligible_alert(alert)]
    return {
        "available": bool(contexts),
        "contexts": contexts,
        "latest": latest,
        "distinct_generation_events": distinct_generation_events,
        "all_alerts": all_alerts,
        "local_alerts": local_alerts,
        "central_alerts": central_alerts,
        "local_alerts_by_panel": {
            "side_leak": [alert for alert in local_alerts if alert.get("tipo_alerta") == ALERT_001],
            "evolution_13_14": [
                alert for alert in local_alerts if alert.get("tipo_alerta") in {ALERT_002, ALERT_003}
            ],
            "evolution_14_15": [
                alert for alert in local_alerts if alert.get("tipo_alerta") in {ALERT_002, ALERT_003}
            ],
        },
    }


def _merge_alert_decisions(
    alerts: Sequence[dict[str, Any]],
    *,
    decisions: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    decision_index = {
        (row["alert_type"], row["dezena"], row["reconciliation_run_id"]): row
        for row in decisions
    }
    merged: list[dict[str, Any]] = []
    for alert in alerts:
        item = dict(alert)
        key = (item["tipo_alerta"], item["dezena"], item["reconciliation_run_id"])
        existing = decision_index.get(key)
        if existing:
            item["status"] = existing.get("status") or existing["adm_decision"]
            item["verdict_type"] = existing.get("verdict_type")
            item["decision_id"] = existing["id"]
            item["verdict_reason"] = existing.get("verdict_reason") or existing.get("adm_reason")
            item["adm_reason"] = existing.get("adm_reason")
            item["adm_user"] = existing.get("adm_user")
            item["decided_at"] = existing.get("decided_at")
            item["missing_evidence"] = list(existing.get("missing_evidence") or [])
            if item.get("evidence_level") == EVIDENCE_LEVEL_RECURRENT:
                item["adr_candidate"] = bool(existing.get("adr_candidate"))
            else:
                item["adr_candidate"] = False
        merged.append(item)
    return merged


def build_central_ml_diagnostics_payload(
    db_path: str = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    """Monta payload da Central — somente alertas RECURRENT_DIAGNOSTIC elegíveis."""
    bundle = build_ml_diagnostic_alerts_bundle(db_path=db_path)
    decisions = list_ml_diagnostic_decisions(db_path=db_path, limit=500)
    active_alerts = _merge_alert_decisions(bundle["central_alerts"], decisions=decisions)
    pending = [alert for alert in active_alerts if alert["status"] in ACTIVE_ALERT_STATUSES]
    latest = bundle["latest"]
    updated_at = datetime.now(UTC).isoformat()
    return {
        "available": bool(bundle["available"]),
        "source": SOURCE_POSTGRESQL,
        "tables": RECONCILIATION_TABLES,
        "reconciliation_run_id": int(latest.get("reconciliation_run_id", 0) or 0),
        "ml_role": ML_ROLE_DIAGNOSTIC_ONLY,
        "generation_command": False,
        "recalibration_command": False,
        "distinct_generation_events": bundle["distinct_generation_events"],
        "min_required_generations": MIN_GENERATIONS_FOR_CENTRAL,
        "local_alerts_count": len(bundle["local_alerts"]),
        "total_alertas_ativos": len(pending),
        "ultima_atualizacao": updated_at,
        "alerts": active_alerts,
        "local_alerts": bundle["local_alerts"],
        "empty_state_message": CENTRAL_EMPTY_NO_RECURRENT_MESSAGE,
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
    status = str(row.status or row.adm_decision or "")
    verdict_reason = row.verdict_reason or row.adm_reason or ""
    return {
        "id": int(row.id or 0),
        "alert_type": row.alert_type,
        "dezena": int(row.dezena or 0),
        "dezena_fmt": f"{int(row.dezena or 0):02d}",
        "ml_proposal": dict(row.ml_proposal or {}),
        "adm_decision": row.adm_decision,
        "decision": status or row.adm_decision,
        "verdict_type": row.verdict_type or "",
        "status": status,
        "adm_reason": row.adm_reason,
        "verdict_reason": verdict_reason,
        "reason": verdict_reason,
        "missing_evidence": list(row.missing_evidence or []),
        "adr_candidate": bool(row.adr_candidate),
        "adm_user": row.adm_user,
        "reconciliation_run_id": int(row.reconciliation_run_id or 0),
        "created_at": row.created_at.isoformat() if row.created_at else "",
        "decided_at": decided_at.isoformat() if decided_at else "",
        "timestamp": decided_at.isoformat() if decided_at else (row.created_at.isoformat() if row.created_at else ""),
    }


def _build_acceptance_effects(
    alert_type: str,
    ml_proposal: dict[str, Any],
    *,
    leakage_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if alert_type == ALERT_001:
        drilldown_count = int(ml_proposal.get("drilldown_rows", 0) or 0)
        evidence = dict(leakage_evidence or {})
        if drilldown_count <= 0 and not evidence.get("drilldown_per_dezena"):
            raise ValueError("ALERT_001 não pode escalar para ADR sem drilldown auditável por jogo.")
        return {
            "effect": "adr_draft_registered",
            "action": ACTION_PROMOVER_RESERVA_ADR,
            "target_dezena": ml_proposal.get("target_dezena"),
            "executed": False,
            "drilldown_attached": True,
            "note": "Rascunho ADR registrado com evidência drilldown; execução aguarda fluxo institucional.",
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


def _build_verdict_effects(
    verdict_type: str,
    alert_type: str,
    ml_proposal: dict[str, Any],
    *,
    leakage_evidence: dict[str, Any] | None = None,
    missing_evidence: Sequence[str] | None = None,
    verdict_reason: str = "",
    alert_card: dict[str, Any] | None = None,
) -> dict[str, Any]:
    operational_effect = False
    card = dict(alert_card or {})
    if verdict_type == VERDICT_ACCEPT_DIAGNOSTIC:
        effects = _build_acceptance_effects(
            alert_type,
            ml_proposal,
            leakage_evidence=leakage_evidence,
        )
        effects.update(
            {
                "feed_institutional_memory": True,
                "adr_candidate": (
                    alert_type == ALERT_001
                    and card.get("evidence_level") == EVIDENCE_LEVEL_RECURRENT
                ),
                "operational_effect": operational_effect,
            }
        )
        return effects
    if verdict_type == VERDICT_REQUEST_MORE_EVIDENCE:
        return {
            "register_missing_evidence": True,
            "keep_alert_active": True,
            "missing_evidence": list(missing_evidence or []),
            "operational_effect": operational_effect,
            "note": "Alerta permanece ativo até evidência complementar.",
        }
    return {
        "register_rejection_reason": True,
        "ml_feedback": True,
        "rejection_reason": verdict_reason,
        "operational_effect": operational_effect,
        "note": "Rejeição registrada com feedback ML; sem efeito operacional.",
    }


def _validate_verdict_request(
    verdict_type: str,
    *,
    alert_card: dict[str, Any] | None,
    leakage_evidence: dict[str, Any] | None,
    verdict_reason: str,
    missing_evidence: Sequence[str],
) -> None:
    alert = dict(alert_card or {})
    proposal = dict(alert.get("ml_proposal") or {})
    gaps = list(missing_evidence) or assess_alert_evidence_gaps(alert, leakage_evidence=leakage_evidence)
    if verdict_type == VERDICT_ACCEPT_DIAGNOSTIC:
        if not proposal.get("action"):
            raise ValueError("ACCEPT_DIAGNOSTIC requer regra_ML_existente_identificada.")
        if gaps:
            raise ValueError(
                "ACCEPT_DIAGNOSTIC requer evidencia_completa e drilldown_auditavel: "
                + ", ".join(gaps)
            )
        if alert.get("generation_command") or alert.get("recalibration_command"):
            raise ValueError("ACCEPT_DIAGNOSTIC exige generation_command=False e recalibration_command=False.")
        return
    if verdict_type == VERDICT_REQUEST_MORE_EVIDENCE:
        if not str(verdict_reason or "").strip():
            raise ValueError("verdict_reason é obrigatório para REQUEST_MORE_EVIDENCE.")
        if not gaps:
            raise ValueError(
                "REQUEST_MORE_EVIDENCE requer ao menos uma lacuna: "
                "amostra_insuficiente, poucas_geracoes, drilldown_incompleto "
                "ou falta_cartao_final_ou_resultado_oficial."
            )
        return
    if verdict_type == VERDICT_REJECT:
        if not str(verdict_reason or "").strip():
            raise ValueError("verdict_reason é obrigatório para REJECT.")


def _validate_central_verdict_allowed(alert_card: dict[str, Any] | None) -> None:
    card = dict(alert_card or {})
    if card.get("evidence_level") == EVIDENCE_LEVEL_LOCAL:
        raise ValueError(
            "Alertas locais (< 20 gerações) não são elegíveis para veredito ADM na Central."
        )
    if not card.get("verdict_buttons_allowed", True):
        raise ValueError("Veredito ADM não permitido para diagnósticos locais.")


def register_ml_diagnostic_verdict(
    *,
    alert_type: str,
    dezena: int,
    ml_proposal: dict[str, Any],
    verdict_type: str,
    reconciliation_run_id: int,
    verdict_reason: str = "",
    adm_user: str = "",
    leakage_evidence: dict[str, Any] | None = None,
    alert_card: dict[str, Any] | None = None,
    missing_evidence: Sequence[str] | None = None,
    db_path: str = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    """Persiste veredito ADM (ADM_VERDICT_POLICY). Nenhum veredito gera efeito operacional."""
    normalized_verdict = str(verdict_type or "").strip().upper()
    if normalized_verdict not in VERDICT_OPTIONS:
        raise ValueError("verdict_type deve ser ACCEPT_DIAGNOSTIC, REQUEST_MORE_EVIDENCE ou REJECT")
    proposal = dict(ml_proposal or {})
    card = dict(alert_card or {})
    card.setdefault("tipo_alerta", alert_type)
    card.setdefault("ml_proposal", proposal)
    card.setdefault("generation_command", False)
    card.setdefault("recalibration_command", False)
    gaps = list(missing_evidence or assess_alert_evidence_gaps(card, leakage_evidence=leakage_evidence))
    _validate_central_verdict_allowed(card)
    _validate_verdict_request(
        normalized_verdict,
        alert_card=card,
        leakage_evidence=leakage_evidence,
        verdict_reason=verdict_reason,
        missing_evidence=gaps,
    )
    status = VERDICT_STATUS_BY_TYPE[normalized_verdict]
    adm_decision = status if status in {STATUS_ACEITO, STATUS_REJEITADO} else STATUS_PENDENTE_EVIDENCIA
    adr_candidate = (
        normalized_verdict == VERDICT_ACCEPT_DIAGNOSTIC
        and alert_type == ALERT_001
        and card.get("evidence_level") == EVIDENCE_LEVEL_RECURRENT
    )
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
        payload["verdict_effects"] = _build_verdict_effects(
            normalized_verdict,
            alert_type,
            proposal,
            leakage_evidence=leakage_evidence,
            missing_evidence=gaps,
            verdict_reason=verdict_reason,
            alert_card=card,
        )
        if leakage_evidence:
            payload["leakage_evidence"] = dict(leakage_evidence)
        if normalized_verdict == VERDICT_REJECT:
            payload["archived"] = True
        row = MlDiagnosticDecision(
            alert_type=alert_type,
            dezena=int(dezena),
            ml_proposal=payload,
            adm_decision=adm_decision,
            adm_reason=str(verdict_reason or "").strip() or None,
            verdict_type=normalized_verdict,
            status=status,
            verdict_reason=str(verdict_reason or "").strip() or None,
            missing_evidence=gaps if normalized_verdict == VERDICT_REQUEST_MORE_EVIDENCE else [],
            adr_candidate=adr_candidate,
            adm_user=str(adm_user or "").strip(),
            reconciliation_run_id=int(reconciliation_run_id),
            created_at=now,
            decided_at=now,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return _serialize_decision_row(row)


def register_ml_diagnostic_decision(
    *,
    alert_type: str,
    dezena: int,
    ml_proposal: dict[str, Any],
    adm_decision: str,
    reconciliation_run_id: int,
    adm_reason: str = "",
    adm_user: str = "",
    leakage_evidence: dict[str, Any] | None = None,
    alert_card: dict[str, Any] | None = None,
    db_path: str = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    """Compat wrapper: ACEITO/REJEITADO → ADM_VERDICT_POLICY."""
    normalized_decision = str(adm_decision or "").strip().upper()
    if normalized_decision == ADM_ACEITO:
        verdict_type = VERDICT_ACCEPT_DIAGNOSTIC
    elif normalized_decision == ADM_REJEITADO:
        verdict_type = VERDICT_REJECT
    else:
        raise ValueError("adm_decision deve ser ACEITO ou REJEITADO")
    card = dict(alert_card or {})
    card.setdefault("tipo_alerta", alert_type)
    card.setdefault("ml_proposal", ml_proposal)
    if leakage_evidence:
        card["leakage_evidence"] = dict(leakage_evidence)
        if alert_type == ALERT_001:
            leakage_table = list(leakage_evidence.get("leakage_table") or [])
            drilldown_map = dict(leakage_evidence.get("drilldown_per_dezena") or {})
            card.setdefault(
                "ml_diagnosis",
                {
                    "sample_size": int((leakage_table[0] or {}).get("sample_size", 0) or 0) if leakage_table else 0,
                    "drilldown_available": bool(drilldown_map),
                },
            )
    return register_ml_diagnostic_verdict(
        alert_type=alert_type,
        dezena=dezena,
        ml_proposal=ml_proposal,
        verdict_type=verdict_type,
        reconciliation_run_id=reconciliation_run_id,
        verdict_reason=adm_reason,
        adm_user=adm_user,
        leakage_evidence=leakage_evidence,
        alert_card=card,
        db_path=db_path,
    )


def build_side_leak_panel_payload(
    context: dict[str, Any],
    *,
    local_alerts: Sequence[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    evidence = build_lateral_leakage_evidence(context)
    leakage_table = list(evidence.get("leakage_table") or [])
    locals_for_panel = list(local_alerts or [])
    return {
        "available": bool(evidence.get("available")),
        "source": SOURCE_POSTGRESQL,
        "tables": RECONCILIATION_TABLES,
        "reconciliation_run_id": int(evidence.get("reconciliation_run_id", 0) or 0),
        "ml_role": ML_ROLE_DIAGNOSTIC_ONLY,
        "generation_command": False,
        "recalibration_command": False,
        "rows": leakage_table,
        "leakage_table": leakage_table,
        "drilldown_per_dezena": dict(evidence.get("drilldown_per_dezena") or {}),
        "total_games": int(evidence.get("sample_size", 0) or 0),
        "sample_size": int(evidence.get("sample_size", 0) or 0),
        "alert": evidence.get("alert"),
        "alert_dezenas": list(evidence.get("alert_dezenas") or []),
        "vazamento_definition": evidence.get("vazamento_definition"),
        "sobra_real_definition": evidence.get("sobra_real_definition"),
        "nucleo_lei15_15d": sorted(NUCLEO_LEI15_15D_CONGELADO),
        "show_local_diagnostics": bool(locals_for_panel),
        "local_diagnostic_label": LOCAL_DIAGNOSTIC_LABEL,
        "local_diagnostics": locals_for_panel,
        "min_required_generations": MIN_GENERATIONS_FOR_CENTRAL,
    }


def _attach_local_diagnostics_to_evolution_payload(
    payload: dict[str, Any],
    *,
    local_alerts: Sequence[dict[str, Any]] | None,
) -> dict[str, Any]:
    enriched = dict(payload)
    locals_for_panel = list(local_alerts or [])
    enriched["show_local_diagnostics"] = bool(locals_for_panel)
    enriched["local_diagnostic_label"] = LOCAL_DIAGNOSTIC_LABEL
    enriched["local_diagnostics"] = locals_for_panel
    enriched["min_required_generations"] = MIN_GENERATIONS_FOR_CENTRAL
    return enriched


def _build_evolution_panel_payload(
    context: dict[str, Any],
    *,
    target_hits: int,
    candidate_flag: str,
    local_alerts: Sequence[dict[str, Any]] | None = None,
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
    return _attach_local_diagnostics_to_evolution_payload(
        {
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
        },
        local_alerts=local_alerts,
    )


def build_evolution_13_14_panel_payload(
    context: dict[str, Any],
    *,
    local_alerts: Sequence[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    game_size = _infer_game_size_from_context(context)
    lower_target, _ = get_evolution_target_hits(game_size)
    return _build_evolution_panel_payload(
        context,
        target_hits=lower_target,
        candidate_flag=CANDIDATE_FLAG_13_14,
        local_alerts=local_alerts,
    )


def build_evolution_14_15_panel_payload(
    context: dict[str, Any],
    *,
    local_alerts: Sequence[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    game_size = _infer_game_size_from_context(context)
    _, upper_target = get_evolution_target_hits(game_size)
    return _build_evolution_panel_payload(
        context,
        target_hits=upper_target,
        candidate_flag=CANDIDATE_FLAG_14_15,
        local_alerts=local_alerts,
    )
