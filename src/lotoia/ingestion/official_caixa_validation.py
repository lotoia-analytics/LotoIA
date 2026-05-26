from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from lotoia.database.contest_repository import ContestRepository
from lotoia.ingestion.caixa_api_client import CaixaApiClient, CaixaContestResult


DEFAULT_OFFICIAL_CAIXA_VALIDATION_DIR = Path("reports") / "institutional_caixa_validation"
DEFAULT_OFFICIAL_CAIXA_VALIDATION_LIMIT = 100


@dataclass(frozen=True)
class CaixaContestValidation:
    contest_number: int
    source_date: str
    source_numbers: list[int]
    persisted_date: str
    persisted_numbers: list[int]
    source_checksum: str
    persisted_checksum: str
    matches: bool
    mismatch_fields: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "contest_number": self.contest_number,
            "source_date": self.source_date,
            "source_numbers": self.source_numbers,
            "persisted_date": self.persisted_date,
            "persisted_numbers": self.persisted_numbers,
            "source_checksum": self.source_checksum,
            "persisted_checksum": self.persisted_checksum,
            "matches": self.matches,
            "mismatch_fields": self.mismatch_fields,
        }


@dataclass(frozen=True)
class CaixaInstitutionalValidationResult:
    created_at: str
    source_provider: str
    db_backend: str
    engine_url: str
    latest_contest: int
    contests_evaluated: int
    contest_numbers: list[int]
    source_count: int
    persisted_count: int
    duplicated_contests: list[int]
    gap_contests: list[int]
    checksum_mismatches: list[int]
    contest_validations: list[CaixaContestValidation]
    dataset_checksum: str
    integrity_status: str
    report_paths: dict[str, str]
    persisted_payload: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at,
            "source_provider": self.source_provider,
            "db_backend": self.db_backend,
            "engine_url": self.engine_url,
            "latest_contest": self.latest_contest,
            "contests_evaluated": self.contests_evaluated,
            "contest_numbers": self.contest_numbers,
            "source_count": self.source_count,
            "persisted_count": self.persisted_count,
            "duplicated_contests": self.duplicated_contests,
            "gap_contests": self.gap_contests,
            "checksum_mismatches": self.checksum_mismatches,
            "contest_validations": [validation.as_dict() for validation in self.contest_validations],
            "dataset_checksum": self.dataset_checksum,
            "integrity_status": self.integrity_status,
            "report_paths": self.report_paths,
            "persisted_payload": self.persisted_payload,
        }


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _contest_checksum(contest_number: int, draw_date: str, numbers: list[int]) -> str:
    payload = {
        "contest_number": int(contest_number),
        "draw_date": str(draw_date),
        "numbers": [int(number) for number in numbers],
        "quantity": len(numbers),
    }
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()


def _dataset_checksum(rows: list[CaixaContestValidation]) -> str:
    accumulator = sha256()
    for row in rows:
        accumulator.update(f"{row.contest_number}:{row.source_checksum}:{row.persisted_checksum}\n".encode("utf-8"))
    return accumulator.hexdigest()


def _persist_rows_csv(path: Path, rows: list[CaixaContestValidation]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "contest_number",
        "source_date",
        "persisted_date",
        "source_numbers",
        "persisted_numbers",
        "source_checksum",
        "persisted_checksum",
        "matches",
        "mismatch_fields",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "contest_number": row.contest_number,
                    "source_date": row.source_date,
                    "persisted_date": row.persisted_date,
                    "source_numbers": " ".join(f"{number:02d}" for number in row.source_numbers),
                    "persisted_numbers": " ".join(f"{number:02d}" for number in row.persisted_numbers),
                    "source_checksum": row.source_checksum,
                    "persisted_checksum": row.persisted_checksum,
                    "matches": row.matches,
                    "mismatch_fields": ",".join(row.mismatch_fields),
                }
            )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_official_caixa_validation(
    *,
    db_path: str | Path,
    last_n: int = DEFAULT_OFFICIAL_CAIXA_VALIDATION_LIMIT,
    report_dir: Path = DEFAULT_OFFICIAL_CAIXA_VALIDATION_DIR,
    client: CaixaApiClient | None = None,
    repository: ContestRepository | None = None,
) -> CaixaInstitutionalValidationResult:
    if last_n < 1:
        raise ValueError("last_n must be positive")

    client = client or CaixaApiClient()
    repository = repository or ContestRepository(db_path)
    repository.create_table()

    latest = client.fetch_latest()
    latest_contest = int(latest.contest_number)
    start_contest = max(1, latest_contest - last_n + 1)
    contest_numbers = list(range(start_contest, latest_contest + 1))

    source_results = client.fetch_contests(contest_numbers)
    source_by_contest = {int(result.contest_number): result for result in source_results}
    duplicated_contests = sorted({contest for contest in contest_numbers if contest_numbers.count(contest) > 1})

    with repository.transaction() as tx:
        for result in source_results:
            repository.save_contest(result.to_contest_record(), commit=False, session=tx)

    persisted_rows = {int(row["concurso"]): row for row in repository.get_all_contests() if int(row["concurso"]) in source_by_contest}

    validations: list[CaixaContestValidation] = []
    gap_contests: list[int] = []
    checksum_mismatches: list[int] = []

    for contest_number in contest_numbers:
        source_result = source_by_contest.get(contest_number)
        persisted_row = persisted_rows.get(contest_number)
        if source_result is None or persisted_row is None:
            gap_contests.append(contest_number)
            continue

        source_numbers = [int(number) for number in source_result.numbers]
        persisted_numbers = [int(str(number).lstrip("0") or "0") for number in persisted_row["dezenas"]]
        source_checksum = _contest_checksum(source_result.contest_number, source_result.draw_date, source_numbers)
        persisted_checksum = _contest_checksum(
            int(persisted_row["concurso"]),
            str(persisted_row["data"]),
            persisted_numbers,
        )
        mismatch_fields: list[str] = []
        if int(persisted_row["concurso"]) != int(source_result.contest_number):
            mismatch_fields.append("contest")
        if str(persisted_row["data"]) != str(source_result.draw_date):
            mismatch_fields.append("date")
        if persisted_numbers != source_numbers:
            mismatch_fields.append("numbers")
        if len(persisted_numbers) != len(source_numbers):
            mismatch_fields.append("quantity")
        if persisted_checksum != source_checksum:
            mismatch_fields.append("checksum")
            checksum_mismatches.append(contest_number)

        validations.append(
            CaixaContestValidation(
                contest_number=contest_number,
                source_date=str(source_result.draw_date),
                source_numbers=source_numbers,
                persisted_date=str(persisted_row["data"]),
                persisted_numbers=persisted_numbers,
                source_checksum=source_checksum,
                persisted_checksum=persisted_checksum,
                matches=not mismatch_fields,
                mismatch_fields=mismatch_fields,
            )
        )

    dataset_checksum = _dataset_checksum(validations)
    integrity_status = "validated" if not gap_contests and not duplicated_contests and not checksum_mismatches else "mismatch_detected"
    created_at = _now()

    payload = {
        "dataset_version": "official_caixa_v1",
        "source_provider": "caixa_official_api",
        "created_at": created_at,
        "latest_contest": latest_contest,
        "contests_evaluated": len(validations),
        "contest_numbers": contest_numbers,
        "source_count": len(source_results),
        "persisted_count": len(validations),
        "duplicated_contests": duplicated_contests,
        "gap_contests": gap_contests,
        "checksum_mismatches": checksum_mismatches,
        "dataset_checksum": dataset_checksum,
        "integrity_status": integrity_status,
        "db_backend": getattr(repository, "backend", "sqlite"),
        "engine_url": getattr(repository, "database_url", ""),
        "contests": [validation.as_dict() for validation in validations],
    }

    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "official_caixa_validation.json"
    csv_path = report_dir / "official_caixa_validation.csv"
    _write_json(json_path, payload)
    _persist_rows_csv(csv_path, validations)

    persisted_payload = {
        "json": str(json_path),
        "csv": str(csv_path),
        "dataset_checksum": dataset_checksum,
        "integrity_status": integrity_status,
    }

    return CaixaInstitutionalValidationResult(
        created_at=created_at,
        source_provider="caixa_official_api",
        db_backend=getattr(repository, "backend", "sqlite"),
        engine_url=getattr(repository, "database_url", ""),
        latest_contest=latest_contest,
        contests_evaluated=len(validations),
        contest_numbers=contest_numbers,
        source_count=len(source_results),
        persisted_count=len(validations),
        duplicated_contests=duplicated_contests,
        gap_contests=gap_contests,
        checksum_mismatches=checksum_mismatches,
        contest_validations=validations,
        dataset_checksum=dataset_checksum,
        integrity_status=integrity_status,
        report_paths={"json": str(json_path), "csv": str(csv_path)},
        persisted_payload=persisted_payload,
    )
