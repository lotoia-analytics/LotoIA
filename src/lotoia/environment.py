from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EnvironmentStatus:
    project_root: Path
    src_path: Path
    package_origin: Path
    is_official_namespace: bool


def get_environment_status() -> EnvironmentStatus:
    package_origin = Path(__file__).resolve()
    src_path = package_origin.parents[1]
    project_root = src_path.parent
    official_package = src_path / "lotoia"

    return EnvironmentStatus(
        project_root=project_root,
        src_path=src_path,
        package_origin=package_origin,
        is_official_namespace=official_package in package_origin.parents,
    )


def validate_official_environment() -> EnvironmentStatus:
    status = get_environment_status()
    if not status.is_official_namespace:
        raise RuntimeError(
            "Ambiente LotoIA invalido: o namespace lotoia nao foi resolvido em src/lotoia."
        )
    return status
