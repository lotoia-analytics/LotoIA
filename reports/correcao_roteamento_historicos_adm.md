# Correção de Roteamento dos Históricos do ADM

## Causa identificada
- Rota não reconhecida e fallback de navegação podiam acabar retornando para a tela de geração.
- Isso fazia o Gerador reaparecer fora do núcleo operacional.

## Rotas afetadas
- `history_analytical`
- `history_institutional`
- fallback/default de páginas não reconhecidas

## Fallback anterior
- Rota desconhecida ou não resolvida podia cair no comportamento padrão da interface, que expunha a geração.

## Fallback corrigido
- Página inicial leve permanece em `home`.
- Rota desconhecida agora cai em uma página leve de fallback.
- Nenhuma rota de histórico pode cair no Gerador.

## Validação dos históricos
- `Histórico Analítico` continua acessível.
- `Histórico Institucional` continua acessível.
- Ambas as rotas renderizam suas próprias telas.

## Confirmação do Gerador
- O Gerador não é mais fallback para histórico ou rota desconhecida.
- O Gerador continua acessível apenas pelo núcleo operacional.

## Testes executados
- `python -m py_compile dashboard/institutional_app.py`
- `python -m pytest tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py -q`

## Confirmação funcional
- Nenhuma lógica funcional foi alterada.
- A correção foi apenas de roteamento/renderização.

