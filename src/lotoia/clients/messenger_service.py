from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from lotoia.clients.messenger_consultor.consultor_service import (
    extract_messenger_payload,
    process_messenger_consultor_webhook,
)
from lotoia.clients.messenger_evolution_service import MessengerEvolutionService

logger = logging.getLogger(__name__)


def process_messenger_webhook(
    payload: dict[str, Any],
    *,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Processa webhook Messenger via consultor M-092B."""
    from lotoia.database.database import DEFAULT_DATABASE_PATH

    resolved_db = db_path or DEFAULT_DATABASE_PATH
    return process_messenger_consultor_webhook(payload, db_path=resolved_db)


def deliver_messenger_webhook(
    payload: dict[str, Any],
    *,
    db_path: Path | None = None,
    messenger_client: MessengerEvolutionService | None = None,
) -> dict[str, Any]:
    from lotoia.database.database import DEFAULT_DATABASE_PATH

    resolved_db = db_path or DEFAULT_DATABASE_PATH
    result = dict(process_messenger_webhook(payload, db_path=resolved_db))
    status = str(result.get("status", "") or "")
    psid = str(result.get("psid") or "")
    client = messenger_client or MessengerEvolutionService()
    delivered = False
    delivery_error = ""

    if status == "ignored":
        result["delivered"] = False
        result["delivery_skipped"] = True
        return result

    try:
        message = str(result.get("message") or "").strip()
        if psid and message:
            delivered = client.send_text_sync(psid, message)
        if not delivered and psid and status in {"ok", "onboarding", "error", "prompt", "menu"}:
            delivery_error = client.last_error_message or "MESSENGER_DELIVERY_FAILED"
    except Exception as exc:  # noqa: BLE001
        delivery_error = str(exc)
        logger.exception("MESSENGER_DELIVERY_ERROR for psid=%s: %s", psid, exc)

    result["delivered"] = delivered
    if delivery_error:
        result["delivery_error"] = delivery_error
    return result


__all__ = ["deliver_messenger_webhook", "extract_messenger_payload", "process_messenger_webhook"]
