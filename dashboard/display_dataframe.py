"""Normalização de DataFrames para exibição estável no Streamlit/Arrow."""

from __future__ import annotations

from typing import Any

import pandas as pd

DISPLAY_TEXT_COLUMNS = frozenset(
    {
        "Valor",
        "valor",
        "Chave",
        "chave",
        "Métrica",
        "Metrica",
        "métrica",
        "metrica",
        "Status",
        "status",
        "Campo",
        "campo",
        "Detalhe",
        "detalhe",
        "Faixa de acertos",
    }
)

PRESERVE_NUMERIC_COLUMNS = frozenset(
    {
        "frequencia",
        "frequência",
        "frequency",
        "percentual",
        "hits",
        "sample_size",
        "concurso",
        "contest_id",
        "generation_event_id",
        "reconciliation_run_id",
        "Quantidade de jogos",
        "Quantidade",
        "count",
        "number",
        "game_index",
        "total_hits",
        "best_hits",
        "prize_count",
    }
)


def _stringify_display_value(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value)


def normalize_display_dataframe(df: pd.DataFrame | None) -> pd.DataFrame:
    """Colunas textuais de exibição em dtype string; numéricas oficiais preservadas."""
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df.copy()

    normalized = df.copy()
    for column in normalized.columns:
        column_name = str(column)
        if column_name in PRESERVE_NUMERIC_COLUMNS:
            continue
        if column_name in DISPLAY_TEXT_COLUMNS:
            normalized[column] = normalized[column].map(_stringify_display_value).astype("string")
    return normalized


def make_arrow_safe_dataframe(df: pd.DataFrame | None) -> pd.DataFrame:
    """Prepara DataFrame para st.dataframe sem warnings de tipos mistos no Arrow."""
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df.copy()

    safe_df = normalize_display_dataframe(df)
    for column in safe_df.columns:
        column_name = str(column)
        if column_name in PRESERVE_NUMERIC_COLUMNS:
            continue
        series = safe_df[column]
        dtype_name = str(series.dtype)
        if dtype_name == "object" or dtype_name.startswith("string"):
            if column_name not in DISPLAY_TEXT_COLUMNS:
                safe_df[column] = series.map(_stringify_display_value).astype("string")
    return safe_df
