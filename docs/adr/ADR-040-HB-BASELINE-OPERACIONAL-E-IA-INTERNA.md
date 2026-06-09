# ADR-040 - HB como Baseline Operacional e IA como Camada Cientifica Interna

## Status
Accepted

## Contexto

A avaliacao comparativa recente entre HB puro e IA puro no pacote premium 18, com:
- ultimos 30 concursos
- 15 jogos
- mesma janela historica
- mesmo seed
- top-5 operacional

indicou que HB apresentou desempenho operacional superior no recorte medido.

Resultados observados:
- HB com maior media de acertos
- HB com maior frequencia de 11+
- HB com maior frequencia de 12+
- HB com overlap medio menor
- HB com estabilidade por concurso ligeiramente melhor

Ao mesmo tempo, a abertura controlada do pool HB indicou sinal positivo quando a exploracao estrutural foi levemente ampliada, ainda sem comprometer de forma relevante a estabilidade.

## Decisao

HB passa a ser o baseline operacional temporario da plataforma.

IA deixa de atuar como gerador operacional concorrente e passa a atuar como mecanismo interno de inteligencia estrutural.

## Papel de HB

HB fica registrado como:
- baseline operacional temporario
- referencia oficial dos proximos benchmarks
- modo principal de geracao

Justificativa institucional:
- avg_hits superior ao IA puro no recorte analisado
- maior frequencia de 11+
- maior frequencia de 12+
- overlap medio menor
- estabilidade por concurso mais favoravel

## Papel de IA

IA fica registrado como:
- camada cientifica interna
- sistema de auditoria estrutural
- calibrador geometrico
- controlador de exploracao
- detector de compressao
- regulador de dispersao

Declaracao institucional:
"IA deixa de atuar como gerador operacional concorrente e passa a atuar como mecanismo interno de inteligencia estrutural."

## O que nao mostrou ganho relevante

As seguintes tentativas nao apresentaram ganho estatistico suficiente no recorte atual:
- reducao isolada de hot_numbers
- cortes leves em pesos dominantes
- flexibilizacao superficial de filtros

Conclusao:
o ganho observado foi insuficiente para justificar mudanca estrutural por si so.

## O que mostrou sinal positivo

A variante de HB com exploracao controlada apresentou:
- avg_hits aproximadamente 9.1
- 11+ = 20
- 12+ = 4

Conclusao:
a abertura geometrica controlada mostrou ganho pequeno, porem consistente, no recorte medido.

## Hipotese Cientifica Atual

Hipotese institucional:
"o proximo avanco provavel da LotoIA virah de exploracao estrutural controlada do candidate space, e nao de aumento de modos operacionais concorrentes."

## Trilhas Futuras

A trilha experimental futura deve investigar:
- exploracao inteligente
- dispersao util
- reducao de centralizacao
- geometria adaptativa
- controle fino de overlap estrutural

Sem:
- explosao de complexidade
- multiplos motores concorrentes
- tuning cego

## Restricoes

Nao alterar permanentemente:
- scoring core
- benchmark oficial
- temporal V1
- scientific expansion engine

Todos os testes devem permanecer:
- auditaveis
- reversiveis
- reproduziveis
- isolados

## Conclusao

Este ADR formaliza:
- o novo baseline operacional da plataforma
- o papel definitivo da IA
- o estado cientifico atual do motor
- e a direcao arquitetural oficial da LotoIA
