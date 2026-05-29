from __future__ import annotations

from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.database.contest_repository import ContestRepository
from lotoia.data.history_export import export_historical_csv
from lotoia.ingestion.caixa_api_client import CaixaApiClient
from lotoia.ingestion.result_sync_service import ResultSyncService
from lotoia.statistics.feature_store import FeatureStore


def main() -> None:
    repository = ContestRepository(DEFAULT_DATABASE_PATH)
    client = CaixaApiClient()
    sync_service = ResultSyncService(client=client, repository=repository)
    feature_store = FeatureStore()

    repository.create_table()
    repository.create_feature_table()

    sync_summary = sync_service.sync_latest()
    contests = repository.get_all_contests()
    frequencies = feature_store.calculate_frequency(contests)
    last_contest = repository.get_last_contest()
    export_historical_csv(contests)

    repository.save_frequency_snapshot(last_contest, frequencies)

    if bool(getattr(sync_summary, "fallback_used", False)):
        print("Sincronizacao oficial indisponivel; mantendo ultimo estado conhecido.")
    else:
        print(f"Concursos sincronizados: {', '.join(str(contest) for contest in sync_summary.synced_contests)}")
    print("Snapshot salvo com sucesso")


if __name__ == "__main__":
    main()
