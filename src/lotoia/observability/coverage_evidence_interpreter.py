"""Interpretação de evidências da Cobertura Estrutural para decisão ML (M-ML-VIS-058)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.observability.card_structure_diagnostics import (
    EVIDENCE_LEVEL_LOCAL,
    load_operational_card_structure_diagnostics_from_db,
)

MISSION_ID = "M-ML-VIS-058"
SCOPE_RECENT_OFFICIAL = "recent_official_generations"
DEFAULT_EVENTS_LIMIT = 10

SIMILARITY_HIGH_THRESHOLD = 0.55
DIVERSITY_LOW_THRESHOLD = 0.55
NEAR_DUP_HIGH_THRESHOLD = 20
MAX_OVERLAP_HIGH_DEFAULT = 13


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


def _format_breakdown_from_structural(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    formats = list((payload.get("summary") or {}).get("formatos_analisados") or [])
    if not formats:
        formats = list((payload.get("evidence_base") or {}).get("formatos_analisados") or [])
    return [{"formato": f"{int(fmt)}D", "jogos": 0} for fmt in sorted(formats)]


def _extract_metrics_from_structural_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    redundancy = dict(payload.get("redundancia_gp") or {})
    abertura = dict(payload.get("abertura") or {})
    fechamento = dict(payload.get("fechamento") or {})
    travamento = dict(payload.get("travamento_13_14") or {})
    summary = dict(payload.get("summary") or {})
    evidence_base = dict(payload.get("evidence_base") or {})

    similaridade = _safe_float(redundancy.get("similaridade_media_entre_jogos"))
    sobreposicao_media = _safe_float(redundancy.get("sobreposicao_media"))
    sobreposicao_maxima = _safe_int(redundancy.get("sobreposicao_maxima"))
    quase_repetidos = _safe_int(redundancy.get("cartoes_quase_repetidos"))
    diversity_score = round(max(0.0, 1.0 - similaridade), 3)

    prefix_top = dict(abertura.get("prefixo_3_mais_gerado") or {})
    suffix_top = dict(fechamento.get("sufixo_3_mais_gerado") or {})
    prefix_freq = _safe_int(prefix_top.get("frequencia"))
    suffix_freq = _safe_int(suffix_top.get("frequencia"))
    total_jogos = max(1, _safe_int(summary.get("total_jogos")))

    subcovered = len(list(redundancy.get("dezenas_fora_em_muitos_jogos") or []))
    excessive = len(list(redundancy.get("ausencias_recorrentes_no_GP") or []))

    prefix_suffix_viciados = (
        prefix_freq >= max(3, int(total_jogos * 0.14))
        or suffix_freq >= max(3, int(total_jogos * 0.14))
    )

    hits_13 = len(list(travamento.get("jogos_com_13_hits") or []))
    hits_14 = len(list(travamento.get("jogos_com_14_hits") or []))
    hits_15 = len(list(travamento.get("jogos_com_15_hits") or []))

    return {
        "similaridade_media": round(similaridade, 3),
        "sobreposicao_media": round(sobreposicao_media, 2),
        "sobreposicao_maxima": sobreposicao_maxima,
        "quase_repetidos": quase_repetidos,
        "redundancia_geral": "alta" if quase_repetidos >= NEAR_DUP_HIGH_THRESHOLD or similaridade >= SIMILARITY_HIGH_THRESHOLD else "normal",
        "prefixos_sufixos_viciados": prefix_suffix_viciados,
        "prefixo_mais_gerado": str(prefix_top.get("estrutura") or "—"),
        "sufixo_mais_gerado": str(suffix_top.get("estrutura") or "—"),
        "dezenas_subcobertas": subcovered,
        "dezenas_excessivas": excessive,
        "diversidade_global": "baixa" if diversity_score < DIVERSITY_LOW_THRESHOLD else "adequada",
        "diversity_score": diversity_score,
        "desempenho_13_hits": hits_13,
        "desempenho_14_hits": hits_14,
        "desempenho_15_hits": hits_15,
        "total_jogos": total_jogos,
        "total_geracoes": _safe_int(summary.get("total_geracoes")),
        "format_breakdown": _format_breakdown_from_structural(payload),
        "generation_event_ids": list(evidence_base.get("generation_event_ids") or []),
        "evidence_level": str(payload.get("evidence_level") or EVIDENCE_LEVEL_LOCAL),
        "six_bases_risco": "alerta" if subcovered > 0 or prefix_suffix_viciados else "estável",
    }


def _merge_ml_aggregate_metrics(
    metrics: dict[str, Any],
    aggregate: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(aggregate, Mapping) or not aggregate.get("available"):
        return metrics
    ml_metrics = dict(aggregate.get("metrics") or {})
    merged = dict(metrics)
    if ml_metrics.get("quase_repetidos") is not None:
        merged["quase_repetidos"] = max(
            _safe_int(merged.get("quase_repetidos")),
            _safe_int(ml_metrics.get("quase_repetidos")),
        )
    if ml_metrics.get("similaridade_media") is not None:
        ml_sim = _safe_float(ml_metrics.get("similaridade_media"))
        if ml_sim > 1.0:
            ml_sim = ml_sim / 15.0
        merged["similaridade_media"] = max(_safe_float(merged.get("similaridade_media")), ml_sim)
    if ml_metrics.get("diversity_score") is not None:
        merged["diversity_score"] = min(
            _safe_float(merged.get("diversity_score")),
            _safe_float(ml_metrics.get("diversity_score")),
        )
    merged["diversidade_global"] = (
        "baixa" if _safe_float(merged.get("diversity_score")) < DIVERSITY_LOW_THRESHOLD else "adequada"
    )
    merged["calibrated_events"] = _safe_int(aggregate.get("calibrated_events"))
    merged["calibration_applied_any"] = bool(aggregate.get("calibration_applied"))
    merged["issue_types"] = list(aggregate.get("issue_types") or [])
    if aggregate.get("format_breakdown"):
        merged["format_breakdown"] = list(aggregate.get("format_breakdown") or [])
    return merged


def _build_decision_block(
    *,
    issue_type: str,
    problema_detectado: str,
    evidencia: str,
    causa_provavel: str,
    acao_recomendada: str,
    impacto_esperado: str,
    severidade: str,
    parametros_sugeridos: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "issue_type": issue_type,
        "problema_detectado": problema_detectado,
        "evidencia": evidencia,
        "causa_provavel": causa_provavel,
        "acao_recomendada": acao_recomendada,
        "impacto_esperado": impacto_esperado,
        "severidade": severidade,
        "status": "detectado",
        "parametros_sugeridos": dict(parametros_sugeridos or {}),
        "trace": {"mission_id": MISSION_ID, "issue_type": issue_type, "severidade": severidade},
    }


def interpret_coverage_evidence(
    metrics: Mapping[str, Any],
    *,
    calibration_applied: bool = False,
    trace_persistido: bool = False,
) -> dict[str, Any]:
    """Transforma métricas estruturais em blocos decisórios para a Central ML."""
    blocks: list[dict[str, Any]] = []
    m = dict(metrics)

    similaridade = _safe_float(m.get("similaridade_media"))
    sobreposicao_max = _safe_int(m.get("sobreposicao_maxima"))
    quase_repetidos = _safe_int(m.get("quase_repetidos"))
    diversity_score = _safe_float(m.get("diversity_score"))
    subcovered = _safe_int(m.get("dezenas_subcobertas"))
    game_size = 15

    if similaridade >= SIMILARITY_HIGH_THRESHOLD:
        blocks.append(
            _build_decision_block(
                issue_type="similaridade_media_gp_elevada",
                problema_detectado="Jogos parecidos demais.",
                evidencia=(
                    f"Similaridade média {similaridade:.3f}; "
                    f"sobreposição média {m.get('sobreposicao_media', '—')}; "
                    f"quase repetidos {quase_repetidos}."
                ),
                causa_provavel="Pool com estruturas muito próximas entre cartões.",
                acao_recomendada="Aumentar penalidade de similaridade/overlap no rerank supervisionado.",
                impacto_esperado="Separar cartões similares e reduzir redundância na próxima geração.",
                severidade="alta" if similaridade >= 0.62 else "media",
                parametros_sugeridos={"redundancy_penalty_boost": 1.2},
            )
        )

    if sobreposicao_max >= max(MAX_OVERLAP_HIGH_DEFAULT, game_size - 2):
        blocks.append(
            _build_decision_block(
                issue_type="sobreposicao_maxima_elevada",
                problema_detectado="Excesso de dezenas repetidas entre cartões.",
                evidencia=f"Sobreposição máxima {sobreposicao_max}; similaridade média {similaridade:.3f}.",
                causa_provavel="Overlap máximo acima do limite estrutural tolerado.",
                acao_recomendada="Limitar overlap máximo na saída/rerank supervisionado.",
                impacto_esperado="Reduzir pares de cartões quase idênticos na bateria.",
                severidade="alta",
                parametros_sugeridos={"max_overlap_penalty": 1.15},
            )
        )

    if quase_repetidos >= NEAR_DUP_HIGH_THRESHOLD:
        blocks.append(
            _build_decision_block(
                issue_type="quase_repetidos_alto",
                problema_detectado="Clones estruturais entre jogos.",
                evidencia=f"Quase repetidos {quase_repetidos}; similaridade média {similaridade:.3f}.",
                causa_provavel="Assinaturas estruturais repetidas no pool oficial recente.",
                acao_recomendada="Penalizar assinaturas parecidas e diversificar candidatos no rerank.",
                impacto_esperado="Menos jogos repetitivos e melhor cobertura estrutural.",
                severidade="alta",
                parametros_sugeridos={"near_duplicate_penalty": 1.25},
            )
        )

    if subcovered > 0 or "dezena_subcoberta" in set(m.get("issue_types") or []):
        blocks.append(
            _build_decision_block(
                issue_type="dezena_subcoberta",
                problema_detectado="Cegueira estrutural — dezenas subcobertas.",
                evidencia=f"Dezenas subcobertas {subcovered}; diversidade {diversity_score:.3f}.",
                causa_provavel="Dezenas críticas ausentes ou sub-representadas no pool recente.",
                acao_recomendada="Reforçar dezenas subcobertas no rerank (7/15/23 críticas).",
                impacto_esperado="Melhor cobertura de dezenas ausentes na próxima geração.",
                severidade="alta" if subcovered >= 3 else "media",
                parametros_sugeridos={"missing_numbers_boost": 1.2, "critical_coverage_boost": 1.1},
            )
        )

    if m.get("prefixos_sufixos_viciados"):
        blocks.append(
            _build_decision_block(
                issue_type="prefixo_excessivo",
                problema_detectado="Vício de estrutura em prefixos/sufixos.",
                evidencia=(
                    f"Prefixo mais gerado {m.get('prefixo_mais_gerado', '—')}; "
                    f"sufixo mais gerado {m.get('sufixo_mais_gerado', '—')}."
                ),
                causa_provavel="Concentração repetida nas faixas 01–03 ou 22–25.",
                acao_recomendada="Penalizar prefixos/sufixos repetidos no rerank supervisionado.",
                impacto_esperado="Distribuição mais equilibrada de aberturas e fechamentos.",
                severidade="media",
                parametros_sugeridos={"prefix_penalty": 1.1, "suffix_penalty": 1.1},
            )
        )

    if diversity_score < DIVERSITY_LOW_THRESHOLD:
        blocks.append(
            _build_decision_block(
                issue_type="diversidade_baixa",
                problema_detectado="Diversidade baixa da saída.",
                evidencia=(
                    f"Score diversidade {diversity_score:.3f}; similaridade média {similaridade:.3f}; "
                    f"sobreposição máxima {sobreposicao_max}; quase repetidos {quase_repetidos}."
                ),
                causa_provavel="Baixa cobertura estrutural agregada nas gerações recentes.",
                acao_recomendada="Aumentar diversidade mínima e redistribuir padrões no rerank.",
                impacto_esperado="Reduzir redundância e melhorar cobertura estrutural da próxima geração.",
                severidade="alta" if diversity_score <= 0.2 else "media",
                parametros_sugeridos={"diversity_floor_boost": 1.2},
            )
        )

    hits_13 = _safe_int(m.get("desempenho_13_hits"))
    hits_14 = _safe_int(m.get("desempenho_14_hits"))
    if hits_13 == 0 and hits_14 == 0 and _safe_int(m.get("total_jogos")) >= 5:
        blocks.append(
            _build_decision_block(
                issue_type="captura_13_14_ausente",
                problema_detectado="Baixa força de captura 13/14 na janela comparada.",
                evidencia=(
                    f"Jogos com 13 hits: {hits_13}; 14 hits: {hits_14}; "
                    f"15 hits: {_safe_int(m.get('desempenho_15_hits'))}."
                ),
                causa_provavel="Ausência de proximidade forte contra referência oficial recente.",
                acao_recomendada=(
                    "Combinar reforço de diversidade, dezenas subcobertas e redução de redundância."
                ),
                impacto_esperado="Melhorar capacidade de aproximação estrutural sem clones.",
                severidade="media",
                parametros_sugeridos={
                    "diversity_floor_boost": 1.1,
                    "missing_numbers_boost": 1.1,
                    "redundancy_penalty_boost": 1.1,
                },
            )
        )

    if not calibration_applied and blocks:
        blocks.append(
            _build_decision_block(
                issue_type="calibracao_pendente",
                problema_detectado="Calibração supervisionada pendente/não aplicada.",
                evidencia=(
                    f"Problemas estruturais detectados ({len(blocks)}); "
                    f"calibration_applied=false; trace={'sim' if trace_persistido else 'não'}."
                ),
                causa_provavel="Saída recente sem calibração ML aplicada apesar de alertas estruturais.",
                acao_recomendada="Autorizar calibração supervisionada com base nas evidências acima.",
                impacto_esperado="Aplicar ajustes de rerank na próxima geração CORE_002 + ML.",
                severidade="media",
                parametros_sugeridos={"calibration_authorized": True},
            )
        )

    primary = blocks[0] if blocks else None
    recommendations = [str(block.get("acao_recomendada") or "") for block in blocks if block.get("acao_recomendada")]
    if not recommendations and not calibration_applied:
        recommendations = [
            "Calibração pendente — autorizar após revisar evidências da Cobertura Estrutural."
        ]
    elif not recommendations and calibration_applied:
        recommendations = [
            "Calibração aplicada — validar diversidade e cobertura na próxima geração."
        ]

    return {
        "mission_id": MISSION_ID,
        "problemas_detectados": [block["problema_detectado"] for block in blocks],
        "evidencias": [block["evidencia"] for block in blocks],
        "acoes_recomendadas": recommendations,
        "decision_blocks": blocks,
        "primary_decision": primary,
        "impacto_esperado": primary.get("impacto_esperado") if primary else "",
        "has_structural_issues": bool(blocks),
    }


def get_structural_coverage_evidence(
    db_path: Path | str = DEFAULT_DATABASE_PATH,
    *,
    scope: str = SCOPE_RECENT_OFFICIAL,
    events_limit: int = DEFAULT_EVENTS_LIMIT,
    generation_event_ids: Sequence[int] | None = None,
    ml_aggregate: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Carrega evidências da Cobertura Estrutural para a Central ML."""
    event_ids = [int(value) for value in (generation_event_ids or []) if int(value) > 0]
    structural = load_operational_card_structure_diagnostics_from_db(
        db_path,
        generation_event_ids=event_ids or None,
    )
    if not structural.get("available") and event_ids:
        structural = load_operational_card_structure_diagnostics_from_db(db_path)

    if not structural.get("available"):
        return {
            "available": False,
            "mission_id": MISSION_ID,
            "scope": scope,
            "headline": "Sem evidências estruturais no PostgreSQL",
            "metrics": {},
            "coverage_evidence_snapshot": {},
            "source": "cobertura_estrutural",
        }

    metrics = _extract_metrics_from_structural_payload(structural)
    metrics = _merge_ml_aggregate_metrics(metrics, ml_aggregate)
    calibration_applied = bool((ml_aggregate or {}).get("calibration_applied"))
    interpretation = interpret_coverage_evidence(
        metrics,
        calibration_applied=calibration_applied,
        trace_persistido=calibration_applied,
    )

    return {
        "available": True,
        "mission_id": MISSION_ID,
        "scope": scope,
        "source": "cobertura_estrutural",
        "tables": structural.get("tables"),
        "coverage_layer": structural.get("coverage_layer"),
        "metrics": metrics,
        "coverage_evidence_snapshot": dict(structural),
        "interpretation": interpretation,
        "decision_blocks": list(interpretation.get("decision_blocks") or []),
        "primary_decision": dict(interpretation.get("primary_decision") or {}),
        "problemas_detectados": list(interpretation.get("problemas_detectados") or []),
        "evidencias": list(interpretation.get("evidencias") or []),
        "acoes_recomendadas": list(interpretation.get("acoes_recomendadas") or []),
        "impacto_esperado": str(interpretation.get("impacto_esperado") or ""),
        "generation_event_ids": list(metrics.get("generation_event_ids") or []),
        "events_limit": int(events_limit),
    }
