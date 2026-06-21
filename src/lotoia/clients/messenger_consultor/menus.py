from __future__ import annotations

MENU_CURIOSO = (
    "👋 Olá! Sou a LotoIA.\n"
    "Análise estatística real da Lotofácil.\n\n"
    "O que você quer ver?\n\n"
    "📊 RESULTADO   → conferência por concurso\n"
    "⏳ ATRASADAS   → dezenas que mais faltam\n"
    "📈 FREQUENTES  → dezenas que mais saem\n"
    "🏆 SCORE       → desempenho do núcleo LotoIA\n"
    "🔍 CONFERIR    → confira seu jogo (3 grátis)\n\n"
    "Digite qualquer opção acima! 👆"
)

CONFERIR_PROMPT = (
    "🔍 Conferência de jogo\n\n"
    "Envie as 15 dezenas do seu jogo.\n"
    "Exemplo: 01 03 05 07 09 11 13 15 17 19 20 21 22 23 24"
)

GERAR_CURIOSO_MESSAGE = (
    "🎯 Para gerar jogos seja assinante LotoIA!\n\n"
    "📊 Plano Completo — R$99,90\n"
    "7 dias (15D) + 12 meses (15D + 20D)\n"
    "👉 www.lotoia.chat\n\n"
    "Após assinar, volte aqui e gere seus jogos direto no Messenger. 🚀"
)

PLANOS_MESSAGE = (
    "📊 Plano LotoIA Completo — R$99,90\n\n"
    "• 7 primeiros dias: 30 jogos/dia em 15D\n"
    "• Depois: 30 jogos/dia em 15D + 20D por 12 meses\n\n"
    "👉 www.lotoia.chat"
)


def menu_cliente_ativo(*, nome: str, plano: str, jogos_hoje: int, saldo_hoje: int) -> str:
    display_name = str(nome or "Cliente").strip() or "Cliente"
    return (
        f"🤖 LotoIA — Bem-vindo de volta, {display_name}!\n\n"
        "📊 RESULTADO   → conferência por concurso\n"
        "⏳ ATRASADAS   → dezenas que mais faltam\n"
        "📈 FREQUENTES  → dezenas que mais saem\n"
        "🏆 SCORE       → desempenho do núcleo LotoIA\n"
        "🔍 CONFERIR    → confira qualquer jogo\n"
        "🎯 GERAR       → ex: 1015D, 5x15D, 520D\n\n"
        f"Plano: LotoIA Completo | Jogos hoje: {jogos_hoje}/30 | Saldo: {saldo_hoje}"
    )
