from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
OFFICIAL_PACKAGE_PATH = SRC_PATH / "lotoia"


@dataclass(frozen=True)
class NamespaceStatus:
    project_root: Path
    src_path: Path
    package_origin: Path
    is_official: bool


def _normalize(path: str) -> str:
    return str(Path(path).resolve())


def ensure_src_layout() -> NamespaceStatus:
    """Resolve o src layout oficial antes de imports do namespace lotoia."""
    if not OFFICIAL_PACKAGE_PATH.is_dir():
        raise RuntimeError(f"Pacote oficial nao encontrado em {OFFICIAL_PACKAGE_PATH}")

    src_text = str(SRC_PATH)
    normalized_src = _normalize(src_text)
    sys.path[:] = [
        entry for entry in sys.path if not entry or _normalize(entry) != normalized_src
    ]
    sys.path.insert(0, src_text)

    loaded = sys.modules.get("lotoia")
    if loaded is not None:
        loaded_file = getattr(loaded, "__file__", None)
        if loaded_file is None or not _is_under_official_package(Path(loaded_file)):
            raise RuntimeError(
                "Namespace lotoia ja foi carregado fora de src/lotoia. "
                f"Modulo carregado: {loaded_file!r}"
            )

    return assert_official_namespace()


def assert_official_namespace() -> NamespaceStatus:
    spec = importlib.util.find_spec("lotoia")
    if spec is None or spec.origin is None:
        raise RuntimeError("Namespace lotoia nao pode ser resolvido.")

    origin = Path(spec.origin).resolve()
    is_official = _is_under_official_package(origin)
    if not is_official:
        raise RuntimeError(
            "Namespace lotoia resolvido fora do pacote oficial. "
            f"Esperado: {OFFICIAL_PACKAGE_PATH}; obtido: {origin}"
        )

    return NamespaceStatus(
        project_root=PROJECT_ROOT,
        src_path=SRC_PATH.resolve(),
        package_origin=origin,
        is_official=True,
    )


def _is_under_official_package(path: Path) -> bool:
    official = OFFICIAL_PACKAGE_PATH.resolve()
    resolved = path.resolve()
    return resolved == official or official in resolved.parents
