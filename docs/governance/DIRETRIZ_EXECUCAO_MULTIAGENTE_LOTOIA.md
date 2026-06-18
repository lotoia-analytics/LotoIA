# Diretriz de Execução Multiagente — LotoIA

## Status

`DIRETRIZ_MULTIAGENTE_FASE_0` — 2026-06-17

---

## 1. Agentes institucionais

| Agente | Domínio |
|--------|---------|
| `agent_governanca` | Políticas, ADRs, quadro, veredictos |
| `agent_visual` | Painel ADM, UX read-only |
| `agent_plataforma` | Runtime, deploy, API, entrypoints |
| `agent_geracao` | Lei 15 / CORE_002 (bloqueado até missão) |
| `agent_dados` | PostgreSQL, histórico, Lei 001 |
| `agent_ml` | ML assistivo, diagnóstico |
| `agent_estatistico` | Métricas, walk-forward |
| `agent_qualidade` | Testes, ruff, CI |

---

## 2. Regra operacional

1. Cada agente atua **somente** no escopo autorizado.
2. Encontrou risco (geração, purge, banco, Núcleo, conflito constitucional)? **Parar subfluxo**, registrar, reportar.
3. **Demais agentes** continuam frentes seguras na mesma rodada/pacote.
4. Nenhum merge direto em `main` sem PR.
5. Evidência de produção **proporcional ao risco** — ver checkpoint simplificado.

---

## 3. Formato de relatório por agente

Obrigatório em `docs/governance/gestao_projetos/rodada_multiagente/RELATORIO_AGENT_*.md`:

1. Agente responsável
2. Missões executadas
3. Arquivos lidos / alterados
4. Implementado vs planejado
5. Bloqueios e riscos
6. Testes e resultados
7. Confirmações (sem geração, purge, banco indevido, Núcleo, Lei 15A, ML operacional, public_app)
8. Veredicto: CONCLUÍDO | PARCIAL | BLOQUEADO | RISCO | EXIGE DECISÃO

---

## 4. Branch de pacote

Preferência: `cursor/<nome-pacote>-cae6` única por rodada.

Subagentes podem trabalhar em commits sequenciais na mesma branch.

---

## 5. Zonas sempre protegidas

Sem missão + ADR quando exigido:

- `LEI15_CORE_002` e flags soberanas
- Geração operacional
- Purge / histórico Lei 001
- Schema/dados PostgreSQL operacionais
- ML operacional automático
- Remoção de `public_app`

---

## 6. Referências

- `.cursor/rules/agent_*.mdc`
- `POLITICA_MISSOES_POR_PACOTE_LOTOIA.md`
- `QUADRO_PROJETOS_MISSOES.md`
