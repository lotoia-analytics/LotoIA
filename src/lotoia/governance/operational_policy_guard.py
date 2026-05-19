"""Operational policy guard for adaptive governance."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PolicySeverity(StrEnum):
    """Policy violation severity."""

    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


@dataclass(frozen=True, slots=True)
class PolicyViolation:
    """One operational governance policy violation."""

    code: str
    severity: PolicySeverity
    message: str
    metric_name: str
    observed_value: float
    threshold: float


@dataclass(frozen=True, slots=True)
class PolicyGuardResult:
    """Policy guard result for adaptive operations."""

    violations: tuple[PolicyViolation, ...]
    blocking_count: int
    allowed: bool


@dataclass(frozen=True, slots=True)
class OperationalPolicyConfig:
    """Policy thresholds for adaptive governance."""

    min_health_score: float = 0.45
    max_critical_anomalies: int = 0
    max_drift_signal: float = 0.20
    min_confidence_score: float = 0.35
    min_rerank_gain: float = -0.01


class OperationalPolicyGuard:
    """Detect policy violations before adaptive operational changes."""

    def __init__(self, config: OperationalPolicyConfig | None = None) -> None:
        self.config = config or OperationalPolicyConfig()

    def evaluate(self, metrics: dict[str, float]) -> PolicyGuardResult:
        violations: list[PolicyViolation] = []
        self._check_min(
            violations,
            code="health_score_below_policy",
            metric_name="health_score",
            value=metrics.get("health_score", 1.0),
            threshold=self.config.min_health_score,
            blocking=True,
        )
        self._check_max(
            violations,
            code="critical_anomaly_limit_exceeded",
            metric_name="critical_anomaly_count",
            value=metrics.get("critical_anomaly_count", 0.0),
            threshold=float(self.config.max_critical_anomalies),
            blocking=True,
        )
        self._check_max(
            violations,
            code="drift_escalation_required",
            metric_name="calibration_drift_signal",
            value=metrics.get("calibration_drift_signal", 0.0),
            threshold=self.config.max_drift_signal,
            blocking=False,
        )
        self._check_min(
            violations,
            code="confidence_collapse_escalation",
            metric_name="confidence_average",
            value=metrics.get("confidence_average", 1.0),
            threshold=self.config.min_confidence_score,
            blocking=True,
        )
        self._check_min(
            violations,
            code="rerank_instability_approval_required",
            metric_name="rerank_average_gain",
            value=metrics.get("rerank_average_gain", 0.0),
            threshold=self.config.min_rerank_gain,
            blocking=False,
        )
        blocking_count = sum(
            1 for violation in violations if violation.severity == PolicySeverity.BLOCKING
        )
        return PolicyGuardResult(
            violations=tuple(violations),
            blocking_count=blocking_count,
            allowed=blocking_count == 0,
        )

    def _check_min(
        self,
        violations: list[PolicyViolation],
        *,
        code: str,
        metric_name: str,
        value: float,
        threshold: float,
        blocking: bool,
    ) -> None:
        if value < threshold:
            violations.append(
                PolicyViolation(
                    code=code,
                    severity=PolicySeverity.BLOCKING if blocking else PolicySeverity.WARNING,
                    message=f"{metric_name} below policy threshold",
                    metric_name=metric_name,
                    observed_value=value,
                    threshold=threshold,
                )
            )

    def _check_max(
        self,
        violations: list[PolicyViolation],
        *,
        code: str,
        metric_name: str,
        value: float,
        threshold: float,
        blocking: bool,
    ) -> None:
        if value > threshold:
            violations.append(
                PolicyViolation(
                    code=code,
                    severity=PolicySeverity.BLOCKING if blocking else PolicySeverity.WARNING,
                    message=f"{metric_name} exceeds policy threshold",
                    metric_name=metric_name,
                    observed_value=value,
                    threshold=threshold,
                )
            )
