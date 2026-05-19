"""Autonomous governance decision engine."""

from __future__ import annotations


class AutonomousDecisionEngine:
    """Produce supervised governance decisions from risk signals."""

    def decide(self, *, risk_score: float) -> str:
        if risk_score >= 0.8:
            return "escalate"
        if risk_score >= 0.4:
            return "review"
        return "approve"
