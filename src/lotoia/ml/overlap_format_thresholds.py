"""Memória ML de limiares de sobreposição por formato — M-ML-060."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

MISSION_ID = "M-ML-060"
MIN_FORMAT_SIZE = 15
MAX_FORMAT_SIZE = 23
SUPPORTED_FORMAT_SIZES: tuple[int, ...] = tuple(range(MIN_FORMAT_SIZE, MAX_FORMAT_SIZE + 1))

SIMILARITY_HIGH_THRESHOLD = 0.55
NEAR_DUP_HIGH_THRESHOLD = 20
DIVERSITY_LOW_THRESHOLD = 0.55

LEVEL_BOM = "bom"
LEVEL_ATENCAO = "atencao"
LEVEL_RUIM = "ruim"
LEVEL_CRITICO = "critico"

LEVEL_LABELS: dict[str, str] = {
    LEVEL_BOM: "bom",
    LEVEL_ATENCAO: "atenção",
    LEVEL_RUIM: "ruim / quase clone",
    LEVEL_CRITICO: "clone total / crítico",
}


def build_format_overlap_threshold(game_size: int) -> dict[str, Any]:
    """Limiar de sobreposição máxima para formato N (regra geral M-ML-060)."""
    size = int(game_size)
    if size < MIN_FORMAT_SIZE or size > MAX_FORMAT_SIZE:
        raise ValueError(f"Formato {size}D fora do intervalo suportado {MIN_FORMAT_SIZE}D–{MAX_FORMAT_SIZE}D.")
    bom_max = size - 3
    return {
        "formato": f"{size}D",
        "game_size": size,
        "bom_max": bom_max,
        "atencao": size - 2,
        "ruim": size - 1,
        "critico": size,
        "faixa_ideal": (
            f"até {bom_max} bom; {size - 2} atenção; {size - 1} ruim; {size} crítico"
        ),
    }


def build_overlap_format_memory() -> dict[str, Any]:
    """Registro institucional de limiares 15D–23D."""
    thresholds = [build_format_overlap_threshold(size) for size in SUPPORTED_FORMAT_SIZES]
    return {
        "mission_id": MISSION_ID,
        "supported_formats": [f"{size}D" for size in SUPPORTED_FORMAT_SIZES],
        "thresholds": thresholds,
        "rule_summary": (
            "Para formato N: N=crítico; N-1=ruim/quase clone; N-2=atenção; até N-3=bom "
            "(desde que similaridade média e quase repetidos não estejam altos)."
        ),
    }


def classify_overlap_for_format(overlap_max: int, game_size: int) -> dict[str, Any]:
    """Classifica sobreposição máxima observada para o formato N."""
    threshold = build_format_overlap_threshold(game_size)
    overlap = int(overlap_max)
    size = int(game_size)
    if overlap >= size:
        level = LEVEL_CRITICO
        verdict = f"CRÍTICO — clone/idêntico detectado no formato {size}D."
    elif overlap >= threshold["ruim"]:
        level = LEVEL_RUIM
        verdict = f"RUIM — quase clone no formato {size}D (sobreposição {overlap})."
    elif overlap >= threshold["atencao"]:
        level = LEVEL_ATENCAO
        verdict = f"ATENÇÃO — sobreposição elevada para {size}D (overlap {overlap})."
    else:
        level = LEVEL_BOM
        verdict = f"BOM — sobreposição dentro da faixa ideal para {size}D."
    return {
        "formato": f"{size}D",
        "game_size": size,
        "sobreposicao_maxima": overlap,
        "level": level,
        "level_label": LEVEL_LABELS[level],
        "verdict": verdict,
        "threshold": threshold,
        "faixa_ideal": threshold["faixa_ideal"],
    }


def _cross_check_redundancy_context(
    metrics: Mapping[str, Any],
    *,
    base_level: str,
) -> tuple[str, str]:
    """Cruza overlap com similaridade, quase repetidos e diversidade."""
    similaridade = float(metrics.get("similaridade_media", 0.0) or 0.0)
    quase_repetidos = int(metrics.get("quase_repetidos", 0) or 0)
    diversity_score = float(metrics.get("diversity_score", 1.0) or 1.0)
    notes: list[str] = []
    level = base_level
    if base_level == LEVEL_BOM:
        if similaridade >= SIMILARITY_HIGH_THRESHOLD:
            level = LEVEL_ATENCAO
            notes.append(f"similaridade média alta ({similaridade:.4f})")
        if quase_repetidos >= NEAR_DUP_HIGH_THRESHOLD:
            level = LEVEL_RUIM if level != LEVEL_CRITICO else level
            notes.append(f"quase repetidos elevados ({quase_repetidos})")
        if diversity_score < DIVERSITY_LOW_THRESHOLD:
            level = LEVEL_ATENCAO if level == LEVEL_BOM else level
            notes.append(f"diversidade baixa ({diversity_score:.4f})")
    elif base_level in {LEVEL_ATENCAO, LEVEL_RUIM}:
        if similaridade >= SIMILARITY_HIGH_THRESHOLD or quase_repetidos >= NEAR_DUP_HIGH_THRESHOLD:
            notes.append("similaridade/quase repetidos reforçam alerta estrutural")
    note = "; ".join(notes)
    return level, note


def evaluate_format_overlap_verdict(
    game_size: int,
    overlap_max: int,
    metrics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Veredito operacional por formato com cruzamento de métricas estruturais."""
    base = classify_overlap_for_format(overlap_max, game_size)
    metrics_map = dict(metrics or {})
    adjusted_level, cross_note = _cross_check_redundancy_context(
        metrics_map,
        base_level=str(base["level"]),
    )
    verdict = str(base["verdict"])
    if adjusted_level != base["level"]:
        size = int(game_size)
        if adjusted_level == LEVEL_CRITICO:
            verdict = f"CRÍTICO — clone/idêntico detectado no formato {size}D."
        elif adjusted_level == LEVEL_RUIM:
            verdict = f"RUIM — redundância estrutural elevada no formato {size}D."
        elif adjusted_level == LEVEL_ATENCAO:
            verdict = f"ATENÇÃO — overlap aceitável, mas métricas agregadas exigem calibração ({size}D)."
    recommended_action = ""
    if adjusted_level in {LEVEL_CRITICO, LEVEL_RUIM}:
        recommended_action = (
            f"Penalizar overlap extremo no formato {int(game_size)}D, eliminar clones estruturais "
            "e reranquear antes de liberar geração oficial."
        )
    elif adjusted_level == LEVEL_ATENCAO:
        recommended_action = (
            f"Monitorar overlap no formato {int(game_size)}D e reforçar diversidade se "
            "similaridade/quase repetidos permanecerem altos."
        )
    return {
        **base,
        "level": adjusted_level,
        "level_label": LEVEL_LABELS.get(adjusted_level, adjusted_level),
        "verdict": verdict,
        "cross_check_note": cross_note,
        "recommended_action": recommended_action,
        "similaridade_media": float(metrics_map.get("similaridade_media", 0.0) or 0.0),
        "quase_repetidos": int(metrics_map.get("quase_repetidos", 0) or 0),
        "diversity_score": float(metrics_map.get("diversity_score", 0.0) or 0.0),
    }


def build_per_format_overlap_analysis(
    payload: Mapping[str, Any],
    metrics: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Análise de overlap por formato a partir do payload da Cobertura Estrutural."""
    metrics_map = dict(metrics or {})
    per_format = dict(payload.get("redundancia_por_formato") or {})
    formats = sorted(int(value) for value in per_format.keys())
    if not formats:
        summary_formats = list((payload.get("summary") or {}).get("formatos_analisados") or [])
        formats = sorted(int(value) for value in summary_formats if int(value) >= MIN_FORMAT_SIZE)
    analyses: list[dict[str, Any]] = []
    for game_size in formats:
        if game_size < MIN_FORMAT_SIZE or game_size > MAX_FORMAT_SIZE:
            continue
        redundancy = dict(per_format.get(str(game_size)) or per_format.get(game_size) or {})
        overlap_max = int(
            redundancy.get("sobreposicao_maxima", metrics_map.get("sobreposicao_maxima", 0)) or 0
        )
        if not redundancy and game_size == int(metrics_map.get("primary_format_size", 0) or 0):
            overlap_max = int(metrics_map.get("sobreposicao_maxima", 0) or 0)
        fmt_metrics = {
            **metrics_map,
            "similaridade_media": float(
                redundancy.get("similaridade_media_entre_jogos", metrics_map.get("similaridade_media", 0.0))
                or 0.0
            ),
            "quase_repetidos": int(
                redundancy.get("cartoes_quase_repetidos", metrics_map.get("quase_repetidos", 0)) or 0
            ),
        }
        analyses.append(evaluate_format_overlap_verdict(game_size, overlap_max, fmt_metrics))
    return analyses


def resolve_primary_format_analysis(analyses: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    """Seleciona análise primária — prioriza veredito mais severo."""
    if not analyses:
        return None
    severity_order = {LEVEL_CRITICO: 4, LEVEL_RUIM: 3, LEVEL_ATENCAO: 2, LEVEL_BOM: 1}
    return max(
        (dict(row) for row in analyses),
        key=lambda row: (
            severity_order.get(str(row.get("level")), 0),
            int(row.get("sobreposicao_maxima", 0) or 0),
        ),
    )
