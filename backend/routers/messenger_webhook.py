from __future__ import annotations

import logging
import os
from typing import Any

import requests
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, Response

from lotoia.clients.messenger_evolution_service import MessengerEvolutionService
from lotoia.clients.messenger_service import deliver_messenger_webhook
from lotoia.database.database import DEFAULT_DATABASE_PATH

router = APIRouter(tags=["messenger"])
logger = logging.getLogger(__name__)

MESSENGER_OUTBOUND_MODE = "graph_api_v1"


def _messenger_verify_token() -> str:
    return str(os.getenv("MESSENGER_VERIFY_TOKEN", "") or "").strip()


def _page_token_health() -> dict[str, object]:
    token = str(os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "") or "").strip()
    page_id = str(os.getenv("FACEBOOK_PAGE_ID", "") or "").strip()
    if not token:
        return {"valid": False, "reason": "missing_token"}
    try:
        response = requests.get(
            "https://graph.facebook.com/v21.0/me",
            params={"fields": "id,name", "access_token": token},
            timeout=8,
        )
        payload = response.json()
        if not response.ok:
            error = dict(payload.get("error") or {})
            return {
                "valid": False,
                "reason": str(error.get("message") or "graph_api_error"),
                "code": error.get("code"),
            }
        graph_page_id = str(payload.get("id") or "")
        return {
            "valid": True,
            "page_name": str(payload.get("name") or ""),
            "page_id_match": bool(page_id and graph_page_id == page_id),
            "page_id_suffix": graph_page_id[-4:] if graph_page_id else "",
        }
    except Exception as exc:  # noqa: BLE001 - diagnostic endpoint boundary
        return {"valid": False, "reason": str(exc)}


def _webhook_subscription_health() -> dict[str, object]:
    token = str(os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "") or "").strip()
    page_id = str(os.getenv("FACEBOOK_PAGE_ID", "") or "").strip()
    if not token or not page_id:
        return {"subscribed": False, "reason": "missing_page_or_token"}
    try:
        response = requests.get(
            f"https://graph.facebook.com/v21.0/{page_id}/subscribed_apps",
            params={"access_token": token},
            timeout=8,
        )
        payload = response.json()
        if not response.ok:
            error = dict(payload.get("error") or {})
            return {
                "subscribed": False,
                "reason": str(error.get("message") or "graph_api_error"),
            }
        apps = list(payload.get("data") or [])
        return {"subscribed": bool(apps), "apps_count": len(apps)}
    except Exception as exc:  # noqa: BLE001 - diagnostic endpoint boundary
        return {"subscribed": False, "reason": str(exc)}


@router.get("/status")
async def messenger_status() -> dict[str, object]:
    """Diagnóstico seguro (sem expor segredos) para setup Messenger."""
    client = MessengerEvolutionService()
    page_id = str(os.getenv("FACEBOOK_PAGE_ID", "") or "").strip()
    token_health = _page_token_health()
    subscription_health = _webhook_subscription_health()
    return {
        "ok": True,
        "outbound_mode": MESSENGER_OUTBOUND_MODE,
        "verify_token_configured": bool(_messenger_verify_token()),
        "graph_api_configured": client.uses_graph_api,
        "evolution_fallback_configured": client.uses_evolution,
        "page_id_configured": bool(page_id),
        "page_id_suffix": page_id[-4:] if page_id else "",
        "page_token": token_health,
        "webhook_subscription": subscription_health,
    }


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
    logger.info(
        "Messenger webhook processed status=%s delivered=%s delivery_error=%s",
        result.get("status"),
        result.get("delivered"),
        result.get("delivery_error") or result.get("error_code"),
    )
    return JSONResponse(status_code=200, content=result)
