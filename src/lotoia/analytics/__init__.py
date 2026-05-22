from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "AnalyticalInsight",
    "ComparativeAnalyticalInsight",
    "build_analytical_intelligence",
    "build_executive_analytical_report",
    "persist_executive_analytical_report",
    "interpret_longitudinal_report",
    "interpret_structural_health",
    "build_institutional_historical_intelligence",
    "build_institutional_analytical_timeline",
    "ensure_institutional_analytical_timeline",
    "load_institutional_analytics_snapshot",
    "load_institutional_analytical_timeline",
    "publish_institutional_analytics",
    "persist_institutional_analytical_timeline",
    "persist_institutional_analytics_snapshot",
    "persist_institutional_historical_intelligence",
    "ADAPTIVE_INSTITUTIONAL_SCHEMA_VERSION",
    "build_adaptive_executive_insights",
    "build_adaptive_institutional_intelligence",
    "build_adaptive_institutional_presence",
    "build_institutional_pattern_detection",
    "build_longitudinal_evolution_v2",
    "build_observational_learning_layer",
    "build_operational_memory",
    "build_strategic_analytical_timeline",
    "build_temporal_adaptive_analysis",
    "build_user_operational_intelligence",
    "load_adaptive_institutional_insights",
    "load_adaptive_institutional_intelligence",
    "load_adaptive_institutional_timeline",
    "persist_adaptive_institutional_insights",
    "persist_adaptive_institutional_intelligence",
    "persist_adaptive_institutional_timeline",
    "publish_adaptive_institutional_intelligence",
]

_EXPORTS: dict[str, tuple[str, str]] = {
    "AnalyticalInsight": ("lotoia.analytics.intelligence_layer", "AnalyticalInsight"),
    "ComparativeAnalyticalInsight": ("lotoia.analytics.intelligence_layer", "ComparativeAnalyticalInsight"),
    "build_analytical_intelligence": ("lotoia.analytics.intelligence_layer", "build_analytical_intelligence"),
    "build_executive_analytical_report": ("lotoia.analytics.intelligence_layer", "build_executive_analytical_report"),
    "persist_executive_analytical_report": ("lotoia.analytics.intelligence_layer", "persist_executive_analytical_report"),
    "interpret_longitudinal_report": ("lotoia.analytics.intelligence_layer", "interpret_longitudinal_report"),
    "interpret_structural_health": ("lotoia.analytics.intelligence_layer", "interpret_structural_health"),
    "build_institutional_historical_intelligence": ("lotoia.analytics.historical_intelligence", "build_institutional_historical_intelligence"),
    "build_institutional_analytical_timeline": ("lotoia.analytics.historical_intelligence", "build_institutional_analytical_timeline"),
    "ensure_institutional_analytical_timeline": ("lotoia.analytics.historical_intelligence", "ensure_institutional_analytical_timeline"),
    "load_institutional_analytics_snapshot": ("lotoia.analytics.historical_intelligence", "load_institutional_analytics_snapshot"),
    "load_institutional_analytical_timeline": ("lotoia.analytics.historical_intelligence", "load_institutional_analytical_timeline"),
    "publish_institutional_analytics": ("lotoia.analytics.historical_intelligence", "publish_institutional_analytics"),
    "persist_institutional_analytical_timeline": ("lotoia.analytics.historical_intelligence", "persist_institutional_analytical_timeline"),
    "persist_institutional_analytics_snapshot": ("lotoia.analytics.historical_intelligence", "persist_institutional_analytics_snapshot"),
    "persist_institutional_historical_intelligence": ("lotoia.analytics.historical_intelligence", "persist_institutional_historical_intelligence"),
    "ADAPTIVE_INSTITUTIONAL_SCHEMA_VERSION": ("lotoia.analytics.adaptive_intelligence", "ADAPTIVE_INSTITUTIONAL_SCHEMA_VERSION"),
    "build_adaptive_executive_insights": ("lotoia.analytics.adaptive_intelligence", "build_adaptive_executive_insights"),
    "build_adaptive_institutional_intelligence": ("lotoia.analytics.adaptive_intelligence", "build_adaptive_institutional_intelligence"),
    "build_adaptive_institutional_presence": ("lotoia.analytics.adaptive_intelligence", "build_adaptive_institutional_presence"),
    "build_institutional_pattern_detection": ("lotoia.analytics.adaptive_intelligence", "build_institutional_pattern_detection"),
    "build_longitudinal_evolution_v2": ("lotoia.analytics.adaptive_intelligence", "build_longitudinal_evolution_v2"),
    "build_observational_learning_layer": ("lotoia.analytics.adaptive_intelligence", "build_observational_learning_layer"),
    "build_operational_memory": ("lotoia.analytics.adaptive_intelligence", "build_operational_memory"),
    "build_strategic_analytical_timeline": ("lotoia.analytics.adaptive_intelligence", "build_strategic_analytical_timeline"),
    "build_temporal_adaptive_analysis": ("lotoia.analytics.adaptive_intelligence", "build_temporal_adaptive_analysis"),
    "build_user_operational_intelligence": ("lotoia.analytics.adaptive_intelligence", "build_user_operational_intelligence"),
    "load_adaptive_institutional_insights": ("lotoia.analytics.adaptive_intelligence", "load_adaptive_institutional_insights"),
    "load_adaptive_institutional_intelligence": ("lotoia.analytics.adaptive_intelligence", "load_adaptive_institutional_intelligence"),
    "load_adaptive_institutional_timeline": ("lotoia.analytics.adaptive_intelligence", "load_adaptive_institutional_timeline"),
    "persist_adaptive_institutional_insights": ("lotoia.analytics.adaptive_intelligence", "persist_adaptive_institutional_insights"),
    "persist_adaptive_institutional_intelligence": ("lotoia.analytics.adaptive_intelligence", "persist_adaptive_institutional_intelligence"),
    "persist_adaptive_institutional_timeline": ("lotoia.analytics.adaptive_intelligence", "persist_adaptive_institutional_timeline"),
    "publish_adaptive_institutional_intelligence": ("lotoia.analytics.adaptive_intelligence", "publish_adaptive_institutional_intelligence"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value

