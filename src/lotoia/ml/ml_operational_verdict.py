"""Veredito operacional ML — M-ML-060-FIX-01."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from lotoia.ml.overlap_format_thresholds import (
    LEVEL_CRITICO,
    LEVEL_RUIM,
    NEAR_DUP_HIGH_THRESHOLD,
    build_per_format_overlap_analysis,
)
from lotoia.observability.card_structure_diagnostics import (
    build_card_structure_payload,
    extract_operational_structural_metrics,
)

MISSION_ID = "M-ML-060-FIX-01"

VERDICT_APROVADO = "APROVADO"
VERDICT_APROVADO_COM_ALERTA = "APROVADO COM ALERTA"
VERDICT_PRECISA_CALIBRAR = "PRECISA CALIBRAR"
VERDICT_REPROVADO = "REPROVADO"
VERDICT_BLOQUEADO = "BLOQUEADO PARA OFICIALIZAÇÃO"

ALL_VERDICTS: tuple[str, ...] = (
    VERDICT_APROVADO,
    VERDICT_APROVADO_COM_ALERTA,
    VERDICT_PRECISA_CALIBRAR,
    VERDICT_REPROVADO,
    VERDICT_BLOQUEADO,
)

BLOCKING_VERDICTS: frozenset[str] = frozenset(
    {
        VERDICT_PRECISA_CALIBRAR,
        VERDICT_REPROVADO,
        VERDICT_BLOQUEADO,
    }
)

OFFICIAL_RELEASE_VERDICTS: frozenset[str] = frozenset(
    {
        VERDICT_APROVADO,
        VERDICT_APROVADO_COM_ALERTA,
    }
)

VERDICT_SEVERITY: dict[str, int] = {
    VERDICT_APROVADO: 1,
    VERDICT_APROVADO_COM_ALERTA: 2,
    VERDICT_PRECISA_CALIBRAR: 3,
    VERDICT_REPROVADO: 4,
    VERDICT_BLOQUEADO: 5,
}

SIMILARITY_ATTENTION_MIN = 0.59
SIMILARITY_ATTENTION_MAX = 0.64
SIMILARITY_CALIBRATION_MIN = 0.65
SIMILARITY_REPROVED_MIN = 0.70
SIMILARITY_HIGH_THRESHOLD = 0.55

NEXT_ACTION_CALIBRATION = "Autorizar calibração supervisionada."


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _merge_verdict(current: str, candidate: str) -> str:
    if VERDICT_SEVERITY.get(candidate, 0) > VERDICT_SEVERITY.get(current, 0):
        return candidate
    return current


def _format_overlap_detail(format_analyses: Sequence[Mapping[str, Any]]) -> str:
    parts: list[str] = []
    for row in format_analyses:
        level = str(row.get("level") or "")
        if level not in {LEVEL_CRITICO, LEVEL_RUIM}:
            continue
        fmt = str(row.get("formato") or "—")
        overlap = int(row.get("sobreposicao_maxima", 0) or 0)
        parts.append(f"sobreposição máxima {overlap} em lote com {fmt}")
    return "; ".join(parts)


def is_ml_official_release_allowed(verdict_payload: Mapping[str, Any] | None) -> bool:
    """True quando o lote pode seguir fluxo oficial (Histórico/Conferência)."""
    if not isinstance(verdict_payload, Mapping):
        return True
    if verdict_payload.get("official_release_allowed") is not None:
        return bool(verdict_payload.get("official_release_allowed"))
    verdict = str(verdict_payload.get("ml_verdict") or VERDICT_APROVADO).strip().upper()
    return verdict in OFFICIAL_RELEASE_VERDICTS


def is_ml_verdict_blocking(verdict: str) -> bool:
    return str(verdict or "").strip().upper() in BLOCKING_VERDICTS


def evaluate_ml_operational_verdict(
    metrics: Mapping[str, Any],
    *,
    format_analyses: Sequence[Mapping[str, Any]] | None = None,
    calibration_applied: bool = False,
    calibration_authorized: bool = False,
) -> dict[str, Any]:
    """Emite veredito operacional ML a partir de métricas da Cobertura Estrutural."""
    m = dict(metrics)
    per_format = [dict(row) for row in list(format_analyses or m.get("format_analyses") or [])]
    similaridade = _safe_float(m.get("similaridade_media"))
    quase_repetidos = _safe_int(m.get("quase_repetidos"))
    hits_13 = _safe_int(m.get("desempenho_13_hits"))
    hits_14 = _safe_int(m.get("desempenho_14_hits"))
    hits_15 = _safe_int(m.get("desempenho_15_hits"))
    total_jogos = _safe_int(m.get("total_jogos"))

    has_critical_overlap = any(str(row.get("level") or "") == LEVEL_CRITICO for row in per_format)
    has_ruim_overlap = any(str(row.get("level") or "") == LEVEL_RUIM for row in per_format)
    high_near_dup = quase_repetidos >= NEAR_DUP_HIGH_THRESHOLD
    high_redundancy = high_near_dup or similaridade >= SIMILARITY_HIGH_THRESHOLD

    verdict = VERDICT_APROVADO
    reason_parts: list[str] = []
    rule_triggers: list[str] = []

    if has_critical_overlap:
        verdict = _merge_verdict(verdict, VERDICT_BLOQUEADO)
        reason_parts.append("clone estrutural / sobreposição extrema")
        rule_triggers.append("overlap_critico_formato")

    if has_ruim_overlap and not has_critical_overlap:
        verdict = _merge_verdict(verdict, VERDICT_REPROVADO)
        reason_parts.append("quase clone estrutural")
        rule_triggers.append("overlap_ruim_formato")

    if similaridade > SIMILARITY_REPROVED_MIN:
        verdict = _merge_verdict(verdict, VERDICT_REPROVADO)
        reason_parts.append(f"similaridade média crítica ({similaridade:.4f})")
        rule_triggers.append("similaridade_reprovada")

    elif similaridade > SIMILARITY_CALIBRATION_MIN:
        verdict = _merge_verdict(verdict, VERDICT_PRECISA_CALIBRAR)
        reason_parts.append(f"similaridade média elevada ({similaridade:.4f})")
        rule_triggers.append("similaridade_calibracao")

    elif SIMILARITY_ATTENTION_MIN <= similaridade <= SIMILARITY_ATTENTION_MAX:
        verdict = _merge_verdict(verdict, VERDICT_APROVADO_COM_ALERTA)
        reason_parts.append(f"similaridade média em atenção ({similaridade:.4f})")
        rule_triggers.append("similaridade_alerta")

    if high_near_dup and similaridade >= SIMILARITY_HIGH_THRESHOLD:
        verdict = _merge_verdict(verdict, VERDICT_PRECISA_CALIBRAR)
        if has_critical_overlap:
            verdict = _merge_verdict(verdict, VERDICT_BLOQUEADO)
        reason_parts.append(f"quase repetidos altos ({quase_repetidos})")
        rule_triggers.append("quase_repetidos_alto")

    if (
        SIMILARITY_ATTENTION_MIN <= similaridade <= SIMILARITY_ATTENTION_MAX
        and high_near_dup
    ):
        verdict = _merge_verdict(verdict, VERDICT_PRECISA_CALIBRAR)
        rule_triggers.append("alerta_com_quase_repetidos")

    if hits_13 == 0 and hits_14 == 0 and hits_15 == 0 and total_jogos >= 5 and high_redundancy:
        verdict = _merge_verdict(verdict, VERDICT_PRECISA_CALIBRAR)
        reason_parts.append("ausência de captura 13/14/15 com redundância alta")
        rule_triggers.append("captura_ausente_redundancia")

    overlap_detail = _format_overlap_detail(per_format)
    if overlap_detail and overlap_detail not in reason_parts:
        reason_parts.insert(0, overlap_detail)
    elif not reason_parts and verdict != VERDICT_APROVADO:
        reason_parts.append("indicadores estruturais exigem revisão ML")

    primary_reason = ". ".join(dict.fromkeys(part for part in reason_parts if part)) or "Sem bloqueios estruturais."
    if high_near_dup and overlap_detail:
        primary_reason = f"{overlap_detail} + quase repetidos {quase_repetidos}."

    critical_problem = is_ml_verdict_blocking(verdict)
    official_release_allowed = verdict in OFFICIAL_RELEASE_VERDICTS
    if critical_problem and not calibration_applied:
        official_release_allowed = False
        rule_triggers.append("calibracao_nao_aplicada")
    elif critical_problem and calibration_applied and calibration_authorized:
        official_release_allowed = verdict in OFFICIAL_RELEASE_VERDICTS

    next_action = (
        NEXT_ACTION_CALIBRATION
        if critical_problem
        else "Manter monitoramento estrutural."
    )
    official_release_label = "LIBERADA" if official_release_allowed else "NÃO LIBERADA"

    trace = {
        "mission_id": MISSION_ID,
        "ml_verdict": verdict,
        "similaridade_media": similaridade,
        "sobreposicao_maxima": _safe_int(m.get("sobreposicao_maxima")),
        "quase_repetidos": quase_repetidos,
        "calibration_applied": bool(calibration_applied),
        "calibration_authorized": bool(calibration_authorized),
        "official_release_allowed": official_release_allowed,
        "rule_triggers": rule_triggers,
        "format_analyses_count": len(per_format),
        "has_critical_overlap": has_critical_overlap,
    }

    return {
        "mission_id": MISSION_ID,
        "ml_verdict": verdict,
        "ml_verdict_reason": primary_reason,
        "motivo_principal": primary_reason,
        "official_release_allowed": official_release_allowed,
        "official_release_label": official_release_label,
        "officialization_status": (
            "blocked_pending_calibration"
            if not official_release_allowed
            else "official_release_allowed"
        ),
        "next_action": next_action,
        "proxima_acao": next_action,
        "calibration_applied": bool(calibration_applied),
        "calibration_authorized": bool(calibration_authorized),
        "trace": trace,
        "format_analyses": per_format,
        "metrics_snapshot": {
            "similaridade_media": similaridade,
            "sobreposicao_maxima": _safe_int(m.get("sobreposicao_maxima")),
            "quase_repetidos": quase_repetidos,
            "desempenho_13_hits": hits_13,
            "desempenho_14_hits": hits_14,
            "desempenho_15_hits": hits_15,
            "total_jogos": total_jogos,
        },
    }


def evaluate_batch_ml_verdict_from_games(
    games: Sequence[Mapping[str, Any]],
    *,
    calibration_applied: bool = False,
    calibration_authorized: bool = False,
    official_cards: Sequence[Sequence[int]] | None = None,
    official_contests: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Avalia veredito ML para lote recém-gerado (pré-persistência)."""
    if not games:
        return evaluate_ml_operational_verdict(
            {},
            format_analyses=[],
            calibration_applied=calibration_applied,
            calibration_authorized=calibration_authorized,
        )
    payload = build_card_structure_payload(
        games=[dict(row) for row in games],
        official_cards=list(official_cards or []),
        official_contests=list(official_contests or []),
        generation_event_ids=[],
        reconciliation_run_ids=[],
        contest_ids=[],
    )
    if not payload.get("available"):
        return evaluate_ml_operational_verdict(
            {},
            format_analyses=[],
            calibration_applied=calibration_applied,
            calibration_authorized=calibration_authorized,
        )
    metrics = extract_operational_structural_metrics(payload)
    format_analyses = build_per_format_overlap_analysis(payload, metrics)
    metrics["format_analyses"] = format_analyses
    return evaluate_ml_operational_verdict(
        metrics,
        format_analyses=format_analyses,
        calibration_applied=calibration_applied,
        calibration_authorized=calibration_authorized,
    )
