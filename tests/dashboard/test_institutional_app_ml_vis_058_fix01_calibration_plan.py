from __future__ import annotations

import inspect
from copy import deepcopy

import pytest

import dashboard.institutional_ml_calibration_cockpit as cockpit
from dashboard.institutional_build import BUILD_MARKER
from dashboard.institutional_supervised_ml import (
    build_cockpit_persist_bundle,
    resolve_authorized_calibration_plan,
)
from lotoia.ml.supervised_output_calibration import apply_supervised_output_calibration
from lotoia.observability.coverage_evidence_interpreter import (
    FIX01_MISSION_ID,
    build_calibration_plan,
    interpret_coverage_evidence,
)


def _rich_metrics() -> dict[str, object]:
    return {
        "similaridade_media": 0.72,
        "sobreposicao_maxima": 14,
        "quase_repetidos": 30,
        "diversity_score": 0.0,
        "dezenas_subcobertas": 3,
        "dezenas_subcobertas_list": ["07", "11", "23"],
        "prefixos_sufixos_viciados": True,
        "prefixo_viciado": True,
        "sufixo_viciado": True,
        "prefixo_mais_gerado": "01-02-03",
        "sufixo_mais_gerado": "23-24-25",
        "total_jogos": 50,
        "desempenho_13_hits": 0,
        "desempenho_14_hits": 0,
    }


def test_build_marker_v40() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v46"


def test_build_calibration_plan_lists_specific_actions() -> None:
    plan = build_calibration_plan(_rich_metrics())
    joined = " ".join(plan["plan_items"]).lower()
    assert plan["mission_id"] == FIX01_MISSION_ID
    assert "similaridade" in joined
    assert "sobreposição máxima" in joined or "sobreposicao maxima" in joined.replace("ç", "c")
    assert "quase repetidos" in joined or "clones" in joined
    assert "01-02-03" in joined
    assert "23-24-25" in joined
    assert "07" in joined and "23" in joined
    assert "diversidade" in joined
    assert any("reranquear" in item.lower() for item in plan["plan_items"])
    assert len(plan["impact_items"]) >= 3


def test_interpret_coverage_evidence_exposes_calibration_plan() -> None:
    result = interpret_coverage_evidence(_rich_metrics(), calibration_applied=False)
    assert result["fix_mission_id"] == FIX01_MISSION_ID
    assert result["calibration_plan"]["has_plan"] is True
    assert result["plan_items"]
    assert result["impacto_detalhado"]
    assert result["parametros_sugeridos"]


def test_similaridade_generates_penalty_action() -> None:
    plan = build_calibration_plan({"similaridade_media": 0.62, "diversity_score": 0.5, "sobreposicao_maxima": 10})
    assert any("similaridade" in item.lower() for item in plan["plan_items"])


def test_sobreposicao_maxima_generates_overlap_action() -> None:
    plan = build_calibration_plan({"sobreposicao_maxima": 14, "similaridade_media": 0.4, "diversity_score": 0.6})
    assert any("sobreposição" in item.lower() or "overlap" in item.lower() for item in plan["plan_items"])


def test_quase_repetidos_generates_clone_action() -> None:
    plan = build_calibration_plan({"quase_repetidos": 25, "similaridade_media": 0.5, "diversity_score": 0.5})
    assert any("quase repetidos" in item.lower() or "clones" in item.lower() for item in plan["plan_items"])


def test_prefix_suffix_viciados_in_plan() -> None:
    plan = build_calibration_plan(
        {
            "prefixo_viciado": True,
            "sufixo_viciado": True,
            "prefixo_mais_gerado": "01-02-03",
            "sufixo_mais_gerado": "23-24-25",
            "similaridade_media": 0.3,
            "diversity_score": 0.7,
        }
    )
    joined = " ".join(plan["plan_items"])
    assert "01-02-03" in joined
    assert "23-24-25" in joined


def test_dezenas_subcobertas_listed_in_plan() -> None:
    plan = build_calibration_plan(
        {
            "dezenas_subcobertas": 2,
            "dezenas_subcobertas_list": ["07", "15"],
            "similaridade_media": 0.3,
            "diversity_score": 0.7,
        }
    )
    joined = " ".join(plan["plan_items"])
    assert "07" in joined
    assert "15" in joined


def test_persist_bundle_stores_full_calibration_plan() -> None:
    metrics = _rich_metrics()
    plan = build_calibration_plan(metrics)
    bundle = build_cockpit_persist_bundle(
        workflow_status="autorizada",
        decision_at="2026-06-17T12:00:00+00:00",
        apply_next_generation=True,
        recommendations=list(plan["plan_items"]),
        coverage_evidence={
            "available": True,
            "problemas_detectados": ["Diversidade baixa."],
            "evidencias": ["Score diversidade 0.0"],
            "calibration_plan": plan,
            "plan_items": plan["plan_items"],
            "impacto_detalhado": plan["impact_items"],
            "parametros_sugeridos": plan["parametros_sugeridos"],
        },
        calibration_plan=plan,
        impacto_detalhado=list(plan["impact_items"]),
        parametros_sugeridos=dict(plan["parametros_sugeridos"]),
        operator_decision="autorizar",
    )
    assert bundle["coverage_fix_mission_id"] == FIX01_MISSION_ID
    assert bundle["calibration_authorized"] is True
    assert bundle["plan_items"]
    assert bundle["calibration_plan"]["plan_items"]
    assert bundle["impacto_detalhado"]
    assert bundle["parametros_sugeridos"]
    assert bundle["operador"]
    assert bundle["trace"]["fix_mission_id"] == FIX01_MISSION_ID
    assert bundle["evidencias"] or bundle["problemas_detectados"]


def test_resolve_authorized_calibration_plan() -> None:
    plan = build_calibration_plan(_rich_metrics())
    bundle = build_cockpit_persist_bundle(
        workflow_status="autorizada",
        decision_at="2026-06-17T12:00:00+00:00",
        apply_next_generation=True,
        recommendations=list(plan["plan_items"]),
        calibration_plan=plan,
        operator_decision="aplicar_proxima_geracao",
    )
    resolved = resolve_authorized_calibration_plan(bundle)
    assert resolved is not None
    assert resolved["authorized"] is True
    assert resolved["plan_items"]
    assert resolved["parametros_sugeridos"]
    assert resolved["trace"]

    bundle_pending = dict(bundle)
    bundle_pending["cockpit_apply_next_generation"] = False
    assert resolve_authorized_calibration_plan(bundle_pending) is None


def test_apply_calibration_uses_authorized_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOTOIA_ML_OUTPUT_CALIBRATION_ENABLED", "1")
    base = sorted(list(range(1, 16)))
    games = [{"numbers": list(base), "profile_score": 20.0, "score_ml": 40.0} for _ in range(10)]
    for index, row in enumerate(games):
        nums = list(base)
        if index:
            nums[index % 14] = ((nums[index % 14] + index) % 25) + 1
            row["numbers"] = sorted(set(nums))[:15]
    plan = build_calibration_plan(_rich_metrics())
    authorized = {
        **plan,
        "authorized": True,
        "trace": {"mission_id": FIX01_MISSION_ID},
        "operador": "tester",
        "timestamp": "2026-06-17T12:00:00+00:00",
    }
    _, bundle = apply_supervised_output_calibration(
        deepcopy(games),
        game_size=15,
        ml_enabled=True,
        calibration_plan=authorized,
    )
    assert bundle["calibration_applied"] is True
    assert bundle.get("authorized_calibration_plan")
    assert bundle["authorized_calibration_plan"]["plan_items"]


def test_cockpit_ui_shows_calibration_plan_section() -> None:
    source = inspect.getsource(cockpit)
    assert "Plano de calibração recomendado" in source
    assert "Impacto esperado" in source
