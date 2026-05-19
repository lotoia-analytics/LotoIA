from __future__ import annotations

from typing import Any

import ingestion
import ingestion.providers
import ingestion.providers.api_provider as legacy_api_provider
import ingestion.sync as legacy_sync
import ingestion.validators as legacy_validators
import lotoia.ingestion as official_ingestion
import lotoia.ingestion.providers as official_providers
import lotoia.ingestion.providers.api_provider as official_api_provider
import lotoia.ingestion.sync as official_sync
import lotoia.ingestion.validators as official_validators


def test_legacy_ingestion_namespace_redirects_to_official_owner() -> None:
    assert ingestion.main is official_ingestion.main
    assert legacy_sync.main is official_sync.main
    assert ingestion.LotteryDataProvider is official_ingestion.LotteryDataProvider
    assert ingestion.providers.LotteryDataProvider is official_providers.LotteryDataProvider
    assert legacy_api_provider.LotteryDataProvider is official_api_provider.LotteryDataProvider


def test_legacy_validators_namespace_is_explicitly_neutralized() -> None:
    assert official_validators.__all__ == []
    assert legacy_validators.__all__ == official_validators.__all__


def test_lottery_data_provider_normalizes_latest_and_specific_contests(monkeypatch) -> None:
    calls: list[str] = []

    class Response:
        def __init__(self, contest_number: int) -> None:
            self.contest_number = contest_number

        def json(self) -> dict[str, Any]:
            return {
                "numero": self.contest_number,
                "dataApuracao": "18/05/2026",
                "listaDezenas": ["01", "02", "03"],
            }

    def fake_get(url: str) -> Response:
        calls.append(url)
        contest_number = 999 if url.endswith("/999") else 1000
        return Response(contest_number)

    monkeypatch.setattr(official_api_provider.requests, "get", fake_get)

    provider = official_api_provider.LotteryDataProvider()

    assert provider.fetch_latest() == {
        "concurso": 1000,
        "data": "18/05/2026",
        "dezenas": ["01", "02", "03"],
    }
    assert provider.fetch_contest(999) == {
        "concurso": 999,
        "data": "18/05/2026",
        "dezenas": ["01", "02", "03"],
    }
    assert calls == [
        official_api_provider.LotteryDataProvider.BASE_URL,
        f"{official_api_provider.LotteryDataProvider.BASE_URL}/999",
    ]


def test_ingestion_sync_main_uses_official_collaborators(monkeypatch, capsys) -> None:
    events: list[tuple[str, Any]] = []

    class FakeProvider:
        def __init__(self) -> None:
            events.append(("provider_init", None))

    class FakeRepository:
        def __init__(self) -> None:
            events.append(("repository_init", None))

        def create_table(self) -> None:
            events.append(("create_table", None))

        def create_feature_table(self) -> None:
            events.append(("create_feature_table", None))

        def get_all_contests(self) -> list[dict[str, Any]]:
            events.append(("get_all_contests", None))
            return [
                {"concurso": 1, "data": "01/01/2026", "dezenas": ["01", "02"]},
                {"concurso": 2, "data": "02/01/2026", "dezenas": ["02", "03"]},
            ]

        def get_last_contest(self) -> int:
            events.append(("get_last_contest", None))
            return 2

        def save_frequency_snapshot(self, concurso: int, frequencies: dict[str, int]) -> None:
            events.append(("save_frequency_snapshot", (concurso, frequencies)))

    monkeypatch.setattr(official_sync, "LotteryDataProvider", FakeProvider)
    monkeypatch.setattr(official_sync, "ContestRepository", FakeRepository)

    official_sync.main()

    assert events == [
        ("provider_init", None),
        ("repository_init", None),
        ("create_table", None),
        ("create_feature_table", None),
        ("get_all_contests", None),
        ("get_last_contest", None),
        ("save_frequency_snapshot", (2, {"01": 1, "02": 2, "03": 1})),
    ]
    assert "Snapshot salvo com sucesso" in capsys.readouterr().out
