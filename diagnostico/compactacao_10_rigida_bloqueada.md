# Compactação 10 Rígida - Bloqueada em 10 Acertos

Diagnóstico registrado para a bateria compacta de 10 jogos da política 15 vNext.

## Resumo

- Bateria: `calibration-20260602202146-5c170e66`
- Concurso de conferência: `3700`
- Melhor acerto: `10`
- Distribuição: `5x 10 acertos`, `4x 8 acertos`, `1x 7 acertos`, `0x 9 acertos`
- Status científico: `FAILED_MINIMUM_11_PLUS`
- Tipo de falha: `RIGID_BIMODAL_COMPACTATION`
- Baseline preservada: `VALIDATED_15_POLICY_LEVEL_3`

## Leitura

- A compactação de 10 jogos foi rígida e bimodal.
- O piso de `11+` não foi atingido nesta amostra compacta.
- O comportamento não rebaixa a baseline 15; o problema está na rigidez operacional da compactação pequena.

## Padrões observados

- Faltas críticas no concurso `3700`:
  - `17` faltou em `10/10`
  - `23` faltou em `9/10`
  - `25` faltou em `7/10`
- Repetição excessiva:
  - `2` apareceu em `10/10`
  - `14` apareceu em `10/10`
  - `24` apareceu em `9/10`
  - `5` apareceu em `9/10`
  - `21` apareceu em `8/10`

## Ajuste operacional proposto

- Manter a baseline oficial 15 intacta.
- Criar ajuste operacional apenas para compactações pequenas.
- Reduzir rigidez do núcleo em lotes de `10/20` jogos.
- Promover diversidade controlada.
- Promover `17` e `23` de forma operacional.
- Controlar repetição de `2`, `5`, `21` e `24`.
- Não transformar esse ajuste em regra fixa permanente.

## Próximo teste

- Gerar `20` jogos novos de `15` dezenas com o ajuste operacional de compactação pequena.
- Conferir contra o concurso `3700` para comparação limpa.
