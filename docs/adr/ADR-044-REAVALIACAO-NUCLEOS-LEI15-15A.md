# ADR-044 — Reavaliação dos Núcleos Lei 15 e Lei 15A + Proposta LEI15_15A_CORE_REALIGNMENT_V2

**Status:** ADR-044 APROVADA PARA IMPLEMENTACAO EM SHADOW_TEST  
**Missão:** MISSAO_DA_VITORIA_REAVALIAR_NUCLEOS_LEI15_15A  
**Data:** 2026-06-16  
**Revisores:** ADM  

### Status institucional

| Item | Estado |
|---|---|
| ADR-044 | Aprovada para implementação em `shadow_test` |
| V2 | Autorizada |
| Modo `active` | **Bloqueado** — requer aprovação ADM explícita e ADR adicional |
| 16D | **Bloqueado** — até nova validação 15D com V2 |
| 15D | **Base da vitória** — todos os testes comparativos partem daqui |

---

## Contexto

O Realinhamento Estrutural V1 (ADR-043) demonstrou que intervenções estruturais
na composição do GP melhoram significativamente os resultados no formato 15D:

| Métrica | BASELINE (STRUCT_TEST_15D_001) | V1 (STRUCT_REALIGN_V1_15D_001) | Delta |
|---|---|---|---|
| Melhor hit | 12 | 14 | +2 |
| Média hits | 11.308 | 12.143 | +0.835 |
| Runs com 14+ | 0 | 5 | +5 |
| Runs com 13+ | 0 | 47 | +47 |
| Top prefixo_3 (01-02-03) | 42.0% | 40.4% | -1.6pp |
| Top sufixo_3 (22-24-25) | 53.0% | 26.7% | -26.3pp |
| Similaridade GP | 12.210 | 9.717 | -2.493 |

O V1 resolveu bem o sufixo, mas o prefixo 01-02-03 permanece em 40.4%.
A auditoria dos núcleos (relatório: `reports/missao_da_vitoria_auditoria_nucleos_lei15_15a.md`)
identificou as causas raízes.

---

## Diagnóstico Confirmado

### Causa Raiz: Herança do Último Sorteio

O mecanismo de geração dos perfis Recorrente (40%) e Híbrido (40%) herda
diretamente 6–10 números do último sorteio oficial:

```python
# PROFILE_RECURRENT (40% do GP)
selected = set(random.sample(sorted(last_numbers), random.randint(8, min(10, len(last_numbers)))))
# PROFILE_HYBRID (40% do GP)
selected.update(random.sample(sorted(last_numbers), random.randint(6, min(9, len(last_numbers)))))
```

Com 80% do GP herdando do mesmo sorteio base, se esse sorteio tem 01-02-03
**quando presentes no último sorteio oficial usado como base**, o viés de prefixo
se propaga inevitavelmente.

O V1 atua na composição (pós-geração), mas não pode diversificar o que não
existe no pool. A causa raiz permanece.

### Causa da Suficiência do V1 no Sufixo mas Não no Prefixo

O sufixo possui mais variação natural no pool (diferentes combinações de
22-25 são possíveis dentro da herança) → V1 consegue selecionar jogos com
sufixos distintos.

O prefixo 01-02-03 é mais rígido: se o último sorteio tem 01, 02, 03, todos
os jogos recorrentes herdam os 3 juntos com probabilidade alta. A variação
no pool para prefixo_3 é menor, limitando o que V1 pode fazer.

---

## Decisão

### O que NÃO fazer (Restrições ADM)

1. NÃO avançar para 16D antes da validação 15D com V2.
2. NÃO ativar modo `active` sem aprovação ADM explícita.
3. NÃO modificar os mecanismos de geração dos perfis (R-03, R-04, R-06)
   sem ADR específico e validação extensa.
4. NÃO substituir Lei 15 por ML.
5. NÃO criar gerador paralelo oculto.
6. NÃO deletar evidências EPOCH_001 ou Realign V1.

### O que FAZER: LEI15_15A_CORE_REALIGNMENT_V2

Implementar uma segunda camada de realinhamento que opera em **duas fases**:

**Fase 1 — Pool Pre-Filter (NOVO):**  
Antes da composição greedy, filtrar o pool de candidatos para garantir que
nenhum prefixo_3 único domine mais de N% dos candidatos disponíveis.
Isso força o greedy a ter material diverso para trabalhar.

**Fase 2 — Composição Reforçada:**  
Usar composição greedy com thresholds mais rígidos que V1:

| Parâmetro | V1 | V2 |
|---|---|---|
| max_prefix3_ratio | 0.25 | 0.15 |
| max_prefix4_ratio | 0.30 | 0.20 |
| max_suffix3_ratio | 0.25 | 0.15 |
| max_suffix4_ratio | 0.30 | 0.20 |
| max_pool_prefix3_ratio | — | 0.30 |
| min_pool_size_after_filter | — | 30 |
| coverage_bonus_per_digit | 1.5 | 2.0 |
| max_coverage_bonus | 6.0 | 9.0 |
| target_coverage_digits | (16,6,17,23,20,8,10,4) | (16,6,17,23,20,8,10,4) |

### Regra de segurança — fallback obrigatório para V1

**V2 não pode reduzir demais o pool.**

Se o pool pós-filtro ficar abaixo do mínimo seguro (`min_pool_size_after_filter`),
o runtime deve fazer **fallback obrigatório para V1** (`compose_diverse_gp` com
configuração V1), e **não** continuar com composição V2 nem cair em composição
por perfil sem realinhamento.

Metadados devem registrar:
- `core_realignment_v2_applied=false`
- `v2_fallback_to_v1=true`
- `pool_pre_filter_applied=false` (quando o filtro foi abortado por pool insuficiente)

---

## Especificação Técnica: LEI15_15A_CORE_REALIGNMENT_V2

### Feature Flag

- **Env var:** `LOTOIA_LEI15_15A_CORE_REALIGNMENT_V2`
- **Valores:** `off` (default), `shadow_test`, `active`
- **Default:** `off` (fail-safe)
- **Modo autorizado agora:** `shadow_test` apenas

### Modo `shadow_test`

- Aplica pre-filter + composição V2 apenas para labels `STRUCT_CORE_REALIGN_V2_*`
- Produção com labels normais permanece inalterada
- Todos os resultados são logados e rastreados
- Fallback para V1 quando pool pós-filtro < mínimo seguro

### Modo `active` — BLOQUEADO

- Não autorizado nesta ADR
- Requer decisão ADM separada após validação comparativa 15D
- Não confundir com "APROVAR V2 para shadow_test 16D"

### Label de Teste

- `STRUCT_CORE_REALIGN_V2_15D_001` (format=15D, GP=50, 20 generation_events)

### Metadado de Rastreabilidade

Cada jogo gerado sob V2 deve conter:
```json
{
  "realignment_metadata": {
    "realignment_tag": "CORE_REALIGNMENT_V2",
    "evidence_epoch": "EPOCH_001_V2",
    "mode": "shadow_test",
    "v1_applied": true,
    "v2_applied": true,
    "v2_fallback_to_v1": false,
    "pool_pre_filter_applied": true,
    "prefix_3": "...",
    "suffix_3": "..."
  },
  "core_realignment_v2_applied": true
}
```

### Módulos

```
src/lotoia/generation/core_realignment_v2.py
src/lotoia/governance/lei15_15a_core_realignment_v2.py
```

---

## Teste Obrigatório V2

### Configuração

- Label: `STRUCT_CORE_REALIGN_V2_15D_001`
- Formato: 15D
- GP: 50
- Generation events: 20
- Jogos totais: 1.000

### Concursos a Reconciliar

3705, 3706, 3707, 3708, 3709, 3710, 3711

### Comparação

| Batch | Tipo |
|---|---|
| STRUCT_TEST_15D_001 | BASELINE (sem realinhamento) |
| STRUCT_REALIGN_V1_15D_001 | V1 (composição GP) |
| STRUCT_CORE_REALIGN_V2_15D_001 | V2 (pool + composição reforçada) |

---

## Critérios de Aprovação V2

V2 aprovada se e somente se, comparado com V1:

| Métrica | Critério |
|---|---|
| Melhor hit | ≥ 14 (não regredir) |
| Média hits | ≥ 12.143 (não regredir) |
| Runs com 14+ | ≥ 5 (não regredir) |
| Runs com 13+ | ≥ 47 (não regredir) |
| Top prefixo_3 (01-02-03) | < 35% (melhorar de 40.4%) |
| Top prefixo_4 (01-02-03-04) | Redução vs V1 |
| Top sufixo_3 (22-24-25) | ≤ 27% (manter ganho V1) |
| Top sufixo_4 (21-22-24-25) | ≤ 17% (manter ganho V1) |
| Similaridade GP | ≤ 9.717 (não regredir) |
| Jogos inválidos | 0 |
| Persistência PostgreSQL | 100% |

## Critérios de Rejeição V2

V2 rejeitada automaticamente se:
- Avançar para 16D antes de corrigir 15D
- Ativar `active` sem aprovação ADM
- Melhorar estrutura mas piorar hits
- Melhorar hits mas aumentar redundância
- Corrigir sufixo e piorar prefixo
- Usar CSV, SQLite ou session_state
- Deletar evidências EPOCH_001 ou Realign V1

---

## Consequências

### Positivas Esperadas

- Prefixo 01-02-03 < 35% (vs 40.4% do V1)
- Manutenção dos ganhos de hits do V1
- Maior cobertura de dezenas críticas ausentes
- Rastreabilidade completa via `core_realignment_v2_applied`

### Riscos

- Pool pre-filter pode reduzir o pool disponível demais → mitigado por fallback V1
- Thresholds mais rígidos podem dificultar composição completa → monitorar
- Penalizar muito o prefixo pode empurrar para prefixos sub-ótimos → validar hits

### Mitigações

- Fallback automático **obrigatório** para V1 se pool pós-filter < mínimo seguro
- Monitoramento de `pool_pre_filter_applied` e `v2_fallback_to_v1` nos metadados
- Comparação rigorosa nos critérios de aprovação

---

## Decisão Final ADM

Após o relatório comparativo dos 3 lotes, o ADM decide entre caminhos **distintos**:

| Decisão ADM | O que autoriza | O que NÃO autoriza |
|---|---|---|
| **APROVAR V2 para shadow_test 16D** | Estender testes V2 em 16D no modo `shadow_test` | Ativar `active`; avançar 16D sem validação 15D |
| **APROVAR V2 para active** | Produção com V2 em modo `active` | Decisão separada; requer ADR adicional e aprovação explícita |
| **PEDIR V3** | Nova iteração de ajuste | — |
| **MANTER V1** | V2 rejeitada; V1 permanece referência | — |
| **REJEITAR** | Retornar ao BASELINE (`STRUCT_TEST_15D_001`) | — |

**Importante:** aprovar V2 para `shadow_test` (inclusive extensão 16D) **não é**
a mesma coisa que aprovar modo `active`. São decisões institucionais separadas.

---

*ADR-044 | LotoIA | 2026-06-16*  
*Missão: MISSAO_DA_VITORIA_REAVALIAR_NUCLEOS_LEI15_15A*
