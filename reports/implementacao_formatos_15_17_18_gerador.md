# Implementação Controlada dos Formatos 15 / 17 / 18 no Gerador

## Contexto
A Lei 15 permanece como única camada de comando da geração.
A Lei 17 e a Lei 18 permanecem como camadas de validação pós-geração.

## Implementação
O gerador passou a expor o seletor `Formato do cartão` com as opções:
- `15 dezenas — Núcleo Lei 15`
- `17 dezenas — Lei 15 + 2 reservas auditadas`
- `18 dezenas — Lei 15 + 3 reservas auditadas`

O botão principal foi mantido como `Gerar com Lei 15`.

## Regras aplicadas
- Formato 15: exibe apenas o núcleo gerado pela Lei 15.
- Formato 17: preserva as 15 dezenas do núcleo e adiciona 2 reservas auditadas.
- Formato 18: preserva as 15 dezenas do núcleo e adiciona 3 reservas auditadas.
- Nenhuma dezena do núcleo foi removida ou substituída.
- As reservas auditadas são derivadas de uma camada compatível com a própria Lei 15, sem uso de calibrador legado.

## Exibição
Cada jogo passou a ser apresentado com separação explícita entre:
- Núcleo Lei 15
- Reservas auditadas
- Cartão final

## Validações pós-geração
- Lei 17: valida 12+ com busca contínua por 14 e 15.
- Lei 18: valida 13+ com busca contínua por 14 e 15.

## Limites institucionais
- A Lei 15 não foi alterada.
- A Lei 17 não foi transformada em gerador.
- A Lei 18 não foi transformada em gerador.
- Não houve recalibração.
- Não houve uso de fluxo legado.
- Não houve substituição da Lei 15.

## Conclusão
Os formatos 17 e 18 dezenas foram implementados como expansão auditada do núcleo de 15 dezenas da Lei 15, sem transformar a Lei 17 ou a Lei 18 em geradores, sem recalibração, sem uso de legado e sem substituição da Lei 15.

## STATUS INSTITUCIONAL CONSOLIDADO
A implementação 15/17/18 no gerador limpo foi publicada com sucesso.
A Lei 15 continua como única comandante da geração.
Os formatos 17 e 18 permanecem como expansão auditada do núcleo de 15 dezenas.
A Lei 17 e a Lei 18 seguem como validações pós-geração.
Nenhuma lógica institucional foi alterada.
Nenhum fluxo legado foi conectado.
Validação técnica concluída com 26 testes aprovados.
