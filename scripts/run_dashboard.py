from __future__ import annotations

try:
    from ._bootstrap import PROJECT_ROOT  # type: ignore[import-not-found]
except ImportError:
    from _bootstrap import PROJECT_ROOT  # type: ignore[no-redef]

import dashboard.app  # noqa: E402,F401
from streamlit.web import bootstrap  # noqa: E402


def main() -> None:
    dashboard_path = PROJECT_ROOT / "dashboard/app.py"
    bootstrap.run(
        str(dashboard_path),
        False,
        [],
        {
            "server.port": 8501,
            "server.headless": True,
            "browser.gatherUsageStats": False,
        },
    )


if __name__ == "__main__":
    main()
