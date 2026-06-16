from random import sample
import logging
import os
from random import Random

from lotoia.data.loader import load_draws_csv
from lotoia.ml.rerank import rerank_games
from lotoia.statistics.advanced import (
    CENTER_NUMBERS,
    EMPTY_FINAL_SCORE,
    calculate_final_score,
    calculate_quadra_score,
    calculate_sequence_stats,
)
from lotoia.statistics.historical_intelligence import (
    GENERATION_PROFILE_RATIOS,
    PROFILE_CHAOTIC,
    PROFILE_HYBRID,
    PROFILE_RECURRENT,
    classify_profile,
    profile_quota,
    profile_score,
)
from lotoia.statistics.generation_trace import persist_stage_snapshot, record_discarded_game, stage_snapshot
from lotoia.governance.law15_structural_realignment_v1 import (
    get_realignment_config,
    realignment_is_active,
    realignment_is_observable,
)

logger = logging.getLogger(__name__)


def _filters_disabled() -> bool:
    return os.getenv("FILTERS_DISABLED", "").strip().lower() in {"1", "true", "yes", "on"}


def _normalization_pressure_level() -> str:
    level = os.getenv("NORMALIZATION_PRESSURE_LEVEL", "hard").strip().lower()
    return level if level in {"hard", "medium", "soft"} else "hard"


def _pressure_scale() -> float:
    level = _normalization_pressure_level()
    return {"hard": 1.0, "medium": 0.8, "soft": 0.6}[level]


def _build_game(numbers: list[int]) -> dict[str, object]:
    ordered_numbers = sorted(numbers)
    odd = sum(1 for number in ordered_numbers if number % 2 != 0)
    center = sum(1 for number in ordered_numbers if number in CENTER_NUMBERS)

    return {
        "numbers": ordered_numbers,
        "odd": odd,
        "even": len(ordered_numbers) - odd,
        "sum": sum(ordered_numbers),
        "frame": len(ordered_numbers) - center,
        "center": center,
    }


def _validation_bounds(level: str, profile_type: str | None) -> dict[str, int]:
    if profile_type is None:
        return {
            "odd_min": 6,
            "odd_max": 10,
            "sum_min": 150,
            "sum_max": 220,
            "frame_min": 8,
            "frame_max": 13,
            "center_min": 3,
            "center_max": 8,
            "sequence_max": 3,
        }

    profile_key = profile_type
    if profile_key == PROFILE_RECURRENT:
        return {
            "hard": {
                "odd_min": 6,
                "odd_max": 10,
                "sum_min": 145,
                "sum_max": 225,
                "frame_min": 7,
                "frame_max": 13,
                "center_min": 2,
                "center_max": 8,
                "sequence_max": 7,
            },
            "medium": {
                "odd_min": 5,
                "odd_max": 11,
                "sum_min": 140,
                "sum_max": 230,
                "frame_min": 7,
                "frame_max": 14,
                "center_min": 2,
                "center_max": 8,
                "sequence_max": 8,
            },
            "soft": {
                "odd_min": 5,
                "odd_max": 11,
                "sum_min": 135,
                "sum_max": 235,
                "frame_min": 6,
                "frame_max": 14,
                "center_min": 1,
                "center_max": 9,
                "sequence_max": 9,
            },
        }[level]

    if profile_key == PROFILE_CHAOTIC:
        return {
            "hard": {
                "odd_min": 5,
                "odd_max": 11,
                "sum_min": 140,
                "sum_max": 235,
                "frame_min": 6,
                "frame_max": 14,
                "center_min": 1,
                "center_max": 9,
                "sequence_max": 8,
            },
            "medium": {
                "odd_min": 5,
                "odd_max": 11,
                "sum_min": 135,
                "sum_max": 240,
                "frame_min": 6,
                "frame_max": 14,
                "center_min": 1,
                "center_max": 9,
                "sequence_max": 9,
            },
            "soft": {
                "odd_min": 4,
                "odd_max": 11,
                "sum_min": 130,
                "sum_max": 245,
                "frame_min": 5,
                "frame_max": 15,
                "center_min": 1,
                "center_max": 10,
                "sequence_max": 10,
            },
        }[level]

    return {
        "hard": {
            "odd_min": 6,
            "odd_max": 10,
            "sum_min": 150,
            "sum_max": 220,
            "frame_min": 8,
            "frame_max": 13,
            "center_min": 3,
            "center_max": 8,
            "sequence_max": 5,
        },
        "medium": {
            "odd_min": 5,
            "odd_max": 11,
            "sum_min": 140,
            "sum_max": 230,
            "frame_min": 7,
            "frame_max": 14,
            "center_min": 2,
            "center_max": 8,
            "sequence_max": 7,
        },
        "soft": {
            "odd_min": 5,
            "odd_max": 11,
            "sum_min": 130,
            "sum_max": 240,
            "frame_min": 6,
            "frame_max": 14,
            "center_min": 1,
            "center_max": 9,
            "sequence_max": 8,
        },
    }[level]


def _is_valid_game(game: dict[str, object], profile_type: str | None = None) -> bool:
    if _filters_disabled():
        return True
    sequence_stats = calculate_sequence_stats(game["numbers"])
    level = _normalization_pressure_level()
    bounds = _validation_bounds(level, profile_type)

    return (
        bounds["odd_min"] <= game["odd"] <= bounds["odd_max"]
        and bounds["sum_min"] <= game["sum"] <= bounds["sum_max"]
        and bounds["frame_min"] <= game["frame"] <= bounds["frame_max"]
        and bounds["center_min"] <= game["center"] <= bounds["center_max"]
        and sequence_stats["sequence_count"] <= bounds["sequence_max"]
        and sequence_stats["largest_sequence"] <= bounds["sequence_max"]
    )


def _soft_filter_penalty(game: dict[str, object]) -> float:
    if _filters_disabled():
        return 0.0
    sequence_stats = calculate_sequence_stats(game["numbers"])
    scale = _pressure_scale()
    penalty = 0.0
    penalty += max(0, 6 - int(game["odd"])) * 4 * scale
    penalty += max(0, int(game["odd"]) - 9) * 4 * scale
    penalty += max(0, 155 - int(game["sum"])) * 0.35 * scale
    penalty += max(0, int(game["sum"]) - 255) * 0.35 * scale
    penalty += max(0, 7 - int(game["frame"])) * 3 * scale
    penalty += max(0, int(game["frame"]) - 13) * 3 * scale
    penalty += max(0, 2 - int(game["center"])) * 3 * scale
    penalty += max(0, int(game["center"]) - 8) * 3 * scale
    penalty += max(0, int(sequence_stats["sequence_count"]) - 5) * 3 * scale
    penalty += max(0, int(sequence_stats["largest_sequence"]) - 6) * 4 * scale
    return round(penalty, 2)


def _attach_scores(
    game: dict[str, object],
    history: list[object] | None = None,
    profile_type: str | None = None,
) -> dict[str, object]:
    numbers = game["numbers"]
    game["quadra_score"] = calculate_quadra_score(numbers)
    try:
        game["final_score"] = calculate_final_score(numbers)
    except Exception as exc:
        logger.warning("Falha ao calcular final_score; usando fallback zero: %s", exc)
        game["final_score"] = {
            "final_score": EMPTY_FINAL_SCORE["final_score"],
            "components": EMPTY_FINAL_SCORE["components"].copy(),
        }
    if history is not None:
        resolved_profile = profile_type or classify_profile(numbers, history)
        intelligence = profile_score(numbers, history, resolved_profile)
        penalty = _soft_filter_penalty(game)
        intelligence["soft_filter_penalty"] = penalty
        intelligence["profile_score"] = round(max(0, float(intelligence["profile_score"]) - penalty), 2)
        game["historical_intelligence"] = intelligence
        game["profile_type"] = resolved_profile
        game["profile_score"] = intelligence["profile_score"]
    return game


def generate_filtered_game() -> dict[str, object]:
    while True:
        game = _build_game(sample(range(1, 26), 15))
        if _is_valid_game(game):
            return _attach_scores(game)


def _generate_profile_candidate(
    random: Random,
    profile_type: str,
    history: list[object],
) -> dict[str, object]:
    last_numbers = set(history[-1].numbers) if history else set()
    hot_numbers: list[int] = []
    if history:
        counts = {number: 0 for number in range(1, 26)}
        for draw in history[-30:]:
            for number in draw.numbers:
                counts[number] += 1
        hot_numbers = [
            number for number, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:12]
        ]

    if profile_type == PROFILE_RECURRENT and history and hot_numbers:
        selected = set(random.sample(sorted(last_numbers), random.randint(8, min(10, len(last_numbers)))))
        available_hot = [number for number in hot_numbers if number not in selected]
        selected.update(random.sample(available_hot, min(len(available_hot), 15 - len(selected))))
        while len(selected) < 15:
            selected.add(random.randint(1, 25))
        return _build_game(list(selected))

    if profile_type == PROFILE_CHAOTIC:
        start = random.randint(1, 20)
        selected = set(range(start, min(26, start + random.randint(5, 7))))
        selected.update(random.choice([range(1, 6), range(6, 11), range(11, 16), range(16, 21), range(21, 26)]))
        while len(selected) < 15:
            selected.add(random.randint(1, 25))
        return _build_game(list(selected))

    selected = set()
    if history:
        selected.update(random.sample(sorted(last_numbers), random.randint(6, min(9, len(last_numbers)))))
    while len(selected) < 15:
        selected.add(random.randint(1, 25))
    return _build_game(list(selected))


def _rank_profile(games: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        games,
        key=lambda game: (
            -float(game.get("profile_score", 0)),
            -float(game.get("final_score", {}).get("final_score", 0)),
            -int(game.get("quadra_score", {}).get("found_quadras", 0)),
        ),
    )


def _compose_profiled_games(scored_games: list[dict[str, object]], count: int) -> list[dict[str, object]]:
    quotas = profile_quota(count)
    by_profile = {profile: [] for profile in GENERATION_PROFILE_RATIOS}
    for game in scored_games:
        by_profile.setdefault(str(game.get("profile_type", PROFILE_HYBRID)), []).append(game)

    selected: list[dict[str, object]] = []
    selected_keys: set[tuple[int, ...]] = set()
    for profile, quota in quotas.items():
        profile_selected = 0
        for game in _rank_profile(by_profile.get(profile, [])):
            if profile_selected >= quota:
                record_discarded_game(
                    "quota_limit",
                    game["numbers"],
                    reason=f"quota reached for profile {profile}",
                    metrics={
                        "profile_type": profile,
                        "profile_score": float(game.get("profile_score", 0)),
                        "final_score": float(game.get("final_score", {}).get("final_score", 0)),
                    },
                    profile_type=profile,
                )
                break
            key = tuple(game["numbers"])
            if key in selected_keys:
                record_discarded_game(
                    "duplicate_selected",
                    game["numbers"],
                    reason="duplicate game already selected",
                    metrics={
                        "profile_type": profile,
                        "profile_score": float(game.get("profile_score", 0)),
                    },
                    profile_type=profile,
                )
                continue
            selected.append(game)
            selected_keys.add(key)
            profile_selected += 1

    if len(selected) < count:
        for game in _rank_profile(scored_games):
            key = tuple(game["numbers"])
            if key in selected_keys:
                record_discarded_game(
                    "global_duplicate",
                    game["numbers"],
                    reason="duplicate game already selected",
                    metrics={
                        "profile_type": game.get("profile_type", ""),
                        "profile_score": float(game.get("profile_score", 0)),
                        "final_score": float(game.get("final_score", {}).get("final_score", 0)),
                    },
                    profile_type=str(game.get("profile_type", "")),
                )
                continue
            selected.append(game)
            selected_keys.add(key)
            if len(selected) >= count:
                break

    if selected:
        profile_counts = {
            profile: sum(1 for game in selected if game.get("profile_type") == profile)
            for profile in GENERATION_PROFILE_RATIOS
        }
        deficits = {profile: quotas.get(profile, 0) - profile_counts.get(profile, 0) for profile in GENERATION_PROFILE_RATIOS}
        surpluses = {profile: profile_counts.get(profile, 0) - quotas.get(profile, 0) for profile in GENERATION_PROFILE_RATIOS}
        for deficit_profile, missing in deficits.items():
            while missing > 0:
                surplus_profile = next((profile for profile, extra in surpluses.items() if extra > 0), None)
                if surplus_profile is None:
                    break
                candidate = next(
                    (game for game in reversed(_rank_profile(selected)) if game.get("profile_type") == surplus_profile),
                    None,
                )
                if candidate is None:
                    break
                candidate["profile_type"] = deficit_profile
                intelligence = candidate.get("historical_intelligence")
                if isinstance(intelligence, dict):
                    intelligence["profile_type"] = deficit_profile
                surpluses[surplus_profile] -= 1
                profile_counts[surplus_profile] -= 1
                profile_counts[deficit_profile] += 1
                missing -= 1
    return selected[:count]


def _record_generation_stage(
    stage: str,
    games: list[dict[str, object]],
    history: list[object],
    profile_distribution: dict[str, int],
) -> None:
    snapshot = stage_snapshot(
        stage,
        games,
        history=history,
        metadata={
            "engine_version": "historical_recalibrated_v2",
            "profile_distribution": profile_distribution,
            "normalization_disabled": os.getenv("NORMALIZATION_DISABLED", "").strip().lower() in {"1", "true", "yes", "on"},
        },
    )
    persist_stage_snapshot(snapshot)


def _repeated_count(first_game: dict[str, object], second_game: dict[str, object]) -> int:
    return len(set(first_game["numbers"]) & set(second_game["numbers"]))


def generate_multiple_games(count: int = 10, max_repeated: int = 9) -> list[dict[str, object]]:
    if count < 1:
        raise ValueError("A quantidade de jogos deve ser maior que zero.")
    if max_repeated < 0 or max_repeated > 15:
        raise ValueError("A repeticao maxima deve estar entre 0 e 15.")

    games: list[dict[str, object]] = []
    seen_games: set[tuple[int, ...]] = set()
    max_attempts = count * 1000
    attempts = 0

    while len(games) < count and attempts < max_attempts:
        attempts += 1
        game = generate_filtered_game()
        game_key = tuple(game["numbers"])

        if game_key in seen_games:
            record_discarded_game(
                "duplicate_pool",
                game["numbers"],
                reason="game already seen in pool",
                metrics={"max_repeated": max_repeated},
            )
            continue
        repeated_over_limit = None if _filters_disabled() else next((previous_game for previous_game in games if _repeated_count(game, previous_game) > max_repeated), None)
        if repeated_over_limit is not None:
            record_discarded_game(
                "max_repeated",
                game["numbers"],
                reason="repetition above allowed threshold",
                metrics={
                    "max_repeated": max_repeated,
                    "repeated_with": tuple(repeated_over_limit["numbers"]),
                    "repeated_count": _repeated_count(game, repeated_over_limit),
                },
            )
            continue

        games.append(game)
        seen_games.add(game_key)

    if len(games) < count:
        raise RuntimeError("Nao foi possivel gerar jogos com os filtros informados.")

    return games


def _hybrid_score_sort_key(game: dict[str, object]) -> tuple[object, object, object]:
    return (
        -game["final_score"]["final_score"],
        -game["quadra_score"]["found_quadras"],
        game["quadra_score"]["average_rank"],
    )


def generate_best_games(
    count: int = 10,
    pool_size: int = 30,
    ml_enabled: bool = False,
    seed: int | None = None,
) -> dict[str, object]:
    if count < 1:
        raise ValueError("A quantidade de jogos deve ser maior que zero.")
    if pool_size < count:
        raise ValueError("O pool de jogos deve ser maior ou igual a quantidade solicitada.")

    history = load_draws_csv()
    games: list[dict[str, object]] = []
    seen_games: set[tuple[int, ...]] = set()
    max_attempts = pool_size * 1500
    attempts = 0
    profiles = list(GENERATION_PROFILE_RATIOS)
    seed_offset = 0 if seed is None else abs(int(seed)) % 1000003

    while len(games) < pool_size and attempts < max_attempts:
        attempts += 1
        profile_type = profiles[attempts % len(profiles)]
        candidate = _generate_profile_candidate(
            Random((attempts * 7919) + pool_size + seed_offset),
            profile_type,
            history,
        )
        if not _is_valid_game(candidate, profile_type=profile_type):
            record_discarded_game(
                "normalize_distribution",
                candidate["numbers"],
                reason="candidate rejected by normalization filter",
                metrics={
                    "pressure_level": _normalization_pressure_level(),
                    "odd": candidate.get("odd"),
                    "sum": candidate.get("sum"),
                    "frame": candidate.get("frame"),
                    "center": candidate.get("center"),
                },
                history=history,
                profile_type=profile_type,
            )
            continue
        game = _attach_scores(
            candidate,
            history=history,
            profile_type=profile_type,
        )
        game_key = tuple(game["numbers"])

        if game_key in seen_games:
            continue

        games.append(game)
        seen_games.add(game_key)

    if len(games) < pool_size:
        raise RuntimeError("Nao foi possivel gerar o pool de jogos com os filtros informados.")

    raw_profile_distribution = {
        profile: sum(1 for game in games if game.get("profile_type") == profile)
        for profile in GENERATION_PROFILE_RATIOS
    }
    _record_generation_stage("raw_generation", games, history, raw_profile_distribution)

    normalization_disabled = os.getenv("NORMALIZATION_DISABLED", "").strip().lower() in {"1", "true", "yes", "on"}
    if normalization_disabled:
        _record_generation_stage("post_normalization_disabled", games, history, raw_profile_distribution)
    else:
        games = rerank_games(games, enabled=ml_enabled)
        rerank_profile_distribution = {
            profile: sum(1 for game in games if game.get("profile_type") == profile)
            for profile in GENERATION_PROFILE_RATIOS
        }
        _record_generation_stage("post_rerank", games, history, rerank_profile_distribution)

    # --- Structural Realignment V1 hook (feature-flagged) -------------------
    _realign_cfg = get_realignment_config()
    if realignment_is_observable():
        from lotoia.generation.structural_realignment_v1 import (
            apply_gp_realignment_scoring,
            compose_diverse_gp,
            compute_gp_realignment_metrics,
        )
        games = apply_gp_realignment_scoring(games, _realign_cfg, game_size=count)
        logger.info("[RealignmentV1] mode=%s pool_size=%d", _realign_cfg.mode, len(games))

    if realignment_is_active():
        from lotoia.generation.structural_realignment_v1 import compose_diverse_gp
        best_games = compose_diverse_gp(games, count, _realign_cfg, game_size=count)
    else:
        best_games = _compose_profiled_games(games, count)

    if realignment_is_observable() and best_games:
        from lotoia.generation.structural_realignment_v1 import compute_gp_realignment_metrics
        _rm = compute_gp_realignment_metrics(best_games, game_size=count)
        logger.info(
            "[RealignmentV1] top_p3=%s(%.0f%%) top_s3=%s(%.0f%%) near_dups=%d",
            _rm.get("top_prefix3"), _rm.get("top_prefix3_ratio", 0) * 100,
            _rm.get("top_suffix3"), _rm.get("top_suffix3_ratio", 0) * 100,
            _rm.get("near_duplicate_pairs", 0),
        )
    # -------------------------------------------------------------------------

    final_profile_distribution = {
        profile: sum(1 for game in best_games if game.get("profile_type") == profile)
        for profile in GENERATION_PROFILE_RATIOS
    }
    _record_generation_stage("final_output", best_games, history, final_profile_distribution)
    profile_counts = {
        profile: sum(1 for game in best_games if game.get("profile_type") == profile)
        for profile in GENERATION_PROFILE_RATIOS
    }
    return {
        "count": len(best_games),
        "games": best_games,
        "profile_counts": profile_counts,
        "profile_percentages": {
            profile: round((amount / len(best_games)) * 100, 2) if best_games else 0.0
            for profile, amount in profile_counts.items()
        },
    }
