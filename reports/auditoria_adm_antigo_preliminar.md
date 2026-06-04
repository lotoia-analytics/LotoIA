# Auditoria Minuciosa do ADM Antigo - Vers?o Preliminar

## Objetivo
Auditar, sem alterar o sistema, a estrutura do ADM antigo da LotoIA para identificar telas, menus, rotas, funcionalidades operacionais, elementos legados e riscos institucionais/t?cnicos, com foco especial na compatibilidade com a Lei 15.

## Escopo avaliado
Levantamento inicial realizado a partir de `dashboard/institutional_app.py`, cobrindo:
- menu lateral
- telas principais e secund?rias
- rotas/p?ginas acess?veis
- hist?rico
- monitoramento p?s-confer?ncia
- gera??o
- confer?ncia
- simula??o
- p?ginas anal?ticas e estrat?gicas
- p?ginas de limpeza/apagamento
- refer?ncias ? Lei 15, Lei 17 e Lei 18

## Invent?rio inicial de menus e p?ginas

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
- `Gerador ADM - Lei 15 Limpo` -> `clean_law15_generation`
- `Gerar Jogos` -> `generation`
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

## Classifica??o inicial por risco

### Baixo risco
- P?ginas de consulta, hist?rico e visualiza??o sem a??o destrutiva direta, quando exibem somente dados.
- `Auditoria Runtime` e subp?ginas de auditoria, desde que permane?am observacionais.

### M?dio risco
- `Conferir Resultados`
- `Simular Resultados`
- `Hist?rico Anal?tico`
- `Hist?rico Institucional`
- `M?tricas HB`
- `Cobertura estrutural`
- `Benchmark resumido`
- `Estat?sticas operacionais`
- `HB Geometry`

### Alto risco
- `Limpar Hist?ricos`
- `Apagar Hist?rico`
- `Replay institucional`
- `Comparativos hist?rico`
- `Testar Estrat?gias`
- `Simular Estrat?gias`
- `An?lises Estrat?gicas`

### Cr?tico / Conflitante
- Qualquer m?dulo que altere gera??o, valide p?s-gera??o com efeito colateral, aplique seletor paralelo, recalibre, ou substitua a Lei 15.
- Refer?ncias com potencial de concorr?ncia institucional entre Lei 15, Lei 17 e Lei 18, se passarem de valida??o/auditoria para comando.

## Observa??es institucionais preliminares
- A estrutura do ADM antigo cont?m ?reas ?teis para auditoria e opera??o.
- H? mistura de camadas operacionais, hist?ricas, anal?ticas e experimentais.
- A presen?a de p?ginas destrutivas exige trava institucional expl?cita.
- As telas de auditoria p?s-confer?ncia devem permanecer observacionais para n?o concorrer com a Lei 15.
- A separa??o entre gera??o, confer?ncia, simula??o e hist?rico precisa ser mantida com rastreabilidade clara.

## Pontos a investigar na pr?xima fase
- detalhes de `Conferir Resultados` e `Simular Resultados`
- comportamento real de `Limpar Hist?ricos` e `Apagar Hist?rico`
- profundidade das p?ginas estrat?gicas e anal?ticas
- depend?ncias ocultas e efeitos colaterais das a??es de confer?ncia/reconcilia??o
- onde a Lei 17 e a Lei 18 aparecem apenas como valida??o e onde podem estar assumindo papel indevido

## Conclus?o preliminar
O ADM antigo tem potencial como base operacional parcial, mas ainda precisa de auditoria minuciosa para separar:
- funcionalidades compat?veis
- componentes suspeitos
- fluxos conflitantes
- m?dulos obsoletos
- a??es destrutivas que exigem trava institucional

A decis?o final entre reestruturar o ADM antigo, manter a LotoIA Clean ou adotar um modelo h?brido controlado deve aguardar o invent?rio completo e a auditoria de risco por tela/rota.
