# Fase 2: Detecção de Mudança Real vs Ruído

## Visão Geral

A Fase 2 implementa detecção estatística de mudanças significativas, permitindo ao sistema distinguir variações reais de ruído estatístico antes de ajustar parâmetros.

## O que foi implementado

### 1. Módulo de Detecção de Mudanças

**Arquivo:** `src/lotoia/statistics/change_detector.py`

#### Classes e Funções

```python
from lotoia.statistics.change_detector import (
    ChangeDetector,
    ChangeDetectionResult,
    is_statistically_significant_change,
    should_adjust_parameter,
)
```

#### ChangeDetector

Classe principal para detectar mudanças estatisticamente significativas:

```python
# Inicializar detector
detector = ChangeDetector(confidence_level=0.95)

# Detectar mudança
result = detector.detect_change(
    current_rate=0.15,      # Taxa observada recentemente
    historical_rate=0.21,   # Taxa histórica de referência
    sample_size_recent=50,  # Tamanho da amostra recente
    sample_size_historical=300,  # Tamanho da amostra histórica
)

if result.is_significant:
    print(f"Mudança significativa: {result.relative_change:.1%}")
    print(f"Z-score: {result.z_score:.2f}")
    print(f"P-value: {result.p_value:.4f}")
```

#### ChangeDetectionResult

Dataclass que representa o resultado da detecção:

```python
@dataclass
class ChangeDetectionResult:
    is_significant: bool        # Se a mudança é estatisticamente significativa
    current_rate: float         # Taxa observada no período recente
    historical_rate: float      # Taxa histórica de referência
    difference: float           # Diferença absoluta (current - historical)
    relative_change: float      # Mudança relativa (difference / historical)
    confidence_interval: list[float]  # IC da taxa histórica
    z_score: float              # Estatística Z do teste
    p_value: float              # Valor p aproximado
    confidence_level: float     # Nível de confiança usado
    sample_size_recent: int     # Tamanho da amostra recente
    sample_size_historical: int # Tamanho da amostra histórica
    detected_at: str            # Timestamp da detecção
```

#### should_adjust_parameter

Método que decide se um parâmetro deve ser ajustado:

```python
# Verificar se deve ajustar parâmetro
should_adjust, result = detector.should_adjust_parameter(
    metric_name="triplet_010203",
    current_rate=0.15,
    historical_config={"value": 0.21, "sample_size": 300},
    sample_size_recent=50,
)

if should_adjust:
    print(f"Ajustar parâmetro: mudança de {result.relative_change:.1%}")
```

**Critérios para ajuste:**
1. Mudança é estatisticamente significativa (fora do IC)
2. Mudança é substancial (> 5% relativo)

### 2. Integração com SmartOrchestrator

**Arquivo:** `src/lotoia/generation/smart_orchestrator.py`

O SmartOrchestrator agora usa o ChangeDetector para decidir quando ajustar parâmetros:

```python
class SmartOrchestrator:
    def __init__(self, format: str = "15D", auto_calibrate: bool = False):
        # ...
        self.change_detector = ChangeDetector(confidence_level=0.95)
    
    def _apply_suggestions(self, base_preset, suggestions, trend):
        # Para cada sugestão, verificar se mudança é significativa
        if adj_type == "increase_triplet_cap":
            if current_rate is not None:
                triplet_config = get_confidence_interval("triplet_010203")
                should_adjust, result = self.change_detector.should_adjust_parameter(
                    metric_name="triplet_010203",
                    current_rate=current_rate,
                    historical_config=triplet_config,
                    sample_size_recent=sample_size,
                )
                if should_adjust:
                    # Aplicar ajuste
                    adjustments["triplet_freq"] = f"{current_freq + 0.02:.2f}"
                else:
                    # Ignorar ajuste (mudança não significativa)
                    logger.debug("Ajuste ignorado (mudança não significativa)")
```

### 3. Testes

**Arquivo:** `tests/statistics/test_change_detector.py`

23 testes cobrindo:
- `TestChangeDetector`: Testes da classe principal
- `TestChangeDetectionResult`: Testes da dataclass
- `TestHelperFunctions`: Testes das funções auxiliares
- `TestIntegrationWithConfig`: Testes de integração com configuração

## Como Funciona

### Antes (Fase 1)

```python
# Ajusta sempre que threshold é violado
if triplet_hit_rate < 0.15:
    increase_triplet_cap()
```

**Problema:** Reage a qualquer flutuação, mesmo ruído estatístico.

### Depois (Fase 2)

```python
# Ajusta só se mudança é significativa
if is_statistically_significant_change(
    current_rate=0.15,
    historical_rate=0.21,
    sample_size_recent=50,
    sample_size_historical=300,
):
    increase_triplet_cap()
```

**Benefício:** Só reage quando há evidência estatística de mudança real.

## Exemplos de Uso

### Detectar Mudança Significativa

```python
from lotoia.statistics.change_detector import ChangeDetector

detector = ChangeDetector(confidence_level=0.95)

# Triplet caiu de 21% para 10%
result = detector.detect_change(
    current_rate=0.10,
    historical_rate=0.21,
    sample_size_recent=50,
    sample_size_historical=300,
)

print(f"Significativa: {result.is_significant}")  # True
print(f"Diferença: {result.difference:.2%}")      # -11.00%
print(f"Mudança relativa: {result.relative_change:.1%}")  # -52.4%
print(f"Z-score: {result.z_score:.2f}")           # -3.45
print(f"P-value: {result.p_value:.4f}")           # 0.0006
```

### Verificar se Deve Ajustar Parâmetro

```python
from lotoia.statistics.change_detector import should_adjust_parameter
from lotoia.config.core_003_config import get_confidence_interval

triplet_config = get_confidence_interval("triplet_010203")

should_adjust, result = should_adjust_parameter(
    metric_name="triplet_010203",
    current_rate=0.15,
    historical_config=triplet_config,
    sample_size_recent=50,
)

if should_adjust:
    print(f"Ajustar triplet_cap: mudança de {result.relative_change:.1%}")
else:
    print("Mudança não é significativa, manter parâmetros atuais")
```

### Integração com Feedback System

```python
from lotoia.generation.post_contest_feedback import post_contest_feedback
from lotoia.statistics.change_detector import ChangeDetector

# Analisar resultado de concurso
feedback = post_contest_feedback(
    contest_number=3720,
    contest_numbers=[...],
    generated_games=games,
)

# Verificar se sugestões são estatisticamente significativas
detector = ChangeDetector(confidence_level=0.95)

for suggestion in feedback["suggestions"]:
    if suggestion["adjustment"] == "increase_triplet_cap":
        current_rate = suggestion.get("current_rate")
        if current_rate:
            should_adjust, result = detector.should_adjust_parameter(
                metric_name="triplet_010203",
                current_rate=current_rate,
                historical_config=get_confidence_interval("triplet_010203"),
                sample_size_recent=suggestion.get("sample_size", 50),
            )
            if should_adjust:
                apply_adjustment(suggestion)
```

## Resultados dos Testes

```
============================== 41 passed in 9.47s ==============================
```

| Suite | Testes |
|-------|--------|
| `test_change_detector.py` | 23 |
| `test_smart_orchestrator.py` | 18 |

## Benefícios

| Benefício | Descrição |
|-----------|-----------|
| **Evita overfitting** | Não reage a flutuações normais |
| **Decisões objetivas** | Baseado em evidência estatística |
| **Transparência** | Z-score e p-value mostram força da evidência |
| **Robustez** | Considera tamanho da amostra |
| **Integração** | Funciona com Fase 1 (IC) e SmartOrchestrator |

## Arquivos Modificados

| Arquivo | Mudança |
|---------|---------|
| `src/lotoia/statistics/change_detector.py` | Novo módulo (287 linhas) |
| `src/lotoia/generation/smart_orchestrator.py` | Integra ChangeDetector |
| `tests/statistics/test_change_detector.py` | Novo arquivo de testes (23 testes) |

## Próximos Passos (Fase 3)

Com a detecção de mudanças implementada, a Fase 3 pode:

1. **Geração nativa por formato**: Cada formato (15D-23D) com motor próprio
2. **Persistência do feedback**: Histórico no PostgreSQL
3. **Walk-forward validation**: Validação temporal rigorosa

## Referências

- [Fase 1: Intervalos de Confiança](CORE_003_PHASE1_CONFIDENCE_INTERVALS.md)
- [Smart Orchestrator](CORE_003_SMART_ORCHESTRATOR.md)
- [CORE_003 Pipeline](CORE_003_SIMPLIFIED_PIPELINE.md)
