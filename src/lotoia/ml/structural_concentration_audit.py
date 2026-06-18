"""Auditoria de concentração estrutural — prefixos, sufixos, cobertura, diversidade (M-ML-068)."""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

from lotoia.ml.overlap_format_thresholds import classify_similarity_for_format
from lotoia.statistics.card_structure import (
    compare_structure_profiles,
    compute_band_counts,
    compute_card_structure_metrics,
    compute_gp_redundancy,
    compute_prefix,
    compute_suffix,
    format_dezena_group,
    resolve_cartao_final_from_game,
)

MISSION_ID = "M-ML-068"

DOMINANCE_ACCEPTABLE_MAX_SHARE = 0.25
DOMINANCE_ATTENTION_MAX_SHARE = 0.40
DOMINANCE_HIGH_MAX_SHARE = 0.55
DOMINANCE_ACCEPTABLE_MAX_COUNT = 5
DOMINANCE_ATTENTION_MAX_COUNT = 8
DOMINANCE_HIGH_MAX_COUNT = 11
DOMINANCE_CRITICAL_MIN_COUNT = 12

DEZENA_SEVERE_UNDER = 8
DEZENA_MODERATE_UNDER = 11
DEZENA_ACCEPTABLE_MAX = 16
DEZENA_HIGH_MAX = 20

BASE_DOMINANCE_LIMIT_SHARE = 0.20
BASE_DOMINANCE_LIMIT_COUNT = 4


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def classify_structure_dominance(count: int, total: int) -> dict[str, Any]:
    """Classifica concentração de prefixo/sufixo/base para lote."""
    total_games = max(int(total), 1)
    value = int(count)
    share = round(value / total_games, 4)
    if value >= DOMINANCE_CRITICAL_MIN_COUNT or share > DOMINANCE_HIGH_MAX_SHARE:
        level = "critico"
        label = "crítico"
    elif value >= DOMINANCE_HIGH_MAX_COUNT or share > DOMINANCE_ATTENTION_MAX_SHARE:
        level = "alto"
        label = "alto"
    elif value >= DOMINANCE_ATTENTION_MAX_COUNT or share > DOMINANCE_ACCEPTABLE_MAX_SHARE:
        level = "atencao"
        label = "atenção"
    else:
        level = "aceitavel"
        label = "aceitável"
    return {
        "count": value,
        "total": total_games,
        "share": share,
        "share_pct": round(share * 100, 1),
        "level": level,
        "level_label": label,
        "exceeds_acceptable": level != "aceitavel",
    }


def classify_dezena_frequency(count: int, *, expected: float) -> str:
    """Classifica frequência de dezena vs média esperada do lote."""
    value = int(count)
    if value < DEZENA_SEVERE_UNDER:
        return "subcobertura_severa"
    if value < DEZENA_MODERATE_UNDER:
        return "subcobertura_moderada"
    if value <= DEZENA_ACCEPTABLE_MAX:
        return "aceitavel"
    if value <= DEZENA_HIGH_MAX:
        return "alta"
    return "excessiva_severa"


def _structure_counter(
    cards: Sequence[Sequence[int]],
    *,
    size: int,
    kind: str,
) -> Counter[str]:
    counter: Counter[str] = Counter()
    for card in cards:
        numbers = sorted({int(number) for number in card})
        if not numbers:
            continue
        if kind == "prefix":
            key = format_dezena_group(compute_prefix(numbers, size))
        else:
            key = format_dezena_group(compute_suffix(numbers, size))
        if key:
            counter[key] += 1
    return counter


def audit_prefix_suffix_concentration(
    cards: Sequence[Sequence[int]],
    *,
    total_games: int | None = None,
    official_cards: Sequence[Sequence[int]] | None = None,
) -> dict[str, Any]:
    """Frequência e dominância de prefixos/sufixos 3/4/5."""
    normalized = [sorted({int(number) for number in card}) for card in cards if card]
    pool_total = int(total_games or len(normalized))
    result: dict[str, Any] = {"total_jogos": pool_total, "prefixos": {}, "sufixos": {}}
    dominant_prefix: dict[str, Any] | None = None
    dominant_suffix: dict[str, Any] | None = None

    for kind, bucket in (("prefix", "prefixos"), ("suffix", "sufixos")):
        for size in (3, 4, 5):
            counter = _structure_counter(normalized, size=size, kind=kind)
            rows = [
                {
                    "estrutura": key,
                    "frequencia": int(count),
                    **classify_structure_dominance(int(count), pool_total),
                }
                for key, count in counter.most_common(10)
            ]
            result[bucket][f"{kind}_{size}"] = rows
            if rows and rows[0]["frequencia"] > 0:
                top = dict(rows[0])
                top["tamanho"] = size
                if kind == "prefix":
                    if dominant_prefix is None or top["frequencia"] > dominant_prefix.get("frequencia", 0):
                        dominant_prefix = top
                elif dominant_suffix is None or top["frequencia"] > dominant_suffix.get("frequencia", 0):
                    dominant_suffix = top

    comparison = (
        compare_structure_profiles(normalized, list(official_cards or []))
        if official_cards
        else {"available": False}
    )
    return {
        **result,
        "prefixo_mais_dominante": dominant_prefix,
        "sufixo_mais_dominante": dominant_suffix,
        "comparacao_oficial": comparison,
    }


def audit_dezena_coverage(
    cards: Sequence[Sequence[int]],
    *,
    game_size: int,
    total_games: int | None = None,
) -> dict[str, Any]:
    """Cobertura 01–25 com desvio vs média esperada."""
    normalized = [sorted({int(number) for number in card}) for card in cards if card]
    pool_total = max(int(total_games or len(normalized)), 1)
    size = int(game_size)
    total_positions = pool_total * size
    expected = round(total_positions / 25.0, 2)
    presence = Counter(number for card in normalized for number in card)
    rows: list[dict[str, Any]] = []
    for number in range(1, 26):
        count = int(presence.get(number, 0))
        deviation = round(count - expected, 2)
        classification = classify_dezena_frequency(count, expected=expected)
        rows.append(
            {
                "dezena": f"{number:02d}",
                "frequencia": count,
                "esperado": expected,
                "desvio": deviation,
                "desvio_absoluto": round(abs(deviation), 2),
                "classificacao": classification,
            }
        )
    rows.sort(key=lambda row: (-float(row["desvio_absoluto"]), row["dezena"]))
    subcovered = [row for row in rows if row["classificacao"].startswith("subcobertura")]
    excessive = [row for row in rows if row["classificacao"] in {"alta", "excessiva_severa"}]
    absent = [row for row in rows if row["frequencia"] == 0]
    return {
        "total_jogos": pool_total,
        "game_size": size,
        "total_posicoes": total_positions,
        "media_esperada_por_dezena": expected,
        "tabela_dezenas": rows,
        "dezenas_subcobertas": subcovered,
        "dezenas_excessivas": excessive,
        "dezenas_ausentes": absent,
        "subcobertura_count": len(subcovered),
        "excessiva_count": len(excessive),
    }


def _structural_signature(card: Sequence[int]) -> str:
    metrics = compute_card_structure_metrics(card)
    bands = compute_band_counts(card)
    return "|".join(
        [
            str(metrics.get("prefixo_3") or ""),
            str(metrics.get("sufixo_3") or ""),
            f"b{bands.get('baixas_01_05', 0)}m{bands.get('medias_06_15', 0)}a{bands.get('altas_16_25', 0)}",
            f"p{metrics.get('pares', 0)}i{metrics.get('impares', 0)}",
        ]
    )


def audit_base_diversity(
    games: Sequence[Mapping[str, Any]],
    *,
    total_games: int | None = None,
) -> dict[str, Any]:
    """Diversidade de bases (core_numbers) e clusters estruturais derivados."""
    pool_total = int(total_games or len(games))
    core_counter: Counter[str] = Counter()
    origin_counter: Counter[str] = Counter()
    profile_counter: Counter[str] = Counter()
    signature_counter: Counter[str] = Counter()
    rows_by_core: dict[str, list[int]] = {}

    for index, game in enumerate(games):
        payload = dict(game)
        card = resolve_cartao_final_from_game(payload)
        core = sorted({int(number) for number in (payload.get("core_numbers") or []) if 1 <= int(number) <= 25})
        if core:
            key = format_dezena_group(core)
        else:
            key = _structural_signature(card) if card else f"game_{index}"
        core_counter[key] += 1
        rows_by_core.setdefault(key, []).append(index)
        origin = str(payload.get("origin") or payload.get("generation_mode") or "desconhecido")
        origin_counter[origin] += 1
        profile = str(payload.get("profile_type") or "desconhecido")
        profile_counter[profile] += 1
        if card:
            signature_counter[_structural_signature(card)] += 1

    bases = [
        {
            "base": key,
            "jogos": int(count),
            **classify_structure_dominance(int(count), pool_total),
            "game_indexes": list(rows_by_core.get(key) or []),
        }
        for key, count in core_counter.most_common()
    ]
    dominant = dict(bases[0]) if bases else None
    exceeds_limit = bool(
        dominant
        and (
            int(dominant.get("jogos", 0) or 0) > BASE_DOMINANCE_LIMIT_COUNT
            or float(dominant.get("share", 0) or 0) > BASE_DOMINANCE_LIMIT_SHARE
        )
    )
    return {
        "total_jogos": pool_total,
        "bases_unicas": len(core_counter),
        "top_bases": bases[:10],
        "base_mais_dominante": dominant,
        "base_excede_20pct": exceeds_limit,
        "origens": [{"origem": k, "jogos": v} for k, v in origin_counter.most_common()],
        "profiles": [{"profile_type": k, "jogos": v} for k, v in profile_counter.most_common()],
        "assinaturas_unicas": len(signature_counter),
        "top_assinaturas": [
            {"assinatura": key, "jogos": count}
            for key, count in signature_counter.most_common(8)
        ],
    }


def audit_17d_expansion(games: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Audita expansão 15D→17D: núcleos, reservas e pares adicionados."""
    nuclei_counter: Counter[str] = Counter()
    expansion_counter: Counter[str] = Counter()
    reserve_pair_counter: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []

    for game in games:
        payload = dict(game)
        final_card = resolve_cartao_final_from_game(payload)
        if len(final_card) != 17:
            continue
        core = sorted({int(number) for number in (payload.get("core_numbers") or []) if 1 <= int(number) <= 25})
        reserves = sorted(
            {int(number) for number in (payload.get("audited_reserve_numbers") or []) if 1 <= int(number) <= 25}
        )
        if not core and len(final_card) >= 15:
            core = final_card[:15]
        nucleus_key = format_dezena_group(core) if core else "—"
        nuclei_counter[nucleus_key] += 1
        added = sorted(set(final_card) - set(core)) if core else []
        added_key = format_dezena_group(added) if added else "—"
        expansion_counter[added_key] += 1
        if len(reserves) >= 2:
            reserve_pair_counter[format_dezena_group(reserves[:2])] += 1
        rows.append(
            {
                "nucleo_15d": nucleus_key,
                "dezenas_adicionadas": added_key,
                "reservas_auditadas": format_dezena_group(reserves) if reserves else "—",
            }
        )

    top_nuclei = [{"nucleo": k, "jogos": v} for k, v in nuclei_counter.most_common(8)]
    top_expansions = [{"expansao": k, "jogos": v} for k, v in expansion_counter.most_common(8)]
    top_reserve_pairs = [{"par_reserva": k, "jogos": v} for k, v in reserve_pair_counter.most_common(8)]
    diversity_rate = round(len(expansion_counter) / max(len(rows), 1), 4)
    same_nucleus_risk = any(int(row["jogos"]) > BASE_DOMINANCE_LIMIT_COUNT for row in top_nuclei)
    repeated_pair_risk = any(int(row["jogos"]) >= 6 for row in top_expansions)

    return {
        "available": bool(rows),
        "cartoes_17d": len(rows),
        "nucleos_15d_unicos": len(nuclei_counter),
        "expansoes_17d_unicas": len(expansion_counter),
        "top_nucleos_15d": top_nuclei,
        "top_pares_adicionados": top_expansions,
        "top_pares_reserva": top_reserve_pairs,
        "taxa_diversidade_expansao": diversity_rate,
        "nucleo_repetido_excessivo": same_nucleus_risk,
        "par_adicionado_repetido": repeated_pair_risk,
        "detalhes": rows[:20],
    }


def audit_pool_and_rerank(
    event_context: Mapping[str, Any] | None,
    games: Sequence[Mapping[str, Any]],
    *,
    game_size: int,
) -> dict[str, Any]:
    """Pool diversity e comparação antes/depois do rerank quando disponível."""
    context = dict(event_context or {})
    calibration = dict(context.get("calibration_diagnostics") or {})
    pool_diag = dict(calibration.get("diagnostics") or calibration)
    fill_diag = dict(context.get("fill_diagnostics") or {})
    cards = [resolve_cartao_final_from_game(dict(game)) for game in games]
    cards = [card for card in cards if card]
    final_redundancy = compute_gp_redundancy(cards, game_size=int(game_size)) if len(cards) >= 2 else {}
    pool_redundancy = dict(pool_diag.get("redundancy") or {})
    pool_cards_count = _safe_int(
        calibration.get("pool_size") or pool_diag.get("pool_size") or len(cards)
    )
    rerank_traces = []
    for game in games:
        trace = dict(dict(game).get("decision_trace") or {})
        if trace:
            rerank_traces.append(trace)
    dominant_prefix_pool = list(pool_diag.get("prefix_top") or [])
    dominant_suffix_pool = list(pool_diag.get("suffix_top") or [])

    before_similarity = float(pool_redundancy.get("similaridade_media_entre_jogos", 0) or 0)
    after_similarity = float(final_redundancy.get("similaridade_media_entre_jogos", 0) or 0)
    diversity_before = round(max(0.0, 1.0 - before_similarity), 4) if before_similarity else None
    diversity_after = round(max(0.0, 1.0 - after_similarity), 4) if after_similarity else None

    return {
        "available": bool(pool_diag or fill_diag or final_redundancy),
        "pool_bruto_tamanho": _safe_int(fill_diag.get("candidate_pool_generated")),
        "candidatos_validos": _safe_int(fill_diag.get("valid_candidates_found") or context.get("valid_candidates_found")),
        "jogos_aceitos": _safe_int(context.get("accepted_games") or len(cards)),
        "pool_calibracao_tamanho": pool_cards_count,
        "similaridade_media_pool": before_similarity if before_similarity else None,
        "similaridade_media_final": after_similarity if after_similarity else None,
        "diversidade_pool": diversity_before,
        "diversidade_final": diversity_after,
        "diversidade_delta": (
            round((diversity_after or 0) - (diversity_before or 0), 4)
            if diversity_before is not None and diversity_after is not None
            else None
        ),
        "rerank_reduziu_similaridade": (
            after_similarity < before_similarity if before_similarity and after_similarity else None
        ),
        "prefix_top_pool": dominant_prefix_pool,
        "suffix_top_pool": dominant_suffix_pool,
        "calibration_applied": bool(context.get("calibration_applied")),
        "calibration_actions_count": len(list(calibration.get("actions_applied") or [])),
        "rerank_trace_samples": rerank_traces[:5],
        "fill_diagnostics": {
            "attempts_used": _safe_int(fill_diag.get("attempts_used")),
            "fill_completed": bool(fill_diag.get("fill_completed")),
        },
    }


def audit_restrictions(event_context: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """Restrições prováveis que comprimem o espaço candidato."""
    context = dict(event_context or {})
    restrictions: list[dict[str, Any]] = []
    mapping = [
        ("lei15_sovereign", bool(context.get("sovereign_generation_path")), "Geração soberana Lei 15 / CORE_002"),
        ("multidezena_core_002", bool(context.get("multidezena_subordinate_core_002")), "Expansão multidezena subordinada ao núcleo 15D"),
        ("ml_enabled", bool(context.get("ml_enabled")), "ML supervisionado ativo no rerank"),
        ("calibration_applied", bool(context.get("calibration_applied")), "Calibração supervisionada aplicada"),
        ("core_numbers", bool(context.get("núcleo_lei_15") or context.get("core_numbers")), "Núcleo 15D fixo por jogo"),
        ("reservas_auditadas", bool(context.get("reservas_auditadas")), "Reservas auditadas na expansão 17D"),
        ("redundancy_penalty", float(context.get("redundancy_penalty", 0) or 0) > 0, "Penalidade de redundância no rerank"),
        ("prefix_penalty", float(context.get("prefix_penalty", 0) or 0) > 0, "Penalidade de prefixo no rerank"),
        ("suffix_penalty", float(context.get("suffix_penalty", 0) or 0) > 0, "Penalidade de sufixo no rerank"),
    ]
    for key, active, label in mapping:
        if active:
            restrictions.append({"restricao": key, "label": label, "ativa": True})
    fill = dict(context.get("fill_diagnostics") or {})
    if fill:
        restrictions.append(
            {
                "restricao": "fill_diagnostics",
                "label": (
                    f"Pool fill: {fill.get('candidate_pool_generated', '—')} candidatos, "
                    f"{fill.get('attempts_used', '—')} tentativas"
                ),
                "ativa": True,
            }
        )
    restrictions.sort(key=lambda row: row.get("restricao") or "")
    return restrictions


def infer_root_cause(report: Mapping[str, Any]) -> dict[str, Any]:
    """Infere causa raiz provável da similaridade média alta."""
    causes: list[str] = []
    evidence: list[str] = []
    actions: list[str] = []

    prefix = dict(report.get("prefixos_sufixos") or {}).get("prefixo_mais_dominante") or {}
    suffix = dict(report.get("prefixos_sufixos") or {}).get("sufixo_mais_dominante") or {}
    base = dict(report.get("base_diversity") or {})
    expansion = dict(report.get("expansao_17d") or {})
    coverage = dict(report.get("cobertura_dezenas") or {})
    redundancy = dict(report.get("redundancia") or {})

    if prefix.get("level") in {"alto", "critico"}:
        causes.append("prefixo_dominante")
        evidence.append(
            f"Prefixo {prefix.get('estrutura')} em {prefix.get('frequencia')}/{prefix.get('total')} jogos "
            f"({prefix.get('share_pct')}%)"
        )
        actions.append(
            f"Limitar prefixo dominante {prefix.get('estrutura')} a no máximo "
            f"{DOMINANCE_ACCEPTABLE_MAX_COUNT}/{prefix.get('total')} jogos"
        )
    if suffix.get("level") in {"alto", "critico"}:
        causes.append("sufixo_dominante")
        evidence.append(
            f"Sufixo {suffix.get('estrutura')} em {suffix.get('frequencia')}/{suffix.get('total')} jogos"
        )
        actions.append("Diversificar sufixos na expansão 17D e no rerank")

    if base.get("base_excede_20pct"):
        dominant = dict(base.get("base_mais_dominante") or {})
        causes.append("baixa_diversidade_bases")
        evidence.append(f"Base estrutural {dominant.get('base', '—')[:24]}… gera {dominant.get('jogos')} jogos")
        actions.append("Diversificar núcleos 15D antes da expansão 17D")

    if expansion.get("nucleo_repetido_excessivo") or expansion.get("par_adicionado_repetido"):
        causes.append("expansao_17d_concentrada")
        top_nucleo = (expansion.get("top_nucleos_15d") or [{}])[0]
        top_par = (expansion.get("top_pares_adicionados") or [{}])[0]
        evidence.append(
            f"Núcleo {top_nucleo.get('nucleo', '—')} → {top_nucleo.get('jogos', 0)} jogos; "
            f"par adicionado {top_par.get('expansao', '—')} → {top_par.get('jogos', 0)} jogos"
        )
        actions.append("Rotacionar pares de dezenas adicionadas e núcleos 15D na expansão")

    sub_count = _safe_int(coverage.get("subcobertura_count"))
    if sub_count >= 3:
        causes.append("dezenas_subcobertas")
        evidence.append(f"{sub_count} dezenas subcobertas no lote")
        actions.append("Reforçar dezenas subcobertas sem concentrar prefixos/sufixos")

    pool = dict(report.get("pool_diversity") or {})
    if pool.get("rerank_reduziu_similaridade") is False:
        causes.append("rerank_manteve_concentracao")
        evidence.append("Rerank ML não reduziu similaridade média do pool")
        actions.append("Revisar pesos de diversidade vs score ML no rerank supervisionado")

    if not causes:
        sim = float(redundancy.get("similaridade_media_entre_jogos", 0) or 0)
        if sim >= 0.65:
            causes.append("concentracao_estrutural_geral")
            evidence.append(f"Similaridade média {sim:.4f} sem dominância extrema isolada")
            actions.append("Combinar diversidade de prefixo, base e expansão 17D na próxima calibração")

    primary = causes[0] if causes else "sem_concentracao_extrema"
    return {
        "problema_detectado": primary,
        "causas_provaveis": causes,
        "evidencias": evidence,
        "acoes_recomendadas": actions,
        "impacto": (
            "Aumenta similaridade média e reduz diversidade mesmo sem clones críticos (M-ML-067)."
            if causes
            else "Concentração dentro dos limiares auditados."
        ),
    }


def audit_structural_concentration(
    games: Sequence[Mapping[str, Any]],
    *,
    game_size: int,
    event_context: Mapping[str, Any] | None = None,
    official_cards: Sequence[Sequence[int]] | None = None,
    generation_event_id: int | None = None,
) -> dict[str, Any]:
    """Auditoria completa de concentração estrutural (read-only)."""
    cards = [resolve_cartao_final_from_game(dict(game)) for game in games]
    cards = [card for card in cards if card]
    total_games = len(cards)
    redundancy = compute_gp_redundancy(cards, game_size=int(game_size)) if total_games >= 2 else {}
    similarity = float(redundancy.get("similaridade_media_entre_jogos", 0) or 0)
    diversity_score = round(max(0.0, 1.0 - similarity), 4)
    similarity_band = classify_similarity_for_format(similarity, int(game_size))

    prefix_suffix = audit_prefix_suffix_concentration(
        cards,
        total_games=total_games,
        official_cards=official_cards,
    )
    coverage = audit_dezena_coverage(cards, game_size=int(game_size), total_games=total_games)
    base_diversity = audit_base_diversity(games, total_games=total_games)
    expansion = audit_17d_expansion(games) if int(game_size) == 17 else {"available": False}
    pool = audit_pool_and_rerank(event_context, games, game_size=int(game_size))
    restrictions = audit_restrictions(event_context)

    report = {
        "mission_id": MISSION_ID,
        "generation_event_id": generation_event_id,
        "formato": f"{int(game_size)}D",
        "quantidade_jogos": total_games,
        "similaridade_media": similarity,
        "similarity_band": similarity_band,
        "diversity_score": diversity_score,
        "redundancia": redundancy,
        "prefixos_sufixos": prefix_suffix,
        "cobertura_dezenas": coverage,
        "base_diversity": base_diversity,
        "expansao_17d": expansion,
        "pool_diversity": pool,
        "restricoes_compressoras": restrictions,
    }
    report["diagnostico"] = infer_root_cause(report)
    return report


def audit_structural_concentration_from_db(
    db_path: str | Any,
    *,
    generation_event_id: int,
    game_size: int | None = None,
) -> dict[str, Any]:
    """Carrega GE do PostgreSQL e executa auditoria M-ML-068 (read-only)."""
    from pathlib import Path

    from lotoia.database.database import GeneratedGame, GenerationEvent, get_session
    from lotoia.observability.card_structure_diagnostics import _load_official_cards

    with get_session(db_path) as session:
        event = session.query(GenerationEvent).filter(GenerationEvent.id == int(generation_event_id)).one_or_none()
        if event is None:
            return {"available": False, "mission_id": MISSION_ID, "reason": "generation_event_not_found"}
        rows = (
            session.query(GeneratedGame)
            .filter(GeneratedGame.generation_event_id == int(generation_event_id))
            .order_by(GeneratedGame.game_index.asc())
            .all()
        )
        games: list[dict[str, Any]] = []
        for row in rows:
            context = dict(row.context_json or {})
            numbers = [int(number) for number in (row.numbers or [])]
            games.append(
                {
                    "numbers": numbers,
                    "final_card_numbers": list(context.get("final_card_numbers") or numbers),
                    "core_numbers": list(context.get("core_numbers") or []),
                    "audited_reserve_numbers": list(context.get("audited_reserve_numbers") or []),
                    "origin": str(getattr(row, "origin", "") or ""),
                    "profile_type": str(getattr(row, "profile_type", "") or ""),
                    "decision_trace": dict(context.get("decision_trace") or {}),
                }
            )
        official_cards, _ = _load_official_cards(session, limit=50)
        event_context = dict(getattr(event, "context_json", {}) or {})

    cards = [resolve_cartao_final_from_game(game) for game in games]
    cards = [card for card in cards if card]
    if not cards:
        return {"available": False, "mission_id": MISSION_ID, "reason": "no_cards"}
    resolved_size = int(game_size or len(cards[0]))
    report = audit_structural_concentration(
        games,
        game_size=resolved_size,
        event_context=event_context,
        official_cards=official_cards,
        generation_event_id=int(generation_event_id),
    )
    report["available"] = True
    return report
