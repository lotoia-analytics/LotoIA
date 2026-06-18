"""Motor de calibração supervisionada da saída — M-ML-054.

Subordinado ao CORE_002: ajusta score/rerank do pool sem alterar L1–L5 soberanos.
"""

from __future__ import annotations

import os
from collections import Counter
from typing import Any, Mapping, Sequence

from lotoia.statistics.card_structure import (
    compute_gp_redundancy,
    compute_missing_dezenas,
    compute_prefix,
    compute_suffix,
    format_dezena_group,
    resolve_cartao_final_from_game,
)

MISSION_ID = "M-ML-054"
CALIBRATION_VERSION = "M-ML-054-v1"
CALIBRATION_ENGINE_ROLE = "SUPERVISED_OUTPUT_CALIBRATION"
ENV_OUTPUT_CALIBRATION_ENABLED = "LOTOIA_ML_OUTPUT_CALIBRATION_ENABLED"

STATUS_ACTIVE = "ML OPERACIONAL SUPERVISIONADO — CALIBRAÇÃO DE SAÍDA ATIVA"

# Dezenas críticas CORE_002 (observacional — reforço supervisionado, sem mutar Núcleo)
CRITICAL_DEZENAS: frozenset[int] = frozenset({7, 15, 23})
DEFAULT_UNDERCOVER_RATIO = 0.18
DEFAULT_PREFIX_SHARE_LIMIT = 0.14
DEFAULT_NEAR_DUP_PAIR_RATIO = 0.28


def is_output_calibration_enabled() -> bool:
    raw = os.getenv(ENV_OUTPUT_CALIBRATION_ENABLED, "1").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _game_card(game: Mapping[str, Any]) -> list[int]:
    return resolve_cartao_final_from_game(dict(game))


def _pool_cards(games: Sequence[Mapping[str, Any]]) -> list[list[int]]:
    return [card for card in (_game_card(game) for game in games) if card]


def analyze_pool_structural_issues(
    games: Sequence[Mapping[str, Any]],
    *,
    game_size: int = 15,
) -> dict[str, Any]:
    """Diagnóstico estrutural do pool — somente leitura + detecção de problemas."""
    cards = _pool_cards(games)
    pool_size = len(cards)
    redundancy = compute_gp_redundancy(cards) if pool_size >= 2 else {}
    issues: list[dict[str, Any]] = []

    if pool_size < 2:
        return {
            "pool_size": pool_size,
            "game_size": int(game_size),
            "redundancy": redundancy,
            "issues": issues,
            "issue_count": 0,
        }

    pair_count = int(redundancy.get("pair_count", 0) or 0)
    near_dup = int(redundancy.get("cartoes_quase_repetidos", 0) or 0)
    near_dup_ratio = (near_dup / pair_count) if pair_count > 0 else 0.0
    if near_dup_ratio >= DEFAULT_NEAR_DUP_PAIR_RATIO:
        issues.append(
            {
                "tipo": "quase_repetidos_alto",
                "severidade": "alta",
                "valor": near_dup,
                "limite": round(DEFAULT_NEAR_DUP_PAIR_RATIO * pair_count, 1),
                "descricao": f"Quase repetidos elevado ({near_dup} pares, ratio={near_dup_ratio:.2f})",
            }
        )

    avg_overlap = float(redundancy.get("sobreposicao_media", 0) or 0)
    max_overlap = int(redundancy.get("sobreposicao_maxima", 0) or 0)
    if avg_overlap >= game_size * 0.55:
        issues.append(
            {
                "tipo": "similaridade_media_gp_elevada",
                "severidade": "media",
                "valor": avg_overlap,
                "descricao": f"Similaridade média GP elevada ({avg_overlap:.2f})",
            }
        )
    if max_overlap >= game_size - 2:
        issues.append(
            {
                "tipo": "sobreposicao_maxima_elevada",
                "severidade": "alta",
                "valor": max_overlap,
                "descricao": f"Sobreposição máxima elevada ({max_overlap})",
            }
        )

    prefix3 = Counter(format_dezena_group(compute_prefix(card, 3)) for card in cards)
    suffix3 = Counter(format_dezena_group(compute_suffix(card, 3)) for card in cards)
    prefix_limit = max(3, int(pool_size * DEFAULT_PREFIX_SHARE_LIMIT))
    for prefix, count in prefix3.most_common(8):
        if count >= prefix_limit:
            issues.append(
                {
                    "tipo": "prefixo_excessivo",
                    "severidade": "media",
                    "estrutura": prefix,
                    "valor": count,
                    "limite": prefix_limit,
                    "descricao": f"Prefixo {prefix} excessivo ({count}/{pool_size})",
                }
            )
    for suffix, count in suffix3.most_common(8):
        if count >= prefix_limit:
            issues.append(
                {
                    "tipo": "sufixo_excessivo",
                    "severidade": "media",
                    "estrutura": suffix,
                    "valor": count,
                    "limite": prefix_limit,
                    "descricao": f"Sufixo {suffix} excessivo ({count}/{pool_size})",
                }
            )

    number_presence = Counter(number for card in cards for number in card)
    min_expected = max(1, int(pool_size * DEFAULT_UNDERCOVER_RATIO))
    for number in range(1, 26):
        count = int(number_presence.get(number, 0))
        if count < min_expected:
            issues.append(
                {
                    "tipo": "dezena_subcoberta",
                    "severidade": "alta" if number in CRITICAL_DEZENAS else "media",
                    "dezena": number,
                    "valor": count,
                    "limite": min_expected,
                    "descricao": f"Dezena {number:02d} subcoberta ({count}/{pool_size})",
                }
            )

    missing_patterns = Counter(
        format_dezena_group(compute_missing_dezenas(card)) for card in cards if card
    )
    for pattern, count in missing_patterns.most_common(3):
        if count >= max(2, pool_size // 4):
            issues.append(
                {
                    "tipo": "padrao_ausencia_recorrente",
                    "severidade": "media",
                    "ausencias": pattern,
                    "valor": count,
                    "descricao": f"Padrão de ausência recorrente: {pattern}",
                }
            )

    return {
        "pool_size": pool_size,
        "game_size": int(game_size),
        "redundancy": redundancy,
        "issues": issues,
        "issue_count": len(issues),
        "number_presence": {str(k): v for k, v in sorted(number_presence.items())},
        "prefix_top": [{"estrutura": k, "frequencia": v} for k, v in prefix3.most_common(5)],
        "suffix_top": [{"estrutura": k, "frequencia": v} for k, v in suffix3.most_common(5)],
    }


def _compute_game_calibration_adjustment(
    game: dict[str, Any],
    *,
    diagnostics: Mapping[str, Any],
    pool_size: int,
    all_cards: Sequence[list[int]],
) -> dict[str, Any]:
    card = _game_card(game)
    if not card:
        return {"penalty": 0.0, "boost": 0.0, "actions": [], "status": "skipped"}

    card_set = set(card)
    actions: list[str] = []
    penalty = 0.0
    boost = 0.0

    overlaps: list[int] = []
    card_key = tuple(card)
    for other in all_cards:
        if tuple(other) == card_key:
            continue
        overlaps.append(len(card_set & set(other)))
    if overlaps:
        avg_overlap = sum(overlaps) / len(overlaps)
        if avg_overlap >= 10:
            delta = (avg_overlap - 9.0) * 0.35
            penalty += delta
            actions.append(f"penalidade_redundancia_media={delta:.3f}")

    prefix3 = format_dezena_group(compute_prefix(card, 3))
    suffix3 = format_dezena_group(compute_suffix(card, 3))
    excessive_prefixes = {
        row.get("estrutura")
        for row in diagnostics.get("issues", [])
        if row.get("tipo") == "prefixo_excessivo"
    }
    excessive_suffixes = {
        row.get("estrutura")
        for row in diagnostics.get("issues", [])
        if row.get("tipo") == "sufixo_excessivo"
    }
    if prefix3 in excessive_prefixes:
        penalty += 1.2
        actions.append(f"penalidade_prefixo_excessivo={prefix3}")
    if suffix3 in excessive_suffixes:
        penalty += 1.0
        actions.append(f"penalidade_sufixo_excessivo={suffix3}")

    number_presence = diagnostics.get("number_presence") or {}
    for issue in diagnostics.get("issues", []):
        if issue.get("tipo") != "dezena_subcoberta":
            continue
        number = int(issue.get("dezena", 0) or 0)
        if number in card_set:
            weight = 0.9 if number in CRITICAL_DEZENAS else 0.45
            boost += weight
            actions.append(f"reforco_dezena_{number:02d}={weight:.2f}")

    score_ml = float(game.get("score_ml", 0) or 0)
    ml_factor = min(max(score_ml / 100.0, 0.0), 1.0) * 0.15
    boost += ml_factor

    status = "moderado"
    if penalty >= 2.5:
        status = "reprovado"
    elif penalty <= 0.5 and boost >= 1.0:
        status = "aprovado"

    return {
        "penalty": round(penalty, 4),
        "boost": round(boost, 4),
        "net_adjustment": round(boost - penalty, 4),
        "actions": actions,
        "status": status,
        "prefix_3": prefix3,
        "suffix_3": suffix3,
        "avg_overlap": round(sum(overlaps) / len(overlaps), 4) if overlaps else 0.0,
        "number_presence_snapshot": dict(number_presence),
    }


def apply_supervised_output_calibration(
    games: list[dict[str, Any]],
    *,
    game_size: int = 15,
    ml_enabled: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Aplica calibração supervisionada no pool antes de compose_sovereign_gp."""
    empty_bundle = {
        "mission_id": MISSION_ID,
        "calibration_applied": False,
        "calibration_version": CALIBRATION_VERSION,
        "calibration_engine_role": "DISABLED",
        "status": "inactive",
    }
    if not ml_enabled or not is_output_calibration_enabled() or not games:
        return games, empty_bundle

    diagnostics = analyze_pool_structural_issues(games, game_size=game_size)
    all_cards = _pool_cards(games)
    pool_size = len(all_cards)
    if pool_size == 0:
        return games, empty_bundle

    calibrated: list[dict[str, Any]] = []
    actions_summary: list[str] = []
    penalties: list[float] = []
    boosts: list[float] = []
    status_counts: Counter[str] = Counter()

    for game in games:
        enriched = dict(game)
        adjustment = _compute_game_calibration_adjustment(
            enriched,
            diagnostics=diagnostics,
            pool_size=pool_size,
            all_cards=all_cards,
        )
        base_profile = float(enriched.get("profile_score", 0) or 0)
        net = float(adjustment.get("net_adjustment", 0) or 0)
        enriched["ml_calibration_penalty"] = adjustment.get("penalty", 0.0)
        enriched["ml_calibration_boost"] = adjustment.get("boost", 0.0)
        enriched["ml_calibration_net"] = net
        enriched["ml_calibration_status"] = adjustment.get("status", "moderado")
        enriched["ml_calibration_actions"] = list(adjustment.get("actions") or [])
        enriched["profile_score"] = round(max(0.0, base_profile + net), 4)
        enriched["calibration_applied"] = True

        details = dict(enriched.get("score_ml_details") or {})
        details["calibration"] = {
            "status": "active",
            "calibration_version": CALIBRATION_VERSION,
            "mission_id": MISSION_ID,
            "penalty": adjustment.get("penalty"),
            "boost": adjustment.get("boost"),
            "net_adjustment": net,
            "actions": adjustment.get("actions"),
            "calibration_status": adjustment.get("status"),
        }
        enriched["score_ml_details"] = details
        actions_summary.extend(enrichment for enrichment in enriched["ml_calibration_actions"])
        penalties.append(float(adjustment.get("penalty", 0) or 0))
        boosts.append(float(adjustment.get("boost", 0) or 0))
        status_counts[str(adjustment.get("status", "moderado"))] += 1
        calibrated.append(enriched)

    calibrated.sort(
        key=lambda row: (
            -float(row.get("profile_score", 0) or 0),
            -float(row.get("score_ml", 0) or 0),
            -float((row.get("final_score") or {}).get("final_score", 0) or 0),
            tuple(row.get("numbers") or ()),
        )
    )

    redundancy_before = diagnostics.get("redundancy") or {}
    bundle = {
        "mission_id": MISSION_ID,
        "calibration_applied": True,
        "calibration_version": CALIBRATION_VERSION,
        "calibration_engine_role": CALIBRATION_ENGINE_ROLE,
        "ml_operational_status": STATUS_ACTIVE,
        "status": "active",
        "diagnostics": diagnostics,
        "actions_applied": sorted(set(actions_summary))[:40],
        "redundancy_penalty": round(sum(penalties), 4),
        "prefix_penalty": sum(
            1 for action in actions_summary if action.startswith("penalidade_prefixo")
        ),
        "suffix_penalty": sum(
            1 for action in actions_summary if action.startswith("penalidade_sufixo")
        ),
        "missing_numbers_boost": sum(
            1 for action in actions_summary if action.startswith("reforco_dezena")
        ),
        "critical_coverage_boost": sum(
            1
            for action in actions_summary
            if action.startswith("reforco_dezena_07")
            or action.startswith("reforco_dezena_15")
            or action.startswith("reforco_dezena_23")
        ),
        "diversity_score": round(
            1.0 - float(redundancy_before.get("similaridade_media_entre_jogos", 0) or 0),
            4,
        ),
        "final_ml_score_avg": round(
            sum(float(row.get("score_ml", 0) or 0) for row in calibrated) / max(len(calibrated), 1),
            4,
        ),
        "batch_status_counts": dict(status_counts),
        "pool_size": pool_size,
        "game_size": int(game_size),
        "lei15_core_002_preserved": True,
        "lei15a_applied": False,
    }
    return calibrated, bundle
