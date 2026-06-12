from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from lotoia.clients.constants import DAILY_LIMIT, PLANS, VALID_QUANTITIES
from lotoia.clients.interactive_menu import is_format_allowed_for_client
from lotoia.clients.repository import ClientRepository
from lotoia.database.database import DEFAULT_DATABASE_PATH


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    error_code: str | None = None
    message: str | None = None
    client: dict[str, Any] | None = None
    restante: int | None = None
    formato: int | None = None
    quantidade: int | None = None


def _format_expiration(value: datetime | date | str | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, datetime):
        return value.astimezone(UTC).strftime("%d/%m/%Y")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    return str(value)[:10]


def validate_request(
    phone: str,
    formato: int | None,
    quantidade: int,
    *,
    db_path: Path = DEFAULT_DATABASE_PATH,
) -> ValidationResult:
    repository = ClientRepository(db_path)
    client = repository.get_by_phone(phone)
    if not client:
        return ValidationResult(
            ok=False,
            error_code="CLIENT_NOT_FOUND",
            message=(
                "Número não cadastrado.\n"
                "Acesse lotoia.chat para assinar."
            ),
        )

    status = str(client.get("status", "") or "").strip().lower()
    if status != "ativo":
        if status == "bloqueado":
            return ValidationResult(
                ok=False,
                error_code="CLIENT_BLOCKED",
                message="Seu acesso está bloqueado. Entre em contato com o suporte.",
                client=client,
            )
        return ValidationResult(
            ok=False,
            error_code="PLAN_EXPIRED",
            message=(
                f"Seu plano expirou em {_format_expiration(client.get('data_expiracao'))}.\n"
                "Acesse lotoia.chat para renovar."
            ),
            client=client,
        )

    expiration = client.get("data_expiracao")
    if isinstance(expiration, datetime):
        expiration_utc = expiration if expiration.tzinfo else expiration.replace(tzinfo=UTC)
        if expiration_utc <= datetime.now(UTC):
            return ValidationResult(
                ok=False,
                error_code="PLAN_EXPIRED",
                message=(
                    f"Seu plano expirou em {_format_expiration(expiration)}.\n"
                    "Acesse lotoia.chat para renovar."
                ),
                client=client,
            )

    resolved_formato = int(formato or 15)
    formato_maximo = int(client.get("formato_maximo", 15) or 15)
    plan_name = str(client.get("plan", "basico") or "basico")
    plan_formats = str(PLANS.get(plan_name, {}).get("formats") or f"{formato_maximo}D")
    if not is_format_allowed_for_client(resolved_formato, formato_maximo=formato_maximo):
        return ValidationResult(
            ok=False,
            error_code="FORMAT_NOT_ALLOWED",
            message=(
                f"Seu plano {plan_name} permite: {plan_formats}.\n"
                f"O formato {resolved_formato}D não está incluído."
            ),
            client=client,
            formato=resolved_formato,
            quantidade=quantidade,
        )

    if quantidade not in VALID_QUANTITIES:
        return ValidationResult(
            ok=False,
            error_code="INVALID_QUANTITY",
            message=(
                "Quantidade inválida.\n"
                "Escolha: 1 a 9, 10, 20 ou 30 jogos."
            ),
            client=client,
            formato=resolved_formato,
            quantidade=quantidade,
        )

    jogos_hoje = repository.get_daily_jogos_count(int(client["id"]))
    restante = max(DAILY_LIMIT - jogos_hoje, 0)
    if restante <= 0:
        return ValidationResult(
            ok=False,
            error_code="DAILY_LIMIT_REACHED",
            message=(
                "Limite diário atingido (30 jogos).\n"
                f"Você tem {restante} jogos disponíveis hoje.\n"
                "Renova amanhã às 00h."
            ),
            client=client,
            restante=restante,
            formato=resolved_formato,
            quantidade=quantidade,
        )

    if quantidade > restante:
        return ValidationResult(
            ok=False,
            error_code="DAILY_LIMIT_PARTIAL",
            message=(
                f"Você tem {restante} jogos disponíveis hoje.\n"
                f"Peça até {restante} jogos."
            ),
            client=client,
            restante=restante,
            formato=resolved_formato,
            quantidade=quantidade,
        )

    return ValidationResult(
        ok=True,
        client=client,
        restante=restante,
        formato=resolved_formato,
        quantidade=quantidade,
    )
