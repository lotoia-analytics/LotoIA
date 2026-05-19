"""Governance consensus engine."""

from __future__ import annotations


class GovernanceConsensusEngine:
    """Calculate council consensus from boolean votes."""

    def consensus(self, votes: tuple[bool, ...]) -> bool:
        if not votes:
            return False
        return sum(1 for vote in votes if vote) > len(votes) / 2
