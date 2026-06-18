"""Seleção e comparação multicontest para Simular Resultados (M-OPS-062-FIX-02)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable, Mapping, Sequence

from lotoia.analytics.lotofacil_scientific_core import _decompose_hit_counts
from lotoia.operations.lot_operational_status import (
    GENERATION_ORIGIN_SIMULATION,
    STATUS_CALIBRATION_SOURCE_ONLY,
    STATUS_NOT_OFFICIALIZED,
)

from dashboard.institutional_monitored_contest import (
    SOVEREIGN_SOURCE_LABEL,
    build_imported_contests_selection_context,
    to_conference_contest_payload,
)

MISSION_ID = "M-OPS-062-FIX-02"
SIMULATION_MAX_CONTESTS = 50
SIMULATION_LAST_N_OPTIONS: tuple[int, ...] = (10, 20, 30, 50)

SELECTION_MODE_LAST_10 = "last_10"
SELECTION_MODE_LAST_20 = "last_20"
SELECTION_MODE_LAST_30 = "last_30"
SELECTION_MODE_LAST_50 = "last_50"
SELECTION_MODE_MANUAL_RANGE = "manual_range"

SELECTION_MODE_LABELS: dict[str, str] = {
    SELECTION_MODE_LAST_10: "Usar últimos 10 concursos oficiais",
    SELECTION_MODE_LAST_20: "Usar últimos 20 concursos oficiais",
    SELECTION_MODE_LAST_30: "Usar últimos 30 concursos oficiais",
    SELECTION_MODE_LAST_50: "Usar últimos 50 concursos oficiais",
    SELECTION_MODE_MANUAL_RANGE: "Selecionar intervalo manual",
}


def build_simulation_contests_context(
    *,
    list_imported_contest_records: Callable[[], list[dict[str, Any]]],
    load_imported_contest: Callable[[int], dict[str, Any] | None],
    official_history_max: int | None = None,
) -> dict[str, Any]:
    """Contexto soberano de concursos para Simular Resultados — PostgreSQL/imported_contests."""
    selection = build_imported_contests_selection_context(
        list_imported_contest_records=list_imported_contest_records,
        load_imported_contest=load_imported_contest,
        official_history_max=official_history_max,
    )
    valid_numbers = list(selection.get("valid_contest_numbers") or [])
    return {
        **selection,
        "mission_id": MISSION_ID,
        "source": SOVEREIGN_SOURCE_LABEL,
        "latest_contest_available": int(selection.get("max_contest") or 0),
        "valid_contest_numbers_desc": list(reversed(valid_numbers)),
        "max_selectable_contests": SIMULATION_MAX_CONTESTS,
    }


def _resolve_last_n_contest_numbers(valid_numbers_desc: Sequence[int], count: int) -> list[int]:
    ordered = sorted(int(number) for number in valid_numbers_desc if int(number) > 0)
    if not ordered:
        return []
    return ordered[-min(int(count), len(ordered)) :]


def resolve_simulation_contest_selection(
    *,
    context: Mapping[str, Any],
    selection_mode: str,
    manual_start: int | None = None,
    manual_end: int | None = None,
) -> dict[str, Any]:
    """Resolve concursos selecionados respeitando limite de 50."""
    valid_numbers = sorted(int(number) for number in (context.get("valid_contest_numbers") or []) if int(number) > 0)
    valid_set = set(valid_numbers)
    mode = str(selection_mode or SELECTION_MODE_LAST_10).strip()
    blocked = False
    block_reason = ""

    if not valid_numbers:
        return {
            "blocked": True,
            "block_reason": "Nenhum concurso oficial válido em imported_contests.",
            "contest_numbers": [],
            "selection_mode": mode,
            "contest_initial": 0,
            "contest_final": 0,
            "total_selected": 0,
        }

    if mode == SELECTION_MODE_MANUAL_RANGE:
        start = int(manual_start or 0)
        end = int(manual_end or 0)
        if start <= 0 or end <= 0:
            return {
                "blocked": True,
                "block_reason": "Informe concurso inicial e final válidos.",
                "contest_numbers": [],
                "selection_mode": mode,
                "contest_initial": start,
                "contest_final": end,
                "total_selected": 0,
            }
        if start > end:
            start, end = end, start
        range_numbers = [number for number in valid_numbers if start <= number <= end]
        if not range_numbers:
            return {
                "blocked": True,
                "block_reason": "Intervalo manual não contém concursos válidos em imported_contests.",
                "contest_numbers": [],
                "selection_mode": mode,
                "contest_initial": start,
                "contest_final": end,
                "total_selected": 0,
            }
        if len(range_numbers) > SIMULATION_MAX_CONTESTS:
            return {
                "blocked": True,
                "block_reason": (
                    f"Intervalo manual excede o limite de {SIMULATION_MAX_CONTESTS} concursos "
                    f"({len(range_numbers)} encontrados)."
                ),
                "contest_numbers": [],
                "selection_mode": mode,
                "contest_initial": start,
                "contest_final": end,
                "total_selected": len(range_numbers),
            }
        selected = range_numbers
    else:
        last_n_map = {
            SELECTION_MODE_LAST_10: 10,
            SELECTION_MODE_LAST_20: 20,
            SELECTION_MODE_LAST_30: 30,
            SELECTION_MODE_LAST_50: 50,
        }
        count = last_n_map.get(mode, 10)
        selected = _resolve_last_n_contest_numbers(valid_numbers, count)
        if not selected:
            return {
                "blocked": True,
                "block_reason": "Não foi possível resolver concursos oficiais recentes.",
                "contest_numbers": [],
                "selection_mode": mode,
                "contest_initial": 0,
                "contest_final": 0,
                "total_selected": 0,
            }

    selected = sorted(set(int(number) for number in selected if int(number) in valid_set))
    return {
        "blocked": blocked,
        "block_reason": block_reason,
        "contest_numbers": selected,
        "selection_mode": mode,
        "contest_initial": selected[0] if selected else 0,
        "contest_final": selected[-1] if selected else 0,
        "total_selected": len(selected),
        "source": SOVEREIGN_SOURCE_LABEL,
        "latest_contest_available": int(context.get("latest_contest_available") or context.get("max_contest") or 0),
    }


def _extract_game_numbers(game: Mapping[str, Any]) -> list[int]:
    raw = game.get("numbers", game.get("final_card_numbers", []))
    numbers: list[int] = []
    for value in raw or []:
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if 1 <= number <= 25 and number not in numbers:
            numbers.append(number)
    return sorted(numbers)


def compare_lab_games_against_contests(
    *,
    games: Sequence[Mapping[str, Any]],
    contest_records: Sequence[Mapping[str, Any]],
    normalize_contest_record: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
) -> dict[str, Any]:
    """Compara lote laboratorial contra concursos selecionados — agrega faixas 11–15."""
    normalize = normalize_contest_record or (lambda record: record)
    contest_results: list[dict[str, Any]] = []
    premium_rows: list[dict[str, Any]] = []
    all_hit_values: list[int] = []
    best_overall_hits = 0
    best_overall_game = 0
    best_overall_contest = 0
    game_best_hits: dict[int, int] = {}

    for record in contest_records:
        contest_payload = to_conference_contest_payload(dict(record)) or dict(normalize(dict(record)) or {})
        if not contest_payload or not contest_payload.get("dezenas"):
            continue
        contest_numbers = set(_extract_game_numbers({"numbers": contest_payload.get("dezenas", [])}))
        contest_number = int(contest_payload.get("concurso", record.get("contest_number", 0)) or 0)
        game_rows: list[dict[str, Any]] = []
        for index, game in enumerate(games, start=1):
            numbers = _extract_game_numbers(game)
            matched = sorted(set(numbers) & contest_numbers)
            hits = len(matched)
            all_hit_values.append(hits)
            game_best_hits[index] = max(game_best_hits.get(index, 0), hits)
            if hits > best_overall_hits:
                best_overall_hits = hits
                best_overall_game = index
                best_overall_contest = contest_number
            row = {
                "concurso": contest_number,
                "jogo": index,
                "hits": hits,
                "premiado": "sim" if hits >= 11 else "nao",
                "dezenas": " ".join(f"{number:02d}" for number in numbers),
                "matched_numbers": matched,
            }
            game_rows.append(row)
            if hits >= 11:
                premium_rows.append(row)
        contest_results.append(
            {
                "contest_number": contest_number,
                "total_games": len(game_rows),
                "premium_games": sum(1 for row in game_rows if int(row.get("hits", 0) or 0) >= 11),
                "best_hits": max((int(row.get("hits", 0) or 0) for row in game_rows), default=0),
                "best_game_index": max(game_rows, key=lambda row: int(row.get("hits", 0) or 0)).get("jogo", 0)
                if game_rows
                else 0,
                "results": game_rows,
            }
        )

    hit_decomposition = _decompose_hit_counts(all_hit_values)
    best_game_index = max(game_best_hits, key=lambda key: game_best_hits[key]) if game_best_hits else 0
    return {
        "mission_id": MISSION_ID,
        "contests_compared": len(contest_results),
        "contest_numbers": [int(block.get("contest_number", 0) or 0) for block in contest_results],
        "premium_rows": premium_rows,
        "contest_results": contest_results,
        "generation_origin": GENERATION_ORIGIN_SIMULATION,
        "officialization_blocked": True,
        "aggregate_summary": {
            "count_11_exact": int(hit_decomposition.get("count_11_exact", 0) or 0),
            "count_12_exact": int(hit_decomposition.get("count_12_exact", 0) or 0),
            "count_13_exact": int(hit_decomposition.get("count_13_exact", 0) or 0),
            "count_14_exact": int(hit_decomposition.get("count_14_exact", 0) or 0),
            "count_15_exact": int(hit_decomposition.get("count_15_exact", 0) or 0),
            "count_11_plus": int(hit_decomposition.get("count_11_plus", 0) or 0),
            "hit_histogram": dict(hit_decomposition.get("hit_histogram") or {}),
            "has_13_or_14": bool(
                int(hit_decomposition.get("count_13_exact", 0) or 0)
                + int(hit_decomposition.get("count_14_exact", 0) or 0)
                > 0
            ),
            "has_15": bool(int(hit_decomposition.get("count_15_exact", 0) or 0) > 0),
        },
        "best_overall": {
            "best_hits": best_overall_hits,
            "best_game_index": best_overall_game,
            "best_contest_number": best_overall_contest,
        },
        "best_game_of_batch": {
            "game_index": best_game_index,
            "best_hits_across_window": game_best_hits.get(best_game_index, 0),
        },
        "total_game_contest_pairs": len(all_hit_values),
        "total_games": len(games),
    }


def build_simulation_central_ml_evidence(
    *,
    multicontest_payload: Mapping[str, Any],
    lab_result: Mapping[str, Any],
    selection: Mapping[str, Any],
) -> dict[str, Any]:
    """Evidência de simulação para Central ML — lote laboratório, não oficializado."""
    aggregate = dict(multicontest_payload.get("aggregate_summary") or {})
    lot_status = str(
        lab_result.get("lot_operational_status")
        or STATUS_NOT_OFFICIALIZED
    ).strip().lower()
    if lot_status not in {STATUS_NOT_OFFICIALIZED, STATUS_CALIBRATION_SOURCE_ONLY}:
        lot_status = STATUS_NOT_OFFICIALIZED
    return {
        "mission_id": MISSION_ID,
        "evidence_type": "simulation_multicontest_lab",
        "status": lot_status,
        "lot_operational_status": lot_status,
        "officialization_blocked": True,
        "generation_origin": GENERATION_ORIGIN_SIMULATION,
        "simulation_mode": True,
        "contests_compared": int(multicontest_payload.get("contests_compared", 0) or 0),
        "contest_numbers": list(multicontest_payload.get("contest_numbers") or []),
        "contest_initial": int(selection.get("contest_initial", 0) or 0),
        "contest_final": int(selection.get("contest_final", 0) or 0),
        "selection_mode": str(selection.get("selection_mode") or ""),
        "source": SOVEREIGN_SOURCE_LABEL,
        "total_games": int(multicontest_payload.get("total_games", 0) or 0),
        "card_format": int(lab_result.get("selected_card_format", lab_result.get("card_format", 15)) or 15),
        "format_label": str(lab_result.get("card_format_label") or ""),
        "hit_distribution": {
            "11": int(aggregate.get("count_11_exact", 0) or 0),
            "12": int(aggregate.get("count_12_exact", 0) or 0),
            "13": int(aggregate.get("count_13_exact", 0) or 0),
            "14": int(aggregate.get("count_14_exact", 0) or 0),
            "15": int(aggregate.get("count_15_exact", 0) or 0),
        },
        "has_13_or_14": bool(aggregate.get("has_13_or_14")),
        "has_15": bool(aggregate.get("has_15")),
        "best_overall": dict(multicontest_payload.get("best_overall") or {}),
        "best_game_of_batch": dict(multicontest_payload.get("best_game_of_batch") or {}),
        "calibration_evidence": {
            "eligible_for_calibration_reading": True,
            "does_not_officialize": True,
            "does_not_enter_analytical_history": True,
            "does_not_enter_conference": True,
        },
        "simulation_trace": {
            "compared_at": datetime.now(UTC).isoformat(),
            "generation_event_id": int(lab_result.get("generation_event_id", 0) or 0),
            "ml_verdict": str(lab_result.get("ml_verdict") or ""),
            "aggregate_summary": aggregate,
        },
    }


def merge_simulation_evidence_into_context(
    context: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Anexa evidência de simulação ao context_json sem alterar status operacional."""
    merged = dict(context or {})
    merged["simulation_multicontest_evidence"] = dict(evidence)
    merged["simulation_multicontest_at"] = str(evidence.get("simulation_trace", {}).get("compared_at") or "")
    merged["central_ml_simulation_evidence_registered"] = True
    return merged
