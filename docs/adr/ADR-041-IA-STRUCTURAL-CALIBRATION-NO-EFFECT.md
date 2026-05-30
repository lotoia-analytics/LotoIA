# ADR-041 - IA Estrutural Sem Efeito Mensuravel na Calibracao Testada

## Status
Accepted

## Contexto

Foi executado um benchmark experimental paralelo para avaliar se a IA estrutural interna altera a geometria operacional do pool HB sem degradar a estabilidade do baseline.

Recorte do teste:
- 30 concursos
- pacote 18
- top-5 operacional
- mesma janela historica
- mesmo seed

Os cenarios avaliados foram:
- HB baseline
- IA estrutural leve
- IA estrutural moderada
- IA estrutural forte controlada
- IA estrutural forte + limite de seguranca

## Resultado

No recorte medido, todos os cenarios convergiram para o mesmo perfil estatistico:
- avg_hits = 9.1333
- 11+ = 21
- 12+ = 5
- best = 13
- avg_overlap = 0.8867
- entropy = 1.0
- unique_ratio_real = 1.0
- stability_sd = 0.5246

## Conclusao

A IA estrutural, nas intensidades testadas:
- observa
- regula
- nao degrada
- mas ainda nao influencia a selecao final de forma mensuravel

Em outras palavras, a camada estrutural permanece segura e auditavel, mas ainda nao deslocou a geometria operacional do pool HB no benchmark analisado.

## Decisao

A IA estrutural nao deve ser promovida para producao neste momento.

## Proxima Hipotese

O proximo ganho provavel da plataforma deve exigir:
- intervencao direta na geometria do pool inicial
- ou ajuste da politica de selecao

e nao apenas regulacao posterior leve.

## Restricoes

Nao alterar permanentemente:
- scoring core
- benchmark oficial
- temporal V1
- scientific expansion engine

Este ADR registra apenas a calibracao experimental e o efeito nulo mensuravel observado no recorte testado.
