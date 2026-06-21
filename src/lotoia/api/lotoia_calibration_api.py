"""M-AUTO-CALIB-001 — API LotoIA: calibração autônoma governada por Cobertura Estrutural."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any, Mapping, Sequence

from lotoia.governance.batch_operational_scope import OPERATIONAL_STATUS_APPROVED
from lotoia.governance.lei15_core_002_sovereign import is_sovereign_core_label
from lotoia.ml.structural_auto_calibration import (
    build_auto_calibration_plan_from_pool,
    is_structural_auto_calibration_format,
)
from lotoia.ml.structural_policy_15d import (
    analyze_batch_structural_policy_15d,
    build_structural_policy_15d_calibration_plan,
)
from lotoia.observability.m_core_003_bias_monitoring import MODERATE_BIAS_RATIO_THRESHOLD
from lotoia.observability.structural_fidelity_analytics import (
    build_structural_intelligence_bundle,
    export_structural_diagnosis_for_lotoia_api,
)

MISSION_ID = "M-AUTO-CALIB-001"
API_VERSION = "v1"
FIDELITY_THRESHOLD = 90.0
BIAS_RATIO_THRESHOLD = float(MODERATE_BIAS_RATIO_THRESHOLD)
MAX_AUTO_RECALIB_ATTEMPTS = 1
CALIBRATION_ENGINE_ROLE = "LOTOIA_API_AUXILIARY"


def is_lotoia_auto_calib_api_enabled() -> bool:
    raw = str(os.getenv("LOTOIA_AUTO_CALIB_API_ENABLED", "1") or "1").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _max_bias_ratio(bias_report: Mapping[str, Any]) -> float:
    ratios = [
        float(row.get("ratio") or 0.0)
        for row in list(bias_report.get("ratio_rows") or [])
    ]
    return max(ratios) if ratios else 0.0


def _resolve_game_size(games: Sequence[Mapping[str, Any]]) -> int:
    if not games:
        return 15
    sample = dict(games[0])
    for key in ("card_format", "selected_card_format", "game_size"):
        value = int(sample.get(key, 0) or 0)
        if value > 0:
            return value
    numbers = list(sample.get("final_card_numbers") or sample.get("numbers") or [])
    return len(numbers) if numbers else 15


def evaluate_structural_sovereignty(
    games: Sequence[Mapping[str, Any]],
    *,
    db_path: Any = None,
    batch_label: str | None = None,
) -> dict[str, Any]:
    """Diagnóstico estrutural agnóstico — entrada principal da API LotoIA."""
    if not games:
        return {
            "mission_id": MISSION_ID,
            "api_version": API_VERSION,
            "available": False,
            "reason": "empty_games",
        }

    bundle = (
        build_structural_intelligence_bundle(db_path, games=games)
        if db_path is not None
        else {"available": False, "reason": "db_path_required"}
    )
    if not bundle.get("available"):
        return {
            "mission_id": MISSION_ID,
            "api_version": API_VERSION,
            "available": False,
            "reason": str(bundle.get("reason") or "bundle_unavailable"),
        }

    diagnosis = export_structural_diagnosis_for_lotoia_api(bundle)
    fidelity_score = float(diagnosis.get("structural_fidelity_score", 0.0) or 0.0)
    max_bias_ratio = float(diagnosis.get("max_bias_ratio", 0.0) or 0.0)
    sovereignty_passed = fidelity_score >= FIDELITY_THRESHOLD and max_bias_ratio < BIAS_RATIO_THRESHOLD
    requires_recalibration = not sovereignty_passed

    game_size = _resolve_game_size(games)
    correction_commands = build_correction_commands(diagnosis, game_size=game_size)

    return {
        "mission_id": MISSION_ID,
        "api_version": API_VERSION,
        "available": True,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "batch_label": str(batch_label or ""),
        "sovereign_batch": bool(is_sovereign_core_label(batch_label)),
        "game_size": game_size,
        "structural_fidelity_score": fidelity_score,
        "fidelity_status": diagnosis.get("fidelity_status"),
        "max_bias_ratio": max_bias_ratio,
        "sovereignty_passed": sovereignty_passed,
        "requires_recalibration": requires_recalibration,
        "thresholds": {
            "fidelity_min_pct": FIDELITY_THRESHOLD,
            "bias_ratio_max": BIAS_RATIO_THRESHOLD,
        },
        "correction_commands": correction_commands,
        "diagnosis": diagnosis,
        "insights": list(bundle.get("insights") or []),
    }


def build_correction_commands(
    diagnosis: Mapping[str, Any],
    *,
    game_size: int = 15,
) -> list[dict[str, Any]]:
    """Comandos de correção estrutural — agnósticos à interface visual."""
    commands: list[dict[str, Any]] = []
    quadrant_gaps = list(diagnosis.get("quadrant_gaps") or [])
    for gap in quadrant_gaps:
        label = str(gap.get("quadrant") or "")
        if label.startswith("Q1"):
            commands.append(
                {
                    "kind": "column_dispersion",
                    "target": "coluna_1",
                    "action": "dispersar_concentracao",
                    "message": (
                        f"Reduzir concentração em {label} — espalhar dezenas da coluna 1 do volante."
                    ),
                    "parametros": {
                        "quadrant_penalty_boost": 1.15,
                        "column_1_dispersion_boost": 1.12,
                    },
                }
            )
        else:
            commands.append(
                {
                    "kind": "quadrant_rebalance",
                    "target": label,
                    "action": "elevar_ocupacao",
                    "message": f"Elevar ocupação do quadrante {label} em direção ao perfil oficial.",
                    "parametros": {"quadrant_rebalance_boost": 1.10},
                }
            )

    for row in list(diagnosis.get("bias_patterns") or []):
        ratio = float(row.get("ratio") or 0.0)
        if ratio < BIAS_RATIO_THRESHOLD:
            continue
        kind = str(row.get("kind") or "pattern")
        pattern = str(row.get("pattern") or "")
        commands.append(
            {
                "kind": f"{kind}_bias",
                "target": pattern,
                "action": "penalizar_padrao",
                "message": f"Penalizar {kind} {pattern} ({ratio:.2f}x vs histórico).",
                "parametros": {
                    "pattern_penalty_boost": min(1.35, 1.0 + (ratio - 1.0) * 0.08),
                    "pattern_kind": kind,
                    "pattern": pattern,
                },
            }
        )

    if float(diagnosis.get("structural_fidelity_score", 0.0) or 0.0) < FIDELITY_THRESHOLD:
        commands.append(
            {
                "kind": "fidelity_recovery",
                "target": "global",
                "action": "recalibrar_ranking_auxiliar",
                "message": (
                    "Aplicar calibração auxiliar de ranking para aproximar perfil oficial."
                ),
                "parametros": {
                    "structural_fidelity_recovery_boost": 1.08,
                    "game_size": int(game_size),
                },
            }
        )

    return commands


def build_autonomous_calibration_plan(
    evaluation: Mapping[str, Any],
    games: Sequence[Mapping[str, Any]],
    *,
    game_size: int | None = None,
) -> dict[str, Any]:
    """Monta plano auxiliar de calibração a partir do diagnóstico da API."""
    size = int(game_size or _resolve_game_size(games))
    diagnosis = dict(evaluation.get("diagnosis") or evaluation)
    parametros: dict[str, Any] = {
        "game_size": size,
        "formato_alvo": f"{size}D",
        "lotoia_api_governed": True,
        "mission_id": MISSION_ID,
    }
    plan_items: list[str] = []
    impact_items: list[str] = []

    commands = list(
        evaluation.get("correction_commands")
        or build_correction_commands(diagnosis, game_size=size)
    )
    for command in commands:
        plan_items.append(str(command.get("message") or ""))
        impact_items.append(str(command.get("action") or "correcao_estrutural"))
        parametros.update(dict(command.get("parametros") or {}))

    if is_structural_auto_calibration_format(size):
        auto_plan = build_auto_calibration_plan_from_pool(list(games), game_size=size)
        if auto_plan.get("authorized"):
            plan_items.extend(str(item) for item in list(auto_plan.get("plan_items") or []))
            impact_items.extend(str(item) for item in list(auto_plan.get("impact_items") or []))
            parametros.update(dict(auto_plan.get("parametros_sugeridos") or {}))
    elif size == 15:
        analysis = analyze_batch_structural_policy_15d(list(games))
        policy_plan = build_structural_policy_15d_calibration_plan(analysis)
        plan_items.extend(str(item) for item in list(policy_plan.get("plan_items") or []))
        impact_items.extend(str(item) for item in list(policy_plan.get("impact_items") or []))
        parametros.update(dict(policy_plan.get("parametros_sugeridos") or {}))

    plan_items = [item for item in plan_items if item.strip()]
    if not plan_items:
        plan_items = [
            "Recalibrar ranking auxiliar com foco em dispersão estrutural e anti-viés M-CORE-003."
        ]
        impact_items = ["Aproximar lote do perfil oficial sem alterar Lei 15."]
        parametros.setdefault("structural_fidelity_recovery_boost", 1.08)

    return {
        "mission_id": MISSION_ID,
        "authorized": True,
        "auto_authorized": True,
        "governed_by": "lotoia_api",
        "plan_items": plan_items,
        "impact_items": impact_items,
        "parametros_sugeridos": parametros,
        "calibration_engine_role": CALIBRATION_ENGINE_ROLE,
    }


def persist_api_governed_calibration_plan(
    plan: Mapping[str, Any],
    *,
    db_path: Any,
    source_generation_event_id: int = 0,
) -> dict[str, Any]:
    from lotoia.ml.authorized_ml_calibration_plan import persist_authorized_ml_calibration_plan

    return persist_authorized_ml_calibration_plan(
        source_generation_event_id=int(source_generation_event_id or 0),
        parametros_sugeridos=dict(plan.get("parametros_sugeridos") or {}),
        plan_items=list(plan.get("plan_items") or []),
        db_path=db_path,
        target_format=str(plan.get("parametros_sugeridos", {}).get("formato_alvo", "15D") or "15D"),
        apply_to_next_generation=True,
        authorized_by_operator=False,
        operator="lotoia_api",
        calibration_plan=dict(plan),
        evidencias=[f"API LotoIA {MISSION_ID}"],
        problemas_detectados=list(plan.get("impact_items") or []),
        responsible_agent="agent_plataforma",
    )


def build_external_agent_payload(
    evaluation: Mapping[str, Any],
    *,
    governance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """JSON padronizado para Telegram, Manus, GPT e outros agentes externos."""
    diagnosis = dict(evaluation.get("diagnosis") or {})
    return {
        "schema": "lotoia.calibration.v1",
        "mission_id": MISSION_ID,
        "api_version": API_VERSION,
        "timestamp": evaluation.get("evaluated_at") or datetime.now(UTC).isoformat(),
        "verdict": {
            "sovereignty_passed": bool(evaluation.get("sovereignty_passed")),
            "requires_recalibration": bool(evaluation.get("requires_recalibration")),
            "structural_fidelity_score": float(evaluation.get("structural_fidelity_score", 0.0) or 0.0),
            "max_bias_ratio": float(evaluation.get("max_bias_ratio", 0.0) or 0.0),
            "status": diagnosis.get("fidelity_status", {}).get("level", "unknown"),
        },
        "correction_commands": list(evaluation.get("correction_commands") or []),
        "governance": dict(governance or {}),
        "insights": list(evaluation.get("insights") or []),
        "integration_hints": {
            "telegram": "Use verdict.requires_recalibration para decidir se notifica operador.",
            "next_action": (
                "regenerate_with_calibration_plan"
                if evaluation.get("requires_recalibration")
                else "officialize_batch"
            ),
        },
    }


def process_sovereign_payload_with_lotoia_api(
    payload: Mapping[str, Any],
    *,
    games: Sequence[Mapping[str, Any]],
    batch_label: str | None,
    db_path: Any = None,
    auto_calib_attempt: int = 0,
) -> dict[str, Any]:
    """Hook pós-geração soberana — avalia, recalibra ou oficializa via API LotoIA."""
    if not is_lotoia_auto_calib_api_enabled():
        return {"should_regenerate": False, "payload_patch": {}}

    evaluation = evaluate_structural_sovereignty(
        games,
        db_path=db_path,
        batch_label=batch_label,
    )
    if not evaluation.get("available"):
        return {"should_regenerate": False, "payload_patch": {}}

    audit_log: list[dict[str, Any]] = [
        {
            "event": "structural_evaluation",
            "at": evaluation.get("evaluated_at"),
            "sovereignty_passed": evaluation.get("sovereignty_passed"),
            "fidelity_score": evaluation.get("structural_fidelity_score"),
            "max_bias_ratio": evaluation.get("max_bias_ratio"),
        }
    ]

    governance: dict[str, Any] = {
        "mission_id": MISSION_ID,
        "api_version": API_VERSION,
        "governed_by": "lotoia_api",
        "calibration_engine_role": CALIBRATION_ENGINE_ROLE,
        "sovereignty_passed": bool(evaluation.get("sovereignty_passed")),
        "requires_recalibration": bool(evaluation.get("requires_recalibration")),
        "auto_recalibrated": False,
        "auto_officialized": False,
        "auto_calib_attempt": int(auto_calib_attempt),
        "structural_fidelity_score": evaluation.get("structural_fidelity_score"),
        "max_bias_ratio": evaluation.get("max_bias_ratio"),
        "audit_log": audit_log,
    }

    memory_patch: dict[str, Any] = {}
    memory_snapshot = dict(payload.get("operational_structural_memory_snapshot") or {})
    if memory_snapshot.get("available"):
        coverage = dict(memory_snapshot.get("coverage_snapshot") or {})
        coverage["lotoia_api_governance"] = dict(governance)
        memory_snapshot["coverage_snapshot"] = coverage
        memory_snapshot["lotoia_api_governed"] = True
        memory_patch["operational_structural_memory_snapshot"] = memory_snapshot

    if evaluation.get("requires_recalibration") and int(auto_calib_attempt) < MAX_AUTO_RECALIB_ATTEMPTS:
        plan = build_autonomous_calibration_plan(evaluation, games)
        persisted: dict[str, Any] = {}
        if db_path is not None:
            persisted = persist_api_governed_calibration_plan(
                plan,
                db_path=db_path,
            )
        audit_log.append(
            {
                "event": "autonomous_recalibration_scheduled",
                "at": datetime.now(UTC).isoformat(),
                "trace_id": persisted.get("calibration_trace_id"),
                "plan_items_count": len(plan.get("plan_items") or []),
            }
        )
        governance["auto_recalibrated"] = True
        governance["calibration_trace_id"] = persisted.get("calibration_trace_id")
        governance["audit_log"] = audit_log
        calibration_plan = {
            **plan,
            "trace": {
                "mission_id": MISSION_ID,
                "governed_by": "lotoia_api",
                "loaded_from_db": bool(persisted),
                "calibration_trace_id": persisted.get("calibration_trace_id"),
            },
            "calibration_plan_loaded_from_db": bool(persisted),
            "authorized": True,
        }
        external_payload = build_external_agent_payload(evaluation, governance=governance)
        return {
            "should_regenerate": True,
            "calibration_plan": calibration_plan,
            "payload_patch": {
                **memory_patch,
                "lotoia_api_governance": governance,
                "lotoia_api_external_payload": external_payload,
                "authorized_calibration_plan": calibration_plan,
                "calibration_authorized": True,
                "calibration_engine_role": CALIBRATION_ENGINE_ROLE,
            },
        }

    if evaluation.get("sovereignty_passed"):
        governance["auto_officialized"] = True
        governance["officialization_status"] = OPERATIONAL_STATUS_APPROVED
        governance["ml_verdict_override"] = "APROVADO_API_LOTOIA"
        audit_log.append(
            {
                "event": "autonomous_officialization",
                "at": datetime.now(UTC).isoformat(),
                "officialization_status": OPERATIONAL_STATUS_APPROVED,
            }
        )
        governance["audit_log"] = audit_log

    external_payload = build_external_agent_payload(evaluation, governance=governance)
    return {
        "should_regenerate": False,
        "payload_patch": {
            **memory_patch,
            "lotoia_api_governance": governance,
            "lotoia_api_external_payload": external_payload,
            "calibration_authorized": bool(evaluation.get("sovereignty_passed")),
            "official_release_allowed": bool(evaluation.get("sovereignty_passed")),
            "calibration_engine_role": CALIBRATION_ENGINE_ROLE,
        },
    }
