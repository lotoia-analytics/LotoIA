# Correção de `batch_reconciliation_memory` no Histórico Institucional

## Erro encontrado

A página `Histórico Institucional` podia quebrar ao renderizar a memória consolidada da bateria conferida quando `batch_reconciliation_memory` não era inicializada em todos os cenários.

## Função afetada

- `_render_scientific_memory_block()`

## Linha aproximada

- bloco em torno da montagem da memória consolidada da bateria conferida

## Causa raiz

- variável opcional sem inicialização segura antes do `if batch_reconciliation_memory:`

## Fallback aplicado

- inicialização defensiva no início da função:
  - `batch_reconciliation_memory: dict[str, Any] = {}`
- mensagem institucional quando não houver memória em lote disponível:
  - `Memória de reconciliação em lote indisponível ou ainda não registrada para esta sessão.`

## Confirmação visual

- a página `Histórico Institucional` passa a abrir sem exceção
- o bloco de memória científica permanece renderizável
- quando não houver memória em lote, a tela exibe mensagem institucional em vez de quebrar

## Confirmações institucionais

- Lei 15 não foi alterada
- Lei 16 não foi alterada
- nenhuma recalibração foi executada
- nenhuma lógica operacional foi alterada

## Testes executados

- `python -m py_compile dashboard/institutional_app.py`
- `python -m pytest tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py -q`
- `python -m pytest tests/test_global_batch_deduplication.py -q`

## Resultado dos testes

- compilação: OK
- pytest núcleo: OK
- pytest deduplicação global: OK

## Commit

- a ser preenchido após publicação
