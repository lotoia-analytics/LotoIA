"""Institutional dashboard components for LotoIA."""

from .analytical_cards import render_analytical_cards
from .executive_dashboard import render_executive_dashboard
from .executive_panel import render_executive_panel
from .executive_summary import render_executive_summary
from .design_system import render_institutional_design_system
from .generation_context import render_generation_context
from .adaptive_intelligence import render_adaptive_institutional_intelligence
from .hero_banner import render_hero_banner
from .live_analytical_intelligence import render_live_analytical_intelligence
from .live_status_header import render_live_status_header
from .institutional_timeline import render_institutional_timeline
from .operational_orchestration import render_operational_orchestration
from .secondary_metrics import render_secondary_operational_metrics
from .structural_health import render_structural_health

__all__ = [
    "render_analytical_cards",
    "render_executive_dashboard",
    "render_hero_banner",
    "render_executive_panel",
    "render_executive_summary",
    "render_institutional_design_system",
    "render_generation_context",
    "render_adaptive_institutional_intelligence",
    "render_live_analytical_intelligence",
    "render_live_status_header",
    "render_institutional_timeline",
    "render_operational_orchestration",
    "render_secondary_operational_metrics",
    "render_structural_health",
]
