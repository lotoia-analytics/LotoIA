# =============================================================================
# CARTÃO DE TAREFA INSTITUCIONAL — LotoIA
# =============================================================================
mission_id: M-AGENT-001
titulo: "Constituição do Primeiro Agente de IA da LotoIA"
owner: agent_governanca
support:
  - agent_plataforma
  - agent_dados
priority: high
status: CONCLUÍDA
operational_effect: false
# -----------------------------------------------------------------------------
# Contexto
# -----------------------------------------------------------------------------
contexto: |
  O ecossistema LotoIA consolidou sua arquitetura com a Lei 15 (CORE_002) e a 
  Matriz de Agentes Institucionais (M-GOV-AGENTS-002). A evolução exige a 
  introdução de um Agente de IA para observação e recomendação contínua de 
  qualidade, operando de forma auditável e sem violar a soberania estatística.
# -----------------------------------------------------------------------------
# Objetivo (uma frase verificável)
# -----------------------------------------------------------------------------
objetivo: |
  Definir a arquitetura institucional completa do primeiro Agente de IA da LotoIA,
  produzindo todos os artefatos documentais exigidos sem alterar o código de produção.
# -----------------------------------------------------------------------------
# Escopo
# -----------------------------------------------------------------------------
autorizado:
  - Criar ADR-049 de constituição do Agente de IA
  - Criar Documento de Constituição
  - Criar Fluxograma Operacional
  - Criar Roadmap de Níveis de Autonomia
  - Criar Matrizes de Permissões, Riscos e Auditoria
proibido:
  - Implementar o agente em código de produção
  - Alterar geração, ML, Lei 15 ou CORE_002
  - Alterar public_app
  - Executar purge ou criar tabelas novas
  - Criar rotinas automáticas
# -----------------------------------------------------------------------------
# Dependências
# -----------------------------------------------------------------------------
depende_de:
  - ADR-048 (Matriz de Agentes Institucionais)
  - ADR-042 (Política de ML Assistivo)
bloqueia:
  - M-AGENT-002 (Implementação do Agente Nível 0)
# -----------------------------------------------------------------------------
# Entregáveis
# -----------------------------------------------------------------------------
entregaveis:
  - docs/adr/ADR-049-CONSTITUICAO-AGENTE-IA.md
  - docs/governance/CONSTITUICAO_AGENTE_IA.md
  - docs/governance/FLUXOGRAMA_AGENTE_IA.md
  - docs/governance/ROADMAP_AUTONOMIA_AGENTE.md
  - docs/governance/MATRIZES_AGENTE_IA.md
  - Evidência Git (branch, PR, commit)
  - Veredicto formal
# -----------------------------------------------------------------------------
# Testes mínimos
# -----------------------------------------------------------------------------
testes:
  - comando: "N/A"
    criterio: "Missão exclusivamente documental e arquitetural."
# -----------------------------------------------------------------------------
# Deploy (se aplicável)
# -----------------------------------------------------------------------------
deploy:
  ambiente: N/A
  checkpoint:
    - Missão não afeta runtime de produção.
# -----------------------------------------------------------------------------
# Veredictos aceitos (escolher um ao encerrar)
# -----------------------------------------------------------------------------
veredictos_possiveis:
  - M-AGENT-001 CONCLUÍDA — CONSTITUIÇÃO DO PRIMEIRO AGENTE DE IA DA LOTOIA DEFINIDA
# -----------------------------------------------------------------------------
# Evidência Git (preencher ao encerrar)
# -----------------------------------------------------------------------------
git:
  branch: cursor/m-agent-001-constituicao-agente-ia
  commits: []
  pr: 
  push_confirmado: false
# -----------------------------------------------------------------------------
# Notas
# -----------------------------------------------------------------------------
notas: |
  A próxima missão (M-AGENT-002) deverá focar na implementação do Nível 0 
  (Observador), adicionando o memory_kind `agent_operational_learning` na tabela 
  `scientific_institutional_memory` e os logs de observação.
