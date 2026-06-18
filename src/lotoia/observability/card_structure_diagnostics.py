"""Diagnóstico observacional de cobertura estrutural do cartão (PostgreSQL only)."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from lotoia.database.database import (
    DEFAULT_DATABASE_PATH,
    GenerationEvent,
    LotofacilOfficialHistory,
    ReconciliationGame,
    ReconciliationRun,
    get_session,
)
from lotoia.governance.analysis_batch_labels import batch_label_game_size
from lotoia.governance.batch_operational_scope import (
    is_generation_event_active_reading,
    summarize_active_reading_exclusions,
)
from lotoia.observability.hb_metrics import resolve_official_numbers_for_contest, resolve_reconciliation_game_hits
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
DEFAULT_OFFICIAL_WINDOW = 50
EVIDENCE_LEVEL_LOCAL = "LOCAL_DIAGNOSTIC"
EVIDENCE_LEVEL_STRUCTURAL_RECURRENT = "STRUCTURAL_RECURRENT_DIAGNOSTIC"
MIN_GENERATIONS_RECURRENT = 20
MIN_CONTESTS_RECURRENT = 5


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
