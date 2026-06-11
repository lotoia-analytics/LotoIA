from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert

from lotoia.clients.constants import DAILY_LIMIT, PLANS
from lotoia.database.database import (
    DEFAULT_DATABASE_PATH,
    LotoiaClient,
    LotoiaClientDailyUsage,
    LotoiaClientGeneration,
    create_database,
    get_session,
)
from lotoia.clients.phone_utils import canonical_brazil_phone, phone_lookup_candidates
from lotoia.public.services import normalize_whatsapp


def _model_to_dict(model: Any) -> dict[str, Any]:
    return {column.name: getattr(model, column.name) for column in model.__table__.columns}


class ClientRepository:
    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path
        create_database(db_path)

    def get_by_phone(self, phone: str) -> dict[str, Any] | None:
        with get_session(self.db_path) as session:
            for candidate in phone_lookup_candidates(phone):
                row = session.query(LotoiaClient).filter(LotoiaClient.phone == candidate).one_or_none()
                if row is not None:
                    return _model_to_dict(row)
        return None

    def activate_client(
        self,
        *,
        phone: str,
        plan: str,
        valor_pago: float,
        name: str = "",
        duration_days: int = 30,
    ) -> dict[str, Any]:
        normalized_phone = canonical_brazil_phone(phone)
        plan_key = str(plan or "basico").strip().lower()
        if plan_key not in PLANS:
            raise ValueError(f"Plano inválido: {plan}")
        plan_config = PLANS[plan_key]
        now = datetime.now(UTC)
        expiration = now + timedelta(days=int(duration_days))
        values = {
            "phone": normalized_phone,
            "name": str(name or "").strip(),
            "plan": plan_key,
            "formato_maximo": int(plan_config["formato_max"]),
            "valor_pago": float(valor_pago),
            "data_inicio": now,
            "data_expiracao": expiration,
            "status": "ativo",
            "created_at": now,
        }
        with get_session(self.db_path) as session:
            backend = session.bind.dialect.name if session.bind is not None else "sqlite"
            if backend == "postgresql":
                stmt = pg_insert(LotoiaClient).values(**values)
                stmt = stmt.on_conflict_do_update(
                    index_elements=[LotoiaClient.phone],
                    set_={
                        "name": stmt.excluded.name,
                        "plan": stmt.excluded.plan,
                        "formato_maximo": stmt.excluded.formato_maximo,
                        "valor_pago": stmt.excluded.valor_pago,
                        "data_inicio": stmt.excluded.data_inicio,
                        "data_expiracao": stmt.excluded.data_expiracao,
                        "status": stmt.excluded.status,
                    },
                )
                session.execute(stmt)
            else:
                existing = session.query(LotoiaClient).filter(LotoiaClient.phone == normalized_phone).one_or_none()
                if existing is None:
                    session.add(LotoiaClient(**values))
                else:
                    existing.name = values["name"]
                    existing.plan = values["plan"]
                    existing.formato_maximo = values["formato_maximo"]
                    existing.valor_pago = values["valor_pago"]
                    existing.data_inicio = values["data_inicio"]
                    existing.data_expiracao = values["data_expiracao"]
                    existing.status = values["status"]
            session.commit()
            row = session.query(LotoiaClient).filter(LotoiaClient.phone == normalized_phone).one()
            return _model_to_dict(row)

    def get_daily_jogos_count(self, client_id: int, *, usage_date: date | None = None) -> int:
        target_date = usage_date or datetime.now(UTC).date()
        with get_session(self.db_path) as session:
            row = (
                session.query(LotoiaClientDailyUsage)
                .filter(
                    LotoiaClientDailyUsage.client_id == int(client_id),
                    LotoiaClientDailyUsage.usage_date == target_date,
                )
                .one_or_none()
            )
            return int(row.jogos_count if row else 0)

    def increment_daily_usage(self, client_id: int, *, quantidade: int) -> dict[str, Any]:
        target_date = datetime.now(UTC).date()
        with get_session(self.db_path) as session:
            row = (
                session.query(LotoiaClientDailyUsage)
                .filter(
                    LotoiaClientDailyUsage.client_id == int(client_id),
                    LotoiaClientDailyUsage.usage_date == target_date,
                )
                .one_or_none()
            )
            if row is None:
                row = LotoiaClientDailyUsage(
                    client_id=int(client_id),
                    usage_date=target_date,
                    geracoes_count=1,
                    jogos_count=int(quantidade),
                )
                session.add(row)
            else:
                row.geracoes_count = int(row.geracoes_count or 0) + 1
                row.jogos_count = int(row.jogos_count or 0) + int(quantidade)
            session.commit()
            session.refresh(row)
            return _model_to_dict(row)

    def log_client_generation(
        self,
        *,
        client_id: int,
        phone: str,
        formato: int,
        quantidade: int,
        jogos: list[dict[str, Any]],
        generation_event_id: int | None = None,
    ) -> dict[str, Any]:
        with get_session(self.db_path) as session:
            row = LotoiaClientGeneration(
                client_id=int(client_id),
                phone=normalize_whatsapp(phone),
                formato=int(formato),
                quantidade=int(quantidade),
                jogos=list(jogos),
                generation_event_id=generation_event_id,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return _model_to_dict(row)

    def get_client_status(self, phone: str) -> dict[str, Any] | None:
        client = self.get_by_phone(phone)
        if not client:
            return None
        jogos_hoje = self.get_daily_jogos_count(int(client["id"]))
        expiration = client.get("data_expiracao")
        dias_restantes = 0
        if isinstance(expiration, datetime):
            expiration_utc = expiration if expiration.tzinfo else expiration.replace(tzinfo=UTC)
            dias_restantes = max((expiration_utc.date() - datetime.now(UTC).date()).days, 0)
        return {
            "name": str(client.get("name", "") or ""),
            "plan": str(client.get("plan", "") or ""),
            "formato_maximo": int(client.get("formato_maximo", 15) or 15),
            "data_expiracao": expiration.isoformat() if isinstance(expiration, datetime) else str(expiration or ""),
            "dias_restantes": dias_restantes,
            "jogos_hoje": jogos_hoje,
            "saldo_hoje": max(DAILY_LIMIT - jogos_hoje, 0),
            "status": str(client.get("status", "") or ""),
        }
