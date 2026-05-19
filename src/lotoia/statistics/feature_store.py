from __future__ import annotations

from typing import Any


class FeatureStore:
    """Legacy structural feature calculations owned by the official statistics namespace."""

    def calculate_frequency(self, contests: list[dict[str, Any]]) -> dict[str, int]:
        frequencies: dict[str, int] = {}

        for contest in contests:
            dezenas = contest["dezenas"]

            for dezena in dezenas:
                if dezena not in frequencies:
                    frequencies[dezena] = 0

                frequencies[dezena] += 1

        return frequencies
