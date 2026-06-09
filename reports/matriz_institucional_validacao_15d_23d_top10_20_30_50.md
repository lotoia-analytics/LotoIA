# Matriz Institucional de Validação 15D-23D por Escalas Top 10/20/30/50

## 1. Resumo executivo

Esta missão registra a matriz institucional correta da LotoIA, separando com rigor dois eixos que não podem ser misturados:

- **D** = quantidade de dezenas por jogo.
- **Top** = quantidade de jogos por camada.

Assim, `15D Top 10` significa **10 jogos com 15 dezenas** cada; `20D Top 20` significa **20 jogos com 20 dezenas** cada. Nesta etapa, a matriz é apenas **documental e governamental**, sem nova geração, sem alteração da Lei 15 e sem publicação no `origin/main`.

## 2. Objetivo da matriz

Formalizar a arquitetura de validação da LotoIA como uma matriz bidimensional:

- eixo vertical: escalas de quantidade de jogos;
- eixo horizontal: formatos de dezenas por jogo.

A matriz existe para orientar leitura, governança e validação observacional, sem converter escala em formato nem formato em escala.

## 3. Regra de interpretação

Regra obrigatória:

- `D` sempre significa **quantidade de dezenas por jogo**.
- `Top` sempre significa **quantidade de jogos selecionados**.

Exemplos oficiais:

- `20D` = jogo com 20 dezenas.
- `Top 20` = 20 jogos.
- `20D Top 20` = 20 jogos com 20 dezenas cada.

## 4. Diferença entre formato e escala

### Formato

O formato descreve o tamanho de cada jogo:

- 15D
- 16D
- 17D
- 18D
- 19D
- 20D
- 21D
- 22D
- 23D

### Escala

A escala descreve quantos jogos compõem a camada:

- Top 10
- Top 20
- Top 30
- Top 50

### Proibição conceitual

- É proibido chamar `Top 20` de `20D`.
- É proibido chamar `Top 10` de `10D`.
- É proibido tratar `20D` como `20 jogos`.
- É proibido tratar `15D Top 20` como jogo de 20 dezenas.

## 5. Matriz completa 15D-23D x Top 10/20/30/50

### Top 10

- 15D Top 10
- 16D Top 10
- 17D Top 10
- 18D Top 10
- 19D Top 10
- 20D Top 10
- 21D Top 10
- 22D Top 10
- 23D Top 10

### Top 20

- 15D Top 20
- 16D Top 20
- 17D Top 20
- 18D Top 20
- 19D Top 20
- 20D Top 20
- 21D Top 20
- 22D Top 20
- 23D Top 20

### Top 30

- 15D Top 30
- 16D Top 30
- 17D Top 30
- 18D Top 30
- 19D Top 30
- 20D Top 30
- 21D Top 30
- 22D Top 30
- 23D Top 30

### Top 50

- 15D Top 50
- 16D Top 50
- 17D Top 50
- 18D Top 50
- 19D Top 50
- 20D Top 50
- 21D Top 50
- 22D Top 50
- 23D Top 50

## 6. Exemplos oficiais

- `15D Top 10` = 10 jogos com 15 dezenas.
- `16D Top 10` = 10 jogos com 16 dezenas.
- `17D Top 20` = 20 jogos com 17 dezenas.
- `23D Top 50` = 50 jogos com 23 dezenas.

Esses exemplos deixam claro que a matriz combina formato por jogo com escala por camada.

## 7. Estado atual da matriz

Estado institucional conhecido nesta sessão:

- `15D Top 20` foi validado como base observacional provisória.
- `15D Top 10` foi reaberto como subcamada candidata observacional, não operacional.
- `15D Top 30` ainda não consolidado.
- `15D Top 50` ainda não consolidado.
- `16D-23D` ainda não iniciados nesta matriz.

Observação obrigatória:

Se campos como `reservas_auditadas` e `cartao_final` aparecerem por herança técnica do sistema, eles devem ser lidos apenas como herança estrutural do runtime legado. Nesta missão, eles **não significam** formato `20D` nem expansão de dezenas. O objeto auditado continua sendo **jogo 15D**.

## 8. Sequências possíveis de trabalho

A sequência institucional recomendada não deve misturar dimensões.

### Por escala

1. Primeiro trabalhar `Top 10` de `15D` até `23D`.
2. Depois `Top 20` de `15D` até `23D`.
3. Depois `Top 30` de `15D` até `23D`.
4. Depois `Top 50` de `15D` até `23D`.

### Por formato

Se houver decisão institucional futura, também será possível trabalhar:

- `15D Top 10/20/30/50`
- depois `16D Top 10/20/30/50`
- e assim por diante.

Em qualquer cenário, a matriz deve ser preservada e a leitura de formato nunca pode ser confundida com a leitura de escala.

## 9. Proibições de governança

- É proibido chamar `Top 20` de `20D`.
- É proibido tratar `20D` como `20 jogos`.
- É proibido tratar `15D Top 20` como jogo de 20 dezenas.
- É proibido avançar para `16D` sem declarar qual célula da matriz está sendo trabalhada.
- É proibido promover qualquer célula para operacional sem relatório próprio.
- É proibido alterar a Lei 15 por causa da matriz.
- É proibido publicar no `origin/main` nesta missão.
- É proibido gerar nova bateria.
- É proibido recalibrar a Lei 15.

## 10. Relação com a Lei 15

A Lei 15 permanece soberana e inalterada.

Esta matriz não altera:

- núcleo da Lei 15;
- geração operacional;
- conferência operacional;
- persistência;
- schema;
- RFE;
- OutputCommander.

A matriz apenas organiza a leitura institucional de formatos e escalas.

## 11. Relação com a expansão 16D-23D

O espaço `16D-23D` existe como coluna futura da matriz, mas ainda não foi iniciado operacionalmente nesta etapa.

Portanto:

- não houve início de `16D`;
- não houve ativação da expansão;
- não houve mudança de regra;
- não houve nova geração;
- não houve push.

## 12. Confirmações finais

- Não houve nova geração.
- Não houve push.
- A Lei 15 não foi alterada.
- `15D` continua em validação observacional.
- `16D-23D` ainda não foram iniciados nesta matriz.
- `Top 10`, `Top 20`, `Top 30` e `Top 50` são escalas de quantidade de jogos.
- `15D-23D` são formatos de quantidade de dezenas por jogo.

## 13. Conclusão institucional

A LotoIA deve interpretar a sua matriz de governança desta forma:

- **formato** = dezenas por jogo;
- **escala** = quantidade de jogos;
- **Lei 15** = soberana, preservada;
- **Top** = camada de quantidade;
- **D** = tamanho do jogo.

Essa distinção evita erros conceituais, mantém a rastreabilidade institucional e prepara a futura validação por célula da matriz sem comprometer a arquitetura vigente.
