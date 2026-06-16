"""Bootstrap PostgreSQL env for headless ops scripts (Lei No 001).

Loads `.env` from the repo root (and optional fallbacks) before resolving
DATABASE_URL / LOTOIA_DATABASE_URL / pooler aliases.
"""

from __future__ import annotations

import os
from pathlib import Path

DATABASE_ENV_VARS: tuple[str, ...] = (
    "LOTOIA_DATABASE_POOLER_URL",
    "STREAMLIT_DATABASE_POOLER_URL",
    "DATABASE_URL",
    "LOTOIA_DATABASE_URL",
    "STREAMLIT_DATABASE_URL",
)


def normalize_database_url(url: str) -> str:
    return str(url or "").strip().replace("postgresql+psycopg://", "postgresql://", 1)


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
    for env_name in DATABASE_ENV_VARS:
        value = os.getenv(env_name, "").strip()
        if value:
            return normalize_database_url(value), env_name
    return "", ""


def _is_placeholder_database_url(url: str) -> bool:
    lowered = url.lower()
    return (
        "user:pass@host:" in lowered
        or "@host:5432" in lowered
        or lowered.endswith("@localhost:5432/lotoia")
    )


def _is_railway_internal_url(url: str) -> bool:
    return ".railway.internal" in url.lower()


def ensure_database_url(*, root: Path) -> str:
    """Load dotenv files and require a PostgreSQL URL for ops scripts."""
    loaded_paths = load_repo_dotenv(root)
    url, source = resolve_database_url()
    if not url:
        hint_paths = ", ".join(
            str(p)
            for p in (root / ".env", root / ".env.local", Path.home() / ".lotoia" / ".env")
        )
        raise RuntimeError(
            "PostgreSQL não configurado (Lei No 001). "
            f"Defina DATABASE_URL ou LOTOIA_DATABASE_URL em um destes arquivos: {hint_paths}. "
            "Copie .env.example para .env e cole a URL do Railway (Settings → Variables)."
        )
    if _is_placeholder_database_url(url):
        raise RuntimeError(
            "DATABASE_URL ainda é o placeholder de .env.example. "
            f"Edite {root / '.env'} com a URL real do Railway "
            "(Dashboard → PostgreSQL → Connect → DATABASE_URL)."
        )
    if _is_railway_internal_url(url):
        raise RuntimeError(
            "DATABASE_URL usa host *.railway.internal — só funciona DENTRO do Railway. "
            "No seu PC, use a URL pública: Railway → PostgreSQL → Connect → "
            "Public Network / External (host tipo *.proxy.rlwy.net ou *.up.railway.app)."
        )

    os.environ.setdefault("DATABASE_URL", url)
    if source != "DATABASE_URL":
        os.environ.setdefault(source, url)
    if loaded_paths:
        os.environ.setdefault("LOTOIA_DOTENV_LOADED", loaded_paths[-1])
    return url
