from __future__ import annotations

import logging
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from lotoia.clients.constants import PLANS
from lotoia.clients.plan_entitlements import resolve_plan_for_activation
from lotoia.clients.evolution_client import EvolutionApiClient
from lotoia.clients.phone_utils import canonical_brazil_phone
from lotoia.clients.whatsapp_service import activate_client
from lotoia.database.database import DEFAULT_DATABASE_PATH

logger = logging.getLogger(__name__)

ACTIVATION_EVENTS = frozenset({"PAYMENT_RECEIVED", "PAYMENT_CONFIRMED"})
EXTERNAL_REF_PATTERN = re.compile(r"^lotoia:([a-z]+):(55\d+)$", re.IGNORECASE)

_PROCESSED_PAYMENTS: dict[str, datetime] = {}
_IDEMPOTENCY_TTL = timedelta(days=7)


def parse_external_reference(value: str) -> tuple[str, str] | None:
    match = EXTERNAL_REF_PATTERN.match(str(value or "").strip())
    if not match:
        return None
    plan = match.group(1).lower()
    phone = canonical_brazil_phone(match.group(2))
    return plan, phone


def is_valid_webhook_token(received: str, expected: str) -> bool:
    expected_token = str(expected or "").strip()
    if not expected_token:
        return True
    return str(received or "").strip() == expected_token


def build_activation_message(*, plan: str, name: str = "") -> str:
    greeting = f"Olá, {name}!" if str(name or "").strip() else "Olá!"
    resolved_plan = resolve_plan_for_activation(plan)
    return (
        f"{greeting}\n\n"
        "✅ Pagamento confirmado. Seu plano LotoIA Completo está ativo.\n\n"
        "• 7 primeiros dias: 30 jogos/dia em 15D\n"
        "• Depois: 30 jogos/dia em 15D + 20D por 12 meses\n\n"
        "Mande olá agora para gerar seus jogos."
        if resolved_plan == "completo"
        else (
            f"{greeting}\n\n"
            f"✅ Pagamento confirmado. Seu plano {resolved_plan} está ativo.\n\n"
            "Mande olá agora para gerar seus jogos."
        )
    )


def _cleanup_processed_payments() -> None:
    cutoff = datetime.now(UTC) - _IDEMPOTENCY_TTL
    expired = [payment_id for payment_id, seen_at in _PROCESSED_PAYMENTS.items() if seen_at < cutoff]
    for payment_id in expired:
        _PROCESSED_PAYMENTS.pop(payment_id, None)


def _was_payment_processed(payment_id: str) -> bool:
    if not payment_id:
        return False
    _cleanup_processed_payments()
    return payment_id in _PROCESSED_PAYMENTS


def _mark_payment_processed(payment_id: str) -> None:
    if not payment_id:
        return
    _cleanup_processed_payments()
    _PROCESSED_PAYMENTS[payment_id] = datetime.now(UTC)


def _resolve_customer_name(payment: dict[str, Any]) -> str:
    customer_id = str(payment.get("customer") or "").strip()
    if not customer_id:
        return ""

    api_key = str(os.getenv("ASAAS_API_KEY", "") or "").strip()
    if not api_key:
        return ""

    base_url = str(os.getenv("ASAAS_API_URL", "https://api.asaas.com/v3") or "").rstrip("/")
    try:
        response = requests.get(
            f"{base_url}/customers/{customer_id}",
            headers={
                "access_token": api_key,
                "User-Agent": "LotoIA-Webhook/1.0",
            },
            timeout=10,
        )
        if response.ok:
            return str(response.json().get("name") or "").strip()
    except Exception:
        logger.exception("Failed to fetch Asaas customer %s", customer_id)
    return ""


def process_asaas_webhook(
    payload: dict[str, Any],
    *,
    db_path: Path = DEFAULT_DATABASE_PATH,
    evolution_client: EvolutionApiClient | None = None,
) -> dict[str, Any]:
    event = str(payload.get("event") or "").strip()
    if event not in ACTIVATION_EVENTS:
        return {
            "status": "ignored",
            "reason": "event_not_handled",
            "event": event,
        }

    payment = dict(payload.get("payment") or {})
    payment_id = str(payment.get("id") or "").strip()
    if payment_id and _was_payment_processed(payment_id):
        return {
            "status": "ignored",
            "reason": "duplicate_payment",
            "payment_id": payment_id,
            "event": event,
        }

    external_reference = str(payment.get("externalReference") or "").strip()
    parsed = parse_external_reference(external_reference)
    if not parsed:
        return {
            "status": "ignored",
            "reason": "external_reference_not_lotoia",
            "event": event,
            "external_reference": external_reference,
        }

    plan, phone = parsed
    resolved_plan = resolve_plan_for_activation(plan)
    if resolved_plan not in PLANS:
        return {
            "status": "error",
            "error_code": "INVALID_PLAN",
            "event": event,
            "plan": plan,
            "phone": phone,
        }

    valor_pago = float(payment.get("value") or 0)
    customer_name = _resolve_customer_name(payment)

    try:
        activation = activate_client(
            phone=phone,
            plan=resolved_plan,
            valor_pago=valor_pago,
            name=customer_name,
            db_path=db_path,
        )
    except ValueError as exc:
        return {
            "status": "error",
            "error_code": "ACTIVATION_FAILED",
            "event": event,
            "phone": phone,
            "plan": plan,
            "message": str(exc),
        }

    if payment_id:
        _mark_payment_processed(payment_id)

    client = evolution_client or EvolutionApiClient()
    welcome_message = build_activation_message(plan=resolved_plan, name=customer_name)
    welcome_delivered = client.send_text(phone, welcome_message)

    return {
        "status": "ok",
        "event": event,
        "payment_id": payment_id,
        "phone": phone,
        "plan": resolved_plan,
        "activation": activation,
        "welcome_delivered": welcome_delivered,
    }
