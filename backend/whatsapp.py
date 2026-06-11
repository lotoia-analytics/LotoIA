from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from lotoia.clients.constants import PLANS
from lotoia.clients.whatsapp_service import (
    activate_client,
    get_client_status,
    process_whatsapp_webhook,
)
from lotoia.database.database import DEFAULT_DATABASE_PATH

router = APIRouter(tags=["whatsapp"])


class ActivateClientRequest(BaseModel):
    phone: str
    plan: str = Field(description="basico|plus|avancado|pro|master|elite")
    valor_pago: float
    name: str = ""


@router.post("/whatsapp/webhook")
def whatsapp_webhook(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return process_whatsapp_webhook(payload, db_path=DEFAULT_DATABASE_PATH)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Erro ao processar webhook do WhatsApp.") from exc


@router.get("/client/{phone}/status")
def client_status(phone: str) -> dict[str, Any]:
    status_payload = get_client_status(phone, db_path=DEFAULT_DATABASE_PATH)
    if not status_payload:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    return status_payload


@router.post("/client/activate")
def client_activate(body: ActivateClientRequest) -> dict[str, Any]:
    plan_key = str(body.plan or "").strip().lower()
    if plan_key not in PLANS:
        raise HTTPException(status_code=400, detail=f"Plano inválido: {body.plan}")
    try:
        return activate_client(
            phone=body.phone,
            plan=plan_key,
            valor_pago=float(body.valor_pago),
            name=body.name,
            db_path=DEFAULT_DATABASE_PATH,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Erro ao ativar cliente.") from exc
