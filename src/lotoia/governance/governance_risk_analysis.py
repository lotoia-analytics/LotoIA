"""Adaptive operational governance risk analysis."""

from __future__ import annotations

from dataclasses import dataclass

from .operational_policy_guard import PolicyGuardResult


@dataclass(frozen=True, slots=True)
class GovernanceRiskResult:
    """Risk score for adaptive operational changes."""

    risk_score: float
    risk_level: str
    policy_pressure: float
    anomaly_pressure: float
    health_pressure: float
    rationale: str


class GovernanceRiskAnalysis:
    """Score risk from policy violations, anomalies, and operational health."""

    def analyze(
        self,
        *,
        metrics: dict[str, float],
        policy_result: PolicyGuardResult,
    ) -> GovernanceRiskResult:
        policy_pressure = min(1.0, len(policy_result.violations) / 5.0)
        anomaly_pressure = min(1.0, metrics.get("critical_anomaly_count", 0.0) + metrics.get("anomaly_count", 0.0) / 5.0)
        health_pressure = 1.0 - max(0.0, min(1.0, metrics.get("health_score", 1.0)))
        risk = max(0.0, min(1.0, policy_pressure * 0.35 + anomaly_pressure * 0.35 + health_pressure * 0.30))
        level = "low" if risk < 0.35 else "medium" if risk < 0.70 else "high"
        return GovernanceRiskResult(
            risk_score=risk,
            risk_level=level,
            policy_pressure=policy_pressure,
            anomaly_pressure=anomaly_pressure,
            health_pressure=health_pressure,
            rationale="adaptive_change_blocked" if not policy_result.allowed else "adaptive_change_reviewable",
        )
