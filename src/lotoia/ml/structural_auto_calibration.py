"""Calibração estrutural automática format-aware 16D–23D — M-ML-069."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from collections import Counter

from lotoia.ml.structural_concentration_audit import (
    BASE_DOMINANCE_LIMIT_COUNT,
    DOMINANCE_ACCEPTABLE_MAX_COUNT,
    audit_structural_concentration,
)
from lotoia.statistics.card_structure import (
    compute_prefix,
    compute_suffix,
    format_dezena_group,
    resolve_cartao_final_from_game,
)

MISSION_ID = "M-ML-069"
CALIBRATION_VERSION = "M-ML-069-v1"
MIN_FORMAT_SIZE = 16
MAX_FORMAT_SIZE = 23
SUPPORTED_FORMAT_SIZES: tuple[int, ...] = tuple(range(MIN_FORMAT_SIZE, MAX_FORMAT_SIZE + 1))

INTENSITY_BAIXA = "baixa"
INTENSITY_MODERADA = "moderada"
INTENSITY_ALTA = "alta"

INTENSITY_SCALE: dict[str, float] = {
    INTENSITY_BAIXA: 1.0,
    INTENSITY_MODERADA: 1.25,
    INTENSITY_ALTA: 1.5,
}

ACTION_PREFIX_DOMINANT = "prefixo_dominante"
ACTION_SUFFIX_DOMINANT = "sufixo_dominante"
ACTION_LOW_BASE_DIVERSITY = "baixa_diversidade_bases"
ACTION_SUPERFICIAL_EXPANSION = "expansao_superficial"
ACTION_UNDERCOVERED_DEZENAS = "dezenas_subcobertas"
ACTION_EXCESSIVE_DEZENAS = "dezenas_excessivas"
ACTION_RERANK_CONCENTRATION = "rerank_concentrado"
ACTION_LOW_DIVERSITY = "baixa_diversidade"


def is_structural_auto_calibration_format(game_size: int) -> bool:
    return MIN_FORMAT_SIZE <= int(game_size) <= MAX_FORMAT_SIZE


def resolve_progressive_intensity(occurrence_count: int) -> str:
    """Calibração gradual — 1ª baixa, 2ª moderada, 3ª+ alta."""
    count = max(int(occurrence_count), 1)
    if count <= 1:
        return INTENSITY_BAIXA
    if count == 2:
        return INTENSITY_MODERADA
    return INTENSITY_ALTA


def _intensity_label(intensity: str) -> str:
    return {
        INTENSITY_BAIXA: "baixa",
        INTENSITY_MODERADA: "moderada",
        INTENSITY_ALTA: "alta",
    }.get(intensity, intensity)


def build_structural_calibration_memory() -> dict[str, Any]:
    """Memória ML institucional — calibração estrutural por formato."""
    return {
        "mission_id": MISSION_ID,
        "calibration_version": CALIBRATION_VERSION,
        "supported_formats": [f"{size}D" for size in SUPPORTED_FORMAT_SIZES],
        "progressive_intensity": {
            "first": INTENSITY_BAIXA,
            "second": INTENSITY_MODERADA,
            "third_plus": INTENSITY_ALTA,
        },
        "dominance_calibration_threshold_count": DOMINANCE_ACCEPTABLE_MAX_COUNT + 1,
        "action_catalog": {
            ACTION_PREFIX_DOMINANT: "Reduzir score estrutural do prefixo dominante",
            ACTION_SUFFIX_DOMINANT: "Reduzir score estrutural do sufixo dominante",
            ACTION_LOW_BASE_DIVERSITY: "Penalizar base estrutural dominante e promover bases alternativas",
            ACTION_SUPERFICIAL_EXPANSION: "Rotacionar dezenas adicionais na expansão multidezena",
            ACTION_UNDERCOVERED_DEZENAS: "Aumentar peso de cobertura para dezenas subcobertas",
            ACTION_EXCESSIVE_DEZENAS: "Reduzir peso de dezenas excessivamente recorrentes",
            ACTION_RERANK_CONCENTRATION: "Rerank com diversidade + cobertura, não só score ML",
            ACTION_LOW_DIVERSITY: "Elevar diversidade mínima estrutural do pool",
        },
        "per_format_records": {f"{size}D": [] for size in SUPPORTED_FORMAT_SIZES},
    }


def _occurrence_count_for_cause(
    event_context: Mapping[str, Any] | None,
    *,
    game_size: int,
    cause: str,
) -> int:
    context = dict(event_context or {})
    history = dict(context.get("structural_calibration_occurrences") or {})
    key = f"{int(game_size)}D:{cause}"
    return max(int(history.get(key, 0) or 0) + 1, 1)


def _build_action_record(
    *,
    cause: str,
    action: str,
    intensity: str,
    formato: str,
    evidence: str,
    expected_impact: str,
    parametros: dict[str, Any],
) -> dict[str, Any]:
    return {
        "problema_detectado": cause,
        "acao_aplicada": action,
        "intensidade": intensity,
        "intensidade_label": _intensity_label(intensity),
        "formato": formato,
        "evidencia": evidence,
        "impacto_esperado": expected_impact,
        "parametros": parametros,
    }


def derive_structural_calibration_actions(
    audit_report: Mapping[str, Any],
    *,
    occurrence_count: int = 1,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Converte auditoria M-ML-068 em ações automáticas format-aware."""
    report = dict(audit_report)
    game_size = int(str(report.get("formato", "17D")).rstrip("D") or 17)
    formato = f"{game_size}D"
    intensity = resolve_progressive_intensity(occurrence_count)
    scale = float(INTENSITY_SCALE[intensity])
    actions: list[dict[str, Any]] = []
    params: dict[str, Any] = {
        "diversity_floor_boost": 1.0,
        "prefix_penalty": 1.0,
        "suffix_penalty": 1.0,
        "missing_numbers_boost": 1.0,
        "critical_coverage_boost": 1.0,
        "near_duplicate_penalty": 1.0,
        "redundancy_penalty_boost": 1.0,
        "max_overlap_penalty": 1.0,
        "structural_diversity_weight": 1.0,
    }

    prefix = dict((report.get("prefixos_sufixos") or {}).get("prefixo_mais_dominante") or {})
    if int(prefix.get("frequencia", 0) or 0) > DOMINANCE_ACCEPTABLE_MAX_COUNT:
        params["prefix_penalty"] = max(params["prefix_penalty"], 1.1 * scale)
        params["prefixo_alvo"] = str(prefix.get("estrutura") or "")
        params["diversity_floor_boost"] = max(params["diversity_floor_boost"], 1.1 * scale)
        params["structural_diversity_weight"] = max(params["structural_diversity_weight"], 1.15 * scale)
        actions.append(
            _build_action_record(
                cause=ACTION_PREFIX_DOMINANT,
                action=build_structural_calibration_memory()["action_catalog"][ACTION_PREFIX_DOMINANT],
                intensity=intensity,
                formato=formato,
                evidence=(
                    f"Prefixo {prefix.get('estrutura')} em {prefix.get('frequencia')}/"
                    f"{prefix.get('total')} ({prefix.get('share_pct')}%)"
                ),
                expected_impact="Aumento da diversidade estrutural e redução de concentração de abertura",
                parametros={
                    "prefix_penalty": params["prefix_penalty"],
                    "prefixo_alvo": params["prefixo_alvo"],
                },
            )
        )

    suffix = dict((report.get("prefixos_sufixos") or {}).get("sufixo_mais_dominante") or {})
    if int(suffix.get("frequencia", 0) or 0) > DOMINANCE_ACCEPTABLE_MAX_COUNT:
        params["suffix_penalty"] = max(params["suffix_penalty"], 1.1 * scale)
        params["sufixo_alvo"] = str(suffix.get("estrutura") or "")
        params["diversity_floor_boost"] = max(params["diversity_floor_boost"], 1.08 * scale)
        actions.append(
            _build_action_record(
                cause=ACTION_SUFFIX_DOMINANT,
                action=build_structural_calibration_memory()["action_catalog"][ACTION_SUFFIX_DOMINANT],
                intensity=intensity,
                formato=formato,
                evidence=(
                    f"Sufixo {suffix.get('estrutura')} em {suffix.get('frequencia')}/"
                    f"{suffix.get('total')} ({suffix.get('share_pct')}%)"
                ),
                expected_impact="Distribuição mais equilibrada de fechamentos estruturais",
                parametros={
                    "suffix_penalty": params["suffix_penalty"],
                    "sufixo_alvo": params["sufixo_alvo"],
                },
            )
        )

    base = dict(report.get("base_diversity") or {})
    if base.get("base_excede_20pct"):
        dominant = dict(base.get("base_mais_dominante") or {})
        params["near_duplicate_penalty"] = max(params["near_duplicate_penalty"], 1.15 * scale)
        params["diversity_floor_boost"] = max(params["diversity_floor_boost"], 1.12 * scale)
        actions.append(
            _build_action_record(
                cause=ACTION_LOW_BASE_DIVERSITY,
                action=build_structural_calibration_memory()["action_catalog"][ACTION_LOW_BASE_DIVERSITY],
                intensity=intensity,
                formato=formato,
                evidence=f"Base dominante com {dominant.get('jogos')} jogos",
                expected_impact="Maior diversidade de bases estruturais no lote",
                parametros={"near_duplicate_penalty": params["near_duplicate_penalty"]},
            )
        )

    expansion = dict(report.get("expansao_17d") or report.get("expansao_multidezena") or {})
    if expansion.get("available") and (
        expansion.get("nucleo_repetido_excessivo") or expansion.get("par_adicionado_repetido")
    ):
        params["missing_numbers_boost"] = max(params["missing_numbers_boost"], 1.1 * scale)
        params["diversity_floor_boost"] = max(params["diversity_floor_boost"], 1.1 * scale)
        actions.append(
            _build_action_record(
                cause=ACTION_SUPERFICIAL_EXPANSION,
                action=build_structural_calibration_memory()["action_catalog"][ACTION_SUPERFICIAL_EXPANSION],
                intensity=intensity,
                formato=formato,
                evidence="Expansão multidezena com núcleos ou pares adicionados repetidos",
                expected_impact="Exploração estrutural mais ampla na expansão do formato",
                parametros={"missing_numbers_boost": params["missing_numbers_boost"]},
            )
        )

    coverage = dict(report.get("cobertura_dezenas") or {})
    subcovered = list(coverage.get("dezenas_subcobertas") or [])
    if subcovered:
        params["missing_numbers_boost"] = max(params["missing_numbers_boost"], 1.15 * scale)
        params["critical_coverage_boost"] = max(params["critical_coverage_boost"], 1.1 * scale)
        dezenas = [str(row.get("dezena")) for row in subcovered[:12]]
        params["dezenas_subcobertas"] = dezenas
        actions.append(
            _build_action_record(
                cause=ACTION_UNDERCOVERED_DEZENAS,
                action=build_structural_calibration_memory()["action_catalog"][ACTION_UNDERCOVERED_DEZENAS],
                intensity=intensity,
                formato=formato,
                evidence=f"{len(subcovered)} dezenas subcobertas",
                expected_impact="Melhor cobertura das dezenas 01–25",
                parametros={
                    "dezenas_subcobertas": dezenas,
                    "missing_numbers_boost": params["missing_numbers_boost"],
                    "critical_coverage_boost": params["critical_coverage_boost"],
                },
            )
        )

    excessive = list(coverage.get("dezenas_excessivas") or [])
    if excessive:
        params["redundancy_penalty_boost"] = max(params["redundancy_penalty_boost"], 1.1 * scale)
        params["dezenas_excessivas"] = [str(row.get("dezena")) for row in excessive[:12]]
        actions.append(
            _build_action_record(
                cause=ACTION_EXCESSIVE_DEZENAS,
                action=build_structural_calibration_memory()["action_catalog"][ACTION_EXCESSIVE_DEZENAS],
                intensity=intensity,
                formato=formato,
                evidence=f"{len(excessive)} dezenas excessivas",
                expected_impact="Redução de recorrência excessiva de dezenas",
                parametros={
                    "dezenas_excessivas": params["dezenas_excessivas"],
                    "redundancy_penalty_boost": params["redundancy_penalty_boost"],
                },
            )
        )

    pool = dict(report.get("pool_diversity") or {})
    diversity_score = float(report.get("diversity_score", 0) or 0)
    if pool.get("rerank_reduziu_similaridade") is False or diversity_score < 0.45:
        params["structural_diversity_weight"] = max(params["structural_diversity_weight"], 1.2 * scale)
        params["diversity_floor_boost"] = max(params["diversity_floor_boost"], 1.15 * scale)
        params["redundancy_penalty_boost"] = max(params["redundancy_penalty_boost"], 1.1 * scale)
        actions.append(
            _build_action_record(
                cause=ACTION_RERANK_CONCENTRATION,
                action=build_structural_calibration_memory()["action_catalog"][ACTION_RERANK_CONCENTRATION],
                intensity=intensity,
                formato=formato,
                evidence="Rerank concentrado por score sem ganho de diversidade",
                expected_impact="Rerank equilibrado entre score ML, diversidade e cobertura",
                parametros={
                    "structural_diversity_weight": params["structural_diversity_weight"],
                    "diversity_floor_boost": params["diversity_floor_boost"],
                },
            )
        )

    if diversity_score < 0.55 and not any(row["problema_detectado"] == ACTION_LOW_DIVERSITY for row in actions):
        params["diversity_floor_boost"] = max(params["diversity_floor_boost"], 1.12 * scale)
        actions.append(
            _build_action_record(
                cause=ACTION_LOW_DIVERSITY,
                action=build_structural_calibration_memory()["action_catalog"][ACTION_LOW_DIVERSITY],
                intensity=intensity,
                formato=formato,
                evidence=f"Score diversidade {diversity_score:.4f}",
                expected_impact="Aumento da diversidade estrutural agregada",
                parametros={"diversity_floor_boost": params["diversity_floor_boost"]},
            )
        )

    return actions, params


def build_auto_calibration_plan(
    audit_report: Mapping[str, Any],
    *,
    occurrence_count: int = 1,
    auto_authorized: bool = True,
) -> dict[str, Any]:
    """Plano de calibração automática a partir da auditoria estrutural."""
    actions, merged_params = derive_structural_calibration_actions(
        audit_report, occurrence_count=occurrence_count
    )
    plan_items: list[str] = []
    impact_items: list[str] = []
    for row in actions:
        plan_items.append(f"{row['acao_aplicada']} ({row['intensidade_label']})")
        impact_items.append(str(row.get("impacto_esperado") or ""))

    game_size = int(str(dict(audit_report).get("formato", "17D")).rstrip("D") or 17)
    memory = build_structural_calibration_memory()
    record = {
        "formato": f"{game_size}D",
        "occurrence_count": int(occurrence_count),
        "actions": actions,
        "parametros": merged_params,
    }
    memory["per_format_records"][f"{game_size}D"] = [record]

    return {
        "mission_id": MISSION_ID,
        "calibration_version": CALIBRATION_VERSION,
        "authorized": bool(auto_authorized),
        "auto_structural_calibration": True,
        "plan_items": plan_items,
        "impact_items": impact_items,
        "parametros_sugeridos": merged_params,
        "structural_actions": actions,
        "structural_calibration_memory": memory,
        "occurrence_count": int(occurrence_count),
        "intensidade": resolve_progressive_intensity(occurrence_count),
    }


def _audit_multidezena_expansion(
    games: Sequence[Mapping[str, Any]],
    *,
    game_size: int,
) -> dict[str, Any]:
    """Expansão multidezena genérica (16D–23D) — núcleo + dezenas adicionadas."""
    if int(game_size) <= 15:
        return {"available": False}
    nuclei_counter: Counter[str] = Counter()
    expansion_counter: Counter[str] = Counter()
    rows = 0
    for game in games:
        payload = dict(game)
        final_card = resolve_cartao_final_from_game(payload)
        if len(final_card) != int(game_size):
            continue
        core = sorted({int(n) for n in (payload.get("core_numbers") or []) if 1 <= int(n) <= 25})
        if not core and len(final_card) >= 15:
            core = final_card[:15]
        nucleus_key = format_dezena_group(core) if core else "—"
        nuclei_counter[nucleus_key] += 1
        added = sorted(set(final_card) - set(core)) if core else []
        expansion_counter[format_dezena_group(added) if added else "—"] += 1
        rows += 1
    top_nuclei = [{"nucleo": k, "jogos": v} for k, v in nuclei_counter.most_common(8)]
    top_expansions = [{"expansao": k, "jogos": v} for k, v in expansion_counter.most_common(8)]
    return {
        "available": rows > 0,
        "cartoes": rows,
        "nucleos_unicos": len(nuclei_counter),
        "expansoes_unicas": len(expansion_counter),
        "top_nucleos": top_nuclei,
        "top_pares_adicionados": top_expansions,
        "nucleo_repetido_excessivo": any(int(r["jogos"]) > BASE_DOMINANCE_LIMIT_COUNT for r in top_nuclei),
        "par_adicionado_repetido": any(int(r["jogos"]) >= 6 for r in top_expansions),
    }


def build_auto_calibration_plan_from_pool(
    games: Sequence[Mapping[str, Any]],
    *,
    game_size: int,
    event_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Audita pool e gera plano automático format-aware (16D–23D)."""
    size = int(game_size)
    if not is_structural_auto_calibration_format(size):
        return {
            "mission_id": MISSION_ID,
            "authorized": False,
            "auto_structural_calibration": False,
            "plan_items": [],
            "parametros_sugeridos": {},
        }
    audit = audit_structural_concentration(
        games,
        game_size=size,
        event_context=event_context,
        generation_event_id=None,
    )
    if size > 15 and not (audit.get("expansao_17d") or {}).get("available"):
        audit["expansao_multidezena"] = _audit_multidezena_expansion(games, game_size=size)
    primary_cause = str((audit.get("diagnostico") or {}).get("problema_detectado") or ACTION_LOW_DIVERSITY)
    occurrence = _occurrence_count_for_cause(event_context, game_size=size, cause=primary_cause)
    plan = build_auto_calibration_plan(audit, occurrence_count=occurrence, auto_authorized=True)
    plan["structural_audit"] = audit
    return plan


def compute_structural_diversity_bonus(
    game: Mapping[str, Any],
    *,
    diagnostics: Mapping[str, Any],
    pool_size: int,
    dominant_prefix: str = "",
    dominant_suffix: str = "",
    rare_prefixes: set[str] | None = None,
    rare_suffixes: set[str] | None = None,
) -> float:
    """Bônus de diversidade estrutural para rerank (não só score ML)."""
    card = resolve_cartao_final_from_game(dict(game))
    if not card:
        return 0.0
    prefix3 = format_dezena_group(compute_prefix(card, 3))
    suffix3 = format_dezena_group(compute_suffix(card, 3))
    bonus = 0.0
    if dominant_prefix and prefix3 != dominant_prefix:
        bonus += 0.35
    if dominant_suffix and suffix3 != dominant_suffix:
        bonus += 0.25
    if rare_prefixes and prefix3 in rare_prefixes:
        bonus += 0.2
    if rare_suffixes and suffix3 in rare_suffixes:
        bonus += 0.15
    number_presence = dict(diagnostics.get("number_presence") or {})
    if number_presence and pool_size > 0:
        min_expected = max(1, int(pool_size * 0.18))
        for number in card:
            if int(number_presence.get(str(number), number_presence.get(number, 0)) or 0) < min_expected:
                bonus += 0.12
    return round(bonus, 4)
