# ADR-037 — Auditoria da Faixa 11+ e Compressão Estrutural do Motor

## Status
Accepted

## Contexto

Executamos benchmark real do motor LotoIA contra:
- pure random
- filtered random baseline

Janela:
- últimos 30 concursos
- 15 jogos
- pool 30
- janela histórica 200

Problema observado:
o motor não demonstrou vantagem consistente na faixa 11+.

## Evidências

### Pool inicial

Métricas:
- 30 candidatos únicos
- entropia: 4.9069
- overlap médio: 10.1839

Dezenas dominantes:
- 5 = 27 ocorrências
- 4 = 25
- 7 = 25
- 24 = 25
- 2 = 24
- 3 = 24
- 9 = 23
- 23 = 23
- 25 = 23
- 1 = 22

Conclusão:
o candidate space nasce comprimido e excessivamente centrado.

### Rerank

Resultado:
desligar ML rerank não altera significativamente o lote.

Conclusão:
o rerank não é o principal causador da compressão.

### Seleção final

Métricas:
- entropia cai de 4.9069 para 3.9069
- overlap médio final: 10.1333

Dezenas dominantes finais:
- 5 e 20 = 14 ocorrências
- 4, 7, 24 = 13
- 9, 14, 23 = 12

Conclusão:
a composição final reduz ainda mais a diversidade efetiva.

## Benchmark Comparativo

| Estratégia | Média | 11+ | 12+ | Máximo |
|---|---|---|---|---|
| lotoia_engine | 9.0489 | 10.44% | 2.44% | 13 |
| filtered_random | 9.1533 | 13.56% | 2.44% | 13 |
| pure_random | 9.0311 | 8.67% | 1.56% | 13 |

Diferenças:
- vs filtered_random: -0.1044
- vs pure_random: +0.0178

## Conclusão Técnica

A perda de desempenho da faixa 11+ ocorre principalmente:
1. na geração do pool inicial
2. na composição final do lote

O sistema apresenta:
- compressão estrutural
- overlap excessivo
- baixa exploração do espaço combinatório
- convergência para dezenas dominantes

O problema NÃO parece estar em:
- rerank ML
- output gate
- UI
- renderização
- persistência

## Impacto Institucional

Estado atual:
- motor coerente
- estabilidade razoável
- leve superioridade ao pure random
- abaixo do baseline filtrado

Diagnóstico:
o sistema privilegia estabilidade em detrimento de exploração estatística.

## Próximos Passos

Auditorias futuras devem focar:
- expansão controlada do candidate space
- redução de overlap estrutural
- aumento de entropia efetiva
- diversidade matemática real entre jogos
- calibração exploração vs estabilidade

Proibido:
- alterar benchmark histórico
- mascarar métricas
- validar performance sem comparação baseline
- alterar scoring sem nova auditoria

## Decisão

O projeto entra oficialmente em fase de:
“auditoria estrutural de diversidade combinatória”.


## Experimento Experimental de Pluralidade Operacional

Foi executada uma simulacao controlada no pacote premium 18 dezenas para avaliar o impacto da pluralidade operacional top-N.

Resultado observado em amostra curta (10 concursos, janela historica 200):
- top-1 preserva a politica atual e limita a saida a 1 aposta operacional
- top-3, top-5 e top-10 aumentam a frequencia de 11+
- o aumento de cobertura veio acompanhado de elevacao do overlap medio

Leitura institucional:
- a restricao top-1 estrangula a exploracao
- o aumento de volume melhora recall estatistico
- o ganho nao vem acompanhado de dispersao matematica proporcional

Conclusao parcial:
- pluralidade operacional e um gargalo real
- pluralidade sem distancia estrutural nao resolve a compressao do candidate space
