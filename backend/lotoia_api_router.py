"""Router FastAPI — API LotoIA (M-AUTO-CALIB-001)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from lotoia.api.lotoia_calibration_api import (
    API_VERSION,
    MISSION_ID,
    build_autonomous_calibration_plan,
    build_external_agent_payload,
    evaluate_structural_sovereignty,
    is_lotoia_auto_calib_api_enabled,
)
from lotoia.database.database import DEFAULT_DATABASE_PATH

router = APIRouter(prefix="/api/lotoia", tags=["lotoia-api"])


class LotoIAGamePayload(BaseModel):
    numbers: list[int] = Field(default_factory=list)
    final_card_numbers: list[int] | None = None
    card_format: int | None = None


class StructuralDiagnoseRequest(BaseModel):
    games: list[LotoIAGamePayload]
    batch_label: str | None = None
    db_path: str | None = None


class StructuralCalibrateRequest(StructuralDiagnoseRequest):
    auto_persist_plan: bool = False


@router.get("/v1/status")
def lotoia_api_status() -> dict[str, Any]:
    return {
        "mission_id": MISSION_ID,
        "api_version": API_VERSION,
        "auto_calibration_enabled": is_lotoia_auto_calib_api_enabled(),
        "role": "central_nervous_system",
        "integration_ready": ["telegram", "external_agents", "streamlit_audit"],
    }


@router.post("/v1/structural/diagnose")
def structural_diagnose(payload: StructuralDiagnoseRequest) -> dict[str, Any]:
    games = [game.model_dump() for game in payload.games]
    if not games:
        raise HTTPException(status_code=400, detail="games_required")
    db_path = payload.db_path or DEFAULT_DATABASE_PATH
    evaluation = evaluate_structural_sovereignty(
        games,
        db_path=db_path,
        batch_label=payload.batch_label,
    )
    external = build_external_agent_payload(evaluation)
    return {
        "evaluation": evaluation,
        "external_agent_payload": external,
    }


@router.post("/v1/structural/calibrate")
def structural_calibrate(payload: StructuralCalibrateRequest) -> dict[str, Any]:
    games = [game.model_dump() for game in payload.games]
    if not games:
        raise HTTPException(status_code=400, detail="games_required")
    db_path = payload.db_path or DEFAULT_DATABASE_PATH
    evaluation = evaluate_structural_sovereignty(
        games,
        db_path=db_path,
        batch_label=payload.batch_label,
    )
    if not evaluation.get("available"):
        raise HTTPException(status_code=422, detail=str(evaluation.get("reason") or "evaluation_failed"))

    plan = build_autonomous_calibration_plan(evaluation, games)
    persisted: dict[str, Any] = {}
    if payload.auto_persist_plan:
        from lotoia.api.lotoia_calibration_api import persist_api_governed_calibration_plan

        persisted = persist_api_governed_calibration_plan(plan, db_path=db_path)

    governance = {
        "mission_id": MISSION_ID,
        "sovereignty_passed": bool(evaluation.get("sovereignty_passed")),
        "requires_recalibration": bool(evaluation.get("requires_recalibration")),
        "auto_officialized": bool(evaluation.get("sovereignty_passed")),
        "calibration_plan": plan,
        "persisted_plan": persisted,
    }
    return {
        "evaluation": evaluation,
        "calibration_plan": plan,
        "governance": governance,
        "external_agent_payload": build_external_agent_payload(evaluation, governance=governance),
    }
