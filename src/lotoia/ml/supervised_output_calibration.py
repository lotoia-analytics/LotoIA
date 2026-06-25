"""Motor de calibração supervisionada da saída — M-ML-054.

Subordinado ao CORE_002: ajusta score/rerank do pool sem alterar L1–L5 soberanos.
"""

from __future__ import annotations

import os
from collections import Counter
from typing import Any, Mapping, Sequence

from lotoia.config.structural_policy_config import DEFAULT_PREFIX_SHARE_LIMIT
from lotoia.ml.structural_auto_calibration import (
    MISSION_ID as STRUCTURAL_AUTO_MISSION_ID,
    build_auto_calibration_plan_from_pool,
    compute_structural_diversity_bonus,
    is_structural_auto_calibration_format,
)
from lotoia.ml.structural_policy_15d import (
    MISSION_ID as STRUCTURAL_POLICY_15D_MISSION_ID,
    build_structural_policy_15d_calibration_plan,
    ensure_structural_policy_15d_memory,
    is_structural_policy_15d_format,
    validate_game_structural_policy_15d,
)
from lotoia.governance.lei15_core_002_sovereign import core_002_batch_label_game_size
from lotoia.ml.overlap_format_thresholds import MAX_FORMAT_SIZE, MIN_FORMAT_SIZE
from lotoia.statistics.card_structure import (
    compute_gp_redundancy,
    compute_missing_dezenas,
    compute_prefix,
    compute_suffix,
    format_dezena_group,
    resolve_cartao_final_from_game,
)

MISSION_ID = "M-ML-054"
MISSION_ID_FIX_03 = "M-ML-070-FIX-03"
CALIBRATION_VERSION = "M-ML-054-v1"
CALIBRATION_ENGINE_ROLE = "SUPERVISED_OUTPUT_CALIBRATION"
ENV_OUTPUT_CALIBRATION_ENABLED = "LOTOIA_ML_OUTPUT_CALIBRATION_ENABLED"

STATUS_ACTIVE = "ML OPERACIONAL SUPERVISIONADO — CALIBRAÇÃO DE SAÍDA ATIVA"

# Dezenas críticas CORE_002 (observacional — reforço supervisionado, sem mutar Núcleo)
CRITICAL_DEZENAS: frozenset[int] = frozenset({7, 15, 23})
DEFAULT_UNDERCOVER_RATIO = 0.18
# DEFAULT_PREFIX_SHARE_LIMIT importado de lotoia.config.structural_policy_config
DEFAULT_NEAR_DUP_PAIR_RATIO = 0.28
MISSION_ID_080 = "M-ML-080"


def resolve_near_duplicate_pair_ratio(requested_count: int) -> float:
    """Limiar adaptativo de quase-clones por tamanho de lote (M-ML-080)."""
    count = max(int(requested_count or 0), 1)
    if count <= 5:
        return 0.60
    if count <= 10:
        return 0.50
    if count <= 20:
        return 0.40
    if count <= 50:
        return 0.33
    return DEFAULT_NEAR_DUP_PAIR_RATIO


DOMINANCE_CALIBRATION_THRESHOLD = 6


def is_output_calibration_enabled() -> bool:
    raw = os.getenv(ENV_OUTPUT_CALIBRATION_ENABLED, "1").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _game_card(game: Mapping[str, Any]) -> list[int]:
    return resolve_cartao_final_from_game(dict(game))


def _pool_cards(games: Sequence[Mapping[str, Any]]) -> list[list[int]]:
    return [card for card in (_game_card(game) for game in games) if card]


def _is_supported_game_size(size: int) -> bool:
    return MIN_FORMAT_SIZE <= int(size) <= MAX_FORMAT_SIZE


def resolve_pool_game_size(
    games: Sequence[Mapping[str, Any]],
    *,
    batch_label: str | None = None,
    game_size: int | None = None,
    requested_count: int | None = None,
    default: int = 15,
) -> tuple[int, dict[str, Any]]:
    """Resolve dezenas por cartão — nunca inferir formato a partir de requested_count."""
    contract: dict[str, Any] = {
        "mission_id": MISSION_ID_FIX_03,
        "requested_game_size": int(game_size) if game_size is not None else None,
        "requested_count": int(requested_count)
        if requested_count is not None
        else None,
        "contract_errors": [],
        "resolved_from": None,
    }

    label_size = core_002_batch_label_game_size(batch_label)
    cards = _pool_cards(games)
    card_sizes = {len(card) for card in cards if card}
    card_size = (
        next(iter(card_sizes))
        if len(card_sizes) == 1 and _is_supported_game_size(next(iter(card_sizes)))
        else None
    )
    if card_size is None and cards and _is_supported_game_size(len(cards[0])):
        card_size = len(cards[0])
        if len(card_sizes) > 1:
            contract["contract_errors"].append(
                "cartões com tamanhos mistos; usando primeiro cartão"
            )

    resolved: int | None = None
    if label_size is not None and _is_supported_game_size(label_size):
        resolved = int(label_size)
        contract["resolved_from"] = "batch_label"
    elif card_size is not None:
        resolved = int(card_size)
        contract["resolved_from"] = "card_numbers"

    requested_size = int(game_size) if game_size is not None else None
    requested_qty = int(requested_count) if requested_count is not None else None

    if requested_size is not None:
        if not _is_supported_game_size(requested_size):
            contract["contract_errors"].append(
                f"game_size={requested_size} fora de {MIN_FORMAT_SIZE}D–{MAX_FORMAT_SIZE}D "
                "(provável confusão com requested_count)"
            )
        elif (
            requested_qty is not None
            and requested_size == requested_qty
            and resolved is not None
            and requested_size != resolved
        ):
            contract["contract_errors"].append(
                f"game_size={requested_size} igual a requested_count; usando {resolved}D do formato/cartão"
            )
        elif resolved is None and _is_supported_game_size(requested_size):
            if requested_qty is not None and requested_size == requested_qty:
                contract["contract_errors"].append(
                    f"game_size={requested_size} igual a requested_count sem batch_label/cartão; "
                    f"usando default {default}D"
                )
                resolved = int(default)
                contract["resolved_from"] = "default_count_guard"
            else:
                resolved = requested_size
                contract["resolved_from"] = "explicit"
        elif resolved is not None and requested_size != resolved:
            contract["contract_errors"].append(
                f"game_size={requested_size} contradiz formato resolvido {resolved}D"
            )

    if resolved is None:
        resolved = int(default)
        contract["resolved_from"] = contract.get("resolved_from") or "default"

    contract["game_size"] = resolved
    return resolved, contract


def analyze_pool_structural_issues(
    games: Sequence[Mapping[str, Any]],
    *,
    game_size: int = 15,
    batch_label: str | None = None,
    requested_count: int | None = None,
) -> dict[str, Any]:
    """Diagnóstico estrutural do pool — somente leitura + detecção de problemas."""
    resolved_size, size_contract = resolve_pool_game_size(
        games,
        batch_label=batch_label,
        game_size=game_size,
        requested_count=requested_count,
    )
    cards = _pool_cards(games)
    pool_size = len(cards)
    redundancy = (
        compute_gp_redundancy(cards, game_size=int(resolved_size))
        if pool_size >= 2
        else {}
    )
    issues: list[dict[str, Any]] = []

    if pool_size < 2:
        return {
            "pool_size": pool_size,
            "game_size": int(resolved_size),
            "game_size_contract": size_contract,
            "redundancy": redundancy,
            "issues": issues,
            "issue_count": 0,
        }

    pair_count = int(
        redundancy.get("pair_count", redundancy.get("pares_possiveis", 0)) or 0
    )
    near_dup = int(
        redundancy.get(
            "quase_repetidos_criticos", redundancy.get("cartoes_quase_repetidos", 0)
        )
        or 0
    )
    near_dup_ratio = (near_dup / pair_count) if pair_count > 0 else 0.0
    near_dup_limit = (
        resolve_near_duplicate_pair_ratio(int(requested_count))
        if requested_count is not None
        else DEFAULT_NEAR_DUP_PAIR_RATIO
    )
    if near_dup_ratio >= near_dup_limit:
        issues.append(
            {
                "tipo": "quase_repetidos_alto",
                "severidade": "alta",
                "valor": near_dup,
                "limite": round(near_dup_limit * pair_count, 1),
                "descricao": (
                    f"Quase repetidos críticos elevado ({near_dup} pares overlap N/N-1, "
                    f"ratio={near_dup_ratio:.2f}, limite_lote={near_dup_limit:.2f})"
                ),
            }
        )

    avg_overlap = float(redundancy.get("sobreposicao_media", 0) or 0)
    max_overlap = int(redundancy.get("sobreposicao_maxima", 0) or 0)
    size = int(resolved_size)
    if avg_overlap >= size * 0.55:
        issues.append(
            {
                "tipo": "similaridade_media_gp_elevada",
                "severidade": "media",
                "valor": avg_overlap,
                "descricao": f"Similaridade média GP elevada ({avg_overlap:.2f})",
            }
        )
    if max_overlap >= size - 2:
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
    prefix_limit = max(
        DOMINANCE_CALIBRATION_THRESHOLD, int(pool_size * DEFAULT_PREFIX_SHARE_LIMIT)
    )
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
    lot_reference = int(requested_count or pool_size or 1)
    from lotoia.ml.ml_operational_hierarchy import resolve_min_coverage_for_count

    min_distinct_coverage = resolve_min_coverage_for_count(lot_reference)
    distinct_present = sum(
        1 for number in range(1, 26) if int(number_presence.get(number, 0)) > 0
    )
    if distinct_present < min_distinct_coverage:
        issues.append(
            {
                "tipo": "dezena_subcoberta",
                "severidade": "alta" if min_distinct_coverage >= 25 else "media",
                "valor": distinct_present,
                "limite": min_distinct_coverage,
                "descricao": (
                    f"Cobertura distinta insuficiente ({distinct_present}/{min_distinct_coverage} "
                    f"dezenas para lote {lot_reference})"
                ),
            }
        )
    elif lot_reference >= 16:
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
    else:
        for number in CRITICAL_DEZENAS:
            count = int(number_presence.get(number, 0))
            if count <= 0:
                issues.append(
                    {
                        "tipo": "dezena_critica_ausente_observacional",
                        "severidade": "observacional",
                        "dezena": number,
                        "valor": count,
                        "limite": 0,
                        "descricao": (
                            f"Dezena crítica {number:02d} ausente no lote {lot_reference} "
                            f"(diagnóstico observacional — cobertura distinta {distinct_present}/"
                            f"{min_distinct_coverage} atendida)"
                        ),
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
        "game_size": int(resolved_size),
        "game_size_contract": size_contract,
        "redundancy": redundancy,
        "issues": issues,
        "issue_count": len(issues),
        "number_presence": {str(k): v for k, v in sorted(number_presence.items())},
        "prefix_top": [
            {"estrutura": k, "frequencia": v} for k, v in prefix3.most_common(5)
        ],
        "suffix_top": [
            {"estrutura": k, "frequencia": v} for k, v in suffix3.most_common(5)
        ],
    }


def _resolve_policy_db_path(event_context: Mapping[str, Any] | None) -> Any:
    payload = dict(event_context or {})
    for key in ("db_path", "database_path", "LOTOIA_DATABASE_PATH"):
        if payload.get(key):
            return payload.get(key)
    return None


def _apply_structural_policy_15d_game_adjustment(
    game: Mapping[str, Any],
    *,
    policy: Mapping[str, Any],
    previous_contest_numbers: Sequence[int] | None,
    plan_params: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    numbers = resolve_cartao_final_from_game(dict(game))
    if not numbers:
        return {"penalty": 0.0, "boost": 0.0, "actions": []}
    validation = validate_game_structural_policy_15d(
        numbers,
        previous_contest_numbers=previous_contest_numbers,
        policy=policy,
    )
    actions: list[str] = []
    penalty = 0.0
    boost = 0.0
    params = dict(plan_params or {})

    for violation in list(validation.get("violations") or []):
        token = str(violation)
        if token.startswith("repeticao"):
            delta = 0.18 * float(params.get("repeat_penalty_boost", 1.0) or 1.0)
            penalty += delta
            actions.append(f"penalidade_politica_repeticao={delta:.3f}")
        elif token.startswith("paridade"):
            delta = 0.14 * float(params.get("parity_penalty_boost", 1.0) or 1.0)
            penalty += delta
            actions.append(f"penalidade_politica_paridade={delta:.3f}")
        elif token.startswith("sequencia"):
            delta = 0.16 * float(params.get("sequence_penalty_boost", 1.0) or 1.0)
            penalty += delta
            actions.append(f"penalidade_politica_sequencia={delta:.3f}")

    core_numbers = {int(value) for value in list(policy.get("core_numbers") or [])}
    discouraged_numbers = {
        int(value) for value in list(policy.get("discouraged_numbers") or [])
    }
    card_set = set(numbers)
    core_present = card_set & core_numbers
    discouraged_present = card_set & discouraged_numbers
    if len(core_present) < 2:
        delta = 0.12 * float(params.get("core_numbers_boost", 1.0) or 1.0)
        missing_core = sorted(core_numbers - card_set)
        if missing_core:
            boost += delta
            actions.append(f"reforco_core_numbers={delta:.3f}")
    if len(discouraged_present) > 3:
        delta = (
            0.1
            * float(params.get("discourage_penalty_boost", 1.0) or 1.0)
            * (len(discouraged_present) - 3)
        )
        penalty += delta
        actions.append(f"penalidade_discouraged_numbers={delta:.3f}")

    return {
        "penalty": round(penalty, 4),
        "boost": round(boost, 4),
        "actions": actions,
        "validation": validation,
    }


def _plan_scale(
    params: Mapping[str, Any] | None, key: str, default: float = 1.0
) -> float:
    if not isinstance(params, Mapping):
        return default
    try:
        return float(params.get(key, default) or default)
    except (TypeError, ValueError):
        return default


def _compute_game_calibration_adjustment(
    game: dict[str, Any],
    *,
    diagnostics: Mapping[str, Any],
    pool_size: int,
    all_cards: Sequence[list[int]],
    plan_params: Mapping[str, Any] | None = None,
    game_size: int = 15,
    policy_15d: Mapping[str, Any] | None = None,
    previous_contest_numbers: Sequence[int] | None = None,
) -> dict[str, Any]:
    card = _game_card(game)
    if not card:
        return {"penalty": 0.0, "boost": 0.0, "actions": [], "status": "skipped"}

    card_set = set(card)
    actions: list[str] = []
    penalty = 0.0
    boost = 0.0
    size = int(game_size or diagnostics.get("game_size") or len(card) or 15)

    overlaps: list[int] = []
    card_key = tuple(card)
    for other in all_cards:
        if tuple(other) == card_key:
            continue
        overlaps.append(len(card_set & set(other)))
    if overlaps:
        avg_overlap = sum(overlaps) / len(overlaps)
        overlap_threshold = max(10.0, size * 0.58)
        if avg_overlap >= overlap_threshold:
            delta = (avg_overlap - (overlap_threshold - 1.0)) * 0.35
            delta *= _plan_scale(plan_params, "redundancy_penalty_boost")
            delta *= _plan_scale(plan_params, "max_overlap_penalty")
            penalty += delta
            actions.append(f"penalidade_redundancia_media={delta:.3f}")
        max_overlap = max(overlaps)
        critical_overlap = max(size - 1, 13)
        if max_overlap >= critical_overlap:
            overlap_delta = (
                (max_overlap - (size - 2))
                * 0.25
                * _plan_scale(plan_params, "max_overlap_penalty")
            )
            penalty += max(overlap_delta, 0.0)
            actions.append(f"penalidade_overlap_maximo={overlap_delta:.3f}")

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
        prefix_scale = _plan_scale(plan_params, "prefix_penalty")
        penalty += 1.2 * prefix_scale
        actions.append(f"penalidade_prefixo_excessivo={prefix3}")
    elif plan_params and str(plan_params.get("prefixo_alvo") or "") == prefix3:
        prefix_scale = _plan_scale(plan_params, "prefix_penalty")
        penalty += 1.0 * prefix_scale
        actions.append(f"penalidade_prefixo_autorizado={prefix3}")
    elif (
        plan_params
        and str(plan_params.get("prefixo_alvo") or "")
        and prefix3 != str(plan_params.get("prefixo_alvo"))
    ):
        boost += 0.25 * _plan_scale(plan_params, "diversity_floor_boost")
        actions.append(f"reforco_prefixo_alternativo={prefix3}")
    if suffix3 in excessive_suffixes:
        suffix_scale = _plan_scale(plan_params, "suffix_penalty")
        penalty += 1.0 * suffix_scale
        actions.append(f"penalidade_sufixo_excessivo={suffix3}")
    elif plan_params and str(plan_params.get("sufixo_alvo") or "") == suffix3:
        suffix_scale = _plan_scale(plan_params, "suffix_penalty")
        penalty += 0.9 * suffix_scale
        actions.append(f"penalidade_sufixo_autorizado={suffix3}")
    elif (
        plan_params
        and str(plan_params.get("sufixo_alvo") or "")
        and suffix3 != str(plan_params.get("sufixo_alvo"))
    ):
        boost += 0.2 * _plan_scale(plan_params, "diversity_floor_boost")
        actions.append(f"reforco_sufixo_alternativo={suffix3}")

    number_presence = diagnostics.get("number_presence") or {}
    authorized_subcovered = {
        int(str(value).lstrip("0") or "0")
        for value in list((plan_params or {}).get("dezenas_subcobertas") or [])
        if str(value).strip().isdigit()
    }
    missing_boost_scale = _plan_scale(plan_params, "missing_numbers_boost")
    critical_boost_scale = _plan_scale(plan_params, "critical_coverage_boost")
    for issue in diagnostics.get("issues", []):
        if issue.get("tipo") != "dezena_subcoberta":
            continue
        number = int(issue.get("dezena", 0) or 0)
        if number in card_set:
            weight = (0.9 if number in CRITICAL_DEZENAS else 0.45) * missing_boost_scale
            if number in CRITICAL_DEZENAS:
                weight *= critical_boost_scale
            if authorized_subcovered and number not in authorized_subcovered:
                continue
            boost += weight
            actions.append(f"reforco_dezena_{number:02d}={weight:.2f}")

    excessive_dezenas = {
        int(str(value).lstrip("0") or "0")
        for value in list((plan_params or {}).get("dezenas_excessivas") or [])
        if str(value).strip().isdigit()
    }
    if excessive_dezenas:
        overlap_count = sum(1 for number in card_set if number in excessive_dezenas)
        if overlap_count >= 2:
            excess_penalty = (
                0.18
                * overlap_count
                * _plan_scale(plan_params, "redundancy_penalty_boost")
            )
            penalty += excess_penalty
            actions.append(f"penalidade_dezenas_excessivas={excess_penalty:.3f}")

    diversity_scale = _plan_scale(plan_params, "diversity_floor_boost")
    structural_weight = _plan_scale(plan_params, "structural_diversity_weight")
    if structural_weight > 1.0 or diversity_scale > 1.0:
        diversity_bonus = compute_structural_diversity_bonus(
            game,
            diagnostics=diagnostics,
            pool_size=pool_size,
            dominant_prefix=str((plan_params or {}).get("prefixo_alvo") or ""),
            dominant_suffix=str((plan_params or {}).get("sufixo_alvo") or ""),
        )
        if diversity_bonus > 0:
            weighted = diversity_bonus * max(structural_weight, diversity_scale)
            boost += weighted
            actions.append(f"reforco_diversidade_estrutural={weighted:.3f}")

    near_dup_scale = _plan_scale(plan_params, "near_duplicate_penalty")
    near_dup_threshold = max(size - 1, 12)
    if near_dup_scale > 1.0 and overlaps and max(overlaps) >= near_dup_threshold:
        near_dup_delta = 0.4 * near_dup_scale
        penalty += near_dup_delta
        actions.append(f"penalidade_quase_repetido={near_dup_delta:.3f}")

    score_ml = float(game.get("score_ml", 0) or 0)
    ml_factor = min(max(score_ml / 100.0, 0.0), 1.0) * 0.15
    boost += ml_factor

    if is_structural_policy_15d_format(size) and policy_15d:
        policy_adjustment = _apply_structural_policy_15d_game_adjustment(
            game,
            policy=policy_15d,
            previous_contest_numbers=previous_contest_numbers,
            plan_params=plan_params,
        )
        penalty += float(policy_adjustment.get("penalty", 0) or 0)
        boost += float(policy_adjustment.get("boost", 0) or 0)
        actions.extend(list(policy_adjustment.get("actions") or []))

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
    calibration_plan: Mapping[str, Any] | None = None,
    event_context: Mapping[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Aplica calibração supervisionada no pool antes de compose_sovereign_gp."""
    empty_bundle = {
        "mission_id": MISSION_ID,
        "calibration_applied": False,
        "calibration_version": CALIBRATION_VERSION,
        "calibration_engine_role": "DISABLED",
        "status": "inactive",
    }
    plan = dict(calibration_plan or {})
    plan_params = dict(plan.get("parametros_sugeridos") or {})
    plan_authorized = bool(plan.get("authorized"))
    context_payload = dict(event_context or {})
    batch_label = context_payload.get("batch_label") or context_payload.get(
        "analysis_batch_label"
    )
    requested_count = context_payload.get("requested_count") or context_payload.get(
        "selected_quantity"
    )
    resolved_size, size_contract = resolve_pool_game_size(
        games,
        batch_label=str(batch_label) if batch_label else None,
        game_size=game_size,
        requested_count=int(requested_count) if requested_count is not None else None,
    )
    size = int(resolved_size)

    auto_plan: dict[str, Any] = {}
    policy_15d: dict[str, Any] = {}
    policy_15d_plan: dict[str, Any] = {}
    previous_contest_numbers: list[int] = []
    if is_structural_auto_calibration_format(size):
        auto_plan = build_auto_calibration_plan_from_pool(
            games,
            game_size=size,
            event_context=event_context,
        )
        if auto_plan.get("auto_structural_calibration") and auto_plan.get(
            "parametros_sugeridos"
        ):
            for key, value in dict(auto_plan.get("parametros_sugeridos") or {}).items():
                plan_params.setdefault(key, value)
            plan_authorized = plan_authorized or bool(auto_plan.get("authorized"))

    if is_structural_policy_15d_format(size):
        db_path = _resolve_policy_db_path(event_context)
        policy_15d = (
            ensure_structural_policy_15d_memory(db_path)
            if db_path
            else ensure_structural_policy_15d_memory()
        )
        previous_contest_numbers = list(
            context_payload.get("previous_contest_numbers") or []
        )
        bundle_ctx = dict(context_payload.get("structural_policy_15d_bundle") or {})
        if not previous_contest_numbers:
            previous_contest_numbers = list(
                bundle_ctx.get("previous_contest_numbers") or []
            )
        policy_15d_plan = build_structural_policy_15d_calibration_plan(
            bundle_ctx or {"violations": list(bundle_ctx.get("violated_rules") or [])},
            policy_15d,
        )
        if policy_15d_plan.get("parametros_sugeridos"):
            for key, value in dict(
                policy_15d_plan.get("parametros_sugeridos") or {}
            ).items():
                plan_params.setdefault(key, value)
            if policy_15d_plan.get("has_plan"):
                plan_authorized = True

    if not ml_enabled or not is_output_calibration_enabled() or not games:
        return games, empty_bundle

    diagnostics = analyze_pool_structural_issues(
        games,
        game_size=size,
        batch_label=str(batch_label) if batch_label else None,
        requested_count=int(requested_count) if requested_count is not None else None,
    )
    all_cards = _pool_cards(games)
    pool_size = len(all_cards)
    if pool_size == 0:
        return games, empty_bundle

    effective_params = (
        plan_params
        if plan_authorized or auto_plan.get("auto_structural_calibration")
        else None
    )

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
            plan_params=effective_params,
            game_size=size,
            policy_15d=policy_15d or None,
            previous_contest_numbers=previous_contest_numbers or None,
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
        actions_summary.extend(
            enrichment for enrichment in enriched["ml_calibration_actions"]
        )
        penalties.append(float(adjustment.get("penalty", 0) or 0))
        boosts.append(float(adjustment.get("boost", 0) or 0))
        status_counts[str(adjustment.get("status", "moderado"))] += 1
        calibrated.append(enriched)

    structural_weight = float(
        (effective_params or {}).get("structural_diversity_weight", 1.0) or 1.0
    )
    calibrated.sort(
        key=lambda row: (
            -float(row.get("profile_score", 0) or 0),
            -compute_structural_diversity_bonus(
                row,
                diagnostics=diagnostics,
                pool_size=pool_size,
                dominant_prefix=str((effective_params or {}).get("prefixo_alvo") or ""),
                dominant_suffix=str((effective_params or {}).get("sufixo_alvo") or ""),
            )
            * structural_weight,
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
            1.0
            - float(redundancy_before.get("similaridade_media_entre_jogos", 0) or 0),
            4,
        ),
        "final_ml_score_avg": round(
            sum(float(row.get("score_ml", 0) or 0) for row in calibrated)
            / max(len(calibrated), 1),
            4,
        ),
        "batch_status_counts": dict(status_counts),
        "pool_size": pool_size,
        "game_size": size,
        "game_size_contract": size_contract,
        "lei15_core_002_preserved": True,
        "lei15a_applied": False,
    }
    if auto_plan.get("auto_structural_calibration"):
        bundle["structural_auto_calibration_mission_id"] = STRUCTURAL_AUTO_MISSION_ID
        bundle["structural_auto_calibration_plan"] = auto_plan
        bundle["structural_calibration_memory"] = dict(
            auto_plan.get("structural_calibration_memory") or {}
        )
        bundle["structural_actions_applied"] = list(
            auto_plan.get("structural_actions") or []
        )
    if plan_authorized:
        bundle["authorized_calibration_plan"] = {
            "mission_id": plan.get("mission_id"),
            "plan_items": list(plan.get("plan_items") or []),
            "impact_items": list(plan.get("impact_items") or []),
            "parametros_sugeridos": plan_params,
            "trace": dict(plan.get("trace") or {}),
            "operador": plan.get("operador"),
            "timestamp": plan.get("timestamp"),
        }
    if policy_15d_plan.get("has_plan"):
        bundle["structural_policy_15d_mission_id"] = STRUCTURAL_POLICY_15D_MISSION_ID
        bundle["structural_policy_15d_calibration_plan"] = policy_15d_plan
        bundle["structural_policy_15d_actions"] = [
            action
            for row in calibrated
            for action in list(row.get("ml_calibration_actions") or [])
            if "politica" in str(action)
            or "core_numbers" in str(action)
            or "discouraged" in str(action)
        ]
        bundle["structural_policy_memory_loaded"] = True
        bundle["structural_policy_version"] = policy_15d.get("policy_version")
        bundle["structural_policy_applied"] = bool(previous_contest_numbers)
    return calibrated, bundle
