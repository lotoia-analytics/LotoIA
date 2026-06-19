"""Auditoria read-only da eficácia da remediação de diversidade M-ML-073 — M-STAT-001."""

from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from typing import Any, Iterator, Mapping, Sequence

from lotoia.governance.institutional_agent_routing_matrix import (
    AGENT_ESTATISTICO,
    MISSION_ID as AGENT_ROUTING_MISSION_ID,
    resolve_agent_routing,
)
from lotoia.ml.ml_operational_hierarchy import (
    STAGE_DIVERSITY,
    _apply_pool_remediation,
    _evaluate_diversity_stage,
    _pool_candidate_slice,
    _remediate_pool_for_stage,
)
from lotoia.ml.overlap_format_thresholds import DIVERSITY_LOW_THRESHOLD
from lotoia.ml.pre_final_pool_ml_calibration import _game_signature, _metric_snapshot
from lotoia.ml.structural_pool_15d_generator import build_ml_structural_15d_pool
from lotoia.ml.supervised_output_calibration import analyze_pool_structural_issues
from lotoia.statistics.card_structure import (
    compute_prefix,
    compute_suffix,
    format_dezena_group,
    resolve_cartao_final_from_game,
)

MISSION_ID = "M-STAT-001"
AUDIT_VERSION = "M-STAT-001-v1"
DEFAULT_AUDIT_POLICY: dict[str, Any] = {
    "policy_version": "M-ML-070-v1",
    "core_numbers": [7, 12, 16, 23],
    "discouraged_numbers": [2, 4, 11, 15, 24, 25],
}


@contextmanager
def audit_runtime_isolation() -> Iterator[None]:
    """Isola auditoria read-only de PostgreSQL (Lei No 001)."""
    from unittest.mock import patch

    with (
        patch(
            "lotoia.ml.supervised_output_calibration.ensure_structural_policy_15d_memory",
            lambda db_path=None: dict(DEFAULT_AUDIT_POLICY),
        ),
        patch(
            "lotoia.ml.structural_pool_15d_generator.build_structural_policy_15d_memory",
            lambda: dict(DEFAULT_AUDIT_POLICY),
        ),
        patch(
            "lotoia.ml.supervised_output_calibration.build_structural_policy_15d_calibration_plan",
            lambda bundle, policy_payload: {"has_plan": False, "parametros_sugeridos": {}},
        ),
    ):
        yield


def _safe_delta(after: float, before: float) -> dict[str, float]:
    before_value = float(before or 0.0)
    after_value = float(after or 0.0)
    delta = round(after_value - before_value, 4)
    pct = round((delta / before_value) * 100, 2) if before_value else 0.0
    return {"absolute": delta, "percent": pct}


def _dominance_rows(diagnostics: Mapping[str, Any], pool_size: int) -> dict[str, Any]:
    issues = list(diagnostics.get("issues") or [])
    prefix_issue = next((row for row in issues if row.get("tipo") == "prefixo_excessivo"), {})
    suffix_issue = next((row for row in issues if row.get("tipo") == "sufixo_excessivo"), {})
    redundancy = dict(diagnostics.get("redundancy") or {})
    return {
        "prefix_top": list(redundancy.get("prefix_top") or [])[:5],
        "suffix_top": list(redundancy.get("suffix_top") or [])[:5],
        "prefix_excessivo": dict(prefix_issue),
        "suffix_excessivo": dict(suffix_issue),
        "pool_size": int(pool_size),
    }


def _structural_families(pool: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    families: Counter[str] = Counter()
    for game in pool:
        card = resolve_cartao_final_from_game(dict(game))
        if not card:
            continue
        prefix = format_dezena_group(compute_prefix(list(card), 3))
        suffix = format_dezena_group(compute_suffix(list(card), 3))
        families[f"{prefix}|{suffix}"] += 1
    return dict(families.most_common(15))


def _top_slice_signatures(
    pool: Sequence[Mapping[str, Any]],
    *,
    requested_count: int,
) -> list[tuple[int, ...]]:
    candidate_pool = _pool_candidate_slice(pool, requested_count=requested_count)
    return [_game_signature(game) for game in candidate_pool]


def capture_pool_audit_snapshot(
    pool: Sequence[Mapping[str, Any]],
    *,
    game_size: int = 15,
    requested_count: int = 20,
    batch_label: str | None = None,
) -> dict[str, Any]:
    candidate_pool = _pool_candidate_slice(pool, requested_count=requested_count)
    diagnostics = analyze_pool_structural_issues(
        candidate_pool,
        game_size=int(game_size),
        batch_label=batch_label,
        requested_count=requested_count,
    )
    redundancy = dict(diagnostics.get("redundancy") or {})
    diversity_stage = _evaluate_diversity_stage(
        pool,
        game_size=game_size,
        batch_label=batch_label,
        requested_count=requested_count,
    )
    metrics = _metric_snapshot(candidate_pool, game_size=game_size, batch_label=batch_label)
    coverage_issues = [
        dict(row)
        for row in list(diagnostics.get("issues") or [])
        if str(row.get("tipo") or "") == "dezena_subcoberta"
    ]
    return {
        "pool_size": len(pool),
        "candidate_pool_size": len(candidate_pool),
        "diversity_score": float(metrics.get("diversity_score", 0.0) or 0.0),
        "similarity_score": float(metrics.get("similarity_score", 0.0) or 0.0),
        "max_overlap": int(redundancy.get("sobreposicao_maxima", 0) or 0),
        "near_duplicate_count": int(
            redundancy.get("quase_repetidos_criticos", redundancy.get("cartoes_quase_repetidos", 0)) or 0
        ),
        "dominance": _dominance_rows(diagnostics, len(candidate_pool)),
        "structural_families": _structural_families(candidate_pool),
        "subcovered_dezenas_count": len(coverage_issues),
        "coverage_status": "approved" if not coverage_issues else "issues_detected",
        "diversity_stage_passed": bool(diversity_stage.get("passed")),
        "diversity_stage_metrics": dict(diversity_stage.get("metrics") or {}),
        "diversity_threshold": DIVERSITY_LOW_THRESHOLD,
    }


def _compare_top_slices(
    before_signatures: Sequence[tuple[int, ...]],
    after_signatures: Sequence[tuple[int, ...]],
) -> dict[str, Any]:
    before_list = list(before_signatures)
    after_list = list(after_signatures)
    reordered = sum(1 for left, right in zip(before_list, after_list, strict=False) if left != right)
    before_set = set(before_list)
    after_set = set(after_list)
    replaced = len(before_set - after_set)
    added = len(after_set - before_set)
    return {
        "top_slice_changed": before_list != after_list,
        "candidates_reordered": int(reordered),
        "candidates_replaced": int(replaced),
        "candidates_added": int(added),
        "top_slice_size": len(after_list),
    }


def audit_structural_pool_expansion(
    pool: Sequence[Mapping[str, Any]],
    *,
    history: Sequence[Any] | None,
    seed: int | None = None,
) -> dict[str, Any]:
    before_size = len(pool)
    before_families = _structural_families(_pool_candidate_slice(pool, requested_count=20))
    expanded_pool, bundle = build_ml_structural_15d_pool(list(pool), history=history, seed=seed)
    after_families = _structural_families(_pool_candidate_slice(expanded_pool, requested_count=20))
    metrics_before = dict(bundle.get("metrics_before") or {})
    metrics_after = dict(bundle.get("metrics_after") or {})
    return {
        "action": "pool_estrutural_15d_expandido",
        "pool_size_before": before_size,
        "pool_size_after": len(expanded_pool),
        "pool_size_delta": len(expanded_pool) - before_size,
        "structural_generated_count": int(bundle.get("structural_generated_count", 0) or 0),
        "structural_compliant_pool_size": int(bundle.get("structural_compliant_pool_size", 0) or 0),
        "compliance_rate": float(bundle.get("compliance_rate", 0.0) or 0.0),
        "diversity_score_delta": _safe_delta(
            float(metrics_after.get("diversity_score", 0.0) or 0.0),
            float(metrics_before.get("diversity_score", 0.0) or 0.0),
        ),
        "structural_families_before": before_families,
        "structural_families_after": after_families,
        "new_candidates_structurally_different": int(
            len(set(after_families) - set(before_families))
        ),
    }


def audit_diversity_remediation_cycle(
    pool: list[dict[str, Any]],
    *,
    game_size: int = 15,
    requested_count: int = 20,
    batch_label: str | None = None,
    history: Sequence[Any] | None = None,
    seed: int | None = None,
    baseline_pool: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Mede antes/depois de um ciclo completo de remediação de diversidade (M-ML-073)."""
    with audit_runtime_isolation():
        before_snapshot = capture_pool_audit_snapshot(
            pool,
            game_size=game_size,
            requested_count=requested_count,
            batch_label=batch_label,
        )
        before_top = _top_slice_signatures(pool, requested_count=requested_count)
        before_families = dict(before_snapshot.get("structural_families") or {})

        remediated_pool = _remediate_pool_for_stage(
            [dict(game) for game in pool],
            stage_id=STAGE_DIVERSITY,
            game_size=game_size,
            history=history,
            seed=seed,
        )
        structural_audit = audit_structural_pool_expansion(
            _pool_candidate_slice(pool, requested_count=requested_count),
            history=history,
            seed=seed,
        )

        calibrated_pool, pre_final_bundle = _apply_pool_remediation(
            [dict(game) for game in pool],
            game_size=game_size,
            requested_count=requested_count,
            batch_label=batch_label,
            calibration_plan={"authorized": True},
            event_context={"batch_label": batch_label, "requested_count": requested_count},
            baseline_pool=baseline_pool or pool,
            compose_gp=None,
            compose_config=None,
            stage_id=STAGE_DIVERSITY,
            history=history,
            seed=seed,
        )

        after_snapshot = capture_pool_audit_snapshot(
            calibrated_pool,
            game_size=game_size,
            requested_count=requested_count,
            batch_label=batch_label,
        )
        after_top = _top_slice_signatures(calibrated_pool, requested_count=requested_count)
        top_slice = _compare_top_slices(before_top, after_top)

        routing = resolve_agent_routing(
            issue_type="diversidade_baixa",
            corrective_action="rerank_diversidade",
        )

        return {
            "mission_id": MISSION_ID,
            "audit_version": AUDIT_VERSION,
            "scenario": {
                "game_size": int(game_size),
                "requested_count": int(requested_count),
                "top_slice_size": int(requested_count) * 3,
                "batch_label": batch_label,
            },
            "before": before_snapshot,
            "after": after_snapshot,
            "delta": {
                "diversity_score": _safe_delta(
                    after_snapshot["diversity_score"],
                    before_snapshot["diversity_score"],
                ),
                "similarity_score": _safe_delta(
                    after_snapshot["similarity_score"],
                    before_snapshot["similarity_score"],
                ),
                "max_overlap": _safe_delta(
                    float(after_snapshot["max_overlap"]),
                    float(before_snapshot["max_overlap"]),
                ),
                "near_duplicate_count": _safe_delta(
                    float(after_snapshot["near_duplicate_count"]),
                    float(before_snapshot["near_duplicate_count"]),
                ),
                "pool_size": _safe_delta(
                    float(after_snapshot["pool_size"]),
                    float(before_snapshot["pool_size"]),
                ),
            },
            "top_slice": top_slice,
            "structural_families_before": before_families,
            "structural_families_after": dict(after_snapshot.get("structural_families") or {}),
            "corrective_actions": {
                "pool_estrutural_15d_expandido": structural_audit,
                "rerank_diversidade": {
                    "action": "rerank_diversidade",
                    "candidates_reordered": int(pre_final_bundle.get("candidates_reordered", 0) or 0),
                    "candidates_replaced": int(pre_final_bundle.get("candidates_replaced", 0) or 0),
                    "pre_final_calibration_applied": bool(
                        pre_final_bundle.get("pre_final_calibration_applied")
                    ),
                    "metrics_before": dict(pre_final_bundle.get("metrics_before") or {}),
                    "metrics_after": dict(pre_final_bundle.get("metrics_after") or {}),
                    "diversity_delta_pre_final": _safe_delta(
                        float((pre_final_bundle.get("metrics_after") or {}).get("diversity_score", 0.0) or 0.0),
                        float((pre_final_bundle.get("metrics_before") or {}).get("diversity_score", 0.0) or 0.0),
                    ),
                    "actions_applied": list(pre_final_bundle.get("actions_applied") or [])[:20],
                },
            },
            "remediation_effective": bool(
                after_snapshot["diversity_score"] >= DIVERSITY_LOW_THRESHOLD
                and after_snapshot.get("diversity_stage_passed")
            ),
            "agent_routing": {
                "agent_routing_mission_id": AGENT_ROUTING_MISSION_ID,
                "responsible_agent": routing.get("responsible_agent"),
                "support_agents": list(routing.get("support_agents") or []),
                "routing_reason": routing.get("routing_reason"),
            },
            "pre_final_bundle": {
                key: pre_final_bundle.get(key)
                for key in (
                    "candidates_reordered",
                    "candidates_replaced",
                    "pre_final_pool_size",
                    "pre_final_pool_deduped_size",
                )
            },
            "remediated_pool_size": len(remediated_pool),
            "calibrated_pool_size": len(calibrated_pool),
        }


def classify_remediation_root_cause(audit: Mapping[str, Any]) -> dict[str, Any]:
    before = dict(audit.get("before") or {})
    after = dict(audit.get("after") or {})
    delta = dict(audit.get("delta") or {})
    top_slice = dict(audit.get("top_slice") or {})
    rerank = dict((audit.get("corrective_actions") or {}).get("rerank_diversidade") or {})
    expansion = dict((audit.get("corrective_actions") or {}).get("pool_estrutural_15d_expandido") or {})

    causes: list[str] = []
    if float(delta.get("diversity_score", {}).get("absolute", 0.0) or 0.0) < 0.05:
        causes.append("rerank_fraco_sem_ganho_material")
    if int(rerank.get("candidates_replaced", 0) or 0) == 0 and not top_slice.get("top_slice_changed"):
        causes.append("falta_substituicao_real_no_top_slice")
    if int(expansion.get("pool_size_delta", 0) or 0) <= 0:
        causes.append("expansao_pool_sem_novos_candidatos")
    elif int(expansion.get("new_candidates_structurally_different", 0) or 0) == 0:
        causes.append("expansao_sem_familias_estruturais_novas")
    if before.get("dominance", {}).get("suffix_excessivo") and after.get("dominance", {}).get("suffix_excessivo"):
        causes.append("penalidade_sufixo_prefixo_insuficiente")
    if float(before.get("diversity_score", 0.0) or 0.0) < DIVERSITY_LOW_THRESHOLD - 0.15:
        causes.append("pool_total_insuficientemente_diverso")
    if not causes:
        causes.append("limite_0_55_atingivel_com_mais_substituicao")

    primary = causes[0]
    recommendation_map = {
        "rerank_fraco_sem_ganho_material": "M-STAT-002 — penalidade estrutural multidezena mais forte no rerank pré-final",
        "falta_substituicao_real_no_top_slice": "M-GER-002 — substituição ativa de clones no top requested_count×3, não só reordenação",
        "expansao_pool_sem_novos_candidatos": "M-ML-072-FIX — expansão 15D com geração forçada de famílias alternativas",
        "expansao_sem_familias_estruturais_novas": "M-ML-072-FIX — seed/filtro anti-família no gerador estrutural 15D",
        "penalidade_sufixo_prefixo_insuficiente": "M-STAT-002 — boost de penalidade prefixo/sufixo dominante no rerank",
        "pool_total_insuficientemente_diverso": "M-GER-002 — matéria-prima gerador CORE_002 com diversidade estrutural mínima",
        "limite_0_55_atingivel_com_mais_substituicao": "M-STAT-002 — calibrar rerank antes de revisar limite 0.55",
    }
    return {
        "primary_cause": primary,
        "causes": causes,
        "recommended_next_mission": recommendation_map.get(primary, "M-STAT-002"),
        "maintain_diversity_threshold": True,
        "responsible_agent": AGENT_ESTATISTICO,
    }


def build_low_diversity_audit_pool(
    *,
    pool_size: int = 100,
    requested_count: int = 20,
    dominant_suffix: tuple[int, ...] = (20, 21, 22, 23, 24),
) -> list[dict[str, Any]]:
    """Pool sintético read-only para auditoria — família de sufixo dominante (cenário GP:20)."""
    from lotoia.generator.basic_generator import _attach_scores, _build_game

    games: list[dict[str, Any]] = []
    suffix = tuple(dominant_suffix)
    for index in range(pool_size):
        head = sorted({((index * 3 + offset) % 19) + 1 for offset in range(10)})
        numbers = sorted(set(head) | set(suffix))
        while len(numbers) < 15:
            candidate = (len(numbers) + index) % 25 + 1
            numbers = sorted(set(numbers) | {candidate})
        game = _build_game(numbers[:15])
        game["profile_score"] = 1000 - (index % 15)
        _attach_scores(game, profile_type="recorrente")
        games.append(game)
    games.sort(key=lambda row: float(row.get("profile_score", 0) or 0), reverse=True)
    _ = requested_count
    return games
