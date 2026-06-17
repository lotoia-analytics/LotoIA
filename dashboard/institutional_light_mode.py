"""Modo leve do painel institucional — performance e UI apenas."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import streamlit as st

from dashboard.institutional_build import CORE_REALIGN_V3_BATCH_LABEL

LIGHT_MODE_ENV = "LOTOIA_PANEL_LIGHT_MODE"
CACHE_TTL_SECONDS = 300
DEFAULT_PAGE_SIZE = 25

SESSION_LIGHT_MODE = "panel_light_mode_enabled"
SESSION_LOAD_STRUCTURAL = "panel_light_load_structural_coverage"
SESSION_LOAD_COMPARATIVE = "panel_light_load_comparative"
SESSION_LOAD_HISTORY = "panel_light_load_history"


def light_mode_default_from_env() -> bool:
    raw = os.getenv(LIGHT_MODE_ENV, "1").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def is_light_mode_enabled() -> bool:
    if SESSION_LIGHT_MODE not in st.session_state:
        st.session_state[SESSION_LIGHT_MODE] = light_mode_default_from_env()
    return bool(st.session_state[SESSION_LIGHT_MODE])


def set_light_mode_enabled(value: bool) -> None:
    st.session_state[SESSION_LIGHT_MODE] = bool(value)


def lazy_load_requested(key: str) -> bool:
    return bool(st.session_state.get(key))


def request_lazy_load(key: str) -> None:
    st.session_state[key] = True


def render_lazy_load_gate(
    key: str,
    button_label: str,
    *,
    help_text: str,
) -> bool:
    if lazy_load_requested(key):
        return True
    st.info(help_text)
    if st.button(button_label, type="primary", key=f"lazy_load_btn_{key}"):
        request_lazy_load(key)
        st.rerun()
    return False


def resolve_default_batch_label(batch_options: list[str]) -> str:
    if CORE_REALIGN_V3_BATCH_LABEL in batch_options:
        return CORE_REALIGN_V3_BATCH_LABEL
    return batch_options[0] if batch_options else CORE_REALIGN_V3_BATCH_LABEL


def batch_select_options(*, include_all: bool = False) -> list[str]:
    from lotoia.governance.analysis_batch_labels import BATCH_LABEL_UI_OPTIONS

    options = list(BATCH_LABEL_UI_OPTIONS)
    if is_light_mode_enabled():
        return options
    if include_all:
        return ["(todos)", *options]
    return options


def default_batch_index(options: list[str]) -> int:
    default = resolve_default_batch_label(options)
    return options.index(default) if default in options else 0


def paginate_rows(
    rows: list[Any],
    *,
    page_key: str,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> tuple[list[Any], int, int]:
    total = len(rows)
    if total <= page_size:
        if total:
            st.caption(f"Exibindo {total} registro(s).")
        return rows, 1, 1
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = int(
        st.number_input(
            "Página",
            min_value=1,
            max_value=total_pages,
            value=1,
            step=1,
            key=page_key,
        )
    )
    start = (page - 1) * page_size
    end = min(start + page_size, total)
    st.caption(f"Exibindo {start + 1}–{end} de {total}")
    return rows[start:end], page, total_pages


def render_paginated_dataframe(
    rows: list[Any],
    *,
    page_key: str,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> None:
    page_rows, _, _ = paginate_rows(rows, page_key=page_key, page_size=page_size)
    if page_rows:
        st.dataframe(pd.DataFrame(page_rows), hide_index=True, use_container_width=True)
    else:
        st.caption("Sem dados.")
