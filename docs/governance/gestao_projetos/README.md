# Gestão de Projetos LotoIA — Fase 0

Camada documental e versionada no Git para controle institucional de missões.

**Modo:** Fase 0 — sem Painel ADM, sem banco, sem automação destrutiva.

---

## Documentos oficiais

| Documento | Caminho | Uso |
|-----------|---------|-----|
| Política (lei) | [`../POLITICA_GESTAO_PROJETOS_LOTOIA.md`](../POLITICA_GESTAO_PROJETOS_LOTOIA.md) | Regras institucionais |
| Checkpoint produção | [`../POLITICA_CHECKPOINT_PRODUCAO_LOTOIA.md`](../POLITICA_CHECKPOINT_PRODUCAO_LOTOIA.md) | Evidência de produção proporcional ao risco |
| Missões por pacote | [`../POLITICA_MISSOES_POR_PACOTE_LOTOIA.md`](../POLITICA_MISSOES_POR_PACOTE_LOTOIA.md) | Agrupamento e risco de pacotes |
| Multiagente | [`../DIRETRIZ_EXECUCAO_MULTIAGENTE_LOTOIA.md`](../DIRETRIZ_EXECUCAO_MULTIAGENTE_LOTOIA.md) | Rodadas multiagente |
| Rodada multiagente | [`rodada_multiagente/`](rodada_multiagente/) | Relatórios por agente |
| Quadro de projetos | [`QUADRO_PROJETOS_MISSOES.md`](QUADRO_PROJETOS_MISSOES.md) | Visão ativa |
| Checklist obrigatório | [`CHECKLIST_MISSAO_OBRIGATORIO.md`](CHECKLIST_MISSAO_OBRIGATORIO.md) | Gate por missão |
| Cartão de tarefa | [`TEMPLATE_CARTAO_TAREFA_INSTITUCIONAL.md`](TEMPLATE_CARTAO_TAREFA_INSTITUCIONAL.md) | Modelo de tarefa |
| Matriz de status | [`MATRIZ_STATUS_TAREFAS.md`](MATRIZ_STATUS_TAREFAS.md) | Estados e transições |
| Registro institucional | [`REGISTRO_MISSOES_INSTITUCIONAL.md`](REGISTRO_MISSOES_INSTITUCIONAL.md) | Log e veredictos |

---

## Fluxo rápido

1. Abrir cartão a partir do template.
2. Registrar a missão no quadro e no registro.
3. Executar com branch Git e agente roteado.
4. Preencher checklist obrigatório.
5. Aplicar matriz de status até veredicto formal.
6. Atualizar quadro e registro ao encerrar.

---

## Agentes responsáveis

- **Primário:** `agent_governanca`
- **Suporte runtime/deploy:** `agent_plataforma`
