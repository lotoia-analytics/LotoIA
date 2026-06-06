from __future__ import annotations

import streamlit as st

from lotoia.analytics.lotofacil_scientific_core import discover_scientific_generation_policy
from lotoia.database.database import (
    GenerationEvent,
    GeneratedGame,
    InstitutionalOutputSignature,
    ScientificInstitutionalMemory,
    create_database,
    get_session,
)
from lotoia.analytics.lotofacil_scientific_core import LotofacilScientificCore
from dashboard.institutional_app import _institutional_generation_policy
from dashboard.institutional_app import _format_scientific_memory_listing
from dashboard.institutional_app import _generation_strategy_display
from dashboard.institutional_app import _compact_small_batch_adjustment
from dashboard.institutional_app import _institutional_source_map
from dashboard.institutional_app import _get_latest_contest
from dashboard.institutional_app import _official_15_policy_status_label
from dashboard.institutional_app import _load_csv_latest_contest_summary
from dashboard.institutional_app import _load_latest_contest_summary
from dashboard.institutional_app import _load_official_sync_contest_summary
from dashboard.institutional_app import _persist_generation_snapshot
from dashboard.institutional_app import _resolve_official_15_calibration_context
from dashboard.institutional_app import _scientific_policy_is_ready
from dashboard.institutional_app import _run_institutional_conference
from dashboard.institutional_app import _scientific_hit_decomposition
from dashboard.institutional_app import _scientific_15_is_official_baseline


def _contest(contest_number: int, numbers: list[int]) -> dict[str, object]:
    return {
        "contest_number": contest_number,
        "numbers": numbers,
        "draw_date": f"2026-05-{contest_number:02d}",
    }


def _game_numbers(hit_count: int) -> list[int]:
    if hit_count == 10:
        return list(range(1, 11)) + list(range(16, 21))
    if hit_count == 9:
        return list(range(1, 10)) + list(range(16, 22))
    return list(range(1, 9)) + list(range(16, 23))


def _build_generation(generation_event_id: int, ten_hit_games: int) -> dict[str, object]:
    games: list[dict[str, object]] = []
    results: list[dict[str, object]] = []
    for index in range(10):
        hit_count = 10 if index < ten_hit_games else 9
        numbers = _game_numbers(hit_count)
        game_signature = f"sig-{generation_event_id}-{index + 1}"
        games.append(
            {
                "game_index": index + 1,
                "numbers": numbers,
                "profile_type": "balanced",
                "perfil": "balanced",
                "game_signature": game_signature,
                "score": 0.75 if hit_count == 10 else 0.50,
            }
        )
        results.append(
            {
                "game_index": index + 1,
                "numbers": numbers,
                "hits": hit_count,
                "matched_numbers": list(range(1, hit_count + 1)),
                "missing_draw_numbers": list(range(hit_count + 1, 16)),
                "extra_numbers": list(range(16, 21)) if hit_count == 10 else list(range(16, 22)),
                "score_original": 0.75 if hit_count == 10 else 0.50,
                "profile_type": "balanced",
                "perfil": "balanced",
                "game_signature": game_signature,
            }
        )

    return {
        "generation_event_id": generation_event_id,
        "batch_id": "batch-351-360",
        "contest_number": 3699,
        "created_at": f"2026-06-01T12:{generation_event_id % 60:02d}:00+00:00",
        "total_games": 10,
        "games": games,
        "results": results,
    }


def test_batch_scientific_memory_is_self_sufficient() -> None:
    contests = [_contest(3699, list(range(1, 16)))]
    generation_results = [
        _build_generation(351, 7),
        _build_generation(352, 1),
        _build_generation(353, 1),
        _build_generation(354, 7),
        _build_generation(355, 1),
        _build_generation(356, 1),
        _build_generation(357, 1),
        _build_generation(358, 1),
        _build_generation(359, 1),
        _build_generation(360, 1),
    ]

    core = LotofacilScientificCore(contests=contests, use_csv_fallback=False)
    payload = core.build_batch_reconciliation_scientific_memory(
        batch_id="batch-351-360",
        contest=contests[0],
        generation_results=generation_results,
        policy_before={"repeat_min": 0, "repeat_max": 15},
        policy_after={"repeat_min": 1, "repeat_max": 14},
    )

    generation_range = dict(payload.get("generation_range") or {})
    cross_validation_summary = dict(payload.get("cross_validation_summary") or {})
    games_with_10_hits = list(cross_validation_summary.get("games_with_10_hits") or [])
    best_generation_details = list(cross_validation_summary.get("best_generation_details") or [])

    assert payload["memory_kind"] == "scientific_batch_reconciliation"
    assert generation_range["generation_event_ids"][:2] == [351, 354]
    assert set(generation_range["generation_event_ids"]) == {351, 352, 353, 354, 355, 356, 357, 358, 359, 360}
    assert generation_range["best_generations"][:2] == [351, 354]
    assert generation_range["total_generations"] == 10
    assert generation_range["total_games_checked"] == 100
    assert generation_range["global_best_hits"] == 10
    assert generation_range["global_count_11_plus"] == 0
    assert generation_range["validation_threshold"] == 11
    assert generation_range["scientific_validation_zone_count"] == 0
    assert generation_range["policy_validation_status"] == "REPROVADO"
    assert generation_range["count_10_exact"] == 22
    assert generation_range["count_11_exact"] == 0
    assert generation_range["count_12_exact"] == 0
    assert generation_range["count_13_exact"] == 0
    assert generation_range["count_14_exact"] == 0
    assert generation_range["count_15_exact"] == 0
    assert generation_range["count_11_plus"] == generation_range["count_11_exact"] + generation_range["count_12_exact"] + generation_range["count_13_exact"] + generation_range["count_14_exact"] + generation_range["count_15_exact"]
    assert generation_range["count_12_plus"] == generation_range["count_12_exact"] + generation_range["count_13_exact"] + generation_range["count_14_exact"] + generation_range["count_15_exact"]
    assert generation_range["hit_histogram"]["10"] == 22
    assert generation_range["classification"] == "STRONG_NEAR_MISS_BATCH"
    assert generation_range["recommended_action"] == "recalibrate_from_strong_near_miss_towards_11_plus_and_15"
    assert best_generation_details
    assert [item["generation_event_id"] for item in best_generation_details[:2]] == [351, 354]
    generation_details = list(cross_validation_summary.get("generation_details") or [])
    assert len(generation_details) == 10
    assert all("games_with_10_hits" in item for item in generation_details)


def test_official_15_policy_status_label_is_exposed() -> None:
    payload = {
        "game_size": 15,
        "policy_validation_status": "VALIDATED_15_POLICY_LEVEL_3",
        "official_15_search_standard": True,
        "validated_target_band": "13_plus_detected",
    }

    assert _official_15_policy_status_label(payload) == (
        "Política 15 validada até nível 13. Ouro 14 e diamante 15 seguem como metas futuras."
    )


def test_official_15_baseline_is_prioritized_over_historical_memory(tmp_path) -> None:
    db_path = tmp_path / "lotoia.db"
    create_database(db_path)

    with get_session(db_path) as session:
        session.add(
            ScientificInstitutionalMemory(
                memory_kind="scientific_batch_reconciliation",
                strategy_name="15 dezenas",
                game_size=15,
                batch_id="batch-351-360",
                generation_range={
                    "batch_id": "batch-351-360",
                    "generation_event_ids": [351, 352, 353, 354, 355, 356, 357, 358, 359, 360],
                    "best_generations": [351, 354],
                    "first_generation_event_id": 351,
                    "last_generation_event_id": 360,
                    "total_generations": 10,
                    "total_games_checked": 100,
                },
                total_games=100,
                unique_games=100,
                duplicate_games=0,
                structural_status="APROVADO",
                scientific_status="APROVADO",
                scientific_classification="STRONG_NEAR_MISS_BATCH",
                main_reason="near_miss_batch",
                recommended_action="recalibrate_from_strong_near_miss_towards_11_plus_and_15",
                policy_applied={"policy_validation_status": "REPROVADO"},
                policy_before={"policy_validation_status": "REPROVADO"},
                policy_after={"policy_validation_status": "REPROVADO"},
                best_hit=10,
                average_hits=10.0,
                count_11_plus=0,
                count_12_plus=0,
                count_13_plus=0,
                count_14_plus=0,
                count_15=0,
                validation_contests=[3699],
                cross_validation_summary={"policy_validation_status": "REPROVADO"},
                decision_mode="OBSERVACAO",
                approved_for_use=0,
                notes="historical memory",
                official_history_count=3699,
                official_history_first_contest=1,
                official_history_last_contest=3699,
                official_history_window=[10, 30, 60],
                source="scientific_reconciliation",
            )
        )
        session.add(
            ScientificInstitutionalMemory(
                memory_kind="scientific_batch_reconciliation",
                strategy_name="15 dezenas",
                game_size=15,
                batch_id="calibration-20260602172948-20a682cd",
                generation_range={
                    "batch_id": "calibration-20260602172948-20a682cd",
                    "contest_number": 3697,
                    "baseline_batch_id": "calibration-20260602172948-20a682cd",
                    "baseline_contest_number": 3697,
                    "policy_validation_status": "VALIDATED_15_POLICY_LEVEL_3",
                    "official_15_search_standard": True,
                    "validated_target_band": "13_plus_detected",
                },
                total_games=50,
                unique_games=50,
                duplicate_games=0,
                structural_status="APROVADO",
                scientific_status="VALIDATED_15_POLICY_LEVEL_3",
                scientific_classification="VALIDATED_15_POLICY_LEVEL_3",
                main_reason="baseline oficial",
                recommended_action="usar baseline oficial validada nível 3 para próxima geração compacta",
                policy_applied={
                    "policy_validation_status": "VALIDATED_15_POLICY_LEVEL_3",
                    "official_15_search_standard": True,
                    "baseline_batch_id": "calibration-20260602172948-20a682cd",
                    "baseline_contest_number": 3697,
                },
                policy_before={},
                policy_after={
                    "policy_validation_status": "VALIDATED_15_POLICY_LEVEL_3",
                    "official_15_search_standard": True,
                    "baseline_batch_id": "calibration-20260602172948-20a682cd",
                    "baseline_contest_number": 3697,
                },
                best_hit=13,
                average_hits=11.14,
                count_11_plus=39,
                count_12_plus=16,
                count_13_plus=3,
                count_14_plus=0,
                count_15=0,
                validation_contests=[3697],
                cross_validation_summary={
                    "policy_validation_status": "VALIDATED_15_POLICY_LEVEL_3",
                    "official_15_search_standard": True,
                },
                decision_mode="OBSERVACAO",
                approved_for_use=1,
                notes="official baseline",
                official_history_count=3697,
                official_history_first_contest=1,
                official_history_last_contest=3697,
                official_history_window=[10, 30, 60],
                source="scientific_calibration",
            )
        )
        session.commit()

    import dashboard.institutional_app as institutional_app

    old_db_path = institutional_app.DB_PATH
    institutional_app.DB_PATH = db_path
    try:
        state, recommendation, technical_payload = _resolve_official_15_calibration_context(
            strategy_size=15,
            scientific_state={
                "mode": "AUTONOMIA SUPERVISIONADA",
                "structural_status": "BLOQUEADO",
                "scientific_status": "STRONG_NEAR_MISS_BATCH",
                "classification": "STRONG_NEAR_MISS_BATCH",
                "main_reason": "recalibrate_from_strong_near_miss_towards_11_plus_and_15",
                "status_visual": "OBSERVAÇÃO",
            },
            scientific_recommendation={
                "action_suggested": "recalibrate_from_strong_near_miss_towards_11_plus_and_15",
                "status_visual": "OBSERVAÇÃO",
            },
            technical_payload={
                "scientific_classification": "STRONG_NEAR_MISS_BATCH",
                "recommended_action": "recalibrate_from_strong_near_miss_towards_11_plus_and_15",
            },
        )
    finally:
        institutional_app.DB_PATH = old_db_path

    assert _scientific_15_is_official_baseline(technical_payload)
    assert state["mode"] == "BASELINE VALIDADA"
    assert state["scientific_status"] == "VALIDATED_15_POLICY_LEVEL_3"
    assert state["classification"] == "VALIDATED_15_POLICY_LEVEL_3"
    assert "Política 15 validada até nível 13" in state["main_reason"]
    assert recommendation["action_suggested"] == "usar baseline oficial validada nível 3 para próxima geração compacta"


def test_scientific_batch_reconciliation_becomes_auxiliary_without_evolution(tmp_path) -> None:
    db_path = tmp_path / "lotoia.db"
    create_database(db_path)

    previous_batch_policy = {
        "repeat_min": 7,
        "repeat_max": 10,
        "preferred_parity_pairs": [[7, 8], [8, 7]],
        "allowed_parity_pairs": [[7, 8], [8, 7]],
        "sequence_max": 6,
        "coverage_min": 0.4,
        "entropy_min": 0.45,
        "max_frequency_ratio": 0.7,
        "min_frequency_ratio": 0.2,
        "policy_origin": "scientific_batch_reconciliation_memory",
        "policy_variant": "batch_near_miss_consolidation",
        "policy_adjustment_reason": "recalibrate_from_strong_near_miss_towards_11_plus_and_15",
    }
    current_batch_policy = {
        "repeat_min": 7,
        "repeat_max": 10,
        "preferred_parity_pairs": [[7, 8], [8, 7]],
        "allowed_parity_pairs": [[7, 8], [8, 7]],
        "sequence_max": 6,
        "coverage_min": 0.4,
        "entropy_min": 0.45,
        "max_frequency_ratio": 0.7,
        "min_frequency_ratio": 0.2,
        "policy_origin": "scientific_batch_reconciliation_memory",
        "policy_variant": "batch_near_miss_consolidation",
        "policy_adjustment_reason": "recalibrate_from_strong_near_miss_towards_11_plus_and_15",
    }
    current_cross_validation_windows = {
        "10": {
            "window_size": 10,
            "contest_numbers": [3685, 3686, 3687, 3688, 3689, 3690, 3691, 3692, 3693, 3694],
            "average_best_hits": 11.6,
            "max_best_hits": 13,
            "total_count_10": 275,
            "total_count_11_plus": 228,
            "total_count_12_plus": 94,
            "total_count_13_plus": 18,
            "total_count_14_plus": 0,
            "total_count_15": 0,
            "count_11_exact": 134,
            "count_12_exact": 76,
            "count_13_exact": 18,
            "count_14_exact": 0,
            "contests_with_11_plus": 7,
            "contests_with_12_plus": 4,
            "contests_with_13_plus": 1,
            "contests_with_14_plus": 0,
            "contests_with_15": 0,
        },
        "30": {
            "window_size": 30,
            "contest_numbers": list(range(3665, 3695)),
            "average_best_hits": 11.5333,
            "max_best_hits": 13,
            "total_count_10": 789,
            "total_count_11_plus": 501,
            "total_count_12_plus": 231,
            "total_count_13_plus": 53,
            "total_count_14_plus": 0,
            "total_count_15": 0,
            "count_11_exact": 270,
            "count_12_exact": 178,
            "count_13_exact": 53,
            "count_14_exact": 0,
            "contests_with_11_plus": 27,
            "contests_with_12_plus": 16,
            "contests_with_13_plus": 5,
            "contests_with_14_plus": 0,
            "contests_with_15": 0,
        },
        "60": {
            "window_size": 60,
            "contest_numbers": list(range(3635, 3695)),
            "average_best_hits": 11.4333,
            "max_best_hits": 13,
            "total_count_10": 1662,
            "total_count_11_plus": 868,
            "total_count_12_plus": 392,
            "total_count_13_plus": 78,
            "total_count_14_plus": 0,
            "total_count_15": 0,
            "count_11_exact": 476,
            "count_12_exact": 314,
            "count_13_exact": 78,
            "count_14_exact": 0,
            "contests_with_11_plus": 53,
            "contests_with_12_plus": 29,
            "contests_with_13_plus": 7,
            "contests_with_14_plus": 0,
            "contests_with_15": 0,
        },
    }
    weak_policy = {
        "repeat_min": 2,
        "repeat_max": 5,
        "preferred_parity_pairs": [[7, 8], [8, 7]],
        "allowed_parity_pairs": [[7, 8], [8, 7]],
        "sequence_max": 5,
        "coverage_min": 0.35,
        "entropy_min": 0.35,
        "max_frequency_ratio": 0.6,
        "min_frequency_ratio": 0.1,
        "policy_origin": "scientific_reconciliation_memory",
        "policy_variant": "recalibrate_from_near_miss_towards_15",
        "policy_adjustment_reason": "recalibrate_from_near_miss_towards_15",
    }

    with get_session(db_path) as session:
        session.add(
            ScientificInstitutionalMemory(
                memory_kind="scientific_batch_reconciliation",
                strategy_name="15 dezenas",
                game_size=15,
                batch_id="batch-previous-13",
                generation_range={
                    "batch_id": "batch-previous-13",
                    "generation_event_ids": [351, 352, 353, 354, 355, 356, 357, 358, 359, 360],
                    "best_generations": [351, 354],
                    "first_generation_event_id": 351,
                    "last_generation_event_id": 360,
                    "total_generations": 10,
                    "total_games_checked": 100,
                    "global_best_hits": 10,
                    "global_count_10": 14,
                    "global_count_11_plus": 0,
                },
                total_games=100,
                unique_games=100,
                duplicate_games=0,
                structural_status="APROVADO",
                scientific_status="APROVADO",
                scientific_classification="STRONG_NEAR_MISS_BATCH",
                main_reason="near_miss_batch",
                recommended_action="recalibrate_from_strong_near_miss_towards_11_plus_and_15",
                policy_applied=dict(previous_batch_policy),
                policy_before=dict(previous_batch_policy),
                policy_after=dict(previous_batch_policy),
                best_hit=10,
                average_hits=10.0,
                count_11_plus=0,
                count_12_plus=0,
                count_13_plus=0,
                count_14_plus=0,
                count_15=0,
                validation_contests=[3699],
                cross_validation_summary={
                    "contest_scope": "BATCH_CONSOLIDATED",
                    "ranking_summary": {
                        "best_generation_event_id": 351,
                        "secondary_generation_event_ids": [354],
                        "best_generations": [351, 354],
                        "total_generations": 10,
                        "total_games_checked": 100,
                        "global_best_hits": 10,
                        "global_count_10": 14,
                        "global_count_11_plus": 0,
                    },
                    "policy_adjustment_reason": "recalibrate_from_strong_near_miss_towards_11_plus_and_15",
                },
                decision_mode="OBSERVACAO",
                approved_for_use=0,
                notes="batch memory",
                official_history_count=3699,
                official_history_first_contest=1,
                official_history_last_contest=3699,
                official_history_window=[10, 60, 100, 300],
                source="scientific_reconciliation",
            )
        )
        session.add(
            ScientificInstitutionalMemory(
                memory_kind="scientific_reconciliation",
                strategy_name="15 dezenas",
                game_size=15,
                batch_id="batch-legacy-999",
                generation_range={"generation_event_id": 999, "batch_id": "batch-legacy-999"},
                total_games=10,
                unique_games=10,
                duplicate_games=0,
                structural_status="APROVADO",
                scientific_status="APROVADO",
                scientific_classification="NEAR_MISS_LOCAL",
                main_reason="legacy_memory",
                recommended_action="recalibrate_from_near_miss_towards_15",
                policy_applied=dict(weak_policy),
                policy_before=dict(weak_policy),
                policy_after=dict(weak_policy),
                best_hit=10,
                average_hits=9.0,
                count_11_plus=0,
                count_12_plus=0,
                count_13_plus=0,
                count_14_plus=0,
                count_15=0,
                validation_contests=[3698],
                cross_validation_summary={"policy_adjustment_reason": "recalibrate_from_near_miss_towards_15"},
                decision_mode="OBSERVACAO",
                approved_for_use=0,
                notes="weaker newer memory",
                official_history_count=3698,
                official_history_first_contest=1,
                official_history_last_contest=3698,
                official_history_window=[10, 60, 100, 300],
                source="scientific_reconciliation",
            )
        )
        session.add(
            ScientificInstitutionalMemory(
                memory_kind="scientific_batch_reconciliation",
                strategy_name="15 dezenas",
                game_size=15,
                batch_id="batch-current-24",
                generation_range={
                    "batch_id": "batch-current-24",
                    "generation_event_ids": [22, 15, 16, 17, 19, 23, 21, 24, 20, 18],
                    "best_generations": [22, 15, 16, 17],
                    "first_generation_event_id": 15,
                    "last_generation_event_id": 24,
                    "total_generations": 10,
                    "total_games_checked": 100,
                    "global_best_hits": 10,
                    "global_count_10": 13,
                    "global_count_11_plus": 0,
                },
                total_games=100,
                unique_games=100,
                duplicate_games=0,
                structural_status="APROVADO",
                scientific_status="APROVADO",
                scientific_classification="STRONG_NEAR_MISS_BATCH",
                main_reason="near_miss_batch_without_evolution",
                recommended_action="recalibrate_from_strong_near_miss_towards_11_plus_and_15",
                policy_applied=dict(current_batch_policy),
                policy_before=dict(current_batch_policy),
                policy_after=dict(current_batch_policy),
                best_hit=10,
                average_hits=10.0,
                count_11_plus=0,
                count_12_plus=0,
                count_13_plus=0,
                count_14_plus=0,
                count_15=0,
                validation_contests=[3694],
                cross_validation_summary={
                    "contest_scope": "BATCH_CONSOLIDATED",
                    "ranking_summary": {
                        "best_generation_event_id": 22,
                        "secondary_generation_event_ids": [15, 16, 17],
                        "best_generations": [22, 15, 16, 17],
                        "total_generations": 10,
                        "total_games_checked": 100,
                        "global_best_hits": 10,
                        "global_count_10": 13,
                        "global_count_11_plus": 0,
                    },
                    "support_level": "dominant_conditional",
                    "cross_validation_reason": "historical_cross_validation_supports_memory",
                    "windows": current_cross_validation_windows,
                    "policy_adjustment_reason": "recalibrate_from_strong_near_miss_towards_11_plus_and_15",
                },
                decision_mode="OBSERVACAO",
                approved_for_use=0,
                notes="current batch memory without evolutionary gain",
                official_history_count=3694,
                official_history_first_contest=1,
                official_history_last_contest=3694,
                official_history_window=[10, 60, 100, 300],
                source="scientific_reconciliation",
            )
        )
        session.commit()

    discovery = discover_scientific_generation_policy(15, contests=[_contest(1, list(range(1, 16)))], db_path=db_path)

    assert discovery["selection_status"] == "POLICY_SELECTED"
    assert discovery["based_on_memory_kind"] == "scientific_batch_reconciliation"
    assert discovery["based_on_batch_id"] == "batch-current-24"
    assert discovery["selection_variant"] == "cross_validated_scientific_batch_memory"
    assert discovery["selection_reason"] == "historical_cross_validation_supports_memory"
    assert discovery["memory_role"] == "strong_support"
    assert discovery["dominant_memory"] == "conditional"
    assert discovery["reason"] == "historical_cross_validation_supports_memory"
    assert discovery["recommended_action"] == "historical_cross_validation_supports_memory"
    assert discovery["policy_adjustment_reason"] == "historical_cross_validation_supports_memory"
    assert discovery["cross_validation_reason"] == "historical_cross_validation_supports_memory"
    assert discovery["validation_threshold"] == 11
    assert discovery["target_band"] == "11_to_15"
    assert discovery["validation_zone_label"] == "Zona de validação científica: 11 a 15 acertos."
    assert discovery["cross_validation_summary"]["support_level"] == "dominant_conditional"
    assert discovery["cross_validation_windows"]["10"]["average_best_hits"] == 11.6
    assert discovery["cross_validation_windows"]["30"]["max_best_hits"] == 13
    assert discovery["cross_validation_windows"]["60"]["total_count_11_plus"] == 868
    assert discovery["policy"]["based_on_memory_kind"] == "scientific_batch_reconciliation"
    assert discovery["policy"]["based_on_batch_id"] == "batch-current-24"
    assert discovery["policy"]["based_on_best_generations"] == [22, 15, 16, 17]
    assert discovery["policy"]["memory_role"] == "strong_support"
    assert discovery["policy"]["dominant_memory"] == "conditional"
    assert discovery["policy"]["dominant_memory_mode"] == "conditional"
    assert discovery["policy"]["reason"] == "historical_cross_validation_supports_memory"
    assert discovery["policy"]["cross_validation_summary"]["support_level"] == "dominant_conditional"
    assert discovery["policy"]["cross_validation_windows"]["10"]["average_best_hits"] == 11.6
    assert discovery["policy"]["cross_validation_windows"]["30"]["max_best_hits"] == 13
    assert discovery["policy"]["cross_validation_windows"]["60"]["total_count_11_plus"] == 868
    assert discovery["policy"]["policy_variant"] == "cross_validated_scientific_batch_memory"
    assert discovery["policy"]["policy_adjustment_reason"] == "historical_cross_validation_supports_memory"


def test_scientific_hit_decomposition_uses_zone_by_game_size() -> None:
    assert _scientific_hit_decomposition({"game_size": 15})["validation_threshold"] == 11
    assert _scientific_hit_decomposition({"game_size": 15})["validation_zone_label"] == "Zona de validação científica: 11 a 15 acertos."
    assert _scientific_hit_decomposition({"game_size": 17})["validation_threshold"] == 12
    assert _scientific_hit_decomposition({"game_size": 17})["validation_zone_label"] == "Zona de validação científica: 12 a 15 acertos."
    assert _scientific_hit_decomposition({"game_size": 18})["validation_threshold"] == 13
    assert _scientific_hit_decomposition({"game_size": 18})["validation_zone_label"] == "Zona de validação científica: 13 a 15 acertos."


def test_persisted_generation_carries_scientific_batch_origin(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "lotoia.db"
    create_database(db_path)
    monkeypatch.setattr("dashboard.institutional_app.DB_PATH", db_path, raising=False)

    games = [
        {
            "numbers": list(range(1, 16)),
            "profile_type": "balanced",
            "final_score": {"final_score": 0.95},
            "quadra_score": {"found_quadras": 1},
        }
    ]
    generation_context = {
        "policy_origin": "scientific_batch_reconciliation_memory",
        "policy_adjustment_reason": "recalibrate_from_strong_near_miss_towards_11_plus_and_15",
        "status_prospectivo": "pending_prospective_validation",
        "memory_role": "strong_support",
        "dominant_memory": "conditional",
        "selection_variant": "cross_validated_scientific_batch_memory",
        "cross_validation_reason": "historical_cross_validation_supports_memory",
        "cross_validation_summary": {"support_level": "dominant_conditional"},
        "based_on_memory_kind": "scientific_batch_reconciliation",
        "based_on_memory_id": 42,
        "based_on_batch_id": "batch-351-360",
        "based_on_generation_range": {
            "first_generation_event_id": 351,
            "last_generation_event_id": 360,
            "total_generations": 10,
            "total_games_checked": 100,
        },
        "based_on_best_generations": [351, 354],
    }

    snapshot = _persist_generation_snapshot(
        games=games,
        seed=12345,
        target_contest=3699,
        batch_id="batch-351-360",
        generation_context=generation_context,
    )

    with get_session(db_path) as session:
        event = session.query(GenerationEvent).filter(GenerationEvent.id == snapshot["generation_event_id"]).one()
        generated_game = session.query(GeneratedGame).filter(GeneratedGame.generation_event_id == event.id).one()
        output_signature = session.query(InstitutionalOutputSignature).filter(
            InstitutionalOutputSignature.generation_event_id == event.id
        ).one()

    assert snapshot["batch_id"] == "batch-351-360"
    assert event.context_json["based_on_memory_kind"] == "scientific_batch_reconciliation"
    assert event.context_json["based_on_memory_id"] == 42
    assert event.context_json["based_on_batch_id"] == "batch-351-360"
    assert event.context_json["status_prospectivo"] == "pending_prospective_validation"
    assert event.context_json["memory_role"] == "strong_support"
    assert event.context_json["dominant_memory"] == "conditional"
    assert event.context_json["selection_variant"] == "cross_validated_scientific_batch_memory"
    assert event.context_json["cross_validation_reason"] == "historical_cross_validation_supports_memory"
    assert event.context_json["cross_validation_summary"]["support_level"] == "dominant_conditional"
    assert event.context_json["based_on_generation_range"]["total_generations"] == 10
    assert event.context_json["based_on_best_generations"] == [351, 354]
    assert event.context_json["policy_adjustment_reason"] == "recalibrate_from_strong_near_miss_towards_11_plus_and_15"
    assert event.context_json["game_signatures"]
    assert generated_game.context_json["based_on_memory_kind"] == "scientific_batch_reconciliation"
    assert generated_game.context_json["based_on_batch_id"] == "batch-351-360"
    assert generated_game.context_json["status_prospectivo"] == "pending_prospective_validation"
    assert output_signature.payload["based_on_memory_kind"] == "scientific_batch_reconciliation"
    assert output_signature.payload["based_on_best_generations"] == [351, 354]
    assert output_signature.payload["status_prospectivo"] == "pending_prospective_validation"
    assert output_signature.payload["memory_role"] == "strong_support"
    assert output_signature.payload["dominant_memory"] == "conditional"
    assert output_signature.payload["selection_variant"] == "cross_validated_scientific_batch_memory"
    assert output_signature.payload["cross_validation_reason"] == "historical_cross_validation_supports_memory"


def test_batch_conference_materializes_global_memory(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "lotoia.db"
    create_database(db_path)
    monkeypatch.setattr("dashboard.institutional_app.DB_PATH", db_path, raising=False)

    contests = [{"contest_number": 3699, "numbers": list(range(1, 16)), "data": "2026-06-01"}]

    def fake_discovery(*args, **kwargs):
        base_policy = {
            "repeat_min": 7,
            "repeat_max": 10,
            "preferred_parity_pairs": [[7, 8], [8, 7]],
            "allowed_parity_pairs": [[7, 8], [8, 7]],
            "sequence_max": 6,
            "coverage_min": 0.4,
            "entropy_min": 0.45,
            "max_frequency_ratio": 0.7,
            "min_frequency_ratio": 0.2,
        }
        return {
            "policy": dict(base_policy),
            "policy_before": dict(base_policy),
            "policy_after": dict(base_policy),
            "policy_origin": "scientific_batch_reconciliation_memory",
            "based_on_memory_kind": "scientific_batch_reconciliation",
            "based_on_memory_id": 42,
            "based_on_batch_id": "batch-351-360",
            "based_on_generation_range": {
                "first_generation_event_id": 351,
                "last_generation_event_id": 360,
                "total_generations": 10,
                "total_games_checked": 100,
            },
            "based_on_best_generations": [351, 354],
        }

    monkeypatch.setattr("dashboard.institutional_app.discover_scientific_generation_policy", fake_discovery)
    monkeypatch.setattr("dashboard.institutional_app._load_imported_contest", lambda contest_number: contests[0])

    def _group(generation_event_id: int, ten_hit_games: int) -> dict[str, object]:
        games = []
        for index in range(10):
            hit_count = 10 if index < ten_hit_games else 9
            numbers = list(range(1, hit_count + 1)) + list(range(16, 16 + (15 - hit_count)))
            games.append(
                {
                    "game_index": index + 1,
                    "numbers": numbers[:15],
                    "profile_type": "balanced",
                    "score": 0.95 if hit_count == 10 else 0.55,
                }
            )
        return {
            "generation_event_id": generation_event_id,
            "batch_id": "batch-351-360",
            "created_at": f"2026-06-01T12:{generation_event_id % 60:02d}:00+00:00",
            "seed": 123 + generation_event_id,
            "strategy": "institutional_clean_hb",
            "total_games": 10,
            "target_contest": 3699,
            "is_conferida": False,
            "games": games,
            "structural_summary": {"games": 10},
        }

    monkeypatch.setattr(
        "dashboard.institutional_app._load_persisted_generation_event_groups",
        lambda batch_id=None: [
            _group(351, 7),
            _group(352, 1),
            _group(353, 1),
            _group(354, 7),
            _group(355, 1),
            _group(356, 1),
            _group(357, 1),
            _group(358, 1),
            _group(359, 1),
            _group(360, 1),
        ],
    )

    st.session_state.clear()
    st.session_state["institutional_active_batch_id"] = "batch-351-360"

    _run_institutional_conference(contest_number=3699)

    batch_result = dict(st.session_state.get("institutional_batch_conference_result") or {})
    check_result = dict(st.session_state.get("institutional_check_result") or {})

    assert batch_result["batch_id"] == "batch-351-360"
    assert batch_result["total_generations"] == 10
    assert batch_result["total_games_checked"] == 100
    assert batch_result["best_hits"] == 10
    assert batch_result["best_generations"][:2] == [351, 354]
    assert batch_result["classification"] == "STRONG_NEAR_MISS_BATCH"
    assert batch_result["count_10_exact"] == 22
    assert batch_result["count_11_exact"] == 0
    assert batch_result["count_12_exact"] == 0
    assert batch_result["count_13_exact"] == 0
    assert batch_result["count_14_exact"] == 0
    assert batch_result["count_15_exact"] == 0
    assert batch_result["count_11_plus"] == batch_result["count_11_exact"] + batch_result["count_12_exact"] + batch_result["count_13_exact"] + batch_result["count_14_exact"] + batch_result["count_15_exact"]
    assert batch_result["count_12_plus"] == batch_result["count_12_exact"] + batch_result["count_13_exact"] + batch_result["count_14_exact"] + batch_result["count_15_exact"]
    assert batch_result["hit_histogram"]["10"] == 22
    assert batch_result["batch_reconciliation_memory"]["memory_kind"] == "scientific_batch_reconciliation"
    assert batch_result["batch_reconciliation_memory"]["generation_range"]["total_games_checked"] == 100
    assert batch_result["batch_reconciliation_memory"]["generation_range"]["best_generations"][:2] == [351, 354]
    assert batch_result["games_with_11_plus"] == []
    assert len(batch_result["generation_results"]) == 10
    assert check_result["batch_conference_result"]["batch_id"] == "batch-351-360"
    assert check_result["batch_reconciliation_memory"]["memory_kind"] == "scientific_batch_reconciliation"


def test_scientific_policy_panel_accepts_scientific_batch_origin() -> None:
    policy_discovery = {
        "policy_origin": "scientific_batch_reconciliation_memory",
        "candidate_count": 3,
        "selection_reason": "historical_cross_validation_supports_memory",
        "selection_status": "POLICY_SELECTED",
        "policy": {"repeat_min": 7},
    }

    assert _scientific_policy_is_ready(policy_discovery) is True


def test_scientific_memory_listing_uses_consistent_nomenclature() -> None:
    listing = _format_scientific_memory_listing(
        [
            {
                "id": 24,
                "memory_kind": "scientific_batch_reconciliation",
                "batch_id": "calibration-20260602003007-665ca6b4",
                "scientific_classification": "STRONG_NEAR_MISS_BATCH",
                "recommended_action": "recalibrate_from_strong_near_miss_towards_11_plus_and_15",
                "cross_validation_summary": {
                    "memory_role": "strong_support",
                    "dominant_memory": "conditional",
                    "selection_variant": "cross_validated_scientific_batch_memory",
                    "cross_validation_reason": "historical_cross_validation_supports_memory",
                    "prospective_status": "pending_prospective_validation",
                    "scientific_reading": "memória com suporte histórico cruzado",
                },
            }
        ]
    )

    assert list(listing.columns) == [
        "leitura científica",
        "memory_id",
        "memory_kind",
        "batch_id de origem",
        "classification",
        "memory_role",
        "dominant_memory",
        "selection_variant",
        "cross_validation_reason",
        "recommended_action",
        "status prospectivo",
    ]
    record = listing.iloc[0].to_dict()
    assert record["leitura científica"] == "memória com suporte histórico cruzado"
    assert record["memory_id"] == 24
    assert record["memory_kind"] == "scientific_batch_reconciliation"
    assert record["batch_id de origem"] == "calibration-20260602003007-665ca6b4"
    assert record["classification"] == "STRONG_NEAR_MISS_BATCH"
    assert record["memory_role"] == "strong_support"
    assert record["dominant_memory"] == "conditional"
    assert record["selection_variant"] == "cross_validated_scientific_batch_memory"
    assert record["cross_validation_reason"] == "historical_cross_validation_supports_memory"
    assert record["recommended_action"] == "recalibrate_from_strong_near_miss_towards_11_plus_and_15"
    assert record["status prospectivo"] == "pending_prospective_validation"


def test_institutional_generation_policy_falls_back_to_history_profile_seed(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "lotoia.db"
    create_database(db_path)
    monkeypatch.setattr("dashboard.institutional_app.DB_PATH", db_path, raising=False)
    monkeypatch.setattr(
        "dashboard.institutional_app.discover_scientific_generation_policy",
        lambda *args, **kwargs: {
            "selection_status": "NONE_APPROVED",
            "selection_variant": "",
            "policy_origin": "automatic_scientific_discovery",
            "selection_reason": "policy_derived_from_official_history",
            "based_on_memory_kind": None,
            "based_on_memory_id": None,
            "based_on_batch_id": None,
            "based_on_generation_range": None,
            "based_on_best_generations": [],
        },
    )

    policy = _institutional_generation_policy(15)

    assert policy["policy_origin"] == "automatic_scientific_discovery"
    assert policy["policy_variant"] == "history_profile_seed"
    assert policy["selection_variant"] == "history_profile_seed"
    assert policy["selection_reason"] == "policy_derived_from_official_history"
    assert policy["policy_adjustment_reason"] == "policy_derived_from_official_history"
    assert policy["based_on_memory_kind"] is None
    assert policy["based_on_batch_id"] is None


def test_latest_contest_sources_are_distinguished(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "lotoia.db"
    create_database(db_path)
    monkeypatch.setattr("dashboard.institutional_app.DB_PATH", db_path, raising=False)
    monkeypatch.setattr(
        "dashboard.institutional_app._load_official_sync_diagnostics",
        lambda: {
            "sync_status": "ok",
            "sync_timestamp": "2026-06-02T17:04:00+00:00",
            "imported_contest": 3700,
            "imported_numbers": [1, 3, 7, 8, 9, 10, 12, 13, 14, 17, 18, 19, 20, 23, 25],
            "payload": {
                "latest_contest": 3700,
                "latest_contest_record": {
                    "contest_number": 3700,
                    "data": "01/06/2026",
                    "dezenas": [1, 3, 7, 8, 9, 10, 12, 13, 14, 17, 18, 19, 20, 23, 25],
                },
            },
        },
    )

    csv_summary = _load_csv_latest_contest_summary()
    sync_summary = _load_official_sync_contest_summary()
    latest_summary = _load_latest_contest_summary()
    latest_contest = _get_latest_contest()

    assert csv_summary is not None
    assert csv_summary["contest_number"] == 3702
    assert sync_summary is not None
    assert sync_summary["contest_number"] == 3700
    assert sync_summary["source"] == "api_caixa_sincronizada"
    assert latest_summary is not None
    assert latest_summary["contest_number"] == 3700
    assert latest_summary["source"] == "api_caixa_sincronizada"
    assert latest_contest is not None
    assert latest_contest["contest_number"] == 3700


def test_institutional_source_map_separates_csv_api_and_persisted_history(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "lotoia.db"
    create_database(db_path)
    monkeypatch.setattr("dashboard.institutional_app.DB_PATH", db_path, raising=False)
    monkeypatch.setattr(
        "dashboard.institutional_app._load_official_history_diagnostics",
        lambda: {
            "total_lotofacil_official_history": 4,
            "contest_number_min": 3697,
            "contest_number_max": 3700,
            "total_concursos_faltantes": 0,
            "ultimo_concurso_lotofacil_official_history": 3700,
            "status_base_oficial": "OK",
        },
    )
    monkeypatch.setattr(
        "dashboard.institutional_app._load_official_sync_diagnostics",
        lambda: {
            "sync_status": "ok",
            "sync_timestamp": "2026-06-02T17:04:00+00:00",
            "imported_contest": 3700,
            "imported_numbers": [1, 3, 7, 8, 9, 10, 12, 13, 14, 17, 18, 19, 20, 23, 25],
            "payload": {
                "latest_contest": 3700,
                "latest_contest_record": {
                    "contest_number": 3700,
                    "data": "01/06/2026",
                    "dezenas": [1, 3, 7, 8, 9, 10, 12, 13, 14, 17, 18, 19, 20, 23, 25],
                },
            },
        },
    )
    snapshot = {"counts": {"imported_contests": 4}}

    source_map = _institutional_source_map(snapshot)
    source_by_layer = {row["camada"]: row for row in source_map}

    assert source_by_layer["CSV histórico versionado"]["uso"].endswith("3702 | papel=seed/documentação | runtime=PostgreSQL")
    assert source_by_layer["API oficial"]["uso"].endswith("3700")
    assert "último concurso persistido=3700" in source_by_layer["Banco persistido"]["uso"]
    assert "lotofacil_official_history=4" in source_by_layer["Banco persistido"]["uso"]
    assert "primeiro=3697" in source_by_layer["Histórico oficial"]["uso"]
    assert "último=3700" in source_by_layer["Histórico oficial"]["uso"]
    assert "faltantes=0" in source_by_layer["Histórico oficial"]["uso"]


def test_generation_strategy_display_prioritizes_baseline_and_prepares_future_sizes(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "lotoia.db"
    create_database(db_path)
    monkeypatch.setattr("dashboard.institutional_app.DB_PATH", db_path, raising=False)
    monkeypatch.setattr(
        "dashboard.institutional_app.discover_scientific_generation_policy",
        lambda *args, **kwargs: {
            "selection_status": "NONE_APPROVED",
            "selection_variant": "",
            "policy_origin": "automatic_scientific_discovery",
            "selection_reason": "policy_derived_from_official_history",
            "based_on_memory_kind": None,
            "based_on_memory_id": None,
            "based_on_batch_id": None,
            "based_on_generation_range": None,
            "based_on_best_generations": [],
        },
    )

    display_15 = _generation_strategy_display(15)
    display_17 = _generation_strategy_display(17)
    display_18 = _generation_strategy_display(18)

    assert display_15["strategy_label"] == "Política 15 validada nível 3"
    assert display_15["scientific_status"] == "VALIDATED_15_POLICY_LEVEL_3"
    assert display_15["status_visual"] == "BASELINE OFICIAL"
    assert "13 acertos" in display_15["summary"]
    assert display_15["action_suggested"] == "usar baseline oficial validada nível 3 para próxima geração compacta"

    assert display_17["strategy_label"] == "Estratégia 17 preparada"
    assert display_17["scientific_status"] == "PREPARADO"
    assert display_17["status_visual"] == "PREPARADO"
    assert "12 = validação mínima" in display_17["main_reason"]

    assert display_18["strategy_label"] == "Estratégia 18 preparada"
    assert display_18["scientific_status"] == "PREPARADO"
    assert display_18["status_visual"] == "PREPARADO"
    assert "13 = validação mínima" in display_18["main_reason"]


def test_small_batch_compact_adjustment_enables_diversity_control() -> None:
    adjustment = _compact_small_batch_adjustment(game_size=15, total_games=20)
    assert adjustment["compactation_mode"] == "LIGHT_PRACTICAL_EXPANDED"
    assert adjustment["scientific_mother_law"].startswith("Lei Cient")
    assert adjustment["natural_scientific_quantity"] is False
    assert adjustment["natural_approvable_candidate"] is True
    assert adjustment["candidate_reason"] == "valid_individual_games_but_incomplete_requested_package"
    assert adjustment["natural_quantity_reason"] == "structural_saturation_under_scientific_law"
    assert adjustment["natural_quantity_mode"] == "OBSERVED_PRACTICAL_16"
    assert adjustment["natural_generated_games"] == 16
    assert adjustment["requested_games"] == 20
    assert adjustment["persisted_games"] == 0
    assert adjustment["approved_total_less_than_requested"] is True
    assert adjustment["blocked_reason"] == "nao_atingiu_quantidade_solicitada"
    assert adjustment["output_commander_status"] == "BLOQUEADO"
    assert adjustment["generated_candidates"] == 16
    assert adjustment["valid_individual_games"] == 16
    assert adjustment["natural_quantity_status"] == "CANDIDATE_OBSERVED"
    assert adjustment["compactation_status"] == "STRUCTURAL_SATURATION"
    assert adjustment["compactation_test_status"] == "FAILED_MINIMUM_11_PLUS"
    assert adjustment["compactation_failure_type"] == "EXPANDED_LIGHT_GEOMETRY"
    assert adjustment["compactation_adjustment_status"] == "ENABLED"
    assert adjustment["compactation_adjustment_mode"] == "LIGHT_PRACTICAL_EXPANDED"
    assert adjustment["compactation_adjustment_boost_numbers"] == [7, 14, 17, 23]
    assert adjustment["compactation_adjustment_reduce_priority_numbers"] == [2, 5, 21, 24]
    assert adjustment["compactation_adjustment_odd_min"] == 5
    assert adjustment["compactation_adjustment_odd_max"] == 10
    assert adjustment["compactation_adjustment_even_min"] == 5
    assert adjustment["compactation_adjustment_even_max"] == 10
    assert adjustment["compactation_adjustment_repeat_min"] == 3
    assert adjustment["compactation_adjustment_repeat_max"] == 9
    assert adjustment["compactation_adjustment_coverage_min"] == 0.34
    assert adjustment["compactation_adjustment_entropy_min"] == 0.38
    assert adjustment["compactation_adjustment_sequence_max"] == 6
    assert adjustment["compactation_adjustment_candidate_multiplier"] == 90
    assert adjustment["compactation_adjustment_attempt_limit"] == 1500
    assert "faixa 20" in adjustment["compactation_operational_law"]
    assert adjustment["compactation_law_role"] == "observed_operational_child_of_scientific_mother_law"
    assert "persist" in adjustment["compactation_required_constraints"][4]

    compact_15 = _compact_small_batch_adjustment(game_size=15, total_games=15)
    assert compact_15["compactation_mode"] == "COMPACT_PRACTICAL_15"
    assert compact_15["scientific_mother_law"].startswith("Lei Cient")
    assert compact_15["natural_scientific_quantity"] is False
    assert compact_15["natural_approvable_candidate"] is True
    assert compact_15["natural_quantity_mode"] == "OBSERVED_COMPACT_12"
    assert compact_15["natural_generated_games"] == 12
    assert compact_15["requested_games"] == 15
    assert compact_15["persisted_games"] == 0
    assert compact_15["approved_total_less_than_requested"] is True
    assert compact_15["blocked_reason"] == "nao_atingiu_quantidade_solicitada"
    assert compact_15["output_commander_status"] == "BLOQUEADO"
    assert compact_15["natural_quantity_status"] == "CANDIDATE_OBSERVED"
    assert compact_15["compactation_status"] == "OPERATIONAL_ACTIVE"
    assert compact_15["compactation_test_status"] == "OPERATIONAL_COMPACT_15"
    assert compact_15["compactation_adjustment_mode"] == "COMPACT_PRACTICAL_15"
    assert compact_15["compactation_adjustment_odd_min"] == 3
    assert compact_15["compactation_adjustment_odd_max"] == 12
    assert compact_15["compactation_adjustment_sequence_max"] == 7
    assert compact_15["compactation_law_role"] == "observed_operational_child_of_scientific_mother_law"

    compact_50 = _compact_small_batch_adjustment(game_size=15, total_games=50)
    assert compact_50["compactation_mode"] == "VALIDATED_BASELINE"
    assert compact_50["scientific_mother_law"].startswith("Lei Cient")
    assert compact_50["natural_scientific_quantity"] is True
    assert compact_50["natural_approvable_candidate"] is False
    assert compact_50["natural_quantity_mode"] == "VALIDATED_BASELINE_50"
    assert compact_50["natural_generated_games"] == 50
    assert compact_50["requested_games"] == 50
    assert compact_50["persisted_games"] == 0
    assert compact_50["approved_total_less_than_requested"] is False
    assert compact_50["blocked_reason"] == ""
    assert compact_50["output_commander_status"] == "APROVADO"
    assert compact_50["natural_quantity_status"] == "NATURAL_APPROVED"
    assert compact_50["compactation_status"] == "VALIDATED_BASELINE"
    assert compact_50["compactation_adjustment_mode"] == "VALIDATED_BASELINE"
    assert compact_50["compactation_adjustment_candidate_multiplier"] == 20


def test_small_batch_compact_adjustment_preserves_rigid_mode_for_10() -> None:
    adjustment = _compact_small_batch_adjustment(game_size=15, total_games=10)
    assert adjustment["compactation_mode"] == "EXTREME_COMPACT"
    assert adjustment["scientific_mother_law"] == "Lei Científica 15"
    assert adjustment["natural_scientific_quantity"] is False
    assert adjustment["natural_approvable_candidate"] is True
    assert adjustment["natural_quantity_mode"] == "OBSERVED_EXTREME_9"
    assert adjustment["natural_generated_games"] == 9
    assert adjustment["requested_games"] == 10
    assert adjustment["persisted_games"] == 0
    assert adjustment["approved_total_less_than_requested"] is True
    assert adjustment["blocked_reason"] == "nao_atingiu_quantidade_solicitada"
    assert adjustment["output_commander_status"] == "BLOQUEADO"
    assert adjustment["natural_quantity_status"] == "CANDIDATE_OBSERVED"
    assert adjustment["compactation_adjustment_mode"] == "EXTREME_COMPACT"
    assert adjustment["compactation_adjustment_boost_numbers"] == [17, 23]
    assert adjustment["compactation_law_role"] == "observed_operational_child_of_scientific_mother_law"


def test_progressive_compactation_profiles_expand_with_batch_size() -> None:
    compact_30 = _compact_small_batch_adjustment(game_size=15, total_games=30)
    compact_40 = _compact_small_batch_adjustment(game_size=15, total_games=40)
    compact_50 = _compact_small_batch_adjustment(game_size=15, total_games=50)

    assert compact_30["compactation_mode"] == "BALANCED_PRACTICAL"
    assert compact_30["scientific_mother_law"] == "Lei Científica 15"
    assert compact_30["compactation_adjustment_odd_max"] == 10
    assert compact_30["compactation_adjustment_sequence_max"] == 5
    assert compact_30["compactation_adjustment_candidate_multiplier"] == 70

    assert compact_40["compactation_mode"] == "NEAR_BASELINE"
    assert compact_40["scientific_mother_law"] == "Lei Científica 15"
    assert compact_40["compactation_adjustment_odd_max"] == 11
    assert compact_40["compactation_adjustment_sequence_max"] == 6
    assert compact_40["compactation_adjustment_candidate_multiplier"] == 90
    assert compact_40["compactation_status"] == "OPERATIONAL_ACTIVE"

    assert compact_50["compactation_mode"] == "VALIDATED_BASELINE"
    assert compact_50["scientific_mother_law"] == "Lei Científica 15"
    assert compact_50["compactation_adjustment_odd_max"] == 12
    assert compact_50["compactation_adjustment_sequence_max"] == 6
    assert compact_50["compactation_adjustment_candidate_multiplier"] == 20
    assert compact_50["compactation_adjustment_status"] == "ENABLED"
