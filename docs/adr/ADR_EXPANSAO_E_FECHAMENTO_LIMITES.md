# ADR: Limites Técnicos e de Governança entre Expansão e Fechamento

## Status
APROVADO

## Contexto
O sistema LotoIA evoluiu para suportar a geração de jogos a partir de conjuntos expandidos de dezenas (16 a 20 dezenas). No entanto, o termo "fechamento" tem sido usado de forma ambígua, podendo sugerir garantias matemáticas de prêmio alvo que o sistema atual não possui. 

## Decisão
Fica estabelecido que:

1. **Separação de Conceitos:** O sistema atual utiliza **Expansão Científica Governada** (amostragem inteligente baseada em filtros de qualidade). O **Fechamento Matemático** (covering design com garantia formal) não está implementado nem aprovado para uso operacional.
2. **Soberania da Lei 15:** A geração soberana unitária (Lei 15) permanece como o motor primário da verdade. O motor de expansão (`scientific_expansion_engine`) é uma camada de conveniência que deve obrigatoriamente consumir as regras da Lei 15.
3. **Impedimento de Fusão:** O código de combinatória não deve ser promovido a motor principal. Ele deve atuar como um módulo de "Expansão de Carteira".
4. **Desambiguação do CLI:** O termo "fechamento" em comandos de CLI refere-se exclusivamente ao **Fechamento Operacional** (finalização de ciclo de dados e logs), não possuindo conotação combinatória.

## Consequências
- Fica proibida qualquer alegação de "garantia de prêmio" no sistema ou documentação.
- Novos módulos que visem implementar garantias matemáticas devem ser criados sob um novo namespace e exigem prova formal de cobertura e novo ADR.
- A rastreabilidade de descarte (`record_discarded_game`) deve ser mantida para garantir que a expansão não ignore os critérios de qualidade institucionais.
