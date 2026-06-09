# Regra Executável de Montagem 16D

## 1. Resumo executivo

Esta missão corrige o bloqueio arquitetural da expansão 16D ao definir uma regra executável, rastreável e reversível para escolha da 16ª dezena em cada jogo 15D.

O conceito `16D = 15 + 1` permanece correto. O bloqueio anterior não era conceitual, mas sim a ausência de uma regra objetiva de escolha da 16ª dezena. Sem essa regra, qualquer composição 16D seria inferência indevida.

Nesta missão:

- nenhuma célula 16D foi classificada;
- nenhuma métrica de desempenho foi executada;
- nenhuma geração operacional foi feita;
- a Lei 15 permaneceu preservada.

## 2. Problema identificado

O bloqueio da validação executiva 16D ocorreu porque não existia regra objetiva para definir a 16ª dezena de cada jogo 15D.

Sem essa regra:

- a composição 16D não pode ser fechada;
- não há rastreabilidade suficiente;
- a construção das células 16D Top 10/20/30/50 fica impedida;
- o processo corre risco de inferência indevida.

## 3. Correção arquitetural

A correção consiste em formalizar uma regra executável única para montagem 16D:

1. carregar as 15 dezenas do jogo-base;
2. listar as dezenas ausentes entre 01 e 25;
3. cruzar as ausentes com J12 e J34;
4. priorizar dezenas presentes em J12 e J34;
5. desempatar por menor redundância com o jogo-base;
6. persistindo empate, desempatar por maior contribuição lateral;
7. J71 só entra como fonte de vigilância ou em cenário comparativo controlado;
8. a dezena escolhida só pode ser adicionada se ainda não existir no jogo-base;
9. o resultado deve ter exatamente 16 dezenas;
10. toda escolha deve registrar fonte, justificativa e reversibilidade.

## 4. Conceito 16D = 15 + 1

O conceito institucional permanece:

- 15D = núcleo fechado;
- 16D = 15 + 1;
- 16D é expansão observacional derivada do 15D fechado;
- 16D não substitui a Lei 15;
- 16D não recalibra a Lei 15.

## 5. Fontes auditadas

### Nível 1 — Fonte principal

- J12
- J34

### Nível 2 — Fonte em vigilância

- J71

Regra institucional:

- J71 não compete em igualdade automática com J12/J34.
- J71 serve como reserva de vigilância ou cenário alternativo controlado.

## 6. Regra executável da 16ª dezena

Para cada jogo 15D:

- carregar as 15 dezenas originais;
- calcular as dezenas ausentes entre 01 e 25;
- identificar candidatas em J12/J34;
- escolher a candidata auditada que melhor respeite o núcleo estrutural;
- se não houver candidata válida em J12/J34, registrar impedimento específico;
- apenas em cenário autorizado posterior, J71 pode ser usado como vigilância.

Regras obrigatórias:

- a 16ª dezena deve ser ausente do jogo-base;
- a 16ª dezena deve ter fonte auditada;
- o jogo final deve ter exatamente 16 dezenas;
- a escolha deve ser reversível e rastreável.

## 7. Critérios de prioridade

1. Candidata presente em J12 e J34 vence candidata presente em apenas uma fonte.
2. Candidata ausente do jogo-base é obrigatória.
3. Candidata que reduz concentração excessiva vence candidata que aumenta clone.
4. Candidata com maior contribuição lateral vence candidata redundante.
5. Candidata oriunda de J71 só entra se marcada como vigilância.
6. Se não houver candidata auditada válida, o jogo fica impedido com motivo específico.

## 8. Critérios de desempate

Os desempates devem seguir a seguinte ordem:

1. presença simultânea em J12 e J34;
2. menor redundância com o jogo-base;
3. maior contribuição lateral;
4. menor risco de clone;
5. rastreabilidade documental mais clara.

## 9. Uso restrito do J71

J71 é reserva em vigilância auditada.

Uso permitido nesta missão:

- vigilância documental;
- cenário comparativo controlado;
- fallback institucional apenas quando explicitamente autorizado em missão posterior.

Uso proibido:

- competir automaticamente com J12/J34;
- reabilitar grupo antigo;
- virar fonte principal por conveniência;
- ser usado sem registro de vigilância.

## 10. Saída esperada por jogo

Para cada jogo 15D, a regra deve produzir:

- `jogo_id`;
- `dezenas_15d_originais`;
- `candidatas_ausentes`;
- `fonte_da_candidata`;
- `dezena_escolhida`;
- `justificativa`;
- `status_da_fonte`:
  - `reserva_condicional_auditada`;
  - `reserva_em_vigilancia_auditada`;
- `dezenas_16d_resultantes`;
- `reversibilidade`;
- `impedimento`, se houver.

## 11. Limites da missão

Esta missão:

- não executa validação por célula;
- não executa métricas de desempenho;
- não constrói Top 10/20/30/50;
- não escolhe escala vencedora;
- não inicia 17D;
- não faz push;
- não altera a Lei 15.

## 12. Estado das células 16D

As células 16D Top 10/20/30/50 continuam pendentes de validação por célula.

Esta missão apenas define a regra executável necessária para que a próxima etapa consiga construir:

- 16D Top 10;
- 16D Top 20;
- 16D Top 30;
- 16D Top 50.

## 13. Próxima missão

Próxima missão prevista:

> Construção das células 16D com base na regra executável aprovada.

Essa próxima etapa deverá aplicar a regra formalizada neste relatório para montar as células 16D Top 10/20/30/50.

## 14. Confirmações finais

- Não houve geração operacional.
- Não houve push.
- Lei 15 não foi alterada.
- Nenhuma célula 16D foi classificada.
- Nenhuma métrica de desempenho foi executada.
- Nenhuma escala 16D foi promovida.
- 17D não foi iniciado.
- A missão apenas definiu a regra executável para montagem 16D.

## 15. Conclusão institucional

A LotoIA passa a ter uma regra objetiva, auditável e reversível para escolher a 16ª dezena de cada jogo 15D, preservando a Lei 15 e impedindo inferência sem fonte.

O bloqueio arquitetural foi resolvido como regra de montagem, não como validação de desempenho.
