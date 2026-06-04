# Correção de Roteamento dos Históricos do ADM

## Causa identificada
- Divergência entre rótulos exibidos na sidebar e chaves internas do roteador, especialmente com variações de acento.
- A página histórica podia cair no fallback por não bater exatamente com a chave esperada.
- Em algumas sessões, a carga leve podia chegar vazia antes do recarregamento controlado, criando uma impressão de página indisponível.
- A navegação estava dependendo do texto do botão em vez do `page_id` explícito, abrindo espaço para mapeamento incorreto.

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

## Chaves corrigidas
- `Histórico Analítico` e `Historico Analitico` agora apontam para `history_analytical`.
- `Histórico Institucional` e `Historico Institucional` agora apontam para `history_institutional`.
- O roteador passou a comparar rótulos com normalização Unicode, reduzindo divergência por acento.
- A sidebar passou a enviar `page_id` explícito para as páginas de histórico.

## Validação dos históricos
- `Histórico Analítico` continua acessível.
- `Histórico Institucional` continua acessível.
- Ambas as rotas renderizam suas próprias telas.
- O fallback seguro continua ativo para rotas desconhecidas.
- Se a amostra leve vier vazia, a página tenta recarregamento controlado antes de exibir estado vazio.

## Confirmação do Gerador
- O Gerador não é mais fallback para histórico ou rota desconhecida.
- O Gerador continua acessível apenas pelo núcleo operacional.

## Testes executados
- `python -m py_compile dashboard/institutional_app.py`
- `python -m pytest tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py -q`

## Confirmação funcional
- Nenhuma lógica funcional foi alterada.
- A correção foi apenas de roteamento/renderização.
