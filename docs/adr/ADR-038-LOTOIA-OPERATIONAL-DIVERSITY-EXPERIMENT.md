# ADR-038 — Auditoria Experimental de Diversidade Estrutural Operacional

## Status
Experimental

## Contexto

Após a auditoria ADR-037, foi identificado que:
- o candidate space premium é amplo
- a diversidade inicial existe
- mas a camada operacional reduz o lote a top-1 por modo

Foi executado replay experimental comparando:
- top-1
- top-3
- top-5
- top-10

nos modos:
- HB
- IA

com pacote premium 18 dezenas.

## Resultado Experimental

### Efeito da pluralidade operacional

Aumentar top-N:
- aumenta operational_bets
- aumenta frequência de 11+
- preserva unique_ratio_real = 1.0

Resultados HB:
- top-1 -> 11+ = 1
- top-3 -> 11+ = 4
- top-5 -> 11+ = 8
- top-10 -> 11+ = 16

Resultados IA:
- top-1 -> 11+ = 1
- top-3 -> 11+ = 2
- top-5 -> 11+ = 5
- top-10 -> 11+ = 11

## Limitação observada

Apesar do ganho de recall estatístico:
- overlap médio aumentou fortemente
- a média por ticket permaneceu quase estável
- os candidatos continuaram orbitando núcleos dominantes similares

Overlap observado:
- HB ~ 12.6-12.66
- IA ~ 13.6-14.0

## Conclusão Parcial

Pluralidade operacional ajuda a abrir a faixa 11+.

Porém:
- volume sozinho não resolve compressão estrutural
- diversidade superficial não equivale a dispersão matemática real
- top-N puro ainda converge para regiões muito semelhantes do espaço combinatório

## Hipótese Científica Atual

A hipótese mais forte passa a ser:

“pluralidade operacional só produz ganho consistente quando acompanhada de diversidade estrutural calibrada”.

## Próxima Auditoria Experimental

A próxima trilha deverá investigar:

- top-N + distância estrutural mínima
- penalização de overlap
- diversidade entre clusters
- dispersão efetiva do candidate space

## Restrições

Não alterar permanentemente:
- scoring core
- rerank ML
- benchmark histórico
- temporal
- scientific expansion engine

Todos os testes devem permanecer:
- paralelos
- reproduzíveis
- comparáveis ao baseline institucional

## Decisão

O projeto entra em fase experimental de:
“pluralidade operacional com diversidade estrutural controlada”.
