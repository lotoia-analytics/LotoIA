from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from lotoia.database.database import DEFAULT_DATABASE_PATH


@dataclass(frozen=True)
class InstitutionalDatabaseAdapter:
    """Resolve the institutional database backend and connection target."""

    path: Path = DEFAULT_DATABASE_PATH

    @property
    def database_url(self) -> str:
        env_url = os.getenv("DATABASE_URL", "").strip()
        if env_url:
            return env_url
        resolved = self.path if self.path.is_absolute() else self.path.resolve()
        return f"sqlite:///{resolved.as_posix()}"

    @property
    def backend(self) -> str:
        url = self.database_url.lower()
        if url.startswith("sqlite:///"):
            return "sqlite"
        if url.startswith("postgresql") or url.startswith("postgres://"):
            return "postgresql"
        return "unknown"

    @property
    def sqlite_path(self) -> Path:
        return self.path if self.path.is_absolute() else self.path.resolve()

    @property
    def is_shared_cloud_ready(self) -> bool:
        return self.backend == "postgresql"

