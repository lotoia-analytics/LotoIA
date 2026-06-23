"""Calibração de thresholds ML a partir de dados reais de conferência — M-SENSOR-001.

Este módulo resolve o problema do ML "alucinando" — thresholds arbitrários que
não refletem a realidade. Em vez de usar valores fixos (similaridade > 0.59 = atenção),
a calibração é empírica: analisa quantos prêmios jogos com determinada similaridade
realmente geram.

Fluxo:
1. Carrega todos os jogos conferidos (reconciliation_games)
2. Para cada jogo, calcula similaridade no lote de origem
3. Agrupa por faixa de similaridade: [0.50-0.55], [0.55-0.60], etc
4. Para cada faixa, calcula métricas: média de prêmios, taxa de 11+ hits, etc
5. Define threshold ótimo como a faixa com melhor relação custo-benefício

Uso:
    from lotoia.ml.threshold_calibration_from_conference import calibrate_ml_thresholds

    result = calibrate_ml_thresholds(db_path="postgresql://...")
    print(result["suggested_thresholds"])
    # {"ideal_max": 0.60, "aceitavel_max": 0.65, "atencao_max": 0.70, "critico_above": 0.78}
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict
from typing import Any, Mapping, Sequence

MISSION_ID = "M-SENSOR-001"
CALIBRATION_VERSION = "M-SENSOR-001-v1"

# Faixas de similaridade para análise
SIMILARITY_BINS: list[tuple[float, float, str]] = [
    (0.00, 0.50, "excelente_diversidade"),
    (0.50, 0.55, "boa_diversidade"),
    (0.55, 0.60, "aceitavel"),
    (0.60, 0.65, "atencao"),
    (0.65, 0.70, "alta_redundancia"),
    (0.70, 0.80, "redundancia_critica"),
    (0.80, 1.01, "clone_estrutural"),
]

# Minimum data for calibration
MIN_GAMES_PER_BIN = 10
MIN_TOTAL_GAMES = 50


def _resolve_database_url() -> str:
    for key in ("DATABASE_URL", "LOTOIA_DATABASE_URL", "LOTOIA_DATABASE_POOLER_URL"):
        value = str(os.getenv(key, "") or "").strip()
        if (
            value
            and not value.startswith("[")
            and "user:pass@host" not in value
            and len(value) >= 20
        ):
            return value.replace("postgresql+psycopg://", "postgresql://").replace(
                "postgresql+psycopg2://", "postgresql://"
            )
    raise RuntimeError(f"[{MISSION_ID}] DATABASE_URL não configurado.")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_conferenced_games_with_similarity(db_path: str) -> list[dict[str, Any]]:
    """Carrega jogos conferidos com similaridade calculada do lote de origem."""
    from sqlalchemy import create_engine, text

    engine = create_engine(db_path)
    with engine.connect() as conn:
        # Carrega reconciliation_games com hits e context
        rows = (
            conn.execute(
                text(
                    """
                SELECT
                    rg.id,
                    rg.game_id,
                    rg.generation_event_id,
                    rg.hits,
                    rg.contest_number,
                    rg.prize_tier,
                    gg.numbers AS game_numbers,
                    gg.context_json AS game_context,
                    ge.context_json AS event_context
                FROM reconciliation_games rg
                JOIN generated_games gg ON gg.id = rg.game_id
                JOIN generation_events ge ON ge.id = rg.generation_event_id
                WHERE rg.hits IS NOT NULL
                ORDER BY rg.contest_number DESC, rg.id DESC
                """
                )
            )
            .mappings()
            .all()
        )

    games = []
    for row in rows:
        game_numbers_raw = row["game_numbers"]
        if isinstance(game_numbers_raw, str):
            game_numbers = [
                int(n.strip())
                for n in game_numbers_raw.split(",")
                if n.strip().isdigit()
            ]
        elif isinstance(game_numbers_raw, list):
            game_numbers = [int(n) for n in game_numbers_raw]
        else:
            game_numbers = []

        if len(game_numbers) != 15:
            continue

        games.append(
            {
                "game_id": int(row["game_id"]),
                "generation_event_id": int(row["generation_event_id"]),
                "hits": _safe_int(row["hits"]),
                "contest_number": _safe_int(row["contest_number"]),
                "prize_tier": str(row["prize_tier"] or ""),
                "numbers": game_numbers,
                "event_context": dict(row["event_context"] or {}),
            }
        )

    return games


def compute_similarity_between_games(games: list[dict[str, Any]]) -> dict[int, float]:
    """Calcula similaridade média de cada jogo em relação aos outros do mesmo lote."""
    # Agrupa por generation_event_id (lote)
    lots: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for game in games:
        lots[game["generation_event_id"]].append(game)

    similarity_map: dict[int, float] = {}

    for lot_id, lot_games in lots.items():
        if len(lot_games) < 2:
            for game in lot_games:
                similarity_map[game["game_id"]] = 0.0
            continue

        for game in lot_games:
            overlaps = []
            for other in lot_games:
                if other["game_id"] == game["game_id"]:
                    continue
                overlap = len(set(game["numbers"]) & set(other["numbers"]))
                overlaps.append(overlap)

            avg_overlap = sum(overlaps) / len(overlaps) if overlaps else 0
            # Similaridade = overlap médio / 15 (normalizado 0-1)
            similarity_map[game["game_id"]] = round(avg_overlap / 15.0, 4)

    return similarity_map


def analyze_similarity_vs_performance(
    games: list[dict[str, Any]],
    similarity_map: dict[int, float],
) -> list[dict[str, Any]]:
    """Analisa performance por faixa de similaridade."""
    bins_data: dict[str, list[dict[str, Any]]] = {
        label: [] for _, _, label in SIMILARITY_BINS
    }

    for game in games:
        similarity = similarity_map.get(game["game_id"], 0.0)
        for low, high, label in SIMILARITY_BINS:
            if low <= similarity < high:
                bins_data[label].append(game)
                break

    results: list[dict[str, Any]] = []
    for low, high, label in SIMILARITY_BINS:
        bin_games = bins_data[label]
        count = len(bin_games)
        if count == 0:
            results.append(
                {
                    "bin": label,
                    "range": f"[{low:.2f}, {high:.2f})",
                    "games_count": 0,
                    "avg_hits": 0,
                    "max_hits": 0,
                    "prize_rate_11plus": 0,
                    "avg_prizes": 0,
                    "performance_score": 0,
                }
            )
            continue

        hits_list = [g["hits"] for g in bin_games]
        avg_hits = sum(hits_list) / count
        max_hits = max(hits_list)
        prizes_11plus = sum(1 for h in hits_list if h >= 11)
        prize_rate_11plus = prizes_11plus / count

        # Performance score: combina média de hits + taxa de prêmios
        performance_score = (avg_hits / 15.0) * 0.5 + prize_rate_11plus * 0.5

        results.append(
            {
                "bin": label,
                "range": f"[{low:.2f}, {high:.2f})",
                "games_count": count,
                "avg_hits": round(avg_hits, 2),
                "max_hits": max_hits,
                "prize_rate_11plus": round(prize_rate_11plus, 4),
                "avg_prizes": round(sum(g["hits"] for g in bin_games) / count, 2),
                "performance_score": round(performance_score, 4),
            }
        )

    return results


def derive_calibrated_thresholds(
    bin_analysis: list[dict[str, Any]],
) -> dict[str, float]:
    """Deriva thresholds calibrados a partir da análise por faixa."""
    # Encontra a faixa com melhor performance score que tem dados suficientes
    viable_bins = [
        b
        for b in bin_analysis
        if b["games_count"] >= MIN_GAMES_PER_BIN and b["performance_score"] > 0
    ]

    if not viable_bins:
        # Fallback: thresholds conservadores baseados em dados limitados
        return {
            "ideal_max": 0.58,
            "aceitavel_max": 0.63,
            "atencao_max": 0.68,
            "critico_above": 0.75,
            "calibration_confidence": "low",
        }

    # Ordena por performance_score decrescente
    viable_bins.sort(key=lambda b: b["performance_score"], reverse=True)

    # Pega a melhor faixa e define thresholds ao redor dela
    best_bin = viable_bins[0]
    best_range = best_bin["range"]
    # Extrai bounds da faixa
    parts = best_range.strip("[]").split(",")
    best_low = float(parts[0])
    best_high = float(parts[1])

    # Encontra a faixa "ruim" (performance < 50% da melhor)
    threshold_half = best_bin["performance_score"] * 0.5
    bad_bins = [b for b in viable_bins if b["performance_score"] < threshold_half]

    # Define thresholds
    ideal_max = best_low + 0.03  # Acima do ideal
    aceitavel_max = best_high + 0.03  # Acima da melhor faixa
    atencao_max = best_high + 0.08  # Zona de atenção
    critico_above = max(atencao_max + 0.08, 0.78)  # Crítico

    # Se há dados ruins, usa o início da primeira faixa ruim
    if bad_bins:
        bad_bins.sort(key=lambda b: b["performance_score"])
        critico_above = max(
            critico_above, float(bad_bins[0]["range"].strip("[]").split(",")[0])
        )

    # Calcula confiança
    total_games = sum(b["games_count"] for b in bin_analysis)
    confidence = (
        "high" if total_games >= 500 else "medium" if total_games >= 200 else "low"
    )

    return {
        "ideal_max": round(ideal_max, 2),
        "aceitavel_max": round(aceitavel_max, 2),
        "atencao_max": round(atencao_max, 2),
        "critico_above": round(critico_above, 2),
        "calibration_confidence": confidence,
        "best_bin": best_bin["bin"],
        "best_bin_performance": best_bin["performance_score"],
        "total_games_analyzed": total_games,
    }


def calibrate_ml_thresholds(db_path: str | None = None) -> dict[str, Any]:
    """Pipeline completo de calibração de thresholds ML a partir de dados reais.

    Returns:
        Dict com:
        - current_thresholds: thresholds atuais (do código)
        - bin_analysis: análise por faixa de similaridade
        - suggested_thresholds: thresholds calibrados
        - recommendation: texto explicativo
    """
    if db_path is None:
        db_path = _resolve_database_url()

    current_thresholds = {
        "ideal_max": 0.55,
        "aceitavel_max": 0.58,
        "atencao_max": 0.64,
        "critico_above": 0.70,
    }

    games = load_conferenced_games_with_similarity(db_path)
    if len(games) < MIN_TOTAL_GAMES:
        return {
            "mission_id": MISSION_ID,
            "status": "insufficient_data",
            "total_games": len(games),
            "min_required": MIN_TOTAL_GAMES,
            "message": f"Dados insuficientes para calibração ({len(games)} jogos, mínimo {MIN_TOTAL_GAMES})",
            "current_thresholds": current_thresholds,
            "suggested_thresholds": current_thresholds,
        }

    similarity_map = compute_similarity_between_games(games)
    bin_analysis = analyze_similarity_vs_performance(games, similarity_map)
    suggested = derive_calibrated_thresholds(bin_analysis)

    # Gera recomendação textual
    if suggested.get("calibration_confidence") == "high":
        recommendation = (
            f"Thresholds calibrados com alta confiança ({suggested['total_games_analyzed']} jogos). "
            f"Faixa ótima: {suggested['best_bin']} (performance {suggested['best_bin_performance']:.2%}). "
            f"Recomenda-se atualizar thresholds para: ideal_max={suggested['ideal_max']}, "
            f"aceitavel_max={suggested['aceitavel_max']}, atencao_max={suggested['atencao_max']}, "
            f"critico_above={suggested['critico_above']}."
        )
    elif suggested.get("calibration_confidence") == "medium":
        recommendation = (
            f"Thresholds calibrados com confiança média ({suggested['total_games_analyzed']} jogos). "
            f"Mais dados de conferência melhorariam a precisão."
        )
    else:
        recommendation = (
            f"Dados limitados ({suggested['total_games_analyzed']} jogos). "
            f"Thresholds sugeridos são conservadores. Execute mais conferências para calibrar melhor."
        )

    return {
        "mission_id": MISSION_ID,
        "calibration_version": CALIBRATION_VERSION,
        "status": "success",
        "total_games_analyzed": len(games),
        "total_lots_analyzed": len(set(g["generation_event_id"] for g in games)),
        "current_thresholds": current_thresholds,
        "bin_analysis": bin_analysis,
        "suggested_thresholds": suggested,
        "recommendation": recommendation,
    }


if __name__ == "__main__":
    import json

    result = calibrate_ml_thresholds()
    print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
