from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests
from requests import Response
from requests.exceptions import RequestException


DEFAULT_CAIXA_LOTOFACIL_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"


@dataclass(frozen=True)
class CaixaContestResult:
    contest_number: int
    draw_date: str
    numbers: list[int]
    source_url: str
    raw_payload: dict[str, Any]

    def to_contest_record(self) -> dict[str, Any]:
        return {
            "concurso": self.contest_number,
            "data": self.draw_date,
            "dezenas": [f"{number:02d}" for number in self.numbers],
            "metadata_json": self.raw_payload,
            "source_url": self.source_url,
        }


class CaixaApiClient:
    """Official Caixa result client with conservative retry and normalization."""

    def __init__(
        self,
        base_url: str = DEFAULT_CAIXA_LOTOFACIL_URL,
        *,
        timeout_seconds: float = 8.0,
        max_retries: int = 3,
        retry_backoff_seconds: float = 0.75,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(1, max_retries)
        self.retry_backoff_seconds = max(0.0, retry_backoff_seconds)
        self.session = session or requests.Session()

    def fetch_latest(self) -> CaixaContestResult:
        payload = self._request_json(self.base_url)
        return self._normalize(payload, self.base_url)

    def fetch_contest(self, contest_number: int) -> CaixaContestResult:
        url = f"{self.base_url}/{contest_number}"
        payload = self._request_json(url)
        return self._normalize(payload, url)

    def fetch_contests(self, contest_numbers: list[int]) -> list[CaixaContestResult]:
        return [self.fetch_contest(contest_number) for contest_number in contest_numbers]

    def _request_json(self, url: str) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(
                    url,
                    timeout=self.timeout_seconds,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": "LotoIA/1.0 (+https://github.com/openai)",
                    },
                )
                self._raise_for_status(response)
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ValueError("Resposta da Caixa nao retornou um JSON objeto.")
                return payload
            except Exception as exc:  # noqa: BLE001 - controlled retry boundary
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff_seconds * attempt)
                    continue
                raise RuntimeError(f"Falha ao consultar a API oficial da Caixa em {url}: {exc}") from exc
        raise RuntimeError(f"Falha ao consultar a API oficial da Caixa em {url}: {last_error}") from last_error

    @staticmethod
    def _raise_for_status(response: Response) -> None:
        response.raise_for_status()

    @staticmethod
    def _normalize(payload: dict[str, Any], source_url: str) -> CaixaContestResult:
        contest_number = int(payload.get("numero") or payload.get("numeroConcurso") or payload.get("numero_concurso"))
        raw_date = str(payload.get("dataApuracao") or payload.get("dataSorteio") or payload.get("data") or "")
        numbers = payload.get("listaDezenas") or payload.get("dezenas") or []
        normalized_numbers = [int(str(number).lstrip("0") or "0") for number in numbers]
        if len(normalized_numbers) != 15:
            raise ValueError("Resposta oficial nao contem 15 dezenas.")
        return CaixaContestResult(
            contest_number=contest_number,
            draw_date=raw_date,
            numbers=sorted(normalized_numbers),
            source_url=source_url,
            raw_payload=payload,
        )
