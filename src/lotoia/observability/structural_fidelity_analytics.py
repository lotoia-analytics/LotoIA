"""M-UI-MODERN-001 — analytics de fidelidade estrutural (observacional)."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Mapping, Sequence

from lotoia.observability.card_structure_diagnostics import _load_official_cards
from lotoia.observability.m_core_003_bias_monitoring import build_m_core_003_bias_monitoring_report
from lotoia.statistics.card_structure import resolve_cartao_final_from_game

MISSION_ID = "M-UI-MODERN-001"
DEFAULT_OFFICIAL_WINDOW = 3000

QUADRANT_RANGES: tuple[tuple[int, int, str], ...] = (
    (1, 6, "Q1 (01–06)"),
    (7, 12, "Q2 (07–12)"),
    (13, 18, "Q3 (13–18)"),
    (19, 25, "Q4 (19–25)"),
)

VOLANTE_GRID: tuple[tuple[int, ...], ...] = (
    (1, 2, 3, 4, 5),
    (6, 7, 8, 9, 10),
    (11, 12, 13, 14, 15),
    (16, 17, 18, 19, 20),
    (21, 22, 23, 24, 25),
)


def extract_cards_from_games(games: Sequence[Mapping[str, Any]]) -> list[list[int]]:
    cards: list[list[int]] = []
    for game in games:
        numbers = resolve_cartao_final_from_game(dict(game))
        if len(numbers) >= 15:
            cards.append([int(value) for value in numbers if 1 <= int(value) <= 25])
    return cards


def dezena_frequency_profile(cards: Sequence[Sequence[int]]) -> dict[int, float]:
    counter: Counter[int] = Counter()
    total = 0
    for card in cards:
        for value in card:
            number = int(value)
            if 1 <= number <= 25:
                counter[number] += 1
                total += 1
    if total <= 0:
        return {number: 0.0 for number in range(1, 26)}
    return {number: round(counter.get(number, 0) / total, 6) for number in range(1, 26)}


def _cosine_similarity(a: Mapping[int, float], b: Mapping[int, float]) -> float:
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for number in range(1, 26):
        av = float(a.get(number, 0.0) or 0.0)
        bv = float(b.get(number, 0.0) or 0.0)
        dot += av * bv
        norm_a += av * av
        norm_b += bv * bv
    if norm_a <= 0.0 or norm_b <= 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


def resolve_fidelity_status(score: float) -> dict[str, str]:
    value = float(score or 0.0)
    if value > 90.0:
        return {"label": "Soberano", "level": "sovereign", "color": "#1b8a5a"}
    if value >= 70.0:
        return {"label": "Alerta de Viés", "level": "warning", "color": "#c9a227"}
    return {"label": "Crítico — Requer Calibração", "level": "critical", "color": "#c0392b"}


def compute_structural_fidelity_score(
    generated_cards: Sequence[Sequence[int]],
    official_cards: Sequence[Sequence[int]],
) -> dict[str, Any]:
    """Proximidade estatística (0–100%) entre LotoIA e histórico oficial."""
    generated_profile = dezena_frequency_profile(generated_cards)
    official_profile = dezena_frequency_profile(official_cards)
    similarity = _cosine_similarity(generated_profile, official_profile)
    score = round(max(0.0, min(100.0, similarity * 100.0)), 2)
    status = resolve_fidelity_status(score)
    return {
        "structural_fidelity_score": score,
        "status_label": status["label"],
        "status_level": status["level"],
        "status_color": status["color"],
        "generated_profile": generated_profile,
        "official_profile": official_profile,
        "official_contests_used": len(official_cards),
    }


def build_quadrant_occupancy(cards: Sequence[Sequence[int]]) -> dict[str, float]:
    counter: Counter[str] = Counter()
    total = 0
    for card in cards:
        for value in card:
            number = int(value)
            if not 1 <= number <= 25:
                continue
            for start, end, label in QUADRANT_RANGES:
                if start <= number <= end:
                    counter[label] += 1
                    total += 1
                    break
    if total <= 0:
        return {label: 0.0 for *_rest, label in QUADRANT_RANGES}
    return {label: round(counter.get(label, 0) / total, 4) for *_rest, label in QUADRANT_RANGES}


def build_volante_heatmap_matrix(profile: Mapping[int, float]) -> list[list[float]]:
    matrix: list[list[float]] = []
    for row in VOLANTE_GRID:
        matrix.append([round(float(profile.get(number, 0.0) or 0.0) * 100.0, 2) for number in row])
    return matrix


def build_actionable_insight_cards(
    *,
    fidelity: Mapping[str, Any],
    bias_report: Mapping[str, Any],
    quadrant_generated: Mapping[str, float],
    quadrant_official: Mapping[str, float],
) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    score = float(fidelity.get("structural_fidelity_score", 0.0) or 0.0)
    if score > 90.0:
        cards.append(
            {
                "icon": "🚀",
                "kind": "insight",
                "title": "Insight",
                "message": (
                    f"Fidelidade estrutural em {score:.1f}% — alinhamento soberano com o "
                    f"histórico oficial ({int(fidelity.get('official_contests_used', 0) or 0)} concursos)."
                ),
            }
        )
    elif score >= 70.0:
        cards.append(
            {
                "icon": "⚠️",
                "kind": "alert",
                "title": "Alerta",
                "message": (
                    f"Fidelidade estrutural em {score:.1f}% — monitorar viés antes da próxima calibração."
                ),
            }
        )
    else:
        cards.append(
            {
                "icon": "⚠️",
                "kind": "alert",
                "title": "Alerta crítico",
                "message": (
                    f"Fidelidade estrutural em {score:.1f}% — recomendada revisão de calibração anti-viés."
                ),
            }
        )

    prefix_rows = list(bias_report.get("prefix_patterns_over_moderate") or [])
    if prefix_rows:
        top = dict(prefix_rows[0])
        cards.append(
            {
                "icon": "🚀",
                "kind": "insight",
                "title": "Insight de prefixo",
                "message": (
                    f"Prefixo {top.get('pattern', '—')} com razão {top.get('ratio', '—')}x "
                    f"vs histórico Lotofácil."
                ),
            }
        )

    repeated = [
        number
        for number, share in (fidelity.get("generated_profile") or {}).items()
        if float(share or 0.0) >= 0.075
    ]
    if repeated:
        cards.append(
            {
                "icon": "⚠️",
                "kind": "alert",
                "title": "Alerta de concentração",
                "message": (
                    f"Detectada concentração elevada nas dezenas "
                    f"{', '.join(f'{int(n):02d}' for n in sorted(repeated)[:4])}. "
                    "Sugerida calibração anti-viés."
                ),
            }
        )

    gaps: list[str] = []
    for label in (item[2] for item in QUADRANT_RANGES):
        official_share = float(quadrant_official.get(label, 0.0) or 0.0)
        generated_share = float(quadrant_generated.get(label, 0.0) or 0.0)
        if official_share > 0.20 and generated_share < official_share * 0.65:
            gaps.append(label)
    if gaps:
        cards.append(
            {
                "icon": "⚠️",
                "kind": "alert",
                "title": "Gap estrutural",
                "message": (
                    f"Quadrantes com cobertura abaixo do oficial: {', '.join(gaps)}."
                ),
            }
        )

    return cards[:4]


def export_structural_diagnosis_for_lotoia_api(bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Normaliza bundle estrutural para consumo da API LotoIA (M-AUTO-CALIB-001)."""
    fidelity = dict(bundle.get("fidelity") or {})
    bias_report = dict(bundle.get("bias_report") or {})
    quadrant_generated = dict(bundle.get("quadrant_generated") or {})
    quadrant_official = dict(bundle.get("quadrant_official") or {})
    score = float(fidelity.get("structural_fidelity_score", 0.0) or 0.0)

    quadrant_gaps: list[dict[str, Any]] = []
    for label in (item[2] for item in QUADRANT_RANGES):
        official_share = float(quadrant_official.get(label, 0.0) or 0.0)
        generated_share = float(quadrant_generated.get(label, 0.0) or 0.0)
        if official_share > 0.20 and generated_share < official_share * 0.65:
            quadrant_gaps.append(
                {
                    "quadrant": label,
                    "official_share": official_share,
                    "generated_share": generated_share,
                    "gap_ratio": round(generated_share / official_share, 4) if official_share else 0.0,
                }
            )

    bias_patterns = [
        {
            "kind": str(row.get("kind") or ""),
            "pattern": str(row.get("pattern") or ""),
            "ratio": float(row.get("ratio") or 0.0),
            "severity": str(row.get("severity") or ""),
        }
        for row in list(bias_report.get("ratio_rows") or [])
    ]
    max_bias_ratio = max((float(row.get("ratio") or 0.0) for row in bias_patterns), default=0.0)

    return {
        "mission_id": MISSION_ID,
        "consumer_mission_id": "M-AUTO-CALIB-001",
        "structural_fidelity_score": score,
        "fidelity_status": resolve_fidelity_status(score),
        "max_bias_ratio": round(max_bias_ratio, 4),
        "quadrant_generated": quadrant_generated,
        "quadrant_official": quadrant_official,
        "quadrant_gaps": quadrant_gaps,
        "bias_patterns": bias_patterns,
        "bias_verdict": str(bias_report.get("verdict") or ""),
        "bias_compliance": bool(bias_report.get("compliance")),
        "official_contests_used": int(fidelity.get("official_contests_used", 0) or 0),
        "correction_commands": [],
    }


def build_structural_intelligence_bundle(
    db_path: Any,
    *,
    games: Sequence[Mapping[str, Any]] | None = None,
    cards: Sequence[Sequence[int]] | None = None,
    official_window: int = DEFAULT_OFFICIAL_WINDOW,
) -> dict[str, Any]:
    """Pacote analítico para o dashboard moderno de Cobertura Estrutural."""
    resolved_cards = [list(card) for card in cards] if cards else extract_cards_from_games(games or [])
    if not resolved_cards:
        return {"available": False, "reason": "no_valid_cards", "mission_id": MISSION_ID}

    from lotoia.database.database import get_session

    with get_session(db_path) as session:
        official_cards, official_contests = _load_official_cards(
            session,
            limit=max(1, int(official_window)),
        )

    fidelity = compute_structural_fidelity_score(resolved_cards, official_cards)
    bias_report = build_m_core_003_bias_monitoring_report(
        resolved_cards,
        games_count=len(resolved_cards),
    )
    quadrant_generated = build_quadrant_occupancy(resolved_cards)
    quadrant_official = build_quadrant_occupancy(official_cards)
    insights = build_actionable_insight_cards(
        fidelity=fidelity,
        bias_report=bias_report,
        quadrant_generated=quadrant_generated,
        quadrant_official=quadrant_official,
    )


    return {
        "available": True,
        "mission_id": MISSION_ID,
        "games_count": len(resolved_cards),
        "official_window": int(official_window),
        "official_contests_used": len(official_contests),
        "fidelity": fidelity,
        "bias_report": bias_report,
        "quadrant_generated": quadrant_generated,
        "quadrant_official": quadrant_official,
        "volante_generated": build_volante_heatmap_matrix(fidelity["generated_profile"]),
        "volante_official": build_volante_heatmap_matrix(fidelity["official_profile"]),
        "insights": insights,
    }


def fidelity_score_from_memory_row(memory_row: Mapping[str, Any]) -> float:
    """Deriva fidelidade a partir da memória M-MEMORY-001 quando score dedicado ausente."""
    snapshot = dict(memory_row.get("coverage_snapshot") or {})
    summary = dict(snapshot.get("bias_report_summary") or {})
    if summary.get("compliance") is True:
        return max(70.0, 100.0 - float(memory_row.get("official_divergence_score", 0.0) or 0.0))
    return max(0.0, 100.0 - float(memory_row.get("official_divergence_score", 0.0) or 0.0))
