from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from statistics import mean, median
from typing import Any

from lotoia.analytics.lotofacil_scientific_core import (
    LotofacilScientificCore,
    _decompose_hit_counts,
    _scientific_validation_rule,
    get_scientific_generation_policy,
)
from lotoia.statistics.advanced import calculate_sequence_stats
from lotoia.statistics.patterns import low_high_distribution, odd_even_distribution

__all__ = [
    "ScientificBatchValidationReport",
    "validate_scientific_batch",
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


def _safe_get(row: Any, key: str, default: Any = None) -> Any:
    if row is None:
        return default
    if isinstance(row, Mapping):
        return row.get(key, default)
    getter = getattr(row, "get", None)
    if callable(getter):
        try:
            return getter(key, default)
        except Exception:
            pass
    return getattr(row, key, default)


def _normalize_numbers(raw_numbers: Any) -> list[int]:
    numbers: list[int] = []
    if raw_numbers is None:
        return numbers
    if isinstance(raw_numbers, Mapping):
        raw_numbers = raw_numbers.get("numbers", raw_numbers.get("dezenas", []))
    if isinstance(raw_numbers, str):
        raw_numbers = raw_numbers.replace(",", " ").split()
    if not isinstance(raw_numbers, Iterable) or isinstance(raw_numbers, (str, bytes)):
        return numbers
    for item in raw_numbers:
        number = _safe_int(item, default=None)
        if number is None or not 1 <= number <= 25:
            continue
        if number not in numbers:
            numbers.append(number)
    return sorted(numbers)


def _normalize_contest(row: Any, *, default_contest: int | None = None) -> dict[str, Any]:
    contest_number = _safe_int(_safe_get(row, "contest_number", _safe_get(row, "concurso", default_contest)), default=default_contest)
    numbers = _normalize_numbers(_safe_get(row, "numbers", _safe_get(row, "dezenas", [])))
    return {
        "contest_number": int(contest_number or 0),
        "numbers": numbers,
        "draw_date": str(_safe_get(row, "draw_date", _safe_get(row, "data", "")) or ""),
    }


def _contest_signature(contest: Mapping[str, Any]) -> str:
    numbers = _normalize_numbers(contest.get("numbers", []))
    return "-".join(f"{number:02d}" for number in numbers)


def _band_distribution(numbers: Sequence[int]) -> dict[str, int]:
    counts = {f"band_{band}": 0 for band in range(1, 6)}
    for number in numbers:
        if 1 <= int(number) <= 25:
            band = ((int(number) - 1) // 5) + 1
            counts[f"band_{band}"] += 1
    return counts


def _parity_profile(numbers: Sequence[int]) -> str:
    parity = odd_even_distribution(list(numbers))
    return f"{int(parity['odd'])}/{int(parity['even'])}"


def _low_high_profile(numbers: Sequence[int]) -> str:
    profile = low_high_distribution(list(numbers))
    return f"{int(profile['low'])}/{int(profile['high'])}"


@dataclass(frozen=True, slots=True)
class ScientificBatchValidationReport:
    batch_id: str
    game_size: int
    reference_contests: tuple[int, ...]
    validation_threshold: int
    target_band: str
    validation_zone_label: str
    total_jogos_solicitados: int
    total_jogos_gerados: int
    total_jogos_unicos: int
    total_jogos_duplicados: int
    total_jogos_aprovados: int
    total_jogos_rejeitados: int
    taxa_duplicidade: float
    best_hits: int
    average_best_hits: float
    median_best_hits: float
    average_hits: float
    count_10_exact: int
    count_11_exact: int
    count_12_exact: int
    count_13_exact: int
    count_14_exact: int
    count_15_exact: int
    count_11_plus: int
    count_12_plus: int
    count_13_plus: int
    count_14_plus: int
    count_15: int
    hit_histogram: dict[str, int]
    frequency_by_number: dict[str, int]
    frequency_maxima_dezena: int
    frequency_maxima_dezena_percentual: float
    frequency_minima_dezena_candidata: int
    frequency_minima_dezena_candidata_percentual: float
    repetition_distribution: dict[str, int]
    parity_profile_distribution: dict[str, int]
    low_high_distribution: dict[str, int]
    band_distribution: dict[str, int]
    sequence_distribution: dict[str, int]
    average_repetition: float
    average_sequence_max: float
    average_low: float
    average_high: float
    average_odd: float
    average_even: float
    alerts_concentracao: tuple[str, ...]
    alerts_ausencia: tuple[str, ...]
    alerts_paridade: tuple[str, ...]
    alerts_repeticao: tuple[str, ...]
    alerts_baixa_alta: tuple[str, ...]
    alerts_faixas: tuple[str, ...]
    alerts_sequencia: tuple[str, ...]
    contest_metrics: tuple[dict[str, Any], ...]
    game_metrics: tuple[dict[str, Any], ...]
    policy: dict[str, Any]
    status_comandante_cientifico: str
    classificacao_cientifica: str
    motivo_cientifico: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "game_size": self.game_size,
            "reference_contests": list(self.reference_contests),
            "validation_threshold": self.validation_threshold,
            "target_band": self.target_band,
            "validation_zone_label": self.validation_zone_label,
            "total_jogos_solicitados": self.total_jogos_solicitados,
            "total_jogos_gerados": self.total_jogos_gerados,
            "total_jogos_unicos": self.total_jogos_unicos,
            "total_jogos_duplicados": self.total_jogos_duplicados,
            "total_jogos_aprovados": self.total_jogos_aprovados,
            "total_jogos_rejeitados": self.total_jogos_rejeitados,
            "taxa_duplicidade": self.taxa_duplicidade,
            "best_hits": self.best_hits,
            "average_best_hits": self.average_best_hits,
            "median_best_hits": self.median_best_hits,
            "average_hits": self.average_hits,
            "count_10_exact": self.count_10_exact,
            "count_11_exact": self.count_11_exact,
            "count_12_exact": self.count_12_exact,
            "count_13_exact": self.count_13_exact,
            "count_14_exact": self.count_14_exact,
            "count_15_exact": self.count_15_exact,
            "count_11_plus": self.count_11_plus,
            "count_12_plus": self.count_12_plus,
            "count_13_plus": self.count_13_plus,
            "count_14_plus": self.count_14_plus,
            "count_15": self.count_15,
            "hit_histogram": dict(self.hit_histogram),
            "frequency_by_number": dict(self.frequency_by_number),
            "frequency_maxima_dezena": self.frequency_maxima_dezena,
            "frequency_maxima_dezena_percentual": self.frequency_maxima_dezena_percentual,
            "frequency_minima_dezena_candidata": self.frequency_minima_dezena_candidata,
            "frequency_minima_dezena_candidata_percentual": self.frequency_minima_dezena_candidata_percentual,
            "repetition_distribution": dict(self.repetition_distribution),
            "parity_profile_distribution": dict(self.parity_profile_distribution),
            "low_high_distribution": dict(self.low_high_distribution),
            "band_distribution": dict(self.band_distribution),
            "sequence_distribution": dict(self.sequence_distribution),
            "average_repetition": self.average_repetition,
            "average_sequence_max": self.average_sequence_max,
            "average_low": self.average_low,
            "average_high": self.average_high,
            "average_odd": self.average_odd,
            "average_even": self.average_even,
            "alerts_concentracao": list(self.alerts_concentracao),
            "alerts_ausencia": list(self.alerts_ausencia),
            "alerts_paridade": list(self.alerts_paridade),
            "alerts_repeticao": list(self.alerts_repeticao),
            "alerts_baixa_alta": list(self.alerts_baixa_alta),
            "alerts_faixas": list(self.alerts_faixas),
            "alerts_sequencia": list(self.alerts_sequencia),
            "contest_metrics": [dict(item) for item in self.contest_metrics],
            "game_metrics": [dict(item) for item in self.game_metrics],
            "policy": dict(self.policy),
            "status_comandante_cientifico": self.status_comandante_cientifico,
            "classificacao_cientifica": self.classificacao_cientifica,
            "motivo_cientifico": self.motivo_cientifico,
        }


def _classify_scientific_batch(
    *,
    best_hits: int,
    validation_threshold: int,
    validation_count_plus: int,
    count_11_plus: int,
    count_12_plus: int,
    total_unique: int,
    total_duplicates: int,
    frequency_max_percent: float,
    frequency_min_candidate_percent: float,
    alerts_concentracao: Sequence[str],
    alerts_ausencia: Sequence[str],
    alerts_paridade: Sequence[str],
    alerts_repeticao: Sequence[str],
    alerts_baixa_alta: Sequence[str],
    alerts_faixas: Sequence[str],
    alerts_sequencia: Sequence[str],
) -> tuple[str, str, str]:
    if total_duplicates > 0 or total_unique <= 0:
        return "REPROVADO", "REPROVADA", "duplicidade ou ausencia de jogos unicos"
    if best_hits < validation_threshold or validation_count_plus == 0:
        return (
            "REPROVADO",
            "APROVADA ESTRUTURALMENTE, REPROVADA CIENTIFICAMENTE",
            f"maior acerto < {validation_threshold} e zona principal inexistente",
        )

    strong_threshold = not alerts_concentracao and not alerts_ausencia and not alerts_paridade and not alerts_repeticao and not alerts_baixa_alta and not alerts_faixas and not alerts_sequencia
    if best_hits >= 13 and count_12_plus > 0 and frequency_max_percent <= 70.0 and frequency_min_candidate_percent >= 20.0 and strong_threshold:
        return "APROVADO", "APROVADA FORTE", "bateria com alta resposta estatistica"
    if best_hits >= validation_threshold and validation_count_plus > 0 and frequency_max_percent <= 70.0 and frequency_min_candidate_percent >= 20.0:
        if validation_threshold >= 13:
            return "APROVADO", "APROVADA MINIMA", "bateria estatisticamente saudavel"
        if validation_threshold == 12:
            return "APROVADO", "APROVADA MINIMA", "bateria estatisticamente saudavel"
        return "APROVADO", "APROVADA MODERADA", "bateria estatisticamente saudavel"
    return "REPROVADO", "REPROVADA", "alertas cientificos acima do limite"


def validate_scientific_batch(
    games: Sequence[Mapping[str, Any]] | Sequence[dict[str, Any]],
    reference_contests: Sequence[Mapping[str, Any]] | Sequence[dict[str, Any]],
    game_size: int,
    policy: Mapping[str, Any] | None = None,
    *,
    batch_id: str | None = None,
) -> dict[str, Any]:
    resolved_policy = dict(policy or get_scientific_generation_policy(game_size))
    validation_rule = _scientific_validation_rule(game_size)
    normalized_games = []
    invalid_games: list[dict[str, Any]] = []
    for index, game in enumerate(games, start=1):
        numbers = _normalize_numbers(_safe_get(game, "numbers", []))
        signature = _contest_signature({"numbers": numbers})
        errors: list[str] = []
        if len(numbers) != int(game_size):
            errors.append("quantidade_invalida")
        if len(numbers) != len(set(numbers)):
            errors.append("dezenas_duplicadas")
        if any(number < 1 or number > 25 for number in numbers):
            errors.append("dezenas_fora_do_intervalo")
        if not numbers:
            errors.append("jogo_vazio")
        if errors:
            invalid_games.append({"index": index, "signature": signature, "numbers": numbers, "errors": errors})
            continue
        normalized_games.append(
            {
                "index": index,
                "numbers": numbers,
                "signature": signature,
                "profile_type": str(_safe_get(game, "profile_type", _safe_get(game, "perfil", "")) or ""),
            }
        )

    normalized_references = [
        _normalize_contest(reference, default_contest=index + 1)
        for index, reference in enumerate(reference_contests)
        if _normalize_numbers(_safe_get(reference, "numbers", _safe_get(reference, "dezenas", [])))
    ]
    normalized_references = sorted(normalized_references, key=lambda item: int(item.get("contest_number", 0) or 0))

    total_requested = len(games)
    total_generated = len(normalized_games)
    total_unique = len({game["signature"] for game in normalized_games})
    total_duplicates = max(0, total_generated - total_unique)
    total_approved = total_unique
    total_rejected = max(0, total_requested - total_approved)
    tax_duplicity = round(total_duplicates / max(1, total_generated), 4)

    if not normalized_games or not normalized_references:
        status, classification, reason = "REPROVADO", "REPROVADA", "referencias ou jogos insuficientes"
        return ScientificBatchValidationReport(
            batch_id=str(batch_id or "").strip() or "scientific-global",
            game_size=int(game_size),
            reference_contests=tuple(item["contest_number"] for item in normalized_references),
            validation_threshold=int(validation_rule["validation_threshold"]),
            target_band=str(validation_rule["target_band"]),
            validation_zone_label=str(validation_rule["validation_zone_label"]),
            total_jogos_solicitados=total_requested,
            total_jogos_gerados=total_generated,
            total_jogos_unicos=total_unique,
            total_jogos_duplicados=total_duplicates,
            total_jogos_aprovados=total_approved,
            total_jogos_rejeitados=total_rejected,
            taxa_duplicidade=tax_duplicity,
            best_hits=0,
            average_best_hits=0.0,
            median_best_hits=0.0,
            average_hits=0.0,
            count_10_exact=0,
            count_11_exact=0,
            count_12_exact=0,
            count_13_exact=0,
            count_14_exact=0,
            count_15_exact=0,
            count_11_plus=0,
            count_12_plus=0,
            count_13_plus=0,
            count_14_plus=0,
            count_15=0,
            hit_histogram={str(number): 0 for number in range(16)},
            frequency_by_number={str(number): 0 for number in range(1, 26)},
            frequency_maxima_dezena=0,
            frequency_maxima_dezena_percentual=0.0,
            frequency_minima_dezena_candidata=0,
            frequency_minima_dezena_candidata_percentual=0.0,
            repetition_distribution={},
            parity_profile_distribution={},
            low_high_distribution={},
            band_distribution={},
            sequence_distribution={},
            average_repetition=0.0,
            average_sequence_max=0.0,
            average_low=0.0,
            average_high=0.0,
            average_odd=0.0,
            average_even=0.0,
            alerts_concentracao=("referencias_ou_jogos_insuficientes",),
            alerts_ausencia=(),
            alerts_paridade=(),
            alerts_repeticao=(),
            alerts_baixa_alta=(),
            alerts_faixas=(),
            alerts_sequencia=(),
            contest_metrics=(),
            game_metrics=(),
            policy=resolved_policy,
            status_comandante_cientifico=status,
            classificacao_cientifica=classification,
            motivo_cientifico=reason,
        ).as_dict()

    latest_reference = normalized_references[-1]
    reference_numbers = [contest["numbers"] for contest in normalized_references]
    per_game_metrics: list[dict[str, Any]] = []
    for game in normalized_games:
        hits_per_reference = [len(set(game["numbers"]) & set(reference_numbers[index])) for index in range(len(reference_numbers))]
        best_hits = max(hits_per_reference) if hits_per_reference else 0
        average_hits = round(mean(hits_per_reference), 4) if hits_per_reference else 0.0
        latest_overlap = len(set(game["numbers"]) & set(latest_reference["numbers"]))
        sequence_max = int(calculate_sequence_stats(game["numbers"])["largest_sequence"])
        parity_profile = _parity_profile(game["numbers"])
        low_high_profile = _low_high_profile(game["numbers"])
        band_counts = _band_distribution(game["numbers"])
        per_game_metrics.append(
            {
                "index": game["index"],
                "signature": game["signature"],
                "numbers": list(game["numbers"]),
                "best_hits": best_hits,
                "average_hits": average_hits,
                "latest_overlap": latest_overlap,
                "parity_profile": parity_profile,
                "low_high_profile": low_high_profile,
                "band_distribution": band_counts,
                "sequence_max": sequence_max,
            }
        )

    best_hits_values = [int(game["best_hits"]) for game in per_game_metrics]
    average_hits_values = [float(game["average_hits"]) for game in per_game_metrics]
    repetition_values = [int(game["latest_overlap"]) for game in per_game_metrics]
    sequence_values = [int(game["sequence_max"]) for game in per_game_metrics]
    low_values = [int(game["low_high_profile"].split("/", 1)[0]) for game in per_game_metrics]
    high_values = [int(game["low_high_profile"].split("/", 1)[1]) for game in per_game_metrics]
    odd_values = [int(game["parity_profile"].split("/", 1)[0]) for game in per_game_metrics]
    even_values = [int(game["parity_profile"].split("/", 1)[1]) for game in per_game_metrics]

    frequency_counter: Counter[int] = Counter()
    parity_counter: Counter[str] = Counter()
    low_high_counter: Counter[str] = Counter()
    band_counter: Counter[str] = Counter()
    sequence_counter: Counter[str] = Counter()
    for game in per_game_metrics:
        frequency_counter.update(game["numbers"])
        parity_counter.update([game["parity_profile"]])
        low_high_counter.update([game["low_high_profile"]])
        sequence_counter.update([str(game["sequence_max"])])
        band_counter.update(game["band_distribution"])

    frequency_by_number = {str(number): int(frequency_counter.get(number, 0)) for number in range(1, 26)}
    max_frequency = max(frequency_counter.values()) if frequency_counter else 0
    min_candidate_frequency = min((frequency_counter.get(number, 0) for number in resolved_policy.get("core_numbers", []) if frequency_counter.get(number, 0) > 0), default=0)
    max_frequency_percent = round((max_frequency / max(1, total_generated)) * 100, 4) if total_generated else 0.0
    min_candidate_frequency_percent = round((min_candidate_frequency / max(1, total_generated)) * 100, 4) if total_generated else 0.0

    contest_metrics: list[dict[str, Any]] = []
    for reference in normalized_references:
        contest_numbers = reference["numbers"]
        hits_per_game = [len(set(game["numbers"]) & set(contest_numbers)) for game in per_game_metrics]
        contest_metrics.append(
            {
                "contest_number": int(reference["contest_number"]),
                "draw_date": str(reference.get("draw_date", "")),
                "best_hits": max(hits_per_game) if hits_per_game else 0,
                "average_hits": round(mean(hits_per_game), 4) if hits_per_game else 0.0,
                "median_hits": round(median(hits_per_game), 4) if hits_per_game else 0.0,
                "count_11_plus": sum(1 for hits in hits_per_game if hits >= 11),
                "count_12_plus": sum(1 for hits in hits_per_game if hits >= 12),
                "count_13_plus": sum(1 for hits in hits_per_game if hits >= 13),
                "count_14_plus": sum(1 for hits in hits_per_game if hits >= 14),
                "count_15": sum(1 for hits in hits_per_game if hits >= 15),
            }
        )

    best_hits = max(best_hits_values) if best_hits_values else 0
    average_best_hits = round(mean(best_hits_values), 4) if best_hits_values else 0.0
    median_best_hits = round(median(best_hits_values), 4) if best_hits_values else 0.0
    average_hits = round(mean(average_hits_values), 4) if average_hits_values else 0.0
    hit_decomposition = _decompose_hit_counts(best_hits_values)
    validation_threshold = int(validation_rule["validation_threshold"])
    target_band = str(validation_rule["target_band"])
    validation_zone_label = str(validation_rule["validation_zone_label"])
    count_11_plus = sum(1 for hits in best_hits_values if hits >= 11)
    count_12_plus = sum(1 for hits in best_hits_values if hits >= 12)
    count_13_plus = sum(1 for hits in best_hits_values if hits >= 13)
    count_14_plus = sum(1 for hits in best_hits_values if hits >= 14)
    count_15 = sum(1 for hits in best_hits_values if hits >= 15)
    validation_count_plus = {
        11: count_11_plus,
        12: count_12_plus,
        13: count_13_plus,
    }[validation_threshold]

    repeat_min = int(resolved_policy.get("repeat_min", 0) or 0)
    repeat_max = int(resolved_policy.get("repeat_max", game_size) or game_size)
    allowed_parity_pairs = {tuple(pair) for pair in resolved_policy.get("allowed_parity_pairs", []) or []}
    preferred_parity_pairs = [tuple(pair) for pair in resolved_policy.get("preferred_parity_pairs", []) or []]
    sequence_max_allowed = int(resolved_policy.get("sequence_max", game_size) or game_size)
    coverage_min = float(resolved_policy.get("coverage_min", 0.0) or 0.0)
    entropy_min = float(resolved_policy.get("entropy_min", 0.0) or 0.0)
    max_frequency_ratio = float(resolved_policy.get("max_frequency_ratio", 1.0) or 1.0)
    min_frequency_ratio = float(resolved_policy.get("min_frequency_ratio", 0.0) or 0.0)
    core_numbers = [int(number) for number in resolved_policy.get("core_numbers", []) or []]
    discouraged_numbers = [int(number) for number in resolved_policy.get("discouraged_numbers", []) or []]

    latest_repetition_distribution = Counter(repetition_values)
    latest_parity_distribution = Counter(parity_counter)
    latest_low_high_distribution = Counter(low_high_counter)
    latest_sequence_distribution = Counter(sequence_counter)
    latest_band_distribution = Counter(band_counter)

    alerts_concentracao: list[str] = []
    alerts_ausencia: list[str] = []
    alerts_paridade: list[str] = []
    alerts_repeticao: list[str] = []
    alerts_baixa_alta: list[str] = []
    alerts_faixas: list[str] = []
    alerts_sequencia: list[str] = []

    average_sequence_max = round(mean(sequence_values), 4) if sequence_values else 0.0
    average_low = round(mean(low_values), 4) if low_values else 0.0
    average_high = round(mean(high_values), 4) if high_values else 0.0
    average_odd = round(mean(odd_values), 4) if odd_values else 0.0
    average_even = round(mean(even_values), 4) if even_values else 0.0

    if max_frequency_percent > max_frequency_ratio * 100:
        alerts_concentracao.append(
            f"frequencia_maxima={max_frequency_percent:.2f}% acima do teto {max_frequency_ratio * 100:.2f}%"
        )
    for number in core_numbers:
        number_percent = round((frequency_counter.get(number, 0) / max(1, total_generated)) * 100, 4) if total_generated else 0.0
        if number_percent < min_frequency_ratio * 100:
            alerts_ausencia.append(f"dezena_candidata_{number:02d}_abaixo_do_piso={number_percent:.2f}%")
    if preferred_parity_pairs and not any(tuple(map(int, pair.split("/", 1))) in allowed_parity_pairs for pair in latest_parity_distribution.keys()):
        alerts_paridade.append("perfil_de_paridade_fora_do_bloco_preferencial")
    if preferred_parity_pairs:
        preferred_usage = sum(latest_parity_distribution.get(f"{odd}/{even}", 0) for odd, even in preferred_parity_pairs)
        preferred_ratio = preferred_usage / max(1, total_generated)
        if preferred_ratio > 0.92:
            alerts_paridade.append(f"perfil_preferencial_concentrado={preferred_ratio:.2%}")
    if any(repetition < repeat_min or repetition > repeat_max for repetition in repetition_values):
        alerts_repeticao.append(f"repeticao_fora_da_faixa_{repeat_min}_a_{repeat_max}")
    average_repetition = round(mean(repetition_values), 4) if repetition_values else 0.0
    if average_repetition < repeat_min or average_repetition > repeat_max:
        alerts_repeticao.append(f"media_repeticao={average_repetition:.4f}")
    if average_low < 0 or average_high < 0:
        alerts_baixa_alta.append("distribuicao_baixa_alta_invalida")
    if any(sequence > sequence_max_allowed for sequence in sequence_values):
        alerts_sequencia.append(f"sequencia_acima_do_limite={sequence_max_allowed}")
    if not latest_band_distribution:
        alerts_faixas.append("faixas_sem_distribuicao")
    else:
        active_bands = sum(1 for amount in latest_band_distribution.values() if int(amount or 0) > 0)
        if active_bands < 3 and game_size >= 15:
            alerts_faixas.append("cobertura_de_faixas_insuficiente")
    if not alerts_paridade and allowed_parity_pairs and latest_parity_distribution:
        if not any(tuple(map(int, pair.split("/"))) in allowed_parity_pairs for pair in latest_parity_distribution.keys()):
            alerts_paridade.append("paridade_fora_do_perfil_permitido")

    status, classification, reason = _classify_scientific_batch(
        best_hits=best_hits,
        validation_threshold=validation_threshold,
        validation_count_plus=validation_count_plus,
        count_11_plus=count_11_plus,
        count_12_plus=count_12_plus,
        total_unique=total_unique,
        total_duplicates=total_duplicates,
        frequency_max_percent=max_frequency_percent,
        frequency_min_candidate_percent=min_candidate_frequency_percent,
        alerts_concentracao=alerts_concentracao,
        alerts_ausencia=alerts_ausencia,
        alerts_paridade=alerts_paridade,
        alerts_repeticao=alerts_repeticao,
        alerts_baixa_alta=alerts_baixa_alta,
        alerts_faixas=alerts_faixas,
        alerts_sequencia=alerts_sequencia,
    )

    return ScientificBatchValidationReport(
        batch_id=str(batch_id or "").strip() or "scientific-global",
        game_size=int(game_size),
        reference_contests=tuple(item["contest_number"] for item in normalized_references),
        validation_threshold=validation_threshold,
        target_band=target_band,
        validation_zone_label=validation_zone_label,
        total_jogos_solicitados=total_requested,
        total_jogos_gerados=total_generated,
        total_jogos_unicos=total_unique,
        total_jogos_duplicados=total_duplicates,
        total_jogos_aprovados=total_approved,
        total_jogos_rejeitados=total_rejected,
        taxa_duplicidade=tax_duplicity,
        best_hits=best_hits,
        average_best_hits=average_best_hits,
        median_best_hits=median_best_hits,
        average_hits=average_hits,
        count_10_exact=int(hit_decomposition["count_10_exact"]),
        count_11_exact=int(hit_decomposition["count_11_exact"]),
        count_12_exact=int(hit_decomposition["count_12_exact"]),
        count_13_exact=int(hit_decomposition["count_13_exact"]),
        count_14_exact=int(hit_decomposition["count_14_exact"]),
        count_15_exact=int(hit_decomposition["count_15_exact"]),
        count_11_plus=count_11_plus,
        count_12_plus=count_12_plus,
        count_13_plus=count_13_plus,
        count_14_plus=count_14_plus,
        count_15=count_15,
        hit_histogram=dict(hit_decomposition["hit_histogram"]),
        frequency_by_number=frequency_by_number,
        frequency_maxima_dezena=int(max_frequency),
        frequency_maxima_dezena_percentual=max_frequency_percent,
        frequency_minima_dezena_candidata=int(min_candidate_frequency),
        frequency_minima_dezena_candidata_percentual=min_candidate_frequency_percent,
        repetition_distribution={str(value): int(amount) for value, amount in sorted(latest_repetition_distribution.items())},
        parity_profile_distribution={key: int(amount) for key, amount in sorted(latest_parity_distribution.items())},
        low_high_distribution={key: int(amount) for key, amount in sorted(latest_low_high_distribution.items())},
        band_distribution={key: int(amount) for key, amount in sorted(latest_band_distribution.items())},
        sequence_distribution={key: int(amount) for key, amount in sorted(latest_sequence_distribution.items(), key=lambda item: int(item[0]))},
        average_repetition=average_repetition,
        average_sequence_max=average_sequence_max,
        average_low=average_low,
        average_high=average_high,
        average_odd=average_odd,
        average_even=average_even,
        alerts_concentracao=tuple(alerts_concentracao),
        alerts_ausencia=tuple(alerts_ausencia),
        alerts_paridade=tuple(alerts_paridade),
        alerts_repeticao=tuple(alerts_repeticao),
        alerts_baixa_alta=tuple(alerts_baixa_alta),
        alerts_faixas=tuple(alerts_faixas),
        alerts_sequencia=tuple(alerts_sequencia),
        contest_metrics=tuple(contest_metrics),
        game_metrics=tuple(per_game_metrics),
        policy=resolved_policy,
        status_comandante_cientifico=status,
        classificacao_cientifica=classification,
        motivo_cientifico=reason,
    ).as_dict()
