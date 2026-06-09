# ADR-039 — Experimento de Calibração de Overlap no Premium 18

## Status
Experimental

## Contexto

Foi executado um experimento controlado para avaliar se a calibragem de overlap entre representantes operacionais melhora a faixa 11+ sem colapsar a pluralidade operacional.

Escopo do teste:
- pacote premium 18 dezenas
- amostra de 10 concursos
- modo HB
- top-5 e top-10
- overlap máximo 15, 14 e 13

## Resultado

Os cenários medidos convergiram para o mesmo perfil estrutural:
- operational_bets = 5
- 11+ = 8
- 12+ = 1
- avg_hits aproximadamente entre 9.14 e 9.16
- avg_overlap aproximadamente entre 12.6 e 12.7
- unique_ratio_real = 1.0

## Observação experimental

Nos cenários testados:
- top-5 e top-10 tiveram comportamento praticamente idêntico
- ajustar overlap máximo entre 13, 14 e 15 não alterou significativamente o lote
- o efeito principal já estava concentrado na saída top-N, e não no refinamento do limite de overlap

## Conclusão

Os resultados sugerem que:
- sair do top-1 ajuda a ampliar a faixa 11+
- top-5 já captura praticamente o ganho observado neste recorte
- top-10 não trouxe ganho adicional relevante nessa amostra
- overlap 13/14/15 não mudou de forma significativa o lote
- o gargalo permanece anterior ao filtro final: o pool ainda nasce centrado

## Decisão

Não implementar distância estrutural rígida neste momento.

A próxima hipótese experimental deve investigar a diversificação do pool inicial, e não apenas o filtro final de overlap.

## Restrições

Não alterar permanentemente:
- scoring core
- rerank ML
- benchmark histórico
- temporal
- scientific expansion engine

Este ADR registra apenas o resultado experimental e a decisão institucional derivada.
