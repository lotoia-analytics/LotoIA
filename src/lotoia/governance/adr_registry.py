"""ADR registry for institutional architectural governance."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AdrRecord:
    """One Architecture Decision Record entry."""

    adr_id: str
    title: str
    status: str
    path: str
    references_feature_generation_protocol: bool


class AdrRegistry:
    """Scan and expose institutional ADRs."""

    def __init__(self, adr_root: str | Path = "docs/adr") -> None:
        self.adr_root = Path(adr_root)

    def list_records(self) -> tuple[AdrRecord, ...]:
        if not self.adr_root.exists():
            return ()
        return tuple(
            self._read_record(path)
            for path in sorted(self.adr_root.glob("*.md"))
        )

    def get(self, adr_id: str) -> AdrRecord | None:
        for record in self.list_records():
            if record.adr_id == adr_id:
                return record
        return None

    def _read_record(self, path: Path) -> AdrRecord:
        text = path.read_text(encoding="utf-8")
        title = _first_heading(text) or path.stem
        status = _status(text)
        return AdrRecord(
            adr_id=path.stem,
            title=title,
            status=status,
            path=str(path),
            references_feature_generation_protocol="FeatureGenerationProtocol" in text,
        )


def _first_heading(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            return line.removeprefix("# ").strip()
    return None


def _status(text: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip().lower() == "## status":
            for next_line in lines[index + 1 :]:
                stripped = next_line.strip().strip(".")
                if stripped:
                    return stripped
    return "unknown"
