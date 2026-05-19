from __future__ import annotations

import json

try:
    from . import _bootstrap  # type: ignore[import-not-found]  # noqa: F401
except ImportError:
    import _bootstrap  # type: ignore[no-redef]  # noqa: F401

from lotoia.database import list_runs


def main() -> None:
    print(json.dumps(list_runs(), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
