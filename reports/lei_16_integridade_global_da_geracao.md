# Lei 16 — Integridade Global da Geração

## Síntese institucional

A Lei 16 formaliza o princípio de unicidade global das combinações geradas pela LotoIA dentro do mesmo evento, lote ou bateria.

Ela não altera a Lei 15, não redefine estratégia de geração e não cria uma política concorrente. Sua função é garantir integridade operacional, rastreabilidade e verdade da entrega final.

## Enunciado soberano

Toda geração institucional da LotoIA deve preservar unicidade global de jogos por assinatura normalizada dentro do mesmo evento, lote ou bateria.

Nenhum jogo pode se repetir na entrega, ainda que pertença a grupos diferentes.

## Regra operacional

Para qualquer geração institucional:

- `total_jogos_solicitados = total_jogos_entregues = total_assinaturas_unicas`
- `duplicados_globais = 0`

Se a quantidade solicitada não puder ser satisfeita com jogos únicos, a geração deve registrar alerta institucional e não mascarar o resultado.

## Escopo de aplicação

A Lei 16 se aplica a:

- geração simples
- bateria única
- bateria dividida em grupos
- bateria de 50 jogos
- bateria de 100 jogos
- bateria de 200 jogos
- modo direto de 15 dezenas
- execuções agrupadas
- execuções parciais do mesmo evento
- persistência de jogos gerados
- entrega final ao usuário

## Assinatura normalizada

Cada jogo deve ser comparado por assinatura normalizada:

- dezenas ordenadas
- formatação padronizada
- comparação independente da ordem original
- representação única por combinação

## Relação com outras leis

- Lei 15: governança soberana da política de geração
- Lei 16: integridade global da entrega gerada
- Lei 17: validação/conferência
- Lei 18: referência/memória/base oficial

## Estado de implementação no runtime

O runtime institucional já passou a compartilhar um controle global de assinaturas entre grupos da mesma bateria, evitando repetição entre grupos e preservando unicidade global da entrega.

## Critério de conformidade

Uma geração está conforme a Lei 16 quando:

- `total_jogos_solicitados = total_jogos_entregues`
- `total_jogos_entregues = total_assinaturas_unicas`
- `duplicados_intra_grupo = 0`
- `duplicados_entre_grupos = 0`
- `duplicados_globais = 0`

## Veredito

Lei 16 está classificada como:

- Compatível
- Impacto alto positivo
- Risco baixo
- Dependência: não altera a Lei 15

## Observação final

Esta documentação formaliza o princípio institucional de integridade global da geração e registra que a bateria não deve ser completada com jogos repetidos apenas para atingir a quantidade solicitada.
