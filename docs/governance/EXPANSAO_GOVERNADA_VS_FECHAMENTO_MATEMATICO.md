# Governança de Geração: Expansão Científica vs. Fechamento Matemático

## 1. Definições Institucionais

### Expansão Científica Governada
- **Status:** APROVADO / OPERACIONAL (via `src/lotoia/combinatorics/`).
- **Definição:** Técnica de amostragem inteligente aplicada sobre um superconjunto de dezenas (ex: 16 a 20 dezenas).
- **Mecânica:** Gera combinações possíveis e aplica filtros da **Lei 15** e **Score ML** para selecionar os cartões com maior integridade estatística e probabilística.
- **Objetivo:** Aumentar a diversidade estrutural sem perder a governança de qualidade.
- **Garantia:** Não oferece garantia matemática de prêmio alvo (ex: 14 se 15). A soberania é da estatística probabilística.

### Fechamento Matemático (Wheeling)
- **Status:** NÃO IMPLEMENTADO / NÃO APROVADO.
- **Definição:** *Covering design* baseado em análise combinatória pura para garantir um prêmio alvo (t) dado que (m) dezenas sorteadas estejam dentro do conjunto (v).
- **Garantia:** Formal e matemática (ex: "18-15-14-15" garante 14 pontos se as 15 sorteadas estiverem entre as 18 escolhidas).
- **Restrição:** Não deve ser confundido com a geração atual da LotoIA. Qualquer implementação futura exige ADR dedicado e prova de cobertura.

### Fechamento Operacional (Cycle Closure)
- **Status:** MANTIDO / DESAMBIGUADO.
- **Definição:** Rotina de finalização de ciclo diário (logs, backups, sincronização de base oficial, reconciliação de memória).
- **Contexto:** Usado em `lotoia operational-lifecycle`. Não possui relação com geração de cartões ou combinatória.

## 2. Matriz de Soberania

| Camada | Motor | Objetivo | Governança |
| :--- | :--- | :--- | :--- |
| **Geração Soberana** | `Lei 15` | Cartões unitários de alta fidelidade | Governança strita |
| **Expansão** | `Scientific Expansion` | Lotes de alta diversidade baseada em Lei 15 | Governança assistida |
| **Fechamento** | `N/A` | Cobertura combinatória garantida | **Não permitido (vnext)** |

## 3. Diretrizes de Comunicação e Desenvolvimento

1. **Proibição de Promessas:** É expressamente proibido alegar "garantia de prêmio" ou usar o termo "fechamento" para descrever a Expansão Científica.
2. **Isolamento de Código:** O módulo `combinatorics` deve permanecer isolado. Ele consome a Lei 15 (via filtros), mas a Lei 15 (basic_generator) nunca deve consumir ou depender da lógica combinatória.
3. **Auditabilidade:** Toda expansão deve gerar um `expansion_event` com metadados claros de que se trata de uma amostragem governada, não um fechamento matemático.
