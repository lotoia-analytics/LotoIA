"""Roteamento institucional da geração Lei 15 — path único CORE_002 (ADR-047).

Registro: LEI15_GENERATION_ROUTING_ADR_047
Agente: agent_geracao

Regras:
  - Único caminho operacional: label soberano STRUCT_LEI15_CORE_CANDIDATE_002_15D_001
  - batch_label=None bloqueado (legacy default)
  - V1/V2/V3/V4/CAND-001/baseline: evidência histórica — sem geração operacional
  - V1 active global bloqueado
  - Geração exige LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=1
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Final

REGISTRY_ID: Final = "LEI15_GENERATION_ROUTING_ADR_047"
ADR_REFERENCE: Final = "ADR-047-TRANSICAO-CONSTITUCIONAL-LEI15-CORE002"
SOVEREIGN_GENERATION_PATH: Final = "LEI15_CORE_002"
SOVEREIGN_BATCH_TYPE: Final = "LEI15_CORE_002_SOVEREIGN"

_HISTORICAL_LABEL_PATTERNS: Final = (
    re.compile(r"^STRUCT_TEST_\d+D(?:_\d+)?$"),
    re.compile(r"^STRUCT_REALIGN_V\d+_\d+D_\d+$"),
    re.compile(r"^STRUCT_CORE_REALIGN_V\d+(?:_[A-Z_]+)?_\d+D_\d+$"),
    re.compile(r"^STRUCT_LEI15_CORE_V\d+(?:_\d+)?(?:_[A-Z0-9_]+)?_\d+D_\d+$"),
    re.compile(r"^STRUCT_LEI15_CORE_CANDIDATE_001(?:_[ABCD])?_\d+D_\d+$"),
)


@dataclass(frozen=True, slots=True)
class GenerationRoutingDecision:
    allowed: bool
    apply_sovereign_core_002: bool
    batch_label: str | None
    batch_type: str | None
    generation_path: str
    legacy_path_blocked: bool
    v1_active_global_blocked: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize_label(batch_label: str | None) -> str:
    return str(batch_label or "").strip().upper()


def is_historical_evidence_label(batch_label: str | None) -> bool:
    """Labels institucionais de evidência — consultáveis, não operacionais isolados."""
    from lotoia.governance.analysis_batch_labels import ALLOWED_BATCH_LABELS, LEGACY_BATCH_LABELS
    from lotoia.governance.lei15_core_002_sovereign import is_sovereign_core_label
    from lotoia.governance.lei15_legacy_core_baseline import is_legacy_core_frozen_label

    normalized = _normalize_label(batch_label)
    if not normalized or is_sovereign_core_label(normalized):
        return False
    if normalized in ALLOWED_BATCH_LABELS or normalized in LEGACY_BATCH_LABELS:
        return True
    if is_legacy_core_frozen_label(normalized):
        return True
    return any(pattern.match(normalized) for pattern in _HISTORICAL_LABEL_PATTERNS)


def assert_v1_active_global_blocked(*, source: str) -> None:
    from lotoia.governance.law15_structural_realignment_v1 import get_realignment_mode

    if get_realignment_mode() == "active":
        raise RuntimeError(
            f"[{REGISTRY_ID}] V1 active global bloqueado (origem={source!r}). "
            f"LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1=active não pode sequestrar GP Lei 15. "
            f"V1 atua somente via v1_selection_compose dentro do LEI15_CORE_002. "
            f"Referência: {ADR_REFERENCE}."
        )


def resolve_generation_routing(batch_label: str | None) -> GenerationRoutingDecision:
    """Resolve roteamento sem executar geração."""
    from lotoia.governance.lei15_core_002_sovereign import (
        BATCH_LABEL as SOVEREIGN_LABEL,
        is_generation_enabled,
        is_sovereign_core_label,
        is_sovereign_implanted,
    )
    from lotoia.governance.analysis_batch_labels import infer_batch_type

    normalized = _normalize_label(batch_label)
    v1_blocked = True

    if not normalized:
        return GenerationRoutingDecision(
            allowed=False,
            apply_sovereign_core_002=False,
            batch_label=None,
            batch_type=None,
            generation_path="blocked",
            legacy_path_blocked=True,
            v1_active_global_blocked=v1_blocked,
            reason="batch_label=None — legacy default operacional bloqueado",
        )

    if not is_sovereign_implanted():
        return GenerationRoutingDecision(
            allowed=False,
            apply_sovereign_core_002=False,
            batch_label=normalized,
            batch_type=None,
            generation_path="blocked",
            legacy_path_blocked=True,
            v1_active_global_blocked=v1_blocked,
            reason="LEI15_CORE_002 não implantado (LOTOIA_LEI15_CORE_002!=sovereign)",
        )

    if not is_sovereign_core_label(normalized):
        if is_historical_evidence_label(normalized):
            reason = (
                f"label={normalized!r} é evidência histórica — não caminho operacional soberano"
            )
        else:
            reason = f"label={normalized!r} desconhecido — fail-closed"
        return GenerationRoutingDecision(
            allowed=False,
            apply_sovereign_core_002=False,
            batch_label=normalized,
            batch_type=infer_batch_type(normalized),
            generation_path="blocked",
            legacy_path_blocked=True,
            v1_active_global_blocked=v1_blocked,
            reason=reason,
        )

    if not is_generation_enabled():
        return GenerationRoutingDecision(
            allowed=False,
            apply_sovereign_core_002=True,
            batch_label=SOVEREIGN_LABEL,
            batch_type=SOVEREIGN_BATCH_TYPE,
            generation_path=SOVEREIGN_GENERATION_PATH,
            legacy_path_blocked=True,
            v1_active_global_blocked=v1_blocked,
            reason=f"geração bloqueada — LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=0",
        )

    return GenerationRoutingDecision(
        allowed=True,
        apply_sovereign_core_002=True,
        batch_label=SOVEREIGN_LABEL,
        batch_type=SOVEREIGN_BATCH_TYPE,
        generation_path=SOVEREIGN_GENERATION_PATH,
        legacy_path_blocked=True,
        v1_active_global_blocked=v1_blocked,
        reason="path único LEI15_CORE_002 autorizado",
    )


def enforce_lei15_generation_routing(
    batch_label: str | None,
    *,
    source: str,
    new_legacy_events: int = 1,
) -> GenerationRoutingDecision:
    """Fail-closed antes de qualquer geração Lei 15."""
    assert_v1_active_global_blocked(source=source)

    decision = resolve_generation_routing(batch_label)
    if is_historical_evidence_label(batch_label):
        from lotoia.governance.lei15_legacy_core_baseline import assert_no_new_legacy_extensive_lot

        assert_no_new_legacy_extensive_lot(batch_label=batch_label, new_events=new_legacy_events)

    if not decision.allowed:
        raise RuntimeError(
            f"[{REGISTRY_ID}] Geração Lei 15 bloqueada (origem={source!r}). "
            f"{decision.reason}. "
            f"Caminho válido futuro: generate_best_games("
            f'batch_label="STRUCT_LEI15_CORE_CANDIDATE_002_15D_001") '
            f"com {ADR_REFERENCE}."
        )
    return decision


def enforce_legacy_lei15_entry_blocked(*, source: str) -> None:
    """Bloqueia entradas legadas sem label soberano (_generate_filtered, API GET, etc.)."""
    enforce_lei15_generation_routing(None, source=source)


def effective_should_apply_gp_realignment(
    batch_label: str | None,
    *,
    apply_sovereign: bool,
) -> bool:
    """V1 compose global desabilitado — CORE_002 usa v1_selection_compose interno."""
    if apply_sovereign:
        return False
    from lotoia.governance.law15_structural_realignment_v1 import should_apply_gp_realignment

    assert_v1_active_global_blocked(source="effective_should_apply_gp_realignment")
    return should_apply_gp_realignment(batch_label)


def build_generation_routing_payload(
    decision: GenerationRoutingDecision,
) -> dict[str, Any]:
    from lotoia.governance.lei15_core_002_sovereign import SOVEREIGN_STATUS

    return {
        "lei15_core_002_applied": decision.apply_sovereign_core_002,
        "sovereign_core_status": SOVEREIGN_STATUS if decision.apply_sovereign_core_002 else None,
        "batch_label": decision.batch_label,
        "batch_type": decision.batch_type,
        "generation_path": decision.generation_path,
        "legacy_path_blocked": decision.legacy_path_blocked,
        "v1_active_global_blocked": decision.v1_active_global_blocked,
        "routing_registry": REGISTRY_ID,
        "routing_adr": ADR_REFERENCE,
    }


def attach_routing_payload_to_games(
    games: list[dict[str, Any]],
    decision: GenerationRoutingDecision,
) -> None:
    payload = build_generation_routing_payload(decision)
    for game in games:
        game.update(payload)
        meta = dict(game.get("lei15_generation_routing") or {})
        meta.update(payload)
        game["lei15_generation_routing"] = meta


def institutional_routing_report() -> dict[str, Any]:
    from lotoia.governance.lei15_core_002_sovereign import (
        BATCH_LABEL,
        ENV_GENERATION_ENABLED,
        institutional_status_report,
    )
    from lotoia.governance.history_preservation_policy import get_protected_batch_labels

    none_decision = resolve_generation_routing(None)
    sovereign_decision = resolve_generation_routing(BATCH_LABEL)
    v1_decision = resolve_generation_routing("STRUCT_REALIGN_V1_15D_001")
    legacy_decision = resolve_generation_routing("STRUCT_TEST_15D_001")

    return {
        "registry": REGISTRY_ID,
        "adr": ADR_REFERENCE,
        "sovereign_label": BATCH_LABEL,
        "sovereign_batch_type": SOVEREIGN_BATCH_TYPE,
        "generation_enabled_env": ENV_GENERATION_ENABLED,
        "core_002_status": institutional_status_report(),
        "protected_historical_labels_count": len(get_protected_batch_labels()),
        "routing_matrix": {
            "batch_label_none": none_decision.to_dict(),
            "sovereign_label": sovereign_decision.to_dict(),
            "v1_evidence_label": v1_decision.to_dict(),
            "legacy_baseline_label": legacy_decision.to_dict(),
        },
        "confirmations": {
            "legacy_default_blocked": not none_decision.allowed,
            "historical_v1_blocked": not v1_decision.allowed,
            "legacy_baseline_blocked": not legacy_decision.allowed,
            "sovereign_routes_core_002": sovereign_decision.apply_sovereign_core_002,
            "generation_blocked_by_flag": not sovereign_decision.allowed,
            "v1_active_global_blocked_policy": True,
        },
    }
