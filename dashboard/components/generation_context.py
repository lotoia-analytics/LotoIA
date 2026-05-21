from __future__ import annotations

from typing import Any, Mapping

import streamlit as st


def render_generation_context(
    executive_report: Mapping[str, Any],
    historical_summary: Mapping[str, Any],
    observability_summary: Mapping[str, Any],
) -> None:
    baseline_mode = executive_report.get("baseline_mode", "-")
    status = executive_report.get("status", "-")
    drift = float(executive_report.get("drift", 0.0))
    confidence = executive_report.get("confidence", "-")
    pressure = float(observability_summary.get("counts", {}).get("generation_events", 0))
    trend = historical_summary.get("trend", "-")

    if status == "saudavel" and drift <= 0.20:
        headline = "Baseline permanece consistente nas ultimas janelas."
        note = "Pressao estrutural controlada e leitura executiva favoravel."
    elif status == "observacao":
        headline = "Baseline consistente, mas pedindo observacao moderada."
        note = "Drift recente dentro da faixa esperada, com monitoramento recomendado."
    else:
        headline = "Baseline requer atencao antes de ampliar a geracao."
        note = "Leitura executiva aponta cautela e observacao reforcada."

    st.markdown("### Leitura contextual da geracao")
    st.info(
        f"{headline} "
        f"| Baseline {baseline_mode} "
        f"| confianca {confidence} "
        f"| drift {drift:.2f} "
        f"| tendencia {trend}"
    )
    st.caption(
        f"{note} "
        f"| observability {observability_summary.get('summary', {}).get('stability_note', '-')}"
        f" | eventos monitorados {int(pressure)}"
    )
