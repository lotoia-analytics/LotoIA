"""Runtime performático — Conferir Resultados (M-PERF-CONFERIR-001)."""

from __future__ import annotations

from typing import Any, Mapping

import streamlit as st

from dashboard.institutional_light_mode import CACHE_TTL_SECONDS, CONFERENCE_EVENTS_LIMIT

MISSION_ID = "M-PERF-CONFERIR-001"
OPS_FIX_MISSION_ID = "M-OPS-066-FIX-01"
CONFERENCE_LOTS_PAGE_SIZE = 10
SESSION_CONFERENCE_CACHE = "institutional_conference_perf_cache"
SESSION_CONFERENCE_SELECTED_GE = "conference_selected_generation_event_id"
SESSION_CONFERENCE_PAGE = "conference_lots_page_index"
SESSION_CONFERENCE_RUN_REQUESTED = "conference_run_requested"
NO_LOT_SELECTED_WARNING = (
    "Nenhum lote conferível selecionado. Escolha um lote na lista e clique em "
    "**Conferir lote selecionado**."
)
INVALID_LOT_WARNING = (
    "generation_event_id inválido para conferência. Selecione um lote conferível "
    "oficializado no PostgreSQL."
)


def conference_cache_key(*, generation_event_id: int, contest_number: int) -> str:
    return f"{int(generation_event_id)}:{int(contest_number)}"


def get_conference_result_cache() -> dict[str, Any]:
    cache = st.session_state.get(SESSION_CONFERENCE_CACHE)
    if not isinstance(cache, dict):
        cache = {}
        st.session_state[SESSION_CONFERENCE_CACHE] = cache
    return cache


def read_cached_conference_result(*, generation_event_id: int, contest_number: int) -> dict[str, Any] | None:
    payload = get_conference_result_cache().get(
        conference_cache_key(generation_event_id=generation_event_id, contest_number=contest_number)
    )
    return dict(payload) if isinstance(payload, Mapping) else None


def store_cached_conference_result(
    *,
    generation_event_id: int,
    contest_number: int,
    check_result: Mapping[str, Any],
) -> None:
    cache = get_conference_result_cache()
    cache[conference_cache_key(generation_event_id=generation_event_id, contest_number=contest_number)] = dict(
        check_result
    )
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


def default_conference_generation_event_id(groups: list[dict[str, Any]]) -> int | None:
    """Último lote conferível (maior generation_event_id)."""
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


def ensure_conference_session_defaults(*, default_ge_id: int | None = None) -> None:
    """Inicializa chaves de sessão da conferência — apenas seleção visual temporária."""
    st.session_state.setdefault(SESSION_CONFERENCE_PAGE, 0)
    if SESSION_CONFERENCE_SELECTED_GE not in st.session_state:
        resolved_default = _safe_positive_generation_event_id(default_ge_id)
        if resolved_default is not None:
            st.session_state[SESSION_CONFERENCE_SELECTED_GE] = resolved_default


def read_conference_selected_ge() -> int | None:
    """Lê seleção visual do lote — não é fonte soberana (PostgreSQL permanece Lei 001)."""
    return _safe_positive_generation_event_id(st.session_state.get(SESSION_CONFERENCE_SELECTED_GE))


def sync_conference_selectbox_selection(
    *,
    selectable_ids: list[int],
    default_ge_id: int | None = None,
) -> int | None:
    """Alinha a chave do selectbox antes do widget renderizar (M-OPS-066-FIX-01)."""
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


def is_valid_resolved_generation_event_id(resolved_ge_id: int | None) -> bool:
    return _safe_positive_generation_event_id(resolved_ge_id) is not None


def conference_runtime_trace() -> dict[str, Any]:
    return {
        "mission_id": MISSION_ID,
        "conference_lots_page_size": CONFERENCE_LOTS_PAGE_SIZE,
        "conference_events_limit": CONFERENCE_EVENTS_LIMIT,
        "cache_ttl_seconds": CACHE_TTL_SECONDS,
        "single_lot_default": True,
        "lazy_conference_compute": True,
        "ops_fix_mission_id": OPS_FIX_MISSION_ID,
        "session_selected_ge_key": SESSION_CONFERENCE_SELECTED_GE,
    }
