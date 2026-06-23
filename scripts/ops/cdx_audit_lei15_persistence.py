#!/usr/bin/env python3
"""CDX audit — Lei 15 CORE_002 persistence path (institutional only)."""

from __future__ import annotations

import json
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def _mock_streamlit() -> None:
    import streamlit as st  # noqa: WPS433

    if not hasattr(st, "session_state") or not isinstance(
        getattr(st, "session_state", None), dict
    ):
        st.session_state = {}  # type: ignore[attr-defined]


def _latest_event_snapshot(db_path: Path) -> dict[str, Any] | None:
    from lotoia.database.database import GeneratedGame, GenerationEvent, get_session

    with get_session(db_path) as session:
        event = (
            session.query(GenerationEvent)
            .order_by(GenerationEvent.id.desc())
            .first()
        )
        if event is None:
            return None
        games_count = (
            session.query(GeneratedGame)
            .filter(GeneratedGame.generation_event_id == event.id)
            .count()
        )
        ctx = dict(event.context_json or {})
        return {
            "generation_event_id": int(event.id),
            "created_at": str(event.created_at),
            "strategy": str(event.strategy),
            "analysis_batch_label": str(event.analysis_batch_label or ""),
            "total_games_row": games_count,
            "target_contest_ctx": ctx.get("target_contest"),
            "user_target_contest_ctx": ctx.get("user_target_contest"),
            "user_selected_target_ctx": ctx.get("user_selected_target"),
            "operational_status": ctx.get("operational_status"),
            "generation_mode": ctx.get("generation_mode"),
            "batch_id": ctx.get("batch_id"),
        }


def _query_event_detail(db_path: Path, event_id: int) -> dict[str, Any]:
    from lotoia.database.database import GeneratedGame, GenerationEvent, get_session

    with get_session(db_path) as session:
        event = session.get(GenerationEvent, event_id)
        if event is None:
            return {"found": False}
        games = (
            session.query(GeneratedGame)
            .filter(GeneratedGame.generation_event_id == event_id)
            .order_by(GeneratedGame.game_index.asc())
            .all()
        )
        ctx = dict(event.context_json or {})
        return {
            "found": True,
            "generation_event_id": event_id,
            "created_at": str(event.created_at),
            "strategy": event.strategy,
            "analysis_batch_label": event.analysis_batch_label,
            "context_json_keys": sorted(ctx.keys()),
            "target_contest": ctx.get("target_contest"),
            "user_target_contest": ctx.get("user_target_contest"),
            "user_selected_target": ctx.get("user_selected_target"),
            "operational_status": ctx.get("operational_status"),
            "total_games": len(games),
            "generated_games_target_contests": sorted(
                {int(g.target_contest) for g in games if g.target_contest is not None}
            ),
            "context_json_valid": _json_safe(ctx),
            "sample_game_context_valid": _json_safe(dict(games[0].context_json or {}))
            if games
            else True,
        }


def _json_safe(payload: Any) -> bool:
    try:
        json.dumps(payload, default=str)
        return True
    except TypeError:
        return False


def main() -> int:
    _mock_streamlit()
    from dashboard import institutional_app as app

    db_path = app.DB_PATH
    latest_official = app.get_latest_official_contest() or {}
    latest_num = app._safe_int(latest_official.get("contest_number"), default=None)
    user_target = int(latest_num) if latest_num else 3500

    print("=== CDX Lei15 Persistence Audit ===")
    print(f"timestamp={datetime.now(UTC).isoformat()}")
    print(f"db_path={db_path}")
    print(f"latest_official_contest={latest_num}")
    print(f"user_target_contest(manual)={user_target}")
    print(f"generation_enabled={not app._is_sovereign_generation_blocked()}")

    before = _latest_event_snapshot(db_path)
    print("\n--- BEFORE (latest generation_event) ---")
    print(json.dumps(before, indent=2, default=str))

    result: dict[str, Any] = {}
    persisted: dict[str, Any] = {}
    error: str | None = None

    try:
        result = app._run_clean_law15_generation(
            requested_count=10,
            selected_card_format=15,
            user_target_contest=user_target,
        )
        print("\n--- GENERATION RESULT (summary) ---")
        print(
            json.dumps(
                {
                    "games_count": len(result.get("games") or []),
                    "requested_count": result.get("requested_count"),
                    "target_contest": result.get("target_contest"),
                    "user_target_contest": result.get("user_target_contest"),
                    "user_selected_target": result.get("user_selected_target"),
                    "hierarchy_blocked": result.get("hierarchy_blocked"),
                    "blocked": result.get("blocked"),
                    "commander_status": (result.get("commander_report") or {}).get(
                        "status_comandante_saida"
                    ),
                    "analysis_batch_label": result.get("analysis_batch_label"),
                },
                indent=2,
            )
        )

        if not result.get("games"):
            print("ABORT: no games generated")
            return 2

        result["selected_card_format"] = 15
        result["card_format_label"] = "15 dezenas — CORE_002"

        persisted = app._persist_clean_law15_generation_history(
            result=result,
            selected_card_format=15,
        )
        print("\n--- PERSIST RESULT ---")
        print(json.dumps(persisted, indent=2, default=str))
    except Exception as exc:  # noqa: BLE001 — audit script
        error = traceback.format_exc()
        print("\n--- EXCEPTION ---")
        print(error)

    after = _latest_event_snapshot(db_path)
    print("\n--- AFTER (latest generation_event) ---")
    print(json.dumps(after, indent=2, default=str))

    new_event_id = int(persisted.get("generation_event_id", 0) or 0)
    if new_event_id > 0:
        detail = _query_event_detail(db_path, new_event_id)
        print("\n--- NEW EVENT DETAIL ---")
        print(json.dumps(detail, indent=2, default=str))

        groups = app._load_persisted_generation_event_groups(
            generation_event_id=new_event_id,
            use_cache=False,
        )
        print(f"\nhistory_group_loaded={bool(groups)} total_games={groups[0].get('total_games') if groups else 0}")

        conf_groups = app._load_official_conference_generation_groups(page_load=True)
        conf_ids = [
            int(g.get("generation_event_id", 0) or 0) for g in conf_groups
        ]
        print(f"conference_page_load_includes_new_event={new_event_id in conf_ids}")

    if error:
        return 1
    if persisted.get("persistence_blocked"):
        print("\nFAIL: persistence_blocked=", persisted.get("persistence_guard_status"))
        return 3
    if new_event_id <= 0:
        print("\nFAIL: no generation_event_id returned")
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
