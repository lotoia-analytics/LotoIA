# Inventário de Rotas — Painel ADM (M-PLAT-040)

**Missão:** `M-PLAT-040`  
**Build:** `institutional-adm-runtime-v16`  
**Módulo:** `dashboard/institutional_route_inventory.py`

---

## Rotas ativas (menu constitucional)

| page_id | Label | Grupo |
|---------|-------|-------|
| `governance_read_only` | Governança Institucional — read-only | Governança |
| `core_002_read_only` | Núcleo Lei 15 — CORE_002 | Governança |
| `home` | Painel Inicial Institucional | Núcleo Operacional |
| `clean_law15_generation` | Gerador ADM CORE_002 — BLOQUEADO | Núcleo Operacional |
| `conference` | Conferir Resultados — Auditoria de Lotes Persistidos | Núcleo Operacional |
| `simulation` | Simular Resultados | Núcleo Operacional |
| `structural_coverage` | Cobertura Estrutural | Analítico observacional |
| `institutional_simulation_backtesting` | Simulação Institucional / Backtesting | Analítico observacional |
| `central_ml_diagnostics` | Central ML Assistiva | Diagnósticos ML |
| `audit_monitoring_side_leak` | Vazamento Lateral Constitucional | Diagnósticos ML |
| `restricted_controlled_cleanup` | Área Restrita — Limpeza Controlada | Área Restrita |

Históricos, auditoria runtime e sub-rotas observacionais permanecem ativas conforme `INSTITUTIONAL_ALLOWED_PAGES`.

---

## Rotas bloqueadas

| page_id | Motivo |
|---------|--------|
| `clean_law15_generation` | Geração soberana bloqueada (ADR-047 / M-LEI15-003) |

---

## Aliases seguros

| Alias | Destino | Motivo |
|-------|---------|--------|
| `generation` | `clean_law15_generation` | Rota órfã — redireciona para gerador bloqueado |
| `Gerar Jogos` | `clean_law15_generation` | Label legado |
| `clear_histories` | `restricted_controlled_cleanup` | M-DADOS-039 — limpeza de sessão |
| `delete_history` | `restricted_controlled_cleanup` | M-DADOS-039 — purge bloqueado |
| `Apagar Histórico` | `restricted_controlled_cleanup` | Label ambíguo removido |
| `Limpar Históricos` | `restricted_controlled_cleanup` | Label ambíguo removido |

---

## Removidas do menu (fallback)

- `strategies_analysis`, `strategies_test`, `strategies_simulation`
- `institutional_replay`, `operational_statistics`, `hb_geometry`
- `audit_monitoring`, `audit_monitoring_group_performance`, `audit_monitoring_offline_hypotheses`

---

## Pendências

| page_id | Estado |
|---------|--------|
| `lei15a_operational` | Sem rota de menu — Lei 15A inoperante (M-GOV-038) |

---

## Guardas institucionais

- Nenhuma rota legada chama `generate_best_games` ou `_generate_direct_15_games`
- `batch_label=None` rejeitado (M-LEI15-003)
- Purge real bloqueado — aliases de limpeza → Área Restrita
- `public_app` fora do escopo

---

## Veredicto

**M-PLAT-040 CONCLUÍDA E ATIVA EM PRODUÇÃO — ÓRFÃS E ROTAS LEGADAS DO ADM LIMPAS/BLOQUEADAS COM SEGURANÇA**
