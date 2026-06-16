"""Métricas observacionais da estrutura do cartão (sem efeito em geração)."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from lotoia.statistics.advanced import (
    calculate_column_distribution,
    calculate_frame_center_distribution,
    calculate_line_distribution,
)
from lotoia.statistics.patterns import odd_even_distribution
from lotoia.statistics.temporal import calculate_sequence_stats, find_sequences

FULL_DEZENAS = tuple(range(1, 26))
BAIXAS = tuple(range(1, 6))
MEDIAS = tuple(range(6, 16))
ALTAS = tuple(range(16, 26))
NEAR_DUPLICATE_OVERLAP = 13


@dataclass(frozen=True)
class DrawAdapter:
    numbers: list[int]


def extract_int_numbers(raw: Sequence[int | str] | str | None) -> list[int]:
    if isinstance(raw, str):
        tokens = raw.replace(",", " ").split()
    elif raw is None:
        tokens = []
    else:
        tokens = list(raw)
    numbers: list[int] = []
    for token in tokens:
        text = str(token).strip().lstrip("+")
        if not text:
            continue
        try:
            value = int(text)
        except ValueError:
            continue
        if 1 <= value <= 25:
            numbers.append(value)
    return sorted(set(numbers))


def resolve_cartao_final_from_game(game: dict[str, Any]) -> list[int]:
    """Resolve cartão final observado (generated_games / reconciliation_games)."""
    for key in (
        "final_card_numbers",
        "cartao_final",
        "cartão_final",
        "numbers",
        "dezenas",
    ):
        raw = game.get(key)
        if raw is None:
            continue
        if isinstance(raw, str):
            numbers = extract_int_numbers(raw)
        else:
            numbers = extract_int_numbers(list(raw))
        if numbers:
            return numbers
    return []


def compute_prefix(numbers: Sequence[int], size: int) -> tuple[int, ...]:
    ordered = sorted(int(number) for number in numbers)
    if not ordered:
        return tuple()
    return tuple(ordered[: min(size, len(ordered))])


def compute_suffix(numbers: Sequence[int], size: int) -> tuple[int, ...]:
    ordered = sorted(int(number) for number in numbers)
    if not ordered:
        return tuple()
    return tuple(ordered[-min(size, len(ordered)) :])


def format_dezena_group(values: Sequence[int]) -> str:
    return "-".join(f"{int(value):02d}" for value in values)


def compute_gaps(numbers: Sequence[int]) -> list[int]:
    ordered = sorted(int(number) for number in numbers)
    if len(ordered) < 2:
        return []
    return [ordered[index + 1] - ordered[index] for index in range(len(ordered) - 1)]


def compute_band_counts(numbers: Sequence[int]) -> dict[str, int]:
    ordered = {int(number) for number in numbers}
    return {
        "baixas_01_05": sum(1 for number in ordered if number in BAIXAS),
        "medias_06_15": sum(1 for number in ordered if number in MEDIAS),
        "altas_16_25": sum(1 for number in ordered if number in ALTAS),
    }


def compute_density_by_band(numbers: Sequence[int]) -> dict[str, float]:
    counts = compute_band_counts(numbers)
    total = max(len(set(numbers)), 1)
    return {
        key: round(value / total, 4)
        for key, value in counts.items()
    }


def compute_missing_dezenas(numbers: Sequence[int], *, universe: Iterable[int] = FULL_DEZENAS) -> list[int]:
    present = {int(number) for number in numbers}
    return sorted(set(universe) - present)


def compute_card_structure_metrics(numbers: Sequence[int]) -> dict[str, Any]:
    cartao = sorted({int(number) for number in numbers if 1 <= int(number) <= 25})
    draw = DrawAdapter(cartao)
    gaps = compute_gaps(cartao)
    sequences = find_sequences(cartao)
    seq_stats = calculate_sequence_stats(cartao)
    odd_even = odd_even_distribution(cartao)
    bands = compute_band_counts(cartao)
    return {
        "game_size": len(cartao),
        "cartao_final": [f"{number:02d}" for number in cartao],
        "dezenas_presentes": cartao,
        "dezenas_ausentes": compute_missing_dezenas(cartao),
        "prefixo_2": format_dezena_group(compute_prefix(cartao, 2)),
        "prefixo_3": format_dezena_group(compute_prefix(cartao, 3)),
        "prefixo_4": format_dezena_group(compute_prefix(cartao, 4)),
        "sufixo_2": format_dezena_group(compute_suffix(cartao, 2)),
        "sufixo_3": format_dezena_group(compute_suffix(cartao, 3)),
        "sufixo_4": format_dezena_group(compute_suffix(cartao, 4)),
        **bands,
        "pares": int(odd_even["even"]),
        "impares": int(odd_even["odd"]),
        "soma_total": sum(cartao),
        "sequencias": sequences,
        "maior_sequencia": int(seq_stats.get("largest_sequence", 0) or 0),
        "gaps_entre_dezenas": gaps,
        "maior_gap": max(gaps) if gaps else 0,
        "densidade_por_faixa": compute_density_by_band(cartao),
        "linhas": calculate_line_distribution(draw),
        "colunas": calculate_column_distribution(draw),
        **calculate_frame_center_distribution(draw),
    }


def compute_gp_redundancy(games: Sequence[Sequence[int]]) -> dict[str, Any]:
    normalized = [sorted({int(number) for number in game}) for game in games if game]
    if len(normalized) < 2:
        return {
            "similaridade_media_entre_jogos": 0.0,
            "sobreposicao_media": 0.0,
            "sobreposicao_maxima": 0.0,
            "cartoes_quase_repetidos": 0,
            "pair_count": 0,
        }
    overlaps: list[int] = []
    near_duplicate_pairs = 0
    pair_count = 0
    for left_index, left in enumerate(normalized):
        left_set = set(left)
        for right in normalized[left_index + 1 :]:
            overlap = len(left_set & set(right))
            overlaps.append(overlap)
            pair_count += 1
            if overlap >= NEAR_DUPLICATE_OVERLAP:
                near_duplicate_pairs += 1
    game_size = max((len(game) for game in normalized), default=15)
    return {
        "similaridade_media_entre_jogos": round(sum(overlaps) / pair_count / game_size, 4) if pair_count else 0.0,
        "sobreposicao_media": round(sum(overlaps) / pair_count, 4) if pair_count else 0.0,
        "sobreposicao_maxima": max(overlaps) if overlaps else 0,
        "cartoes_quase_repetidos": near_duplicate_pairs,
        "pair_count": pair_count,
    }


def _frequency_counter(cards: Sequence[Sequence[int]], *, extractor) -> Counter[str]:
    counter: Counter[str] = Counter()
    for card in cards:
        key = extractor(card)
        if key:
            counter[key] += 1
    return counter


def compare_structure_profiles(
    generated_cards: Sequence[Sequence[int]],
    official_cards: Sequence[Sequence[int]],
) -> dict[str, Any]:
    generated = [sorted({int(number) for number in card}) for card in generated_cards if card]
    official = [sorted({int(number) for number in card}) for card in official_cards if card]
    if not generated:
        return {
            "available": False,
            "estruturas_mais_geradas_pela_LotoIA": [],
            "estruturas_mais_frequentes_nos_concursos": [],
            "estruturas_pouco_cobertas_pela_LotoIA": [],
            "prefixos_oficiais_raros_na_LotoIA": [],
            "prefixos_LotoIA_excessivos": [],
        }

    def top(counter: Counter[str], limit: int = 5) -> list[dict[str, Any]]:
        return [
            {"estrutura": key, "frequencia": count}
            for key, count in counter.most_common(limit)
        ]

    gen_prefix3 = _frequency_counter(generated, extractor=lambda card: format_dezena_group(compute_prefix(card, 3)))
    off_prefix3 = _frequency_counter(official, extractor=lambda card: format_dezena_group(compute_prefix(card, 3)))
    gen_prefix4 = _frequency_counter(generated, extractor=lambda card: format_dezena_group(compute_prefix(card, 4)))
    off_prefix4 = _frequency_counter(official, extractor=lambda card: format_dezena_group(compute_prefix(card, 4)))
    gen_suffix3 = _frequency_counter(generated, extractor=lambda card: format_dezena_group(compute_suffix(card, 3)))
    off_suffix3 = _frequency_counter(official, extractor=lambda card: format_dezena_group(compute_suffix(card, 3)))

    official_rare_in_lotoia = [
        {"prefixo_3": key, "frequencia_oficial": count, "frequencia_lotoia": gen_prefix3.get(key, 0)}
        for key, count in off_prefix3.items()
        if gen_prefix3.get(key, 0) == 0
    ][:5]
    lotoia_excessive = [
        {
            "prefixo_3": key,
            "frequencia_lotoia": count,
            "frequencia_oficial": off_prefix3.get(key, 0),
        }
        for key, count in gen_prefix3.items()
        if count >= 2 and off_prefix3.get(key, 0) <= 0
    ][:5]

    low_coverage = [
        {
            "prefixo_3": key,
            "frequencia_lotoia": count,
            "frequencia_oficial": off_prefix3.get(key, 0),
        }
        for key, count in gen_prefix3.items()
        if count == 1
    ][:5]

    return {
        "available": True,
        "prefixo_3": {"lotoia": top(gen_prefix3), "oficial": top(off_prefix3)},
        "prefixo_4": {"lotoia": top(gen_prefix4), "oficial": top(off_prefix4)},
        "sufixo_3": {"lotoia": top(gen_suffix3), "oficial": top(off_suffix3)},
        "sufixo_4": {
            "lotoia": top(_frequency_counter(generated, extractor=lambda card: format_dezena_group(compute_suffix(card, 4)))),
            "oficial": top(_frequency_counter(official, extractor=lambda card: format_dezena_group(compute_suffix(card, 4)))),
        },
        "faixas_baixas_medias_altas": {
            "lotoia": top(_frequency_counter(generated, extractor=lambda card: str(compute_band_counts(card)))),
            "oficial": top(_frequency_counter(official, extractor=lambda card: str(compute_band_counts(card)))),
        },
        "gaps": {
            "lotoia": top(_frequency_counter(generated, extractor=lambda card: str(compute_gaps(card)))),
            "oficial": top(_frequency_counter(official, extractor=lambda card: str(compute_gaps(card)))),
        },
        "sequencias": {
            "lotoia": top(_frequency_counter(generated, extractor=lambda card: str(find_sequences(card)))),
            "oficial": top(_frequency_counter(official, extractor=lambda card: str(find_sequences(card)))),
        },
        "ausencias": {
            "lotoia": top(_frequency_counter(generated, extractor=lambda card: format_dezena_group(compute_missing_dezenas(card)))),
            "oficial": top(_frequency_counter(official, extractor=lambda card: format_dezena_group(compute_missing_dezenas(card)))),
        },
        "estruturas_mais_geradas_pela_LotoIA": top(gen_prefix3),
        "estruturas_mais_frequentes_nos_concursos": top(off_prefix3),
        "estruturas_pouco_cobertas_pela_LotoIA": low_coverage,
        "prefixos_oficiais_raros_na_LotoIA": official_rare_in_lotoia,
        "prefixos_LotoIA_excessivos": lotoia_excessive,
    }


def analyze_stuck_games(
    games: Sequence[dict[str, Any]],
    *,
    official_numbers: Sequence[int] | None = None,
) -> dict[str, Any]:
    stuck_13: list[dict[str, Any]] = []
    stuck_14: list[dict[str, Any]] = []
    missing_for_14_counter: Counter[int] = Counter()
    missing_for_15_counter: Counter[int] = Counter()

    for game in games:
        cartao = resolve_cartao_final_from_game(game)
        if not cartao:
            continue
        game_official = extract_int_numbers(list(game.get("official_numbers") or official_numbers or []))
        official_set = set(game_official)
        hits = int(game.get("hits") or 0)
        if hits <= 0 and official_set:
            hits = len(set(cartao) & official_set)
        metrics = compute_card_structure_metrics(cartao)
        missing = sorted(official_set - set(cartao))
        row = {
            "game_index": int(game.get("game_index") or 0),
            "generation_event_id": int(game.get("generation_event_id") or 0),
            "reconciliation_run_id": int(game.get("reconciliation_run_id") or 0),
            "hits": hits,
            "cartao_final": metrics["cartao_final"],
            "estrutura": metrics,
            "dezenas_faltantes": [f"{number:02d}" for number in missing],
        }
        if hits == 13:
            stuck_13.append(row)
            for number in missing:
                missing_for_14_counter[number] += 1
        elif hits == 14:
            stuck_14.append(row)
            for number in missing:
                missing_for_15_counter[number] += 1

    return {
        "jogos_com_13_hits": stuck_13,
        "jogos_com_14_hits": stuck_14,
        "dezenas_faltantes_para_14": [
            {"dezena": f"{number:02d}", "frequencia": count}
            for number, count in missing_for_14_counter.most_common()
        ],
        "dezenas_faltantes_para_15": [
            {"dezena": f"{number:02d}", "frequencia": count}
            for number, count in missing_for_15_counter.most_common()
        ],
    }
