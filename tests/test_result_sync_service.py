from __future__ import annotations

from pathlib import Path

from lotoia.database.contest_repository import ContestRepository
from lotoia.ingestion.caixa_api_client import CaixaApiClient, CaixaContestResult
from lotoia.ingestion.result_sync_service import ResultSyncService


def test_caixa_api_client_normalizes_payload_and_retries(monkeypatch) -> None:
    calls: list[str] = []

    class FakeResponse:
        def __init__(self, payload: dict[str, object]) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return self._payload

    class FakeSession:
        def __init__(self) -> None:
            self.attempt = 0

        def get(self, url: str, timeout: float, headers: dict[str, str]) -> FakeResponse:  # noqa: ARG002
            calls.append(url)
            self.attempt += 1
            if self.attempt == 1:
                raise OSError("temporary network failure")
            return FakeResponse(
                {
                    "numero": 3690,
                    "dataApuracao": "20/05/2026",
                    "listaDezenas": ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12", "13", "14", "15"],
                }
            )

    monkeypatch.setattr("lotoia.ingestion.caixa_api_client.time.sleep", lambda *_: None)
    client = CaixaApiClient(session=FakeSession(), max_retries=2, retry_backoff_seconds=0.0)

    result = client.fetch_latest()

    assert isinstance(result, CaixaContestResult)
    assert result.contest_number == 3690
    assert result.draw_date == "20/05/2026"
    assert result.numbers == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    assert calls == [client.base_url, client.base_url]


def test_result_sync_service_persists_official_result_metadata(tmp_path: Path) -> None:
    db_path = tmp_path / "lotoia.db"
    repository = ContestRepository(db_path)

    class FakeClient:
        base_url = "https://example.test/api/lotofacil"

        def fetch_latest(self) -> CaixaContestResult:
            return CaixaContestResult(
                contest_number=3690,
                draw_date="20/05/2026",
                numbers=list(range(1, 16)),
                source_url=self.base_url,
                raw_payload={"numero": 3690, "dataApuracao": "20/05/2026", "listaDezenas": [f"{n:02d}" for n in range(1, 16)]},
            )

        def fetch_contest(self, contest_number: int) -> CaixaContestResult:
            raise AssertionError(f"Unexpected fetch_contest for {contest_number}")

    service = ResultSyncService(client=FakeClient(), repository=repository)

    summary = service.sync_latest()
    latest_record = repository.get_latest_contest_record()

    assert summary.latest_contest == 3690
    assert summary.synced_contests == [3690]
    assert summary.persisted_contests == 1
    assert latest_record is not None
    assert latest_record["concurso"] == 3690
    assert latest_record["dezenas"] == [f"{n:02d}" for n in range(1, 16)]
    assert '"numero": 3690' in latest_record["metadata_json"]


def test_result_sync_service_syncs_small_missing_gap(tmp_path: Path) -> None:
    db_path = tmp_path / "lotoia.db"
    repository = ContestRepository(db_path)
    repository.create_table()
    repository.save_contest(
        {
            "concurso": 3689,
            "data": "18/05/2026",
            "dezenas": [f"{n:02d}" for n in range(1, 16)],
            "metadata_json": {"numero": 3689, "dataApuracao": "18/05/2026"},
        }
    )

    class FakeClient:
        base_url = "https://example.test/api/lotofacil"

        def fetch_latest(self) -> CaixaContestResult:
            return CaixaContestResult(
                contest_number=3690,
                draw_date="20/05/2026",
                numbers=list(range(1, 16)),
                source_url=self.base_url,
                raw_payload={"numero": 3690, "dataApuracao": "20/05/2026", "listaDezenas": [f"{n:02d}" for n in range(1, 16)]},
            )

        def fetch_contest(self, contest_number: int) -> CaixaContestResult:
            return CaixaContestResult(
                contest_number=contest_number,
                draw_date="19/05/2026" if contest_number == 3689 else "20/05/2026",
                numbers=list(range(1, 16)),
                source_url=self.base_url,
                raw_payload={"numero": contest_number, "dataApuracao": "19/05/2026", "listaDezenas": [f"{n:02d}" for n in range(1, 16)]},
            )

    service = ResultSyncService(client=FakeClient(), repository=repository)
    summary = service.sync_latest()

    assert summary.synced_contests == [3690]
    assert repository.get_contest(3690) is not None
