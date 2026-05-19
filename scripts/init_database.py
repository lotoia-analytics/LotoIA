from __future__ import annotations

try:
    from . import _bootstrap  # type: ignore[import-not-found]  # noqa: F401
except ImportError:
    import _bootstrap  # type: ignore[no-redef]  # noqa: F401

from lotoia.database import DEFAULT_DATABASE_PATH, create_database


def main() -> None:
    create_database()
    print(f"Banco inicializado em {DEFAULT_DATABASE_PATH}")


if __name__ == "__main__":
    main()
