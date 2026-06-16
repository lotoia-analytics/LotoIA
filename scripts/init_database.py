from __future__ import annotations

import os
import sys

try:
    from . import _bootstrap  # type: ignore[import-not-found]  # noqa: F401
except ImportError:
    import _bootstrap  # type: ignore[no-redef]  # noqa: F401

from lotoia.database import create_database

_INSTITUTIONAL_DATABASE_ENV_VARS = (
    "DATABASE_URL",
    "LOTOIA_DATABASE_URL",
    "STREAMLIT_DATABASE_URL",
    "LOTOIA_DATABASE_POOLER_URL",
    "STREAMLIT_DATABASE_POOLER_URL",
)


def _has_database_url() -> bool:
    return any(os.getenv(name, "").strip() for name in _INSTITUTIONAL_DATABASE_ENV_VARS)


def main() -> None:
    if not _has_database_url():
        print(
            "DATABASE_URL obrigatório. Fallback SQLite operacional desabilitado (Lei No 001).\n"
            "Use: python scripts/ops/apply_cloud_migrations.py",
            file=sys.stderr,
        )
        raise SystemExit(1)
    create_database()
    print("Schema inicializado via PostgreSQL (DATABASE_URL).")


if __name__ == "__main__":
    main()
