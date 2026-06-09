from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable

from lotoia.data.loader import DEFAULT_HISTORY_PATH, DRAW_NUMBER_COLUMNS


def _normalize_draw_numbers(raw_numbers: Iterable[Any]) -> list[int]:
    return [int(str(number).lstrip("0") or "0") for number in raw_numbers]


def export_historical_csv(
    contests: list[dict[str, Any]],
    *,
    output_path: str | Path = DEFAULT_HISTORY_PATH,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered_contests = sorted(
        (
            {
                "concurso": int(contest["concurso"]),
                "data": str(contest["data"]),
                "dezenas": _normalize_draw_numbers(contest["dezenas"]),
            }
            for contest in contests
            if contest and str(contest.get("concurso", "")).isdigit()
        ),
        key=lambda contest: contest["concurso"],
    )
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["concurso", "data", *DRAW_NUMBER_COLUMNS])
        for contest in ordered_contests:
            dezenas = contest["dezenas"][:15]
            if len(dezenas) < 15:
                dezenas = dezenas + [0] * (15 - len(dezenas))
            writer.writerow(
                [
                    contest["concurso"],
                    contest["data"],
                    *dezenas[:15],
                ]
            )
    return path

