# Registro Institucional de Missões — LotoIA

Log cronológico de missões, evidências, bloqueios e veredictos.

**Modo:** Fase 0 — documental/Git (fonte: este arquivo versionado no repositório).

---

## Índice rápido

| ID | Título | Status | Veredicto |
|----|--------|--------|-----------|
| [M-GOV-030](#m-gov-030--gestão-de-projetos-fase-0) | Gestão de Projetos Fase 0 | `EM_EXECUCAO` | pendente |
| [M-OPS-INC-001](#m-ops-inc-001--incidente-deploy-artefato-não-versionado) | Incidente deploy artefato não versionado | `AGUARDANDO_EVIDENCIA` | pendente |
| [M-GOV-027](#m-gov-027--auditoria-constitucional) | Auditoria constitucional | `AGUARDANDO_VEREDICTO` | `LOTOIA CONFLITANTE` |
| [M-LEI15-002](#m-lei15-002--implantação-lei15_core_002) | Implantação LEI15_CORE_002 | `CONCLUIDA` | `NÚCLEO SOBERANO IMPLANTADO` |
| [M-GOV-028](#m-gov-028--manutenção-institucional-contínua) | Mission 28 manutenção | `CONCLUIDA` | `APROVADO` |
| [M-OPS-015](#m-ops-015--cloud-only-railway) | Cloud-only Railway | `CONCLUIDA` | `APROVADO` |

---

## Entradas

### M-GOV-030 — Gestão de Projetos Fase 0

| Campo | Valor |
|-------|-------|
| Data abertura | 2026-06-17 |
| Projeto | `P-GOV-001` |
| Agentes | `agent_governanca` (primário), `agent_plataforma` (suporte) |
| Status | `EM_EXECUCAO` |
| Origem | Missão institucional pós-incidente de deploy |

**Objetivo:** Implantar camada documental de Gestão de Projetos (Fase 0) sem alterar Painel ADM, geração, banco ou `LEI15_CORE_002`.

**Escopo autorizado:**

- `docs/governance/POLITICA_GESTAO_PROJETOS_LOTOIA.md`
- `docs/governance/gestao_projetos/*`
- referências em `.cursor/rules/agent_governanca.mdc`

**Escopo proibido:** Painel ADM, PostgreSQL, geração, Núcleo LEI15_CORE_002, automação destrutiva.

**Evidência Git:**

| Campo | Valor |
|-------|-------|
| Branch | `cursor/gestao-projetos-fase0-cae6` |
| Tipo | documental |

**Checklist:** B e C em preenchimento; D e E = N/A (escopo documental).

**Veredicto:** pendente.

---

### M-OPS-INC-001 — Incidente deploy artefato não versionado

| Campo | Valor |
|-------|-------|
| Data abertura | 2026-06-17 (retroativa — registro Fase 0) |
| Projeto | `P-OPS-001` |
| Agente | `agent_plataforma` |
| Status | `AGUARDANDO_EVIDENCIA` |

**Descrição:** Deploy afetado por artefato ou configuração não rastreada no Git. Motivador da Política de Gestão de Projetos Fase 0.

**Evidência faltante:**

- inventário formal do artefato não versionado;
- commit ou ADR de correção;
- validação pós-deploy com SHA documentado.

**Bloqueio ativo:** `BLK-GIT-001`, `BLK-DEPLOY-001`

**Veredicto:** pendente — missão permanece aberta até fechamento com evidência.

**Lição institucional:** Tarefa não existe como concluída sem prova versionada no repositório.

---

### M-GOV-027 — Auditoria constitucional

| Campo | Valor |
|-------|-------|
| Data | 2026-06-17 |
| Agente | `agent_governanca` |
| Status | `AGUARDANDO_VEREDICTO` |
| Documento | `AUDITORIA_CONSTITUCIONAL_LOTOIA_2026_06_17.md` |

**Resumo:** Plataforma funcional para auditoria read-only, porém constitucionalmente fragmentada após implantação LEI15_CORE_002.

**Veredicto preliminar (relatório):** `LOTOIA CONFLITANTE — EXIGE CORREÇÃO ANTES DO PAINEL`

**Missões derivadas sugeridas:**

- M-LEI15-001 (alinhamento ADM/doc) — `BLOQUEADA`
- correção purge evidência Lei 001 — backlog

---

### M-LEI15-002 — Implantação LEI15_CORE_002

| Campo | Valor |
|-------|-------|
| Data | 2026-06-17 |
| Agente | `agent_geracao` |
| Status | `CONCLUIDA` |
| ADR | ADR-046 |
| Relatório | `RELATORIO_LEI15_CORE_002_IMPLANTACAO_2026_06_17.md` |

**Veredicto:** `NÚCLEO SOBERANO LEI 15 IMPLANTADO`

**Ressalva:** `LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=0` — geração bloqueada até missão autorizada.

---

### M-GOV-028 — Manutenção institucional contínua

| Campo | Valor |
|-------|-------|
| Data | política formalizada em Mission 28 |
| Agente | `agent_governanca` |
| Status | `CONCLUIDA` |
| Documento | `MISSION_28_CONTINUOUS_MAINTENANCE_POLICY.md` |

**Veredicto:** `APROVADO` — política de manutenção recorrente ativa.

---

### M-OPS-015 — Cloud-only Railway

| Campo | Valor |
|-------|-------|
| Data | 2026-06-15 |
| Agente | `agent_plataforma` |
| Status | `CONCLUIDA` |
| Documento | `RAILWAY_CLOUD_ONLY_DEPLOYMENT_2026_06_15.md` |

**Veredicto:** `APROVADO` — Lei 001 operacional em cloud; PostgreSQL como fonte única.

**Nota:** validações SHA subsequentes devem referenciar este registro e atualizar evidência de deploy quando o SHA ativo mudar.

---

## Modelo de nova entrada

Copiar e preencher ao abrir missão:

```markdown
### M-___-___ — Título

| Campo | Valor |
|-------|-------|
| Data abertura | YYYY-MM-DD |
| Projeto | P-___-___ |
| Agente | agent___ |
| Status | PROPOSTA |

**Objetivo:**

**Escopo autorizado:**

**Escopo proibido:**

**Evidência Git:** branch / commits / PR

**Evidência testes:** N/A ou comando + resultado

**Evidência deploy:** N/A ou SHA + checklist

**Bloqueios:**

**Veredicto:** pendente | APROVADO | ...
```

---

## Regras do registro

1. Entradas são **append-only** — não apagar histórico; corrigir com nova nota datada.
2. Veredicto formal é obrigatório antes de status `CONCLUIDA` no quadro.
3. Incidentes operacionais devem gerar entrada aqui em até um ciclo Git.
4. Export JSON futuro (Fase 1+) não substitui este arquivo na Fase 0.

---

## Referências

- [`QUADRO_PROJETOS_MISSOES.md`](QUADRO_PROJETOS_MISSOES.md)
- [`POLITICA_GESTAO_PROJETOS_LOTOIA.md`](../POLITICA_GESTAO_PROJETOS_LOTOIA.md)
- [`GOVERNANCA_OPERACIONAL_LOTOIA.md`](../GOVERNANCA_OPERACIONAL_LOTOIA.md) — Regra 8 (incidentes)
