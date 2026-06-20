"""Memória ML de limiares format-aware — overlap e similaridade 15D–23D (M-ML-060 / M-ML-067)."""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

MISSION_ID = "M-ML-060"
MISSION_ID_067 = "M-ML-067"
MIN_FORMAT_SIZE = 15
MAX_FORMAT_SIZE = 23
SUPPORTED_FORMAT_SIZES: tuple[int, ...] = tuple(range(MIN_FORMAT_SIZE, MAX_FORMAT_SIZE + 1))

# Regra legada (pré M-ML-067): overlap fixo >= 13 em qualquer formato — incorreta para multidezena.
LEGACY_NEAR_DUPLICATE_OVERLAP_15D = 13

SIMILARITY_HIGH_THRESHOLD = 0.55
NEAR_DUP_HIGH_THRESHOLD = 20
DIVERSITY_LOW_THRESHOLD = 0.55
MISSION_ID_080 = "M-ML-080"


def resolve_diversity_low_threshold(requested_count: int) -> float:
    """Limiar adaptativo de diversidade por tamanho de lote (M-ML-080)."""
    count = max(int(requested_count or 0), 1)
    if count <= 5:
        return 0.35
    if count <= 10:
        return 0.42
    if count <= 20:
        return 0.48
    if count <= 50:
        return 0.52
    return DIVERSITY_LOW_THRESHOLD

LEVEL_BOM = "bom"
LEVEL_ATENCAO = "atencao"
LEVEL_RUIM = "ruim"
LEVEL_CRITICO = "critico"

LEVEL_LABELS: dict[str, str] = {
    LEVEL_BOM: "bom / aceitável",
    LEVEL_ATENCAO: "atenção",
    LEVEL_RUIM: "ruim / quase clone",
    LEVEL_CRITICO: "clone total / crítico",
}

GENERAL_SIMILARITY_BANDS: dict[str, float] = {
    "boa_diversidade_max": 0.50,
    "aceitavel_max": 0.58,
    "atencao_max": 0.64,
    "alta_redundancia_max": 0.70,
}

FORMAT_SIMILARITY_THRESHOLDS: dict[int, dict[str, float]] = {
    15: {
        "ideal_min": 0.50, "ideal_max": 0.55,
        "aceitavel_min": 0.56, "aceitavel_max": 0.58,
        "atencao_min": 0.59, "atencao_max": 0.64,
        "alta_min": 0.65, "critico_above": 0.70,
    },
    16: {
        "ideal_min": 0.52, "ideal_max": 0.57,
        "aceitavel_min": 0.58, "aceitavel_max": 0.61,
        "atencao_min": 0.62, "atencao_max": 0.66,
        "alta_min": 0.67, "critico_above": 0.70,
    },
    17: {
        "ideal_min": 0.56, "ideal_max": 0.60,
        "atencao_min": 0.61, "atencao_max": 0.64,
        "alta_min": 0.65, "alta_max": 0.70,
        "critico_above": 0.70,
    },
    18: {
        "ideal_min": 0.58, "ideal_max": 0.62,
        "atencao_min": 0.63, "atencao_max": 0.66,
        "alta_min": 0.67, "alta_max": 0.71,
        "critico_above": 0.71,
    },
    19: {
        "ideal_min": 0.60, "ideal_max": 0.64,
        "atencao_min": 0.65, "atencao_max": 0.68,
        "alta_min": 0.69, "alta_max": 0.73,
        "critico_above": 0.73,
    },
    20: {
        "ideal_min": 0.62, "ideal_max": 0.66,
        "atencao_min": 0.67, "atencao_max": 0.70,
        "alta_min": 0.71, "alta_max": 0.75,
        "critico_above": 0.75,
    },
    21: {
        "ideal_min": 0.64, "ideal_max": 0.68,
        "atencao_min": 0.69, "atencao_max": 0.72,
        "alta_min": 0.73, "alta_max": 0.77,
        "critico_above": 0.77,
    },
    22: {
        "ideal_min": 0.66, "ideal_max": 0.70,
        "atencao_min": 0.71, "atencao_max": 0.74,
        "alta_min": 0.75, "alta_max": 0.79,
        "critico_above": 0.79,
    },
    23: {
        "ideal_min": 0.68, "ideal_max": 0.72,
        "atencao_min": 0.73, "atencao_max": 0.76,
        "alta_min": 0.77, "alta_max": 0.81,
        "critico_above": 0.81,
    },
}


def build_format_overlap_threshold(game_size: int) -> dict[str, Any]:
    """Limiar de sobreposição máxima para formato N (regra geral M-ML-060 / M-ML-067)."""
    size = int(game_size)
    if size < MIN_FORMAT_SIZE or size > MAX_FORMAT_SIZE:
        raise ValueError(f"Formato {size}D fora do intervalo suportado {MIN_FORMAT_SIZE}D–{MAX_FORMAT_SIZE}D.")
    bom_max = size - 3
    return {
        "formato": f"{size}D",
        "game_size": size,
        "bom_max": bom_max,
        "aceitavel_max": bom_max,
        "atencao": size - 2,
        "ruim": size - 1,
        "critico": size,
        "faixa_ideal": (
            f"overlap {size}=clone total/crítico; {size - 1}=quase clone/ruim; "
            f"{size - 2}=atenção; {bom_max} ou menor=aceitável/bom"
        ),
    }


def classify_pair_overlap_level(overlap: int, game_size: int) -> str:
    """Classifica um par pelo overlap observado para formato N."""
    size = int(game_size)
    value = int(overlap)
    if value >= size:
        return LEVEL_CRITICO
    if value >= size - 1:
        return LEVEL_RUIM
    if value >= size - 2:
        return LEVEL_ATENCAO
    return LEVEL_BOM


def classify_overlap_for_format(overlap_max: int, game_size: int) -> dict[str, Any]:
    """Classifica sobreposição máxima observada para o formato N."""
    threshold = build_format_overlap_threshold(game_size)
    overlap = int(overlap_max)
    size = int(game_size)
    level = classify_pair_overlap_level(overlap, size)
    verdict_map = {
        LEVEL_CRITICO: f"CRÍTICO — clone/idêntico detectado no formato {size}D.",
        LEVEL_RUIM: f"RUIM — quase clone no formato {size}D (sobreposição {overlap}).",
        LEVEL_ATENCAO: f"ATENÇÃO — sobreposição elevada para {size}D (overlap {overlap}).",
        LEVEL_BOM: f"BOM — sobreposição dentro da faixa ideal para {size}D.",
    }
    return {
        "formato": f"{size}D",
        "game_size": size,
        "sobreposicao_maxima": overlap,
        "level": level,
        "level_label": LEVEL_LABELS[level],
        "verdict": verdict_map[level],
        "threshold": threshold,
        "faixa_ideal": threshold["faixa_ideal"],
    }


def classify_similarity_for_format(similarity: float, game_size: int) -> dict[str, Any]:
    """Classifica similaridade média para formato N (M-ML-067)."""
    size = int(game_size)
    thresholds = dict(FORMAT_SIMILARITY_THRESHOLDS.get(size) or FORMAT_SIMILARITY_THRESHOLDS[15])
    value = float(similarity)
    if value > float(thresholds["critico_above"]):
        band = "critico"
        label = "crítico"
    elif "alta_min" in thresholds and value >= float(thresholds["alta_min"]):
        band = "alta_redundancia"
        label = "alta redundância"
    elif "atencao_min" in thresholds and value >= float(thresholds["atencao_min"]):
        band = "atencao"
        label = "atenção / redundância moderada"
    elif "aceitavel_min" in thresholds and value >= float(thresholds["aceitavel_min"]):
        band = "aceitavel"
        label = "aceitável"
    elif value >= float(thresholds["ideal_min"]) and value <= float(
        thresholds.get("ideal_max", thresholds["ideal_min"])
    ):
        band = "ideal"
        label = "faixa ideal"
    elif value < float(thresholds["ideal_min"]):
        band = "boa_diversidade"
        label = "boa diversidade"
    else:
        band = "aceitavel"
        label = "aceitável"
    return {
        "formato": f"{size}D",
        "game_size": size,
        "similaridade_media": round(value, 4),
        "band": band,
        "band_label": label,
        "thresholds": thresholds,
        "general_bands": dict(GENERAL_SIMILARITY_BANDS),
    }


def build_pair_overlap_distribution(
    games: Sequence[Sequence[int]],
    *,
    game_size: int | None = None,
) -> dict[str, Any]:
    """Distribui pares por overlap e severidade format-aware (M-ML-067)."""
    normalized = [sorted({int(number) for number in game}) for game in games if game]
    if len(normalized) < 2:
        size = int(game_size or (len(normalized[0]) if normalized else 15))
        return {
            "game_size": size,
            "formato": f"{size}D",
            "pair_count": 0,
            "pares_possiveis": 0,
            "distribuicao_por_overlap": {},
            "pares_clone_total": 0,
            "pares_quase_clone": 0,
            "pares_atencao": 0,
            "pares_aceitavel": 0,
            "quase_repetidos_criticos": 0,
            "cartoes_quase_repetidos": 0,
            "near_duplicate_threshold_overlap": max(size - 1, 0),
            "atencao_threshold_overlap": max(size - 2, 0),
            "legacy_near_duplicate_overlap_15d": LEGACY_NEAR_DUPLICATE_OVERLAP_15D,
        }

    size = int(game_size or max(len(card) for card in normalized))
    threshold = build_format_overlap_threshold(size)
    counts_by_overlap: Counter[int] = Counter()
    bucket = {"clone_total": 0, "quase_clone": 0, "atencao": 0, "aceitavel": 0}

    for left_index, left in enumerate(normalized):
        left_set = set(left)
        for right in normalized[left_index + 1 :]:
            overlap = len(left_set & set(right))
            counts_by_overlap[overlap] += 1
            level = classify_pair_overlap_level(overlap, size)
            if level == LEVEL_CRITICO:
                bucket["clone_total"] += 1
            elif level == LEVEL_RUIM:
                bucket["quase_clone"] += 1
            elif level == LEVEL_ATENCAO:
                bucket["atencao"] += 1
            else:
                bucket["aceitavel"] += 1

    pair_count = sum(counts_by_overlap.values())
    critical_pairs = bucket["clone_total"] + bucket["quase_clone"]
    return {
        "game_size": size,
        "formato": f"{size}D",
        "pair_count": pair_count,
        "pares_possiveis": pair_count,
        "distribuicao_por_overlap": {str(key): int(value) for key, value in sorted(counts_by_overlap.items())},
        "pares_clone_total": bucket["clone_total"],
        "pares_quase_clone": bucket["quase_clone"],
        "pares_atencao": bucket["atencao"],
        "pares_aceitavel": bucket["aceitavel"],
        "quase_repetidos_criticos": critical_pairs,
        "cartoes_quase_repetidos": critical_pairs,
        "near_duplicate_threshold_overlap": int(threshold["ruim"]),
        "atencao_threshold_overlap": int(threshold["atencao"]),
        "legacy_near_duplicate_overlap_15d": LEGACY_NEAR_DUPLICATE_OVERLAP_15D,
        "overlap_composition_rows": build_overlap_composition_rows(size, counts_by_overlap),
    }


def build_overlap_composition_rows(
    game_size: int,
    counts_by_overlap: Mapping[int, int] | Counter[int],
) -> list[dict[str, Any]]:
    """Linhas de composição para Cobertura / Central ML."""
    size = int(game_size)
    threshold = build_format_overlap_threshold(size)
    rows: list[dict[str, Any]] = []
    for overlap in range(size, threshold["aceitavel_max"], -1):
        count = int(counts_by_overlap.get(overlap, 0) or 0)
        if overlap == size:
            label = "clone total / crítico"
        elif overlap == size - 1:
            label = "quase clone / ruim"
        elif overlap == size - 2:
            label = "atenção"
        else:
            continue
        rows.append(
            {
                "overlap": overlap,
                "pares": count,
                "classificacao": label,
                "level": classify_pair_overlap_level(overlap, size),
            }
        )
    aceitavel_count = sum(
        int(counts_by_overlap.get(overlap, 0) or 0)
        for overlap in range(1, threshold["aceitavel_max"] + 1)
    )
    rows.append(
        {
            "overlap": f"{threshold['aceitavel_max']} ou menor",
            "pares": aceitavel_count,
            "classificacao": "aceitável/bom",
            "level": LEVEL_BOM,
        }
    )
    return rows


def build_overlap_format_memory() -> dict[str, Any]:
    """Registro institucional de limiares 15D–23D (M-ML-060)."""
    thresholds = [build_format_overlap_threshold(size) for size in SUPPORTED_FORMAT_SIZES]
    return {
        "mission_id": MISSION_ID,
        "supported_formats": [f"{size}D" for size in SUPPORTED_FORMAT_SIZES],
        "thresholds": thresholds,
        "rule_summary": (
            "Para formato N: N=crítico; N-1=ruim/quase clone; N-2=atenção; até N-3=bom "
            "(desde que similaridade média e quase repetidos críticos não estejam altos)."
        ),
    }


def build_similarity_format_memory() -> dict[str, Any]:
    """Limiares de similaridade média por formato (M-ML-067)."""
    return {
        "mission_id": MISSION_ID_067,
        "general_bands": dict(GENERAL_SIMILARITY_BANDS),
        "format_thresholds": {
            f"{size}D": dict(FORMAT_SIMILARITY_THRESHOLDS[size])
            for size in SUPPORTED_FORMAT_SIZES
        },
    }


def build_ml_format_aware_memory() -> dict[str, Any]:
    """Memória ML unificada — overlap + similaridade + régua legada (M-ML-067)."""
    return {
        "mission_id": MISSION_ID_067,
        "overlap_memory": build_overlap_format_memory(),
        "similarity_memory": build_similarity_format_memory(),
        "legacy_rule": {
            "near_duplicate_overlap_fixed": LEGACY_NEAR_DUPLICATE_OVERLAP_15D,
            "status": "deprecated_pre_m_ml_067",
            "problem": (
                "Contava overlap >= 13 em qualquer formato — overlap 15 em 17D "
                "era tratado como quase repetido crítico."
            ),
        },
        "correct_rule": {
            "near_duplicate_critical": "overlap N (clone) + overlap N-1 (quase clone)",
            "attention_pairs": "overlap N-2",
            "acceptable_pairs": "overlap N-3 ou menor",
        },
    }


def _cross_check_redundancy_context(
    metrics: Mapping[str, Any],
    *,
    base_level: str,
    game_size: int | None = None,
) -> tuple[str, str]:
    """Cruza overlap com similaridade, quase repetidos críticos e diversidade."""
    similaridade = float(metrics.get("similaridade_media", 0.0) or 0.0)
    quase_repetidos = int(
        metrics.get("quase_repetidos_criticos", metrics.get("quase_repetidos", 0)) or 0
    )
    diversity_score = float(metrics.get("diversity_score", 1.0) or 1.0)
    size = int(game_size or metrics.get("primary_format_size", metrics.get("game_size", 15)) or 15)
    similarity_band = classify_similarity_for_format(similaridade, size)
    notes: list[str] = []
    level = base_level
    if base_level == LEVEL_BOM:
        if similarity_band["band"] in {"atencao", "alta_redundancia", "critico"}:
            level = LEVEL_ATENCAO
            notes.append(f"similaridade média {similaridade:.4f} — {similarity_band['band_label']}")
        elif similaridade >= SIMILARITY_HIGH_THRESHOLD:
            level = LEVEL_ATENCAO
            notes.append(f"similaridade média alta ({similaridade:.4f})")
        if quase_repetidos >= NEAR_DUP_HIGH_THRESHOLD:
            level = LEVEL_RUIM if level != LEVEL_CRITICO else level
            notes.append(f"quase repetidos críticos elevados ({quase_repetidos})")
        if diversity_score < DIVERSITY_LOW_THRESHOLD:
            level = LEVEL_ATENCAO if level == LEVEL_BOM else level
            notes.append(f"diversidade baixa ({diversity_score:.4f})")
    elif base_level in {LEVEL_ATENCAO, LEVEL_RUIM}:
        if similarity_band["band"] in {"alta_redundancia", "critico"}:
            notes.append(f"similaridade {similarity_band['band_label']} para {size}D")
        if quase_repetidos >= NEAR_DUP_HIGH_THRESHOLD:
            notes.append("quase repetidos críticos reforçam alerta estrutural")
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
    metrics_map.setdefault("primary_format_size", int(game_size))
    adjusted_level, cross_note = _cross_check_redundancy_context(
        metrics_map,
        base_level=str(base["level"]),
        game_size=int(game_size),
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
            "similaridade/quase repetidos críticos permanecerem altos."
        )
    similarity_reading = classify_similarity_for_format(
        float(metrics_map.get("similaridade_media", 0.0) or 0.0),
        int(game_size),
    )
    return {
        **base,
        "level": adjusted_level,
        "level_label": LEVEL_LABELS.get(adjusted_level, adjusted_level),
        "verdict": verdict,
        "cross_check_note": cross_note,
        "recommended_action": recommended_action,
        "similaridade_media": float(metrics_map.get("similaridade_media", 0.0) or 0.0),
        "similarity_band": similarity_reading,
        "quase_repetidos": int(
            metrics_map.get("quase_repetidos_criticos", metrics_map.get("quase_repetidos", 0)) or 0
        ),
        "quase_repetidos_criticos": int(
            metrics_map.get("quase_repetidos_criticos", metrics_map.get("quase_repetidos", 0)) or 0
        ),
        "pares_em_atencao": int(metrics_map.get("pares_em_atencao", 0) or 0),
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
            "primary_format_size": game_size,
            "game_size": game_size,
            "similaridade_media": float(
                redundancy.get("similaridade_media_entre_jogos", metrics_map.get("similaridade_media", 0.0))
                or 0.0
            ),
            "quase_repetidos": int(
                redundancy.get("quase_repetidos_criticos", redundancy.get("cartoes_quase_repetidos", 0))
                or metrics_map.get("quase_repetidos", 0)
                or 0
            ),
            "quase_repetidos_criticos": int(
                redundancy.get("quase_repetidos_criticos", redundancy.get("cartoes_quase_repetidos", 0)) or 0
            ),
            "pares_em_atencao": int(redundancy.get("pares_atencao", 0) or 0),
            "pair_count": int(redundancy.get("pair_count", redundancy.get("pares_possiveis", 0)) or 0),
            "distribuicao_por_overlap": dict(redundancy.get("distribuicao_por_overlap") or {}),
            "overlap_composition_rows": list(redundancy.get("overlap_composition_rows") or []),
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
