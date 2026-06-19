# M-ML-070-AUDIT-01 — Auditoria da Aplicação Efetiva da Política Estrutural 15D

> **STATUS pós-correção:** os achados abaixo (APENAS OBSERVACIONAL / NÃO APLICADA
> em GP:20) foram **corrigidos pela M-ML-070-FIX-01**: a política passou a governar
> o lote final por **formato** (não por quantidade), priorizando cartões conformes,
> expondo `structural_policy_applied=true` e alimentando o veredito/diagnóstico/plano.
> Rodar `scripts/ops/audit_m_ml_070_structural_policy_15d.py` após a correção
> classifica GP:20 como **APLICADA_EFETIVAMENTE**.

**Pergunta:** A Política Estrutural 15D (M-ML-070) realmente governa o lote final
entregue pelo GP soberano / CORE_002, ou atua apenas como memória / validação
posterior / observabilidade?

**Veredito:** **APENAS OBSERVACIONAL** — e **NÃO APLICADA** no cenário auditado GP:20.

Evidência reproduzível:
- Script read-only: `scripts/ops/audit_m_ml_070_structural_policy_15d.py`
- Suíte de auditoria: `tests/ml/test_m_ml_070_audit_01_application.py`

---

## 1. Resumo executivo

| Item | Resultado |
|------|-----------|
| Política carregada da memória ML | ✅ Sim (`ensure_structural_policy_15d_memory`, versão `M-ML-070-v1`) |
| Política aplicada no fluxo GP 15D | ⚠️ Parcial: só é invocada quando `count == 15` (quantidade de jogos), não pelo formato 15 dezenas |
| Lote final respeita repetição/paridade/sequência | ❌ Não garantido — não conformes permanecem no lote |
| Violações rastreadas | ✅ Sim (validação por jogo + bundle) |
| Central ML recebe evidência | ⚠️ Apenas exibe card; não entra no diagnóstico/veredito/plano |
| `structural_policy_applied` exposto | ❌ Ausente (artefato esperado pelo critério #2 não existe) |
| Lote final é alterado pela política | ❌ Não (`lote_alterado = False`) |
| **Classificação final** | **APENAS OBSERVACIONAL** (NÃO APLICADA em GP:20) |

---

## 2. Achados técnicos (com evidência)

### 2.1. O gate de aplicação é por quantidade, não por formato
`src/lotoia/generator/basic_generator.py` aplica a política dentro de
`if count == 15:`. Aqui `count` é a **quantidade de jogos**, não o tamanho do
cartão. Empiricamente:

| Cenário | jogos | card_size | bundle da política |
|---------|-------|-----------|--------------------|
| GP:20 (count=20) | 20 | 15 | **AUSENTE** |
| GP:15 (count=15) | 15 | 15 | PRESENTE |

➡️ O lote **GP:20 15D** (cenário auditado) **não recebe nenhum artefato da
política**. O 15D é o formato (card_size sempre 15 no path soberano); o gate
correto deveria ser por `game_size == 15`, não `count == 15`.

### 2.2. A aplicação não governa o lote final (observacional)
`apply_structural_policy_15d_to_sovereign_batch` valida o pool, mas em
`_append_candidate` insere primeiro **todos** os `selected_games` (saída original
do GP), antes do pool conforme. Como `compose_sovereign_gp` já entrega
`required_count` jogos únicos, os slots são preenchidos pela seleção original e o
pool conforme nunca é usado.

Teste de efeito (script): `required_count=20`, `selected=20`, `final=20`,
`lote_alterado = False`, `games_compliant = 9/20`. Ou seja, **11 jogos não
conformes permaneceram** no lote final sem bloqueio/reordenação.

### 2.3. `structural_policy_applied` não existe
A busca por `structural_policy_applied` no repositório retorna zero ocorrências.
O bundle expõe `structural_policy_memory_loaded`, `structural_policy_version` e
`policy_compliance_status`, mas **não** o flag de aplicação efetiva pedido no
critério #2.

### 2.4. Central ML: exibe, não decide
`dashboard/institutional_ml_calibration_cockpit.py::_render_structural_policy_15d_card`
apenas **exibe** memória/conformidade. Os módulos de veredito/diagnóstico
(`ml_operational_verdict.py`, `scientific_commander.py`,
`ml_diagnostic_panels.py`, `scientific_calibration_engine.py`) **não** consomem
`policy_compliance_status` / `policy_violations`. Critério #7 (entrar no
diagnóstico/veredito/plano) **não atendido**.

### 2.5. Cobertura Estrutural
`src/lotoia/observability/coverage_evidence_interpreter.py` inclui
`structural_policy_15d_memory` e `structural_policy_15d_application`, com gate
correto por formato (`is_structural_policy_15d_format`). Porém a `application` só
fica disponível se o `context_json` do evento contiver o bundle — o que só ocorre
no path `count == 15`.

---

## 3. Compliance dos jogos (empírico)

Concurso anterior usado: **3706** → `[1,4,6,8,9,10,12,14,15,16,18,21,22,24,25]`
(history[-1] do CSV, mesma referência usada pela política).
Política: repetição 7–10 · paridade permitida {6/9,7/8,8/7,9/6} · sequência ≤ 6.

### GP:20 (cenário auditado — sem política aplicada)
- total: 20 · conformes: **15** · violação: 5 · taxa: **0.75**
- violações por regra: sequência>6 (3 jogos), paridade (2 jogos), repetição (1 jogo)
- jogos afetados: sequência → #17,#19,#20 · paridade → #13,#14 · repetição → #14

### GP:15 (count==15 — política presente no bundle)
- total: 15 · conformes: **13** · violação: 2 · taxa: **0.8667**
- bundle: `policy_compliance_status = partial`, `games_compliant = 9/20` no teste de efeito
- violações: paridade (#13,#14), repetição (#14)

> A presença de não conformes no lote final, mesmo com a política "ativa",
> confirma a natureza observacional.

---

## 4. Classificação final

**APENAS OBSERVACIONAL.** A política é carregada, valida cada jogo e expõe
conformidade/violações para a Cobertura e para um card da Central ML, **mas não
governa o lote final** (não reordena, não bloqueia, não substitui não conformes).
No cenário específico **GP:20** ela é **NÃO APLICADA** (gate por quantidade).

### Recomendações de remediação (missão futura, fora do escopo desta auditoria)
1. Trocar o gate `count == 15` por `game_size == 15` (formato), cobrindo GP:N 15D.
2. Em `_append_candidate`, priorizar o pool conforme antes da seleção original
   (ou bloquear/substituir não conformes) para tornar a aplicação efetiva.
3. Expor `structural_policy_applied = true` no bundle.
4. Consumir `policy_compliance_status` no veredito/diagnóstico/plano da Central ML.

> Auditoria não força oficialização nem mascara violação; remediação não foi
> aplicada para preservar CORE_002 / Lei 15 e exigir aprovação institucional.

---

## 5. Testes executados

- ✅ `tests/ml/test_m_ml_070_structural_policy_15d.py` (M-ML-070)
- ✅ `tests/ml/test_m_ml_070_audit_01_application.py` (esta auditoria, 4 testes)
- ✅ `tests/ml/test_m_ml_069_structural_auto_calibration.py` + `test_m_ml_069_audit_01_application.py` (regressão 069)
- ✅ `tests/ml/test_m_ml_067_format_aware_overlap.py` (regressão 067)
- ✅ `tests/ml/test_m_ml_068_structural_concentration_audit.py` (lógica)
- ✅ `scripts/checks/governance_contract_check.py`
- ⚠️ Pré-existente em `main` (não relacionado a esta auditoria): pins de build
  marker desatualizados (`test_build_marker_v56` em
  `test_overlap_format_thresholds.py` e `test_m_ml_068_*`) esperam v56 mas o
  marker atual é v58.

---

## 6. Integridade institucional

- CORE_002, Lei 15, Lei 15A e `public_app`: **não alterados** (auditoria adicionou
  apenas script read-only + testes + este relatório).
- M-ML-067 / M-ML-068 / M-ML-069: **intactas**.
- **Sem purge.** Sem `structural_calibration_memory` 16D–23D tocada.
