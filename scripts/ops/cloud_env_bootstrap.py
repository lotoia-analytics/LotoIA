"""Bootstrap PostgreSQL env for headless ops scripts (Lei No 001)."""

from __future__ import annotations

import os
from pathlib import Path

from lotoia.database.env_resolution import (
    COMPAT_DATABASE_PUBLIC_URL_ENV,
    is_invalid_database_url_literal,
    is_placeholder_database_url,
    is_railway_internal_database_url,
    normalize_database_url,
    promote_resolved_database_url_to_env,
    resolve_institutional_database_url_from_env,
)

DATABASE_ENV_VARS: tuple[str, ...] = (
    "LOTOIA_DATABASE_POOLER_URL",
    "STREAMLIT_DATABASE_POOLER_URL",
    "DATABASE_URL",
    "LOTOIA_DATABASE_URL",
    "STREAMLIT_DATABASE_URL",
    COMPAT_DATABASE_PUBLIC_URL_ENV,
)


def load_repo_dotenv(root: Path) -> list[str]:
    """Load dotenv files without overriding variables already in os.environ."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return []

    candidates = [
        root / ".env",
        root / ".env.local",
        Path.home() / ".lotoia" / ".env",
    ]
    loaded: list[str] = []
    for path in candidates:
        if path.is_file():
            load_dotenv(path, override=False)
            loaded.append(str(path))
    return loaded


def resolve_database_url() -> tuple[str, str]:
    return resolve_institutional_database_url_from_env()


def ensure_database_url(*, root: Path) -> str:
    """Load dotenv files and require a PostgreSQL URL for ops scripts."""
    loaded_paths = load_repo_dotenv(root)
    url, source = resolve_institutional_database_url_from_env()
    if not url:
        hint_paths = ", ".join(
            str(p)
            for p in (root / ".env", root / ".env.local", Path.home() / ".lotoia" / ".env")
        )
        raw_database_url = os.getenv("DATABASE_URL", "").strip()
        if is_invalid_database_url_literal(raw_database_url):
            raise RuntimeError(
                "DATABASE_URL está configurado como texto literal 'DATABASE_URL'. "
                "No Railway, use ${{Postgres.DATABASE_URL}}. "
                "No Cloud Agent, defina DATABASE_URL com a URL PostgreSQL real "
                f"ou {COMPAT_DATABASE_PUBLIC_URL_ENV} temporariamente."
            )
        raise RuntimeError(
            "PostgreSQL não configurado (Lei No 001). "
            f"Defina DATABASE_URL ou LOTOIA_DATABASE_URL. Arquivos opcionais: {hint_paths}."
        )
    if is_placeholder_database_url(url):
        raise RuntimeError(
            "DATABASE_URL ainda é placeholder. Configure URL PostgreSQL real "
            "(Railway → Postgres → Variables / referência ${{Postgres.DATABASE_URL}})."
        )
    if _is_external_runtime() and is_railway_internal_database_url(url):
        raise RuntimeError(
            "DATABASE_URL usa host *.railway.internal — inacessível fora do Railway. "
            f"Use URL pública em DATABASE_URL ou {COMPAT_DATABASE_PUBLIC_URL_ENV}."
        )

    promote_resolved_database_url_to_env()
    if loaded_paths:
        os.environ.setdefault("LOTOIA_DOTENV_LOADED", loaded_paths[-1])
    if source == COMPAT_DATABASE_PUBLIC_URL_ENV:
        os.environ.setdefault("LOTOIA_DATABASE_URL_COMPAT_SOURCE", source)
    return url


def _is_external_runtime() -> bool:
    markers = (
        "RAILWAY_ENVIRONMENT",
        "RAILWAY_PROJECT_ID",
        "RAILWAY_SERVICE_ID",
        "RAILWAY_PUBLIC_DOMAIN",
    )
    return not any(os.getenv(name, "").strip() for name in markers)
