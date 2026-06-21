from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from lotoia.clients.constants import DAILY_LIMIT, OFFICIAL_LANDING_HOST, VALID_QUANTITIES
from lotoia.clients.interactive_menu import is_format_allowed_for_client
from lotoia.clients.plan_entitlements import effective_formato_maximo, effective_formats_label, normalize_plan_key
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
                f"Acesse {OFFICIAL_LANDING_HOST} para assinar."
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
                f"Acesse {OFFICIAL_LANDING_HOST} para renovar."
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
                    f"Acesse {OFFICIAL_LANDING_HOST} para renovar."
                ),
                client=client,
            )

    resolved_formato = int(formato or 15)
    formato_maximo = effective_formato_maximo(client)
    plan_name = normalize_plan_key(str(client.get("plan", "") or ""))
    plan_formats = effective_formats_label(client)
    if not is_format_allowed_for_client(resolved_formato, formato_maximo=formato_maximo):
        trial_hint = ""
        if plan_name == "completo" and formato_maximo <= 15 and int(formato or 15) > 15:
            trial_hint = "\nApós 7 dias você libera 15D + 20D."
        return ValidationResult(
            ok=False,
            error_code="FORMAT_NOT_ALLOWED",
            message=(
                f"Seu plano {plan_name} permite: {plan_formats}.\n"
                f"O formato {resolved_formato}D não está incluído.{trial_hint}"
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


def validate_messenger_request(
    psid: str,
    formato: int | None,
    quantidade: int,
    *,
    db_path: Path = DEFAULT_DATABASE_PATH,
) -> ValidationResult:
    repository = ClientRepository(db_path)
    client = repository.get_by_messenger_psid(psid)
    if not client:
        return ValidationResult(
            ok=False,
            error_code="CLIENT_NOT_FOUND",
            message=(
                "Conta Messenger não cadastrada.\n"
                f"Acesse {OFFICIAL_LANDING_HOST} para assinar."
            ),
        )
    return validate_request(
        str(client.get("phone") or repository.messenger_phone(psid)),
        formato,
        quantidade,
        db_path=db_path,
    )
