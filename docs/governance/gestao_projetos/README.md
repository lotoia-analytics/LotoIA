# Gestão de Projetos LotoIA — Fase 0

Camada documental de controle de missões. **Sem interface, sem banco, sem automação destrutiva.**

## Documentos

| Arquivo | Uso |
|---------|-----|
| [../POLITICA_GESTAO_PROJETOS_LOTOIA.md](../POLITICA_GESTAO_PROJETOS_LOTOIA.md) | Política institucional (lei operacional) |
| [QUADRO_MISSOES.md](QUADRO_MISSOES.md) | Quadro ativo — o que está em andamento |
| [CHECKLIST_MISSAO_OBRIGATORIO.md](CHECKLIST_MISSAO_OBRIGATORIO.md) | Gate obrigatório por missão |
| [MODELO_CARTAO_TAREFA.md](MODELO_CARTAO_TAREFA.md) | Template para abrir missão |
| [MATRIZ_STATUS_TAREFAS.md](MATRIZ_STATUS_TAREFAS.md) | Estados, transições e veredictos |
| [REGISTRO_MISSOES.md](REGISTRO_MISSOES.md) | Histórico auditável de missões |

## Regra rápida

> Nenhuma missão encerra sem veredicto formal + evidência Git (quando houver código).

## Atualização

Ao abrir, avançar ou encerrar missão:

1. Preencher cartão (cópia do modelo).
2. Atualizar `QUADRO_MISSOES.md`.
3. Ao encerrar, append em `REGISTRO_MISSOES.md` com hash, testes e veredicto.
