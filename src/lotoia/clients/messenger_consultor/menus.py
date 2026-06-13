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
    "📊 Planos a partir de R$15,99/mês\n"
    "👉 www.lotoia.chat\n\n"
    "Após assinar, volte aqui e gere seus jogos direto no Messenger. 🚀"
)

PLANOS_MESSAGE = (
    "📊 Planos LotoIA — 30 dias de acesso:\n\n"
    "Básico R$15,99 | Plus R$29,99 | Avançado R$39,99\n"
    "Pro R$49,99 | Master R$59,99 | Elite R$69,99\n\n"
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
        "🎯 GERAR       → ex: 5x15D, 3x18D\n\n"
        f"Plano: {plano} | Jogos hoje: {jogos_hoje}/30 | Saldo: {saldo_hoje}"
    )
