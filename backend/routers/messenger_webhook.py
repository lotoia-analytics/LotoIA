from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, Response

from lotoia.clients.messenger_service import deliver_messenger_webhook
from lotoia.database.database import DEFAULT_DATABASE_PATH

router = APIRouter(tags=["messenger"])
logger = logging.getLogger(__name__)


def _messenger_verify_token() -> str:
    return str(os.getenv("MESSENGER_VERIFY_TOKEN", "") or "").strip()


@router.get("/webhook")
async def messenger_verify(
    hub_mode: str = Query(default="", alias="hub.mode"),
    hub_token: str = Query(default="", alias="hub.verify_token"),
    hub_challenge: str = Query(default="", alias="hub.challenge"),
) -> Response:
    """Meta webhook verification — retorna hub.challenge em texto puro."""
    _ = hub_mode
    expected = _messenger_verify_token()
    if not expected or hub_token != expected:
        raise HTTPException(status_code=403, detail="Invalid verify token.")
    return Response(content=str(hub_challenge), media_type="text/plain")


@router.post("/webhook")
async def messenger_receive(payload: dict[str, Any]) -> JSONResponse:
    try:
        result = deliver_messenger_webhook(payload, db_path=DEFAULT_DATABASE_PATH)
    except Exception as exc:  # noqa: BLE001 - Meta/Evolution require HTTP 200
        logger.exception("Unhandled Messenger webhook error: %s", exc)
        result = {
            "status": "error",
            "error_code": "WEBHOOK_PROCESSING_ERROR",
            "delivered": False,
        }
    return JSONResponse(status_code=200, content=result)
