from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH, MessengerConversationState, get_session


class MessengerStateRepository:
    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path

    def get_state(self, psid: str) -> dict[str, Any]:
        normalized = str(psid or "").strip()
        with get_session(self.db_path) as session:
            row = session.get(MessengerConversationState, normalized)
            if row is None:
                return {
                    "psid": normalized,
                    "state": "initial",
                    "free_checks_used": 0,
                }
            return {
                "psid": row.psid,
                "state": row.state,
                "free_checks_used": int(row.free_checks_used or 0),
                "last_interaction": row.last_interaction,
                "updated_at": row.updated_at,
            }

    def set_state(self, psid: str, state: str) -> dict[str, Any]:
        normalized = str(psid or "").strip()
        now = datetime.now(UTC)
        with get_session(self.db_path) as session:
            row = session.get(MessengerConversationState, normalized)
            if row is None:
                row = MessengerConversationState(psid=normalized, state=state)
                session.add(row)
            else:
                row.state = str(state)
                row.last_interaction = now
                row.updated_at = now
            session.commit()
            session.refresh(row)
            return self.get_state(normalized)

    def reset_state(self, psid: str) -> dict[str, Any]:
        return self.set_state(psid, "initial")

    def ensure_lead_state(self, psid: str) -> dict[str, Any]:
        normalized = str(psid or "").strip()
        with get_session(self.db_path) as session:
            row = session.get(MessengerConversationState, normalized)
            if row is None:
                row = MessengerConversationState(psid=normalized)
                session.add(row)
                session.commit()
            return self.get_state(normalized)
