# Governanca Operacional LotoIA

## Status
Documento oficial de extensao pratica da Lei No 001 - Fonte Unica da Verdade LotoIA.

## Objetivo

Estabelecer as regras de governanca que garantem que nenhum modulo da plataforma opere fora
da fonte unica institucional.

## Fonte oficial

**PostgreSQL Institucional**

Nenhum dado operacional e considerado verdadeiro se nao estiver persistido, validado e
rastreavel no PostgreSQL Institucional.

## Relacao com a Lei No 001

- A Lei No 001 define a cadeia oficial de verdade.
- A Governanca Operacional define como essa cadeia sera fiscalizada, auditada e aplicada
  na pratica.
- Qualquer divergencia entre painel, historicos, auditoria ou memoria e tratada como incidente
  de governanca.

## Regras de governanca

### Regra 1 - Fonte unica

Todo dado operacional deve vir do PostgreSQL Institucional.

#### Obrigatorio para

- concursos oficiais
- dezenas sorteadas
- jogos gerados
- conferencias
- acertos
- premiacoes
- memoria HB
- historicos
- painel ADM
- futura integracao WhatsApp

#### Proibido como fonte operacional

- CSV
- SQLite local
- session_state
- cache
- payload temporario
- resposta direta da API sem persistencia
- snapshot antigo

### Regra 2 - Importacao oficial

Toda importacao deve seguir:

```text
Caixa
  -> Validacao
  -> Persistencia no PostgreSQL
  -> Confirmacao pos-commit
  -> Disponibilizacao para o painel
```

Nenhuma sincronizacao pode retornar "OK" sem prova de persistencia.

#### Criticos obrigatorios

- status HTTP valido
- payload recebido
- concurso validado
- dezenas validadas
- upsert realizado
- SELECT pos-commit confirmado

### Regra 3 - Conferencia oficial

Toda conferencia deve usar exclusivamente concursos persistidos no PostgreSQL Institucional.

Fluxo correto:

```text
imported_contests
  -> generated_games
  -> reconciliation_runs
  -> reconciliation_games
  -> memoria HB
```

### Regra 4 - Memoria HB

A Memoria HB so pode aprender a partir de dados:

- oficiais
- conferidos
- persistidos
- auditaveis

Proibido aprendizado baseado em:

- simulacao nao validada
- payload temporario
- dados manuais sem validacao
- CSV nao institucionalizado

### Regra 5 - Painel ADM

O Painel ADM e o centro operacional da LotoIA.

Ele deve exibir sempre dados vindos do PostgreSQL Institucional.

Criterio obrigatorio:

```text
PostgreSQL = Auditoria Runtime = Painel ADM
```

Se houver divergencia, considerar incidente de governanca.

### Regra 6 - Auditoria Runtime

A Auditoria Runtime deve permanecer disponivel no Painel ADM.

Ela deve exibir:

- backend
- database_source
- host
- schema
- build ativo
- commit ativo
- contagem das tabelas institucionais
- ultimo concurso importado
- ultima sincronizacao
- status de queries
- erros SQL, se existirem

### Regra 7 - Historicos

Separacao obrigatoria:

#### Historico Analitico

Responde: "como os jogos performaram?"

Deve conter:

- dezenas dos jogos
- acertos
- premiacoes
- melhores jogos
- distribuicao de acertos
- score
- perfil HB
- cobertura
- entropia
- comparativos de desempenho

#### Historico Institucional

Responde: "o que aconteceu na plataforma?"

Deve conter:

- sincronizacoes
- importacoes
- geracoes
- conferencias
- auditorias
- eventos de governanca
- memoria HB
- futuras entregas WhatsApp
- tabelas institucionais

Tabelas Institucionais devem ficar somente no Historico Institucional.

### Regra 8 - Erros e incidentes

Qualquer divergencia entre banco, painel, auditoria ou historico deve ser tratada como incidente.

Todo incidente deve registrar:

- causa raiz
- modulo afetado
- tabela afetada
- correcao aplicada
- commit
- validacao final

### Regra 9 - Testes 15 a 23 dezenas

Testes entre 15 e 23 dezenas devem registrar:

- quantidade de dezenas
- quantidade de jogos
- parametros HB
- geracao
- conferencia
- acertos
- premiacao
- score
- memoria associada

### Regra 10 - WhatsApp

A futura integracao WhatsApp deve consumir apenas dados ja persistidos no PostgreSQL Institucional.

O WhatsApp sera canal de entrega, nao fonte da verdade.

## Gestao de Projetos (Fase 0)

Missões institucionais seguem a camada documental de Gestão de Projetos — controle de
escopo, agente responsável, evidência Git, testes, deploy e veredicto formal.

| Documento | Caminho |
|-----------|---------|
| Política | `docs/governance/POLITICA_GESTAO_PROJETOS_LOTOIA.md` |
| Quadro ativo | `docs/governance/gestao_projetos/QUADRO_MISSOES.md` |
| Checklist | `docs/governance/gestao_projetos/CHECKLIST_MISSAO_OBRIGATORIO.md` |

**Regra:** nenhuma missão encerra sem veredicto da matriz oficial e evidência Git quando
houver alteração de repositório. Ver incidente `institutional_light_mode` (2026-06-17).

## Checklist de conformidade

- [ ] O modulo le do PostgreSQL Institucional?
- [ ] O modulo evita CSV como fonte operacional?
- [ ] O modulo evita session_state como fonte de verdade?
- [ ] O modulo persiste antes de exibir sucesso?
- [ ] O modulo possui validacao pos-commit?
- [ ] O modulo aparece corretamente na Auditoria Runtime?
- [ ] O modulo respeita a separacao Analitico x Institucional?
- [ ] O modulo registra erros de forma auditavel?
- [ ] O modulo respeita a Lei No 001?

## Governanca de aceite

Nenhuma nova funcionalidade deve ser considerada concluida se violar a Lei No 001 ou esta Governanca Operacional.

## Criterio de aceite institucional

1. Codigo compila.
2. Dados persistem no PostgreSQL.
3. Auditoria Runtime confirma.
4. Painel exibe o mesmo valor.
5. Historico correto recebe o evento.
6. Nao ha fonte paralela de verdade.

