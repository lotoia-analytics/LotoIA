# Proteção da Branch `main` — Governança LotoIA

## Status

`BRANCH_PROTECTION_MAIN_DOCUMENTED`

---

## Objetivo

Impedir alteração direta em código institucional, Lei 15, Lei 15A, dashboard, runtime,
histórico, analítico e governança sem PR, revisão de CODEOWNER e checks obrigatórios.

---

## Artefatos no repositório

| Artefato | Função |
|----------|--------|
| `.github/CODEOWNERS` | Revisão obrigatória de owner em áreas institucionais |
| `.github/workflows/governance-gate.yml` | Checks `lint`, `tests` e gates institucionais |
| `scripts/checks/governance_contract_check.py` | Valida contratos de governança |
| `scripts/checks/lei15_lei15a_boundary_check.py` | Valida fronteira Lei 15 / Lei 15A |
| `scripts/checks/dashboard_semantic_label_check.py` | Valida rótulos semânticos do painel |
| `scripts/apply_main_branch_protection.sh` | Aplica regra de proteção via GitHub API |

---

## Checks obrigatórios antes do merge

1. `lint`
2. `tests`
3. `governance-contract-check`
4. `lei15-lei15a-boundary-check`
5. `dashboard-semantic-label-check`

> Após o primeiro workflow em `main`, habilite estes contextos em
> **Settings → Branches → Branch protection rules → main**.

---

## Aplicar proteção (admin do repositório)

```bash
chmod +x scripts/apply_main_branch_protection.sh
./scripts/apply_main_branch_protection.sh
```

Ou manualmente em **Settings → Branches → Add rule** para `main`:

- Require a pull request before merging (1 approval)
- Dismiss stale pull request approvals when new commits are pushed
- Require review from Code Owners
- Require status checks to pass before merging (lista acima)
- Require branches to be up to date before merging
- Require conversation resolution before merging
- Require linear history
- Do not allow bypassing the above settings
- Restrict who can push to matching branches (recomendado: ninguém direto em `main`)
- Do not allow force pushes
- Do not allow deletions

---

## Áreas protegidas por CODEOWNERS

- `docs/governance/**`
- `dashboard/**`
- `runtime/**`, `lotoia_runtime.py`
- `history/**`, `analytics/**`, `institutional/**`, `src/lotoia/analytics/**`
- Arquivos `*lei15*`, `*lei15a*`, `*Lei15*`, `*Lei15A*`
- `.github/**`

Owner padrão: `@lotoia-analytics`

---

## Referências

- `AGENTS.md`
- `docs/governance/POLITICA_ML_ASSISTIVO.md`
- `docs/governance/ADR_LEI15A_CARTAO_REGISTRO_APOSTA.md`
