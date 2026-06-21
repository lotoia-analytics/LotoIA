from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from lotoia.clients.constants import OFFICIAL_LANDING_URL
from lotoia.database.database import DEFAULT_DATABASE_PATH, MessengerConversationState, get_session

FREE_CHECK_LIMIT = 3


class FreemiumGuard:
    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path

    def _get_or_create(self, psid: str) -> MessengerConversationState:
        normalized = str(psid or "").strip()
        with get_session(self.db_path) as session:
            row = session.get(MessengerConversationState, normalized)
            if row is None:
                row = MessengerConversationState(psid=normalized)
                session.add(row)
                session.commit()
                session.refresh(row)
            return row

    def can_check(self, psid: str) -> tuple[bool, int]:
        row = self._get_or_create(psid)
        used = int(row.free_checks_used or 0)
        restantes = max(FREE_CHECK_LIMIT - used, 0)
        return restantes > 0, restantes

    def consume_check(self, psid: str) -> int:
        normalized = str(psid or "").strip()
        with get_session(self.db_path) as session:
            row = session.get(MessengerConversationState, normalized)
            if row is None:
                row = MessengerConversationState(psid=normalized, free_checks_used=1)
                session.add(row)
            else:
                row.free_checks_used = int(row.free_checks_used or 0) + 1
                row.last_interaction = datetime.now(UTC)
                row.updated_at = datetime.now(UTC)
            session.commit()
            session.refresh(row)
            return max(FREE_CHECK_LIMIT - int(row.free_checks_used or 0), 0)

    @staticmethod
    def get_limit_message(checks_restantes: int) -> str:
        if checks_restantes > 0:
            return f"💡 Você ainda tem {checks_restantes} conferência(s) gratuita(s)."
        return (
            "🔒 Você usou suas 3 conferências gratuitas.\n\n"
            "Para conferências ilimitadas + geração de jogos:\n\n"
            f"👉 {OFFICIAL_LANDING_URL}\n"
            "Plano Completo — R$99,90 🎯"
        )

    def is_active_client(self, psid: str, client: dict | None) -> bool:
        if not client:
            return False
        if str(client.get("status", "")).strip().lower() != "ativo":
            return False
        expiration = client.get("data_expiracao")
        if isinstance(expiration, datetime):
            expiration_utc = expiration if expiration.tzinfo else expiration.replace(tzinfo=UTC)
            return expiration_utc.date() >= datetime.now(UTC).date()
        return True
