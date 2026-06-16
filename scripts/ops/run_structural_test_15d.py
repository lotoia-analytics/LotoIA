#!/usr/bin/env python3
"""Executa teste estrutural 15D (STRUCT_TEST_15D) headless no PostgreSQL.

Procedimento:
- últimos N concursos oficiais (default 5)
- 4 gerações G50 (50 jogos) por concurso
- analysis_batch_label=STRUCT_TEST_15D
- reconciliação por concurso
- validação da base da Cobertura Estrutural

Sem efeito operacional: não altera Lei 15, Lei 15A, conferência ou geração.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

BATCH_LABEL = "STRUCT_TEST_15D"
GAMES_PER_GENERATION = 50
DEFAULT_CONTESTS = 5
DEFAULT_GENERATIONS_PER_CONTEST = 4
CARD_FORMAT = 15
OFFICIAL_GROUP = "G50"


def _ensure_layout() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    src = ROOT / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def _load_last_official_contests(limit: int) -> list[dict[str, Any]]:
    from dashboard.institutional_app import _load_official_history_rows

    rows = _load_official_history_rows(limit=limit, descending=True)
    contests = [
        {
            "concurso": int(row.get("concurso", 0) or 0),
            "data": str(row.get("data", "") or ""),
            "dezenas": [
                int(token)
                for token in str(row.get("dezenas_sorteadas", "") or "").split()
                if str(token).strip().lstrip("+").isdigit()
            ],
        }
        for row in rows
        if int(row.get("concurso", 0) or 0) > 0 and len(
            [
                int(token)
                for token in str(row.get("dezenas_sorteadas", "") or "").split()
                if str(token).strip().lstrip("+").isdigit()
            ]
        )
        == 15
    ]
    return sorted(contests, key=lambda item: int(item["concurso"]))


def _history_number_frequency() -> dict[int, int]:
    from lotoia.database.database import LotofacilOfficialHistory, get_session
    from lotoia.statistics.basic import number_frequency

    from dashboard.institutional_app import DB_PATH

    with get_session(DB_PATH) as session:
        rows = (
            session.query(LotofacilOfficialHistory)
            .filter(LotofacilOfficialHistory.is_valid == 1)
            .order_by(LotofacilOfficialHistory.contest_number.asc())
            .all()
        )
    draws: list[list[int]] = []
    for row in rows:
        numbers = [
            int(value)
            for value in str(getattr(row, "numbers", "") or "").replace(",", " ").split()
            if str(value).isdigit()
        ]
        if len(numbers) == 15:
            draws.append(numbers)
    if not draws:
        return {}
    frequencies = number_frequency(draws)
    return {int(number): int(amount) for number, amount in frequencies.items()}


def _generate_g50_batch(
    *,
    contest_number: int,
    run_index: int,
    seed: int,
) -> dict[str, Any]:
    from lotoia.governance.output_commander import load_all_output_signatures, output_commander_validate_games

    from dashboard.institutional_app import (
        _generate_direct_15_games,
        _institutional_generation_policy,
        _official_15_generation_context,
        get_previous_official_contest,
    )

    previous_reference = get_previous_official_contest(int(contest_number))
    if not previous_reference.found or len(previous_reference.numbers or []) != 15:
        raise RuntimeError(
            f"RFE bloqueada para concurso {contest_number}: concurso anterior indisponível ou inválido."
        )

    previous_contest_record = None
    if previous_reference.contest_id:
        from dashboard.institutional_app import get_official_contest

        previous_contest_record = get_official_contest(previous_reference.contest_id)

    latest_numbers = set(int(number) for number in (previous_contest_record or {}).get("dezenas", []) or [])
    policy = _institutional_generation_policy(CARD_FORMAT)
    fill_diagnostics: dict[str, Any] = {}
    batch_number_usage: dict[int, int] = {}
    batch_profile_usage: dict[tuple[int, int], int] = {}
    history_frequency = _history_number_frequency()

    odd_min = 5
    odd_max = 10
    even_min = 5
    even_max = 10
    sequence_max = int(policy.get("sequence_max", 15) or 15)
    coverage_min = float(policy.get("coverage_min", 0.0) or 0.0)
    entropy_min = float(policy.get("entropy_min", 0.0) or 0.0)
    repeat_min = int(policy.get("repeat_min", 0) or 0)
    repeat_max = int(policy.get("repeat_max", 15) or 15)

    games = _generate_direct_15_games(
        total_games=GAMES_PER_GENERATION,
        seed=seed,
        history_frequency=history_frequency,
        latest_numbers=latest_numbers,
        batch_number_usage=batch_number_usage,
        batch_profile_usage=batch_profile_usage,
        batch_total_games=GAMES_PER_GENERATION,
        core_numbers=[int(number) for number in (policy.get("core_numbers", []) or [])],
        discouraged_numbers=[int(number) for number in (policy.get("discouraged_numbers", []) or [])],
        max_frequency_ratio=float(policy.get("max_frequency_ratio", 1.0) or 1.0),
        min_frequency_ratio=float(policy.get("min_frequency_ratio", 0.0) or 0.0),
        preferred_profile_ratios=dict(policy.get("preferred_profile_ratios", {}) or {}),
        odd_min=odd_min,
        odd_max=odd_max,
        even_min=even_min,
        even_max=even_max,
        sequence_max=sequence_max,
        coverage_min=coverage_min,
        entropy_min=entropy_min,
        repeat_min=repeat_min,
        repeat_max=repeat_max,
        preferred_parity_pairs=list(policy.get("preferred_parity_pairs", []) or []),
        allowed_parity_pairs=list(policy.get("allowed_parity_pairs", []) or []),
        fill_diagnostics=fill_diagnostics,
        previous_contest_numbers=list(previous_reference.numbers or []),
    )

    batch_id = f"struct-test-15d-c{contest_number}-r{run_index}-{uuid.uuid4().hex[:8]}"
    commander_report = output_commander_validate_games(
        games,
        batch_id=batch_id,
        generation_event_id=None,
        target_size=CARD_FORMAT,
        required_total=GAMES_PER_GENERATION,
        candidate_total=GAMES_PER_GENERATION,
        persisted_signatures=set(load_all_output_signatures()),
        historical_deduplication_mode="AUDIT_ONLY",
    )

    if (
        commander_report.get("status_comandante_saida") != "APROVADO"
        or len(games) < GAMES_PER_GENERATION
        or fill_diagnostics.get("insufficient_reason")
        in {"RFE_PREVIOUS_CONTEST_NOT_FOUND", "RFE_PREVIOUS_CONTEST_INVALID_NUMBERS"}
    ):
        reason = (
            fill_diagnostics.get("insufficient_reason")
            or commander_report.get("motivo_bloqueio")
            or commander_report.get("error_message")
            or "GENERATION_BLOCKED"
        )
        raise RuntimeError(
            f"Geração bloqueada para concurso {contest_number} run={run_index}: {reason} "
            f"(gerados={len(games)}/{GAMES_PER_GENERATION})"
        )

    official_context = _official_15_generation_context(OFFICIAL_GROUP)
    return {
        "games": games,
        "seed": seed,
        "batch_id": batch_id,
        "target_contest": int(contest_number),
        "contest_number": int(contest_number),
        "run_index": int(run_index),
        "fill_diagnostics": fill_diagnostics,
        "commander_report": commander_report,
        "official_15_context": official_context,
        "rfe_previous_contest_id": previous_reference.contest_id,
        "structural_test_mission": "CREATE_ANALYSIS_BATCH_LABELS",
        "analysis_batch_label": BATCH_LABEL,
        "operational_effect": False,
    }


def _persist_generation(
    *,
    generation_payload: dict[str, Any],
    created_by: str,
) -> dict[str, Any]:
    from lotoia.governance.analysis_batch_labels import build_batch_metadata

    from dashboard.institutional_app import _persist_generation_snapshot

    batch_metadata = build_batch_metadata(
        BATCH_LABEL,
        game_size=CARD_FORMAT,
        created_by=created_by,
        runtime_max_format=20,
    )
    generation_context = {
        **dict(generation_payload.get("official_15_context") or {}),
        **batch_metadata,
        "structural_test_mission": "CREATE_ANALYSIS_BATCH_LABELS",
        "structural_test_contest": int(generation_payload["contest_number"]),
        "structural_test_run_index": int(generation_payload["run_index"]),
        "selected_15_group": OFFICIAL_GROUP,
        "dezenas_per_game": CARD_FORMAT,
        "total_games": GAMES_PER_GENERATION,
        "card_format": CARD_FORMAT,
        "format_cartao": CARD_FORMAT,
        "generation_mode": "STRUCTURAL_TEST_15D_HEADLESS",
        "policy_mode": "STRUCTURAL_TEST_15D_HEADLESS",
        "batch_fill_strategy": "FILL_UNTIL_REQUESTED_QUANTITY",
        "scientific_law_role": "COMMANDER",
        "output_commander_role": "AUDITOR",
        "legacy_calibrator_role": "REMOVED_FROM_RUNTIME",
        "calibration_engine_role": "DISABLED",
        "rfe_previous_contest_id": generation_payload.get("rfe_previous_contest_id"),
        "commander_report": generation_payload.get("commander_report"),
        "fill_diagnostics": generation_payload.get("fill_diagnostics"),
    }
    return _persist_generation_snapshot(
        games=list(generation_payload.get("games") or []),
        seed=int(generation_payload.get("seed", 0) or 0),
        target_contest=int(generation_payload.get("target_contest", 0) or 0),
        batch_id=str(generation_payload.get("batch_id") or ""),
        generation_context=generation_context,
        analysis_batch_label=batch_metadata.get("analysis_batch_label"),
        analysis_batch_type=batch_metadata.get("analysis_batch_type"),
        analysis_batch_created_by=batch_metadata.get("analysis_batch_created_by"),
        analysis_batch_created_at=batch_metadata.get("analysis_batch_created_at"),
    )


def _reconcile_generation(
    *,
    generation_event_id: int,
    games: list[dict[str, Any]],
    contest: dict[str, Any],
) -> dict[str, Any]:
    from dashboard.institutional_app import _compare_games_against_contest

    prepared_games: list[dict[str, Any]] = []
    for index, game in enumerate(games, start=1):
        prepared = dict(game)
        prepared["generation_event_id"] = int(generation_event_id)
        prepared["game_index"] = int(index)
        prepared["formato_cartao"] = CARD_FORMAT
        prepared["card_format"] = CARD_FORMAT
        prepared["selected_card_format"] = CARD_FORMAT
        prepared.setdefault("final_card_numbers", list(prepared.get("numbers", []) or []))
        prepared.setdefault("core_numbers", list(prepared.get("numbers", []) or []))
        prepared_games.append(prepared)

    comparison = _compare_games_against_contest(
        generation_event_id=int(generation_event_id),
        games=prepared_games,
        contest=contest,
    )
    if str(comparison.get("status", "")).lower() == "error":
        raise RuntimeError(
            f"Reconciliação bloqueada para generation_event_id={generation_event_id}: "
            f"{comparison.get('message', comparison.get('persistence_guard_status', 'erro'))}"
        )
    return comparison


def _validate_cobertura_payload(
    payload: dict[str, Any],
    *,
    expected_contests: list[int],
    expected_generations: int,
    expected_games: int,
) -> dict[str, Any]:
    summary = dict(payload.get("summary") or {})
    evidence = dict(payload.get("evidence_base") or {})
    checks = {
        "available": bool(payload.get("available")),
        "total_geracoes": int(summary.get("total_geracoes", 0) or 0) == expected_generations,
        "total_jogos": int(summary.get("total_jogos", 0) or 0) == expected_games,
        "total_concursos": int(evidence.get("total_concursos", 0) or 0) == len(expected_contests),
        "concursos_analisados": sorted(int(value) for value in (evidence.get("concursos_analisados") or []))
        == sorted(expected_contests),
        "generation_event_ids_count": len(evidence.get("generation_event_ids") or []) == expected_generations,
        "reconciliation_run_ids_count": len(evidence.get("reconciliation_run_ids") or []) == expected_generations,
        "analysis_batch_label": str(evidence.get("analysis_batch_label") or summary.get("analysis_batch_label") or "")
        == BATCH_LABEL,
        "formatos_only_15d": list(summary.get("formatos_analisados") or []) == [15],
        "evidence_level": str(payload.get("evidence_level") or "") == "STRUCTURAL_RECURRENT_DIAGNOSTIC",
        "operational_effect_false": payload.get("operational_effect") is False,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "summary": summary,
        "evidence_base": evidence,
        "evidence_level": payload.get("evidence_level"),
    }


def run_structural_test(
    *,
    contest_count: int = DEFAULT_CONTESTS,
    generations_per_contest: int = DEFAULT_GENERATIONS_PER_CONTEST,
    created_by: str = "ops/run_structural_test_15d",
    dry_run: bool = False,
) -> dict[str, Any]:
    _ensure_layout()

    from lotoia.database.database import DEFAULT_DATABASE_PATH
    from lotoia.governance.cloud_runtime_policy import evaluate_cloud_runtime_policy
    from lotoia.observability.card_structure_diagnostics import load_card_structure_diagnostics_from_db

    from dashboard.institutional_app import DB_PATH, get_official_contest

    policy = evaluate_cloud_runtime_policy(DEFAULT_DATABASE_PATH)
    if policy.backend != "postgresql":
        raise RuntimeError("Teste estrutural exige PostgreSQL (Lei No 001). Configure DATABASE_URL.")

    contests = _load_last_official_contests(contest_count)
    if len(contests) < contest_count:
        raise RuntimeError(
            f"Histórico oficial insuficiente: encontrados {len(contests)} concursos válidos, "
            f"necessários {contest_count}."
        )

    expected_total_generations = contest_count * generations_per_contest
    expected_total_games = expected_total_generations * GAMES_PER_GENERATION
    report: dict[str, Any] = {
        "mission_id": "CREATE_ANALYSIS_BATCH_LABELS",
        "batch_label": BATCH_LABEL,
        "card_format": CARD_FORMAT,
        "official_group": OFFICIAL_GROUP,
        "contests": [int(item["concurso"]) for item in contests],
        "generations_per_contest": generations_per_contest,
        "expected_generation_events": expected_total_generations,
        "expected_games": expected_total_games,
        "dry_run": dry_run,
        "started_at": datetime.now(UTC).isoformat(),
        "generation_events": [],
        "reconciliation_runs": [],
        "errors": [],
    }

    if dry_run:
        report["status"] = "DRY_RUN"
        report["message"] = "Pré-validação concluída. Nenhuma geração persistida."
        return report

    base_seed = int(time.time()) % 1_000_000
    for contest in contests:
        contest_number = int(contest["concurso"])
        official_contest = get_official_contest(contest_number)
        if not official_contest:
            raise RuntimeError(f"Concurso oficial {contest_number} não encontrado no PostgreSQL.")

        for run_index in range(1, generations_per_contest + 1):
            seed = base_seed + contest_number * 10 + run_index
            print(
                f"[struct-test] concurso={contest_number} run={run_index}/{generations_per_contest} "
                f"seed={seed} ...",
                flush=True,
            )
            generation_payload = _generate_g50_batch(
                contest_number=contest_number,
                run_index=run_index,
                seed=seed,
            )
            snapshot = _persist_generation(
                generation_payload=generation_payload,
                created_by=created_by,
            )
            generation_event_id = int(snapshot.get("generation_event_id", 0) or 0)
            comparison = _reconcile_generation(
                generation_event_id=generation_event_id,
                games=list(generation_payload.get("games") or []),
                contest=official_contest,
            )
            report["generation_events"].append(
                {
                    "generation_event_id": generation_event_id,
                    "contest_number": contest_number,
                    "run_index": run_index,
                    "games_count": int(snapshot.get("games_count", 0) or 0),
                    "batch_id": snapshot.get("batch_id"),
                    "analysis_batch_label": snapshot.get("analysis_batch_label"),
                }
            )
            report["reconciliation_runs"].append(
                {
                    "generation_event_id": generation_event_id,
                    "reconciliation_run_id": int((comparison.get("reconciliation") or {}).get("id", 0) or 0),
                    "contest_number": contest_number,
                    "best_hits": int(comparison.get("best_hits", 0) or 0),
                    "total_games": int(comparison.get("total_games", 0) or 0),
                    "status": comparison.get("status"),
                }
            )

    diagnostics_payload = load_card_structure_diagnostics_from_db(
        DB_PATH,
        run_limit=max(100, expected_total_generations * 3),
        analysis_batch_label=BATCH_LABEL,
        game_size=CARD_FORMAT,
    )
    validation = _validate_cobertura_payload(
        diagnostics_payload,
        expected_contests=[int(item["concurso"]) for item in contests],
        expected_generations=expected_total_generations,
        expected_games=expected_total_games,
    )
    report["cobertura_estrutural"] = diagnostics_payload
    report["validation"] = validation
    report["finished_at"] = datetime.now(UTC).isoformat()
    report["status"] = validation["status"]
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Rodar teste estrutural 15D (STRUCT_TEST_15D)")
    parser.add_argument("--contests", type=int, default=DEFAULT_CONTESTS)
    parser.add_argument("--generations-per-contest", type=int, default=DEFAULT_GENERATIONS_PER_CONTEST)
    parser.add_argument("--created-by", default="ops/run_structural_test_15d")
    parser.add_argument("--dry-run", action="store_true", help="Valida pré-requisitos sem persistir")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        report = run_structural_test(
            contest_count=max(1, int(args.contests)),
            generations_per_contest=max(1, int(args.generations_per_contest)),
            created_by=str(args.created_by),
            dry_run=bool(args.dry_run),
        )
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        if args.json:
            print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"structural-test-15d: ERROR — {exc}")
        return 1

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"structural-test-15d: {report.get('status', 'UNKNOWN')}")
        if report.get("validation"):
            for key, ok in dict(report["validation"].get("checks") or {}).items():
                print(f"  {'PASS' if ok else 'FAIL'}: {key}")
        if report.get("generation_events"):
            print(f"  generation_events={len(report['generation_events'])}")
        if report.get("reconciliation_runs"):
            print(f"  reconciliation_runs={len(report['reconciliation_runs'])}")

    return 0 if str(report.get("status", "")).upper() in {"PASS", "DRY_RUN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
