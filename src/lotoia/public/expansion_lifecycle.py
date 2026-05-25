from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.database.public_repository import (
    cleanup_expansion_history,
    save_institutional_memory_refresh,
    save_validated_expansion,
)

EXPANSION_STATUS_PENDING = "PENDING"
EXPANSION_STATUS_VALIDATED = "VALIDATED"
EXPANSION_STATUS_ARCHIVED = "ARCHIVED"
EXPANSION_STATUS_DISCARDED = "DISCARDED"
EXPANSION_STATUS_PREMIUM = "PREMIUM"
EXPANSION_STATUSES = (
    EXPANSION_STATUS_PENDING,
    EXPANSION_STATUS_VALIDATED,
    EXPANSION_STATUS_ARCHIVED,
    EXPANSION_STATUS_DISCARDED,
    EXPANSION_STATUS_PREMIUM,
)


@dataclass(frozen=True)
class ExpansionLifecycleRow:
    ranking: int
    dezenas: str
    numbers: list[int]
    status: str
    hits: int
    recurrence_score: float
    proximity_score: float
    efficiency_score: float
    scientific_score: float
    diversity_score: float
    overlap_score: float
    profile_type: str
    retention_reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ranking": self.ranking,
            "dezenas": self.dezenas,
            "numbers": list(self.numbers),
            "status": self.status,
            "hits": self.hits,
            "recurrence_score": self.recurrence_score,
            "proximity_score": self.proximity_score,
            "efficiency_score": self.efficiency_score,
            "scientific_score": self.scientific_score,
            "diversity_score": self.diversity_score,
            "overlap_score": self.overlap_score,
            "profile_type": self.profile_type,
            "retention_reason": self.retention_reason,
        }


def _numbers_from_row(row: dict[str, Any]) -> list[int]:
    numbers = row.get("numbers") or []
    if not numbers and row.get("dezenas"):
        numbers = [int(item) for item in str(row.get("dezenas", "")).split() if str(item).isdigit()]
    return [int(item) for item in numbers]


def _official_set(official_numbers: Sequence[int] | None) -> set[int]:
    return {int(number) for number in official_numbers or []}


def _classify_status(*, hits: int, scientific_score: float, diversity_score: float, overlap_score: float, official_present: bool) -> tuple[str, str]:
    if not official_present:
        return EXPANSION_STATUS_PENDING, "aguardando_validacao"
    if scientific_score >= 72.0 and diversity_score >= 0.45 and overlap_score <= 0.35:
        return EXPANSION_STATUS_PREMIUM, "alta_performance"
    if hits >= 13 or scientific_score >= 62.0:
        return EXPANSION_STATUS_VALIDATED, "validado"
    if overlap_score >= 0.60:
        return EXPANSION_STATUS_DISCARDED, "redundante"
    return EXPANSION_STATUS_ARCHIVED, "relevante_preservado"


def evaluate_expansion_lifecycle(
    preview_payload: dict[str, Any],
    *,
    official_numbers: Sequence[int] | None = None,
) -> dict[str, Any]:
    premium_games = list(preview_payload.get("premium_games", []))
    official = _official_set(official_numbers)
    official_present = bool(official)

    rows: list[ExpansionLifecycleRow] = []
    for ranking, row in enumerate(premium_games, start=1):
        numbers = _numbers_from_row(row)
        hits = len(set(numbers).intersection(official)) if official_present else 0
        scientific_score = float(row.get("scientific_score", 0.0))
        diversity_score = float(row.get("diversity_score", row.get("diversity_index", 0.0)))
        overlap_score = float(row.get("overlap_score", 0.0))
        status, reason = _classify_status(
            hits=hits,
            scientific_score=scientific_score,
            diversity_score=diversity_score,
            overlap_score=overlap_score,
            official_present=official_present,
        )
        rows.append(
            ExpansionLifecycleRow(
                ranking=ranking,
                dezenas=" ".join(f"{number:02d}" for number in numbers),
                numbers=numbers,
                status=status,
                hits=hits,
                recurrence_score=float(row.get("recurrence_score", 0.0)),
                proximity_score=float(row.get("historical_similarity", row.get("proximity", 0.0))),
                efficiency_score=max(0.0, round((hits * 10.0) + (scientific_score * 0.25) - (overlap_score * 15.0), 4)),
                scientific_score=scientific_score,
                diversity_score=diversity_score,
                overlap_score=overlap_score,
                profile_type=str(row.get("profile_type") or row.get("historical_profile") or "indefinido"),
                retention_reason=reason,
            )
        )

    counts = {status: 0 for status in EXPANSION_STATUSES}
    for row in rows:
        counts[row.status] = counts.get(row.status, 0) + 1
    for status in EXPANSION_STATUSES:
        counts.setdefault(status, 0)

    kept = counts[EXPANSION_STATUS_VALIDATED] + counts[EXPANSION_STATUS_PREMIUM] + counts[EXPANSION_STATUS_ARCHIVED]
    discarded = counts[EXPANSION_STATUS_DISCARDED]
    average_score = round(sum(row.scientific_score for row in rows) / len(rows), 4) if rows else 0.0
    average_diversity = round(sum(row.diversity_score for row in rows) / len(rows), 4) if rows else 0.0
    average_overlap = round(sum(row.overlap_score for row in rows) / len(rows), 4) if rows else 0.0

    badges = [
        {"status": EXPANSION_STATUS_PENDING, "label": "aguardando validação", "count": counts[EXPANSION_STATUS_PENDING]},
        {"status": EXPANSION_STATUS_VALIDATED, "label": "validado", "count": counts[EXPANSION_STATUS_VALIDATED]},
        {"status": EXPANSION_STATUS_ARCHIVED, "label": "arquivado", "count": counts[EXPANSION_STATUS_ARCHIVED]},
        {"status": EXPANSION_STATUS_PREMIUM, "label": "premium", "count": counts[EXPANSION_STATUS_PREMIUM]},
        {"status": EXPANSION_STATUS_DISCARDED, "label": "descartado", "count": counts[EXPANSION_STATUS_DISCARDED]},
    ]

    return {
        "status": EXPANSION_STATUS_PENDING if not official_present else (EXPANSION_STATUS_PREMIUM if counts[EXPANSION_STATUS_PREMIUM] else EXPANSION_STATUS_VALIDATED if counts[EXPANSION_STATUS_VALIDATED] else EXPANSION_STATUS_ARCHIVED if counts[EXPANSION_STATUS_ARCHIVED] else EXPANSION_STATUS_DISCARDED if counts[EXPANSION_STATUS_DISCARDED] else EXPANSION_STATUS_PENDING),
        "official_present": official_present,
        "counts": counts,
        "summary": {
            "total": len(rows),
            "kept": kept,
            "discarded": discarded,
            "average_score": average_score,
            "average_diversity": average_diversity,
            "average_overlap": average_overlap,
        },
        "rows": [row.to_dict() for row in rows],
        "badges": badges,
    }


def promote_validated_expansions(
    preview_payload: dict[str, Any],
    *,
    official_numbers: Sequence[int] | None = None,
    contest_id: int | None = None,
    db_path: Path = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    lifecycle = evaluate_expansion_lifecycle(preview_payload, official_numbers=official_numbers)
    promoted: list[dict[str, Any]] = []
    generation_event_id = preview_payload.get("generation_event_id")
    expansion_event_id = preview_payload.get("institutional_expansion_event", {}).get("id")

    for row in lifecycle["rows"]:
        if row["status"] not in {EXPANSION_STATUS_VALIDATED, EXPANSION_STATUS_PREMIUM, EXPANSION_STATUS_ARCHIVED}:
            continue
        promoted.append(
            save_validated_expansion(
                expansion_event_id=int(expansion_event_id) if expansion_event_id is not None else None,
                generation_event_id=int(generation_event_id) if generation_event_id is not None else None,
                contest_id=contest_id,
                status=row["status"],
                profile_type=str(row.get("profile_type", "")),
                scientific_score=float(row.get("scientific_score", 0.0)),
                diversity_score=float(row.get("diversity_score", 0.0)),
                overlap_score=float(row.get("overlap_score", 0.0)),
                hits=int(row.get("hits", 0)),
                recurrence_score=float(row.get("recurrence_score", 0.0)),
                proximity_score=float(row.get("proximity_score", 0.0)),
                efficiency_score=float(row.get("efficiency_score", 0.0)),
                premium_rank=int(row.get("ranking", 0)),
                payload={"preview_payload": preview_payload, "lifecycle": lifecycle, "row": row},
                metrics=preview_payload.get("metrics", {}),
                db_path=db_path,
            )
        )
    memory_refresh: dict[str, Any] | None = None
    if promoted:
        execution_id = f"institutional-expansion-{contest_id or 'pending'}-{len(promoted)}"
        memory_id = f"institutional-expansion-memory-{contest_id or 'pending'}"
        memory_refresh = save_institutional_memory_refresh(
            execution_id=execution_id,
            snapshot_type="institutional_validated_expansions",
            state_type="validated_expansion_memory",
            memory_id=memory_id,
            state={
                "contest_id": contest_id,
                "promoted_count": len(promoted),
                "status_counts": lifecycle["counts"],
                "summary": lifecycle["summary"],
            },
            metadata={
                "source": "expansion_lifecycle.promote_validated_expansions",
                "official_present": lifecycle["official_present"],
            },
            lineage_events=[
                {
                    "event_type": "expansion_promoted",
                    "entity_type": "institutional_validated_expansion",
                    "entity_id": str(item.get("id", "")),
                    "status": item.get("status", ""),
                    "ranking": item.get("premium_rank", 0),
                }
                for item in promoted
            ],
            db_path=db_path,
        )
    return {
        "lifecycle": lifecycle,
        "promoted": promoted,
        "summary": {"promoted_count": len(promoted)},
        "memory_refresh": memory_refresh,
    }
