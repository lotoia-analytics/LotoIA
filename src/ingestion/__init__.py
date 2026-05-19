"""Legacy ingestion adapter.

New ingestion implementations must live under ``lotoia.ingestion``.
This namespace is retained only for compatibility redirects.
"""

from lotoia.ingestion import LotteryDataProvider, main

__all__ = ["LotteryDataProvider", "main"]
