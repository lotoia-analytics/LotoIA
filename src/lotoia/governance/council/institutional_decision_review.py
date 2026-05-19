"""Institutional decision review."""

from __future__ import annotations


class InstitutionalDecisionReview:
    """Audit decision review records."""

    def review(self, session: dict[str, str], *, reviewer: str) -> dict[str, str]:
        return {**session, "reviewer": reviewer, "review_status": "audited"}
