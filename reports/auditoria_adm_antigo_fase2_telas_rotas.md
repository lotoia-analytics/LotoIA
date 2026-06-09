# Miss?o CDX - Fase 2
## Auditoria Profunda por Tela/Rota do ADM Antigo

**Base documental:** `dashboard/institutional_app.py`  
**Fase anterior:** [reports/auditoria_adm_antigo_preliminar.md](./auditoria_adm_antigo_preliminar.md)  
**Natureza da fase:** documental, t?cnica e institucional.  
**Restri??o principal:** nenhuma altera??o funcional, visual, l?gica ou estrutural foi executada.

## 1. Vis?o geral

Esta fase aprofunda o invent?rio do ADM antigo e registra, por tela/rota, os pontos operacionais, hist?ricos, anal?ticos, estrat?gicos e destrutivos que podem influenciar uma decis?o posterior entre:
- reestruturar o ADM antigo;
- manter a LotoIA Clean como base;
- adotar um modelo h?brido controlado.

A auditoria foi conduzida por leitura do c?digo e mapeamento das rotas/p?ginas declaradas no painel institucional. N?o houve execu??o de a??es destrutivas, migra??o, redesign ou refatora??o.

## 2. Mapa de rotas e p?ginas priorit?rias

### Auditoria
- `Auditoria Runtime` -> `audit`
- `Auditoria e Monitoramento` -> `audit_monitoring`
- `Confer?ncia por concurso` -> `audit_monitoring_conference`
- `Desempenho por grupo` -> `audit_monitoring_group_performance`
- `Dezenas faltantes` -> `audit_monitoring_missing_numbers`
- `Dezenas sobrando` -> `audit_monitoring_extra_numbers`
- `Vazamento lateral` -> `audit_monitoring_side_leak`
- `Evolu??o 13 -> 14` -> `audit_monitoring_13_to_14`
- `Evolu??o 14 -> 15` -> `audit_monitoring_14_to_15`
- `Hip?teses para teste offline` -> `audit_monitoring_offline_hypotheses`

### Opera??es
- `Gerar Jogos` -> `generation`
- `Gerador ADM - Lei 15 Limpo` -> `clean_law15_generation`
- `Conferir Resultados` -> `conference`
- `Simular Resultados` -> `simulation`

### Hist?ricos
- `Hist?rico Anal?tico` -> `history_analytical`
- `Hist?rico Institucional` -> `history_institutional`
- `Limpar Hist?ricos` -> `clear_histories`
- `Apagar Hist?rico` -> `delete_history`
- `Comparativos hist?rico` -> `comparative_history`

### Estrat?gias
- `An?lises Estrat?gicas` -> `strategies_analysis`
- `Testar Estrat?gias` -> `strategies_test`
- `Simular Estrat?gias` -> `strategies_simulation`

### Anal?tico
- `M?tricas HB` -> `hb_metrics`
- `Cobertura estrutural` -> `structural_coverage`
- `Replay institucional` -> `institutional_replay`
- `Benchmark resumido` -> `summary_benchmark`
- `Estat?sticas operacionais` -> `operational_statistics`
- `HB Geometry` -> `hb_geometry`

## 3. Auditoria por tela/rota

> Observa??o: a coluna **evid?ncias** usa refer?ncia textual do c?digo e fun??es encontradas em `dashboard/institutional_app.py`.

| ID | Tela/Menu | Rota | Tipo | Status | Fun??o / dados | Bot?es / a??es | Rela??o com Lei 15 | Rela??o com Lei 17/18 | Risco t?cnico | Risco institucional | Classifica??o | Decis?o provis?ria | Evid?ncias |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 | Auditoria Runtime | `audit` | T?cnica / documental | Ativo | Auditoria do runtime publicado, backend, schema, fontes de dados | Navega??o lateral | Indireta | Indireta | Baixo | Baixo | Compat?vel | Preservar | `_render_runtime_audit_page`, `backend`, `DATABASE_URL`, `snapshot` |
| A2 | Auditoria e Monitoramento | `audit_monitoring` | Observacional | Ativo | Camada institucional de observa??o p?s-confer?ncia | Navega??o lateral | Indireta | Sim, como valida??o | Baixo | Baixo | Compat?vel | Preservar | `_render_audit_monitoring_page`, `POST_DRAW_MONITORING_PAYLOAD` |
| A3 | Confer?ncia por concurso | `audit_monitoring_conference` | Operacional / anal?tica | Ativo | Confer?ncia por concurso e por grupo | Navega??o lateral | Sim, via jogos gerados | Sim, observa??o p?s-gera??o | M?dio | M?dio | Suspeito | Preservar com ajuste futuro | `_render_audit_monitoring_page`, `confer?ncia por concurso` |
| A4 | Desempenho por grupo | `audit_monitoring_group_performance` | Anal?tica | Ativo | Desempenho por G50/G30/G20/G10 | Navega??o lateral | Indireta | Sim | M?dio | M?dio | Suspeito | Preservar com ajuste futuro | se??o `Desempenho por grupo` |
| A5 | Dezenas faltantes | `audit_monitoring_missing_numbers` | Anal?tica | Ativo | Lista/frequ?ncia de dezenas ausentes | Navega??o lateral | Indireta | Sim | M?dio | M?dio | Suspeito | Preservar com ajuste futuro | se??o `Dezenas faltantes` |
| A6 | Dezenas sobrando | `audit_monitoring_extra_numbers` | Anal?tica | Ativo | Lista/frequ?ncia de dezenas excedentes | Navega??o lateral | Indireta | Sim | M?dio | M?dio | Suspeito | Preservar com ajuste futuro | se??o `Dezenas sobrando` |
| A7 | Vazamento lateral | `audit_monitoring_side_leak` | Anal?tica / experimental | Ativo | Leitura de vazamento lateral e borda | Navega??o lateral | Indireta | Sim | M?dio | M?dio | Suspeito | Isolar | se??o `Vazamento lateral` |
| A8 | Evolu??o 13 -> 14 | `audit_monitoring_13_to_14` | Anal?tica / experimental | Ativo | Hip?tese de progress?o 13->14 | Navega??o lateral | Indireta | Sim | Alto | Alto | Conflitante | Isolar | se??o `Evolu??o 13 -> 14` |
| A9 | Evolu??o 14 -> 15 | `audit_monitoring_14_to_15` | Anal?tica / experimental | Ativo | Hip?tese de progress?o 14->15 | Navega??o lateral | Indireta | Sim | Alto | Alto | Conflitante | Isolar | se??o `Evolu??o 14 -> 15` |
| A10 | Hip?teses para teste offline | `audit_monitoring_offline_hypotheses` | Experimental | Ativo | Hip?teses sem comando de gera??o | Navega??o lateral | Indireta | Sim | M?dio | M?dio | Suspeito | Isolar | se??o `Hip?teses para teste offline` |
| O1 | Gerar Jogos | `generation` | Operacional | Ativo | Gera??o principal, com contagem, concilia??o e snapshots | Bot?o gerar e filtros | Sim | Lei 17/18 aparecem como valida??o/registro | Alto | Alto | Compat?vel / Suspeito | Preservar com ajuste futuro | `_render_generation_page`, `policy_mode`, `generation_mode` |
| O2 | Gerador ADM - Lei 15 Limpo | `clean_law15_generation` | Operacional / isolado | Ativo | P?gina limpa da Lei 15 com formato 15/17/18 auditado | Bot?o `Gerar com Lei 15` | Sim | Sim, valida??o p?s-gera??o | M?dio | Baixo | Compat?vel | Preservar | `_render_clean_law15_generation_page` |
| O3 | Conferir Resultados | `conference` | Operacional / reconcilia??o | Ativo | Sele??o de bateria/gera??o, ?ltimo concurso, dezenas oficiais, reconcilia??o | Conferir, sincronizar, importar | Sim | Indireta | Alto | Alto | Suspeito | Preservar com ajuste futuro | `_render_conference_page`, `Syncronizar`, `Importar` |
| O4 | Simular Resultados | `simulation` | Operacional / simula??o | Ativo | Simula dezenas contra jogos persistidos | Bot?o simular, input de 15 dezenas | Indireta | Indireta | M?dio | M?dio | Compat?vel / Suspeito | Preservar | `_render_simulation_page` |
| H1 | Hist?rico Anal?tico | `history_analytical` | Documental / anal?tica | Ativo | Tabela de gera??es persistidas, filtros, ordena??o | Filtros de data, estrat?gia, concurso | Sim | Indireta | M?dio | M?dio | Compat?vel | Preservar | `_render_history_page` -> `_render_analytical_page` |
| H2 | Hist?rico Institucional | `history_institutional` | Documental / institucional | Ativo | Macro vis?o de gera??es, reconcilia??es, integridade operacional, m?tricas oficiais | Filtros, tabelas, m?tricas | Sim | Sim, m?tricas de decis?es cient?ficas | Alto | Alto | Suspeito / Conflitante | Isolar | `_render_history_institutional_page`, `scientific_calibration_decisions` |
| H3 | Limpar Hist?ricos | `clear_histories` | Destrutiva / administrativa | Ativo | Limpa estado da sess?o | Bot?o limpar | Indireta | Indireta | Baixo | Alto | Conflitante | Bloquear da navega??o | `_render_clear_histories_page`, `_clear_institutional_history_state` |
| H4 | Apagar Hist?rico | `delete_history` | Destrutiva | Ativo | Remove registros operacionais persistidos | Bot?o apagar persistido | Indireta | Indireta | Alto | Cr?tico | Conflitante | Bloquear da navega??o | `_render_delete_history_page`, `_purge_institutional_history_tables` |
| H5 | Comparativos hist?rico | `comparative_history` | Anal?tica | Ativo | Compara gera??o, reconcilia??o e base oficial | Filtros e tabelas | Sim | Indireta | M?dio | M?dio | Suspeito | Preservar com ajuste futuro | `_render_comparative_history_page` |
| S1 | An?lises Estrat?gicas | `strategies_analysis` | Estrat?gica | Ativo | An?lise de estrat?gias sobre gera??o persistida | Bot?es de a??o | Indireta | Indireta | M?dio | M?dio | Suspeito | Isolar | `_render_strategies_page` |
| S2 | Testar Estrat?gias | `strategies_test` | Experimental | Ativo | Testes de estrat?gias | Bot?es de a??o | Indireta | Indireta | Alto | Alto | Conflitante | Isolar | `_render_strategies_page` |
| S3 | Simular Estrat?gias | `strategies_simulation` | Experimental | Ativo | Simula??o de estrat?gias | Bot?es de a??o | Indireta | Indireta | M?dio | M?dio | Suspeito | Isolar | `_render_strategies_page` |
| AN1 | M?tricas HB | `hb_metrics` | Anal?tica | Ativo | Resumo HB do replay estrutural incremental | M?tricas / tabela | Indireta | Indireta | M?dio | M?dio | Suspeito | Preservar com ajuste futuro | `_render_metrics_hb_page` |
| AN2 | Cobertura estrutural | `structural_coverage` | Anal?tica | Ativo | Geometria e concentra??o do lote institucional | M?tricas / tabela | Indireta | Indireta | M?dio | M?dio | Suspeito | Preservar com ajuste futuro | `_render_cobertura_estrutural_page` |
| AN3 | Replay institucional | `institutional_replay` | Anal?tica / operacional | Ativo | Reexecuta leitura do ?ltimo lote contra o concurso oficial | Bot?o replay | Sim | Indireta | Alto | Alto | Conflitante | Isolar | `_render_replay_institutional_page` |
| AN4 | Benchmark resumido | `summary_benchmark` | Anal?tica | Ativo | Snapshot curto dos indicadores | Tabelas e JSON | Indireta | Indireta | Baixo | Baixo | Compat?vel | Preservar | `_render_benchmark_resumido_page` |
| AN5 | Estat?sticas operacionais | `operational_statistics` | Anal?tica | Ativo | Fluxo operacional persistido e sess?o corrente | M?tricas | Indireta | Indireta | Baixo | Baixo | Compat?vel | Preservar | `_render_estatisticas_operacionais_page` |
| AN6 | HB Geometry | `hb_geometry` | T?cnica / experimental | Ativo | Auditoria incremental isolada do motor oficial | Iniciar/Continuar/Resetar | Indireta | Indireta | Alto | Alto | Conflitante | Bloquear da navega??o | `_render_hb_geometry_page` |

## 4. Auditoria especial das a??es destrutivas

### Limpar Hist?ricos
- O que limpa: estado visual e operacional da sess?o corrente.
- O que n?o limpa: banco permanente.
- Confirma??o: n?o h? dupla confirma??o.
- Trava de permiss?es: n?o identificada no c?digo analisado.
- Backup: n?o h? backup expl?cito.
- Log: n?o foi identificado log persistido espec?fico da limpeza.
- Revers?o: revers?vel apenas no n?vel da sess?o, n?o no banco.
- Impacto: n?o afeta diretamente o banco, mas pode remover contexto da navega??o atual.
- Classifica??o: **alto risco institucional** se exposto sem trava adicional.

### Apagar Hist?rico
- O que apaga: tabelas operacionais do runtime atual (`generation_events`, `generated_games`, `reconciliation_runs`, `reconciliation_games`, `reconciliation_events`, `operational_logs`, `reset_events`) e, em purga dedicada, `institutional_output_signatures`.
- Confirma??o: h? bot?o de a??o, mas a confirma??o textual expl?cita n?o aparece na fun??o analisada de `institutional_app.py`.
- Dupla confirma??o: n?o identificada.
- Trava de permiss?es: n?o identificada no c?digo analisado.
- Backup: n?o h? backup autom?tico vis?vel na fun??o.
- Log: h? atualiza??o de snapshot e limpeza de estado, mas n?o um log detalhado expl?cito da exclus?o.
- Revers?o: n?o revers?vel por design operacional.
- Afeta hist?rico anal?tico: sim.
- Afeta hist?rico institucional: sim, indiretamente e por purga dos eventos de runtime.
- Afeta rastreabilidade da Lei 15: sim, porque remove evid?ncias de gera??o e reconcilia??o.
- Classifica??o: **cr?tico / alto risco institucional**.

## 5. Auditoria especial da Lei 15, Lei 17 e Lei 18

### Onde aparecem no c?digo
- Lei 15 aparece como n?cleo do fluxo de gera??o, especialmente em `Gerar Jogos` e `Gerador ADM - Lei 15 Limpo`.
- Lei 17 e Lei 18 aparecem como valida??o/regra futura em textos institucionais, contexto cient?fico e formato 17/18.
- H? refer?ncias de calibra??o, recomenda??o e pol?tica cient?fica em m?ltiplos trechos do painel antigo.

### Classifica??o por comportamento
- **Lei 15**: geralmente compat?vel quando serve como comando da gera??o; torna-se suspeita quando misturada com filtros ou pol?ticas concorrentes.
- **Lei 17**: frequentemente usada como valida??o/perspectiva futura; suspeita quando entra como estrat?gia, calibra??o ou comando impl?cito.
- **Lei 18**: semelhante ? Lei 17, com risco maior quando extrapola valida??o e passa a orientar execu??o.

### Pontos cr?ticos observados
- O painel antigo carrega `scientific_calibration_engine` e decis?es de calibra??o/recomenda??o.
- H? men??o a `recalibrate_from_*` e pol?tica cient?fica em v?rias camadas.
- Isso indica que o painel antigo n?o ? puramente operacional; ele mistura opera??o, an?lise e calibra??o.

### Classifica??o geral
- Lei 15 no ADM antigo: **compat?vel em partes, suspeita em outras**.
- Lei 17/18 no ADM antigo: **suspeitas** quando permanecem restritas ? valida??o, **conflitantes** quando assumem papel de comando ou recalibra??o.

## 6. Componentes legados, suspeitos, conflitantes e obsoletos

### Compat?veis
- `Gerar Jogos` quando operado como fluxo principal da Lei 15.
- `Auditoria Runtime` quando usado como observa??o do ambiente.
- `Benchmark resumido`.
- `Estat?sticas operacionais`.
- `Hist?rico Anal?tico` se for apenas documental.

### Suspeitos
- `Conferir Resultados`.
- `Simular Resultados`.
- `Auditoria e Monitoramento`.
- `Desempenho por grupo` e demais subp?ginas de monitoramento.
- `Hist?rico Institucional`.
- `Comparativos hist?rico`.
- `M?tricas HB`.
- `Cobertura estrutural`.
- `Replay institucional`.
- `An?lises Estrat?gicas`.
- `Simular Estrat?gias`.

### Conflitantes
- `Limpar Hist?ricos` se exposto sem trava institucional.
- `Apagar Hist?rico`.
- `Testar Estrat?gias`.
- `HB Geometry` se continuar com reset/in?cio/continua??o de auditoria e l?gica t?cnica ativa.
- Telas que utilizem calibradores, recalibra??o, seletor paralelo ou pol?tica concorrente.

### Obsoletos / candidatos a isolamento
- M?dulos que preservam apenas evid?ncia hist?rica sem valor operacional para a linha limpa.
- Camadas de calibra??o que n?o fa?am parte da governan?a atual da Lei 15.

## 7. Risco t?cnico e institucional por grupo

### Baixo risco
- p?ginas de leitura, benchmarking e estat?sticas simples.

### M?dio risco
- p?ginas que consomem dados reais e calculam m?tricas sem a??o destrutiva.

### Alto risco
- p?ginas que sincronizam, reconcilia, reexecutam replay, usam estrat?gia ou dependem de estrutura cient?fica antiga.

### Cr?tico
- a??es destrutivas sem trava institucional.
- p?ginas que misturam gera??o, recalibra??o e valida??o concorrente.

## 8. Decis?o provis?ria por item

- **Preservar:** `Auditoria Runtime`, `Benchmark resumido`, `Estat?sticas operacionais`.
- **Preservar com ajuste futuro:** `Gerar Jogos`, `Gerador ADM - Lei 15 Limpo`, `Conferir Resultados`, `Simular Resultados`, `Hist?rico Anal?tico`.
- **Isolar:** `Auditoria e Monitoramento`, `Desempenho por grupo`, `Dezenas faltantes`, `Dezenas sobrando`, `Vazamento lateral`, `Evolu??o 13 -> 14`, `Evolu??o 14 -> 15`, `Hip?teses para teste offline`, `Replay institucional`, `M?tricas HB`, `Cobertura estrutural`, `An?lises Estrat?gicas`, `Simular Estrat?gias`.
- **Bloquear da navega??o:** `Limpar Hist?ricos`, `Apagar Hist?rico`, `HB Geometry`.
- **Usar apenas como refer?ncia:** partes de hist?rico/institucional que servem de prova documental, mas n?o devem comandar gera??o.

## 9. Tabelas de s?ntese

### 9.1 Rela??o com Lei 15 / 17 / 18
| Grupo | Lei 15 | Lei 17 | Lei 18 | Observa??o |
|---|---|---|---|---|
| Opera??es | Sim | Indireta | Indireta | A Lei 15 deve permanecer como comando; 17/18 apenas valida??o/registro |
| Hist?ricos | Sim | Indireta | Indireta | Valor documental alto; risco ao apagar/limpar |
| Estrat?gias | Indireta | Indireta | Indireta | Alta chance de concorr?ncia conceitual |
| Anal?tico | Indireta | Indireta | Indireta | ?til para auditoria, mas exige isolamento |
| Auditoria/Monitoramento | Sim | Sim | Sim | Deve permanecer observacional, sem recalibra??o |

### 9.2 Lista consolidada de a??es destrutivas
- `Limpar Hist?ricos`
- `Apagar Hist?rico`
- qualquer purga de tabelas operacionais
- qualquer a??o que remova rastreabilidade da gera??o, reconcilia??o ou valida??o

### 9.3 Lista consolidada de componentes suspeitos
- `Conferir Resultados`
- `Simular Resultados`
- `Hist?rico Institucional`
- `Comparativos hist?rico`
- `An?lises Estrat?gicas`
- `Testar Estrat?gias`
- `Simular Estrat?gias`
- `Replay institucional`
- `M?tricas HB`
- `Cobertura estrutural`
- `HB Geometry`

### 9.4 Lista consolidada de componentes conflitantes
- `Limpar Hist?ricos`
- `Apagar Hist?rico`
- `HB Geometry`
- qualquer fluxo com recalibra??o / calibrador / seletor paralelo

### 9.5 Lista consolidada de componentes compat?veis
- `Auditoria Runtime`
- `Benchmark resumido`
- `Estat?sticas operacionais`
- partes de `Gerar Jogos` quando restritas ? Lei 15

## 10. Conclus?o sobre a viabilidade preliminar

O ADM antigo **pode** servir como base operacional parcial, mas ainda apresenta:
- mistura entre opera??o, hist?rico, an?lise e calibra??o;
- a??es destrutivas sem travas institucionais expl?citas;
- ?reas estrat?gicas/experimentais que precisam de isolamento;
- pontos de poss?vel concorr?ncia com a Lei 15 e com as valida??es Lei 17/18.

### Recomenda??o preliminar
**Modelo h?brido controlado**, com forte isolamento dos m?dulos legados e preserva??o dos blocos que j? demonstraram utilidade operacional/documental.

### Observa??o final
Antes de qualquer migra??o ou reestrutura??o, ? necess?rio concluir a auditoria tela por tela e rota por rota, para que a decis?o entre:
1. reestruturar o ADM antigo,
2. manter a LotoIA Clean,
ou 3. adotar um h?brido controlado,

seja tomada com rastreabilidade e sem risco institucional.
