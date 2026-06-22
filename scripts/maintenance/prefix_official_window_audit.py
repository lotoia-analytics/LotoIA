"""Auditoria de prefixos contra janela oficial da Lotofácil.

Uso:
    python scripts/maintenance/prefix_official_window_audit.py --window 300

Saídas:
    prefix-official-window-audit.json
    prefix-official-window-audit.csv

Não imprime DATABASE_URL nem credenciais.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import create_engine, text

DEFAULT_PREFIXES = [
    "01-02-05",
    "03-06-07",
    "01-02-06",
    "03-04-06",
    "01-03-05",
    "03-04-05",
    "02-04-05",
    "01-03-07",
]

EXCESSIVE_PREFIXES = {"01-02-05", "03-06-07", "01-02-06", "03-04-06"}
RARE_OFFICIAL_PREFIXES = {"01-03-05", "03-04-05", "02-04-05", "01-03-07"}


@dataclass(frozen=True)
class OfficialContest:
    contest_number: int
    numbers: set[int]


def _parse_numbers(raw: Any) -> set[int]:
    if raw is None:
        return set()
    if isinstance(raw, list):
        return {int(value) for value in raw if str(value).strip().isdigit()}
    if isinstance(raw, tuple):
        return {int(value) for value in raw if str(value).strip().isdigit()}
    if isinstance(raw, str):
        cleaned = raw.replace("{", "").replace("}", "").replace("[", "").replace("]", "")
        parts = [part.strip() for part in cleaned.replace(";", ",").replace(" ", ",").split(",")]
        return {int(part) for part in parts if part.isdigit()}
    return set()


def _prefix_numbers(prefix: str) -> set[int]:
    return {int(part) for part in str(prefix).split("-") if part.strip().isdigit()}


def _load_last_contests(engine: Any, window: int) -> list[OfficialContest]:
    with engine.connect() as conn:
        table_names = [
            row[0]
            for row in conn.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name IN ('lotofacil_official_history', 'imported_contests')
                    """
                )
            ).all()
        ]
        if "lotofacil_official_history" in table_names:
            rows = conn.execute(
                text(
                    """
                    SELECT contest_number, numbers
                    FROM lotofacil_official_history
                    WHERE contest_number IS NOT NULL
                    ORDER BY contest_number DESC
                    LIMIT :window
                    """
                ),
                {"window": int(window)},
            ).all()
        elif "imported_contests" in table_names:
            rows = conn.execute(
                text(
                    """
                    SELECT contest_number, numbers
                    FROM imported_contests
                    WHERE contest_number IS NOT NULL
                    ORDER BY contest_number DESC
                    LIMIT :window
                    """
                ),
                {"window": int(window)},
            ).all()
        else:
            raise RuntimeError("Nenhuma tabela oficial encontrada: lotofacil_official_history/imported_contests")
    contests = [
        OfficialContest(contest_number=int(row[0]), numbers=_parse_numbers(row[1]))
        for row in rows
    ]
    return [contest for contest in contests if len(contest.numbers) >= 15]


def _classify(prefix: str, came_count: int, window: int) -> str:
    if came_count == 0:
        return "zero_presence_in_window"
    rate = came_count / max(1, window)
    if prefix in EXCESSIVE_PREFIXES and rate < 0.01:
        return "lotoia_excessive_rare_official"
    if prefix in RARE_OFFICIAL_PREFIXES:
        return "official_rare_boost_candidate"
    if rate < 0.01:
        return "very_rare"
    return "observed"


def _audit(contests: list[OfficialContest], prefixes: Iterable[str]) -> list[dict[str, Any]]:
    window = len(contests)
    results: list[dict[str, Any]] = []
    for prefix in prefixes:
        nums = _prefix_numbers(prefix)
        came_in = [contest.contest_number for contest in contests if nums.issubset(contest.numbers)]
        came_count = len(came_in)
        results.append(
            {
                "prefixo_3": prefix,
                "grupo_relatorio": (
                    "lotoia_excessivo" if prefix in EXCESSIVE_PREFIXES else "oficial_raro_na_lotoia"
                ),
                "janela_oficial": window,
                "veio_em": came_count,
                "nao_veio_em": max(0, window - came_count),
                "taxa_presenca": round(came_count / max(1, window), 6),
                "concursos_em_que_veio": came_in,
                "classificacao": _classify(prefix, came_count, window),
                "acao_sugerida": (
                    "bloquear_ou_penalizar_forte" if prefix in EXCESSIVE_PREFIXES and came_count == 0
                    else "penalizar" if prefix in EXCESSIVE_PREFIXES
                    else "boost_leve_observacional"
                ),
            }
        )
    return results


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "prefixo_3",
        "grupo_relatorio",
        "janela_oficial",
        "veio_em",
        "nao_veio_em",
        "taxa_presenca",
        "classificacao",
        "acao_sugerida",
        "concursos_em_que_veio",
    ]
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            csv_row = dict(row)
            csv_row["concursos_em_que_veio"] = "|".join(str(item) for item in row.get("concursos_em_que_veio", []))
            writer.writerow({key: csv_row.get(key, "") for key in fieldnames})


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window", type=int, default=300)
    parser.add_argument("--prefixes", default=",".join(DEFAULT_PREFIXES))
    parser.add_argument("--json-out", default="prefix-official-window-audit.json")
    parser.add_argument("--csv-out", default="prefix-official-window-audit.csv")
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL ausente")

    prefixes = [item.strip() for item in str(args.prefixes).split(",") if item.strip()]
    engine = create_engine(database_url)
    contests = _load_last_contests(engine, int(args.window))
    rows = _audit(contests, prefixes)
    payload = {
        "status": "ok",
        "requested_window": int(args.window),
        "actual_window": len(contests),
        "latest_contest": max((contest.contest_number for contest in contests), default=0),
        "oldest_contest": min((contest.contest_number for contest in contests), default=0),
        "prefixes": rows,
    }
    Path(args.json_out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_csv(Path(args.csv_out), rows)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
