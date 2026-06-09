# Saneamento Institucional - Parte 5: Politica do Historico Oficial e Fonte Unica de Concursos

## 1. Resumo executivo

Esta parte definiu documentalmente qual escopo institucional de historico oficial a LotoIA deve adotar, considerando o estado atual do banco ativo, a faixa ja reconciliada na Parte 4B e os modulos que leem concursos no projeto.

Conclusao executiva:
- o banco ativo esta sincronizado com a Caixa na faixa auditada `3689-3704`;
- o sistema nao depende, nesta sessao, de historico oficial completo para operar;
- o projeto usa historico recente auditado como base operacional, enquanto alguns modulos e diagnosticos ainda referenciam `official_lotofacil_history` como artefato esperado;
- a ausencia de `official_lotofacil_history` no schema ativo nao bloqueia a operacao atual, mas representa dependencia legada/ausente que precisa ser tratada como politica, nao como verdade silenciosa.

### Classificacao final

- **PARTE_5_APROVADA_POLITICA_HISTORICO_CANDIDATA_DEFINIDA**

---

## 2. Estado pos-Parte 4B

### Base consolidada

- repositorio candidato: `C:\Projetos\LotoIA`
- painel ADM ativo: `dashboard/institutional_app.py`
- banco ativo: `C:\Projetos\LotoIA\data\lotoia.db`
- tabelas reais: `imported_contests` / `contests`
- faixa sincronizada atual: `3689-3704`
- status atual da base: `SINCRONIZADO_CAIXA_NA_FAIXA_3689_3704`
- `official_lotofacil_history` nao existe no schema ativo

### Estado institucional atual

- o banco agora contem `16` concursos em cada tabela real, na faixa auditada;
- nao ha lacunas internas na faixa `3689-3704`;
- o banco bate com a Caixa nessa faixa;
- o painel continua apontando para `dashboard/institutional_app.py`;
- nao houve alteracao de banco nesta parte.

---

## 3. Banco ativo e tabelas reais

- **Banco ativo**: `C:\Projetos\LotoIA\data\lotoia.db`
- **Tipo**: SQLite local
- **Hash atual**: `88fd31310a03682b894d646aa516af6befebe315efea8c80a3bdff1817a780ef`
- **WAL presente**: sim
- **SHM presente**: sim

### Tabelas reais em uso

- `imported_contests`
- `contests`

### Observacao sobre schema

- `official_lotofacil_history` nao existe no schema do banco ativo observado nesta sessao.
- O codigo institucional, contudo, ainda a referencia em alguns caminhos de diagnostico e historico.

---

## 4. Faixa sincronizada atual

### Faixa validada

- `3689` a `3704`

### Situação

- sem lacunas;
- sem divergencia de dezenas;
- sem divergencia de data;
- sem duplicados na faixa auditada.

### Trava provisoria vigente

> "Validacoes historicas so sao confiaveis dentro da faixa sincronizada e sem lacunas."

Regra provisoria aplicada a esta parte:
- permitir auditoria e validacao dentro da faixa sincronizada;
- bloquear ou marcar como nao confiavel qualquer validacao que exija concursos fora da faixa;
- nao afirmar historico completo.

---

## 5. Mapa de uso do historico no projeto

### Principais referencias encontradas

| Arquivo | Trecho / funcao | Tabela ou fonte esperada | Escopo esperado | Risco se historico for parcial | Impacto institucional |
|---|---|---|---|---|---|
| `dashboard/institutional_app.py` | `_institutional_source_map`, `_load_imported_contest`, `get_official_contest`, `get_previous_official_contest`, `_load_official_history_diagnostics` | `imported_contests`, `contests`, `official_lotofacil_history`, Caixa/API | painel, conferência, RFE, diagnósticos | fallback silencioso ou inconsistência de origem | alto |
| `src/lotoia/ingestion/result_sync_service.py` | `sync_latest`, `sync_contests` | Caixa API + `imported_contests` | sincronização oficial | baixa cobertura se base parcial | alto |
| `src/lotoia/ingestion/official_caixa_validation.py` | `run_official_caixa_validation` | Caixa API + `imported_contests` | validação institucional de janela | gaps em janela geram mismatch | alto |
| `src/lotoia/governance/temporal_scientific_governance.py` | `build_temporal_operational_nuclei`, `build_temporal_benchmark_engine` | `imported_contests` | governança temporal / benchmark | se janela incompleta, benchmarking pode perder representatividade | alto |
| `src/lotoia/governance/temporal_history_registry.py` | registro de `imported_contests`, `backtest_runs`, `walk_forward_validation_*` | artefatos históricos | trilha temporal e ML | parcialidade reduz cobertura, mas não invalida tudo | médio/alto |
| `src/lotoia/governance/structural_rfe.py` | validação estrutural do cartão final | referência anterior oficial | conferência / RFE | sem concurso anterior, bloqueia | alto |
| `src/lotoia/ml/walk_forward_validation.py` | walk-forward temporal | sequência de concursos | validação temporal | precisa da integridade da janela usada | alto |
| `src/lotoia/backtesting/backtester.py` | backtest histórico | draws históricos | robustez / benchmarking | janela parcial reduz confiança | alto |

---

## 6. Exigencia de historico por modulo

### Classificacao institucional

| Modulo | Classificacao |
|---|---|
| Painel ADM | `FUNCIONA_COM_HISTORICO_PARCIAL` |
| Conferencia oficial | `EXIGE_APENAS_CONCURSO_ANTERIOR` |
| RFE | `EXIGE_APENAS_CONCURSO_ANTERIOR` |
| Validacao historica | `EXIGE_JANELA_RECENTE_CONTINUA` |
| Auditoria de robustez | `EXIGE_JANELA_RECENTE_CONTINUA` |
| Geracao limpa | `EXIGE_APENAS_CONCURSO_ANTERIOR` |
| Testes automatizados | `FUNCIONA_COM_HISTORICO_PARCIAL` |
| Relatorios institucionais | `FUNCIONA_COM_HISTORICO_PARCIAL` |

### Leitura objetiva

- **Painel ADM**: opera com fonte persistida e diagnosticos recentes; nao exige historico completo para renderizacao atual.
- **Conferencia oficial**: precisa do concurso selecionado e, para a RFE, do concurso anterior.
- **RFE**: exige apenas o concurso anterior oficial.
- **Validacao historica / robustez / backtest**: dependem de janela recente contigua e leakage-free.
- **Geracao limpa**: depende do concurso anterior e da cadeia oficial persistida, nao do historico completo.
- **Testes e relatorios**: aceitam a janela parcial sincronizada para validar os caminhos atuais.

---

## 7. Auditoria da ausencia de `official_lotofacil_history`

### Arquivos que citam `official_lotofacil_history`

- `dashboard/institutional_app.py`
- `src/lotoia/database/contest_repository.py`
- `src/lotoia/governance/structural_rfe.py` (via contexto operacional da referencia oficial)
- relatórios e snapshots institucionais que exibem a camada de histórico oficial

### Classificacao da ausencia

- **NECESSARIA_MAS_AUSENTE**

### Justificativa

- O codigo ainda espera essa tabela em diagnosticos e fluxos institucionais.
- O banco ativo observado nao a possui.
- O sistema, porem, opera com `imported_contests` e `contests` para a janela sincronizada e com fallback institucional controlado.

### Risco de erro silencioso

- existe risco se algum fluxo tentar usar `official_lotofacil_history` como verdade absoluta sem verificar existencia.
- por isso, a politica precisa explicitar que o historico oficial confiavel, nesta fase, e a faixa sincronizada sem lacunas.

---

## 8. Politicas candidatas

### Politica A - Janela recente auditada

**Descricao**
- manter somente a faixa recente continua e validada;
- bloquear validacoes fora da janela;
- tratar a janela como referencia operacional.

**Beneficios**
- reduz risco de fallback silencioso;
- simples de auditar;
- alinha com o estado atual do banco.

**Riscos**
- nao resolve a ausencia de historico completo como aspiracao futura;
- pode limitar analises historicas amplas e backtests mais longos.

**Impacto**
- banco: baixo;
- painel: baixo;
- conferencia: baixo;
- RFE: baixo;
- backup: baixo;
- reversibilidade: alta;
- aderencia institucional: alta para o estado atual.

---

### Politica B - Historico completo Caixa

**Descricao**
- importar e manter todo o historico oficial disponivel;
- usar o banco como fonte completa institucional;
- exigir rotina continua de sincronizacao.

**Beneficios**
- traz a fonte oficial mais ampla;
- reduz dependencia de janelas parciais;
- melhora cobertura historica e validade analitica.

**Riscos**
- exige importacao continua e manutencao permanente;
- amplia o impacto de schema e de persistencia;
- aumenta o custo operacional.

**Impacto**
- banco: alto;
- painel: medio/alto;
- conferencia: alto;
- RFE: medio;
- backup: alto;
- reversibilidade: media;
- aderencia institucional: alta no longo prazo, mas acima do que a sessao atual pede.

---

### Politica C - Hibrida controlada

**Descricao**
- manter historico completo quando disponivel;
- declarar explicitamente uma janela operacional validada;
- bloquear qualquer validacao fora do escopo sincronizado;
- tratar a ausencia de partes do historico como informacao institucional, nao como verdade escondida.

**Beneficios**
- combina a seguranca da janela auditada com a aspiracao de historico completo;
- evita mascarar lacunas;
- preserva evolucao futura sem romper o presente.

**Riscos**
- exige disciplina de fonte unica e de trava operacional;
- pode gerar complexidade de regra se nao houver documentacao clara.

**Impacto**
- banco: medio;
- painel: medio;
- conferencia: medio;
- RFE: medio;
- backup: medio;
- reversibilidade: alta;
- aderencia institucional: muito alta.

---

## 9. Comparativo de riscos

| Politica | Seguranca imediata | Cobertura historica | Complexidade | Risco de mascarar lacunas | Aderencia ao estado atual |
|---|---|---|---|---|---|
| A | alta | media | baixa | baixa | alta |
| B | media | alta | alta | media | media |
| C | alta | alta/média | media | baixa | muito alta |

---

## 10. Politica institucional recomendada

### Recomendacao

- **POLITICA_C_HIBRIDA_CONTROLADA**

### Por que e a mais segura

- porque preserva a janela sincronizada como verdade operacional imediata;
- porque nao obriga a importacao completa nesta fase;
- porque permite futura ampliacao do historico sem reescrever a governanca atual;
- porque evita transformar a ausencia de `official_lotofacil_history` em verdade silenciosa.

### Risco eliminado

- elimina o risco de tratar qualquer concurso fora da faixa sincronizada como validado por padrao;
- elimina o risco de fallback silencioso para fonte nao comprovada.

### Risco que permanece

- permanece a necessidade de disciplinar a expansao futura do historico completo;
- permanece a necessidade de definir, na Parte 6, se a fonte institucional devera ser ampliada para cobertura total ou permanecer por janela validada.

### O que precisa ser feito na Parte 6

- definir se a LotoIA vai consolidar somente janela recente auditada ou se vai migrar para historico completo Caixa;
- formalizar o papel definitivo de `official_lotofacil_history`;
- documentar a trava operacional definitiva para validacoes fora do escopo sincronizado.

---

## 11. Trava operacional provisoria

### Trava recomendada

> "Validacoes historicas so sao confiaveis dentro da faixa sincronizada e sem lacunas."

### Regra provisoria

- permitir auditoria dentro da faixa sincronizada `3689-3704`;
- bloquear ou marcar como nao confiavel qualquer validacao que exija concursos fora da faixa;
- nao afirmar historico completo ate homologacao formal da politica final.

---

## 12. Impactos para Parte 6

Na Parte 6, a decisao institucional devera:

1. escolher definitivamente entre:
   - janela recente auditada;
   - historico completo Caixa;
   - hibrido controlado consolidado;

2. definir se `official_lotofacil_history` sera:
   - historico oficial obrigatório;
   - artefato legado documentado;
   - tabela operacional futura;

3. ajustar, se necessario, os pontos de leitura institucional do painel e das validacoes.

---

## 13. Conclusao institucional

A politica institucional recomendada, nesta fase, e **POLITICA_C_HIBRIDA_CONTROLADA**. Ela e a mais segura porque respeita o estado real do banco, nao mascara a ausencia de `official_lotofacil_history` e permite evolucao futura sem comprometer a confiabilidade atual.

### Status final da Parte 5

- **PARTE_5_APROVADA_POLITICA_HISTORICO_CANDIDATA_DEFINIDA**

---

## 14. Confirmacoes finais

- banco nao foi alterado: **sim**
- schema nao foi alterado: **sim**
- painel nao foi alterado: **sim**
- `official_lotofacil_history` nao foi criada: **sim**
- nao houve importacao: **sim**
- nao houve `push`: **sim**
- relatorio apenas documental: **sim**

