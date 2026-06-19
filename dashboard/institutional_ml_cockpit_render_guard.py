"""Proteções de renderização Streamlit — Central ML (M-ML-VIS-071-FIX-01)."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any

import pandas as pd
import streamlit as st

from dashboard.display_dataframe import make_arrow_safe_dataframe

MISSION_ID = "M-ML-VIS-071-FIX-01"
MAX_DATAFRAME_ROWS = 100
MAX_JSON_DEPTH = 8
MAX_JSON_LIST_ITEMS = 64
MAX_JSON_STRING_LEN = 4_000
MAX_JSON_CHARS = 48_000


def _is_primitive(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def sanitize_for_streamlit_json(
    value: Any,
    *,
    max_depth: int = MAX_JSON_DEPTH,
    max_list_items: int = MAX_JSON_LIST_ITEMS,
    max_str_len: int = MAX_JSON_STRING_LEN,
    _depth: int = 0,
    _seen: set[int] | None = None,
) -> Any:
    """Remove recursão, profundidade excessiva e strings gigantes antes de st.json."""
    seen = _seen or set()
    if isinstance(value, (dict, list, tuple)):
        obj_id = id(value)
        if obj_id in seen:
            return "<recursive>"
        seen.add(obj_id)
    if _depth >= max_depth:
        return "<max_depth>"
    if _is_primitive(value):
        if isinstance(value, str) and len(value) > max_str_len:
            return value[:max_str_len] + "…"
        return value
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= max_list_items:
                sanitized["…"] = f"<truncated {len(value) - max_list_items} keys>"
                break
            sanitized[str(key)] = sanitize_for_streamlit_json(
                item,
                max_depth=max_depth,
                max_list_items=max_list_items,
                max_str_len=max_str_len,
                _depth=_depth + 1,
                _seen=seen,
            )
        return sanitized
    if isinstance(value, (list, tuple)):
        items = list(value)[:max_list_items]
        sanitized_list = [
            sanitize_for_streamlit_json(
                item,
                max_depth=max_depth,
                max_list_items=max_list_items,
                max_str_len=max_str_len,
                _depth=_depth + 1,
                _seen=seen,
            )
            for item in items
        ]
        if len(value) > max_list_items:
            sanitized_list.append(f"<truncated {len(value) - max_list_items} items>")
        return sanitized_list
    text = str(value)
    if len(text) > max_str_len:
        return text[:max_str_len] + "…"
    return text


def flatten_record_for_dataframe(record: Mapping[str, Any]) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in dict(record).items():
        if isinstance(value, (dict, list, tuple)):
            encoded = json.dumps(
                sanitize_for_streamlit_json(value, max_depth=4, max_list_items=24),
                ensure_ascii=False,
                default=str,
            )
            flat[str(key)] = encoded[:MAX_JSON_STRING_LEN]
        else:
            flat[str(key)] = value
    return flat


def safe_cockpit_dataframe(
    records: Any,
    *,
    max_rows: int = MAX_DATAFRAME_ROWS,
) -> pd.DataFrame:
    rows = [
        flatten_record_for_dataframe(dict(row))
        for row in list(records or [])[: max(0, int(max_rows))]
    ]
    if not rows:
        return pd.DataFrame()
    return make_arrow_safe_dataframe(pd.DataFrame(rows))


def safe_cockpit_json_display(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    sanitized = sanitize_for_streamlit_json(dict(payload or {}))
    encoded = json.dumps(sanitized, ensure_ascii=False, default=str)
    if len(encoded) > MAX_JSON_CHARS:
        return {
            "truncated": True,
            "preview_chars": MAX_JSON_CHARS,
            "payload_size_chars": len(encoded),
            "preview": encoded[:MAX_JSON_CHARS] + "…",
        }
    return dict(sanitized) if isinstance(sanitized, dict) else {"value": sanitized}


def summarize_coverage_snapshot_for_ui(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Resumo seguro — nunca expõe payload estrutural bruto gigante no expander."""
    structural = dict(payload or {})
    summary = dict(structural.get("summary") or {})
    evidence_base = dict(structural.get("evidence_base") or {})
    redundancia = dict(structural.get("redundancia_gp") or {})
    return sanitize_for_streamlit_json(
        {
            "available": structural.get("available"),
            "source": structural.get("source"),
            "summary": summary,
            "evidence_base": evidence_base,
            "evidence_level": structural.get("evidence_level"),
            "excluded_batches_count": structural.get("excluded_batches_count"),
            "formatos_analisados": list(summary.get("formatos_analisados") or evidence_base.get("formatos_analisados") or []),
            "generation_event_ids": list(evidence_base.get("generation_event_ids") or [])[:24],
            "redundancia_gp_keys": sorted(str(key) for key in redundancia.keys()),
        },
        max_depth=6,
    )


def detect_mixed_format_aggregate(snapshot: Mapping[str, Any] | None) -> bool:
    payload = dict(snapshot or {})
    if not payload.get("aggregate_mode"):
        return False
    metrics = dict((payload.get("coverage_evidence") or {}).get("metrics") or {})
    formats = [int(value) for value in list(metrics.get("formatos_analisados") or []) if int(value) > 0]
    return len(set(formats)) > 1


def render_cockpit_block_safe(block_name: str, render_fn: Callable[[], None]) -> bool:
    try:
        render_fn()
        return True
    except Exception as exc:  # noqa: BLE001 — proteção de UI Streamlit
        st.warning(
            f"Bloco `{block_name}` indisponível — renderização protegida ({MISSION_ID})."
        )
        st.caption(str(exc)[:280])
        return False


def display_cockpit_json(label: str, payload: Mapping[str, Any] | None) -> None:
    st.caption(label)
    st.json(safe_cockpit_json_display(payload))


def display_cockpit_dataframe(records: Any, *, max_rows: int = MAX_DATAFRAME_ROWS) -> None:
    dataframe = safe_cockpit_dataframe(records, max_rows=max_rows)
    if dataframe.empty:
        st.caption("Sem linhas para exibir.")
        return
    st.dataframe(dataframe, hide_index=True, use_container_width=True)
