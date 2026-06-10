# Guia simples — Proteger a branch `main` no GitHub

**Tempo estimado:** 5 minutos  
**Quem pode fazer:** dono do repositório ou admin da org `lotoia-analytics`

---

## Link direto (comece aqui)

Abra no navegador (logado na conta certa):

**https://github.com/lotoia-analytics/LotoIA/settings/rules**

Se não abrir, use:

**https://github.com/lotoia-analytics/LotoIA/settings/branches**

---

## Opção A — Rulesets (GitHub novo, recomendado)

1. Entre em **Settings** do repositório LotoIA  
2. Menu lateral: **Rules** → **Rulesets**  
3. Clique **New ruleset** → **New branch ruleset**  
4. Preencha:
   - **Ruleset name:** `Proteger main`
   - **Enforcement status:** **Active**
5. Em **Bypass list**, deixe vazio (ninguém pode pular a regra)
6. Em **Target branches**, clique **Add target** → **Include default branch**  
   *(ou digite `main` se preferir)*
7. Marque estas regras:

   | Marque esta opção |
   |---|
   | Restrict deletions |
   | Require linear history |
   | Require a pull request before merging |
   | → Required approvals: **1** |
   | → Dismiss stale pull request approvals when new commits are pushed |
   | → Require review from Code Owners |
   | Require status checks to pass |
   | → Require branches to be up to date before merging |
   | → Adicione os checks (após 1º workflow rodar): `lint`, `tests`, `governance-contract-check`, `lei15-lei15a-boundary-check`, `dashboard-semantic-label-check` |
   | Block force pushes |
   | Require conversation resolution before merging |

8. Clique **Create** ou **Save**

---

## Opção B — Branch protection rules (GitHub clássico)

1. Abra: **https://github.com/lotoia-analytics/LotoIA/settings/branches**  
2. Clique **Add branch protection rule**  
3. **Branch name pattern:** digite `main`  
4. Marque **tudo** abaixo:

```
☑ Require a pull request before merging
    ☑ Require approvals: 1
    ☑ Dismiss stale pull request approvals when new commits are pushed
    ☑ Require review from Code Owners

☑ Require status checks to pass before merging
    ☑ Require branches to be up to date before merging
    (na caixa de busca, selecione quando aparecerem:)
    - lint
    - tests
    - governance-contract-check
    - lei15-lei15a-boundary-check
    - dashboard-semantic-label-check

☑ Require conversation resolution before merging
☑ Require linear history
☑ Do not allow bypassing the above settings
☑ Restrict who can push to matching branches
    → deixe vazio ou só bots de deploy autorizados

☑ Do not allow force pushes
☑ Do not allow deletions
```

5. Clique **Create** ou **Save changes**

---

## Os 5 checks só aparecem depois do 1º workflow

O workflow já está no repositório (`governance-gate.yml`).

1. Abra: **https://github.com/lotoia-analytics/LotoIA/actions**  
2. Aguarde um run verde em `main` (pode levar 2–3 min)  
3. Volte em **Settings → Branches** ou **Rulesets**  
4. Agora os nomes dos checks aparecem na busca — selecione os 5

Se ainda não aparecerem, faça um commit qualquer via PR e merge; o workflow roda no PR.

---

## Como saber se deu certo

Tente editar `main` direto no GitHub:

1. Abra um arquivo qualquer em `main`  
2. Clique no lápis (Edit)  
3. O GitHub deve **bloquear** e pedir **Pull Request**

Ou tente push direto no terminal — deve falhar com mensagem de branch protegida.

---

## Precisa de ajuda?

Se não vir **Settings** no repositório, sua conta não é admin. Peça ao dono de `lotoia-analytics` para:

1. Ir em **Settings → Collaborators** e dar role **Admin**, ou  
2. Seguir este guia logado como owner.

---

## Resumo em uma frase

> A `main` fica protegida quando você marca “exigir PR + aprovação + checks” nas configurações do GitHub — o código dos checks já está no repositório.
