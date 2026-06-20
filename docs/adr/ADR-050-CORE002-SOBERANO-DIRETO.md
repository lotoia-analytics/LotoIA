# ADR-050 — CORE_002 Soberano Direto (M-OPS-079)

## Status

**ACEITO** — 2026-06-20

| Campo | Valor |
|-------|-------|
| Registro | `ADR-050-CORE002-SOBERANO-DIRETO` |
| Missão | `M-OPS-079` |
| Agentes | `agent_plataforma` (primário), `agent_governanca`, `agent_qualidade` |
| Depende de | M-ML-079 (mergeada) |

---

## Contexto

O CORE_002 (`LEI15_CORE_002`) é o gerador soberano da LotoIA: produz jogos estruturados, pontuados e classificados por perfil histórico sem depender de validação externa para existir como motor de geração.

Após a consolidação do ML operacional (M-ML-073, M-ML-074, M-AGENT-002), componentes auxiliares passaram a atuar como **portões de aprovação** no fluxo de geração quando habilitados por padrão (`default="1"`). Isso tensiona a política institucional documentada em ADR-042:

> ML como Assistente: atua exclusivamente como camada de calibração, diagnóstico e reranking. Nunca substitui a lógica estatística soberana nem gera jogos autonomamente.

O bloqueio de entrega por limiares de diversidade/cobertura (mesmo em modo ATENÇÃO) reforçava o papel de portão, em vez de ferramenta analítica sob demanda.

---

## Decisão

O **CORE_002 é o gerador soberano direto**. O fluxo operacional padrão no código é:

1. Usuário solicita N jogos (15D–23D, 1–100)
2. `build_sovereign_pool` + `compose_sovereign_gp` entregam o lote
3. Política Estrutural 15D (M-ML-079) aplica diagnóstico sem bloqueio operacional
4. Jogos persistidos no PostgreSQL

Os componentes ML permanecem no codebase como **ferramentas analíticas opt-in**, ativadas explicitamente via variáveis de ambiente no Railway ou no painel ADM quando o operador solicitar análise/calibração supervisionada.

### Defaults alterados (`"1"` → `"0"`)

| Módulo | Função | Variável de ambiente |
|--------|--------|----------------------|
| `institutional_supervised_ml.py` | `is_ml_operational_enabled()` | `LOTOIA_ML_CORE_002_OPERATIONAL_ENABLED` |
| `ml_operational_hierarchy.py` | `is_ml_operational_hierarchy_enabled()` | `LOTOIA_ML_OPERATIONAL_HIERARCHY_ENABLED` |
| `pre_final_pool_ml_calibration.py` | `is_pre_final_pool_ml_enabled()` | `LOTOIA_ML_PRE_FINAL_POOL_ENABLED` |
| `agent_operador_ml_executor.py` | `is_agent_operador_ml_enabled()` | `LOTOIA_AGENT_OPERADOR_ML_ENABLED` |
| `pre_gp_deterministic_recovery.py` | `is_pre_gp_recovery_enabled()` | `LOTOIA_ML_PRE_GP_RECOVERY_ENABLED` |

---

## Componentes reposicionados

| Componente | Papel anterior | Papel após ADR-050 |
|------------|----------------|-------------------|
| CORE_002 | Gera, mas podia ser bloqueado pelo ML | Soberano — gera e entrega diretamente |
| ML Operacional | Portão de aprovação | Ferramenta analítica opt-in |
| Hierarquia ML (M-ML-073) | Etapas obrigatórias pré-GP | Diagnóstico/recuperação sob demanda |
| Pre-Final Pool ML (M-ML-071) | Calibração automática no pipeline | Calibração quando ML ativo |
| Agente Operador ML (M-AGENT-002) | Intervenção pré-entrega | Observador/corretor quando ativado |
| Recuperação pré-GP (M-ML-074) | Loop antes de expor bloqueio | Loop apenas com ML ativo |

---

## Consequências

### Positivas

- Geração ADM funciona no Railway sem variáveis ML adicionais
- Alinhamento com ADR-042 e AGENTS.md (ML auxiliar, não central)
- Reversibilidade total via env vars no Railway

### Negativas / mitigação

- Operadores que dependiam do ML automático devem definir `LOTOIA_ML_CORE_002_OPERATIONAL_ENABLED=1` (e flags subordinadas conforme necessário)
- Testes que assumiam ML ativo por padrão foram atualizados para opt-in explícito

---

## Reversibilidade

Qualquer componente pode ser reativado individualmente:

```bash
LOTOIA_ML_CORE_002_OPERATIONAL_ENABLED=1
LOTOIA_ML_OPERATIONAL_HIERARCHY_ENABLED=1
LOTOIA_ML_PRE_FINAL_POOL_ENABLED=1
LOTOIA_ML_PRE_GP_RECOVERY_ENABLED=1
LOTOIA_AGENT_OPERADOR_ML_ENABLED=1
```

---

## Escopo não alterado

- Lógica interna do CORE_002 (`lei15_core_002.py`, `lei15_core_candidate_001.py`)
- Lei 15, Lei 15A, núcleo soberano
- Schema PostgreSQL
- `structural_policy_15d.py` (M-ML-079)
- `public_app.py`
- Telas de Cobertura Estrutural, Histórico Analítico, Conferir Resultados

---

## Referências

- ADR-042 — Política ML Assistivo
- ADR-047 — Transição Constitucional Lei 15 / CORE_002
- M-ML-079 — Reconciliação validadores 15D
- `docs/governance/POLITICA_ML_ASSISTIVO.md`
