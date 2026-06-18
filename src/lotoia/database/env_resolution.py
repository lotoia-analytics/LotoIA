"""Resolve institutional PostgreSQL URLs from environment (Lei No 001)."""

from __future__ import annotations

import os
from urllib.parse import urlparse

PRIMARY_DATABASE_ENV_VARS: tuple[str, ...] = (
    "LOTOIA_DATABASE_POOLER_URL",
    "STREAMLIT_DATABASE_POOLER_URL",
    "DATABASE_URL",
    "LOTOIA_DATABASE_URL",
    "STREAMLIT_DATABASE_URL",
)

COMPAT_DATABASE_PUBLIC_URL_ENV = "DATABASE_PUBLIC_URL"

_INVALID_DATABASE_URL_LITERALS: frozenset[str] = frozenset(
    {
        "DATABASE_URL",
        "LOTOIA_DATABASE_URL",
        "STREAMLIT_DATABASE_URL",
        "LOTOIA_DATABASE_POOLER_URL",
        "STREAMLIT_DATABASE_POOLER_URL",
        "DATABASE_PUBLIC_URL",
    }
)


def normalize_database_url(url: str) -> str:
    return str(url or "").strip().replace("postgresql+psycopg://", "postgresql://", 1)


def is_invalid_database_url_literal(value: str) -> bool:
    return value.strip() in _INVALID_DATABASE_URL_LITERALS


_PLACEHOLDER_MARKERS: tuple[str, ...] = (
    "sua_senha",
    "your_password",
    "changeme",
)


def is_placeholder_database_url(url: str) -> bool:
    lowered = normalize_database_url(url).lower()
    if not lowered:
        return True
    if is_invalid_database_url_literal(url):
        return True
    if any(marker in lowered for marker in _PLACEHOLDER_MARKERS):
        return True
    parsed = urlparse(lowered)
    host = (parsed.hostname or "").lower()
    username = (parsed.username or "").lower()
    password = (parsed.password or "").lower()
    if host == "host" and username == "user" and password == "pass":
        return True
    return False


def is_postgresql_database_url(url: str) -> bool:
    scheme = urlparse(normalize_database_url(url)).scheme.lower()
    return scheme.startswith("postgres")


def is_railway_internal_database_url(url: str) -> bool:
    host = (urlparse(normalize_database_url(url)).hostname or "").lower()
    return ".railway.internal" in host


def _read_env_value(env_name: str) -> str:
    return os.getenv(env_name, "").strip()


def resolve_institutional_database_url_from_env(
    *,
    allow_public_url_fallback: bool = True,
) -> tuple[str, str]:
    """Return (url, source_env). DATABASE_URL is sovereign when valid."""
    for env_name in PRIMARY_DATABASE_ENV_VARS:
        value = _read_env_value(env_name)
        if not value or is_placeholder_database_url(value):
            continue
        if not is_postgresql_database_url(value):
            continue
        return normalize_database_url(value), env_name

    if allow_public_url_fallback:
        public_url = _read_env_value(COMPAT_DATABASE_PUBLIC_URL_ENV)
        if public_url and not is_placeholder_database_url(public_url) and is_postgresql_database_url(public_url):
            return normalize_database_url(public_url), COMPAT_DATABASE_PUBLIC_URL_ENV

    return "", ""


def promote_resolved_database_url_to_env(*, allow_public_url_fallback: bool = True) -> tuple[str, str]:
    """Resolve URL and mirror into DATABASE_URL / LOTOIA_DATABASE_URL when needed."""
    url, source = resolve_institutional_database_url_from_env(
        allow_public_url_fallback=allow_public_url_fallback
    )
    if not url:
        return "", ""

    current_database_url = os.getenv("DATABASE_URL", "").strip()
    if source == COMPAT_DATABASE_PUBLIC_URL_ENV or is_invalid_database_url_literal(current_database_url):
        os.environ["DATABASE_URL"] = url
    else:
        os.environ.setdefault("DATABASE_URL", url)
    if source != "DATABASE_URL":
        os.environ.setdefault(source, url)
    if source == COMPAT_DATABASE_PUBLIC_URL_ENV:
        os.environ.setdefault("LOTOIA_DATABASE_URL", url)
    return url, source


def database_url_resolution_issue(url: str, *, source: str = "") -> str | None:
    if not url:
        return "DATABASE_URL ausente — PostgreSQL obrigatório (Lei No 001)"
    if is_invalid_database_url_literal(url):
        return (
            f"{source or 'DATABASE_URL'} contém valor literal inválido "
            f"('{url.strip()}') — use connection string PostgreSQL real "
            f"ou referência Railway ${{Postgres.DATABASE_URL}}"
        )
    if is_placeholder_database_url(url):
        return f"{source or 'DATABASE_URL'} ainda é placeholder — configure URL PostgreSQL real"
    if not is_postgresql_database_url(url):
        return f"{source or 'DATABASE_URL'} deve ser PostgreSQL (scheme atual inválido)"
    return None
