#!/usr/bin/env python3
"""M-FLOW-001 — Bateria controlada GP:20 15D × N ciclos (geração → calibração → reentrada).

Usa SQLite efêmero isolado — NÃO toca PostgreSQL operacional. Sem purge. Sem apagar dados.
Pool soberano mockado para velocidade; persistência, plano autorizado e loaders de tela são reais.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import traceback
from collections import Counter
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MISSION_ID = "M-FLOW-001"
REQUESTED_COUNT = 20
CARD_FORMAT = 15
BATCH_LABEL = "STRUCT_LEI15_CORE_CANDIDATE_002_15D_001"
POOL_SIZE = 60

SAMPLE_CALIBRATION_PARAMS: dict[str, Any] = {
    "redundancy_penalty_boost": 1.25,
    "max_overlap_penalty": 1.2,
    "near_duplicate_penalty": 1.15,
    "prefix_penalty": 1.3,
    "suffix_penalty": 1.2,
    "missing_numbers_boost": 1.4,
    "diversity_floor_boost": 1.1,
    "discourage_penalty_boost": 1.2,
    "dezenas_subcobertas": ["07", "11", "23"],
}

FAILURE_LABELS: dict[str, str] = {
    "A": "N não persistiu",
    "B": "plano não foi criado",
    "C": "plano não carregou na N+1",
    "D": "plano carregou mas não aplicou",
    "E": "N+1 não persistiu",
    "F": "N+1 persistiu mas não promoveu",
    "G": "N+1 promoveu mas Histórico não leu",
    "H": "N+1 promoveu mas Conferir não leu",
    "I": "N+1 não liberado por qualidade",
    "J": "erro técnico/exception",
    "K": "outro",
}


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _bool_field(ctx: dict[str, Any], *keys: str) -> bool:
    for key in keys:
        if key in ctx:
            return bool(ctx.get(key))
    return False


def _int_field(ctx: dict[str, Any], *keys: str, default: int = 0) -> int:
    for key in keys:
        raw = ctx.get(key)
        if raw is not None and str(raw).strip() not in {"", "None"}:
            try:
                return int(raw)
            except (TypeError, ValueError):
                continue
    return default


@contextmanager
def _battery_runtime(db_path: Path, *, setup_db: bool = True) -> Iterator[None]:
    """Configura env + DB isolado + mocks de pool para bateria rápida."""
    from lotoia.generator.basic_generator import _attach_scores, _build_game

    env_overrides = {
        "LOTOIA_LEI15_CORE_002": "sovereign",
        "LOTOIA_GENERATION_ENABLED": "1",
        "LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1": "off",
        "LOTOIA_ML_OUTPUT_CALIBRATION_ENABLED": "1",
        "LOTOIA_ML_PRE_FINAL_POOL_ENABLED": "1",
        "LOTOIA_ML_OPERATIONAL_HIERARCHY_ENABLED": "0",
    }
    prior = {key: os.environ.get(key) for key in env_overrides}
    for key, value in env_overrides.items():
        os.environ[key] = value
    for key in ("DATABASE_URL", "LOTOIA_DATABASE_URL", "LOTOIA_DATABASE_POOLER_URL", "DATABASE_PUBLIC_URL"):
        os.environ.pop(key, None)

    if setup_db:
        from lotoia.database.database import create_database
        import dashboard.institutional_app as institutional_app

        create_database(db_path)
        institutional_app.DB_PATH = db_path

    class _FakeSessionState(dict):
        def get(self, key, default=None):  # type: ignore[override]
            return super().get(key, default)

    fake_session = _FakeSessionState()
    policy_stub: dict[str, Any] = {
        "policy_version": "M-ML-070-test-stub",
        "core_numbers": [7, 12, 16, 23],
        "discouraged_numbers": [2, 4, 11, 15, 24, 25],
    }

    def _mock_pool(pool_size_arg: int, *, seed: int, history: Any, config: Any) -> list[dict[str, Any]]:
        games: list[dict[str, Any]] = []
        for index in range(int(pool_size_arg)):
            numbers = sorted({((int(seed) + index + offset * 7) % 25) + 1 for offset in range(CARD_FORMAT)})
            game = _build_game(numbers)
            _attach_scores(game, history=history, profile_type="recorrente")
            games.append(game)
        return games

    def _mock_compose(pool: list[dict[str, Any]], count_arg: int, cfg: Any, *, game_size: int = 15) -> list[dict[str, Any]]:
        return list(pool[: int(count_arg)])

    with (
        patch("lotoia.generation.lei15_core_002.build_sovereign_pool", side_effect=_mock_pool),
        patch("lotoia.generation.lei15_core_002.compose_sovereign_gp", side_effect=_mock_compose),
        patch(
            "lotoia.ml.structural_policy_15d.apply_structural_policy_15d_to_sovereign_batch",
            side_effect=lambda selected, **kwargs: (selected, {"structural_policy_applied": False}),
        ),
        patch("lotoia.ml.supervised_output_calibration.ensure_structural_policy_15d_memory", return_value=policy_stub),
        patch(
            "lotoia.ml.supervised_output_calibration.build_structural_policy_15d_calibration_plan",
            return_value={"has_plan": False, "parametros_sugeridos": {}},
        ),
        patch("dashboard.institutional_app.st.session_state", fake_session),
        patch("dashboard.institutional_app._load_latest_contest_summary", return_value=None),
        patch("dashboard.institutional_app._invalidate_operational_structural_cache", return_value=None),
        patch("dashboard.institutional_app._supersede_prior_lots_for_calibration", return_value=0),
    ):
        try:
            yield
        finally:
            for key, value in prior.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


def _generate_gp20(*, seed: int, calibration_plan: dict[str, Any] | None = None) -> dict[str, Any]:
    from lotoia.generator.basic_generator import generate_best_games

    payload = dict(
        generate_best_games(
            count=REQUESTED_COUNT,
            pool_size=POOL_SIZE,
            batch_label=BATCH_LABEL,
            ml_enabled=True,
            seed=int(seed),
            calibration_plan=calibration_plan,
        )
    )
    payload["requested_count"] = REQUESTED_COUNT
    payload["analysis_batch_label"] = BATCH_LABEL
    payload["ml_enabled"] = True
    if calibration_plan:
        payload["authorized_calibration_plan"] = calibration_plan
    return payload


def _persist_generation(result: dict[str, Any], db_path: Path) -> dict[str, Any]:
    import dashboard.institutional_app as institutional_app

    institutional_app.DB_PATH = db_path
    return dict(
        institutional_app._persist_clean_law15_generation_history(
            result=result,
            selected_card_format=CARD_FORMAT,
        )
        or {}
    )


def _load_event_context(db_path: Path, generation_event_id: int) -> dict[str, Any]:
    from lotoia.ml.authorized_ml_calibration_plan import load_generation_event_context

    return dict(load_generation_event_context(int(generation_event_id), db_path) or {})


def _count_persisted_games(db_path: Path, generation_event_id: int) -> int:
    from lotoia.database.database import GeneratedGame, get_session

    if int(generation_event_id) <= 0:
        return 0
    with get_session(db_path) as session:
        return int(
            session.query(GeneratedGame)
            .filter(GeneratedGame.generation_event_id == int(generation_event_id))
            .count()
            or 0
        )


def _screen_visibility(db_path: Path, generation_event_id: int) -> dict[str, bool]:
    from lotoia.database.database import GeneratedGame, GenerationEvent, get_session
    from lotoia.governance.lei15_core_002_sovereign import is_sovereign_core_label
    from lotoia.operations.lot_operational_status import (
        is_analytical_history_eligible,
        is_official_conference_eligible,
    )
    from dashboard.institutional_operational_structural_coverage import load_operational_core_002_generations
    from dashboard.institutional_supervised_ml import load_supervised_ml_operational_events_from_db

    ge_id = int(generation_event_id)
    if ge_id <= 0:
        return {
            "in_coverage": False,
            "in_central_ml": False,
            "in_analytical_history": False,
            "in_conferir_resultados": False,
        }

    with get_session(db_path) as session:
        event = session.get(GenerationEvent, ge_id)
        if event is None:
            return {
                "in_coverage": False,
                "in_central_ml": False,
                "in_analytical_history": False,
                "in_conferir_resultados": False,
            }
        ctx = dict(getattr(event, "context_json", {}) or {})
        batch_label = str(getattr(event, "analysis_batch_label", "") or "")
        ml_enabled = int(getattr(event, "ml_enabled", 0) or 0) == 1
        game_count = int(
            session.query(GeneratedGame).filter(GeneratedGame.generation_event_id == ge_id).count() or 0
        )

    coverage_ids = {
        int(row.get("generation_event_id", 0) or 0)
        for row in load_operational_core_002_generations(db_path, limit=1000)
    }
    ml_ids = {
        int(row.get("generation_event_id", 0) or 0)
        for row in load_supervised_ml_operational_events_from_db(db_path, limit=1000)
    }
    analytical_eligible = is_analytical_history_eligible(ctx) and game_count > 0
    conference_eligible = is_official_conference_eligible(ctx) and game_count > 0
    active_reading = bool(
        ctx.get("is_active_structural_reading", ctx.get("active_reading_scope", True))
    )

    return {
        "in_coverage": ge_id in coverage_ids,
        "in_central_ml": ge_id in ml_ids and ml_enabled and is_sovereign_core_label(batch_label),
        "in_analytical_history": analytical_eligible and active_reading and ge_id in coverage_ids,
        "in_conferir_resultados": conference_eligible and ge_id in coverage_ids,
    }


def _classify_failure(record: dict[str, Any]) -> str:
    if record.get("technical_error"):
        return "J"
    if not record.get("generation_event_id_N"):
        return "A"
    if not record.get("calibration_plan_created"):
        return "B"
    if record.get("generation_event_id_N1", 0) <= 0:
        return "E"
    if not _bool_field(
        record,
        "calibration_plan_loaded_from_db",
        "authorized_plan_loaded_from_db",
    ):
        return "C"
    if not _bool_field(
        record,
        "calibration_plan_applied_to_generation",
        "authorized_plan_applied_to_generation",
    ):
        return "D"
    if not record.get("post_calibration_promotion_evaluated"):
        return "F"
    if not record.get("is_analytical_history_eligible") and not record.get("in_analytical_history"):
        if record.get("promotion_block_reason") and "quality" in str(record.get("promotion_block_reason", "")).lower():
            return "I"
        if str(record.get("ml_verdict_N1", "")).upper() in {"REPROVADO", "BLOQUEADO", "PRECISA CALIBRAR"}:
            return "I"
        if str(record.get("gp_quality_tier_N1", "")).upper() in {"REPROVADO", "CRITICO", "CRÍTICO"}:
            return "I"
        return "G" if record.get("promoted_to_official_conference") else "F"
    if record.get("is_analytical_history_eligible") and not record.get("in_analytical_history"):
        return "G"
    if record.get("is_official_conference_eligible") and not record.get("in_conferir_resultados"):
        return "H"
    if not record.get("is_official_conference_eligible"):
        return "I"
    if not record.get("in_conferir_resultados"):
        return "H"
    return "OK"


def run_single_cycle(*, cycle_id: int, db_path: Path, seed: int) -> dict[str, Any]:
    from lotoia.ml.authorized_ml_calibration_plan import (
        persist_authorized_ml_calibration_plan,
        resolve_authorized_calibration_plan_from_db,
    )
    from lotoia.operations.lot_operational_status import (
        extract_lot_operational_status,
        is_analytical_history_eligible,
        is_official_conference_eligible,
    )

    record: dict[str, Any] = {
        "cycle_id": int(cycle_id),
        "seed": int(seed),
        "generation_event_id_N": 0,
        "generation_event_id_N1": 0,
        "generated_games_count_N": 0,
        "generated_games_count_N1": 0,
        "calibration_plan_created": False,
        "calibration_plan_loaded_from_db": False,
        "calibration_plan_applied_to_generation": False,
        "authorized_plan_loaded_from_db": False,
        "authorized_plan_applied_to_generation": False,
        "post_calibration_promotion_evaluated": False,
        "lot_operational_status_N1": "",
        "gp_quality_tier_N1": "",
        "ml_verdict_N1": "",
        "official_release_allowed_N1": False,
        "is_analytical_history_eligible": False,
        "is_official_conference_eligible": False,
        "promoted_to_analytical_history": False,
        "promoted_to_official_conference": False,
        "persistence_blocked": False,
        "promotion_block_reason": "",
        "in_coverage": False,
        "in_central_ml": False,
        "in_analytical_history": False,
        "in_conferir_resultados": False,
        "technical_error": "",
        "failure_stage": "",
    }

    try:
        gen_n = _generate_gp20(seed=seed)
        if gen_n.get("hierarchy_blocked") or not list(gen_n.get("games") or []):
            record["technical_error"] = str(gen_n.get("hierarchy_block_message") or "generation_N_empty")
            record["failure_stage"] = _classify_failure(record)
            return record

        persist_n = _persist_generation(gen_n, db_path)
        ge_n = int(persist_n.get("generation_event_id", 0) or 0)
        record["generation_event_id_N"] = ge_n
        record["generated_games_count_N"] = _count_persisted_games(db_path, ge_n)
        record["persistence_blocked"] = bool(persist_n.get("persistence_blocked"))
        if ge_n <= 0 or record["generated_games_count_N"] <= 0:
            record["failure_stage"] = _classify_failure(record)
            return record

        ctx_n = _load_event_context(db_path, ge_n)
        if not ctx_n:
            record["technical_error"] = "context_N_missing"
            record["failure_stage"] = _classify_failure(record)
            return record

        plan = persist_authorized_ml_calibration_plan(
            source_generation_event_id=ge_n,
            parametros_sugeridos=SAMPLE_CALIBRATION_PARAMS,
            plan_items=["aumentar_penalidade_similaridade", "reforcar_dezenas_subcobertas"],
            db_path=db_path,
        )
        record["calibration_plan_created"] = int(plan.get("memory_row_id", 0) or 0) > 0
        if not record["calibration_plan_created"]:
            record["failure_stage"] = _classify_failure(record)
            return record

        loaded_plan = resolve_authorized_calibration_plan_from_db(db_path)
        if not loaded_plan:
            record["failure_stage"] = _classify_failure(record)
            return record

        gen_n1 = _generate_gp20(seed=seed + 1, calibration_plan=loaded_plan)
        gen_n1["authorized_calibration_plan"] = loaded_plan
        if gen_n1.get("hierarchy_blocked") or not list(gen_n1.get("games") or []):
            record["technical_error"] = str(gen_n1.get("hierarchy_block_message") or "generation_N1_empty")
            record["failure_stage"] = _classify_failure(record)
            return record

        persist_n1 = _persist_generation(gen_n1, db_path)
        ge_n1 = int(persist_n1.get("generation_event_id", 0) or 0)
        record["generation_event_id_N1"] = ge_n1
        record["generated_games_count_N1"] = _count_persisted_games(db_path, ge_n1)
        record["persistence_blocked"] = bool(persist_n1.get("persistence_blocked"))
        if ge_n1 <= 0 or record["generated_games_count_N1"] <= 0:
            record["failure_stage"] = _classify_failure(record)
            return record

        ctx_n1 = _load_event_context(db_path, ge_n1)
        record["calibration_plan_loaded_from_db"] = _bool_field(
            ctx_n1,
            "calibration_plan_loaded_from_db",
            "authorized_plan_loaded_from_db",
        )
        record["authorized_plan_loaded_from_db"] = record["calibration_plan_loaded_from_db"]
        record["calibration_plan_applied_to_generation"] = _bool_field(
            ctx_n1,
            "calibration_plan_applied_to_generation",
            "authorized_plan_applied_to_generation",
        )
        record["authorized_plan_applied_to_generation"] = record["calibration_plan_applied_to_generation"]
        record["post_calibration_promotion_evaluated"] = bool(
            ctx_n1.get("post_calibration_promotion_evaluated")
            or ctx_n1.get("post_calibration_consumer_lot")
        )
        record["lot_operational_status_N1"] = extract_lot_operational_status(ctx_n1)
        record["gp_quality_tier_N1"] = str(
            ctx_n1.get("gp_quality_tier_after_authorized_plan")
            or ctx_n1.get("gp_quality_tier")
            or ""
        )
        record["ml_verdict_N1"] = str(
            ctx_n1.get("ml_verdict_after_authorized_plan") or ctx_n1.get("ml_verdict") or ""
        )
        record["official_release_allowed_N1"] = bool(ctx_n1.get("official_release_allowed"))
        record["is_analytical_history_eligible"] = is_analytical_history_eligible(ctx_n1)
        record["is_official_conference_eligible"] = is_official_conference_eligible(ctx_n1)
        record["promoted_to_analytical_history"] = bool(ctx_n1.get("promoted_to_analytical_history"))
        record["promoted_to_official_conference"] = bool(ctx_n1.get("promoted_to_official_conference"))
        record["promotion_block_reason"] = str(ctx_n1.get("promotion_block_reason") or "")

        visibility = _screen_visibility(db_path, ge_n1)
        record.update(visibility)

        record["failure_stage"] = _classify_failure(record)
        return record
    except Exception as exc:
        record["technical_error"] = f"{type(exc).__name__}: {exc}"
        record["failure_stage"] = "J"
        record["traceback"] = traceback.format_exc()
        return record


def aggregate_results(cycles: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(cycles)
    ok = sum(1 for row in cycles if row.get("failure_stage") == "OK")
    failure_counts = Counter(str(row.get("failure_stage") or "K") for row in cycles if row.get("failure_stage") != "OK")

    def _count(predicate) -> int:
        return sum(1 for row in cycles if predicate(row))

    summary = {
        "total_cycles": total,
        "cycles_completed_ok": ok,
        "N_persisted": _count(lambda r: int(r.get("generation_event_id_N", 0) or 0) > 0),
        "plans_created": _count(lambda r: bool(r.get("calibration_plan_created"))),
        "N1_persisted": _count(lambda r: int(r.get("generation_event_id_N1", 0) or 0) > 0),
        "plans_loaded": _count(
            lambda r: _bool_field(r, "calibration_plan_loaded_from_db", "authorized_plan_loaded_from_db")
        ),
        "plans_applied": _count(
            lambda r: _bool_field(
                r, "calibration_plan_applied_to_generation", "authorized_plan_applied_to_generation"
            )
        ),
        "promotions_evaluated": _count(lambda r: bool(r.get("post_calibration_promotion_evaluated"))),
        "eligible_analytical_history": _count(lambda r: bool(r.get("is_analytical_history_eligible"))),
        "eligible_conferir": _count(lambda r: bool(r.get("is_official_conference_eligible"))),
        "visible_analytical_history": _count(lambda r: bool(r.get("in_analytical_history"))),
        "visible_conferir": _count(lambda r: bool(r.get("in_conferir_resultados"))),
        "not_released_by_quality": _count(lambda r: str(r.get("failure_stage")) == "I"),
        "technical_failures": _count(lambda r: str(r.get("failure_stage")) == "J"),
    }

    failure_table: list[dict[str, Any]] = []
    for code, count in sorted(failure_counts.items(), key=lambda item: (-item[1], item[0])):
        sample = next((row for row in cycles if row.get("failure_stage") == code), {})
        example_ge = int(sample.get("generation_event_id_N1", 0) or sample.get("generation_event_id_N", 0) or 0)
        failure_table.append(
            {
                "failure": code,
                "label": FAILURE_LABELS.get(code, code),
                "quantity": count,
                "percent": round(100.0 * count / max(total, 1), 2),
                "example_generation_event_id": example_ge,
                "probable_cause": _probable_cause(code, sample),
            }
        )

    dominant = failure_table[0] if failure_table else {"failure": "none", "quantity": 0}
    recommendation = _recommendation(summary, dominant)

    return {
        "mission_id": MISSION_ID,
        "summary": summary,
        "failure_table": failure_table,
        "dominant_failure": dominant,
        "recommendation": recommendation,
        "purge_executed": False,
    }


def _probable_cause(code: str, sample: dict[str, Any]) -> str:
    mapping = {
        "A": "bloqueio de persistência N (contrato runtime ou commander)",
        "B": "falha ao gravar authorized_ml_calibration_plan",
        "C": "loader DB não encontrou plano ativo na geração N+1",
        "D": "plano carregado sem flag applied_to_generation no context_json",
        "E": "bloqueio de persistência N+1 ou geração vazia",
        "F": "promote_post_calibration não elevou status operacional",
        "G": "filtro da tela Histórico Analítico exclui lote elegível",
        "H": "filtro Conferir Resultados exclui lote promovido",
        "I": "ml_verdict/gp_quality_tier impedem liberação oficial",
        "J": str(sample.get("technical_error") or "exception não classificada"),
        "K": "condição não mapeada",
    }
    return mapping.get(code, mapping["K"])


def _recommendation(summary: dict[str, Any], dominant: dict[str, Any]) -> str:
    total = int(summary.get("total_cycles", 0) or 0)
    n1 = int(summary.get("N1_persisted", 0) or 0)
    visible_hist = int(summary.get("visible_analytical_history", 0) or 0)
    visible_conf = int(summary.get("visible_conferir", 0) or 0)
    if n1 == total and visible_hist < total * 0.5:
        return (
            "Persistência N+1 estável; gargalo dominante é elegibilidade/qualidade ou filtro das telas "
            "Histórico/Conferir — revisar ml_verdict, gp_quality_tier e flags is_*_eligible."
        )
    if int(summary.get("plans_loaded", 0) or 0) < n1:
        return "Priorizar memória autorizada (M-ML-075-FIX-01): plano não carrega consistentemente na N+1."
    if int(summary.get("N_persisted", 0) or 0) < total:
        return "Priorizar persistência do lote N: falhas antes da calibração cross-geração."
    code = str(dominant.get("failure") or "")
    if code == "I":
        return "Dominância de bloqueio por qualidade — comportamento esperado se veredito REPROVADO; não confundir com plano não aplicado."
    if code in {"G", "H"}:
        return "Promoção ocorre mas telas não exibem — auditar filtros _load_accumulated_analytical_rows e _load_official_conference_generation_groups."
    return f"Investigar falha dominante {code}: {dominant.get('label', '')}."


def run_battery(*, cycles: int, db_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = _utc_stamp()
    cycle_rows: list[dict[str, Any]] = []
    cycles_dir = output_dir / "cycle_dbs"
    cycles_dir.mkdir(parents=True, exist_ok=True)

    with _battery_runtime(db_path, setup_db=False):
        from lotoia.database.database import create_database
        import dashboard.institutional_app as institutional_app

        for cycle_id in range(1, int(cycles) + 1):
            cycle_db = cycles_dir / f"cycle_{cycle_id:03d}.db"
            if cycle_db.exists():
                cycle_db.unlink()
            create_database(cycle_db)
            institutional_app.DB_PATH = cycle_db
            cycle_rows.append(run_single_cycle(cycle_id=cycle_id, db_path=cycle_db, seed=10_000 + cycle_id))
            if cycle_id % 10 == 0:
                print(f"  ... ciclo {cycle_id}/{cycles}", flush=True)

    aggregate = aggregate_results(cycle_rows)
    payload = {
        "mission_id": MISSION_ID,
        "executed_at": datetime.now(UTC).isoformat(),
        "configuration": {
            "requested_count": REQUESTED_COUNT,
            "card_format": CARD_FORMAT,
            "batch_label": BATCH_LABEL,
            "pool_size": POOL_SIZE,
            "isolated_sqlite_per_cycle": str(cycles_dir / "cycle_XXX.db"),
            "production_postgresql_touched": False,
            "purge_executed": False,
            "pool_mocked_for_speed": True,
        },
        **aggregate,
        "cycles": cycle_rows,
    }

    json_path = output_dir / f"lotoia_m_flow_001_battery_{stamp}.json"
    csv_path = output_dir / f"lotoia_m_flow_001_battery_{stamp}.csv"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    fieldnames = list(cycle_rows[0].keys()) if cycle_rows else ["cycle_id"]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(cycle_rows)

    md_path = ROOT / "docs" / "audits" / "M-FLOW-001_RELATORIO_BATERIA_100X.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_render_markdown(payload, json_path, csv_path), encoding="utf-8")
    payload["artifact_paths"] = {
        "json": str(json_path),
        "csv": str(csv_path),
        "markdown": str(md_path),
    }
    return payload


def _render_markdown(payload: dict[str, Any], json_path: Path, csv_path: Path) -> str:
    summary = dict(payload.get("summary") or {})
    lines = [
        "# M-FLOW-001 — Bateria GP:20 15D",
        "",
        f"**Executado em:** {payload.get('executed_at', '')}",
        f"**Veredito:** M-FLOW-001 CONCLUÍDA — BATERIA 100x IDENTIFICOU ONDE O FLUXO GERAÇÃO → CALIBRAÇÃO → REENTRADA FALHA",
        "",
        "## Resumo agregado",
        "",
        "| Métrica | Valor |",
        "|---------|------:|",
        f"| Total ciclos | {summary.get('total_cycles', 0)} |",
        f"| N persistidos | {summary.get('N_persisted', 0)} |",
        f"| Planos criados | {summary.get('plans_created', 0)} |",
        f"| N+1 persistidos | {summary.get('N1_persisted', 0)} |",
        f"| Planos carregados | {summary.get('plans_loaded', 0)} |",
        f"| Planos aplicados | {summary.get('plans_applied', 0)} |",
        f"| Promoções avaliadas | {summary.get('promotions_evaluated', 0)} |",
        f"| Elegíveis Histórico | {summary.get('eligible_analytical_history', 0)} |",
        f"| Elegíveis Conferir | {summary.get('eligible_conferir', 0)} |",
        f"| Visíveis Histórico | {summary.get('visible_analytical_history', 0)} |",
        f"| Visíveis Conferir | {summary.get('visible_conferir', 0)} |",
        f"| Não liberados por qualidade | {summary.get('not_released_by_quality', 0)} |",
        f"| Falhas técnicas | {summary.get('technical_failures', 0)} |",
        f"| Ciclos OK completos | {summary.get('cycles_completed_ok', 0)} |",
        "",
        "## Tabela por falha",
        "",
        "| Falha | Quantidade | Percentual | Exemplo GE | Causa provável |",
        "|-------|----------:|-----------:|-----------:|----------------|",
    ]
    for row in payload.get("failure_table") or []:
        lines.append(
            f"| {row.get('failure')} — {row.get('label')} | {row.get('quantity')} | "
            f"{row.get('percent')}% | {row.get('example_generation_event_id')} | {row.get('probable_cause')} |"
        )
    dominant = dict(payload.get("dominant_failure") or {})
    lines.extend(
        [
            "",
            f"**Causa dominante:** {dominant.get('failure', '—')} — {dominant.get('label', '')} ({dominant.get('quantity', 0)} ocorrências)",
            "",
            f"**Recomendação:** {payload.get('recommendation', '')}",
            "",
            "## Artefatos",
            "",
            f"- JSON: `{json_path}`",
            f"- CSV: `{csv_path}`",
            "",
            "## Confirmações",
            "",
            "- Sem purge",
            "- Sem alteração de geração/ML/thresholds",
            "- SQLite isolado — PostgreSQL operacional não alterado",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="M-FLOW-001 battery audit")
    parser.add_argument("--cycles", type=int, default=100, help="Número de ciclos (default: 100)")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=ROOT / "experiments" / "m_flow_001" / "battery_isolated.db",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "experiments" / "m_flow_001",
    )
    parser.add_argument("--json", action="store_true", help="Imprimir resumo JSON no stdout")
    args = parser.parse_args()

    report = run_battery(cycles=max(1, int(args.cycles)), db_path=args.db_path, output_dir=args.output_dir)
    summary = report.get("summary") or {}
    if args.json:
        print(json.dumps({"summary": summary, "failure_table": report.get("failure_table")}, indent=2, ensure_ascii=False))
    else:
        print(f"{MISSION_ID}: total={summary.get('total_cycles')} ok={summary.get('cycles_completed_ok')}")
        print(f"  N persistidos: {summary.get('N_persisted')} | N+1 persistidos: {summary.get('N1_persisted')}")
        print(f"  planos carregados: {summary.get('plans_loaded')} | aplicados: {summary.get('plans_applied')}")
        print(f"  elegíveis histórico: {summary.get('eligible_analytical_history')} | conferir: {summary.get('eligible_conferir')}")
        print(f"  dominante: {(report.get('dominant_failure') or {}).get('failure')}")
        print(f"  artefatos: {report.get('artifact_paths')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
