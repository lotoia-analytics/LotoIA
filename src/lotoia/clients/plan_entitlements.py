from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, Mapping

from lotoia.clients.constants import DEFAULT_PLAN_ID, LEGACY_PLAN_ALIASES, LEGACY_PLANS, PLANS


def normalize_plan_key(plan: str | None) -> str:
    return str(plan or DEFAULT_PLAN_ID).strip().lower()


def is_valid_activation_plan(plan: str | None) -> bool:
    key = normalize_plan_key(plan)
    return key in PLANS or key in LEGACY_PLAN_ALIASES


def resolve_plan_for_activation(plan: str | None) -> str:
    key = normalize_plan_key(plan)
    if key in PLANS:
        return key
    if key in LEGACY_PLAN_ALIASES:
        return LEGACY_PLAN_ALIASES[key]
    raise ValueError(f"Plano inválido: {plan}")


def is_legacy_plan(plan: str | None) -> bool:
    return normalize_plan_key(plan) in LEGACY_PLANS


def _coerce_datetime(value: datetime | date | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=UTC)
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def days_since_start(client: Mapping[str, Any]) -> int:
    started_at = _coerce_datetime(client.get("data_inicio"))
    if started_at is None:
        return 0
    return max((datetime.now(UTC).date() - started_at.astimezone(UTC).date()).days, 0)


def is_trial_phase(client: Mapping[str, Any]) -> bool:
    plan_key = normalize_plan_key(str(client.get("plan") or ""))
    if plan_key != DEFAULT_PLAN_ID:
        return False
    plan_config = PLANS[DEFAULT_PLAN_ID]
    trial_days = int(plan_config.get("trial_days", 0) or 0)
    return trial_days > 0 and days_since_start(client) < trial_days


def trial_days_remaining(client: Mapping[str, Any]) -> int:
    if not is_trial_phase(client):
        return 0
    plan_config = PLANS[DEFAULT_PLAN_ID]
    trial_days = int(plan_config.get("trial_days", 0) or 0)
    return max(trial_days - days_since_start(client), 0)


def effective_formato_maximo(client: Mapping[str, Any]) -> int:
    plan_key = normalize_plan_key(str(client.get("plan") or ""))
    if plan_key == DEFAULT_PLAN_ID:
        plan_config = PLANS[DEFAULT_PLAN_ID]
        if is_trial_phase(client):
            return int(plan_config.get("trial_formato_max", 15) or 15)
        return int(plan_config.get("formato_max", 20) or 20)
    if plan_key in LEGACY_PLANS:
        return int(client.get("formato_maximo", LEGACY_PLANS[plan_key]["formato_max"]) or 15)
    return int(client.get("formato_maximo", 15) or 15)


def effective_formats_label(client: Mapping[str, Any]) -> str:
    plan_key = normalize_plan_key(str(client.get("plan") or ""))
    if plan_key == DEFAULT_PLAN_ID:
        if is_trial_phase(client):
            return "15D (fase inicial — 7 dias)"
        return str(PLANS[DEFAULT_PLAN_ID].get("formats") or "15D + 20D")
    if plan_key in LEGACY_PLANS:
        return str(LEGACY_PLANS[plan_key].get("formats") or f"{effective_formato_maximo(client)}D")
    return f"até {effective_formato_maximo(client)}D"


def subscription_duration_days(plan: str | None) -> int:
    plan_key = resolve_plan_for_activation(plan)
    plan_config = PLANS[plan_key]
    return int(plan_config.get("subscription_days", 372) or 372)


def enrich_client_entitlements(client: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(client)
    payload["formato_maximo_efetivo"] = effective_formato_maximo(client)
    payload["formatos_disponiveis"] = effective_formats_label(client)
    payload["fase"] = "trial" if is_trial_phase(client) else "completo"
    payload["dias_trial_restantes"] = trial_days_remaining(client)
    return payload
