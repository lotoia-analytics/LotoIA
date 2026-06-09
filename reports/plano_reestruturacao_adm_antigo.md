# Plano de Reestrutura??o Controlada do ADM Antigo ? P&D-ADM-001

## 1. Objetivo

Transformar o ADM antigo em uma estrutura mais limpa, segura e institucionalmente govern?vel, preservando o que j? tem valor operacional e isolando ou bloqueando componentes de risco.

**Importante:** este documento ? apenas um plano documental/t?cnico/institucional. N?o h? autoriza??o para alterar o sistema nesta etapa.

## 2. Base documental utilizada

- [reports/auditoria_adm_antigo_preliminar.md](./auditoria_adm_antigo_preliminar.md)
- [reports/auditoria_adm_antigo_fase2_telas_rotas.md](./auditoria_adm_antigo_fase2_telas_rotas.md)
- `dashboard/institutional_app.py`

## 3. Diretriz institucional

Decis?o provis?ria consolidada:
- o ADM antigo ser? tratado como base principal candidata ? reestrutura??o;
- a LotoIA Clean pode ser usada apenas como refer?ncia visual/conceitual, se necess?rio;
- o modelo h?brido n?o ? o destino final neste momento.

## 4. Mapa atual resumido

### N?cleo operacional
- `Gerador ADM - Lei 15 Limpo`
- `Gerar Jogos`
- `Conferir Resultados`
- `Simular Resultados`

### Hist?ricos e rastreabilidade
- `Hist?rico Anal?tico`
- `Hist?rico Institucional`
- `Comparativos hist?rico` (somente se permanecer observacional/documental)

### Auditoria observacional
- `Auditoria Runtime`
- `Auditoria e Monitoramento`
- `Confer?ncia por concurso`
- `Desempenho por grupo`
- `Dezenas faltantes`
- `Dezenas sobrando`

### Anal?tico observacional
- `Benchmark resumido`
- `Estat?sticas operacionais`
- `M?tricas HB`
- `Cobertura estrutural`
- `HB Geometry` (somente se n?o executar reset, recalibra??o ou a??o t?cnica ativa)

### Quarentena institucional
- `Vazamento lateral`
- `Evolu??o 13 -> 14`
- `Evolu??o 14 -> 15`
- `Hip?teses para teste offline`
- `An?lises Estrat?gicas`
- `Testar Estrat?gias`
- `Simular Estrat?gias`
- `Replay institucional`
- qualquer calibrador
- qualquer recalibra??o
- qualquer seletor paralelo
- qualquer pol?tica concorrente ? Lei 15

### ?rea bloqueada / restrita
- `Limpar Hist?ricos`
- `Apagar Hist?rico`
- qualquer purga de tabelas operacionais
- qualquer a??o que remova rastreabilidade

## 5. Nova proposta de organiza??o por camadas

### 5.1 N?cleo Operacional
**Objetivo:** manter o fluxo essencial de gera??o, confer?ncia e simula??o, com Lei 15 como comando.

**Itens:**
- `Gerador ADM - Lei 15 Limpo`
- `Gerar Jogos`
- `Conferir Resultados`
- `Simular Resultados`

**Crit?rio:** permanecer na navega??o principal, com rastreabilidade e sem componentes concorrentes.

### 5.2 Hist?ricos e Rastreabilidade
**Objetivo:** preservar mem?ria operacional e institucional, permitindo auditoria posterior.

**Itens:**
- `Hist?rico Anal?tico`
- `Hist?rico Institucional`
- `Comparativos hist?rico` (se puramente documental)

**Crit?rio:** permanecer acess?vel, por?m sem a??es destrutivas nem reescrita de evid?ncias.

### 5.3 Auditoria Observacional
**Objetivo:** observar o runtime e os resultados sem comandar a gera??o.

**Itens:**
- `Auditoria Runtime`
- `Auditoria e Monitoramento`
- `Confer?ncia por concurso`
- `Desempenho por grupo`
- `Dezenas faltantes`
- `Dezenas sobrando`

**Crit?rio:** permanecer na navega??o principal apenas se restrito ? observa??o.

### 5.4 Anal?tico Observacional
**Objetivo:** permitir an?lise de comportamento, cobertura e benchmark sem alterar a Lei.

**Itens:**
- `Benchmark resumido`
- `Estat?sticas operacionais`
- `M?tricas HB`
- `Cobertura estrutural`
- `HB Geometry` (se n?o houver a??o t?cnica ativa)

**Crit?rio:** manter, mas com isolamento forte se houver qualquer a??o que reexecute ou resete auditoria.

### 5.5 Quarentena Institucional
**Objetivo:** isolar componentes com potencial de conflito, recalibra??o ou concorr?ncia com a Lei 15.

**Itens:**
- `Vazamento lateral`
- `Evolu??o 13 -> 14`
- `Evolu??o 14 -> 15`
- `Hip?teses para teste offline`
- `An?lises Estrat?gicas`
- `Testar Estrat?gias`
- `Simular Estrat?gias`
- `Replay institucional`
- qualquer calibrador
- qualquer recalibra??o
- qualquer seletor paralelo
- qualquer pol?tica concorrente ? Lei 15

**Crit?rio:** n?o integrar diretamente ? navega??o principal; manter em ?rea isolada ou bloqueada at? revis?o.

### 5.6 ?rea Bloqueada / Restrita
**Objetivo:** proteger rastreabilidade e integridade institucional.

**Itens:**
- `Limpar Hist?ricos`
- `Apagar Hist?rico`
- qualquer purga de tabelas operacionais
- qualquer a??o que remova rastreabilidade

**Crit?rio:** remover da navega??o principal ou exigir trava institucional r?gida com dupla confirma??o e log obrigat?rio.

## 6. Tabela de decis?o por tela/rota

| Tela/Menu | Rota | Camada de destino | Classifica??o atual | Decis?o proposta | Justificativa | Risco t?cnico | Risco institucional | Rela??o com Lei 15 | Rela??o com Lei 17/18 | Exige trava | Exige isolamento | Exige bloqueio | Navega??o principal | Preservar como refer?ncia |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Gerador ADM - Lei 15 Limpo | `clean_law15_generation` | N?cleo operacional | Ativo | Preservar | Fluxo isolado da Lei 15 j? ? a base limpa | M?dio | Baixo | Sim | Indireta | Sim | N?o | N?o | Sim | N?o |
| Gerar Jogos | `generation` | N?cleo operacional | Ativo | Preservar com ajuste futuro | Fluxo principal, mas ainda carrega camadas institucionais complexas | Alto | Alto | Sim | Indireta | Sim | N?o | N?o | Sim | N?o |
| Conferir Resultados | `conference` | N?cleo operacional / auditoria | Ativo | Preservar com ajuste futuro | Tem valor operacional, mas depende de concilia??o e integra??o com hist?rico | Alto | Alto | Sim | Indireta | Sim | N?o | N?o | Sim | N?o |
| Simular Resultados | `simulation` | N?cleo operacional / auditoria | Ativo | Preservar | Simula??o ? ?til e separada da gera??o, mas precisa de clareza visual | M?dio | M?dio | Indireta | Indireta | Sim | N?o | N?o | Sim | N?o |
| Hist?rico Anal?tico | `history_analytical` | Hist?ricos e rastreabilidade | Ativo | Preservar | Valor documental direto para auditoria | M?dio | M?dio | Sim | Indireta | Sim | N?o | N?o | Sim | Sim |
| Hist?rico Institucional | `history_institutional` | Hist?ricos e rastreabilidade | Ativo | Preservar | Serve como prova institucional e rastreamento | Alto | Alto | Sim | Indireta | Sim | N?o | N?o | Sim | Sim |
| Comparativos hist?rico | `comparative_history` | Hist?ricos e rastreabilidade | Ativo | Preservar com ajuste futuro | ?til, mas pode virar an?lise concorrente se mal interpretado | M?dio | M?dio | Sim | Indireta | Sim | N?o | N?o | Opcional | Sim |
| Limpar Hist?ricos | `clear_histories` | ?rea bloqueada / restrita | Ativo | Bloquear da navega??o | Limpa sess?o e pode confundir o usu?rio sem uma trava forte | Baixo | Alto | Indireta | Indireta | Sim | Sim | Sim | N?o | N?o |
| Apagar Hist?rico | `delete_history` | ?rea bloqueada / restrita | Ativo | Bloquear da navega??o | A??o destrutiva com perda de rastreabilidade | Alto | Cr?tico | Indireta | Indireta | Sim | Sim | Sim | N?o | N?o |
| Auditoria Runtime | `audit` | Auditoria observacional | Ativo | Preservar | Observa??o t?cnica ?til, sem comando direto | Baixo | Baixo | Indireta | Indireta | N?o | N?o | N?o | Sim | N?o |
| Auditoria e Monitoramento | `audit_monitoring` | Auditoria observacional | Ativo | Preservar | Observa??o p?s-confer?ncia sem recalibra??o | Baixo | Baixo | Indireta | Sim | Sim | N?o | N?o | Sim | N?o |
| Confer?ncia por concurso | `audit_monitoring_conference` | Auditoria observacional | Ativo | Preservar | Observa desempenho por concurso | M?dio | M?dio | Sim | Sim | Sim | N?o | N?o | Sim | N?o |
| Desempenho por grupo | `audit_monitoring_group_performance` | Auditoria observacional | Ativo | Preservar | Relevante para compara??o por grupo | M?dio | M?dio | Indireta | Sim | Sim | N?o | N?o | Sim | N?o |
| Dezenas faltantes | `audit_monitoring_missing_numbers` | Auditoria observacional | Ativo | Preservar | Ajuda a diagnosticar cobertura/borda | M?dio | M?dio | Indireta | Sim | Sim | N?o | N?o | Sim | N?o |
| Dezenas sobrando | `audit_monitoring_extra_numbers` | Auditoria observacional | Ativo | Preservar | Similar ao item anterior | M?dio | M?dio | Indireta | Sim | Sim | N?o | N?o | Sim | N?o |
| Vazamento lateral | `audit_monitoring_side_leak` | Quarentena institucional | Ativo | Isolar | Pode indicar desvio estrutural sem necessariamente ser oper?vel | M?dio | Alto | Indireta | Sim | Sim | Sim | N?o | N?o | N?o |
| Evolu??o 13 -> 14 | `audit_monitoring_13_to_14` | Quarentena institucional | Ativo | Isolar | Hip?tese de progress?o; n?o deve comandar a Lei | Alto | Alto | Indireta | Sim | Sim | Sim | N?o | N?o | N?o |
| Evolu??o 14 -> 15 | `audit_monitoring_14_to_15` | Quarentena institucional | Ativo | Isolar | Idem acima, ainda mais sens?vel | Alto | Alto | Indireta | Sim | Sim | Sim | N?o | N?o | N?o |
| Hip?teses para teste offline | `audit_monitoring_offline_hypotheses` | Quarentena institucional | Ativo | Isolar | ?til apenas como investiga??o documental | M?dio | M?dio | Indireta | Sim | Sim | Sim | N?o | Sim | Sim |
| An?lises Estrat?gicas | `strategies_analysis` | Quarentena institucional | Ativo | Isolar | Pode competir com a Lei 15 se virar comando | M?dio | Alto | Indireta | Sim | Sim | Sim | N?o | N?o | N?o |
| Testar Estrat?gias | `strategies_test` | Quarentena institucional | Ativo | Isolar | Potencial concorr?ncia com governan?a | Alto | Alto | Indireta | Sim | Sim | Sim | N?o | N?o | N?o |
| Simular Estrat?gias | `strategies_simulation` | Quarentena institucional | Ativo | Isolar | Experimental, sem comando | M?dio | M?dio | Indireta | Sim | Sim | Sim | N?o | N?o | N?o |
| Replay institucional | `institutional_replay` | Quarentena institucional | Ativo | Isolar | Reexecu??o auditiva pode confundir hist?rico e opera??o | Alto | Alto | Sim | Indireta | Sim | Sim | N?o | N?o | Sim |
| M?tricas HB | `hb_metrics` | Anal?tico observacional | Ativo | Preservar com ajuste futuro | Indicadores ?teis para benchmark estrutural | M?dio | M?dio | Indireta | Indireta | N?o | N?o | N?o | Sim | N?o |
| Cobertura estrutural | `structural_coverage` | Anal?tico observacional | Ativo | Preservar com ajuste futuro | ?til para vis?o de geometria e concentra??o | M?dio | M?dio | Indireta | Indireta | N?o | N?o | N?o | Sim | N?o |
| HB Geometry | `hb_geometry` | ?rea bloqueada / restrita | Ativo | Bloquear da navega??o | Tem potencial de iniciar/continuar/resetar auditoria t?cnica | Alto | Alto | Indireta | Indireta | Sim | Sim | Sim | N?o | N?o |
| Benchmark resumido | `summary_benchmark` | Anal?tico observacional | Ativo | Preservar | Snapshot curto e seguro | Baixo | Baixo | Indireta | Indireta | N?o | N?o | N?o | Sim | N?o |
| Estat?sticas operacionais | `operational_statistics` | Anal?tico observacional | Ativo | Preservar | Resumo operacional e de sess?o | Baixo | Baixo | Indireta | Indireta | N?o | N?o | N?o | Sim | N?o |

## 7. Travas institucionais obrigat?rias

### 7.1 Limpar Hist?ricos
- **Tipo de bloqueio:** trava de sess?o + confirma??o expl?cita.
- **Mensagem ao usu?rio:** `Esta a??o limpa apenas a sess?o atual. N?o apaga o banco.`
- **Permiss?o necess?ria:** confirma??o de operador.
- **Dupla confirma??o:** recomendada.
- **Backup:** n?o necess?rio para limpeza de sess?o, mas recomendado se houver caches associados.
- **Log institucional:** obrigat?rio.
- **Reversibilidade:** parcial, apenas visual/sess?o.
- **Risco residual:** m?dio.

### 7.2 Apagar Hist?rico
- **Tipo de bloqueio:** trava destrutiva com confirma??o textual + confirma??o dupla.
- **Mensagem ao usu?rio:** `Digite APAGAR para confirmar.`
- **Permiss?o necess?ria:** perfil institucional elevado.
- **Dupla confirma??o:** obrigat?ria.
- **Backup:** obrigat?rio antes da a??o.
- **Log institucional:** obrigat?rio, com antes/depois.
- **Reversibilidade:** baixa ou nula, salvo restore externo.
- **Risco residual:** alto/cr?tico.

### 7.3 HB Geometry
- **Tipo de bloqueio:** trava de execu??o t?cnica.
- **Mensagem ao usu?rio:** `Auditoria t?cnica isolada, sem reset autom?tico.`
- **Permiss?o necess?ria:** perfil t?cnico autorizado.
- **Dupla confirma??o:** recomendada para reset/continuar.
- **Backup:** obrigat?rio se houver persist?ncia de estado.
- **Log institucional:** obrigat?rio.
- **Reversibilidade:** parcial.
- **Risco residual:** alto.

### 7.4 Replay institucional
- **Tipo de bloqueio:** isolamento de execu??o com confirma??o.
- **Mensagem ao usu?rio:** `Replay apenas observa, n?o reescreve a gera??o.`
- **Permiss?o necess?ria:** operador institucional.
- **Dupla confirma??o:** recomendada.
- **Backup:** n?o obrigat?rio, mas desej?vel.
- **Log institucional:** obrigat?rio.
- **Reversibilidade:** parcial.
- **Risco residual:** alto.

### 7.5 M?dulos de estrat?gia
- **Tipo de bloqueio:** isolamento anal?tico.
- **Mensagem ao usu?rio:** `Estrat?gias n?o podem comandar a Lei 15.`
- **Permiss?o necess?ria:** analista/t?cnico.
- **Dupla confirma??o:** n?o obrigat?ria se for leitura; obrigat?ria se gerar altera??o persistida.
- **Backup:** se houver persist?ncia, sim.
- **Log institucional:** obrigat?rio.
- **Reversibilidade:** depende do m?dulo.
- **Risco residual:** alto.

### 7.6 Evolu??o 13 -> 14 / 14 -> 15 / Hip?teses offline
- **Tipo de bloqueio:** quarentena institucional.
- **Mensagem ao usu?rio:** `Hip?tese observacional sem comando de gera??o.`
- **Permiss?o necess?ria:** pesquisador/analista.
- **Dupla confirma??o:** recomendada para ativa??o.
- **Backup:** n?o obrigat?rio se apenas leitura; obrigat?rio se persistir hip?teses.
- **Log institucional:** obrigat?rio.
- **Reversibilidade:** alta se somente leitura; m?dia se persistir hip?tese.
- **Risco residual:** m?dio/alto.

### 7.7 Fun??es que recalibram, testam, selecionam ou influenciam gera??o
- **Tipo de bloqueio:** isolamento ou bloqueio da navega??o principal.
- **Mensagem ao usu?rio:** `Esta fun??o n?o pode substituir a Lei 15.`
- **Permiss?o necess?ria:** analista institu?do.
- **Dupla confirma??o:** recomendada se houver aplica??o persistida.
- **Backup:** obrigat?rio se houver altera??o de estado.
- **Log institucional:** obrigat?rio.
- **Reversibilidade:** depende do fluxo.
- **Risco residual:** alto.

## 8. Sequ?ncia recomendada de execu??o

1. Consolidar o invent?rio por tela/rota.
2. Confirmar quais p?ginas s?o n?cleo operacional e quais s?o apenas observacionais.
3. Aplicar travas institucionais ?s a??es destrutivas e ? auditoria t?cnica.
4. Isolar quarentena institucional e componentes experimentais.
5. Bloquear da navega??o principal o que for destrutivo ou conflitante.
6. Preservar o que for ?til como refer?ncia documental.
7. S? depois disso planejar a reestrutura??o incremental do ADM antigo.

## 9. Riscos residuais

- persist?ncia de componentes com recalibra??o impl?cita;
- p?ginas de estrat?gia ainda concorrendo com a Lei 15;
- a??es destrutivas sem trava institucional forte;
- mistura entre hist?rico operacional e prova institucional;
- depend?ncia de p?ginas anal?ticas para decis?es de execu??o;
- risco de confus?o entre valida??o (Lei 17/18) e comando (Lei 15).

## 10. Conclus?o sobre a viabilidade da reestrutura??o

A reestrutura??o do ADM antigo ? **vi?vel**, mas **somente de forma controlada e faseada**.

### Recomenda??o institucional
- manter o **n?cleo operacional**;
- isolar a **quarentena institucional**;
- bloquear a **?rea destrutiva**;
- preservar como refer?ncia o que for documental e historicamente ?til;
- tratar Lei 17 e Lei 18 apenas como valida??o, nunca como comando.

### S?ntese final
O ADM antigo possui valor suficiente para justificar uma reestrutura??o controlada, desde que o projeto siga uma sequ?ncia com travas institucionais, isolamento dos m?dulos de maior risco e preserva??o rigorosa da rastreabilidade.
