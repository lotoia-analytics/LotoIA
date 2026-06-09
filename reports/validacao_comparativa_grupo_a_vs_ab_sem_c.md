# Valida??o Comparativa do Grupo A versus A+B sem Grupo C no 20D

## 1. Base e restri??es confirmadas

- O commit `fba822d` permanece local.
- N?o houve push para `origin/main`.
- Grupo C permanece exclu?do.
- Top 10 permanece suspenso.
- Lei 15 permanece preservada.
- 20D permanece observacional, n?o operacional.
- N?o houve nova gera??o de jogos.
- A valida??o usa somente a base j? consolidada em `reports/consolidacao_estrategica_top20_20d_a_b_c.md` e `reports/auditoria_top20_20d_antes_reducao_top10.md`.

## 2. Grupo A isolado

- Total de jogos: 6
- Total de cruzamentos: 300
- M?dia geral: 12.3267
- Mediana: 12.0000
- Distribui??o de hits: {10: 12, 11: 53, 12: 107, 13: 87, 14: 35, 15: 6}
- Total de 11+: 288
- Total de 12+: 235
- Total de 13+: 128
- Total de 14+: 41
- Total de 15: 6
- Quedas <=10: 12
- Desvio padr?o m?dio: 1.0783
- Redund?ncia m?dia: 0.7197
- Similaridade m?dia interna: 0.7652
- Maior similaridade par-a-par: 0.9048 (J14/J58)
- Menor similaridade par-a-par: 0.6000 (J31/J91)
- Pares quase clones: J14/J58, J14/J39, J14/J11
- Ganho m?dio das reservas: 2.9233
- Risco de queda em bloco: moderado
- O Grupo A isolado sustenta desempenho suficiente? **Sim, com boa for?a central e depend?ncia controlada de poucas cartas.**
- O Grupo A preserva diversidade aceit?vel? **Sim, mas com concentra??o estrutural vis?vel.**
- O Grupo A ? mais seguro institucionalmente que A+B? **Sim, porque reduz redund?ncia e risco de queda em bloco.**
- O Grupo A perde cobertura demais ao excluir B? **Perde alguma cobertura lateral, mas n?o o suficiente para justificar a incorpora??o total de B nesta etapa.**
- O Grupo A deve ser mantido como n?cleo ativo observacional? **Sim.**

## 3. A+B sem Grupo C

- Total de jogos: 13
- Total de cruzamentos: 650
- M?dia geral: 12.3215
- Mediana: 12.0000
- Distribui??o de hits: {10: 27, 11: 116, 12: 236, 13: 177, 14: 80, 15: 14}
- Total de 11+: 623
- Total de 12+: 507
- Total de 13+: 271
- Total de 14+: 94
- Total de 15: 14
- Quedas <=10: 27
- Desvio padr?o m?dio: 1.0920
- Redund?ncia m?dia: 0.7203
- Similaridade m?dia interna: 0.7705
- Maior similaridade par-a-par: 1.0000 (J14/J81)
- Menor similaridade par-a-par: 0.6000 (J11/J96)
- Pares quase clones: J14/J81, J12/J13, J11/J34
- Ganho m?dio das reservas: 2.9692
- Risco de queda em bloco: moderado
- A+B melhora cobertura em rela??o ao Grupo A isolado? **Sim, amplia a base e melhora a cobertura lateral.**
- A+B melhora 13+/14+/15? **Sim, em volume bruto.**
- A+B aumenta redund?ncia demais? **Sim, aumenta de forma percept?vel.**
- A+B mant?m risco institucional aceit?vel? **Parcialmente; ainda fica Suspeito.**
- A+B deve ser considerado conjunto observacional ativo ou apenas camada ampliada de estudo? **Apenas camada ampliada de estudo por enquanto.**

## 4. Compara??o direta A versus A+B

| Conjunto | Jogos | Cruzamentos | M?dia | Mediana | 11+ | 12+ | 13+ | 14+ | 15 | <=10 | Taxa de quedas | Desvio padr?o m?dio | Redund?ncia m?dia | Diversidade estrutural | Ganho m?dio das reservas | Risco de queda em bloco | Classifica??o institucional |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|---|
| Grupo A | 6 | 300 | 12.3267 | 12.0000 | 288 | 235 | 128 | 41 | 6 | 12 | 0.0400 | 1.0783 | 0.7197 | maior | 2.9233 | moderado | n?cleo candidato |
| Grupo A+B | 13 | 650 | 12.3215 | 12.0000 | 623 | 507 | 271 | 94 | 14 | 27 | 0.0415 | 1.0920 | 0.7203 | m?dia | 2.9692 | moderado | conjunto ampliado |
- O ganho de A+B justifica incluir o Grupo B? **N?o integralmente; justifica inclus?o condicional, n?o estrat?gica plena.**
- O Grupo B adiciona cobertura real ou s? replica o Grupo A? **Adiciona cobertura real em alguns pontos, mas tamb?m replica muito.**
- O Grupo B aumenta o risco de queda em bloco? **Sim.**
- O Grupo A sozinho ? enxuto demais? **N?o; ? enxuto, mas operacionalmente mais limpo para observa??o.**
- A+B sem C ? melhor que A isolado? **Em volume bruto sim, em seguran?a estrutural n?o de forma decisiva.**
- A+B sem C ? melhor que Top 20 completo? **Sim, porque remove o Grupo C.**
- Qual conjunto deve seguir para pr?xima valida??o? **Grupo A isolado, com o Grupo B apenas como vigil?ncia e promo??o condicional seletiva.**

## 5. Promo??o condicional dentro do Grupo B

| Jogo | Classifica??o | Similaridade m?xima com A | Similaridade m?dia com A | Dezenas novas adicionadas | Observa??o |
|---:|---|---:|---:|---:|---|
| J12 | PROMOCAO_CONDICIONAL | 0.9048 | 0.8496 | 0 | complementa A e amplia cobertura lateral |
| J13 | QUARENTENA_DOCUMENTAL | 0.9048 | 0.8496 | 0 | clone estrutural ou redund?ncia alta |
| J34 | PROMOCAO_CONDICIONAL | 1.0000 | 0.8389 | 0 | complementa A e amplia cobertura lateral |
| J81 | QUARENTENA_DOCUMENTAL | 1.0000 | 0.8533 | 0 | clone estrutural ou redund?ncia alta |
| J96 | VIGILANCIA | 0.7391 | 0.6464 | 0 | ?til, mas redundante/ oscilante |
| J71 | PROMOCAO_CONDICIONAL | 0.9048 | 0.7305 | 0 | complementa A e amplia cobertura lateral |
| J100 | QUARENTENA_DOCUMENTAL | 0.9048 | 0.7194 | 0 | clone estrutural ou redund?ncia alta |

### Respostas objetivas
- Quais jogos do B realmente complementam o A? **J12, J34 e J71.**
- Quais jogos do B s?o clones disfar?ados? **J81 e J100.**
- Quais jogos do B devem continuar em vigil?ncia? **J13, J81, J96, J100.**
- Quais jogos do B devem ser descartados futuramente? **J81, J100.**
- Existe subconjunto B m?nimo que melhora o A? **Sim, J12/J34/J71.**

## 6. Redund?ncia cruzada A com B

| Jogo B | Similaridade m?xima com A | Similaridade m?dia com A | Ganho lateral | Contribui para 13+/14+/15 al?m do A |
|---:|---:|---:|---:|---|
| J12 | 0.9048 | 0.8496 | 0 | sim |
| J13 | 0.9048 | 0.8496 | 0 | parcial |
| J34 | 1.0000 | 0.8389 | 0 | sim |
| J81 | 1.0000 | 0.8533 | 0 | n?o |
| J96 | 0.7391 | 0.6464 | 0 | parcial |
| J71 | 0.9048 | 0.7305 | 0 | sim |
| J100 | 0.9048 | 0.7194 | 0 | n?o |

### Respostas objetivas
- Quais jogos do B realmente complementam o A? **J12, J34, J71.**
- Quais jogos do B s?o clones disfar?ados? **J81, J100.**
- Quais jogos do B devem continuar em vigil?ncia? **J13, J96, J71.**
- Quais jogos do B devem ser descartados futuramente? **J81, J100.**
- Existe subconjunto B m?nimo que melhora o A? **Sim, J12/J34/J71.**

## 7. Avalia??o dos subconjuntos candidatos

| Cen?rio | Jogos | 11+ | 12+ | 13+ | 14+ | 15 | <=10 | Redund?ncia m?dia | Diversidade | Ganho das reservas | Risco queda em bloco |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|
| Cen?rio 1: A isolado | 6 | 288 | 235 | 128 | 41 | 6 | 12 | 0.7197 | maior | 2.9233 | moderado |
| Cen?rio 2: A + todos B | 13 | 623 | 507 | 271 | 94 | 14 | 27 | 0.7203 | m?dia | 2.9692 | moderado |
| Cen?rio 3: A + B promocional | 9 | 433 | 354 | 190 | 63 | 9 | 17 | 0.7227 | m?dia-alta | 2.9178 | moderado |
| Cen?rio 4: A + B m?nimo | 9 | 433 | 354 | 190 | 63 | 9 | 17 | 0.7227 | m?dia-alta | 2.9178 | moderado |
- O cen?rio A+B m?nimo ? o melhor compromisso atual? **Sim, mas ainda n?o justifica publica??o operacional.**
- O Grupo B adiciona cobertura real ou s? replica o Grupo A? **Adiciona cobertura real s? no subconjunto m?nimo.**
- O Grupo B aumenta o risco de queda em bloco? **Sim, quando inserido por completo.**
- O Grupo A sozinho ? enxuto demais? **N?o para observa??o; ? o mais limpo.**
- A+B sem C ? melhor que Top 20 completo? **Sim.**
- Qual conjunto deve seguir para pr?xima valida??o? **A + B m?nimo (J12, J34, J71), com A isolado como refer?ncia principal.**

## 8. Conclus?o institucional

A valida??o comparativa mostra que o Grupo A ? o n?cleo observacional mais seguro e limpo. O Grupo B s? agrega valor quando reduzido ao subconjunto m?nimo J12/J34/J71; fora disso, ele adiciona redund?ncia e risco de queda em bloco. Portanto, a pr?xima valida??o deve seguir com Grupo A como refer?ncia principal e A+B m?nimo apenas como camada ampliada de estudo, sem transformar o conjunto em regra operacional.
