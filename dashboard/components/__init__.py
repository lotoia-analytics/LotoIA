"""Institutional dashboard components for LotoIA."""

from .analytical_cards import render_analytical_cards
from .executive_dashboard import render_executive_dashboard
from .executive_panel import render_executive_panel
from .executive_summary import render_executive_summary
from .generation_context import render_generation_context
from .hero_banner import render_hero_banner
from .live_status_header import render_live_status_header
from .institutional_timeline import render_institutional_timeline
from .secondary_metrics import render_secondary_operational_metrics
from .structural_health import render_structural_health

__all__ = [
    "render_analytical_cards",
    "render_executive_dashboard",
    "render_hero_banner",
    "render_executive_panel",
    "render_executive_summary",
    "render_generation_context",
    "render_live_status_header",
    "render_institutional_timeline",
    "render_secondary_operational_metrics",
    "render_structural_health",
]
