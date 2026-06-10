from __future__ import annotations

import pandas as pd

from dashboard.display_dataframe import (
    make_arrow_safe_dataframe,
    normalize_display_dataframe,
    strip_adm_technical_columns,
    strip_adm_technical_records,
)


def test_normalize_display_dataframe_casts_valor_column_to_string() -> None:
    dataframe = pd.DataFrame(
        [
            {"Métrica": "Média de sobreposição", "Valor": 11.2449},
            {"Métrica": "Dezenas dominantes", "Valor": "20(27x) 25(27x) 01(26x)"},
            {"Métrica": "Concursos analisados", "Valor": 1},
            {"Métrica": "Status", "Valor": "reconciled"},
        ]
    )
    normalized = normalize_display_dataframe(dataframe)
    assert str(normalized["Valor"].dtype) == "string"
    assert normalized["Valor"].tolist() == ["11.2449", "20(27x) 25(27x) 01(26x)", "1", "reconciled"]
    assert str(normalized["Métrica"].dtype) == "string"


def test_normalize_display_dataframe_preserves_numeric_columns() -> None:
    dataframe = pd.DataFrame(
        [
            {
                "Métrica": "hits",
                "Valor": "11",
                "hits": 11,
                "frequencia": 27,
                "generation_event_id": 42,
                "reconciliation_run_id": 788,
            }
        ]
    )
    normalized = normalize_display_dataframe(dataframe)
    assert str(normalized["Valor"].dtype) == "string"
    assert int(normalized.loc[0, "hits"]) == 11
    assert int(normalized.loc[0, "frequencia"]) == 27
    assert int(normalized.loc[0, "generation_event_id"]) == 42
    assert int(normalized.loc[0, "reconciliation_run_id"]) == 788


def test_make_arrow_safe_dataframe_handles_mixed_object_columns() -> None:
    dataframe = pd.DataFrame(
        [
            {"Campo": "Maior acerto", "Valor": 10},
            {"Campo": "Status", "Valor": "reconciled"},
            {"Campo": "Dezenas dominantes", "Valor": "03(48x) 24(46x)"},
        ]
    )
    safe = make_arrow_safe_dataframe(dataframe)
    assert str(safe["Valor"].dtype) == "string"
    assert str(safe["Campo"].dtype) == "string"


def test_make_arrow_safe_dataframe_keeps_hit_distribution_numeric_column() -> None:
    dataframe = pd.DataFrame(
        [
            {"Faixa de acertos": "10", "Quantidade de jogos": 5},
            {"Faixa de acertos": "11", "Quantidade de jogos": 45},
        ]
    )
    safe = make_arrow_safe_dataframe(dataframe)
    assert str(safe["Faixa de acertos"].dtype) == "string"
    assert int(safe.loc[0, "Quantidade de jogos"]) == 5
    assert int(safe.loc[1, "Quantidade de jogos"]) == 45


def test_strip_adm_technical_columns_removes_hidden_fields() -> None:
    dataframe = pd.DataFrame(
        [
            {
                "geração": "Geração 42",
                "generation_event_id": 42,
                "reconciliation_run_id": 7,
                "sample_size": 20,
                "leftover_basis": "real",
                "ml_role": "diagnostic",
                "origem_observacional": "cartao_final",
                "hits": 11,
            }
        ]
    )
    stripped = strip_adm_technical_columns(dataframe)
    assert "geração" in stripped.columns
    assert "hits" in stripped.columns
    assert "generation_event_id" not in stripped.columns
    assert "reconciliation_run_id" not in stripped.columns
    assert "sample_size" not in stripped.columns


def test_make_arrow_safe_dataframe_strips_adm_technical_columns() -> None:
    dataframe = pd.DataFrame([{"Campo": "acertos", "Valor": 11, "generation_event_id": 99}])
    safe = make_arrow_safe_dataframe(dataframe)
    assert "generation_event_id" not in safe.columns
    assert "Campo" in safe.columns


def test_strip_adm_technical_records_removes_hidden_keys() -> None:
    records = [
        {
            "dezena": "03",
            "generation_event_id": 10,
            "ml_role": "diagnostic",
            "hits": 12,
        }
    ]
    cleaned = strip_adm_technical_records(records)
    assert cleaned == [{"dezena": "03", "hits": 12}]
