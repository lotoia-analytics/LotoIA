"""Official ingestion namespace."""

from lotoia.ingestion.caixa_api_client import CaixaApiClient
from lotoia.ingestion.result_sync_service import ResultSyncService
from lotoia.ingestion.providers.api_provider import LotteryDataProvider
from lotoia.ingestion.sync import main

__all__ = ["CaixaApiClient", "LotteryDataProvider", "ResultSyncService", "main"]
