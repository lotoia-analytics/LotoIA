from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "AssistanceGovernanceSnapshot",
    "AdaptiveAssistanceMemorySnapshot",
    "ContextualRecommendationSnapshot",
    "ExplainableAnalyticsSnapshot",
    "ExecutiveAssistanceSnapshot",
    "ExecutiveSummarySnapshot",
    "FullExecutiveAssistancePresenceSnapshot",
    "HumanAnalyticalLanguageSnapshot",
    "InstitutionalSupportExperienceSnapshot",
    "OperationalGuidanceSnapshot",
    "build_assistance_governance",
    "build_adaptive_assistance_memory",
    "build_contextual_recommendations",
    "build_explainable_analytics",
    "build_executive_assistance",
    "build_executive_summary",
    "build_full_executive_assistance_presence",
    "build_institutional_support_experience",
    "build_human_analytical_language",
    "build_operational_guidance",
]


_EXPORTS: dict[str, tuple[str, str]] = {
    "AssistanceGovernanceSnapshot": ("lotoia.assistance.governance", "AssistanceGovernanceSnapshot"),
    "AdaptiveAssistanceMemorySnapshot": ("lotoia.assistance.adaptive_memory", "AdaptiveAssistanceMemorySnapshot"),
    "ContextualRecommendationSnapshot": ("lotoia.assistance.contextual_recommendation", "ContextualRecommendationSnapshot"),
    "ExplainableAnalyticsSnapshot": ("lotoia.assistance.explainable_analytics", "ExplainableAnalyticsSnapshot"),
    "ExecutiveAssistanceSnapshot": ("lotoia.assistance.executive_assistance", "ExecutiveAssistanceSnapshot"),
    "ExecutiveSummarySnapshot": ("lotoia.assistance.executive_summary", "ExecutiveSummarySnapshot"),
    "FullExecutiveAssistancePresenceSnapshot": ("lotoia.assistance.full_presence", "FullExecutiveAssistancePresenceSnapshot"),
    "HumanAnalyticalLanguageSnapshot": ("lotoia.assistance.human_language", "HumanAnalyticalLanguageSnapshot"),
    "InstitutionalSupportExperienceSnapshot": ("lotoia.assistance.institutional_support_experience", "InstitutionalSupportExperienceSnapshot"),
    "OperationalGuidanceSnapshot": ("lotoia.assistance.operational_guidance", "OperationalGuidanceSnapshot"),
    "build_assistance_governance": ("lotoia.assistance.governance", "build_assistance_governance"),
    "build_adaptive_assistance_memory": ("lotoia.assistance.adaptive_memory", "build_adaptive_assistance_memory"),
    "build_contextual_recommendations": ("lotoia.assistance.contextual_recommendation", "build_contextual_recommendations"),
    "build_explainable_analytics": ("lotoia.assistance.explainable_analytics", "build_explainable_analytics"),
    "build_executive_assistance": ("lotoia.assistance.executive_assistance", "build_executive_assistance"),
    "build_executive_summary": ("lotoia.assistance.executive_summary", "build_executive_summary"),
    "build_full_executive_assistance_presence": ("lotoia.assistance.full_presence", "build_full_executive_assistance_presence"),
    "build_institutional_support_experience": ("lotoia.assistance.institutional_support_experience", "build_institutional_support_experience"),
    "build_human_analytical_language": ("lotoia.assistance.human_language", "build_human_analytical_language"),
    "build_operational_guidance": ("lotoia.assistance.operational_guidance", "build_operational_guidance"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
