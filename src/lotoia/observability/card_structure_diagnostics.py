"""Diagnóstico observacional de cobertura estrutural do cartão (PostgreSQL only)."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from lotoia.database.database import (
    DEFAULT_DATABASE_PATH,
    GeneratedGame,
    GenerationEvent,
    LotofacilOfficialHistory,
    ReconciliationGame,
    ReconciliationRun,
    get_session,
)
from lotoia.governance.analysis_batch_labels import batch_label_game_size
from lotoia.governance.batch_operational_scope import (
    is_active_reading_scope,
    is_generation_event_active_reading,
    summarize_active_reading_exclusions,
)
from lotoia.governance.lei15_core_002_sovereign import core_002_batch_label_game_size, is_sovereign_core_label
from lotoia.observability.hb_metrics import (
    resolve_official_numbers_for_contest,
    resolve_reconciliation_game_hits,
)
from lotoia.statistics.card_structure import (
    analyze_stuck_games,
    compare_structure_profiles,
    compute_card_structure_metrics,
    compute_gp_redundancy,
    compute_missing_dezenas,
    compute_prefix,
    compute_suffix,
    format_dezena_group,
    resolve_cartao_final_from_game,
)

SOURCE_POSTGRESQL = "postgresql"
RECONCILIATION_TABLES = "reconciliation_runs / reconciliation_games"
OPERATIONAL_TABLES = "generation_events / generated_games"
DEFAULT_OFFICIAL_WINDOW = 50
EVIDENCE_LEVEL_LOCAL = "LOCAL_DIAGNOSTIC"
EVIDENCE_LEVEL_STRUCTURAL_RECURRENT = "STRUCTURAL_RECURRENT_DIAGNOSTIC"
MIN_GENERATIONS_RECURRENT = 20
MIN_CONTESTS_RECURRENT = 5
MISSION_ID_STRUCTURAL_SNAPSHOT = "M-ML-VIS-059"
SCOPE_ALL_OPERATIONAL_CORE_002 = "operational_core_002_all"
SCOPE_LABEL_ALL_OPERATIONAL = "Todos — todas as gerações operacionais CORE_002"
SOURCE_COBERTURA_ESTRUTURAL = "cobertura_estrutural"


def empty_card_structure_payload() -> dict[str, Any]:
    return {
        "available": False,
        "source": SOURCE_POSTGRESQL,
        "tables": RECONCILIATION_TABLES,
        "operational_effect": False,
        "generation_command": False,
        "recalibration_command": False,
        "ml_role": "diagnostic_only",
        "summary": {
            "total_geracoes": 0,
            "total_jogos": 0,
            "total_concursos_comparados": 0,
            "formatos_analisados": [],
        },
        "abertura": {},
        "fechamento": {},
        "faixas_gaps": {},
        "travamento_13_14": {},
        "redundancia_gp": {},
        "comparacao_oficial": {},
        "evidence_base": {
            "concursos_analisados": [],
            "generation_event_ids": [],
            "reconciliation_run_ids": [],
            "analysis_batch_label": None,
            "analysis_batch_labels": [],
            "formatos_analisados": [],
            "total_concursos": 0,
            "total_geracoes": 0,
            "total_runs": 0,
            "evidence_level": EVIDENCE_LEVEL_LOCAL,
        },
        "evidence_level": EVIDENCE_LEVEL_LOCAL,
        "excluded_batches_count": 0,
        "excluded_batches_message": "Nenhum lote excluído da leitura ativa.",
        "excluded_batches_audit": [],
    }


def empty_operational_card_structure_payload() -> dict[str, Any]:
    payload = empty_card_structure_payload()
    payload["tables"] = OPERATIONAL_TABLES
    payload["coverage_layer"] = "operational_core_002"
    return payload


def _serialize_generated_game(row: GeneratedGame, *, generation_event_id: int) -> dict[str, Any]:
    context = dict(row.context_json or {})
    numbers = [int(number) for number in (row.numbers or [])]
    final_card_numbers = [int(number) for number in (context.get("final_card_numbers") or numbers or [])]
    return {
        "game_index": int(row.game_index or 0),
        "numbers": numbers,
        "final_card_numbers": final_card_numbers,
        "core_numbers": list(context.get("core_numbers") or []),
        "audited_reserve_numbers": list(context.get("audited_reserve_numbers") or []),
        "generation_event_id": int(generation_event_id),
        "reconciliation_run_id": 0,
        "hits": 0,
        "matched_numbers": [],
        "prize_tier": "",
        "contest_id": int(getattr(row, "target_contest", 0) or 0),
    }


def _resolve_generated_game_card_size(game: dict[str, Any], *, batch_label: str | None = None) -> int:
    numbers = resolve_cartao_final_from_game(game)
    if numbers:
        return len(numbers)
    label_size = core_002_batch_label_game_size(batch_label)
    if label_size is not None:
        return int(label_size)
    return len(game.get("numbers") or [])


def _event_eligible_for_active_structural_reading(context: Mapping[str, Any]) -> bool:
    """Lotes ativos na leitura padrão — M-DADOS-ML-061 / M-OPS-062 / M-OPS-062-FIX-04."""
    if context.get("legacy_excluded_from_active_coverage"):
        return False
    if context.get("active_reading_scope") is False:
        return False
    return is_active_reading_scope(context)


def load_operational_card_structure_diagnostics_from_db(
    db_path: Path | str = DEFAULT_DATABASE_PATH,
    *,
    generation_event_id: int | None = None,
    generation_event_ids: Sequence[int] | None = None,
    game_size: int | None = None,
    official_window: int = DEFAULT_OFFICIAL_WINDOW,
) -> dict[str, Any]:
    """Carrega diagnóstico estrutural a partir de generation_events + generated_games (CORE_002)."""
    selected_ge_id = int(generation_event_id or 0)
    effective_game_size = int(game_size) if game_size is not None and int(game_size) > 0 else None
    allowed_event_ids = {
        int(value)
        for value in (generation_event_ids or [])
        if int(value) > 0
    }

    with get_session(db_path) as session:
        event_query = session.query(GenerationEvent).order_by(
            GenerationEvent.created_at.asc(),
            GenerationEvent.id.asc(),
        )
        if selected_ge_id > 0:
            event_query = event_query.filter(GenerationEvent.id == selected_ge_id)
        elif allowed_event_ids:
            event_query = event_query.filter(GenerationEvent.id.in_(sorted(allowed_event_ids)))
        events = event_query.all()

        sovereign_events = [
            event
            for event in events
            if is_sovereign_core_label(str(getattr(event, "analysis_batch_label", "") or ""))
            and is_generation_event_active_reading(event)
        ]
        exclusions_summary = summarize_active_reading_exclusions(db_path)
        if not sovereign_events:
            empty_payload = empty_operational_card_structure_payload()
            empty_payload["excluded_batches_count"] = int(exclusions_summary.get("excluded_batches_count", 0) or 0)
            empty_payload["excluded_batches_message"] = str(exclusions_summary.get("message", "") or "")
            empty_payload["excluded_batches_audit"] = list(exclusions_summary.get("excluded_batches") or [])
            return empty_payload

        games: list[dict[str, Any]] = []
        generation_event_ids: list[int] = []
        contest_ids: list[int] = []
        batch_labels_seen: set[str] = set()
        selected_batch_label: str | None = None

        for event in sovereign_events:
            ge_id = int(event.id or 0)
            if ge_id <= 0:
                continue
            event_context = dict(getattr(event, "context_json", {}) or {})
            if not _event_eligible_for_active_structural_reading(event_context):
                continue
            rows = (
                session.query(GeneratedGame)
                .filter(GeneratedGame.generation_event_id == ge_id)
                .order_by(GeneratedGame.game_index.asc())
                .all()
            )
            if not rows:
                continue
            event_label = str(getattr(event, "analysis_batch_label", "") or "").strip()
            if event_label:
                batch_labels_seen.add(event_label)
                if selected_ge_id > 0:
                    selected_batch_label = event_label
            generation_event_ids.append(ge_id)
            for row in rows:
                payload = _serialize_generated_game(row, generation_event_id=ge_id)
                contest_id = int(payload.get("contest_id") or 0)
                if contest_id > 0:
                    contest_ids.append(contest_id)
                resolved_card = resolve_cartao_final_from_game(payload)
                card_size = len(resolved_card) if resolved_card else _resolve_generated_game_card_size(
                    payload,
                    batch_label=event_label,
                )
                if effective_game_size is not None and card_size != effective_game_size:
                    continue
                games.append(payload)

        if not games:
            return empty_operational_card_structure_payload()

        official_cards, official_contests = _load_official_cards(session, limit=official_window)

    payload = build_card_structure_payload(
        games=games,
        official_cards=official_cards,
        official_contests=official_contests,
        generation_event_ids=generation_event_ids,
        reconciliation_run_ids=[],
        contest_ids=contest_ids,
        analysis_batch_labels=sorted(batch_labels_seen),
        selected_analysis_batch_label=str(selected_batch_label or "").strip().upper() or None,
        excluded_batches_summary=exclusions_summary,
    )
    payload["tables"] = OPERATIONAL_TABLES
    payload["coverage_layer"] = "operational_core_002"
    if selected_ge_id > 0:
        payload["selected_generation_event_id"] = selected_ge_id
    return payload


def resolve_evidence_level(*, total_geracoes: int, total_concursos: int) -> str:
    if total_geracoes >= MIN_GENERATIONS_RECURRENT and total_concursos >= MIN_CONTESTS_RECURRENT:
        return EVIDENCE_LEVEL_STRUCTURAL_RECURRENT
    return EVIDENCE_LEVEL_LOCAL


def _serialize_reconciliation_game(row: ReconciliationGame, *, run_id: int) -> dict[str, Any]:
    return {
        "game_index": int(row.game_index or 0),
        "numbers": list(row.numbers or []),
        "hits": int(row.hits or 0),
        "matched_numbers": list(row.matched_numbers or []),
        "prize_tier": str(row.prize_tier or ""),
        "contest_id": int(row.contest_id or 0),
        "generation_event_id": int(row.generation_event_id or 0),
        "reconciliation_run_id": int(run_id),
    }


def _load_official_cards(session: Any, *, limit: int = DEFAULT_OFFICIAL_WINDOW) -> tuple[list[list[int]], list[int]]:
    rows = (
        session.query(LotofacilOfficialHistory)
        .order_by(LotofacilOfficialHistory.contest_number.desc())
        .limit(max(1, int(limit)))
        .all()
    )
    cards: list[list[int]] = []
    contests: list[int] = []
    for row in rows:
        contest_id = int(getattr(row, "contest_number", 0) or 0)
        numbers_text = str(getattr(row, "numbers", "") or "")
        numbers = [
            int(token)
            for token in numbers_text.replace(",", " ").split()
            if str(token).strip().lstrip("+").isdigit()
        ]
        numbers = sorted({number for number in numbers if 1 <= number <= 25})
        if len(numbers) == 15:
            cards.append(numbers)
            contests.append(contest_id)
    return cards, sorted(set(contests))


def _aggregate_opening_closing(cards: Sequence[Sequence[int]]) -> tuple[dict[str, Any], dict[str, Any]]:
    prefix3 = Counter(format_dezena_group(compute_prefix(card, 3)) for card in cards)
    prefix4 = Counter(format_dezena_group(compute_prefix(card, 4)) for card in cards)
    suffix3 = Counter(format_dezena_group(compute_suffix(card, 3)) for card in cards)
    suffix4 = Counter(format_dezena_group(compute_suffix(card, 4)) for card in cards)

    def top(counter: Counter[str], limit: int = 5) -> list[dict[str, Any]]:
        return [{"estrutura": key, "frequencia": count} for key, count in counter.most_common(limit)]

    low_prefix3 = [item for item, count in prefix3.items() if count == 1][:5]
    low_suffix3 = [item for item, count in suffix3.items() if count == 1][:5]
    abertura = {
        "prefixo_3_mais_gerado": top(prefix3, 1)[0] if prefix3 else None,
        "prefixo_4_mais_gerado": top(prefix4, 1)[0] if prefix4 else None,
        "prefixos_pouco_cobertos": low_prefix3,
        "ranking_prefixo_3": top(prefix3),
        "ranking_prefixo_4": top(prefix4),
    }
    fechamento = {
        "sufixo_3_mais_gerado": top(suffix3, 1)[0] if suffix3 else None,
        "sufixo_4_mais_gerado": top(suffix4, 1)[0] if suffix4 else None,
        "sufixos_pouco_cobertos": low_suffix3,
        "ranking_sufixo_3": top(suffix3),
        "ranking_sufixo_4": top(suffix4),
    }
    return abertura, fechamento


def _aggregate_faixas_gaps(cards: Sequence[Sequence[int]]) -> dict[str, Any]:
    if not cards:
        return {}
    gap_counter: Counter[str] = Counter()
    sequence_counter: Counter[str] = Counter()
    max_gap = 0
    band_totals = Counter({"baixas_01_05": 0, "medias_06_15": 0, "altas_16_25": 0})
    for card in cards:
        metrics = compute_card_structure_metrics(card)
        gap_counter[str(metrics["gaps_entre_dezenas"])] += 1
        sequence_counter[str(metrics["sequencias"])] += 1
        max_gap = max(max_gap, int(metrics["maior_gap"] or 0))
        for key in ("baixas_01_05", "medias_06_15", "altas_16_25"):
            band_totals[key] += int(metrics.get(key, 0) or 0)
    total_cards = len(cards)
    return {
        "distribuicao_baixas_medias_altas": {
            key: round(band_totals[key] / total_cards, 4) for key in band_totals
        },
        "gaps_mais_comuns": [
            {"gaps": key, "frequencia": count}
            for key, count in gap_counter.most_common(5)
        ],
        "maior_gap": max_gap,
        "sequencias_mais_comuns": [
            {"sequencias": key, "frequencia": count}
            for key, count in sequence_counter.most_common(5)
        ],
    }


def _aggregate_absence_patterns(cards: Sequence[Sequence[int]]) -> dict[str, Any]:
    missing_counter: Counter[str] = Counter()
    per_game_missing: Counter[int] = Counter()
    for card in cards:
        missing = compute_missing_dezenas(card)
        for number in missing:
            per_game_missing[number] += 1
        missing_counter[format_dezena_group(missing)] += 1
    return {
        "ausencias_recorrentes_no_GP": [
            {"dezena": f"{number:02d}", "jogos_ausente": count}
            for number, count in per_game_missing.most_common(10)
        ],
        "dezenas_fora_em_muitos_jogos": [
            {"dezena": f"{number:02d}", "jogos_ausente": count}
            for number, count in per_game_missing.most_common(10)
            if count >= max(1, len(cards) // 2)
        ],
        "padroes_ausencia": [
            {"ausencias": key, "frequencia": count}
            for key, count in missing_counter.most_common(5)
        ],
    }


def build_card_structure_payload(
    *,
    games: Sequence[dict[str, Any]],
    official_cards: Sequence[Sequence[int]],
    official_contests: Sequence[int],
    generation_event_ids: Sequence[int],
    reconciliation_run_ids: Sequence[int],
    contest_ids: Sequence[int],
    analysis_batch_labels: Sequence[str] | None = None,
    selected_analysis_batch_label: str | None = None,
    excluded_batches_summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not games:
        return empty_card_structure_payload()

    resolved_cards = [resolve_cartao_final_from_game(game) for game in games]
    resolved_cards = [card for card in resolved_cards if card]
    if not resolved_cards:
        return empty_card_structure_payload()

    formats = sorted({len(card) for card in resolved_cards})
    total_geracoes = len(set(int(value) for value in generation_event_ids if int(value) > 0))
    total_concursos = len(set(int(value) for value in contest_ids if int(value) > 0))
    evidence_level = resolve_evidence_level(
        total_geracoes=total_geracoes,
        total_concursos=total_concursos,
    )
    abertura, fechamento = _aggregate_opening_closing(resolved_cards)
    faixas_gaps = _aggregate_faixas_gaps(resolved_cards)
    redundancia = compute_gp_redundancy(resolved_cards)
    redundancia_por_formato: dict[str, Any] = {}
    for fmt in formats:
        cards_fmt = [card for card in resolved_cards if len(card) == int(fmt)]
        if len(cards_fmt) >= 2:
            redundancia_por_formato[str(int(fmt))] = compute_gp_redundancy(cards_fmt)
    ausencias = _aggregate_absence_patterns(resolved_cards)
    comparacao = compare_structure_profiles(resolved_cards, official_cards)
    comparacao["comparacao_com_concursos_oficiais"] = {
        "total_concursos_oficiais": len(official_contests),
        "janela_oficial": DEFAULT_OFFICIAL_WINDOW,
    }
    abertura["comparacao_com_concursos_oficiais"] = comparacao.get("prefixo_3")
    abertura["comparacao_com_concursos_oficiais_prefixo_4"] = comparacao.get("prefixo_4")
    fechamento["comparacao_com_concursos_oficiais"] = comparacao.get("sufixo_3")
    fechamento["comparacao_com_concursos_oficiais_sufixo_4"] = comparacao.get("sufixo_4")

    official_numbers = official_cards[0] if official_cards else []
    travamento = analyze_stuck_games(games, official_numbers=official_numbers)

    evidence_base = {
        "concursos_analisados": sorted(set(int(value) for value in contest_ids if int(value) > 0)),
        "generation_event_ids": sorted(set(int(value) for value in generation_event_ids if int(value) > 0)),
        "reconciliation_run_ids": sorted(set(int(value) for value in reconciliation_run_ids if int(value) > 0)),
        "analysis_batch_label": selected_analysis_batch_label,
        "analysis_batch_labels": sorted(
            {
                str(value).strip()
                for value in (analysis_batch_labels or [])
                if str(value or "").strip()
            }
        ),
        "formatos_analisados": formats,
        "total_concursos": total_concursos,
        "total_geracoes": total_geracoes,
        "total_runs": len(set(int(value) for value in reconciliation_run_ids if int(value) > 0)),
        "evidence_level": evidence_level,
    }

    summary_payload = {
        "total_geracoes": total_geracoes,
        "total_jogos": len(resolved_cards),
        "total_concursos_comparados": len(set(official_contests)),
        "formatos_analisados": formats,
    }
    if selected_analysis_batch_label:
        summary_payload["analysis_batch_label"] = selected_analysis_batch_label

    exclusions = dict(excluded_batches_summary or {})
    payload = {
        "available": True,
        "source": SOURCE_POSTGRESQL,
        "tables": RECONCILIATION_TABLES,
        "operational_effect": False,
        "generation_command": False,
        "recalibration_command": False,
        "ml_role": "diagnostic_only",
        "summary": summary_payload,
        "abertura": abertura,
        "fechamento": fechamento,
        "faixas_gaps": faixas_gaps,
        "travamento_13_14": travamento,
        "redundancia_gp": {**redundancia, **ausencias},
        "redundancia_por_formato": redundancia_por_formato,
        "comparacao_oficial": comparacao,
        "evidence_base": evidence_base,
        "evidence_level": evidence_level,
        "excluded_batches_count": int(exclusions.get("excluded_batches_count", 0) or 0),
        "excluded_batches_message": str(exclusions.get("message", "") or ""),
        "excluded_batches_audit": list(exclusions.get("excluded_batches") or []),
    }
    return payload


def load_card_structure_diagnostics_from_db(
    db_path: Path | str = DEFAULT_DATABASE_PATH,
    *,
    run_limit: int = 500,
    official_window: int = DEFAULT_OFFICIAL_WINDOW,
    analysis_batch_label: str | None = None,
    game_size: int | None = None,
    generation_event_id: int | None = None,
    reconciliation_run_id: int | None = None,
    concurso_analisado: int | None = None,
    active_reading_only: bool = True,
) -> dict[str, Any]:
    """Carrega diagnóstico estrutural a partir das reconciliations persistidas."""
    normalized_batch_label = str(analysis_batch_label or "").strip().upper() or None
    exclusions_summary = summarize_active_reading_exclusions(db_path)
    with get_session(db_path) as session:
        query = session.query(ReconciliationRun)
        if reconciliation_run_id is not None and int(reconciliation_run_id) > 0:
            query = query.filter(ReconciliationRun.id == int(reconciliation_run_id))
        if concurso_analisado is not None and int(concurso_analisado) > 0:
            query = query.filter(ReconciliationRun.contest_id == int(concurso_analisado))
        if generation_event_id is not None and int(generation_event_id) > 0:
            query = query.filter(ReconciliationRun.generation_event_id == int(generation_event_id))
        runs = (
            query.order_by(ReconciliationRun.created_at.desc(), ReconciliationRun.id.desc())
            .limit(max(1, int(run_limit)))
            .all()
        )
        if not runs:
            return empty_card_structure_payload()

        generation_event_cache: dict[int, GenerationEvent | None] = {}

        def _load_generation_event(event_id: int) -> GenerationEvent | None:
            if event_id <= 0:
                return None
            if event_id not in generation_event_cache:
                generation_event_cache[event_id] = (
                    session.query(GenerationEvent).filter(GenerationEvent.id == event_id).one_or_none()
                )
            return generation_event_cache[event_id]

        if normalized_batch_label:
            filtered_runs: list[ReconciliationRun] = []
            for run in runs:
                event_id = int(getattr(run, "generation_event_id", 0) or 0)
                event = _load_generation_event(event_id)
                event_label = str(getattr(event, "analysis_batch_label", "") or "").strip().upper()
                if event_label == normalized_batch_label:
                    filtered_runs.append(run)
            runs = filtered_runs
            if not runs:
                return empty_card_structure_payload()

        expected_batch_game_size = batch_label_game_size(normalized_batch_label) if normalized_batch_label else None
        effective_game_size = int(game_size) if game_size is not None and int(game_size) > 0 else expected_batch_game_size

        games: list[dict[str, Any]] = []
        generation_event_ids: list[int] = []
        reconciliation_run_ids: list[int] = []
        contest_ids: list[int] = []
        batch_labels_seen: set[str] = set()

        for run in runs:
            run_id = int(run.id or 0)
            generation_event_id_value = int(getattr(run, "generation_event_id", 0) or 0)
            if active_reading_only:
                event = _load_generation_event(generation_event_id_value)
                if event is not None and not is_generation_event_active_reading(event):
                    continue
            reconciliation_run_ids.append(run_id)
            if generation_event_id_value > 0:
                generation_event_ids.append(generation_event_id_value)
                event = _load_generation_event(generation_event_id_value)
                event_label = str(getattr(event, "analysis_batch_label", "") or "").strip()
                if event_label:
                    batch_labels_seen.add(event_label)
            contest_id = int(getattr(run, "contest_id", 0) or 0)
            if contest_id > 0:
                contest_ids.append(contest_id)
            rows = (
                session.query(ReconciliationGame)
                .filter(ReconciliationGame.reconciliation_run_id == run.id)
                .order_by(ReconciliationGame.game_index.asc())
                .all()
            )
            official_numbers, _ = resolve_official_numbers_for_contest(session, contest_id)
            for row in rows:
                payload = _serialize_reconciliation_game(row, run_id=run_id)
                payload["hits"] = resolve_reconciliation_game_hits(
                    hits=payload.get("hits"),
                    matched_numbers=payload.get("matched_numbers"),
                    numbers=payload.get("numbers"),
                    official_numbers=official_numbers,
                    prize_tier=payload.get("prize_tier"),
                )
                payload["official_numbers"] = list(official_numbers)
                resolved_card = resolve_cartao_final_from_game(payload)
                if effective_game_size is not None and len(resolved_card) != int(effective_game_size):
                    continue
                games.append(payload)

        official_cards, official_contests = _load_official_cards(session, limit=official_window)

    if not games:
        empty_payload = empty_card_structure_payload()
        empty_payload["excluded_batches_count"] = int(exclusions_summary.get("excluded_batches_count", 0) or 0)
        empty_payload["excluded_batches_message"] = str(exclusions_summary.get("message", "") or "")
        empty_payload["excluded_batches_audit"] = list(exclusions_summary.get("excluded_batches") or [])
        return empty_payload

    return build_card_structure_payload(
        games=games,
        official_cards=official_cards,
        official_contests=official_contests,
        generation_event_ids=generation_event_ids,
        reconciliation_run_ids=reconciliation_run_ids,
        contest_ids=contest_ids,
        analysis_batch_labels=sorted(batch_labels_seen),
        selected_analysis_batch_label=normalized_batch_label,
        excluded_batches_summary=exclusions_summary,
    )


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


def _format_breakdown_from_payload(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    summary = dict(payload.get("summary") or {})
    formats = list(summary.get("formatos_analisados") or [])
    if not formats:
        formats = list((payload.get("evidence_base") or {}).get("formatos_analisados") or [])
    return [{"formato": f"{int(fmt)}D", "jogos": int(summary.get("total_jogos", 0) or 0)} for fmt in sorted(formats)]


def extract_operational_structural_metrics(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Extrai métricas canônicas do payload da Cobertura Estrutural (fonte única M-ML-VIS-059)."""
    redundancy = dict(payload.get("redundancia_gp") or {})
    abertura = dict(payload.get("abertura") or {})
    fechamento = dict(payload.get("fechamento") or {})
    travamento = dict(payload.get("travamento_13_14") or {})
    summary = dict(payload.get("summary") or {})
    evidence_base = dict(payload.get("evidence_base") or {})

    similaridade = _safe_float(redundancy.get("similaridade_media_entre_jogos"))
    sobreposicao_media = _safe_float(redundancy.get("sobreposicao_media"))
    sobreposicao_maxima = _safe_int(redundancy.get("sobreposicao_maxima"))
    quase_repetidos_criticos = _safe_int(
        redundancy.get("quase_repetidos_criticos", redundancy.get("cartoes_quase_repetidos"))
    )
    quase_repetidos = quase_repetidos_criticos
    pares_em_atencao = _safe_int(redundancy.get("pares_em_atencao", redundancy.get("pares_atencao")))
    pares_possiveis = _safe_int(redundancy.get("pares_possiveis", redundancy.get("pair_count")))
    distribuicao_por_overlap = dict(redundancy.get("distribuicao_por_overlap") or {})
    overlap_composition_rows = list(redundancy.get("overlap_composition_rows") or [])
    diversity_score = round(max(0.0, 1.0 - similaridade), 4)
    formatos = [
        int(value)
        for value in list(evidence_base.get("formatos_analisados") or summary.get("formatos_analisados") or [])
    ]
    primary_format_size = int(formatos[0]) if len(formatos) == 1 else 0
    if primary_format_size <= 0 and redundancy.get("game_size"):
        primary_format_size = _safe_int(redundancy.get("game_size"))
    redundancia_por_formato = dict(payload.get("redundancia_por_formato") or {})
    if primary_format_size > 0:
        fmt_redundancy = dict(redundancia_por_formato.get(str(primary_format_size)) or {})
        if fmt_redundancy:
            quase_repetidos_criticos = _safe_int(
                fmt_redundancy.get("quase_repetidos_criticos", fmt_redundancy.get("cartoes_quase_repetidos"))
            )
            quase_repetidos = quase_repetidos_criticos
            pares_em_atencao = _safe_int(fmt_redundancy.get("pares_em_atencao", fmt_redundancy.get("pares_atencao")))
            pares_possiveis = _safe_int(fmt_redundancy.get("pares_possiveis", fmt_redundancy.get("pair_count")))
            distribuicao_por_overlap = dict(fmt_redundancy.get("distribuicao_por_overlap") or distribuicao_por_overlap)
            overlap_composition_rows = list(fmt_redundancy.get("overlap_composition_rows") or overlap_composition_rows)
            similaridade = _safe_float(
                fmt_redundancy.get("similaridade_media_entre_jogos", similaridade)
            )
            sobreposicao_maxima = _safe_int(fmt_redundancy.get("sobreposicao_maxima", sobreposicao_maxima))
            diversity_score = round(max(0.0, 1.0 - similaridade), 4)

    prefix_top = dict(abertura.get("prefixo_3_mais_gerado") or {})
    suffix_top = dict(fechamento.get("sufixo_3_mais_gerado") or {})
    prefix_freq = _safe_int(prefix_top.get("frequencia"))
    suffix_freq = _safe_int(suffix_top.get("frequencia"))
    total_jogos = _safe_int(summary.get("total_jogos"))

    subcovered_rows = list(redundancy.get("dezenas_fora_em_muitos_jogos") or [])
    subcovered_list = [
        str(row.get("dezena") or "")
        for row in subcovered_rows
        if isinstance(row, Mapping) and row.get("dezena")
    ]
    prefix_viciado = prefix_freq >= max(3, int(max(1, total_jogos) * 0.14))
    suffix_viciado = suffix_freq >= max(3, int(max(1, total_jogos) * 0.14))

    hits_13 = len(list(travamento.get("jogos_com_13_hits") or []))
    hits_14 = len(list(travamento.get("jogos_com_14_hits") or []))
    hits_15 = len(list(travamento.get("jogos_com_15_hits") or []))

    redundancia_geral = (
        "alta"
        if quase_repetidos_criticos >= 20 or similaridade >= 0.55 or pares_em_atencao >= 20
        else "normal"
    )

    return {
        "similaridade_media": similaridade,
        "similaridade_media_entre_jogos": similaridade,
        "sobreposicao_media": sobreposicao_media,
        "sobreposicao_maxima": sobreposicao_maxima,
        "quase_repetidos": quase_repetidos,
        "quase_repetidos_criticos": quase_repetidos_criticos,
        "cartoes_quase_repetidos": quase_repetidos_criticos,
        "pares_em_atencao": pares_em_atencao,
        "pares_possiveis": pares_possiveis,
        "distribuicao_por_overlap": distribuicao_por_overlap,
        "overlap_composition_rows": overlap_composition_rows,
        "primary_format_size": primary_format_size,
        "redundancia_geral": redundancia_geral,
        "prefixos_sufixos_viciados": prefix_viciado or suffix_viciado,
        "prefixo_viciado": prefix_viciado,
        "sufixo_viciado": suffix_viciado,
        "prefixo_mais_gerado": str(prefix_top.get("estrutura") or "—"),
        "sufixo_mais_gerado": str(suffix_top.get("estrutura") or "—"),
        "dezenas_subcobertas": len(subcovered_rows),
        "dezenas_subcobertas_list": subcovered_list,
        "diversidade_global": "baixa" if diversity_score < 0.55 else "adequada",
        "diversity_score": diversity_score,
        "desempenho_13_hits": hits_13,
        "desempenho_14_hits": hits_14,
        "desempenho_15_hits": hits_15,
        "total_jogos": total_jogos,
        "total_geracoes": _safe_int(summary.get("total_geracoes")),
        "format_breakdown": _format_breakdown_from_payload(payload),
        "formatos_analisados": [
            int(value)
            for value in list(evidence_base.get("formatos_analisados") or summary.get("formatos_analisados") or [])
        ],
        "generation_event_ids": [
            int(value)
            for value in list(evidence_base.get("generation_event_ids") or [])
            if _safe_int(value) > 0
        ],
        "evidence_level": str(payload.get("evidence_level") or EVIDENCE_LEVEL_LOCAL),
        "six_bases_risco": "alerta" if subcovered_rows or prefix_viciado or suffix_viciado else "estável",
    }


def compute_coverage_snapshot_checksum(payload: Mapping[str, Any]) -> str:
    """Checksum estável do núcleo redundante do payload (rastreio de leitura)."""
    core = {
        "redundancia_gp": dict(payload.get("redundancia_gp") or {}),
        "summary": dict(payload.get("summary") or {}),
        "generation_event_ids": list((payload.get("evidence_base") or {}).get("generation_event_ids") or []),
    }
    encoded = json.dumps(core, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def build_structural_coverage_reading_metadata(
    payload: Mapping[str, Any],
    metrics: Mapping[str, Any],
    *,
    scope_id: str,
    scope_label: str,
    filters: Mapping[str, Any] | None = None,
    read_at: str | None = None,
) -> dict[str, Any]:
    evidence_base = dict(payload.get("evidence_base") or {})
    return {
        "mission_id": MISSION_ID_STRUCTURAL_SNAPSHOT,
        "source": SOURCE_COBERTURA_ESTRUTURAL,
        "tables": str(payload.get("tables") or OPERATIONAL_TABLES),
        "coverage_layer": str(payload.get("coverage_layer") or "operational_core_002"),
        "scope_id": scope_id,
        "scope_label": scope_label,
        "filters": dict(filters or {}),
        "total_geracoes": _safe_int(metrics.get("total_geracoes")),
        "total_jogos": _safe_int(metrics.get("total_jogos")),
        "format_breakdown": list(metrics.get("format_breakdown") or []),
        "generation_event_ids": list(metrics.get("generation_event_ids") or []),
        "formatos_analisados": list(evidence_base.get("formatos_analisados") or []),
        "read_at": read_at or datetime.now(UTC).isoformat(),
        "coverage_snapshot_checksum": compute_coverage_snapshot_checksum(payload),
    }


def compare_structural_coverage_scopes(
    sovereign_ids: Sequence[int],
    alternate_ids: Sequence[int],
) -> dict[str, Any]:
    sovereign = sorted({int(value) for value in sovereign_ids if int(value) > 0})
    alternate = sorted({int(value) for value in alternate_ids if int(value) > 0})
    same_scope = sovereign == alternate
    return {
        "same_scope": same_scope,
        "sovereign_generation_event_ids": sovereign,
        "alternate_generation_event_ids": alternate,
        "scope_mismatch": not same_scope,
        "scope_mismatch_reason": (
            ""
            if same_scope
            else "Central ML usa escopo diferente da Cobertura Estrutural atual"
        ),
    }


def get_structural_coverage_snapshot(
    db_path: Path | str = DEFAULT_DATABASE_PATH,
    *,
    generation_event_id: int | None = None,
    generation_event_ids: Sequence[int] | None = None,
    game_size: int | None = None,
    scope_id: str = SCOPE_ALL_OPERATIONAL_CORE_002,
    scope_label: str = SCOPE_LABEL_ALL_OPERATIONAL,
) -> dict[str, Any]:
    """Fonte soberana compartilhada — Cobertura Estrutural e Central ML (M-ML-VIS-059)."""
    selected_ge_id = int(generation_event_id or 0)
    event_ids = [int(value) for value in (generation_event_ids or []) if int(value) > 0]
    effective_game_size = int(game_size) if game_size is not None and int(game_size) > 0 else None
    filters: dict[str, Any] = {
        "generation_event_id": selected_ge_id if selected_ge_id > 0 else None,
        "generation_event_ids": event_ids,
        "game_size": effective_game_size,
    }
    structural = load_operational_card_structure_diagnostics_from_db(
        db_path,
        generation_event_id=selected_ge_id if selected_ge_id > 0 else None,
        generation_event_ids=event_ids or None,
        game_size=effective_game_size,
    )
    if not structural.get("available"):
        return {
            "available": False,
            "mission_id": MISSION_ID_STRUCTURAL_SNAPSHOT,
            "source": SOURCE_COBERTURA_ESTRUTURAL,
            "scope_id": scope_id,
            "scope_label": scope_label,
            "filters": filters,
            "metrics": {},
            "payload": {},
            "reading": {},
        }

    metrics = extract_operational_structural_metrics(structural)
    read_at = datetime.now(UTC).isoformat()
    reading = build_structural_coverage_reading_metadata(
        structural,
        metrics,
        scope_id=scope_id,
        scope_label=scope_label,
        filters=filters,
        read_at=read_at,
    )
    return {
        "available": True,
        "mission_id": MISSION_ID_STRUCTURAL_SNAPSHOT,
        "source": SOURCE_COBERTURA_ESTRUTURAL,
        "scope_id": scope_id,
        "scope_label": scope_label,
        "filters": filters,
        "tables": structural.get("tables"),
        "coverage_layer": structural.get("coverage_layer"),
        "payload": dict(structural),
        "metrics": metrics,
        "reading": reading,
        "coverage_snapshot_checksum": reading.get("coverage_snapshot_checksum"),
        "read_at": read_at,
        "generation_event_ids": list(metrics.get("generation_event_ids") or []),
    }
