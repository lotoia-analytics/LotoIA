from __future__ import annotations

from typing import Any

import requests


class LotteryDataProvider:
    BASE_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"

    def fetch_latest(self) -> dict[str, Any]:
        response = requests.get(self.BASE_URL)

        data = response.json()

        contest = {
            "concurso": data["numero"],
            "data": data["dataApuracao"],
            "dezenas": data["listaDezenas"],
        }

        return contest

    def fetch_contest(self, contest_number: int) -> dict[str, Any]:
        response = requests.get(f"{self.BASE_URL}/{contest_number}")

        data = response.json()

        contest = {
            "concurso": data["numero"],
            "data": data["dataApuracao"],
            "dezenas": data["listaDezenas"],
        }

        return contest
