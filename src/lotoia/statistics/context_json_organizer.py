"""Reorganizador de context_json — CORE_002.

Transforma context_json plano (300+ campos) em sub-objetos organizados
para melhor legibilidade e debug.

Versão: 1.0.0
"""

from __future__ import annotations

from typing import Any, Mapping


def organize_context_json(context: Mapping[str, Any] | None) -> dict[str, Any]:
    """Reorganiza context_json em sub-objetos estruturados.

    Args:
        context: context_json plano com 300+ campos

    Returns:
        context_json reorganizado com sub-objetos:
        - generation_info: informações básicas da geração
        - structural_metrics: métricas estruturais (triplet, suffix, overlap)
        - validation: resultados de validação
        - calibration: dados de calibração ML
        - hierarchy: dados da hierarquia ML
        - diverse_top_slice: dados do M-STAT-002
    """
    if not context:
        return {}

    ctx = dict(context)
    organized: dict[str, Any] = {}

    # =========================================================================
    # generation_info — informações básicas da geração
    # =========================================================================
    organized["generation_info"] = {
        "mode": ctx.get("generation_mode")
        or ctx.get("sovereign_core_status")
        or "unknown",
        "format": ctx.get("game_size") or ctx.get("card_size") or 15,
        "requested_count": ctx.get("requested_count"),
        "generated_count": ctx.get("count") or ctx.get("games_count"),
        "target_contest": ctx.get("target_contest"),
        "batch_label": ctx.get("batch_label"),
        "batch_id": ctx.get("batch_id"),
    }

    # =========================================================================
    # structural_metrics — métricas estruturais agrupadas
    # =========================================================================
    structural_metrics: dict[str, Any] = {}

    # Triplet 01-02-03
    triplet_keys = {
        "count": "structural_triplet_010203_count",
        "cap": "structural_triplet_010203_cap",
        "excess": "structural_triplet_010203_excess",
        "swaps": "structural_triplet_010203_swaps",
    }
    triplet_data = {
        new_key: ctx.get(old_key)
        for new_key, old_key in triplet_keys.items()
        if ctx.get(old_key) is not None
    }
    if triplet_data:
        # Calcular pct se possível
        count = triplet_data.get("count")
        total = organized["generation_info"].get("generated_count")
        if count is not None and total and total > 0:
            triplet_data["pct"] = round(count / total, 4)
        triplet_data["policy"] = ctx.get("structural_triplet_policy")
        structural_metrics["triplet_010203"] = triplet_data

    # Suffix 23-24-25
    suffix_keys = {
        "count": "structural_suffix_232425_count",
        "cap": "structural_suffix_232425_cap",
        "excess": "structural_suffix_232425_excess",
    }
    suffix_data = {
        new_key: ctx.get(old_key)
        for new_key, old_key in suffix_keys.items()
        if ctx.get(old_key) is not None
    }
    if suffix_data:
        count = suffix_data.get("count")
        total = organized["generation_info"].get("generated_count")
        if count is not None and total and total > 0:
            suffix_data["pct"] = round(count / total, 4)
        structural_metrics["suffix_232425"] = suffix_data

    # Overlap e diversidade
    overlap_data = {}
    if ctx.get("avg_overlap") is not None:
        overlap_data["avg"] = ctx.get("avg_overlap")
    if ctx.get("max_overlap") is not None:
        overlap_data["max"] = ctx.get("max_overlap")
    if ctx.get("max_overlap_permitted") is not None:
        overlap_data["permitted"] = ctx.get("max_overlap_permitted")
    if overlap_data:
        structural_metrics["overlap"] = overlap_data

    if ctx.get("diversity_score") is not None:
        structural_metrics["diversity_score"] = ctx.get("diversity_score")
    if ctx.get("similarity_score") is not None:
        structural_metrics["similarity_score"] = ctx.get("similarity_score")

    # Caps e limites
    caps_data = {}
    if ctx.get("prefix_cap") is not None:
        caps_data["prefix"] = ctx.get("prefix_cap")
    if ctx.get("suffix_cap") is not None:
        caps_data["suffix"] = ctx.get("suffix_cap")
    if ctx.get("family_cap") is not None:
        caps_data["family"] = ctx.get("family_cap")
    if ctx.get("structural_issue_limit") is not None:
        caps_data["issue_limit"] = ctx.get("structural_issue_limit")
    if caps_data:
        structural_metrics["caps"] = caps_data

    # Pool stats
    pool_data = {}
    if ctx.get("candidate_pool_size") is not None:
        pool_data["candidate_size"] = ctx.get("candidate_pool_size")
    if ctx.get("non_triplet_pool_count") is not None:
        pool_data["non_triplet_pool"] = ctx.get("non_triplet_pool_count")
    if ctx.get("non_triplet_reserve_count") is not None:
        pool_data["non_triplet_reserve"] = ctx.get("non_triplet_reserve_count")
    if ctx.get("non_triplet_required_count") is not None:
        pool_data["non_triplet_required"] = ctx.get("non_triplet_required_count")
    if ctx.get("pool_insufficient_non_triplet_reserve") is not None:
        pool_data["insufficient_reserve"] = ctx.get(
            "pool_insufficient_non_triplet_reserve"
        )
    if pool_data:
        structural_metrics["pool"] = pool_data

    if structural_metrics:
        organized["structural_metrics"] = structural_metrics

    # =========================================================================
    # validation — resultados de validação
    # =========================================================================
    validation: dict[str, Any] = {}

    # Structural validation (da tarefa 2)
    if ctx.get("structural_validation"):
        sv = ctx["structural_validation"]
        validation["structural"] = {
            "valid": sv.get("valid"),
            "violations": sv.get("violations") or [],
            "warnings": sv.get("warnings") or [],
        }

    # Frequency validation
    if ctx.get("frequency_validation"):
        fv = ctx["frequency_validation"]
        validation["frequency"] = {
            "valid": fv.get("is_valid"),
            "max_deviation_pp": fv.get("max_deviation_pp"),
            "avg_deviation_pp": fv.get("avg_deviation_pp"),
            "violation_count": fv.get("violation_count"),
        }

    # Policy validation
    if ctx.get("policy_compliance_status"):
        validation["policy"] = {
            "status": ctx.get("policy_compliance_status"),
            "violated_rules": ctx.get("violated_rules") or [],
            "games_compliant": ctx.get("games_compliant"),
            "games_non_compliant": ctx.get("games_non_compliant"),
            "compliance_rate": ctx.get("compliance_rate"),
        }

    if validation:
        organized["validation"] = validation

    # =========================================================================
    # calibration — dados de calibração ML
    # =========================================================================
    calibration: dict[str, Any] = {}

    if ctx.get("calibration_applied") is not None:
        calibration["applied"] = ctx.get("calibration_applied")
    if ctx.get("calibration_engine_role"):
        calibration["engine_role"] = ctx.get("calibration_engine_role")

    # Calibration bundle
    cal_bundle = ctx.get("calibration_bundle") or {}
    if cal_bundle:
        calibration["bundle"] = {
            "pre_final_applied": cal_bundle.get("pre_final_pool_calibration_applied"),
            "issues_detected": cal_bundle.get("structural_issues_detected"),
            "calibration_plan_id": cal_bundle.get("calibration_plan_id"),
        }

    if calibration:
        organized["calibration"] = calibration

    # =========================================================================
    # hierarchy — dados da hierarquia ML
    # =========================================================================
    hierarchy: dict[str, Any] = {}

    hier_bundle = ctx.get("ml_operational_hierarchy") or {}
    if hier_bundle:
        hierarchy["applied"] = hier_bundle.get("hierarchy_applied")
        hierarchy["compliance"] = hier_bundle.get("hierarchy_compliance")
        hierarchy["version"] = hier_bundle.get("ml_hierarchy_version")
        hierarchy["status"] = hier_bundle.get("ml_hierarchy_status")
        hierarchy["current_stage"] = hier_bundle.get("current_stage")
        hierarchy["quality_tier"] = hier_bundle.get("gp_quality_tier")
        hierarchy["quality_reasons"] = hier_bundle.get("gp_quality_reasons") or []
        hierarchy["stages_completed"] = [
            stage
            for stage in [
                "conformidade",
                "diversidade",
                "cobertura",
                "fechamento",
                "validacao_final",
            ]
            if hier_bundle.get(f"stage_{stage}_passed")
        ]
        hierarchy["blocked"] = hier_bundle.get("gp_delivery_blocked")

    if hierarchy:
        organized["hierarchy"] = hierarchy

    # =========================================================================
    # diverse_top_slice — dados do M-STAT-002
    # =========================================================================
    diverse_slice: dict[str, Any] = {}

    dts_bundle = ctx.get("diverse_top_slice_m_stat_002") or {}
    if dts_bundle:
        diverse_slice["swaps"] = {
            "total": dts_bundle.get("structural_swaps"),
            "triple": dts_bundle.get("structural_triple_swaps")
            or dts_bundle.get("structural_triplet_010203_swaps"),
            "prefix": dts_bundle.get("prefix_swaps"),
            "suffix": dts_bundle.get("suffix_swaps"),
            "overlap": dts_bundle.get("overlap_swaps"),
        }
        diverse_slice["iterations"] = dts_bundle.get("iterations")
        diverse_slice["exhausted"] = dts_bundle.get("swap_exhausted")

    if diverse_slice:
        organized["diverse_top_slice"] = diverse_slice

    # =========================================================================
    # structural_pool — dados do pool estrutural M-ML-072
    # =========================================================================
    structural_pool: dict[str, Any] = {}

    if ctx.get("structural_pool_applied") is not None:
        structural_pool["applied"] = ctx.get("structural_pool_applied")
    if ctx.get("pool_origin"):
        structural_pool["origin"] = ctx.get("pool_origin")
    if ctx.get("structural_pool_size") is not None:
        structural_pool["size"] = ctx.get("structural_pool_size")
    if ctx.get("structural_compliant_pool_size") is not None:
        structural_pool["compliant_size"] = ctx.get("structural_compliant_pool_size")
    if ctx.get("structural_pool_compliance_rate") is not None:
        structural_pool["compliance_rate"] = ctx.get("structural_pool_compliance_rate")

    sp_bundle = ctx.get("ml_structural_15d_pool") or {}
    if sp_bundle:
        structural_pool["origin"] = sp_bundle.get("pool_origin") or structural_pool.get(
            "origin"
        )
        structural_pool["size"] = sp_bundle.get(
            "structural_pool_size"
        ) or structural_pool.get("size")
        structural_pool["compliant_size"] = sp_bundle.get(
            "structural_compliant_pool_size"
        ) or structural_pool.get("compliant_size")
        structural_pool["compliance_rate"] = sp_bundle.get(
            "compliance_rate"
        ) or structural_pool.get("compliance_rate")

    if structural_pool:
        organized["structural_pool"] = structural_pool

    # =========================================================================
    # routing — dados de roteamento
    # =========================================================================
    routing = ctx.get("generation_routing") or {}
    if routing:
        organized["routing"] = {
            "routed": routing.get("routed"),
            "batch_type": routing.get("batch_type"),
            "sovereign": routing.get("sovereign_core"),
            "reason": routing.get("routing_reason"),
        }

    # =========================================================================
    # operational_status — status operacional do lote
    # =========================================================================
    if ctx.get("operational_status"):
        organized["operational_status"] = {
            "status": ctx.get("operational_status"),
            "active": ctx.get("is_active_reading"),
            "conference_eligible": ctx.get("is_conference_eligible"),
        }

    # =========================================================================
    # raw — campos não categorizados (para debug)
    # =========================================================================
    # Preservar campos importantes que não foram categorizados
    raw_keys_to_preserve = [
        "structural_sovereignty_sanity",
        "operational_structural_memory_snapshot",
        "realignment_metadata",
        "agent_routing_mission_id",
        "primary_responsible_agent",
    ]
    raw = {k: ctx[k] for k in raw_keys_to_preserve if k in ctx}
    if raw:
        organized["raw"] = raw

    return organized


def flatten_context_json(organized: Mapping[str, Any] | None) -> dict[str, Any]:
    """Reverte organized → plano (para compatibilidade com código legado).

    Útil para migração gradual: novos códigos leem organized,
    códigos legados continuam lendo campos planos.
    """
    if not organized:
        return {}

    org = dict(organized)
    flat: dict[str, Any] = {}

    # generation_info
    gen = org.get("generation_info") or {}
    flat["game_size"] = gen.get("format")
    flat["requested_count"] = gen.get("requested_count")
    flat["count"] = gen.get("generated_count")
    flat["target_contest"] = gen.get("target_contest")
    flat["batch_label"] = gen.get("batch_label")
    flat["batch_id"] = gen.get("batch_id")

    # structural_metrics
    sm = org.get("structural_metrics") or {}
    triplet = sm.get("triplet_010203") or {}
    flat["structural_triplet_010203_count"] = triplet.get("count")
    flat["structural_triplet_010203_cap"] = triplet.get("cap")
    flat["structural_triplet_010203_excess"] = triplet.get("excess")
    flat["structural_triplet_010203_swaps"] = triplet.get("swaps")
    flat["structural_triplet_policy"] = triplet.get("policy")

    suffix = sm.get("suffix_232425") or {}
    flat["structural_suffix_232425_count"] = suffix.get("count")
    flat["structural_suffix_232425_cap"] = suffix.get("cap")
    flat["structural_suffix_232425_excess"] = suffix.get("excess")

    overlap = sm.get("overlap") or {}
    flat["avg_overlap"] = overlap.get("avg")
    flat["max_overlap"] = overlap.get("max")
    flat["max_overlap_permitted"] = overlap.get("permitted")

    flat["diversity_score"] = sm.get("diversity_score")
    flat["similarity_score"] = sm.get("similarity_score")

    caps = sm.get("caps") or {}
    flat["prefix_cap"] = caps.get("prefix")
    flat["suffix_cap"] = caps.get("suffix")
    flat["family_cap"] = caps.get("family")
    flat["structural_issue_limit"] = caps.get("issue_limit")

    pool = sm.get("pool") or {}
    flat["candidate_pool_size"] = pool.get("candidate_size")
    flat["non_triplet_pool_count"] = pool.get("non_triplet_pool")
    flat["non_triplet_reserve_count"] = pool.get("non_triplet_reserve")
    flat["non_triplet_required_count"] = pool.get("non_triplet_required")
    flat["pool_insufficient_non_triplet_reserve"] = pool.get("insufficient_reserve")

    # validation
    val = org.get("validation") or {}
    sv = val.get("structural") or {}
    if sv:
        flat["structural_validation"] = {
            "valid": sv.get("valid"),
            "violations": sv.get("violations") or [],
            "warnings": sv.get("warnings") or [],
        }

    # raw
    raw = org.get("raw") or {}
    flat.update(raw)

    # Remover None values
    return {k: v for k, v in flat.items() if v is not None}
