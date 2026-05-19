"""Governance autonomy monitor."""

from __future__ import annotations


class GovernanceAutonomyMonitor:
    """Track autonomous governance actions."""

    def __init__(self) -> None:
        self._actions: list[dict[str, str]] = []

    def record(self, action: dict[str, str]) -> dict[str, str]:
        self._actions.append(action)
        return action

    def list(self) -> tuple[dict[str, str], ...]:
        return tuple(self._actions)
