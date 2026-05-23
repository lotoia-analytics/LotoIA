from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import text

from lotoia.database.database import DEFAULT_DATABASE_PATH, get_session


def _isoformat(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return str(value.isoformat())
    return str(value)


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _safe_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


@dataclass(frozen=True, slots=True)
class UserLifecycleEvent:
    created_at: str
    event_type: str
    actor_type: str
    actor_id: int | None
    subject: str
    status: str
    runtime_origin: str
    details: dict[str, Any]


@dataclass(frozen=True, slots=True)
class UserLifecycleSnapshot:
    created_at: datetime
    source: str
    summary: dict[str, Any]
    lifecycle: dict[str, Any]
    analytics: dict[str, Any]
    timeline: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at.isoformat(),
            "source": self.source,
            "summary": self.summary,
            "lifecycle": self.lifecycle,
            "analytics": self.analytics,
            "timeline": self.timeline,
        }


def _merge_timeline_rows(rows: Iterable[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    timeline = sorted(rows, key=lambda item: item["created_at"], reverse=True)
    return timeline[:limit]


def build_user_lifecycle_analytics(
    db_path: Path = DEFAULT_DATABASE_PATH,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    with get_session(db_path) as session:
        institutional_users = _safe_int(session.execute(text("SELECT COUNT(*) FROM institutional_users")).scalar())
        auth_events = _safe_int(session.execute(text("SELECT COUNT(*) FROM auth_events")).scalar())
        auth_sessions = _safe_int(session.execute(text("SELECT COUNT(*) FROM auth_sessions")).scalar())
        active_sessions = _safe_int(
            session.execute(text("SELECT COUNT(*) FROM auth_sessions WHERE status = 'active'")).scalar()
        )
        ended_sessions = _safe_int(
            session.execute(text("SELECT COUNT(*) FROM auth_sessions WHERE status = 'ended'")).scalar()
        )
        access_events = _safe_int(session.execute(text("SELECT COUNT(*) FROM access_events")).scalar())
        feature_flags = _safe_int(session.execute(text("SELECT COUNT(*) FROM feature_flags")).scalar())
        feature_usage_events = _safe_int(session.execute(text("SELECT COUNT(*) FROM feature_usage_events")).scalar())
        generation_events = _safe_int(session.execute(text("SELECT COUNT(*) FROM generation_events")).scalar())
        ml_usage_events = _safe_int(session.execute(text("SELECT COUNT(*) FROM ml_usage_events")).scalar())
        check_events = _safe_int(session.execute(text("SELECT COUNT(*) FROM check_events")).scalar())
        report_events = _safe_int(session.execute(text("SELECT COUNT(*) FROM report_events")).scalar())
        expansion_events = _safe_int(session.execute(text("SELECT COUNT(*) FROM expansion_events")).scalar())
        reconciliation_events = _safe_int(session.execute(text("SELECT COUNT(*) FROM reconciliation_events")).scalar())
        workflow_events = _safe_int(session.execute(text("SELECT COUNT(*) FROM workflow_events")).scalar())

        role_rows = session.execute(
            text(
                """
                SELECT role, COUNT(*) AS total
                FROM institutional_users
                GROUP BY role
                ORDER BY total DESC, role ASC
                """
            )
        ).all()
        role_distribution = {str(row[0]): _safe_int(row[1]) for row in role_rows}

        feature_rows = session.execute(
            text(
                """
                SELECT feature_name, COUNT(*) AS total, SUM(CASE WHEN allowed = 1 THEN 1 ELSE 0 END) AS allowed_total
                FROM feature_usage_events
                GROUP BY feature_name
                ORDER BY total DESC, feature_name ASC
                """
            )
        ).all()
        feature_usage = {
            str(row[0]): {
                "total": _safe_int(row[1]),
                "allowed": _safe_int(row[2]),
            }
            for row in feature_rows
        }

        timeline_rows: list[dict[str, Any]] = []
        timeline_rows.extend(
            {
                "created_at": _isoformat(row[0]),
                "event_type": str(row[1]),
                "actor_type": "user",
                "actor_id": _safe_int(row[2]) if row[2] is not None else None,
                "subject": f"session:{row[3]}",
                "status": str(row[4]),
                "runtime_origin": str(row[5]),
                "details": _safe_json(row[6]),
            }
            for row in session.execute(
                text(
                    """
                    SELECT created_at, event_type, user_id, session_id, 'completed' AS status, runtime_origin, payload
                    FROM auth_events
                    ORDER BY created_at DESC, id DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).all()
        )
        timeline_rows.extend(
            {
                "created_at": _isoformat(row[0]),
                "event_type": "access",
                "actor_type": "user",
                "actor_id": _safe_int(row[1]) if row[1] is not None else None,
                "subject": str(row[3]),
                "status": "allowed" if _safe_int(row[4]) else "denied",
                "runtime_origin": str(row[5]),
                "details": _safe_json(row[6]),
            }
            for row in session.execute(
                text(
                    """
                    SELECT created_at, user_id, session_id, feature_name, allowed, runtime_origin, payload
                    FROM access_events
                    ORDER BY created_at DESC, id DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).all()
        )
        timeline_rows.extend(
            {
                "created_at": _isoformat(row[0]),
                "event_type": "feature_usage",
                "actor_type": "user",
                "actor_id": _safe_int(row[1]) if row[1] is not None else None,
                "subject": str(row[3]),
                "status": "allowed" if _safe_int(row[4]) else "denied",
                "runtime_origin": str(row[5]),
                "details": _safe_json(row[6]),
            }
            for row in session.execute(
                text(
                    """
                    SELECT created_at, user_id, session_id, feature_name, allowed, runtime_origin, payload
                    FROM feature_usage_events
                    ORDER BY created_at DESC, id DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).all()
        )
        timeline_rows.extend(
            {
                "created_at": _isoformat(row[0]),
                "event_type": "generation",
                "actor_type": "lead",
                "actor_id": _safe_int(row[1]) if row[1] is not None else None,
                "subject": str(row[5]),
                "status": "ml" if _safe_int(row[4]) else "standard",
                "runtime_origin": "public",
                "details": {
                    "first_name": str(row[2] or ""),
                    "whatsapp": str(row[3] or ""),
                    "ranking_score": float(row[6] or 0.0),
                    "execution_time_ms": float(row[7] or 0.0),
                },
            }
            for row in session.execute(
                text(
                    """
                    SELECT created_at, lead_id, first_name, whatsapp, ml_enabled, strategy, ranking_score, execution_time_ms
                    FROM generation_events
                    ORDER BY created_at DESC, id DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).all()
        )
        timeline_rows.extend(
            {
                "created_at": _isoformat(row[0]),
                "event_type": "check",
                "actor_type": "lead",
                "actor_id": _safe_int(row[1]) if row[1] is not None else None,
                "subject": f"contest:{row[2]}",
                "status": f"hits:{_safe_int(row[4])}",
                "runtime_origin": "public",
                "details": {
                    "selected_numbers": _safe_json(row[3]),
                    "result_payload": _safe_json(row[5]),
                },
            }
            for row in session.execute(
                text(
                    """
                    SELECT created_at, lead_id, contest_id, selected_numbers, hits, result_payload
                    FROM check_events
                    ORDER BY created_at DESC, id DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).all()
        )
        timeline_rows.extend(
            {
                "created_at": _isoformat(row[0]),
                "event_type": "report",
                "actor_type": "lead",
                "actor_id": _safe_int(row[1]) if row[1] is not None else None,
                "subject": str(row[4]),
                "status": str(row[5] or ""),
                "runtime_origin": str(row[6] or ""),
                "details": _safe_json(row[7]),
            }
            for row in session.execute(
                text(
                    """
                    SELECT created_at, lead_id, generation_event_id, report_type, generation_origin, runtime_origin, strategy_profile, payload
                    FROM report_events
                    ORDER BY created_at DESC, id DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).all()
        )
        timeline_rows.extend(
            {
                "created_at": _isoformat(row[0]),
                "event_type": "expansion",
                "actor_type": "lead",
                "actor_id": _safe_int(row[1]) if row[1] is not None else None,
                "subject": str(row[4]),
                "status": str(row[5] or ""),
                "runtime_origin": str(row[6] or ""),
                "details": {
                    "strategy_profile": str(row[7] or ""),
                    "payload": _safe_json(row[8]),
                },
            }
            for row in session.execute(
                text(
                    """
                    SELECT created_at, lead_id, generation_event_id, origin, expansion_type, expansion_size, runtime_origin, strategy_profile, payload
                    FROM expansion_events
                    ORDER BY created_at DESC, id DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).all()
        )
        timeline_rows.extend(
            {
                "created_at": _isoformat(row[0]),
                "event_type": "reconciliation",
                "actor_type": "lead",
                "actor_id": _safe_int(row[1]) if row[1] is not None else None,
                "subject": str(row[3]),
                "status": f"hits:{_safe_int(row[4])}",
                "runtime_origin": str(row[6] or ""),
                "details": {
                    "matched_numbers": _safe_json(row[5]),
                    "payload": _safe_json(row[7]),
                },
            }
            for row in session.execute(
                text(
                    """
                    SELECT created_at, lead_id, generation_event_id, reconciliation_type, hits, matched_numbers, runtime_origin, payload
                    FROM reconciliation_events
                    ORDER BY created_at DESC, id DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).all()
        )
        timeline_rows.extend(
            {
                "created_at": _isoformat(row[0]),
                "event_type": "workflow",
                "actor_type": "system",
                "actor_id": None,
                "subject": str(row[2]),
                "status": str(row[6] or ""),
                "runtime_origin": str(row[5] or ""),
                "details": {
                    "workflow_id": str(row[1] or ""),
                    "correlation_id": str(row[3] or ""),
                    "stage": str(row[4] or ""),
                    "finished_at": _isoformat(row[7]),
                    "duration_ms": float(row[8] or 0.0) if row[8] is not None else None,
                    "error_message": str(row[9] or ""),
                    "payload": _safe_json(row[10]),
                },
            }
            for row in session.execute(
                text(
                    """
                    SELECT started_at, workflow_id, workflow_name, correlation_id, stage, source, status, finished_at, duration_ms, error_message, payload
                    FROM workflow_events
                    ORDER BY started_at DESC, id DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).all()
        )

    timeline = _merge_timeline_rows(timeline_rows, limit=limit)
    lifecycle_summary = {
        "institutional_users": institutional_users,
        "auth_sessions": auth_sessions,
        "active_sessions": active_sessions,
        "ended_sessions": ended_sessions,
        "auth_events": auth_events,
        "access_events": access_events,
        "feature_flags": feature_flags,
        "feature_usage_events": feature_usage_events,
        "generation_events": generation_events,
        "ml_usage_events": ml_usage_events,
        "check_events": check_events,
        "report_events": report_events,
        "expansion_events": expansion_events,
        "reconciliation_events": reconciliation_events,
        "workflow_events": workflow_events,
        "role_distribution": role_distribution,
        "feature_usage": feature_usage,
        "event_volume": (
            auth_events
            + access_events
            + feature_usage_events
            + generation_events
            + ml_usage_events
            + check_events
            + report_events
            + expansion_events
            + reconciliation_events
            + workflow_events
        ),
    }
    lifecycle_metrics = {
        "session_activity_rate": round(active_sessions / auth_sessions, 4) if auth_sessions else 0.0,
        "user_activation_rate": round((auth_events + access_events) / institutional_users, 4) if institutional_users else 0.0,
        "feature_governance_density": round(feature_usage_events / feature_flags, 4) if feature_flags else 0.0,
        "event_coverage": round(
            (
                generation_events
                + check_events
                + report_events
                + expansion_events
                + reconciliation_events
                + workflow_events
            )
            / max(1, institutional_users),
            4,
        ),
    }
    snapshot = UserLifecycleSnapshot(
        created_at=datetime.now(UTC),
        source=str(db_path),
        summary={
            "status": "active" if lifecycle_summary["event_volume"] else "idle",
            "timeline_size": len(timeline),
            "active_users": institutional_users,
            "active_sessions": active_sessions,
            "feature_usage_events": feature_usage_events,
            "event_volume": lifecycle_summary["event_volume"],
        },
        lifecycle=lifecycle_summary,
        analytics=lifecycle_metrics,
        timeline=timeline,
    )
    return snapshot.to_dict()
