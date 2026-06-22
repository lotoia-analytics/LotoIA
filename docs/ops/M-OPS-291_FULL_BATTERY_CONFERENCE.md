# M-OPS-291 — Conferência completa por bateria

## Problema

As últimas sessões GP:50 + GP:20 de 15D geraram mais jogos do que foram conferidos. Exemplo operacional:

- 3 × GP:50 = 150 jogos
- 2 × GP:20 = 40 jogos
- total bruto esperado = 190 jogos
- total conferido observado = 35 jogos

## Causa

`filter_conference_games()` aplicava promoção parcial mesmo quando o lote inteiro já estava oficialmente elegível para conferência. Assim, o Conferir usava apenas `games_promoted_to_conference` em vez de todos os jogos persistidos do lote.

## Correção

Quando o lote é oficialmente conferível (`is_official_conference_eligible`), `filter_conference_games()` retorna todos os jogos persistidos.

A promoção parcial continua válida apenas para lote não oficializado/rejeitado que possui jogos individualmente promovidos.

## Regra

- lote oficial/conferível: conferir todos os jogos persistidos;
- lote não oficial com promoção parcial: conferir somente jogos promovidos;
- sem alteração de BD, schema, migration ou histórico.
