"""Local feature artifact persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class FeatureArtifactStore:
    """Persist feature materialization payloads as JSON artifacts."""

    def __init__(self, root: str | Path = "infra/storage/features") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, materialization_id: str, payload: dict[str, Any]) -> Path:
        path = self.root / f"{materialization_id}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
        return path

    def list(self) -> tuple[Path, ...]:
        return tuple(sorted(self.root.glob("*.json")))
