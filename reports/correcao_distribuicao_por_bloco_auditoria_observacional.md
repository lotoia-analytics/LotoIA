# Correção da Distribuição por Bloco na Auditoria Observacional

## Tela ajustada

- `Auditoria e Monitoramento` → `Conferência por Concurso`

## Função/bloco alterado

- Bloco de renderização da subpágina `conference` em `dashboard/institutional_app.py`
- Novo cálculo observacional baseado nas dezenas oficiais do concurso monitorado

## Fonte das dezenas oficiais

- Tabela oficial usada pelo ADM local: `lotofacil_official_history`
- Leitura feita via helper oficial de histórico do painel

## Concurso usado na validação

- Concurso `3702`

## Distribuição calculada

- `01–05: 3`  
- `06–10: 1`  
- `11–15: 3`  
- `16–20: 4`  
- `21–25: 4`

## Motivo anterior da indisponibilidade

- A tela estava lendo a distribuição a partir de `POST_DRAW_MONITORING_PAYLOAD`
- Quando o payload não carregava `block_distribution`, a interface mostrava `Distribuição indisponível`
- Agora a distribuição é calculada diretamente a partir das dezenas oficiais do concurso monitorado

## Confirmação institucional

- Nenhuma lógica de geração foi alterada
- Nenhuma recalibração foi adicionada
- Lei 15, Lei 17 e Lei 18 permanecem intactas
- A correção é apenas observacional e de exibição

## Testes executados

- `python -m py_compile dashboard/institutional_app.py`
- `python -m pytest tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py -q`

Resultado:

- `26 passed`
