from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
OFFICIAL_PACKAGE_PATH = PROJECT_ROOT / "src" / "lotoia"
OFFICIAL_INIT = OFFICIAL_PACKAGE_PATH / "__init__.py"

if not OFFICIAL_INIT.is_file():
    raise ImportError(f"Official lotoia package not found at {OFFICIAL_INIT}")

__file__ = str(OFFICIAL_INIT)
__path__ = [str(OFFICIAL_PACKAGE_PATH)]
__package__ = "lotoia"

if __spec__ is not None:
    __spec__.origin = __file__
    __spec__.submodule_search_locations = __path__

exec(compile(OFFICIAL_INIT.read_text(encoding="utf-8"), __file__, "exec"))
