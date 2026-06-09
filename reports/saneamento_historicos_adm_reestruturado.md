# Saneamento dos Históricos do ADM Reestruturado

## Contexto

O Histórico Institucional estava caindo em erro de interface por aninhamento de `expanders` no Streamlit, enquanto o Histórico Analítico já havia sido reduzido para uma abertura leve com detalhes avançados recolhidos.

## Causa provável

- O bloco `Diagnóstico histórico` do Histórico Institucional chamava um painel científico que ainda abria payload técnico em `expander` interno.
- A página também expunha blocos legados de memória científica em formato operacional, sem separação clara entre rastreabilidade principal, memória pós-reconciliação e documentação histórica.

## Ajustes feitos

- O painel `Lei Científica da Geração` passou a aceitar `use_expander=False` para evitar aninhamento quando renderizado dentro do Histórico Institucional.
- O Histórico Institucional foi reorganizado em camadas textuais:
  - `Rastreabilidade institucional principal`
  - `Diagnóstico histórico observacional`
  - `Memória científica legada — quarentena documental`
- O bloco de memória legada foi recolhido por padrão e permanece apenas como documentação.
- O Histórico Analítico segue com a tabela extensa recolhida por padrão em `Jogos completos históricos conferíveis — detalhes avançados`.

## Limites aplicados

- Nenhuma lógica de geração, conferência ou simulação foi alterada.
- Lei 15, Lei 17 e Lei 18 permaneceram intactas.
- Banco de dados, endpoints, histórico salvo e estrutura das tabelas não foram modificados.

## Validação

Executado:

- `python -m py_compile dashboard/institutional_app.py`
- `python -m pytest tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py -q`

Resultado:

- `26 passed`
- 1 warning de cache do pytest por permissão no ambiente, sem impacto funcional.

## Confirmação final

- O erro de `expanders` aninhados foi tratado na renderização do Histórico Institucional.
- O conteúdo sensível ficou separado em quarentena documental.
- Nenhuma lógica funcional foi alterada.
