from __future__ import annotations

from lotoia.clients.whatsapp_service import format_games_whatsapp_message


def test_format_games_whatsapp_message_uses_institutional_footer() -> None:
    message = format_games_whatsapp_message(
        quantidade=3,
        games=[
            {"numbers": [2, 3, 4, 5, 8, 9, 10, 12, 14, 15, 16, 18, 21, 22, 25]},
            {"numbers": [1, 3, 4, 6, 8, 9, 11, 12, 14, 15, 16, 18, 22, 23, 25]},
            {"numbers": [1, 2, 3, 4, 5, 10, 11, 12, 13, 14, 16, 17, 18, 23, 24]},
        ],
        targets=[(15, 3)],
    )

    assert "🎯 *Seus jogos LotoIA — 15D*" in message
    assert "Jogo 01: 02 03 04 05 08 09 10 12 14 15 16 18 21 22 25" in message
    assert "✅ Gerado com estatística estrutural" in message
    assert "⚠️ Jogue com responsabilidade" in message
    assert "Boa sorte" not in message


def test_format_games_whatsapp_message_dual_format_header() -> None:
    message = format_games_whatsapp_message(
        quantidade=5,
        games=[
            {"numbers": list(range(1, 16)), "formato_cartao": 15},
            {"numbers": list(range(1, 17)), "formato_cartao": 16},
        ],
        targets=[(15, 3), (16, 2)],
    )

    assert "🎯 *Seus jogos LotoIA — 15D e 16D*" in message
    assert "Jogo 01 (15D):" in message
    assert "⚠️ Jogue com responsabilidade" in message
