"""Veredito operacional ML — M-ML-060-FIX-01."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from lotoia.ml.overlap_format_thresholds import (
    LEVEL_ATENCAO,
    LEVEL_CRITICO,
    LEVEL_RUIM,
    NEAR_DUP_HIGH_THRESHOLD,
    build_per_format_overlap_analysis,
    classify_similarity_for_format,
)
from lotoia.observability.card_structure_diagnostics import (
    build_card_structure_payload,
    extract_operational_structural_metrics,
)

MISSION_ID = "M-ML-060-FIX-01"
HITS_SEPARATION_MISSION_ID = "M-ML-076-FIX-01"

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

# M-SENSOR-001: thresholds calibráveis via feedback de conferência
# Quando calibração disponível, estes valores são sobrescritos por
# calibrate_ml_thresholds() em threshold_calibration_from_conference.py
_CALIBRATED_THRESHOLDS: dict[str, float] | None = None


def set_calibrated_thresholds(thresholds: dict[str, float]) -> None:
    """M-SENSOR-001: Atualiza thresholds com valores calibrados empiricamente.

    Deve ser chamado após calibrate_ml_thresholds() rodar com dados suficientes
    de conferência. Os thresholds calibrados substituem os defaults para o
    restante da sessão.
    """
    global _CALIBRATED_THRESHOLDS
    _CALIBRATED_THRESHOLDS = thresholds


def get_similarity_thresholds() -> dict[str, float]:
    """M-SENSOR-001: Retorna thresholds ativos (calibrados ou default)."""
    if _CALIBRATED_THRESHOLDS:
        return {
            "attention_min": _CALIBRATED_THRESHOLDS.get("ideal_max", 0.58) + 0.01,
            "attention_max": _CALIBRATED_THRESHOLDS.get("atencao_max", 0.64),
            "calibration_min": _CALIBRATED_THRESHOLDS.get("atencao_max", 0.64) + 0.01,
            "reproved_min": _CALIBRATED_THRESHOLDS.get("critico_above", 0.70),
        }
    return {
        "attention_min": SIMILARITY_ATTENTION_MIN,
        "attention_max": SIMILARITY_ATTENTION_MAX,
        "calibration_min": SIMILARITY_CALIBRATION_MIN,
        "reproved_min": SIMILARITY_REPROVED_MIN,
    }


NEXT_ACTION_CALIBRATION = "Autorizar calibração supervisionada."


def build_structural_verdict_hits_separation_trace() -> dict[str, Any]:
    """Rastreabilidade M-ML-076-FIX-01 — hits fora do veredito estrutural."""
    return {
        "structural_verdict_ignores_hits": True,
        "hits_evaluation_scope": "historical_analytics_only",
        "hit_metrics_excluded_from_release": True,
        "m_ml_076_fix_01_applied": True,
        "hits_separation_mission_id": HITS_SEPARATION_MISSION_ID,
    }


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
    per_format = [
        dict(row) for row in list(format_analyses or m.get("format_analyses") or [])
    ]
    similaridade = _safe_float(m.get("similaridade_media"))
    quase_repetidos = _safe_int(
        m.get("quase_repetidos_criticos", m.get("quase_repetidos"))
    )
    pares_atencao = _safe_int(m.get("pares_em_atencao"))
    primary_size = _safe_int(
        m.get("primary_format_size") or (m.get("formatos_analisados") or [15])[0]
        if m.get("formatos_analisados")
        else 15,
        15,
    )
    similarity_reading = classify_similarity_for_format(similaridade, primary_size)
    thresholds = get_similarity_thresholds()
    hits_13 = _safe_int(m.get("desempenho_13_hits"))
    hits_14 = _safe_int(m.get("desempenho_14_hits"))
    hits_15 = _safe_int(m.get("desempenho_15_hits"))
    total_jogos = _safe_int(m.get("total_jogos"))

    has_critical_overlap = any(
        str(row.get("level") or "") == LEVEL_CRITICO for row in per_format
    )
    has_ruim_overlap = any(
        str(row.get("level") or "") == LEVEL_RUIM for row in per_format
    )
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

    if similarity_reading["band"] == "critico":
        verdict = _merge_verdict(verdict, VERDICT_REPROVADO)
        reason_parts.append(
            f"similaridade média crítica para {primary_size}D ({similaridade:.4f})"
        )
        rule_triggers.append("similaridade_critica_formato")
    elif similarity_reading["band"] == "alta_redundancia":
        verdict = _merge_verdict(verdict, VERDICT_PRECISA_CALIBRAR)
        reason_parts.append(
            f"similaridade média alta para {primary_size}D ({similaridade:.4f})"
        )
        rule_triggers.append("similaridade_alta_redundancia_formato")
    elif similarity_reading["band"] == "atencao":
        verdict = _merge_verdict(verdict, VERDICT_APROVADO_COM_ALERTA)
        reason_parts.append(
            f"similaridade média em atenção para {primary_size}D ({similaridade:.4f})"
        )
        rule_triggers.append("similaridade_atencao_formato")
    elif similaridade > thresholds["reproved_min"]:
        verdict = _merge_verdict(verdict, VERDICT_REPROVADO)
        reason_parts.append(f"similaridade média crítica ({similaridade:.4f})")
        rule_triggers.append("similaridade_reprovada")
    elif similaridade > thresholds["calibration_min"]:
        verdict = _merge_verdict(verdict, VERDICT_PRECISA_CALIBRAR)
        reason_parts.append(f"similaridade média elevada ({similaridade:.4f})")
        rule_triggers.append("similaridade_calibracao")
    elif thresholds["attention_min"] <= similaridade <= thresholds["attention_max"]:
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
        thresholds["attention_min"] <= similaridade <= thresholds["attention_max"]
        and high_near_dup
    ):
        verdict = _merge_verdict(verdict, VERDICT_PRECISA_CALIBRAR)
        rule_triggers.append("alerta_com_quase_repetidos")

    primary_analysis = per_format[0] if len(per_format) == 1 else None
    if primary_analysis and str(primary_analysis.get("level")) == LEVEL_ATENCAO:
        if (
            similarity_reading["band"] in {"atencao", "alta_redundancia", "critico"}
            and pares_atencao >= 10
        ):
            verdict = _merge_verdict(verdict, VERDICT_PRECISA_CALIBRAR)
            reason_parts.append(
                f"overlap máximo em atenção ({primary_analysis.get('sobreposicao_maxima')}) "
                f"com {pares_atencao} pares em atenção e similaridade {similaridade:.4f}"
            )
            rule_triggers.append("overlap_atencao_com_redundancia_agregada")

    policy_status = str(m.get("policy_compliance_status") or "").strip().lower()
    policy_label = str(m.get("policy_compliance_label") or "").strip().upper()
    policy_violations = [
        str(item).strip()
        for item in list(m.get("policy_violations") or [])
        if str(item).strip()
    ]
    if policy_status == "non_compliant" or policy_label == "REPROVADO":
        policy_verdict = (
            VERDICT_REPROVADO
            if len(policy_violations) >= 3
            else VERDICT_PRECISA_CALIBRAR
        )
        verdict = _merge_verdict(verdict, policy_verdict)
        reason_parts.append(
            f"política estrutural 15D não conforme ({policy_label or policy_status})"
        )
        rule_triggers.append("structural_policy_15d_non_compliant")
    elif policy_status == "partial" or policy_label == "ATENÇÃO":
        policy_verdict = (
            VERDICT_PRECISA_CALIBRAR
            if policy_violations
            else VERDICT_APROVADO_COM_ALERTA
        )
        verdict = _merge_verdict(verdict, policy_verdict)
        reason_parts.append(
            f"política estrutural 15D em atenção ({policy_label or policy_status})"
        )
        rule_triggers.append("structural_policy_15d_atencao")
    elif policy_violations:
        verdict = _merge_verdict(verdict, VERDICT_APROVADO_COM_ALERTA)
        reason_parts.append("alertas de política estrutural 15D (core/discouraged)")
        rule_triggers.append("structural_policy_15d_diagnostic")

    overlap_detail = _format_overlap_detail(per_format)
    if overlap_detail and overlap_detail not in reason_parts:
        reason_parts.insert(0, overlap_detail)
    elif not reason_parts and verdict != VERDICT_APROVADO:
        reason_parts.append("indicadores estruturais exigem revisão ML")

    primary_reason = (
        ". ".join(dict.fromkeys(part for part in reason_parts if part))
        or "Sem bloqueios estruturais."
    )
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
        **build_structural_verdict_hits_separation_trace(),
        "similaridade_media": similaridade,
        "sobreposicao_maxima": _safe_int(m.get("sobreposicao_maxima")),
        "quase_repetidos": quase_repetidos,
        "quase_repetidos_criticos": quase_repetidos,
        "pares_em_atencao": pares_atencao,
        "similarity_band": similarity_reading,
        "calibration_applied": bool(calibration_applied),
        "calibration_authorized": bool(calibration_authorized),
        "official_release_allowed": official_release_allowed,
        "rule_triggers": rule_triggers,
        "format_analyses_count": len(per_format),
        "has_critical_overlap": has_critical_overlap,
        "policy_compliance_status": policy_status,
        "policy_compliance_label": policy_label,
        "policy_violations": policy_violations,
        "thresholds_source": "calibrated" if _CALIBRATED_THRESHOLDS else "default",
        "active_thresholds": thresholds,
    }

    return {
        "mission_id": MISSION_ID,
        "ml_verdict": verdict,
        **build_structural_verdict_hits_separation_trace(),
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
            "quase_repetidos_criticos": quase_repetidos,
            "pares_em_atencao": pares_atencao,
            "similarity_band": similarity_reading,
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
