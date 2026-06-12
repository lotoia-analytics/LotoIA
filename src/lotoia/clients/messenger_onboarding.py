from __future__ import annotations

from pathlib import Path
from typing import Any

from lotoia.clients.constants import OFFICIAL_LANDING_URL
from lotoia.database.database import DEFAULT_DATABASE_PATH, GenerationEvent, Lead, get_session
from lotoia.public.persistence import LeadRepository

WELCOME_MESSAGE = (
    "👋 Bem-vindo à LotoIA! Análise estatística da Lotofácil.\n"
    "Para começar, escolha seu plano:\n"
    f"👉 {OFFICIAL_LANDING_URL}\n"
    "Após o pagamento via PIX, você já pode gerar seus jogos aqui!"
)


def _find_messenger_lead(psid: str, *, db_path: Path) -> dict[str, Any] | None:
    with get_session(db_path) as session:
        row = (
            session.query(Lead)
            .filter(Lead.messenger_psid == psid)
            .order_by(Lead.created_at.desc())
            .first()
        )
        if row is not None:
            return {column.name: getattr(row, column.name) for column in Lead.__table__.columns}
        row = (
            session.query(Lead)
            .filter(Lead.source == "messenger", Lead.whatsapp == psid)
            .order_by(Lead.created_at.desc())
            .first()
        )
        if row is not None:
            return {column.name: getattr(row, column.name) for column in Lead.__table__.columns}
        return None


def _log_messenger_capture_event(
    *,
    lead_id: int,
    psid: str,
    db_path: Path,
) -> dict[str, Any]:
    with get_session(db_path) as session:
        event = GenerationEvent(
            lead_id=int(lead_id),
            first_name="Messenger",
            whatsapp=str(psid),
            generated_games=[],
            context_json={
                "event_type": "MESSENGER_LEAD_CAPTURED",
                "source": "messenger",
                "messenger_psid": str(psid),
            },
            ml_enabled=0,
            seed=0,
            strategy="messenger_lead_captured",
            ranking_score=0.0,
            execution_time_ms=0.0,
            channel="messenger",
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        return {column.name: getattr(event, column.name) for column in GenerationEvent.__table__.columns}


def handle_new_messenger_lead(
    psid: str,
    *,
    db_path: Path = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    """
    Captação de novo lead via Messenger.
    messenger_psid nunca substitui phone — canais independentes.
    """
    normalized_psid = str(psid or "").strip()
    if not normalized_psid:
        return {
            "status": "error",
            "error_code": "INVALID_PSID",
            "message": "PSID inválido.",
        }

    existing = _find_messenger_lead(normalized_psid, db_path=db_path)
    if existing is not None:
        return {
            "status": "ok",
            "duplicate": True,
            "psid": normalized_psid,
            "lead_id": int(existing["id"]),
            "message": WELCOME_MESSAGE,
        }

    lead_repo = LeadRepository(db_path)
    lead = lead_repo.insert(
        first_name="Messenger",
        whatsapp=normalized_psid,
        source="messenger",
        ip_hash="",
        user_agent="messenger_bot",
        messenger_psid=normalized_psid,
    )
    lead_id = int(lead["id"])

    capture_event = _log_messenger_capture_event(
        lead_id=lead_id,
        psid=normalized_psid,
        db_path=db_path,
    )

    return {
        "status": "ok",
        "duplicate": False,
        "psid": normalized_psid,
        "lead_id": lead_id,
        "generation_event_id": capture_event.get("id"),
        "message": WELCOME_MESSAGE,
    }
