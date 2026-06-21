"""Runtime performático — Conferir Resultados (M-PERF-CONFERIR-001 / M-OPS-289A)."""

from __future__ import annotations

from typing import Any, Mapping

import streamlit as st

from dashboard.institutional_light_mode import CACHE_TTL_SECONDS, CONFERENCE_EVENTS_LIMIT
from dashboard.institutional_operational_battery import (
    MISSION_ID as BATTERY_MISSION_ID,
    OPERATIONAL_BATTERY_ALL_ID,
    build_operational_battery_aggregate,
    format_operational_battery_label,
)

MISSION_ID = "M-PERF-CONFERIR-001"
OPS_FIX_MISSION_ID = "M-OPS-066-FIX-01"
BATTERY_OPS_MISSION_ID = BATTERY_MISSION_ID
CONFERENCE_LOTS_PAGE_SIZE = 10
SESSION_CONFERENCE_CACHE = "institutional_conference_perf_cache"
SESSION_CONFERENCE_SELECTED_GE = "conference_selected_generation_event_id"
SESSION_CONFERENCE_SELECTED_BATTERY = "conference_selected_battery_id"
SESSION_CONFERENCE_PAGE = "conference_lots_page_index"
SESSION_CONFERENCE_RUN_REQUESTED = "conference_run_requested"
NO_LOT_SELECTED_WARNING = (
    "Nenhuma bateria conferível selecionada. Escolha uma bateria na lista e clique em "
    "**Conferir bateria selecionada**."
)
INVALID_LOT_WARNING = (
    "battery_id inválido para conferência. Selecione uma bateria conferível "
    "oficializada no PostgreSQL."
)


def conference_cache_key(*, battery_id: str, contest_number: int) -> str:
    return f"{str(battery_id or '').strip()}:{int(contest_number)}"


def get_conference_result_cache() -> dict[str, Any]:
    cache = st.session_state.get(SESSION_CONFERENCE_CACHE)
    if not isinstance(cache, dict):
        cache = {}
        st.session_state[SESSION_CONFERENCE_CACHE] = cache
    return cache


def read_cached_conference_result(*, battery_id: str, contest_number: int) -> dict[str, Any] | None:
    payload = get_conference_result_cache().get(
        conference_cache_key(battery_id=battery_id, contest_number=contest_number)
    )
    return dict(payload) if isinstance(payload, Mapping) else None


def store_cached_conference_result(
    *,
    battery_id: str,
    contest_number: int,
    check_result: Mapping[str, Any],
) -> None:
    cache = get_conference_result_cache()
    cache[conference_cache_key(battery_id=battery_id, contest_number=contest_number)] = dict(check_result)
    st.session_state[SESSION_CONFERENCE_CACHE] = cache


def paginate_conference_lots(
    groups: list[dict[str, Any]],
    *,
    page_index: int,
    page_size: int = CONFERENCE_LOTS_PAGE_SIZE,
) -> tuple[list[dict[str, Any]], int, int]:
    """Retorna fatia da página, total de páginas e índice normalizado."""
    total = len(groups)
    if total <= 0:
        return [], 0, 0
    pages = max(1, (total + page_size - 1) // page_size)
    normalized_page = max(0, min(int(page_index), pages - 1))
    start = normalized_page * page_size
    end = start + page_size
    return list(groups[start:end]), pages, normalized_page


def format_conference_lot_label(group: Mapping[str, Any]) -> str:
    ge_id = int(group.get("generation_event_id", 0) or 0)
    games = int(group.get("total_games", 0) or 0)
    status = str(group.get("lot_operational_status") or group.get("conference_status") or "—")
    created = str(group.get("created_at") or "")[:10]
    batch_id = str(group.get("batch_id") or "—")
    return f"GE {ge_id} — {games} jogos — {status} — {batch_id} — {created}"


def default_conference_battery_id(battery_groups: list[dict[str, Any]]) -> str | None:
    """Última bateria conferível (maior generation_event_id agregado)."""
    if not battery_groups:
        return None
    ordered = sorted(
        battery_groups,
        key=lambda battery: max(
            [int(value) for value in list(battery.get("generation_event_ids") or []) if int(value or 0) > 0]
            or [0]
        ),
        reverse=True,
    )
    battery_id = str(ordered[0].get("battery_id") or "").strip()
    return battery_id or None


def default_conference_generation_event_id(groups: list[dict[str, Any]]) -> int | None:
    """Compatibilidade — último lote conferível (maior generation_event_id)."""
    candidates = sorted(
        {int(group.get("generation_event_id", 0) or 0) for group in groups if int(group.get("generation_event_id", 0) or 0) > 0},
        reverse=True,
    )
    return candidates[0] if candidates else None


def _safe_positive_generation_event_id(value: Any) -> int | None:
    try:
        ge_id = int(value)
    except (TypeError, ValueError):
        return None
    return ge_id if ge_id > 0 else None


def _safe_battery_id(value: Any) -> str | None:
    battery_id = str(value or "").strip()
    if not battery_id:
        return None
    if battery_id == OPERATIONAL_BATTERY_ALL_ID:
        return battery_id
    return battery_id if battery_id.startswith("BAT-") else None


def ensure_conference_session_defaults(*, default_battery_id: str | None = None, default_ge_id: int | None = None) -> None:
    """Inicializa chaves de sessão da conferência — apenas seleção visual temporária."""
    st.session_state.setdefault(SESSION_CONFERENCE_PAGE, 0)
    if SESSION_CONFERENCE_SELECTED_BATTERY not in st.session_state:
        resolved_battery = _safe_battery_id(default_battery_id)
        if resolved_battery is not None:
            st.session_state[SESSION_CONFERENCE_SELECTED_BATTERY] = resolved_battery
    if SESSION_CONFERENCE_SELECTED_GE not in st.session_state:
        resolved_default = _safe_positive_generation_event_id(default_ge_id)
        if resolved_default is not None:
            st.session_state[SESSION_CONFERENCE_SELECTED_GE] = resolved_default


def read_conference_selected_battery() -> str | None:
    """Lê seleção visual da bateria — não é fonte soberana (PostgreSQL permanece Lei 001)."""
    return _safe_battery_id(st.session_state.get(SESSION_CONFERENCE_SELECTED_BATTERY))


def read_conference_selected_ge() -> int | None:
    """Compatibilidade legada — preferir read_conference_selected_battery()."""
    return _safe_positive_generation_event_id(st.session_state.get(SESSION_CONFERENCE_SELECTED_GE))


def sync_conference_battery_selection(
    *,
    selectable_battery_ids: list[str],
    default_battery_id: str | None = None,
) -> str | None:
    """Alinha a chave do selectbox antes do widget renderizar (M-OPS-289A)."""
    ensure_conference_session_defaults(default_battery_id=default_battery_id)
    valid_ids = [_safe_battery_id(battery_id) for battery_id in selectable_battery_ids]
    valid_ids = [battery_id for battery_id in valid_ids if battery_id is not None]
    if not valid_ids:
        return None
    current = read_conference_selected_battery()
    if current not in valid_ids:
        st.session_state[SESSION_CONFERENCE_SELECTED_BATTERY] = valid_ids[0]
        return valid_ids[0]
    return current


def sync_conference_selectbox_selection(
    *,
    selectable_ids: list[int],
    default_ge_id: int | None = None,
) -> int | None:
    """Compatibilidade legada — preferir sync_conference_battery_selection()."""
    ensure_conference_session_defaults(default_ge_id=default_ge_id)
    valid_ids = [_safe_positive_generation_event_id(ge_id) for ge_id in selectable_ids]
    valid_ids = [ge_id for ge_id in valid_ids if ge_id is not None]
    if not valid_ids:
        return None
    current = read_conference_selected_ge()
    if current not in valid_ids:
        st.session_state[SESSION_CONFERENCE_SELECTED_GE] = valid_ids[0]
        return valid_ids[0]
    return current


def resolve_conference_battery_selection(
    battery_groups: list[dict[str, Any]],
    *,
    selected_battery_id: str | None,
) -> dict[str, Any]:
    battery_id = _safe_battery_id(selected_battery_id) or read_conference_selected_battery()
    if battery_id == OPERATIONAL_BATTERY_ALL_ID:
        return build_operational_battery_aggregate(battery_groups)
    for battery in battery_groups:
        if str(battery.get("battery_id") or "").strip() == battery_id:
            return dict(battery)
    return {}


def is_valid_resolved_battery_id(resolved_battery_id: str | None) -> bool:
    return _safe_battery_id(resolved_battery_id) is not None


def is_valid_resolved_generation_event_id(resolved_ge_id: int | None) -> bool:
    return _safe_positive_generation_event_id(resolved_ge_id) is not None


def conference_runtime_trace() -> dict[str, Any]:
    return {
        "mission_id": MISSION_ID,
        "battery_mission_id": BATTERY_OPS_MISSION_ID,
        "conference_lots_page_size": CONFERENCE_LOTS_PAGE_SIZE,
        "conference_events_limit": CONFERENCE_EVENTS_LIMIT,
        "cache_ttl_seconds": CACHE_TTL_SECONDS,
        "single_battery_default": True,
        "lazy_conference_compute": True,
        "ops_fix_mission_id": OPS_FIX_MISSION_ID,
        "session_selected_battery_key": SESSION_CONFERENCE_SELECTED_BATTERY,
        "session_selected_ge_key": SESSION_CONFERENCE_SELECTED_GE,
        "battery_label_formatter": format_operational_battery_label.__name__,
    }
