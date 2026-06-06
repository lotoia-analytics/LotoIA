# Remoção de `batch_id` / `clean-law15-*` da memória consolidada e dos blocos visuais

## Objetivo

Substituir o rótulo visual de origem da geração por `generation_event_id` e remover `clean-law15-*` dos blocos visuais de memória consolidada, sem alterar a lógica funcional.

## O que foi ajustado

- `ID da geração de origem` foi trocado para `generation_event_id` nos blocos de memória consolidada.
- O bloco de memória pós-conferência passou a exibir `generation_event_id` como referência visual.
- O bloco de resumo da geração passou a exibir `generation_event_id` em vez de `batch_id`.
- A captura visual da memória consolidada deixou de exibir `batch_id` como eixo de leitura principal.

## O que não foi alterado

- Lei 15
- Lei 16
- RFE estrutural
- OutputCommander
- geração de cartões
- fonte oficial de concursos
- persistência
- schema

## Validação

O ajuste preserva `batch_id` apenas como identificador técnico interno, sem exibição como comando operacional.

## Conclusão institucional

A interface passa a privilegiar `generation_event_id` como identificador visual da origem da geração, sem expor `clean-law15-*` nos blocos de memória consolidada.
