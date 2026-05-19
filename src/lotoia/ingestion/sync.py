from __future__ import annotations

from lotoia.database.contest_repository import ContestRepository
from lotoia.ingestion.providers.api_provider import LotteryDataProvider
from lotoia.statistics.feature_store import FeatureStore


def main() -> None:
    provider = LotteryDataProvider()
    repository = ContestRepository()
    feature_store = FeatureStore()

    repository.create_table()
    repository.create_feature_table()

    contests = repository.get_all_contests()
    frequencies = feature_store.calculate_frequency(contests)
    last_contest = repository.get_last_contest()

    repository.save_frequency_snapshot(last_contest, frequencies)

    print("Snapshot salvo com sucesso")


if __name__ == "__main__":
    main()
