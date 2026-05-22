"""Enterprise observability foundation for LotoIA."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "DistributedTracer",
    "LogLevel",
    "MetricSample",
    "MetricSummary",
    "MetricType",
    "MetricsRegistry",
    "ObservabilityAlert",
    "ObservabilityAlertEngine",
    "ObservabilityAlertRule",
    "ObservabilityReport",
    "ObservabilityRepository",
    "InstitutionalObservabilityDashboard",
    "build_live_telemetry_snapshot",
    "build_live_operational_memory",
    "build_operational_health_snapshot",
    "build_operational_experience",
    "build_live_institutional_presence",
    "build_real_time_governance",
    "build_runtime_storytelling",
    "build_institutional_observability_dashboard",
    "OperationalMonitoring",
    "OperationalMonitoringSnapshot",
    "StructuredLogEvent",
    "StructuredLogger",
    "TraceSpan",
    "ObservabilityTracer",
    "build_observational_stabilization_report",
    "build_memory_timeline",
    "load_observational_stabilization_report",
    "persist_observational_stabilization_report",
]


_EXPORTS: dict[str, tuple[str, str]] = {
    "DistributedTracer": ("lotoia.observability.distributed_tracing", "DistributedTracer"),
    "LogLevel": ("lotoia.observability.structured_logging", "LogLevel"),
    "MetricSample": ("lotoia.observability.metrics_registry", "MetricSample"),
    "MetricSummary": ("lotoia.observability.metrics_registry", "MetricSummary"),
    "MetricType": ("lotoia.observability.metrics_registry", "MetricType"),
    "MetricsRegistry": ("lotoia.observability.metrics_registry", "MetricsRegistry"),
    "ObservabilityAlert": ("lotoia.observability.observability_alerts", "ObservabilityAlert"),
    "ObservabilityAlertEngine": ("lotoia.observability.observability_alerts", "ObservabilityAlertEngine"),
    "ObservabilityAlertRule": ("lotoia.observability.observability_alerts", "ObservabilityAlertRule"),
    "ObservabilityReport": ("lotoia.observability.observability_report", "ObservabilityReport"),
    "ObservabilityRepository": ("lotoia.observability.observability_repository", "ObservabilityRepository"),
    "InstitutionalObservabilityDashboard": ("lotoia.observability.institutional_dashboard", "InstitutionalObservabilityDashboard"),
    "build_live_telemetry_snapshot": ("lotoia.observability.live_telemetry", "build_live_telemetry_snapshot"),
    "build_live_operational_memory": ("lotoia.observability.live_operational_memory", "build_live_operational_memory"),
    "build_operational_health_snapshot": ("lotoia.observability.operational_health", "build_operational_health_snapshot"),
    "build_operational_experience": ("lotoia.observability.operational_experience", "build_operational_experience"),
    "build_live_institutional_presence": ("lotoia.observability.operational_experience", "build_live_institutional_presence"),
    "build_real_time_governance": ("lotoia.observability.real_time_governance", "build_real_time_governance"),
    "build_runtime_storytelling": ("lotoia.observability.runtime_storytelling", "build_runtime_storytelling"),
    "build_institutional_observability_dashboard": ("lotoia.observability.institutional_dashboard", "build_institutional_observability_dashboard"),
    "OperationalMonitoring": ("lotoia.observability.operational_monitoring", "OperationalMonitoring"),
    "OperationalMonitoringSnapshot": ("lotoia.observability.operational_monitoring", "OperationalMonitoringSnapshot"),
    "StructuredLogEvent": ("lotoia.observability.structured_logging", "StructuredLogEvent"),
    "StructuredLogger": ("lotoia.observability.structured_logging", "StructuredLogger"),
    "TraceSpan": ("lotoia.observability.distributed_tracing", "TraceSpan"),
    "ObservabilityTracer": ("lotoia.observability.observability_repository", "ObservabilityTracer"),
    "build_observational_stabilization_report": ("lotoia.observability.observational_stabilization", "build_observational_stabilization_report"),
    "build_memory_timeline": ("lotoia.memory.memory_timeline", "build_memory_timeline"),
    "load_observational_stabilization_report": ("lotoia.observability.observational_stabilization", "load_observational_stabilization_report"),
    "persist_observational_stabilization_report": ("lotoia.observability.observational_stabilization", "persist_observational_stabilization_report"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
