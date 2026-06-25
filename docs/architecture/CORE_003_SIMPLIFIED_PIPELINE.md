# CORE_003 — Pipeline Simplificado de Geração Estrutural

## Visão Geral

O **CORE_003** é uma simplificação do CORE_002, consolidando 10 módulos em 4 camadas claras. Mantém toda a funcionalidade essencial com complexidade reduzida.

### Comparação: CORE_002 vs CORE_003

| Aspecto | CORE_002 (atual) | CORE_003 (proposto) |
|---------|------------------|---------------------|
| Camadas | 5 (L1-L5) | 4 (L1-L4) |
| Módulos | 10+ | 4 consolidados |
| Complexidade | Alta | Média |
| Configuração | Fragmentada | Centralizada |
| Presets | Nenhum | 3 (conservador, equilibrado, agressivo) |

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│  L1: Pool Generation                                        │
│  - Gera pool base de candidatos                            │
│  - Suporta formatos 15D-23D                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  L2: Structural Policy                                      │
│  - Políticas estruturais consolidadas                      │
│  - Triplet 01-02-03 (21%)                                  │
│  - Suffix 23-24-25 (21.67%)                                │
│  - Anti-viés de prefixo/sufixo                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  L3: Anti-Clone + Diversity                                 │
│  - Controle de overlap entre jogos                         │
│  - Diversidade por família (prefixo + sufixo)              │
│  - Relaxamento progressivo por tamanho de lote             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  L4: Critical Digits                                        │
│  - Reforço suave (07, 12, 23)                              │
│  - Penalização contextual (11, 15, 24, 25)                 │
│  - Nunca bloqueia completamente (15, 24, 25)               │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    GP FINAL COM MÉTRICAS
```

## Uso Básico

### Função Simplificada

```python
from lotoia.generation.core_003_pipeline import generate_core_003_games

# Gerar 50 jogos 15D com calibração equilibrada
games = generate_core_003_games(
    format="15D",
    count=50,
    calibration="equilibrado",
)

print(f"Jogos gerados: {len(games)}")
print(f"Primeiro jogo: {games[0]['numbers']}")
```

### Pipeline Completo

```python
from lotoia.generation.core_003_pipeline import Core003Pipeline

# Criar pipeline
pipeline = Core003Pipeline(
    format="15D",
    calibration="equilibrado",
)

# Gerar jogos
games = pipeline.generate(count=50, pool_size=150)

# Obter métricas
metrics = pipeline.get_metrics()
print(f"Triplet 01-02-03: {metrics['triplet_010203_pct']:.1%}")
print(f"Overlap médio: {metrics['avg_overlap']:.1f}")
print(f"Diversity score: {metrics['diversity_score']:.2f}")
```

## Presets de Calibração

### Conservador

- **Overlap máximo:** 11 (mais tolerante)
- **Diversity floor:** 0.75
- **Critical digit boost:** 2.0 (menor)
- **Pool multiplier:** 2.5x
- **Use case:** Quando quer mais jogos válidos, menos rigor

### Equilibrado (padrão)

- **Overlap máximo:** 10
- **Diversity floor:** 0.78
- **Critical digit boost:** 2.5
- **Pool multiplier:** 3.0x
- **Use case:** Balanceamento entre qualidade e quantidade

### Agressivo

- **Overlap máximo:** 9 (mais restritivo)
- **Diversity floor:** 0.80
- **Critical digit boost:** 3.0 (maior)
- **Pool multiplier:** 3.5x
- **Use case:** Máxima qualidade estrutural, menos jogos válidos

## Configuração Centralizada

Todas as configurações estão em `src/lotoia/config/core_003_config.py`:

```python
from lotoia.config.core_003_config import (
    CORE_003_CONFIG,
    get_calibration_preset,
    get_format_config,
    get_structural_policy,
    get_critical_digits,
)

# Obter preset de calibração
preset = get_calibration_preset("equilibrado")
print(f"Overlap máximo: {preset['max_overlap']}")

# Obter configuração de formato
format_config = get_format_config("15D")
print(f"Dezenas: {format_config['dezenas']}")

# Obter políticas estruturais
policy = get_structural_policy()
print(f"Triplet 01-02-03 freq: {policy['triplet_010203']['freq']}")

# Obter dezenas críticas
digits = get_critical_digits()
print(f"Reforço: {digits['reinforce']}")
```

## Métricas Estruturais

O pipeline calcula automaticamente:

| Métrica | Descrição | Target |
|---------|-----------|--------|
| `triplet_010203_pct` | % de jogos com 01-02-03 | 21% |
| `suffix_232425_pct` | % de jogos com 23-24-25 | 21.67% |
| `avg_overlap` | Overlap médio entre jogos | 10.0 |
| `diversity_score` | 1 - (overlap/game_size) | 0.78 |
| `validation` | Resultado da validação | válido |

### Validação Automática

```python
metrics = pipeline.get_metrics()
validation = metrics["validation"]

if validation["valid"]:
    print("Jogos válidos!")
else:
    print(f"Violações: {validation['violations']}")
    print(f"Avisos: {validation['warnings']}")
```

## Formatos Suportados

| Formato | Dezenas | Label |
|---------|---------|-------|
| 15D | 15 | `STRUCT_LEI15_CORE_CANDIDATE_003_15D_001` |
| 16D | 16 | `STRUCT_LEI15_CORE_CANDIDATE_003_16D_001` |
| 17D | 17 | `STRUCT_LEI15_CORE_CANDIDATE_003_17D_001` |
| 18D | 18 | `STRUCT_LEI15_CORE_CANDIDATE_003_18D_001` |
| 19D | 19 | `STRUCT_LEI15_CORE_CANDIDATE_003_19D_001` |
| 20D | 20 | `STRUCT_LEI15_CORE_CANDIDATE_003_20D_001` |
| 21D | 21 | `STRUCT_LEI15_CORE_CANDIDATE_003_21D_001` |
| 22D | 22 | `STRUCT_LEI15_CORE_CANDIDATE_003_22D_001` |
| 23D | 23 | `STRUCT_LEI15_CORE_CANDIDATE_003_23D_001` |

## Exemplos Avançados

### Geração com Pool Customizado

```python
games = generate_core_003_games(
    format="15D",
    count=50,
    pool_size=200,  # pool maior = mais diversidade
    calibration="equilibrado",
)
```

### Comparando Presets

```python
from lotoia.statistics.structural_metrics_validator import compute_structural_metrics

for preset in ["conservador", "equilibrado", "agressivo"]:
    games = generate_core_003_games(
        format="15D",
        count=50,
        calibration=preset,
    )
    metrics = compute_structural_metrics(games)
    print(f"{preset}: overlap={metrics['avg_overlap']:.1f}, "
          f"diversity={metrics['diversity_score']:.2f}")
```

### Validação Customizada

```python
from lotoia.statistics.structural_metrics_validator import (
    compute_structural_metrics,
    validate_structural_metrics,
)

games = generate_core_003_games(format="15D", count=50)
metrics = compute_structural_metrics(games)

# Validar com limites customizados
validation = validate_structural_metrics(
    metrics,
    limits={
        "triplet_010203_pct": {"min": 0.15, "max": 0.25},
        "avg_overlap": {"min": 8.0, "max": 11.0},
    }
)
```

## Migração do CORE_002

Se você está usando CORE_002, a migração é simples:

### Antes (CORE_002)

```python
from lotoia.generator.basic_generator import generate_best_games

result = generate_best_games(
    count=50,
    pool_size=150,
    batch_label="STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
)
games = result["games"]
```

### Depois (CORE_003)

```python
from lotoia.generation.core_003_pipeline import generate_core_003_games

games = generate_core_003_games(
    format="15D",
    count=50,
    calibration="equilibrado",
)
```

## Testes

```bash
# Executar todos os testes CORE_003
pytest tests/generation/test_core_003_pipeline.py -v

# Executar testes de configuração
pytest tests/generation/test_core_003_pipeline.py::TestCore003Config -v

# Executar testes de pipeline
pytest tests/generation/test_core_003_pipeline.py::TestCore003Pipeline -v
```

## Arquivos Principais

| Arquivo | Função |
|---------|--------|
| `src/lotoia/generation/core_003_pipeline.py` | Pipeline principal (4 camadas) |
| `src/lotoia/config/core_003_config.py` | Configuração centralizada |
| `tests/generation/test_core_003_pipeline.py` | Testes de integração |

## Status

- **Status:** Experimental (pronto para produção após validação)
- **Compatibilidade:** Retrocompatível com CORE_002
- **Performance:** Similar ao CORE_002
- **Cobertura de testes:** 19 testes passando

## Referências

- [CORE_002 Pipeline](CORE_002_SOVEREIGN_PIPELINE.md) — Pipeline original
- [Structural Policy Config](STRUCTURAL_POLICY_CONFIG.md) — Configuração centralizada
- [CHANGELOG](../../CHANGELOG.md) — Histórico de mudanças
