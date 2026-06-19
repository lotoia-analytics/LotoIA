"""Hierarquia operacional ML — memória decisória soberana (M-ML-073)."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any, Callable, Mapping, Sequence

from lotoia.database.database import DEFAULT_DATABASE_PATH, ScientificInstitutionalMemory, create_database, get_session
from lotoia.governance.institutional_agent_routing_matrix import enrich_hierarchy_bundle
from lotoia.ml.ml_operational_verdict import evaluate_ml_operational_verdict
from lotoia.ml.overlap_format_thresholds import (
    DIVERSITY_LOW_THRESHOLD,
    LEVEL_CRITICO,
    LEVEL_RUIM,
    MAX_FORMAT_SIZE,
    MIN_FORMAT_SIZE,
    classify_overlap_for_format,
)
from lotoia.ml.pre_final_pool_ml_calibration import (
    MISSION_ID as PRE_FINAL_MISSION_ID,
    apply_pre_final_pool_ml_calibration,
)
from lotoia.ml.structural_policy_15d import (
    is_structural_policy_15d_format,
    resolve_previous_contest_numbers,
    validate_game_structural_policy_15d,
)
from lotoia.ml.structural_pool_15d_generator import (
    MISSION_ID as STRUCTURAL_POOL_MISSION_ID,
    MIN_COMPLIANT_POOL_SIZE,
    MIN_POOL_COMPLIANCE_RATE,
    build_ml_structural_15d_pool,
)
from lotoia.ml.supervised_output_calibration import (
    DEFAULT_NEAR_DUP_PAIR_RATIO,
    analyze_pool_structural_issues,
)
from lotoia.statistics.card_structure import resolve_cartao_final_from_game

MISSION_ID = "M-ML-073"
HIERARCHY_VERSION = "M-ML-073-v1"
MEMORY_KIND = "ml_operational_hierarchy"
MEMORY_STATUS_ACTIVE = "active"
ENV_HIERARCHY_ENABLED = "LOTOIA_ML_OPERATIONAL_HIERARCHY_ENABLED"
MAX_REMEDIATION_ATTEMPTS = 5

STAGE_CONFORMITY = "conformidade_estrutural"
STAGE_DIVERSITY = "diversidade"
STAGE_COVERAGE = "cobertura"
STAGE_GP_CLOSURE = "fechamento_gp"
STAGE_FINAL_VALIDATION = "validacao_final"

STAGE_ORDER: tuple[str, ...] = (
    STAGE_CONFORMITY,
    STAGE_DIVERSITY,
    STAGE_COVERAGE,
    STAGE_GP_CLOSURE,
    STAGE_FINAL_VALIDATION,
)

STAGE_LABELS: dict[str, str] = {
    STAGE_CONFORMITY: "Etapa 1: Conformidade",
    STAGE_DIVERSITY: "Etapa 2: Diversidade",
    STAGE_COVERAGE: "Etapa 3: Cobertura",
    STAGE_GP_CLOSURE: "Etapa 4: Fechamento GP",
    STAGE_FINAL_VALIDATION: "Etapa 5: Veredito",
}

SUPPORTED_FORMAT_SIZES: tuple[int, ...] = tuple(range(MIN_FORMAT_SIZE, MAX_FORMAT_SIZE + 1))

DIVERSITY_ISSUE_TYPES: frozenset[str] = frozenset(
    {
        "quase_repetidos_alto",
        "similaridade_media_gp_elevada",
        "sobreposicao_maxima_elevada",
        "prefixo_excessivo",
        "sufixo_excessivo",
    }
)
COVERAGE_ISSUE_TYPES: frozenset[str] = frozenset({"dezena_subcoberta"})


def is_ml_operational_hierarchy_enabled() -> bool:
    raw = os.getenv(ENV_HIERARCHY_ENABLED, "1").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def is_hierarchy_format(game_size: int) -> bool:
    return MIN_FORMAT_SIZE <= int(game_size) <= MAX_FORMAT_SIZE


def build_ml_operational_hierarchy_memory() -> dict[str, Any]:
    return {
        "memory_kind": MEMORY_KIND,
        "mission_id": MISSION_ID,
        "hierarchy_version": HIERARCHY_VERSION,
        "ml_hierarchy_version": HIERARCHY_VERSION,
        "ml_hierarchy_status": MEMORY_STATUS_ACTIVE,
        "status": MEMORY_STATUS_ACTIVE,
        "supported_formats": [f"{size}D" for size in SUPPORTED_FORMAT_SIZES],
        "stages": [
            {
                "stage_id": stage_id,
                "label": STAGE_LABELS[stage_id],
                "mandatory": stage_id in {STAGE_CONFORMITY, STAGE_DIVERSITY, STAGE_COVERAGE},
            }
            for stage_id in STAGE_ORDER
        ],
        "thresholds": {
            "min_compliance_rate": MIN_POOL_COMPLIANCE_RATE,
            "min_diversity_score": DIVERSITY_LOW_THRESHOLD,
            "max_near_dup_pair_ratio": DEFAULT_NEAR_DUP_PAIR_RATIO,
            "min_compliant_pool_size_15d": MIN_COMPLIANT_POOL_SIZE,
        },
        "subordinate_missions": {
            "structural_policy_15d": "M-ML-070",
            "pre_final_pool_ml": PRE_FINAL_MISSION_ID,
            "structural_pool_15d": STRUCTURAL_POOL_MISSION_ID,
        },
        "origem_institucional": "M-ML-073",
        "updated_at": datetime.now(UTC).isoformat(),
    }


def persist_ml_operational_hierarchy_memory(
    db_path: Any = DEFAULT_DATABASE_PATH,
    memory: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(memory or build_ml_operational_hierarchy_memory())
    payload["updated_at"] = datetime.now(UTC).isoformat()
    create_database(db_path)
    with get_session(db_path) as session:
        session.add(
            ScientificInstitutionalMemory(
                memory_kind=MEMORY_KIND,
                strategy_name="Hierarquia Operacional ML",
                game_size=0,
                batch_id=f"{MISSION_ID}-{HIERARCHY_VERSION}",
                generation_range={"mission_id": MISSION_ID, "formatos": "15D-23D"},
                total_games=0,
                unique_games=0,
                duplicate_games=0,
                structural_status=MEMORY_STATUS_ACTIVE,
                scientific_status=MEMORY_STATUS_ACTIVE,
                scientific_classification="ML_OPERATIONAL_HIERARCHY",
                main_reason="Ordem obrigatória de decisão ML antes do fechamento do GP",
                recommended_action="execute_ml_operational_hierarchy",
                policy_applied=dict(payload),
                policy_before={},
                policy_after=dict(payload),
                decision_mode="INSTITUCIONAL",
                approved_for_use=1,
                notes="Conformidade → Diversidade → Cobertura → GP → Veredito",
                source=MISSION_ID,
            )
        )
        session.commit()
    return payload


def ensure_ml_operational_hierarchy_memory(db_path: Any = DEFAULT_DATABASE_PATH) -> dict[str, Any]:
    create_database(db_path)
    with get_session(db_path) as session:
        row = (
            session.query(ScientificInstitutionalMemory)
            .filter(
                ScientificInstitutionalMemory.memory_kind == MEMORY_KIND,
                ScientificInstitutionalMemory.approved_for_use == 1,
            )
            .order_by(
                ScientificInstitutionalMemory.created_at.desc(),
                ScientificInstitutionalMemory.id.desc(),
            )
            .first()
        )
    if row is not None:
        stored = dict(getattr(row, "policy_applied", {}) or {})
        if stored:
            stored.setdefault("memory_row_id", int(getattr(row, "id", 0) or 0))
            return stored
    return persist_ml_operational_hierarchy_memory(db_path)


def _diversity_score_from_diagnostics(diagnostics: Mapping[str, Any]) -> float:
    redundancy = dict(diagnostics.get("redundancy") or {})
    return round(1.0 - float(redundancy.get("similaridade_media_entre_jogos", 0) or 0), 4)


def _issues_by_type(diagnostics: Mapping[str, Any], types: frozenset[str]) -> list[dict[str, Any]]:
    return [
        dict(issue)
        for issue in list(diagnostics.get("issues") or [])
        if isinstance(issue, dict) and str(issue.get("tipo") or "") in types
    ]


def _pool_candidate_slice(
    pool: Sequence[Mapping[str, Any]],
    *,
    requested_count: int | None = None,
) -> list[dict[str, Any]]:
    rows = [dict(game) for game in pool]
    if not rows:
        return rows
    if requested_count is None:
        return rows
    ranked = sorted(
        rows,
        key=lambda row: float(row.get("profile_score", 0) or 0),
        reverse=True,
    )
    limit = max(int(requested_count) * 3, int(requested_count), 20)
    return ranked[: min(limit, len(ranked))]


def _evaluate_conformity_stage(
    pool: Sequence[Mapping[str, Any]],
    *,
    game_size: int,
    history: Sequence[Any] | None,
    structural_pool_bundle: Mapping[str, Any] | None,
    batch_label: str | None,
) -> dict[str, Any]:
    size = int(game_size)
    failures: list[str] = []
    corrective_actions: list[str] = []
    compliance_rate = 0.0

    if is_structural_policy_15d_format(size):
        bundle = dict(structural_pool_bundle or {})
        if bundle.get("structural_pool_applied"):
            compliance_rate = float(bundle.get("compliance_rate", 0.0) or 0.0)
            compliant_size = int(bundle.get("structural_compliant_pool_size", 0) or 0)
            if compliance_rate < MIN_POOL_COMPLIANCE_RATE:
                failures.append(
                    f"compliance_rate={compliance_rate:.2%} abaixo de {MIN_POOL_COMPLIANCE_RATE:.0%}"
                )
            if compliant_size < MIN_COMPLIANT_POOL_SIZE:
                failures.append(
                    f"pool conforme={compliant_size} abaixo do mínimo {MIN_COMPLIANT_POOL_SIZE}"
                )
            corrective_actions.append("expandir_pool_estrutural_15d")
        else:
            previous = resolve_previous_contest_numbers(history)
            approved = 0
            for game in pool:
                numbers = list(game.get("numbers") or game.get("final_card_numbers") or [])
                if validate_game_structural_policy_15d(
                    numbers,
                    previous_contest_numbers=previous,
                ).get("approved"):
                    approved += 1
            compliance_rate = approved / max(len(pool), 1)
            if compliance_rate < MIN_POOL_COMPLIANCE_RATE:
                failures.append(
                    f"compliance_rate={compliance_rate:.2%} abaixo de {MIN_POOL_COMPLIANCE_RATE:.0%}"
                )
                corrective_actions.append("gerar_pool_estrutural_15d")
    else:
        diagnostics = analyze_pool_structural_issues(pool, game_size=size, batch_label=batch_label)
        alta_issues = [
            dict(issue)
            for issue in list(diagnostics.get("issues") or [])
            if isinstance(issue, dict)
            and str(issue.get("severidade") or "") == "alta"
            and str(issue.get("tipo") or "") not in DIVERSITY_ISSUE_TYPES | COVERAGE_ISSUE_TYPES
        ]
        redundancy = dict(diagnostics.get("redundancy") or {})
        max_overlap = int(redundancy.get("sobreposicao_maxima", 0) or 0)
        overlap_level = str(classify_overlap_for_format(max_overlap, size).get("level") or "")
        compliance_rate = round(1.0 - (len(alta_issues) / max(len(pool), 1)), 4)
        if overlap_level == LEVEL_CRITICO:
            failures.append(f"overlap_critico_multidezena={max_overlap}")
            corrective_actions.append("substituir_clones_multidezena")
        if alta_issues:
            failures.extend(
                str(issue.get("descricao") or issue.get("tipo") or "conformidade")
                for issue in alta_issues[:5]
            )
            corrective_actions.append("calibracao_estrutural_multidezena")
        if compliance_rate < MIN_POOL_COMPLIANCE_RATE:
            failures.append(
                f"compliance_rate={compliance_rate:.2%} abaixo de {MIN_POOL_COMPLIANCE_RATE:.0%}"
            )

    passed = not failures
    return {
        "stage_id": STAGE_CONFORMITY,
        "stage_label": STAGE_LABELS[STAGE_CONFORMITY],
        "status": "approved" if passed else "rejected",
        "passed": passed,
        "metrics": {
            "compliance_rate": round(compliance_rate, 4),
            "pool_size": len(pool),
            "format": f"{size}D",
            "batch_label": batch_label,
        },
        "failures": failures,
        "corrective_actions": corrective_actions,
    }


def _evaluate_diversity_stage(
    pool: Sequence[Mapping[str, Any]],
    *,
    game_size: int,
    batch_label: str | None,
    requested_count: int | None = None,
) -> dict[str, Any]:
    size = int(game_size)
    candidate_pool = _pool_candidate_slice(pool, requested_count=requested_count)
    diagnostics = analyze_pool_structural_issues(
        candidate_pool,
        game_size=size,
        batch_label=batch_label,
        requested_count=requested_count,
    )
    diversity_issues = _issues_by_type(diagnostics, DIVERSITY_ISSUE_TYPES)
    diversity_score = _diversity_score_from_diagnostics(diagnostics)
    redundancy = dict(diagnostics.get("redundancy") or {})
    max_overlap = int(redundancy.get("sobreposicao_maxima", 0) or 0)
    overlap_eval = classify_overlap_for_format(max_overlap, size)
    overlap_level = str(overlap_eval.get("level") or "")

    failures: list[str] = []
    corrective_actions: list[str] = []
    if diversity_score < DIVERSITY_LOW_THRESHOLD:
        failures.append(
            f"diversity_score={diversity_score:.4f} abaixo de {DIVERSITY_LOW_THRESHOLD}"
        )
        corrective_actions.append("rerank_diversidade")
    if overlap_level in {LEVEL_RUIM, LEVEL_CRITICO}:
        failures.append(f"overlap_maximo={max_overlap} nivel={overlap_level}")
        corrective_actions.append("substituir_quase_clones")
    pair_count = int(redundancy.get("pair_count", redundancy.get("pares_possiveis", 0)) or 0)
    near_dup = int(
        redundancy.get("quase_repetidos_criticos", redundancy.get("cartoes_quase_repetidos", 0)) or 0
    )
    near_dup_ratio = (near_dup / pair_count) if pair_count > 0 else 0.0
    if near_dup_ratio >= DEFAULT_NEAR_DUP_PAIR_RATIO:
        failures.append(
            f"quase_clones_ratio={near_dup_ratio:.2f} limite={DEFAULT_NEAR_DUP_PAIR_RATIO}"
        )
        corrective_actions.append("expansao_pool_diversidade")
    for issue in diversity_issues:
        if str(issue.get("severidade") or "") in {"alta", "media"}:
            failures.append(str(issue.get("descricao") or issue.get("tipo") or "diversidade"))

    passed = not failures
    return {
        "stage_id": STAGE_DIVERSITY,
        "stage_label": STAGE_LABELS[STAGE_DIVERSITY],
        "status": "approved" if passed else "rejected",
        "passed": passed,
        "metrics": {
            "diversity_score": diversity_score,
            "similarity_score": float(redundancy.get("similaridade_media_entre_jogos", 0) or 0),
            "max_overlap": max_overlap,
            "overlap_level": overlap_level,
            "near_dup_ratio": round(near_dup_ratio, 4),
            "issue_count": len(diversity_issues),
            "candidate_pool_size": len(candidate_pool),
        },
        "failures": failures,
        "corrective_actions": list(dict.fromkeys(corrective_actions)),
    }


def _evaluate_coverage_stage(
    pool: Sequence[Mapping[str, Any]],
    *,
    game_size: int,
    batch_label: str | None,
    requested_count: int | None = None,
) -> dict[str, Any]:
    size = int(game_size)
    candidate_pool = _pool_candidate_slice(pool, requested_count=requested_count)
    diagnostics = analyze_pool_structural_issues(
        candidate_pool,
        game_size=size,
        batch_label=batch_label,
        requested_count=requested_count,
    )
    coverage_issues = _issues_by_type(diagnostics, COVERAGE_ISSUE_TYPES)
    alta_coverage = [
        issue for issue in coverage_issues if str(issue.get("severidade") or "") == "alta"
    ]
    failures = [
        str(issue.get("descricao") or issue.get("tipo") or "cobertura")
        for issue in coverage_issues
    ]
    corrective_actions: list[str] = []
    if coverage_issues:
        corrective_actions.append("reforco_dezenas_ausentes")
        corrective_actions.append("rebalanceamento_estrutural")

    passed = not failures
    return {
        "stage_id": STAGE_COVERAGE,
        "stage_label": STAGE_LABELS[STAGE_COVERAGE],
        "status": "approved" if passed else "rejected",
        "passed": passed,
        "metrics": {
            "subcovered_dezenas_count": len(coverage_issues),
            "critical_subcoverage_count": len(alta_coverage),
            "issue_count": len(coverage_issues),
            "candidate_pool_size": len(candidate_pool),
        },
        "failures": failures,
        "corrective_actions": corrective_actions,
    }


def _filter_near_clone_games(
    pool: Sequence[Mapping[str, Any]],
    *,
    game_size: int,
) -> list[dict[str, Any]]:
    size = int(game_size)
    overlap_limit = max(size - 1, 13)
    selected: list[dict[str, Any]] = []
    selected_cards: list[list[int]] = []
    ranked = sorted(
        pool,
        key=lambda row: float(row.get("profile_score", 0) or 0),
        reverse=True,
    )
    for game in ranked:
        card = resolve_cartao_final_from_game(dict(game))
        if not card:
            continue
        if any(len(set(card) & set(other)) >= overlap_limit for other in selected_cards):
            continue
        selected.append(dict(game))
        selected_cards.append(card)
    return selected if len(selected) >= max(10, len(pool) // 4) else [dict(game) for game in pool]


def _remediate_pool_for_stage(
    pool: list[dict[str, Any]],
    *,
    stage_id: str,
    game_size: int,
    history: Sequence[Any] | None,
    seed: int | None,
) -> list[dict[str, Any]]:
    if stage_id == STAGE_DIVERSITY:
        filtered = _filter_near_clone_games(pool, game_size=game_size)
        if is_structural_policy_15d_format(int(game_size)):
            expanded, _ = build_ml_structural_15d_pool(
                filtered,
                history=history,
                seed=(abs(int(seed or 0)) + 31) % 1_000_003,
            )
            return expanded
        return filtered
    if stage_id == STAGE_COVERAGE and is_structural_policy_15d_format(int(game_size)):
        expanded, _ = build_ml_structural_15d_pool(
            pool,
            history=history,
            seed=(abs(int(seed or 0)) + 53) % 1_000_003,
        )
        return expanded
    return pool


def _apply_pool_remediation(
    pool: list[dict[str, Any]],
    *,
    game_size: int,
    requested_count: int,
    batch_label: str | None,
    calibration_plan: Mapping[str, Any] | None,
    event_context: Mapping[str, Any] | None,
    baseline_pool: Sequence[Mapping[str, Any]],
    compose_gp: Callable[..., list[dict[str, Any]]] | None,
    compose_config: Any,
    stage_id: str,
    history: Sequence[Any] | None = None,
    seed: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    pool = _remediate_pool_for_stage(
        [dict(game) for game in pool],
        stage_id=stage_id,
        game_size=game_size,
        history=history,
        seed=seed,
    )
    authorized_plan = dict(calibration_plan or {})
    if stage_id == STAGE_DIVERSITY:
        authorized_plan.setdefault("authorized", True)
        params = dict(authorized_plan.get("parametros_sugeridos") or {})
        params.setdefault("redundancy_penalty_boost", 1.35)
        params.setdefault("max_overlap_penalty", 1.25)
        authorized_plan["parametros_sugeridos"] = params
    elif stage_id == STAGE_COVERAGE:
        authorized_plan.setdefault("authorized", True)
        params = dict(authorized_plan.get("parametros_sugeridos") or {})
        params.setdefault("missing_numbers_boost", 1.4)
        params.setdefault("critical_coverage_boost", 1.3)
        authorized_plan["parametros_sugeridos"] = params

    return apply_pre_final_pool_ml_calibration(
        pool,
        game_size=game_size,
        requested_count=requested_count,
        ml_enabled=True,
        batch_label=batch_label,
        calibration_plan=authorized_plan,
        event_context=event_context,
        baseline_pool=baseline_pool,
        compose_gp=compose_gp,
        compose_config=compose_config,
    )


def execute_ml_operational_hierarchy(
    games: list[dict[str, Any]],
    *,
    game_size: int,
    requested_count: int,
    history: Sequence[Any] | None = None,
    seed: int | None = None,
    batch_label: str | None = None,
    calibration_plan: Mapping[str, Any] | None = None,
    event_context: Mapping[str, Any] | None = None,
    compose_gp: Callable[..., list[dict[str, Any]]] | None = None,
    compose_config: Any = None,
    db_path: Any = DEFAULT_DATABASE_PATH,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Executa etapas 1–3 da hierarquia ML e prepara pool para fechamento do GP."""
    memory = build_ml_operational_hierarchy_memory()
    empty_bundle: dict[str, Any] = {
        "mission_id": MISSION_ID,
        "hierarchy_version": HIERARCHY_VERSION,
        "ml_hierarchy_version": HIERARCHY_VERSION,
        "ml_hierarchy_status": MEMORY_STATUS_ACTIVE,
        "hierarchy_applied": False,
        "gp_closure_allowed": True,
        "hierarchy_compliance": True,
        "current_stage": STAGE_CONFORMITY,
        "stage_results": {},
        "stage_failures": [],
    }
    if not is_ml_operational_hierarchy_enabled() or not is_hierarchy_format(game_size):
        return games, empty_bundle, {}

    try:
        memory = ensure_ml_operational_hierarchy_memory(db_path)
    except Exception:  # noqa: BLE001 — memória opcional em testes/offline
        memory = build_ml_operational_hierarchy_memory()

    pool = [dict(game) for game in games]
    structural_pool_bundle: dict[str, Any] = {}
    pre_final_bundle: dict[str, Any] = {}
    stage_results: dict[str, Any] = {}
    stage_failures: list[str] = []
    corrective_actions: list[str] = []
    current_stage = STAGE_CONFORMITY
    baseline_pool = [dict(game) for game in pool]

    if is_structural_policy_15d_format(int(game_size)):
        pool, structural_pool_bundle = build_ml_structural_15d_pool(
            pool,
            history=history,
            seed=seed,
        )
        if structural_pool_bundle.get("structural_pool_applied"):
            corrective_actions.append("pool_estrutural_15d_expandido")

    conformity = _evaluate_conformity_stage(
        pool,
        game_size=game_size,
        history=history,
        structural_pool_bundle=structural_pool_bundle,
        batch_label=batch_label,
    )
    stage_results[STAGE_CONFORMITY] = conformity
    current_stage = STAGE_CONFORMITY
    if not conformity["passed"]:
        stage_failures.extend(conformity["failures"])
        corrective_actions.extend(conformity["corrective_actions"])

    for stage_id, evaluator in (
        (
            STAGE_DIVERSITY,
            lambda current: _evaluate_diversity_stage(
                current,
                game_size=game_size,
                batch_label=batch_label,
                requested_count=requested_count,
            ),
        ),
        (
            STAGE_COVERAGE,
            lambda current: _evaluate_coverage_stage(
                current,
                game_size=game_size,
                batch_label=batch_label,
                requested_count=requested_count,
            ),
        ),
    ):
        current_stage = stage_id
        result = evaluator(pool)
        attempts = 0
        while not result["passed"] and attempts < MAX_REMEDIATION_ATTEMPTS:
            attempts += 1
            pool, pre_final_bundle = _apply_pool_remediation(
                pool,
                game_size=game_size,
                requested_count=requested_count,
                batch_label=batch_label,
                calibration_plan=calibration_plan,
                event_context=event_context,
                baseline_pool=baseline_pool,
                compose_gp=compose_gp,
                compose_config=compose_config,
                stage_id=stage_id,
                history=history,
                seed=seed,
            )
            result = evaluator(pool)
            result["remediation_attempts"] = attempts
            corrective_actions.extend(result.get("corrective_actions") or [])
        stage_results[stage_id] = result
        if not result["passed"]:
            stage_failures.extend(result["failures"])

    pre_gp_stages_passed = all(
        stage_results.get(stage_id, {}).get("passed") for stage_id in (STAGE_CONFORMITY, STAGE_DIVERSITY, STAGE_COVERAGE)
    )
    gp_closure_allowed = pre_gp_stages_passed
    current_stage = STAGE_GP_CLOSURE if gp_closure_allowed else stage_results.get(STAGE_COVERAGE, {}).get("stage_id", STAGE_COVERAGE)

    if gp_closure_allowed and not pre_final_bundle:
        pool, pre_final_bundle = apply_pre_final_pool_ml_calibration(
            pool,
            game_size=game_size,
            requested_count=requested_count,
            ml_enabled=True,
            batch_label=batch_label,
            calibration_plan=calibration_plan,
            event_context=event_context,
            baseline_pool=baseline_pool,
            compose_gp=compose_gp,
            compose_config=compose_config,
        )

    stage_results[STAGE_GP_CLOSURE] = {
        "stage_id": STAGE_GP_CLOSURE,
        "stage_label": STAGE_LABELS[STAGE_GP_CLOSURE],
        "status": "approved" if gp_closure_allowed else "blocked",
        "passed": gp_closure_allowed,
        "metrics": {"requested_count": int(requested_count), "pool_size": len(pool)},
        "failures": [] if gp_closure_allowed else stage_failures,
        "corrective_actions": list(dict.fromkeys(corrective_actions)),
    }

    hierarchy_bundle: dict[str, Any] = enrich_hierarchy_bundle(
        {
            "mission_id": MISSION_ID,
            "hierarchy_version": HIERARCHY_VERSION,
            "ml_hierarchy_version": HIERARCHY_VERSION,
            "ml_hierarchy_status": MEMORY_STATUS_ACTIVE,
            "memory_kind": MEMORY_KIND,
            "hierarchy_applied": True,
            "hierarchy_compliance": gp_closure_allowed,
            "gp_closure_allowed": gp_closure_allowed,
            "gp_closure_blocked": not gp_closure_allowed,
            "current_stage": current_stage,
            "last_completed_stage": (
                STAGE_COVERAGE
                if pre_gp_stages_passed
                else next(
                    (
                        stage_id
                        for stage_id in (STAGE_CONFORMITY, STAGE_DIVERSITY, STAGE_COVERAGE)
                        if not stage_results.get(stage_id, {}).get("passed")
                    ),
                    STAGE_COVERAGE,
                )
            ),
            "blocking_reason": "; ".join(stage_failures[:5]) if stage_failures else "",
            "corrective_action_applied": list(dict.fromkeys(corrective_actions))[:20],
            "stage_results": stage_results,
            "stage_failures": stage_failures,
            "operational_hierarchy_memory": memory,
            "subordinate_missions": {
                "structural_pool_15d": structural_pool_bundle,
                "pre_final_pool_ml": pre_final_bundle,
            },
        }
    )
    mission_bundles = {
        "structural_pool": structural_pool_bundle,
        "pre_final": pre_final_bundle,
    }
    return pool, hierarchy_bundle, mission_bundles


def finalize_ml_operational_hierarchy_validation(
    hierarchy_bundle: Mapping[str, Any] | None,
    *,
    final_gp: Sequence[Mapping[str, Any]],
    structural_policy_bundle: Mapping[str, Any] | None = None,
    pre_final_bundle: Mapping[str, Any] | None = None,
    structural_pool_bundle: Mapping[str, Any] | None = None,
    metrics_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Etapa 5 — consolida M-ML-070/071/072 e emite veredito hierárquico."""
    payload = dict(hierarchy_bundle or {})
    stage_results = dict(payload.get("stage_results") or {})

    verdict_payload: dict[str, Any] = {}
    if metrics_payload:
        try:
            verdict_payload = evaluate_ml_operational_verdict(
                dict(metrics_payload.get("metrics") or metrics_payload or {}),
                format_analyses=list(metrics_payload.get("format_analyses") or []),
            )
        except Exception:  # noqa: BLE001 — veredito opcional
            verdict_payload = {}

    subordinate_status = {
        "M-ML-070": bool((structural_policy_bundle or {}).get("structural_policy_applied")),
        "M-ML-071": bool((pre_final_bundle or {}).get("pre_final_calibration_applied")),
        "M-ML-072": bool((structural_pool_bundle or {}).get("structural_pool_applied")),
    }
    verdict = str(verdict_payload.get("ml_verdict") or "")
    final_passed = payload.get("gp_closure_allowed", True) and verdict not in {
        "REPROVADO",
        "BLOQUEADO PARA OFICIALIZAÇÃO",
        "PRECISA CALIBRAR",
    }
    if not verdict and payload.get("gp_closure_allowed", True):
        verdict = "APROVADO"

    stage_results[STAGE_FINAL_VALIDATION] = {
        "stage_id": STAGE_FINAL_VALIDATION,
        "stage_label": STAGE_LABELS[STAGE_FINAL_VALIDATION],
        "status": "approved" if final_passed else "rejected",
        "passed": final_passed,
        "metrics": {
            "final_gp_size": len(list(final_gp or [])),
            "subordinate_missions": subordinate_status,
            "ml_verdict": verdict,
        },
        "failures": [] if final_passed else [str(verdict_payload.get("ml_verdict_reason") or verdict or "veredito_reprovado")],
        "corrective_actions": list(verdict_payload.get("acoes_recomendadas") or [])[:10],
        "verdict_payload": verdict_payload,
    }

    payload["stage_results"] = stage_results
    payload["current_stage"] = STAGE_FINAL_VALIDATION
    payload["last_completed_stage"] = STAGE_FINAL_VALIDATION
    payload["ml_verdict"] = verdict
    payload["ml_verdict_reason"] = str(verdict_payload.get("ml_verdict_reason") or "")
    payload["hierarchy_compliance"] = bool(payload.get("gp_closure_allowed")) and final_passed
    payload["subordinate_missions_status"] = subordinate_status
    return enrich_hierarchy_bundle(payload)


def build_ml_operational_hierarchy_trace(bundle: Mapping[str, Any] | None) -> dict[str, Any]:
    source = dict(bundle or {})
    stage_results = dict(source.get("stage_results") or {})
    safe_stage_results: dict[str, Any] = {}
    for stage_id, result in stage_results.items():
        if not isinstance(result, dict):
            continue
        safe_stage_results[stage_id] = {
            "stage_id": result.get("stage_id"),
            "stage_label": result.get("stage_label"),
            "status": result.get("status"),
            "passed": bool(result.get("passed")),
            "metrics": dict(result.get("metrics") or {}),
            "failures": list(result.get("failures") or [])[:10],
            "corrective_actions": list(result.get("corrective_actions") or [])[:10],
            "responsible_agent": str(result.get("responsible_agent") or ""),
            "support_agents": list(result.get("support_agents") or [])[:5],
            "routing_reason": str(result.get("routing_reason") or ""),
        }
    return {
        "mission_id": str(source.get("mission_id") or MISSION_ID),
        "ml_hierarchy_version": str(source.get("ml_hierarchy_version") or HIERARCHY_VERSION),
        "ml_hierarchy_status": str(source.get("ml_hierarchy_status") or MEMORY_STATUS_ACTIVE),
        "hierarchy_applied": bool(source.get("hierarchy_applied")),
        "hierarchy_compliance": bool(source.get("hierarchy_compliance")),
        "gp_closure_allowed": bool(source.get("gp_closure_allowed")),
        "gp_closure_blocked": bool(source.get("gp_closure_blocked")),
        "current_stage": str(source.get("current_stage") or ""),
        "last_completed_stage": str(source.get("last_completed_stage") or ""),
        "blocking_reason": str(source.get("blocking_reason") or ""),
        "corrective_action_applied": list(source.get("corrective_action_applied") or [])[:20],
        "stage_results": safe_stage_results,
        "stage_failures": list(source.get("stage_failures") or [])[:20],
        "ml_verdict": str(source.get("ml_verdict") or ""),
        "ml_verdict_reason": str(source.get("ml_verdict_reason") or ""),
        "subordinate_missions_status": dict(source.get("subordinate_missions_status") or {}),
        "agent_routing_mission_id": str(source.get("agent_routing_mission_id") or ""),
        "agent_routing_matrix_version": str(source.get("agent_routing_matrix_version") or ""),
        "blocking_responsible_agent": str(source.get("blocking_responsible_agent") or ""),
        "stage_responsible_agents": list(source.get("stage_responsible_agents") or []),
    }


class MlOperationalHierarchyBlockedError(RuntimeError):
    """GP bloqueado pelas etapas 1–3 da hierarquia M-ML-073 (pré-compose_sovereign_gp)."""

    def __init__(self, message: str, *, hierarchy_bundle: Mapping[str, Any]) -> None:
        super().__init__(message)
        self.hierarchy_bundle = dict(hierarchy_bundle)

    @classmethod
    def from_bundle(cls, hierarchy_bundle: Mapping[str, Any]) -> MlOperationalHierarchyBlockedError:
        reason = str(hierarchy_bundle.get("blocking_reason") or "etapas 1–3 reprovadas")
        recovery = dict(hierarchy_bundle.get("pre_gp_recovery") or {})
        attempts = int(recovery.get("internal_recovery_attempts", 0) or 0)
        if recovery.get("internal_recovery_attempted") and attempts > 0:
            message = (
                "[M-ML-073/M-ML-074] Fechamento GP bloqueado após "
                f"{attempts} tentativas internas de recuperação pré-GP: {reason}"
            )
        else:
            message = (
                "[M-ML-073] Fechamento GP bloqueado pela hierarquia operacional ML: "
                f"{reason}"
            )
        return cls(message, hierarchy_bundle=hierarchy_bundle)


def is_ml_operational_hierarchy_block_error(exc: BaseException) -> bool:
    if isinstance(exc, MlOperationalHierarchyBlockedError):
        return True
    return str(exc).startswith("[M-ML-073]")


def resolve_failed_hierarchy_stage(hierarchy_bundle: Mapping[str, Any] | None) -> str:
    source = dict(hierarchy_bundle or {})
    stage_results = dict(source.get("stage_results") or {})
    for stage_id in (STAGE_CONFORMITY, STAGE_DIVERSITY, STAGE_COVERAGE):
        row = stage_results.get(stage_id)
        if isinstance(row, dict) and not row.get("passed"):
            return str(stage_id)
    return str(source.get("current_stage") or "")


def build_ml_hierarchy_block_operational_payload(
    hierarchy_bundle: Mapping[str, Any] | None,
    *,
    exception_message: str = "",
) -> dict[str, Any]:
    """Estado operacional seguro quando o GP é bloqueado antes do fechamento."""
    source = dict(hierarchy_bundle or {})
    failed_stage = resolve_failed_hierarchy_stage(source)
    stage_row = dict(source.get("stage_results", {}).get(failed_stage) or {})
    responsible_agent = str(
        source.get("blocking_responsible_agent")
        or stage_row.get("responsible_agent")
        or ""
    )
    supporting_agents = list(stage_row.get("support_agents") or [])
    trace = build_ml_operational_hierarchy_trace(source)
    category_map = {
        STAGE_CONFORMITY: "conformidade estrutural",
        STAGE_DIVERSITY: "diversidade / overlap",
        STAGE_COVERAGE: "cobertura estrutural",
    }
    return {
        "mission_id": "M-ML-073-FIX-01",
        "status": "GP BLOQUEADO PELA HIERARQUIA ML",
        "exception_message": str(exception_message or source.get("blocking_reason") or ""),
        "ml_hierarchy_version": str(source.get("ml_hierarchy_version") or HIERARCHY_VERSION),
        "hierarchy_compliance": bool(source.get("hierarchy_compliance")),
        "gp_closure_allowed": bool(source.get("gp_closure_allowed")),
        "current_stage": str(source.get("current_stage") or ""),
        "failed_stage": failed_stage,
        "failed_stage_label": str(stage_row.get("stage_label") or STAGE_LABELS.get(failed_stage, failed_stage)),
        "failure_category": category_map.get(failed_stage, "hierarquia operacional ML"),
        "stage_results": dict(trace.get("stage_results") or {}),
        "stage_failures": list(trace.get("stage_failures") or []),
        "corrective_action_applied": list(trace.get("corrective_action_applied") or []),
        "blocking_reason": str(source.get("blocking_reason") or ""),
        "responsible_agent": responsible_agent,
        "supporting_agents": supporting_agents,
        "primary_responsible_agent": responsible_agent,
        "agent_routing_matrix_version": str(source.get("agent_routing_matrix_version") or ""),
        "next_step": (
            "Gerar novo pool / ajustar geração / revisar diversidade e cobertura estrutural."
        ),
        "ml_operational_hierarchy_trace": trace,
        "no_final_lot_created": True,
        "pre_gp_block": True,
    }
