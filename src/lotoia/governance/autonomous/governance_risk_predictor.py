"""Governance risk predictor."""

from __future__ import annotations


class GovernanceRiskPredictor:
    """Estimate governance risk from normalized signals."""

    def predict(self, signals: tuple[float, ...]) -> float:
        if not signals:
            return 0.0
        return min(1.0, max(0.0, sum(signals) / len(signals)))
