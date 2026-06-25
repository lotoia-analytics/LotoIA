# Fase 1: Intervalos de Confiança nas Políticas Estruturais

## Visão Geral

A Fase 1 substitui valores fixos por intervalos com confiança estatística, permitindo ao sistema distinguir variações reais de ruído estatístico.

## O que foi implementado

### 1. Módulo de Cálculo de Intervalos de Confiança

**Arquivo:** `src/lotoia/statistics/confidence_interval_calculator.py`

#### Classes e Funções

```python
from lotoia.statistics.confidence_interval_calculator import (
    ConfidenceInterval,
    ConfidenceIntervalCalculator,
    calculate_proportion_ci,
    calculate_mean_ci,
    compare_proportions,
)
```

#### ConfidenceInterval

Dataclass que representa um intervalo de confiança:

```python
@dataclass
class ConfidenceInterval:
    value: float              # Valor pontual (proporção ou média)
    lower_bound: float        # Limite inferior do intervalo
    upper_bound: float        # Limite superior do intervalo
    confidence_level: float   # Nível de confiança (ex: 0.95)
    sample_size: int          # Tamanho da amostra
    margin_of_error: float    # Margem de erro
    last_updated: str         # Data da última atualização
    
    def contains(self, test_value: float) -> bool:
        """Verifica se um valor está dentro do intervalo."""
    
    def is_significantly_different(self, other_value: float) -> bool:
        """Verifica se um valor é significativamente diferente."""
```

#### ConfidenceIntervalCalculator

Classe principal para calcular intervalos de confiança:

```python
# Inicializar com nível de confiança (padrão: 95%)
calc = ConfidenceIntervalCalculator(confidence_level=0.95)

# Calcular IC para proporção (ex: triplet 01-02-03)
ci = calc.calculate_proportion_interval(
    successes=63,    # 63 concursos com triplet
    sample_size=300  # em 300 concursos
)
print(f"Proporção: {ci.value:.2%} ± {ci.margin_of_error:.2%}")
print(f"IC 95%: [{ci.lower_bound:.2%}, {ci.upper_bound:.2%}]")

# Calcular IC para média (ex: overlap médio)
ci = calc.calculate_mean_interval([10.0, 10.5, 9.8, 10.2, 9.9])

# Comparar duas proporções
result = calc.compare_proportions(
    successes1=63, sample_size1=300,  # 21%
    successes2=90, sample_size2=300,  # 30%
)
print(f"Diferença significativa: {result['is_significant']}")
```

### 2. Configuração Atualizada

**Arquivo:** `src/lotoia/config/core_003_config.py`

Nova seção `confidence_intervals` na configuração:

```python
CORE_003_CONFIG = {
    # ... outras configurações ...
    
    "confidence_intervals": {
        "triplet_010203": {
            "value": 0.21,  # 63 ocorrências em 300 concursos
            "confidence_interval": [0.164, 0.256],  # IC 95%
            "confidence_level": 0.95,
            "sample_size": 300,
            "margin_of_error": 0.046,
            "last_updated": "2026-06-25",
        },
        "suffix_232425": {
            "value": 0.2167,  # 65 ocorrências em 300 concursos
            "confidence_interval": [0.170, 0.263],  # IC 95%
            "confidence_level": 0.95,
            "sample_size": 300,
            "margin_of_error": 0.047,
            "last_updated": "2026-06-25",
        },
        "paridade_8_7": {
            "value": 0.35,
            "confidence_interval": [0.296, 0.404],
            "confidence_level": 0.95,
            "sample_size": 300,
            "margin_of_error": 0.054,
            "last_updated": "2026-06-25",
        },
        "soma_180_220": {
            "value": 0.60,
            "confidence_interval": [0.545, 0.655],
            "confidence_level": 0.95,
            "sample_size": 300,
            "margin_of_error": 0.055,
            "last_updated": "2026-06-25",
        },
    },
}
```

#### Funções de Acesso

```python
from lotoia.config.core_003_config import (
    get_confidence_intervals,
    get_confidence_interval,
)

# Obter todos os intervalos
all_ci = get_confidence_intervals()

# Obter intervalo específico
triplet_ci = get_confidence_interval("triplet_010203")
print(f"Triplet: {triplet_ci['value']:.2%} ± {triplet_ci['margin_of_error']:.2%}")
```

### 3. Testes

**Arquivo:** `tests/statistics/test_confidence_intervals.py`

28 testes cobrindo:
- `TestConfidenceInterval`: Testes da dataclass
- `TestConfidenceIntervalCalculator`: Testes da calculadora
- `TestHelperFunctions`: Testes das funções auxiliares
- `TestIntegrationWithConfig`: Testes de integração com a configuração

## Resultados dos Testes

```
============================= 81 passed in 23.11s ==============================
```

- 19 testes: `test_core_003_pipeline.py`
- 18 testes: `test_smart_orchestrator.py`
- 16 testes: `test_feedback_and_versioning.py`
- 28 testes: `test_confidence_intervals.py` (Fase 1)

## Como Usar

### Verificar se uma Métrica está Dentro do Intervalo Esperado

```python
from lotoia.config.core_003_config import get_confidence_interval
from lotoia.statistics.confidence_interval_calculator import ConfidenceInterval

# Obter IC do triplet
triplet_ci_dict = get_confidence_interval("triplet_010203")

# Criar objeto ConfidenceInterval
triplet_ci = ConfidenceInterval(
    value=triplet_ci_dict["value"],
    lower_bound=triplet_ci_dict["confidence_interval"][0],
    upper_bound=triplet_ci_dict["confidence_interval"][1],
    confidence_level=triplet_ci_dict["confidence_level"],
    sample_size=triplet_ci_dict["sample_size"],
    margin_of_error=triplet_ci_dict["margin_of_error"],
    last_updated=triplet_ci_dict["last_updated"],
)

# Verificar se taxa observada está dentro do IC
observed_rate = 0.23  # 23% de triplet nos últimos concursos
if triplet_ci.contains(observed_rate):
    print("Taxa observada está dentro do intervalo esperado")
else:
    print("Taxa observada é significativamente diferente do esperado")
```

### Comparar Dois Períodos

```python
from lotoia.statistics.confidence_interval_calculator import compare_proportions

# Comparar triplet em dois períodos
result = compare_proportions(
    successes1=63, sample_size1=300,  # Período 1: 21%
    successes2=75, sample_size2=300,  # Período 2: 25%
    confidence_level=0.95,
)

if result["is_significant"]:
    print(f"Diferença significativa: {result['difference']:.2%}")
    print(f"IC da diferença: {result['confidence_interval']}")
else:
    print("Diferença não é estatisticamente significativa")
```

### Calcular IC para Novos Dados

```python
from lotoia.statistics.confidence_interval_calculator import calculate_proportion_ci

# Após analisar 50 novos concursos
new_successes = 12  # 12 concursos com triplet
new_sample_size = 50

ci = calculate_proportion_ci(
    successes=new_successes,
    sample_size=new_sample_size,
    confidence_level=0.95,
)

print(f"Novo IC: {ci.value:.2%} ± {ci.margin_of_error:.2%}")
print(f"Intervalo: [{ci.lower_bound:.2%}, {ci.upper_bound:.2%}]")
```

## Benefícios

| Benefício | Descrição |
|-----------|-----------|
| **Rigor estatístico** | Substitui valores arbitrários por intervalos calculados |
| **Detecção de mudanças reais** | Sistema sabe quando variação é real ou ruído |
| **Transparência** | Intervalos mostram incerteza das estimativas |
| **Base para Fase 2** | Permite implementar detecção de mudança estatisticamente significativa |

## Próximos Passos (Fase 2)

Com os intervalos de confiança implementados, a Fase 2 pode:

1. **Detectar mudanças reais**: Comparar métricas recentes com IC histórico
2. **Evitar overfitting**: Só ajustar parâmetros quando mudança é significativa
3. **Alertas inteligentes**: Alertar apenas quando há evidência estatística

```python
# Exemplo de uso na Fase 2
if not triplet_ci.contains(recent_rate):
    # Mudança estatisticamente significativa
    suggest_parameter_adjustment()
else:
    # Variação dentro do ruído esperado
    maintain_current_parameters()
```

## Arquivos Modificados

| Arquivo | Mudança |
|---------|---------|
| `src/lotoia/statistics/confidence_interval_calculator.py` | Novo módulo (287 linhas) |
| `src/lotoia/config/core_003_config.py` | Adicionada seção `confidence_intervals` |
| `tests/statistics/test_confidence_intervals.py` | Novo arquivo de testes (28 testes) |

## Referências

- [CORE_003 Pipeline](CORE_003_SIMPLIFIED_PIPELINE.md)
- [Smart Orchestrator](CORE_003_SMART_ORCHESTRATOR.md)
- [Feedback and Versioning](CORE_003_FEEDBACK_AND_VERSIONING.md)
