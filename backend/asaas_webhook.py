from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from lotoia.clients.asaas_webhook import is_valid_webhook_token, process_asaas_webhook
from lotoia.database.database import DEFAULT_DATABASE_PATH

router = APIRouter(tags=["asaas"])
logger = logging.getLogger(__name__)


@router.post("/asaas/webhook")
def asaas_webhook(request: Request, payload: dict[str, Any]) -> JSONResponse:
    expected_token = str(os.getenv("ASAAS_WEBHOOK_TOKEN", "") or "").strip()
    received_token = str(request.headers.get("asaas-access-token") or "").strip()
    if not is_valid_webhook_token(received_token, expected_token):
        raise HTTPException(status_code=401, detail="Token de webhook inválido.")

    try:
        result = process_asaas_webhook(payload, db_path=DEFAULT_DATABASE_PATH)
    except Exception as exc:  # noqa: BLE001 - Asaas expects a stable HTTP response
        logger.exception("Unhandled Asaas webhook error: %s", exc)
        result = {
            "status": "error",
            "error_code": "WEBHOOK_PROCESSING_ERROR",
            "message": str(exc),
        }

    return JSONResponse(status_code=200, content=result)
