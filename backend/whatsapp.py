from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse

from lotoia.clients.plan_entitlements import is_valid_activation_plan, resolve_plan_for_activation
from lotoia.clients.deploy_info import build_deploy_info
from lotoia.clients.evolution_client import EvolutionApiClient
from lotoia.clients.whatsapp_service import (
    activate_client,
    deliver_whatsapp_webhook,
    get_client_status,
)
from lotoia.database.database import DEFAULT_DATABASE_PATH

router = APIRouter(tags=["whatsapp"])
logger = logging.getLogger(__name__)


class ActivateClientRequest(BaseModel):
    phone: str
    plan: str = Field(description="completo")
    valor_pago: float
    name: str = ""


@router.get("/whatsapp/status")
def whatsapp_status() -> dict[str, object]:
    client = EvolutionApiClient()
    return {
        "channel": "whatsapp",
        "deploy": build_deploy_info(),
        "evolution": {
            "configured": client.is_configured,
            "base_url": client.base_url or None,
            "instance": client.instance or None,
            "api_key_present": bool(client.api_key),
        },
    }


@router.post("/whatsapp/webhook")
def whatsapp_webhook(payload: dict[str, Any]) -> JSONResponse:
    try:
        result = deliver_whatsapp_webhook(payload, db_path=DEFAULT_DATABASE_PATH)
    except Exception as exc:  # noqa: BLE001 - Evolution API requires HTTP 200
        logger.exception("Unhandled WhatsApp webhook error: %s", exc)
        result = {
            "status": "error",
            "error_code": "WEBHOOK_PROCESSING_ERROR",
            "delivered": False,
        }
    return JSONResponse(status_code=200, content=result)


@router.get("/client/{phone}/status")
def client_status(phone: str) -> dict[str, Any]:
    status_payload = get_client_status(phone, db_path=DEFAULT_DATABASE_PATH)
    if not status_payload:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    return status_payload


@router.post("/client/activate")
def client_activate(body: ActivateClientRequest) -> dict[str, Any]:
    plan_key = str(body.plan or "").strip().lower()
    if not is_valid_activation_plan(plan_key):
        raise HTTPException(status_code=400, detail=f"Plano inválido: {body.plan}")
    resolved_plan = resolve_plan_for_activation(plan_key)
    try:
        return activate_client(
            phone=body.phone,
            plan=resolved_plan,
            valor_pago=float(body.valor_pago),
            name=body.name,
            db_path=DEFAULT_DATABASE_PATH,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Erro ao ativar cliente.") from exc
