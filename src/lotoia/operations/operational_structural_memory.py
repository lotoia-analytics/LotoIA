"""M-MEMORY-001 — persistência automática de cobertura estrutural (memória evolutiva)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from lotoia.database.database import (
    DEFAULT_DATABASE_PATH,
    GenerationEvent,
    OperationalStructuralMemory,
    get_session,
)
from lotoia.generation.m_core_003_prefix_suffix_policy import compute_pattern_distribution
from lotoia.governance.lei15_core_002_sovereign import is_sovereign_core_label
from lotoia.observability.card_structure_diagnostics import _load_official_cards
from lotoia.observability.m_core_003_bias_monitoring import build_m_core_003_bias_monitoring_report
from lotoia.statistics.card_structure import compare_structure_profiles, resolve_cartao_final_from_game

MISSION_ID = "M-MEMORY-001"
MEMORY_STATUS_PERSISTED = "PERSISTED"
STATUS_CRITICAL_BIAS = "STATUS_CRITICAL_BIAS"
CRITICAL_DIVERGENCE_THRESHOLD_PCT = 15.0
DEFAULT_TIMELINE_LIMIT = 50


def _extract_cards_from_games(games: Sequence[Mapping[str, Any]]) -> list[list[int]]:
    cards: list[list[int]] = []
    for game in games:
        numbers = resolve_cartao_final_from_game(dict(game))
        if len(numbers) >= 15:
            cards.append([int(value) for value in numbers])
    return cards


def compute_official_divergence_score(bias_report: Mapping[str, Any]) -> float:
    """Desvio máximo (%) vs frequência histórica oficial — base M-CORE-003."""
    max_deviation = 0.0
    for row in list(bias_report.get("ratio_rows") or []):
        ratio = float(row.get("ratio") or 0.0)
        if ratio > 1.0:
            max_deviation = max(max_deviation, (ratio - 1.0) * 100.0)
    return round(max_deviation, 2)


def build_bias_alerts(bias_report: Mapping[str, Any]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for row in list(bias_report.get("ratio_rows") or []):
        alerts.append(
            {
                "kind": str(row.get("kind") or ""),
                "pattern": str(row.get("pattern") or ""),
                "generated_pct": float(row.get("generated_pct") or 0.0),
                "historical_pct": float(row.get("historical_pct") or 0.0),
                "ratio": float(row.get("ratio") or 0.0),
                "severity": str(row.get("severity") or ""),
                "message": (
                    f"{row.get('kind', '')} {row.get('pattern', '')}: "
                    f"{row.get('ratio', '—')}x vs histórico"
                ),
            }
        )
    verdict = str(bias_report.get("verdict") or "")
    if verdict and not bool(bias_report.get("compliance")):
        alerts.insert(
            0,
            {
                "kind": "verdict",
                "pattern": "",
                "severity": "severo" if int(bias_report.get("severe_bias_count", 0) or 0) > 0 else "moderado",
                "message": verdict,
            },
        )
    return alerts


def compute_operational_structural_memory_snapshot(
    games: Sequence[Mapping[str, Any]],
    *,
    db_path: Path | str | None = None,
    generation_event_id: int | None = None,
) -> dict[str, Any]:
    """Calcula snapshot de memória estrutural a partir do GP final (hook pós-compose)."""
    cards = _extract_cards_from_games(games)
    if not cards:
        return {
            "mission_id": MISSION_ID,
            "available": False,
            "reason": "no_valid_15d_cards",
        }

    bias_report = build_m_core_003_bias_monitoring_report(
        cards,
        games_count=len(cards),
        generation_event_ids=[int(generation_event_id)] if generation_event_id else None,
    )
    prefix_distribution = compute_pattern_distribution(cards, kind="prefix")
    suffix_distribution = compute_pattern_distribution(cards, kind="suffix")
    official_divergence_score = compute_official_divergence_score(bias_report)
    bias_alerts = build_bias_alerts(bias_report)

    comparacao_oficial: dict[str, Any] = {"available": False}
    if db_path is not None:
        try:
            with get_session(db_path) as session:
                official_cards, official_contests = _load_official_cards(session, limit=50)
            comparacao_oficial = compare_structure_profiles(cards, official_cards)
            comparacao_oficial["official_contests_window"] = list(official_contests)
        except Exception:  # noqa: BLE001 — snapshot não deve bloquear geração
            comparacao_oficial = {"available": False, "reason": "official_compare_failed"}

    memory_status = MEMORY_STATUS_PERSISTED
    if official_divergence_score >= CRITICAL_DIVERGENCE_THRESHOLD_PCT:
        memory_status = STATUS_CRITICAL_BIAS
        bias_alerts.insert(
            0,
            {
                "kind": "critical_bias",
                "pattern": "",
                "severity": "critico",
                "message": (
                    f"Divergência oficial {official_divergence_score:.1f}% "
                    f">= limiar {CRITICAL_DIVERGENCE_THRESHOLD_PCT:.0f}% — "
                    "notificar agent_operador_ml"
                ),
                "agent_operador_ml_notify": True,
            },
        )

    return {
        "mission_id": MISSION_ID,
        "available": True,
        "recorded_at": datetime.now(UTC).isoformat(),
        "generation_event_id": int(generation_event_id or 0) or None,
        "games_count": len(cards),
        "prefix_distribution": prefix_distribution,
        "suffix_distribution": suffix_distribution,
        "official_divergence_score": official_divergence_score,
        "bias_alerts": bias_alerts,
        "memory_status": memory_status,
        "bias_report": dict(bias_report),
        "comparacao_oficial": comparacao_oficial,
        "coverage_snapshot": {
            "mission_id": MISSION_ID,
            "games_count": len(cards),
            "prefix_distribution": prefix_distribution,
            "suffix_distribution": suffix_distribution,
            "official_divergence_score": official_divergence_score,
            "bias_alerts": bias_alerts,
            "memory_status": memory_status,
            "bias_report_summary": {
                "verdict": bias_report.get("verdict"),
                "compliance": bias_report.get("compliance"),
                "severe_bias_count": bias_report.get("severe_bias_count"),
                "moderate_bias_count": bias_report.get("moderate_bias_count"),
                "entropy_prefix": bias_report.get("entropy_prefix"),
                "entropy_suffix": bias_report.get("entropy_suffix"),
            },
            "comparacao_oficial": comparacao_oficial,
        },
    }


def persist_operational_structural_memory(
    db_path: Path | str,
    *,
    generation_event_id: int,
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Grava ou atualiza memória estrutural para um generation_event."""
    ge_id = int(generation_event_id or 0)
    if ge_id <= 0:
        return {"persisted": False, "reason": "invalid_generation_event_id"}
    if not bool(snapshot.get("available")):
        return {"persisted": False, "reason": str(snapshot.get("reason") or "snapshot_unavailable")}

    payload = dict(snapshot)
    with get_session(db_path) as session:
        event = session.get(GenerationEvent, ge_id)
        if event is None:
            return {"persisted": False, "reason": "generation_event_not_found"}

        existing = (
            session.query(OperationalStructuralMemory)
            .filter(OperationalStructuralMemory.generation_event_id == ge_id)
            .one_or_none()
        )
        row = existing or OperationalStructuralMemory(generation_event_id=ge_id)
        row.recorded_at = datetime.now(UTC)
        row.prefix_distribution = dict(payload.get("prefix_distribution") or {})
        row.suffix_distribution = dict(payload.get("suffix_distribution") or {})
        row.official_divergence_score = float(payload.get("official_divergence_score") or 0.0)
        row.bias_alerts = list(payload.get("bias_alerts") or [])
        row.mission_id = str(payload.get("mission_id") or MISSION_ID)
        row.memory_status = str(payload.get("memory_status") or MEMORY_STATUS_PERSISTED)
        row.coverage_snapshot = dict(payload.get("coverage_snapshot") or {})
        session.add(row)
        session.commit()
        session.refresh(row)
        return {
            "persisted": True,
            "memory_row_id": int(row.id),
            "generation_event_id": ge_id,
            "memory_status": row.memory_status,
            "official_divergence_score": row.official_divergence_score,
            "mission_id": row.mission_id,
        }


def load_operational_structural_memory_for_event(
    db_path: Path | str,
    generation_event_id: int,
) -> dict[str, Any] | None:
    ge_id = int(generation_event_id or 0)
    if ge_id <= 0:
        return None
    with get_session(db_path) as session:
        row = (
            session.query(OperationalStructuralMemory)
            .filter(OperationalStructuralMemory.generation_event_id == ge_id)
            .one_or_none()
        )
        if row is None:
            return None
        return _serialize_memory_row(row)


def load_operational_structural_memory_timeline(
    db_path: Path | str,
    *,
    limit: int = DEFAULT_TIMELINE_LIMIT,
    sovereign_only: bool = True,
) -> list[dict[str, Any]]:
    """Últimas N gerações com memória persistida — independente da fila operacional ativa."""
    max_rows = max(1, int(limit or DEFAULT_TIMELINE_LIMIT))
    with get_session(db_path) as session:
        query = (
            session.query(OperationalStructuralMemory, GenerationEvent)
            .join(GenerationEvent, GenerationEvent.id == OperationalStructuralMemory.generation_event_id)
            .order_by(OperationalStructuralMemory.recorded_at.desc(), OperationalStructuralMemory.id.desc())
            .limit(max_rows)
        )
        rows = query.all()

    timeline: list[dict[str, Any]] = []
    for memory_row, event in rows:
        if sovereign_only and not is_sovereign_core_label(
            str(getattr(event, "analysis_batch_label", "") or "")
        ):
            continue
        payload = _serialize_memory_row(memory_row)
        payload["analysis_batch_label"] = str(getattr(event, "analysis_batch_label", "") or "")
        payload["games_count_event"] = len(list(getattr(event, "generated_games", []) or []))
        timeline.append(payload)
    return timeline


def build_bias_timeline_trend(timeline: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Resume tendência de qualidade estrutural ao longo do histórico de memória."""
    ordered = list(timeline)
    if not ordered:
        return {
            "available": False,
            "points": 0,
            "trend": "indisponível",
        }
    scores = [float(row.get("official_divergence_score") or 0.0) for row in ordered]
    chronological = list(reversed(scores))
    if len(chronological) < 2:
        trend = "estável"
    else:
        delta = chronological[-1] - chronological[0]
        if delta <= -1.0:
            trend = "melhorando"
        elif delta >= 1.0:
            trend = "piorando"
        else:
            trend = "estável"
    critical_count = sum(
        1 for row in ordered if str(row.get("memory_status") or "") == STATUS_CRITICAL_BIAS
    )
    return {
        "available": True,
        "points": len(ordered),
        "latest_score": scores[0] if scores else 0.0,
        "oldest_score": scores[-1] if scores else 0.0,
        "avg_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
        "critical_bias_count": critical_count,
        "trend": trend,
    }


def should_persist_structural_memory_for_batch(batch_label: str | None) -> bool:
    return is_sovereign_core_label(str(batch_label or ""))


def _serialize_memory_row(row: OperationalStructuralMemory) -> dict[str, Any]:
    recorded_at = row.recorded_at
    if recorded_at is not None and recorded_at.tzinfo is None:
        recorded_at = recorded_at.replace(tzinfo=UTC)
    return {
        "memory_row_id": int(row.id),
        "generation_event_id": int(row.generation_event_id),
        "recorded_at": recorded_at.isoformat() if recorded_at else None,
        "prefix_distribution": dict(row.prefix_distribution or {}),
        "suffix_distribution": dict(row.suffix_distribution or {}),
        "official_divergence_score": float(row.official_divergence_score or 0.0),
        "bias_alerts": list(row.bias_alerts or []),
        "mission_id": str(row.mission_id or MISSION_ID),
        "memory_status": str(row.memory_status or MEMORY_STATUS_PERSISTED),
        "coverage_snapshot": dict(row.coverage_snapshot or {}),
    }
