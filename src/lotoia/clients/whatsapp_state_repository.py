from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH, WhatsAppConversationState, get_session
from lotoia.clients.phone_utils import canonical_brazil_phone, phone_lookup_candidates
from lotoia.public.services import normalize_whatsapp


class WhatsAppStateRepository:
    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path

    def _normalize_phone(self, phone: str) -> str:
        stored = str(phone or "").strip()
        if stored.startswith("m:"):
            return stored
        try:
            return canonical_brazil_phone(stored)
        except ValueError:
            return normalize_whatsapp(stored)

    def get_state(self, phone: str) -> dict[str, Any]:
        normalized = self._normalize_phone(phone)
        with get_session(self.db_path) as session:
            row = session.get(WhatsAppConversationState, normalized)
            if row is None:
                return {"phone": normalized, "state": "initial"}
            return {
                "phone": row.phone,
                "state": row.state,
                "last_interaction": row.last_interaction,
                "updated_at": row.updated_at,
            }

    def set_state(self, phone: str, state: str) -> dict[str, Any]:
        normalized = self._normalize_phone(phone)
        now = datetime.now(UTC)
        with get_session(self.db_path) as session:
            row = session.get(WhatsAppConversationState, normalized)
            if row is None:
                row = WhatsAppConversationState(phone=normalized, state=state)
                session.add(row)
            else:
                row.state = str(state)
                row.last_interaction = now
                row.updated_at = now
            session.commit()
            session.refresh(row)
            return self.get_state(normalized)

    def reset_state(self, phone: str) -> dict[str, Any]:
        return self.set_state(phone, "initial")

    def is_awaiting_concurso(self, phone: str) -> bool:
        for candidate in phone_lookup_candidates(phone):
            if str(self.get_state(candidate).get("state") or "") == "awaiting_concurso":
                return True
        return False

    def set_awaiting_concurso(self, phone: str) -> dict[str, Any]:
        normalized = self._normalize_phone(phone)
        for candidate in phone_lookup_candidates(phone):
            if candidate != normalized:
                self.reset_state(candidate)
        return self.set_state(normalized, "awaiting_concurso")

    def clear_awaiting_concurso(self, phone: str) -> dict[str, Any]:
        for candidate in phone_lookup_candidates(phone):
            self.reset_state(candidate)
        return self.get_state(self._normalize_phone(phone))
