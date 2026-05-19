# Divisoes Temporais

## Politica Oficial

O LotoIA usa divisao temporal como criterio cientifico obrigatorio. A validacao
supervisionada futura deve seguir walk-forward validation, com treino sempre anterior ao
teste.

```text
train_start <= train_end < test_start <= test_end
```

## Walk-Forward Baseline

A estrutura minima adotada e de janela de treino expansiva:

1. treina-se conceitualmente com concursos historicos ate `train_end`;
2. testa-se na janela imediatamente posterior;
3. avanca-se o corte temporal;
4. repete-se mantendo rastreabilidade do split.

Esta etapa cria apenas a definicao e validacao dos splits. Nenhum modelo e treinado.

## Artefatos Relacionados

- `src/lotoia/experiments/temporal_governance.py`
- `experiments/registry/README.md`
- `docs/governance/ANTI_LEAKAGE.md`
- `reports/TEMPORAL_GOVERNANCE_REPORT.md`
