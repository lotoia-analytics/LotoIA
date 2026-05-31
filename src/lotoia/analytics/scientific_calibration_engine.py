from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from statistics import mean
from typing import Any, Mapping, Sequence

from sqlalchemy import select

from lotoia.analytics.lotofacil_scientific_core import (
    LotofacilScientificCore,
    get_scientific_generation_policy,
)
from lotoia.database.database import (
    DEFAULT_DATABASE_PATH,
    GenerationEvent,
    GeneratedGame,
    ImportedContest,
    InstitutionalOutputSignature,
    ReconciliationGame,
    ReconciliationRun,
    ScientificCalibrationDecision,
    get_session,
)
from lotoia.governance.output_commander import (
    load_batch_output_signatures,
    output_commander_validate_games,
)
from lotoia.governance.scientific_commander import validate_scientific_batch

__all__ = [
    "ScientificCalibrationContext",
    "ScientificCalibrationDecisionPayload",
    "build_calibration_context",
    "evaluate_last_batch",
    "generate_recalibration_policy",
    "recommend_next_strategy",
    "apply_supervised_calibration",
    "register_calibration_decision",
]


def _safe_int(value: Any, default: int | None = None) -> int | None:
    if value is None:
        return default
    try:
        if isinstance(value, str):
            value = value.strip()
            if value in {"", "-", "None", "nan", "NaN"}:
                return default
        return int(float(value))
    except Exception:
        return default


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        text = str(value).strip()
    except Exception:
        return default
    return text or default


def _normalize_numbers(raw_numbers: Any) -> list[int]:
    numbers: list[int] = []
    if raw_numbers is None:
        return numbers
    if isinstance(raw_numbers, Mapping):
        raw_numbers = raw_numbers.get("numbers", raw_numbers.get("dezenas", []))
    if isinstance(raw_numbers, str):
        raw_numbers = raw_numbers.replace(",", " ").split()
    if not isinstance(raw_numbers, Sequence) or isinstance(raw_numbers, (str, bytes)):
        return numbers
    for item in raw_numbers:
        number = _safe_int(item, default=None)
        if number is None or not 1 <= number <= 25:
            continue
        if number not in numbers:
            numbers.append(number)
    return sorted(numbers)


def _latest_batch_id(db_path: Any = DEFAULT_DATABASE_PATH) -> str:
    with get_session(db_path) as session:
        row = (
            session.query(InstitutionalOutputSignature.batch_id)
            .order_by(InstitutionalOutputSignature.created_at.desc(), InstitutionalOutputSignature.id.desc())
            .first()
        )
    return _safe_str(row[0] if row else "")


def _load_batch_games(batch_id: str | None, db_path: Any = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    resolved_batch_id = _safe_str(batch_id)
    if not resolved_batch_id:
        return []
    with get_session(db_path) as session:
        rows = (
            session.query(InstitutionalOutputSignature)
            .filter(InstitutionalOutputSignature.batch_id == resolved_batch_id)
            .order_by(InstitutionalOutputSignature.created_at.asc(), InstitutionalOutputSignature.id.asc())
            .all()
        )
    games: list[dict[str, Any]] = []
    for row in rows:
        payload = dict(getattr(row, "payload", {}) or {})
        games.append(
            {
                "game_index": int(payload.get("game_index", len(games) + 1) or len(games) + 1),
                "numbers": _normalize_numbers(payload.get("numbers", [])),
                "game_signature": _safe_str(getattr(row, "game_signature", "")),
                "batch_id": resolved_batch_id,
                "generation_event_id": int(getattr(row, "generation_event_id", 0) or 0),
                "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else "",
                "source": _safe_str(payload.get("source", "institutional_app"), "institutional_app"),
            }
        )
    return games


def _load_latest_generation_rows(db_path: Any = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    with get_session(db_path) as session:
        row = (
            session.query(GenerationEvent)
            .order_by(GenerationEvent.created_at.desc(), GenerationEvent.id.desc())
            .first()
        )
        if row is None:
            return []
        games = (
            session.query(GeneratedGame)
            .filter(GeneratedGame.generation_event_id == int(row.id))
            .order_by(GeneratedGame.game_index.asc())
            .all()
        )
    return [
        {
            "generation_event_id": int(row.id),
            "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else "",
            "seed": int(getattr(row, "seed", 0) or 0),
            "strategy": _safe_str(getattr(row, "strategy", "")),
            "total_games": len(games),
            "games": [
                {
                    "game_index": int(game.game_index),
                    "numbers": list(game.numbers or []),
                    "profile_type": _safe_str(getattr(game, "profile_type", "")),
                    "target_contest": int(getattr(game, "target_contest", 0) or 0) if getattr(game, "target_contest", None) is not None else None,
                }
                for game in games
            ],
        }
    ]


def _load_latest_reconciliation_summary(db_path: Any = DEFAULT_DATABASE_PATH) -> dict[str, Any] | None:
    with get_session(db_path) as session:
        run = (
            session.query(ReconciliationRun)
            .order_by(ReconciliationRun.created_at.desc(), ReconciliationRun.id.desc())
            .first()
        )
        if run is None:
            return None
        games_rows = (
            session.query(ReconciliationGame)
            .filter(ReconciliationGame.reconciliation_run_id == run.id)
            .order_by(ReconciliationGame.game_index.asc())
            .all()
        )
    hit_counts: Counter[int] = Counter()
    for row in games_rows:
        hit_counts[int(getattr(row, "hits", 0) or 0)] += 1
    return {
        "id": int(run.id),
        "generation_event_id": int(getattr(run, "generation_event_id", 0) or 0),
        "contest_id": int(getattr(run, "contest_id", 0) or 0),
        "status": _safe_str(getattr(run, "status", "")),
        "best_hits": int(getattr(run, "best_hits", 0) or 0),
        "total_hits": int(getattr(run, "total_hits", 0) or 0),
        "prize_count": int(getattr(run, "prize_count", 0) or 0),
        "games_count": len(games_rows),
        "hit_distribution": {str(hit): int(count) for hit, count in sorted(hit_counts.items())},
        "created_at": run.created_at.isoformat() if getattr(run, "created_at", None) else "",
    }


def _load_institutional_counts(db_path: Any = DEFAULT_DATABASE_PATH) -> dict[str, int]:
    with get_session(db_path) as session:
        generation_events = session.query(GenerationEvent).count()
        generated_games = session.query(GeneratedGame).count()
        reconciliation_runs = session.query(ReconciliationRun).count()
        reconciliation_games = session.query(ReconciliationGame).count()
        institutional_output_signatures = session.query(InstitutionalOutputSignature).count()
        imported_contests = session.query(ImportedContest).count()
    return {
        "generation_events": int(generation_events),
        "generated_games": int(generated_games),
        "reconciliation_runs": int(reconciliation_runs),
        "reconciliation_games": int(reconciliation_games),
        "institutional_output_signatures": int(institutional_output_signatures),
        "imported_contests": int(imported_contests),
    }


def _build_source_generation_range(games: Sequence[Mapping[str, Any]] | Sequence[dict[str, Any]]) -> dict[str, Any]:
    generation_event_ids = sorted(
        {
            int(_safe_int(item.get("generation_event_id"), default=0) or 0)
            for item in games
            if int(_safe_int(item.get("generation_event_id"), default=0) or 0) > 0
        }
    )
    game_indices = sorted(
        {
            int(_safe_int(item.get("game_index"), default=0) or 0)
            for item in games
            if int(_safe_int(item.get("game_index"), default=0) or 0) > 0
        }
    )
    return {
        "generation_event_ids": generation_event_ids,
        "first_generation_event_id": generation_event_ids[0] if generation_event_ids else None,
        "last_generation_event_id": generation_event_ids[-1] if generation_event_ids else None,
        "first_game_index": game_indices[0] if game_indices else None,
        "last_game_index": game_indices[-1] if game_indices else None,
    }


def _merge_policy(base_policy: Mapping[str, Any], report: Mapping[str, Any]) -> dict[str, Any]:
    policy = dict(base_policy)
    frequency_by_number = {
        int(number): int(amount)
        for number, amount in (report.get("frequency_by_number") or {}).items()
        if str(number).isdigit()
    }
    ordered_numbers = sorted(frequency_by_number.items(), key=lambda item: (-item[1], item[0]))
    core_numbers = [int(number) for number in policy.get("core_numbers", []) or []]
    if not core_numbers:
        core_numbers = [number for number, _ in ordered_numbers[:4]] or [7, 12, 16, 23]
    top_numbers = [number for number, _ in ordered_numbers[:6]]
    discouraged_numbers = [number for number in policy.get("discouraged_numbers", []) or []]
    if not discouraged_numbers:
        discouraged_numbers = [number for number, _ in sorted(frequency_by_number.items(), key=lambda item: (item[1], item[0]))[:6]]

    frequency_caps = {str(number): 0.70 for number in top_numbers[:4]}
    frequency_floors = {str(number): 0.20 for number in core_numbers[:4]}
    if int(policy.get("game_size", 15) or 15) == 15:
        frequency_caps = {str(number): min(0.70, float(policy.get("max_frequency_ratio", 0.70) or 0.70)) for number in top_numbers[:4]}
        frequency_floors = {str(number): max(0.20, float(policy.get("min_frequency_ratio", 0.20) or 0.20)) for number in core_numbers[:4]}

    return {
        "strategy": f"{int(policy.get('game_size', 15) or 15)}_dezenas",
        "game_size": int(policy.get("game_size", 15) or 15),
        "action": "recalibrate_frequency_distribution"
        if str(report.get("classificacao_cientifica", "")).upper().startswith("REPROVADA")
        else "maintain_current_policy",
        "reason": _safe_str(report.get("motivo_cientifico", "")),
        "frequency_caps": frequency_caps,
        "frequency_floors": frequency_floors,
        "keep_rules": {
            "game_size": int(policy.get("game_size", 15) or 15),
            "batch_size": 100,
            "repeat_previous_min": int(policy.get("repeat_min", 7) or 7),
            "repeat_previous_max": int(policy.get("repeat_max", 10) or 10),
            "sequence_max": int(policy.get("sequence_max", 6) or 6),
            "unique_required": True,
        },
        "preferred_parity_pairs": [list(pair) for pair in policy.get("preferred_parity_pairs", []) or []],
        "allowed_parity_pairs": [list(pair) for pair in policy.get("allowed_parity_pairs", []) or []],
        "core_numbers": core_numbers,
        "discouraged_numbers": discouraged_numbers,
        "policy_before": dict(policy),
    }


@dataclass(frozen=True, slots=True)
class ScientificCalibrationContext:
    strategy: str
    game_size: int
    mode: str
    source_batch_id: str
    source_generation_range: dict[str, Any]
    structural_status: str
    scientific_status: str
    classification: str
    main_reason: str
    policy_before: dict[str, Any]
    policy_after: dict[str, Any]
    recommendation: dict[str, Any]
    scientific_report: dict[str, Any]
    structural_report: dict[str, Any]
    historical_profile: dict[str, Any]
    institutional_counts: dict[str, int]
    latest_generation: dict[str, Any]
    latest_reconciliation: dict[str, Any] | None
    latest_contest: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "game_size": self.game_size,
            "mode": self.mode,
            "source_batch_id": self.source_batch_id,
            "source_generation_range": dict(self.source_generation_range),
            "structural_status": self.structural_status,
            "scientific_status": self.scientific_status,
            "classification": self.classification,
            "main_reason": self.main_reason,
            "policy_before": dict(self.policy_before),
            "policy_after": dict(self.policy_after),
            "recommendation": dict(self.recommendation),
            "scientific_report": dict(self.scientific_report),
            "structural_report": dict(self.structural_report),
            "historical_profile": dict(self.historical_profile),
            "institutional_counts": dict(self.institutional_counts),
            "latest_generation": dict(self.latest_generation),
            "latest_reconciliation": dict(self.latest_reconciliation or {}),
            "latest_contest": dict(self.latest_contest),
        }


@dataclass(frozen=True, slots=True)
class ScientificCalibrationDecisionPayload:
    strategy: str
    game_size: int
    source_batch_id: str
    source_generation_range: dict[str, Any]
    structural_status: str
    scientific_status: str
    classification: str
    main_reason: str
    recommended_action: str
    policy_before: dict[str, Any]
    policy_after: dict[str, Any]
    mode: str
    applied: bool
    approved_by: str
    notes: str
    status_visual: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "game_size": self.game_size,
            "source_batch_id": self.source_batch_id,
            "source_generation_range": dict(self.source_generation_range),
            "structural_status": self.structural_status,
            "scientific_status": self.scientific_status,
            "classification": self.classification,
            "main_reason": self.main_reason,
            "recommended_action": self.recommended_action,
            "policy_before": dict(self.policy_before),
            "policy_after": dict(self.policy_after),
            "mode": self.mode,
            "applied": self.applied,
            "approved_by": self.approved_by,
            "notes": self.notes,
            "status_visual": self.status_visual,
        }


def build_calibration_context(
    game_size: int = 15,
    *,
    batch_id: str | None = None,
    mode: str = "OBSERVACAO",
    contests: Sequence[Mapping[str, Any]] | Sequence[dict[str, Any]] | None = None,
    games: Sequence[Mapping[str, Any]] | Sequence[dict[str, Any]] | None = None,
    reference_contests: Sequence[Mapping[str, Any]] | Sequence[dict[str, Any]] | None = None,
    policy_before: Mapping[str, Any] | None = None,
    db_path: Any = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    core = LotofacilScientificCore(contests=contests, db_path=db_path)
    resolved_game_size = int(game_size or 15)
    resolved_batch_id = _safe_str(batch_id) or _latest_batch_id(db_path)
    loaded_games = list(games or [])
    if not loaded_games and resolved_batch_id:
        loaded_games = _load_batch_games(resolved_batch_id, db_path)
    if not reference_contests:
        reference_contests = core.contests[-10:] if core.contests else []
    base_policy = dict(policy_before or get_scientific_generation_policy(resolved_game_size, contests=core.contests if core.contests else None))
    scientific_report = validate_scientific_batch(
        loaded_games,
        reference_contests,
        resolved_game_size,
        base_policy,
        batch_id=resolved_batch_id,
    )
    structural_report = output_commander_validate_games(
        loaded_games,
        batch_id=resolved_batch_id or "scientific-calibration",
        target_size=resolved_game_size,
        required_total=len(loaded_games),
        candidate_total=len(loaded_games),
        db_path=db_path,
        persisted_signatures=load_batch_output_signatures(resolved_batch_id, db_path) if resolved_batch_id else set(),
    ) if loaded_games else {
        "status_comandante_saida": "REPROVADO",
        "quantidade_jogos_solicitada": 0,
        "quantidade_jogos_gerados": 0,
        "quantidade_jogos_unicos": 0,
        "quantidade_jogos_duplicados": 0,
    }
    recommendation = _merge_policy(base_policy, scientific_report)
    policy_after = dict(recommendation)
    latest_generation_rows = _load_latest_generation_rows(db_path)
    latest_generation = latest_generation_rows[0] if latest_generation_rows else {}
    latest_reconciliation = _load_latest_reconciliation_summary(db_path)
    latest_contest = core.contests[-1] if core.contests else {}
    counts = _load_institutional_counts(db_path)
    source_generation_range = _build_source_generation_range(loaded_games)
    calibration_context = ScientificCalibrationContext(
        strategy=f"{resolved_game_size}_dezenas",
        game_size=resolved_game_size,
        mode=_safe_str(mode, "OBSERVACAO"),
        source_batch_id=resolved_batch_id or "scientific-global",
        source_generation_range=source_generation_range,
        structural_status=_safe_str(structural_report.get("status_comandante_saida"), "REPROVADO"),
        scientific_status=_safe_str(scientific_report.get("status_comandante_cientifico"), "REPROVADO"),
        classification=_safe_str(scientific_report.get("classificacao_cientifica"), "REPROVADA"),
        main_reason=_safe_str(scientific_report.get("motivo_cientifico"), ""),
        policy_before=base_policy,
        policy_after=policy_after,
        recommendation=recommendation,
        scientific_report=dict(scientific_report),
        structural_report=dict(structural_report),
        historical_profile=dict(core.build_scientific_profile(window_size=min(100, max(20, resolved_game_size * 4))) if core.contests else {}),
        institutional_counts=counts,
        latest_generation=latest_generation,
        latest_reconciliation=latest_reconciliation,
        latest_contest=dict(latest_contest),
    )
    return calibration_context.as_dict()


def evaluate_last_batch(
    game_size: int = 15,
    *,
    batch_id: str | None = None,
    mode: str = "OBSERVACAO",
    contests: Sequence[Mapping[str, Any]] | Sequence[dict[str, Any]] | None = None,
    games: Sequence[Mapping[str, Any]] | Sequence[dict[str, Any]] | None = None,
    reference_contests: Sequence[Mapping[str, Any]] | Sequence[dict[str, Any]] | None = None,
    policy_before: Mapping[str, Any] | None = None,
    db_path: Any = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    return build_calibration_context(
        game_size,
        batch_id=batch_id,
        mode=mode,
        contests=contests,
        games=games,
        reference_contests=reference_contests,
        policy_before=policy_before,
        db_path=db_path,
    )


def generate_recalibration_policy(context: Mapping[str, Any]) -> dict[str, Any]:
    return dict(context.get("policy_after") or context.get("recommendation") or {})


def recommend_next_strategy(context: Mapping[str, Any]) -> dict[str, Any]:
    recommendation = dict(context.get("recommendation") or {})
    return {
        "strategy": _safe_str(context.get("strategy"), f"{int(context.get('game_size', 15) or 15)}_dezenas"),
        "game_size": int(context.get("game_size", 15) or 15),
        "mode": _safe_str(context.get("mode"), "OBSERVACAO"),
        "source_batch_id": _safe_str(context.get("source_batch_id"), "scientific-global"),
        "structural_status": _safe_str(context.get("structural_status"), "REPROVADO"),
        "scientific_status": _safe_str(context.get("scientific_status"), "REPROVADO"),
        "classification": _safe_str(context.get("classification"), "REPROVADA"),
        "main_reason": _safe_str(context.get("main_reason"), ""),
        "action_suggested": _safe_str(recommendation.get("action"), "maintain_current_policy"),
        "recommended_policy": dict(recommendation),
        "status_visual": "APROVADO" if _safe_str(context.get("scientific_status"), "").upper() == "APROVADO" else "REPROVADO",
        "analysis": {
            "11_plus": int((context.get("scientific_report") or {}).get("count_11_plus", 0) or 0),
            "12_plus": int((context.get("scientific_report") or {}).get("count_12_plus", 0) or 0),
            "best_hits": int((context.get("scientific_report") or {}).get("best_hits", 0) or 0),
            "total_jogos_unicos": int((context.get("scientific_report") or {}).get("total_jogos_unicos", 0) or 0),
            "total_jogos_duplicados": int((context.get("scientific_report") or {}).get("total_jogos_duplicados", 0) or 0),
        },
    }


def apply_supervised_calibration(
    context: Mapping[str, Any],
    *,
    approved_by: str = "",
    notes: str = "",
    auto_apply: bool = False,
) -> dict[str, Any]:
    recommendation = recommend_next_strategy(context)
    applied = bool(auto_apply and recommendation["status_visual"] == "APROVADO")
    return ScientificCalibrationDecisionPayload(
        strategy=_safe_str(recommendation.get("strategy"), "15_dezenas"),
        game_size=int(recommendation.get("game_size", 15) or 15),
        source_batch_id=_safe_str(recommendation.get("source_batch_id"), "scientific-global"),
        source_generation_range=dict(context.get("source_generation_range") or {}),
        structural_status=_safe_str(recommendation.get("structural_status"), "REPROVADO"),
        scientific_status=_safe_str(recommendation.get("scientific_status"), "REPROVADO"),
        classification=_safe_str(recommendation.get("classification"), "REPROVADA"),
        main_reason=_safe_str(recommendation.get("main_reason"), ""),
        recommended_action=_safe_str(recommendation.get("action_suggested"), "maintain_current_policy"),
        policy_before=dict(context.get("policy_before") or {}),
        policy_after=dict(recommendation.get("recommended_policy") or {}),
        mode=_safe_str(context.get("mode"), "OBSERVACAO"),
        applied=applied,
        approved_by=_safe_str(approved_by),
        notes=_safe_str(notes),
        status_visual=_safe_str(recommendation.get("status_visual"), "REPROVADO"),
    ).as_dict()


def register_calibration_decision(
    context: Mapping[str, Any],
    decision: Mapping[str, Any] | None = None,
    *,
    db_path: Any = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    payload = dict(decision or apply_supervised_calibration(context))
    batch_id = _safe_str(payload.get("source_batch_id"), _safe_str(context.get("source_batch_id"), "scientific-global"))
    mode = _safe_str(payload.get("mode"), _safe_str(context.get("mode"), "OBSERVACAO"))
    with get_session(db_path) as session:
        row = (
            session.query(ScientificCalibrationDecision)
            .filter(
                ScientificCalibrationDecision.source_batch_id == batch_id,
                ScientificCalibrationDecision.mode == mode,
            )
            .order_by(
                ScientificCalibrationDecision.created_at.desc(),
                ScientificCalibrationDecision.id.desc(),
            )
            .first()
        )
        if row is None:
            row = ScientificCalibrationDecision(
                strategy=_safe_str(payload.get("strategy"), "15_dezenas"),
                game_size=int(payload.get("game_size", context.get("game_size", 15)) or 15),
                source_batch_id=batch_id,
                source_generation_range=dict(payload.get("source_generation_range") or context.get("source_generation_range") or {}),
                structural_status=_safe_str(payload.get("structural_status"), "REPROVADO"),
                scientific_status=_safe_str(payload.get("scientific_status"), "REPROVADO"),
                classification=_safe_str(payload.get("classification"), "REPROVADA"),
                main_reason=_safe_str(payload.get("main_reason"), ""),
                recommended_action=_safe_str(payload.get("recommended_action"), "maintain_current_policy"),
                policy_before=dict(payload.get("policy_before") or context.get("policy_before") or {}),
                policy_after=dict(payload.get("policy_after") or context.get("policy_after") or {}),
                mode=mode,
                applied=1 if bool(payload.get("applied")) else 0,
                approved_by=_safe_str(payload.get("approved_by"), ""),
                notes=_safe_str(payload.get("notes"), ""),
            )
            session.add(row)
        else:
            row.strategy = _safe_str(payload.get("strategy"), row.strategy)
            row.game_size = int(payload.get("game_size", row.game_size) or row.game_size)
            row.source_generation_range = dict(payload.get("source_generation_range") or row.source_generation_range or {})
            row.structural_status = _safe_str(payload.get("structural_status"), row.structural_status)
            row.scientific_status = _safe_str(payload.get("scientific_status"), row.scientific_status)
            row.classification = _safe_str(payload.get("classification"), row.classification)
            row.main_reason = _safe_str(payload.get("main_reason"), row.main_reason)
            row.recommended_action = _safe_str(payload.get("recommended_action"), row.recommended_action)
            row.policy_before = dict(payload.get("policy_before") or row.policy_before or {})
            row.policy_after = dict(payload.get("policy_after") or row.policy_after or {})
            row.applied = 1 if bool(payload.get("applied")) else 0
            row.approved_by = _safe_str(payload.get("approved_by"), row.approved_by)
            row.notes = _safe_str(payload.get("notes"), row.notes)
        session.commit()
        session.refresh(row)
    return {
        "id": int(row.id),
        "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else "",
        "strategy": row.strategy,
        "game_size": int(row.game_size),
        "source_batch_id": row.source_batch_id,
        "source_generation_range": dict(row.source_generation_range or {}),
        "structural_status": row.structural_status,
        "scientific_status": row.scientific_status,
        "classification": row.classification,
        "main_reason": row.main_reason,
        "recommended_action": row.recommended_action,
        "policy_before": dict(row.policy_before or {}),
        "policy_after": dict(row.policy_after or {}),
        "mode": row.mode,
        "applied": bool(row.applied),
        "approved_by": row.approved_by,
        "notes": row.notes,
    }
