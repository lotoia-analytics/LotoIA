from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

DEFAULT_LONGITUDINAL_REPORT = Path("reports") / "longitudinal" / "baseline_hard_longitudinal.json"
DEFAULT_EXECUTIVE_ANALYTICS_REPORT = Path("reports") / "analytics" / "executive_analytical_report.json"


@dataclass(frozen=True)
class AnalyticalInsight:
    metric: str
    value: float
    interpretation: str
    confidence: str


@dataclass(frozen=True)
class ComparativeAnalyticalInsight:
    label: str
    baseline: float
    compared: float
    delta: float
    interpretation: str


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _confidence_label(value: float) -> str:
    if value >= 0.80:
        return "alta"
    if value >= 0.55:
        return "moderada"
    return "baixa"


def _stability_interpretation(stability: float) -> str:
    if stability >= 0.85:
        return "baseline estável com drift controlado"
    if stability >= 0.65:
        return "baseline consistente, mas com atenção moderada"
    return "baseline com instabilidade relevante"


def _coverage_interpretation(coverage_10: float, coverage_11: float) -> str:
    if coverage_11 >= 0.50:
        return "cobertura alta em faixas superiores"
    if coverage_10 >= 0.50:
        return "cobertura funcional em faixa intermediária"
    return "cobertura conservadora e sem tração de cauda"


def _pressure_interpretation(normalization_pressure: float) -> str:
    if normalization_pressure >= 0.45:
        return "pressão estrutural elevada"
    if normalization_pressure >= 0.25:
        return "pressão estrutural controlada"
    return "pressão estrutural permissiva"


def _drift_interpretation(drift: float) -> str:
    if drift <= 0.20:
        return "drift longitudinal controlado"
    if drift <= 0.35:
        return "drift moderado, mas observável"
    return "drift elevado e requer governança"


def interpret_structural_health(metrics: Mapping[str, Any]) -> list[AnalyticalInsight]:
    stability = _safe_float(metrics.get("stability_index", metrics.get("stability", 0.0)))
    coverage_10 = _safe_float(metrics.get("coverage_10", 0.0))
    coverage_11 = _safe_float(metrics.get("coverage_11", 0.0))
    avg_hits = _safe_float(metrics.get("average_hits", 0.0))
    hits_sd = _safe_float(metrics.get("hits_standard_deviation", metrics.get("standard_deviation", 0.0)))
    drift = _safe_float(metrics.get("drift", metrics.get("behavior_drift", 0.0)))
    normalization_pressure = _safe_float(metrics.get("normalization_pressure", 0.0))
    recurrence_density = _safe_float(metrics.get("recurrence_density", 0.0))

    return [
        AnalyticalInsight(
            metric="stability",
            value=round(stability, 4),
            interpretation=_stability_interpretation(stability),
            confidence=_confidence_label(stability),
        ),
        AnalyticalInsight(
            metric="coverage",
            value=round((coverage_10 + coverage_11) / 2, 4),
            interpretation=_coverage_interpretation(coverage_10, coverage_11),
            confidence=_confidence_label(max(coverage_10, coverage_11)),
        ),
        AnalyticalInsight(
            metric="average_hits",
            value=round(avg_hits, 4),
            interpretation="faixa média de acertos consistente com baseline validado" if avg_hits >= 9 else "faixa média abaixo da referência institucional",
            confidence=_confidence_label(min(1.0, avg_hits / 10 if avg_hits else 0.0)),
        ),
        AnalyticalInsight(
            metric="drift",
            value=round(drift, 4),
            interpretation=_drift_interpretation(drift),
            confidence=_confidence_label(1.0 - min(drift, 1.0)),
        ),
        AnalyticalInsight(
            metric="normalization_pressure",
            value=round(normalization_pressure, 4),
            interpretation=_pressure_interpretation(normalization_pressure),
            confidence=_confidence_label(1.0 - min(normalization_pressure, 1.0)),
        ),
        AnalyticalInsight(
            metric="recurrence_density",
            value=round(recurrence_density, 4),
            interpretation="recorrência estrutural presente e operacionalmente útil" if recurrence_density >= 0.9 else "recorrência moderada e sob observação",
            confidence=_confidence_label(recurrence_density),
        ),
        AnalyticalInsight(
            metric="hits_standard_deviation",
            value=round(hits_sd, 4),
            interpretation="dispersão de acertos controlada" if hits_sd <= 1.5 else "dispersão de acertos ampliada",
            confidence=_confidence_label(1.0 - min(hits_sd / 3.0, 1.0)),
        ),
    ]


def interpret_longitudinal_report(report: Mapping[str, Any]) -> list[AnalyticalInsight]:
    summary = report.get("summary", {}) if isinstance(report, Mapping) else {}
    if not isinstance(summary, Mapping):
        summary = {}
    metrics = {
        "stability_index": summary.get("stability_index", 0.0),
        "coverage_10": summary.get("coverage_10", 0.0),
        "coverage_11": summary.get("coverage_11", 0.0),
        "average_hits": summary.get("average_hits", 0.0),
        "hits_standard_deviation": summary.get("hits_standard_deviation", 0.0),
    }
    insights = interpret_structural_health(metrics)
    insights.append(
        AnalyticalInsight(
            metric="longitudinal_profile",
            value=round(_safe_float(summary.get("stability_index", 0.0)), 4),
            interpretation="baseline longitudinal validado sem colapso agressivo" if _safe_float(summary.get("stability_index", 0.0)) >= 0.8 else "baseline longitudinal requer observação adicional",
            confidence=_confidence_label(_safe_float(summary.get("stability_index", 0.0))),
        )
    )
    return insights


def compare_longitudinal_checkpoints(report: Mapping[str, Any]) -> list[ComparativeAnalyticalInsight]:
    runs = report.get("runs", []) if isinstance(report, Mapping) else []
    if not isinstance(runs, list) or len(runs) < 2:
        return []
    first = runs[0].get("result", {}) if isinstance(runs[0], Mapping) else {}
    last = runs[-1].get("result", {}) if isinstance(runs[-1], Mapping) else {}
    comparisons = []
    keys = [
        ("average_hits", "average_hits"),
        ("standard_deviation", "stability_window_sd"),
        ("final_score_hit_correlation", "final_score_hit_correlation"),
    ]
    labels = {
        "average_hits": "média de acertos",
        "standard_deviation": "dispersão dos hits",
        "final_score_hit_correlation": "correlação score/hits",
    }
    for key, nested_key in keys:
        baseline = _safe_float(first.get("lotoia", {}).get(key, 0.0)) if isinstance(first, Mapping) else 0.0
        compared = _safe_float(last.get("lotoia", {}).get(key, 0.0)) if isinstance(last, Mapping) else 0.0
        if key == "standard_deviation":
            compared = _safe_float(last.get("lotoia", {}).get("standard_deviation", 0.0))
        delta = compared - baseline
        if key == "average_hits":
            interpretation = "crescimento longitudinal" if delta > 0 else "baseline longitudinal preservado sem ganho relevante"
        elif key == "standard_deviation":
            interpretation = "maior dispersão longitudinal" if delta > 0 else "dispersão longitudinal controlada"
        else:
            interpretation = "correlação estável" if abs(delta) < 0.05 else "correlação com mudança observável"
        comparisons.append(
            ComparativeAnalyticalInsight(
                label=labels[key],
                baseline=round(baseline, 4),
                compared=round(compared, 4),
                delta=round(delta, 4),
                interpretation=interpretation,
            )
        )
    return comparisons


def build_analytical_intelligence(
    longitudinal_report_path: Path = DEFAULT_LONGITUDINAL_REPORT,
) -> dict[str, Any]:
    longitudinal_report: dict[str, Any] = {}
    if longitudinal_report_path.exists():
        longitudinal_report = json.loads(longitudinal_report_path.read_text(encoding="utf-8"))
    insights = [insight.__dict__ for insight in interpret_longitudinal_report(longitudinal_report)]
    comparisons = [comparison.__dict__ for comparison in compare_longitudinal_checkpoints(longitudinal_report)]
    summary = longitudinal_report.get("summary", {}) if isinstance(longitudinal_report, Mapping) else {}
    if not isinstance(summary, Mapping):
        summary = {}
    structural_health = _safe_float(summary.get("stability_index", 0.0))
    confidence = _confidence_label(structural_health)
    return {
        "source": str(longitudinal_report_path),
        "generated_at": longitudinal_report.get("created_at", ""),
        "baseline_mode": longitudinal_report.get("baseline_mode", "hard"),
        "analytical_summary": {
            "structural_health": round(structural_health, 4),
            "confidence": confidence,
            "interpretation": _stability_interpretation(structural_health),
            "coverage_10": round(_safe_float(summary.get("coverage_10", 0.0)), 4),
            "coverage_11": round(_safe_float(summary.get("coverage_11", 0.0)), 4),
            "average_hits": round(_safe_float(summary.get("average_hits", 0.0)), 4),
            "drift": round(_safe_float(summary.get("drift", 0.0)), 4),
            "runtime_profile": summary.get("runtime_profile", "incremental_longitudinal"),
        },
        "insights": insights,
        "comparisons": comparisons,
    }


def build_executive_analytical_report(
    longitudinal_report_path: Path = DEFAULT_LONGITUDINAL_REPORT,
) -> dict[str, Any]:
    report = build_analytical_intelligence(longitudinal_report_path)
    summary = report.get("analytical_summary", {})
    insights = report.get("insights", [])
    comparisons = report.get("comparisons", [])

    structural_health = _safe_float(summary.get("structural_health", 0.0))
    drift = _safe_float(summary.get("drift", 0.0))
    coverage_11 = _safe_float(summary.get("coverage_11", 0.0))
    confidence = str(summary.get("confidence", "baixa"))

    if structural_health >= 0.80 and drift <= 0.20:
        status = "saudavel"
        recommendation = "manter baseline hard e monitorar longitudinalmente"
    elif structural_health >= 0.65:
        status = "observacao"
        recommendation = "manter baseline hard com observacao reforcada"
    else:
        status = "atencao"
        recommendation = "revisar baseline antes de qualquer ampliacao experimental"

    headline = "baseline longitudinal consistente" if structural_health >= 0.80 else "baseline longitudinal requer atenção"
    if coverage_11 >= 0.50:
        headline = "baseline com cobertura alta em faixas superiores"

    key_takeaways = []
    for insight in insights[:4]:
        if isinstance(insight, Mapping):
            key_takeaways.append(
                {
                    "metric": insight.get("metric", ""),
                    "interpretation": insight.get("interpretation", ""),
                    "confidence": insight.get("confidence", ""),
                }
            )

    return {
        "status": status,
        "headline": headline,
        "recommendation": recommendation,
        "confidence": confidence,
        "structural_health": round(structural_health, 4),
        "drift": round(drift, 4),
        "coverage_11": round(coverage_11, 4),
        "baseline_mode": report.get("baseline_mode", "hard"),
        "source": report.get("source", ""),
        "generated_at": report.get("generated_at", ""),
        "key_takeaways": key_takeaways,
        "comparisons": comparisons,
    }


def persist_executive_analytical_report(
    report_path: Path = DEFAULT_EXECUTIVE_ANALYTICS_REPORT,
    *,
    longitudinal_report_path: Path = DEFAULT_LONGITUDINAL_REPORT,
) -> dict[str, Any]:
    report = build_executive_analytical_report(longitudinal_report_path)
    payload = {
        "source": str(longitudinal_report_path),
        "generated_at": report.get("generated_at", ""),
        "report": report,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
