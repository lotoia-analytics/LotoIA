# Anti-Leakage Temporal

## Regra Central

Nenhum artefato do LotoIA pode usar informacao posterior ao ponto temporal declarado.
Para datasets supervisionados, o corte de features deve ser estritamente anterior ao
concurso usado como label.

```text
feature_cutoff_contest < label_contest
```

## Fontes de Leakage Proibidas

- estatisticas globais calculadas com concursos futuros;
- normalizacao feita com a serie completa antes do split temporal;
- features derivadas do concurso alvo;
- mistura de treino e teste em uma mesma janela;
- reuso de resultados de benchmark futuro durante selecao de features;
- manifestos sem versao de dataset, codigo e split temporal.

## Controles Minimos

- validar ordem e unicidade dos concursos;
- validar `train_end < test_start`;
- declarar `feature_cutoff_contest` em cada linha supervisionada;
- declarar `label_contest` em cada linha supervisionada;
- bloquear `score_ml` na etapa atual;
- registrar manifesto experimental antes de qualquer execucao supervisionada real.

## Status Atual

A base atual formaliza validadores e documentacao. Ela nao implementa treinamento,
inferencia, score supervisionado ou alteracao de ranking.
