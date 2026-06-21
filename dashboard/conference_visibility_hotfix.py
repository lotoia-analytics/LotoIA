"""Hotfix de visibilidade do Conferir Resultados.

Garante que grupos/lotes com status `approved_with_warning` sejam tratados como
conferíveis mesmo quando o painel recebe um group com campos derivados zerados
(`is_official_conference_eligible=False`, `games_promoted_to_conference=0`).
"""

from __future__ import annotations

from typing import Any, Mapping

import lotoia.operations.lot_operational_status as lot_status

_STATUS_KEYS: tuple[str, ...] = (
    "lot_operational_status",
    "post_calibration_promotion_status",
    "operational_status",
    "officialization_status",
    "conference_status",
)


def _payload(context: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(context, Mapping):
        return {}
    nested = context.get("context_json")
    if isinstance(nested, Mapping):
        return {**dict(nested), **dict(context)}
    return dict(context)


def _resolved_status(context: Mapping[str, Any] | None) -> str:
    payload = _payload(context)
    for key in _STATUS_KEYS:
        status = str(payload.get(key) or "").strip().lower()
        if status:
            return status
    trace = payload.get("lot_status_trace")
    if isinstance(trace, Mapping):
        return str(trace.get("lot_operational_status") or "").strip().lower()
    return ""


def _legacy_allowed(context: Mapping[str, Any] | None) -> bool:
    payload = _payload(context)
    if not payload:
        return True
    if payload.get("official_release_allowed") is False:
        return False
    verdict = str(payload.get("ml_verdict") or lot_status.VERDICT_APROVADO).strip().upper()
    return verdict in {lot_status.VERDICT_APROVADO, lot_status.VERDICT_APROVADO_COM_ALERTA}


def is_official_conference_eligible(context: Mapping[str, Any] | None) -> bool:
    if not isinstance(context, Mapping):
        return True
    status = _resolved_status(context)
    if status:
        return status in lot_status.OFFICIAL_CONFERENCE_STATUSES
    return _legacy_allowed(context)


def is_analytical_history_eligible(context: Mapping[str, Any] | None) -> bool:
    if not isinstance(context, Mapping):
        return True
    status = _resolved_status(context)
    if status:
        return status in lot_status.ANALYTICAL_HISTORY_STATUSES
    return _legacy_allowed(context)


def apply_conference_visibility_hotfix() -> None:
    lot_status.is_official_conference_eligible = is_official_conference_eligible
    lot_status.is_analytical_history_eligible = is_analytical_history_eligible


apply_conference_visibility_hotfix()
