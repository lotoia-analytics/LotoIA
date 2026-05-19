"""Official ingestion namespace."""

from lotoia.ingestion.providers.api_provider import LotteryDataProvider
from lotoia.ingestion.sync import main

__all__ = ["LotteryDataProvider", "main"]
