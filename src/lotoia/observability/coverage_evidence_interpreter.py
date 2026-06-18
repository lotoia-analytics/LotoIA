"""Interpretação de evidências da Cobertura Estrutural para decisão ML (M-ML-VIS-058)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.ml.ml_operational_verdict import (
    MISSION_ID as ML_VERDICT_MISSION_ID,
    evaluate_ml_operational_verdict,
)
from lotoia.ml.overlap_format_thresholds import (
    LEVEL_CRITICO,
    LEVEL_RUIM,
    MISSION_ID as OVERLAP_MISSION_ID,
    MISSION_ID_067 as OVERLAP_MISSION_ID_067,
    build_ml_format_aware_memory,
    build_per_format_overlap_analysis,
    resolve_primary_format_analysis,
)
from lotoia.ml.structural_concentration_audit import (
    MISSION_ID as CONCENTRATION_MISSION_ID,
    audit_structural_concentration_from_db,
)
from lotoia.observability.card_structure_diagnostics import (
    SCOPE_ALL_OPERATIONAL_CORE_002,
    SCOPE_LABEL_ALL_OPERATIONAL,
    SOURCE_COBERTURA_ESTRUTURAL,
    extract_operational_structural_metrics,
    get_structural_coverage_snapshot,
)

MISSION_ID = "M-ML-VIS-058"
FIX01_MISSION_ID = "M-ML-VIS-058-FIX-01"
SOVEREIGN_MISSION_ID = "M-ML-VIS-059"
OVERLAP_FORMAT_MISSION_ID = OVERLAP_MISSION_ID
OVERLAP_FORMAT_MISSION_ID_067 = OVERLAP_MISSION_ID_067
SCOPE_RECENT_OFFICIAL = SCOPE_ALL_OPERATIONAL_CORE_002
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


def _extract_metrics_from_structural_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Compat: delega para fonte única da Cobertura Estrutural (M-ML-VIS-059)."""
    return extract_operational_structural_metrics(payload)


def _attach_ml_operational_metadata(
    metrics: dict[str, Any],
    aggregate: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Anexa metadados operacionais ML sem sobrescrever métricas estruturais soberanas."""
    if not isinstance(aggregate, Mapping) or not aggregate.get("available"):
        return metrics
    merged = dict(metrics)
    merged["calibrated_events"] = _safe_int(aggregate.get("calibrated_events"))
    merged["calibration_applied_any"] = bool(aggregate.get("calibration_applied"))
    merged["ml_events_analyzed"] = _safe_int(aggregate.get("total_events"))
    merged["ml_lot_rows"] = list(aggregate.get("lot_rows") or [])
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


def build_calibration_plan(
    metrics: Mapping[str, Any],
    *,
    format_analyses: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Transforma métricas estruturais em plano operacional de calibração (M-ML-VIS-058-FIX-01)."""
    m = dict(metrics)
    plan_items: list[str] = []
    impact_items: list[str] = []
    parametros_sugeridos: dict[str, Any] = {}

    per_format = [dict(row) for row in list(format_analyses or [])]
    primary_format = resolve_primary_format_analysis(per_format)
    if primary_format:
        fmt = str(primary_format.get("formato") or "")
        overlap = int(primary_format.get("sobreposicao_maxima", 0) or 0)
        level = str(primary_format.get("level") or "")
        plan_items.append(
            f"Classificar sobreposição máxima {overlap} no formato {fmt} "
            f"({primary_format.get('faixa_ideal', '—')})."
        )
        if level in {LEVEL_CRITICO, LEVEL_RUIM}:
            action = str(primary_format.get("recommended_action") or "")
            if action and action not in plan_items:
                plan_items.append(action)
            impact_items.append(f"Reduzir clones/overlap extremo no formato {fmt}.")
            parametros_sugeridos["formato_alvo"] = fmt
            parametros_sugeridos["game_size"] = int(primary_format.get("game_size", 0) or 0)
            parametros_sugeridos["max_overlap_penalty"] = max(
                _safe_float(parametros_sugeridos.get("max_overlap_penalty"), 1.0),
                1.25 if level == LEVEL_CRITICO else 1.15,
            )

    similaridade = _safe_float(m.get("similaridade_media"))
    sobreposicao_max = _safe_int(m.get("sobreposicao_maxima"))
    quase_repetidos = _safe_int(m.get("quase_repetidos_criticos", m.get("quase_repetidos")))
    pares_atencao = _safe_int(m.get("pares_em_atencao"))
    diversity_score = _safe_float(m.get("diversity_score"))
    subcovered = _safe_int(m.get("dezenas_subcobertas"))
    subcovered_list = [
        str(value)
        for value in list(m.get("dezenas_subcobertas_list") or [])
        if str(value).strip()
    ]
    prefix = str(m.get("prefixo_mais_gerado") or "—")
    suffix = str(m.get("sufixo_mais_gerado") or "—")
    prefix_viciado = bool(m.get("prefixo_viciado") or m.get("prefixos_sufixos_viciados"))
    suffix_viciado = bool(m.get("sufixo_viciado") or m.get("prefixos_sufixos_viciados"))
    primary_game_size = int(
        (primary_format or {}).get("game_size")
        or (m.get("formatos_analisados") or [15])[0]
        if len(m.get("formatos_analisados") or []) == 1
        else 15
    )
    game_size = primary_game_size

    if similaridade >= SIMILARITY_HIGH_THRESHOLD:
        plan_items.append("Aumentar penalidade de similaridade/overlap.")
        impact_items.append("Reduzir jogos parecidos.")
        parametros_sugeridos["redundancy_penalty_boost"] = max(
            _safe_float(parametros_sugeridos.get("redundancy_penalty_boost"), 1.0),
            1.2,
        )

    if sobreposicao_max >= max(MAX_OVERLAP_HIGH_DEFAULT, game_size - 2):
        plan_items.append(
            f"Reduzir sobreposição máxima entre cartões (formato {game_size}D, overlap {sobreposicao_max})."
        )
        impact_items.append("Diminuir pares com overlap excessivo.")
        parametros_sugeridos["max_overlap_penalty"] = max(
            _safe_float(parametros_sugeridos.get("max_overlap_penalty"), 1.0),
            1.15,
        )

    if quase_repetidos >= NEAR_DUP_HIGH_THRESHOLD:
        plan_items.append("Penalizar clones estruturais e quase repetidos críticos (overlap N e N-1).")
        impact_items.append("Diminuir quase repetidos críticos.")
        parametros_sugeridos["near_duplicate_penalty"] = max(
            _safe_float(parametros_sugeridos.get("near_duplicate_penalty"), 1.0),
            1.25,
        )

    if pares_atencao >= 10:
        plan_items.append(
            f"Monitorar {pares_atencao} pares em atenção (overlap N-2) — não confundir com quase clone crítico."
        )
        impact_items.append("Reduzir pares em atenção sem mascarar clones reais.")

    if prefix_viciado and prefix not in {"—", ""}:
        plan_items.append(f"Penalizar prefixo viciado {prefix}.")
        impact_items.append("Reduzir vício de prefixo/sufixo.")
        parametros_sugeridos["prefix_penalty"] = max(
            _safe_float(parametros_sugeridos.get("prefix_penalty"), 1.0),
            1.1,
        )
        parametros_sugeridos["prefixo_alvo"] = prefix

    if suffix_viciado and suffix not in {"—", ""}:
        plan_items.append(f"Penalizar sufixo viciado {suffix}.")
        if "Reduzir vício de prefixo/sufixo." not in impact_items:
            impact_items.append("Reduzir vício de prefixo/sufixo.")
        parametros_sugeridos["suffix_penalty"] = max(
            _safe_float(parametros_sugeridos.get("suffix_penalty"), 1.0),
            1.1,
        )
        parametros_sugeridos["sufixo_alvo"] = suffix

    if subcovered > 0 or "dezena_subcoberta" in set(m.get("issue_types") or []):
        dezenas_label = ", ".join(subcovered_list[:12]) if subcovered_list else f"{subcovered} dezena(s)"
        plan_items.append(
            "Reforçar dezenas subcobertas identificadas pela Cobertura Estrutural "
            f"({dezenas_label})."
        )
        impact_items.append("Melhorar distribuição das dezenas.")
        impact_items.append("Aumentar cobertura estrutural.")
        parametros_sugeridos["missing_numbers_boost"] = max(
            _safe_float(parametros_sugeridos.get("missing_numbers_boost"), 1.0),
            1.2,
        )
        parametros_sugeridos["critical_coverage_boost"] = max(
            _safe_float(parametros_sugeridos.get("critical_coverage_boost"), 1.0),
            1.1,
        )
        if subcovered_list:
            parametros_sugeridos["dezenas_subcobertas"] = subcovered_list

    if diversity_score < DIVERSITY_LOW_THRESHOLD:
        plan_items.append("Elevar diversidade mínima da saída e redistribuir padrões estruturais.")
        impact_items.append("Preparar próxima geração com maior diversidade e menor redundância.")
        parametros_sugeridos["diversity_floor_boost"] = max(
            _safe_float(parametros_sugeridos.get("diversity_floor_boost"), 1.0),
            1.2,
        )

    hits_13 = _safe_int(m.get("desempenho_13_hits"))
    hits_14 = _safe_int(m.get("desempenho_14_hits"))
    if hits_13 == 0 and hits_14 == 0 and _safe_int(m.get("total_jogos")) >= 5:
        combo = (
            "Combinar elevação de diversidade, reforço de dezenas subcobertas "
            "e redução de redundância para captura 13/14."
        )
        if combo not in plan_items:
            plan_items.append(combo)
        impact_items.append("Melhorar leitura das 6 bases.")
        parametros_sugeridos.setdefault("diversity_floor_boost", 1.1)
        parametros_sugeridos.setdefault("missing_numbers_boost", 1.1)
        parametros_sugeridos.setdefault("redundancy_penalty_boost", 1.1)

    if plan_items:
        rerank_action = "Reranquear candidatos antes da persistência oficial."
        if rerank_action not in plan_items:
            plan_items.append(rerank_action)
        parametros_sugeridos["rerank_before_persist"] = True

    # Impacto transversal quando há plano estrutural
    if plan_items:
        for item in (
            "Melhorar leitura das 6 bases.",
            "Preparar próxima geração com maior diversidade e menor redundância.",
        ):
            if item not in impact_items:
                impact_items.append(item)

    return {
        "mission_id": FIX01_MISSION_ID,
        "overlap_format_mission_id": OVERLAP_FORMAT_MISSION_ID,
        "overlap_format_mission_id_067": OVERLAP_FORMAT_MISSION_ID_067,
        "plan_items": plan_items,
        "impact_items": impact_items,
        "parametros_sugeridos": parametros_sugeridos,
        "rerank_action": "Reranquear candidatos antes da persistência oficial." if plan_items else "",
        "has_plan": bool(plan_items),
        "primary_format_analysis": dict(primary_format or {}),
        "format_analyses": per_format,
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
    quase_repetidos = _safe_int(m.get("quase_repetidos_criticos", m.get("quase_repetidos")))
    pares_atencao = _safe_int(m.get("pares_em_atencao"))
    diversity_score = _safe_float(m.get("diversity_score"))
    subcovered = _safe_int(m.get("dezenas_subcobertas"))
    formatos = [int(value) for value in list(m.get("formatos_analisados") or []) if int(value) > 0]
    game_size = int(formatos[0]) if len(formatos) == 1 else 15

    if similaridade >= SIMILARITY_HIGH_THRESHOLD:
        blocks.append(
            _build_decision_block(
                issue_type="similaridade_media_gp_elevada",
                problema_detectado="Jogos parecidos demais.",
                evidencia=(
                    f"Similaridade média {similaridade:.3f}; "
                    f"sobreposição média {m.get('sobreposicao_media', '—')}; "
                    f"quase repetidos críticos {quase_repetidos}; "
                    f"pares em atenção {pares_atencao}."
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
                problema_detectado="Clones estruturais entre jogos (overlap N ou N-1).",
                evidencia=(
                    f"Quase repetidos críticos {quase_repetidos}; "
                    f"pares em atenção {pares_atencao}; similaridade média {similaridade:.3f}."
                ),
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
    format_analyses = list(m.get("format_analyses") or [])
    calibration_plan = build_calibration_plan(m, format_analyses=format_analyses)
    plan_items = list(calibration_plan.get("plan_items") or [])
    recommendations = plan_items if plan_items else [
        str(block.get("acao_recomendada") or "")
        for block in blocks
        if block.get("issue_type") != "calibracao_pendente" and block.get("acao_recomendada")
    ]
    if not recommendations and not calibration_applied:
        recommendations = [
            "Calibração pendente — autorizar após revisar evidências da Cobertura Estrutural."
        ]
    elif not recommendations and calibration_applied:
        recommendations = [
            "Calibração aplicada — validar diversidade e cobertura na próxima geração."
        ]

    impacto_detalhado = list(calibration_plan.get("impact_items") or [])
    if not impacto_detalhado and primary:
        impacto_detalhado = [str(primary.get("impacto_esperado") or "")]

    return {
        "mission_id": MISSION_ID,
        "fix_mission_id": FIX01_MISSION_ID,
        "problemas_detectados": [block["problema_detectado"] for block in blocks],
        "evidencias": [block["evidencia"] for block in blocks],
        "acoes_recomendadas": recommendations,
        "calibration_plan": calibration_plan,
        "plan_items": plan_items,
        "impacto_detalhado": impacto_detalhado,
        "parametros_sugeridos": dict(calibration_plan.get("parametros_sugeridos") or {}),
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
    generation_event_id: int | None = None,
    generation_event_ids: Sequence[int] | None = None,
    game_size: int | None = None,
    scope_label: str = SCOPE_LABEL_ALL_OPERATIONAL,
    ml_aggregate: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Carrega evidências da Cobertura Estrutural para a Central ML (leitura soberana M-ML-VIS-059)."""
    snapshot = get_structural_coverage_snapshot(
        db_path,
        generation_event_id=generation_event_id,
        generation_event_ids=generation_event_ids,
        game_size=game_size,
        scope_id=scope,
        scope_label=scope_label,
    )
    if not snapshot.get("available"):
        return {
            "available": False,
            "mission_id": MISSION_ID,
            "sovereign_mission_id": SOVEREIGN_MISSION_ID,
            "scope": scope,
            "headline": "Sem evidências estruturais no PostgreSQL",
            "metrics": {},
            "coverage_evidence_snapshot": {},
            "source": SOURCE_COBERTURA_ESTRUTURAL,
            "reading": {},
        }

    structural = dict(snapshot.get("payload") or {})
    metrics = dict(snapshot.get("metrics") or {})
    format_analyses = build_per_format_overlap_analysis(structural, metrics)
    primary_format = resolve_primary_format_analysis(format_analyses)
    overlap_format_memory = build_ml_format_aware_memory()
    if primary_format:
        metrics["primary_format_analysis"] = dict(primary_format)
    metrics["format_analyses"] = format_analyses
    metrics = _attach_ml_operational_metadata(metrics, ml_aggregate)
    calibration_applied = bool((ml_aggregate or {}).get("calibration_applied"))
    calibration_authorized = bool((ml_aggregate or {}).get("calibration_authorized"))
    interpretation = interpret_coverage_evidence(
        metrics,
        calibration_applied=calibration_applied,
        trace_persistido=calibration_applied,
    )
    ml_verdict_payload = evaluate_ml_operational_verdict(
        metrics,
        format_analyses=format_analyses,
        calibration_applied=calibration_applied,
        calibration_authorized=calibration_authorized,
    )
    reading = dict(snapshot.get("reading") or {})

    structural_concentration_audit: dict[str, Any] = {"available": False}
    ge_ids = [int(value) for value in list(metrics.get("generation_event_ids") or []) if int(value) > 0]
    formatos = [int(value) for value in list(metrics.get("formatos_analisados") or []) if int(value) > 0]
    if len(ge_ids) == 1 and formatos:
        try:
            structural_concentration_audit = audit_structural_concentration_from_db(
                db_path,
                generation_event_id=ge_ids[0],
                game_size=formatos[0] if len(formatos) == 1 else None,
            )
        except Exception:
            structural_concentration_audit = {"available": False, "mission_id": CONCENTRATION_MISSION_ID}

    return {
        "available": True,
        "mission_id": MISSION_ID,
        "sovereign_mission_id": SOVEREIGN_MISSION_ID,
        "scope": scope,
        "scope_label": scope_label,
        "source": SOURCE_COBERTURA_ESTRUTURAL,
        "tables": snapshot.get("tables"),
        "coverage_layer": snapshot.get("coverage_layer"),
        "metrics": metrics,
        "coverage_evidence_snapshot": structural,
        "reading": reading,
        "coverage_snapshot_checksum": snapshot.get("coverage_snapshot_checksum"),
        "read_at": snapshot.get("read_at"),
        "filters": dict(snapshot.get("filters") or {}),
        "interpretation": interpretation,
        "decision_blocks": list(interpretation.get("decision_blocks") or []),
        "primary_decision": dict(interpretation.get("primary_decision") or {}),
        "problemas_detectados": list(interpretation.get("problemas_detectados") or []),
        "evidencias": list(interpretation.get("evidencias") or []),
        "acoes_recomendadas": list(interpretation.get("acoes_recomendadas") or []),
        "calibration_plan": dict(interpretation.get("calibration_plan") or {}),
        "plan_items": list(interpretation.get("plan_items") or []),
        "impacto_detalhado": list(interpretation.get("impacto_detalhado") or []),
        "parametros_sugeridos": dict(interpretation.get("parametros_sugeridos") or {}),
        "impacto_esperado": str(interpretation.get("impacto_esperado") or ""),
        "generation_event_ids": list(metrics.get("generation_event_ids") or []),
        "events_limit": int(events_limit),
        "overlap_format_mission_id": OVERLAP_FORMAT_MISSION_ID,
        "overlap_format_mission_id_067": OVERLAP_FORMAT_MISSION_ID_067,
        "overlap_format_memory": overlap_format_memory,
        "ml_format_aware_memory": overlap_format_memory,
        "format_analyses": format_analyses,
        "primary_format_analysis": dict(primary_format or {}),
        "ml_verdict_mission_id": ML_VERDICT_MISSION_ID,
        "ml_verdict": str(ml_verdict_payload.get("ml_verdict") or ""),
        "ml_verdict_reason": str(ml_verdict_payload.get("ml_verdict_reason") or ""),
        "motivo_principal": str(ml_verdict_payload.get("motivo_principal") or ""),
        "official_release_allowed": bool(ml_verdict_payload.get("official_release_allowed")),
        "official_release_label": str(ml_verdict_payload.get("official_release_label") or ""),
        "officialization_status": str(ml_verdict_payload.get("officialization_status") or ""),
        "next_action": str(ml_verdict_payload.get("next_action") or ""),
        "proxima_acao": str(ml_verdict_payload.get("proxima_acao") or ""),
        "ml_verdict_trace": dict(ml_verdict_payload.get("trace") or {}),
        "ml_verdict_payload": ml_verdict_payload,
        "structural_concentration_mission_id": CONCENTRATION_MISSION_ID,
        "structural_concentration_audit": structural_concentration_audit,
    }
