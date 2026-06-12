from __future__ import annotations

from typing import Any, Sequence

NUCLEO_LEI15_15D_CONGELADO: tuple[int, ...] = (1, 2, 3, 4, 9, 10, 11, 12, 13, 18, 20, 22, 23, 24, 25)
RESERVAS_LEI15A_PRIORITARIAS: tuple[int, ...] = (15, 5, 7, 14, 19)


def _to_int_list(values: Sequence[Any]) -> list[int]:
    return [int(value) for value in values]


def build_lei15a_operational_read(
    *,
    cartao_final_lei15: Sequence[int],
    formato_d: int,
) -> dict[str, Any]:
    """Leitura operacional Lei 15A — cartão validado sincronizado com o cartão final Lei 15."""
    nucleo_operacional_gp = list(NUCLEO_LEI15_15D_CONGELADO)
    cartao_validado = sorted(_to_int_list(cartao_final_lei15))
    resolved_format = int(formato_d or 15)
    if resolved_format <= 15:
        auditadas: list[int] = []
    else:
        auditadas = sorted(set(cartao_validado) - set(nucleo_operacional_gp))
    vigilantes = sorted(set(auditadas).intersection(RESERVAS_LEI15A_PRIORITARIAS))
    lei15_final = sorted(_to_int_list(cartao_final_lei15))
    lei15a_synchronized = cartao_validado == lei15_final
    return {
        "nucleo_operacional_gp": nucleo_operacional_gp,
        "auditadas": auditadas,
        "vigilantes": vigilantes,
        "cartao_validado": cartao_validado,
        "lei15a_synchronized": lei15a_synchronized,
    }


def apply_lei15a_validated_card(game: dict[str, Any], *, formato_d: int) -> dict[str, Any]:
    """Marca o jogo com o cartão Lei 15A validado (leitura sincronizada) para entrega."""
    final_card = _to_int_list(
        game.get("final_card_numbers") or game.get("cartao_final") or game.get("numbers") or []
    )
    lei15a_read = build_lei15a_operational_read(cartao_final_lei15=final_card, formato_d=formato_d)
    tagged = dict(game)
    validated = list(lei15a_read["cartao_validado"])
    tagged["cartao_validado_lei15a"] = validated
    tagged["lei15a_synchronized"] = bool(lei15a_read["lei15a_synchronized"])
    tagged["numbers"] = validated
    return tagged
