"""Bloco operacional da política estrutural 15D na Cobertura Estrutural (M-ML-070-FLOW)."""

from __future__ import annotations

from typing import Any, Mapping

import streamlit as st

from lotoia.ml.structural_policy_15d import (
    MISSION_ID,
    analyze_games_from_context_or_records,
    build_structural_policy_15d_calibration_plan,
    extract_structural_policy_application_from_context,
    is_structural_policy_15d_format,
    load_active_structural_policy_15d_memory,
)

MISSION_FLOW_ID = "M-ML-070-FLOW"


def build_structural_policy_coverage_context(
    db_path: Any,
    payload: Mapping[str, Any],
    generation_event_id: int | None,
    card_format: int | None,
) -> dict[str, Any]:
    size = int(card_format or 0)
    if not is_structural_policy_15d_format(size):
        return {"available": False, "mission_id": MISSION_FLOW_ID}

    memory = load_active_structural_policy_15d_memory(db_path, persist_if_missing=False)
    context_payload = dict(payload or {})
    if generation_event_id:
        context_payload.setdefault("selected_generation_event_id", int(generation_event_id))
        context_payload.setdefault("generation_event_id", int(generation_event_id))
    context_payload.setdefault(
        "generation_event_ids",
        list(context_payload.get("generation_event_ids") or [])
        or ([int(generation_event_id)] if generation_event_id else []),
    )

    application = extract_structural_policy_application_from_context(context_payload)
    analysis: dict[str, Any] = {}
    if not application.get("available"):
        analysis = analyze_games_from_context_or_records(
            None,
            context_payload,
            memory,
            None,
            db_path=db_path,
        )
        application = {
            "available": bool(analysis.get("games_total", 0)),
            "structural_policy_memory_loaded": bool(memory),
            "structural_policy_format": "15D",
            "structural_policy_version": str(
                analysis.get("structural_policy_version") or memory.get("policy_version") or ""
            ),
            "structural_policy_applied": bool(analysis.get("structural_policy_applied")),
            "policy_compliance_status": str(analysis.get("policy_compliance_status") or ""),
            "compliance_label": str(analysis.get("compliance_label") or ""),
            "policy_violations": list(analysis.get("policy_violations") or []),
            "violated_rules": list(analysis.get("violations") or []),
            "games_validated": int(analysis.get("games_validated", 0) or 0),
            "games_compliant": int(analysis.get("games_compliant", 0) or 0),
        }

    calibration_plan = build_structural_policy_15d_calibration_plan(
        analysis or application,
        memory,
    )
    compliance = {
        "compliance_label": str(
            application.get("compliance_label")
            or analysis.get("compliance_label")
            or "—"
        ),
        "policy_compliance_status": str(application.get("policy_compliance_status") or ""),
        "policy_violations": list(
            application.get("policy_violations")
            or application.get("violated_rules")
            or analysis.get("policy_violations")
            or []
        ),
        "games_validated": int(application.get("games_validated", 0) or analysis.get("games_validated", 0) or 0),
        "games_compliant": int(application.get("games_compliant", 0) or analysis.get("games_compliant", 0) or 0),
    }
    return {
        "available": True,
        "mission_id": MISSION_FLOW_ID,
        "policy_mission_id": MISSION_ID,
        "memory": dict(memory or {}),
        "application": application,
        "analysis": dict(analysis or {}),
        "compliance": compliance,
        "calibration_plan": calibration_plan,
        "structural_policy_memory_loaded": bool(memory),
        "structural_policy_version": str(
            application.get("structural_policy_version") or memory.get("policy_version") or ""
        ),
        "structural_policy_applied": bool(application.get("structural_policy_applied")),
        "policy_compliance_status": compliance.get("policy_compliance_status"),
        "policy_violations": list(compliance.get("policy_violations") or []),
    }


def render_structural_policy_15d_operational_block(
    memory: Mapping[str, Any] | None,
    application: Mapping[str, Any] | None,
    compliance: Mapping[str, Any] | None,
) -> None:
    st.markdown(f"##### Política estrutural soberana 15D ({MISSION_ID})")
    memory_loaded = bool((memory or {}).get("policy_version"))
    applied = bool((application or {}).get("structural_policy_applied"))
    policy_cols = st.columns(4)
    policy_cols[0].metric("Política carregada", "SIM" if memory_loaded else "NÃO")
    policy_cols[1].metric("Política aplicada", "SIM" if applied else "NÃO")
    policy_cols[2].metric(
        "Compliance",
        str((compliance or {}).get("compliance_label") or (application or {}).get("compliance_label") or "—"),
    )
    violations = list(
        (compliance or {}).get("policy_violations")
        or (application or {}).get("policy_violations")
        or (application or {}).get("violated_rules")
        or []
    )
    policy_cols[3].metric("Violações", len(violations))

    if memory_loaded:
        st.caption(
            f"Versão: {(memory or {}).get('policy_version', '—')} | "
            f"Origem: {(memory or {}).get('origem_institucional', '—')}"
        )
        rules = list((memory or {}).get("regras_aplicadas") or [])
        if rules:
            st.caption("Regras: " + ", ".join(str(rule) for rule in rules))

    if violations:
        st.warning("Violações detectadas: " + ", ".join(str(item) for item in violations[:8]))
    elif memory_loaded:
        st.success("Nenhuma violação estrutural da política 15D no lote analisado.")

    games_validated = int((compliance or {}).get("games_validated", 0) or 0)
    games_compliant = int((compliance or {}).get("games_compliant", 0) or 0)
    if games_validated > 0:
        st.caption(f"Jogos validados: {games_validated} | Conformes: {games_compliant}")
