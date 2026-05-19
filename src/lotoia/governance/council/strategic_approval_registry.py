"""Strategic approval registry."""

from __future__ import annotations


class StrategicApprovalRegistry:
    """Persist strategic approval records in memory."""

    def __init__(self) -> None:
        self._approvals: list[dict[str, str]] = []

    def register(self, approval: dict[str, str]) -> dict[str, str]:
        self._approvals.append(approval)
        return approval

    def list(self) -> tuple[dict[str, str], ...]:
        return tuple(self._approvals)
