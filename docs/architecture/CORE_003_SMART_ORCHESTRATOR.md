# Smart Orchestrator CORE_003

## Visão Geral

O **Smart Orchestrator** é a camada de orquestração inteligente que conecta:
- Sistema de Feedback Automático
- Versionamento de Modelos
- Pipeline de Geração CORE_003

Ele permite que o sistema **ajuste automaticamente os parâmetros de geração** baseado em resultados anteriores, criando um ciclo de melhoria contínua.

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│  generate_core_003_games() ← Função pública                 │
│         ↓                                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  SmartOrchestrator                                  │   │
│  │  - Consulta feedback system                         │   │
│  │  - Aplica ajustes automáticos                       │   │
│  │  - Seleciona/calibra preset                         │   │
│  │  - Registra versão                                  │   │
│  └─────────────────────────────────────────────────────┘   │
│         ↓                                                   │
│  Core003Pipeline (4 camadas L1-L4)                         │
│         ↓                                                   │
│  Jogos Gerados                                              │
└─────────────────────────────────────────────────────────────┘
```

## Uso Básico

### Sem Auto-Calibração (padrão)

```python
from lotoia.generation.core_003_pipeline import generate_core_003_games

# Uso simples — igual ao anterior
games = generate_core_003_games(
    format="15D",
    count=50,
    calibration="equilibrado",
)
```

### Com Auto-Calibração

```python
# Uso com auto-calibração — ajusta parâmetros baseado em feedback
games = generate_core_003_games(
    format="15D",
    count=50,
    auto_calibrate=True,  # <-- Novo parâmetro
)
```

### Com Versão Específica

```python
# Uso com versão específica do modelo
games = generate_core_003_games(
    format="15D",
    count=50,
    version="v3.1.0",  # <-- Novo parâmetro
)
```

## Como Funciona

### 1. Consulta Feedback System

O orchestrator consulta o sistema de feedback para obter:
- Tendência de desempenho (improving, declining, stable)
- Sugestões pendentes de ajuste
- Métricas históricas

### 2. Calibra Preset

Baseado no feedback, o orchestrator:
- Ajusta o preset de calibração (conservador → equilibrado → agressivo)
- Aplica ajustes finos aos parâmetros:
  - `diversity_floor`: ±0.03
  - `overlap_penalty`: ±0.05
  - `triplet_freq`: ±0.02
  - `suffix_freq`: ±0.02

### 3. Registra Versão

Se houve ajustes significativos, o orchestrator:
- Cria nova versão (incrementa patch: v3.0.0 → v3.0.1)
- Registra mudanças na configuração
- Salva resultados de backtest

### 4. Gera Jogos

O pipeline CORE_003 é executado com a configuração ajustada.

## Exemplos Avançados

### Usando SmartOrchestrator Diretamente

```python
from lotoia.generation.smart_orchestrator import SmartOrchestrator

# Criar orchestrator
orchestrator = SmartOrchestrator(
    format="15D",
    auto_calibrate=True,
)

# Calibrar preset
calibrated_preset, adjustments = orchestrator.calibrate_preset("equilibrado")
print(f"Preset calibrado: {calibrated_preset}")
print(f"Ajustes: {adjustments}")

# Aplicar ajustes à configuração
config = orchestrator.apply_adjustments_to_config(adjustments)

# Obter resumo da orquestração
summary = orchestrator.get_orchestration_summary()
print(f"Tendência: {summary['feedback_trend']['trend']}")
```

### Integrando com Feedback Pós-Concurso

```python
from lotoia.generation.core_003_pipeline import generate_core_003_games
from lotoia.generation.post_contest_feedback import post_contest_feedback

# 1. Gerar jogos para concurso N
games = generate_core_003_games(
    format="15D",
    count=50,
    auto_calibrate=True,
)

# 2. Após o concurso, analisar resultado
result = post_contest_feedback(
    contest_number=3720,
    contest_numbers=[1, 2, 3, 5, 8, 10, 12, 15, 18, 20, 22, 23, 24, 25, 17],
    generated_games=games,
    format="15D",
)

# 3. Ver sugestões
for suggestion in result["suggestions"]:
    print(f"Ajuste: {suggestion['adjustment']}")
    print(f"Motivo: {suggestion['reason']}")

# 4. Próxima geração usará essas sugestões automaticamente
next_games = generate_core_003_games(
    format="15D",
    count=50,
    auto_calibrate=True,  # Aplica sugestões automaticamente
)
```

### Comparando Versões

```python
from lotoia.generation.model_versioning import compare_model_versions

# Comparar duas versões
comparison = compare_model_versions("v3.0.0", "v3.1.0")

print(f"Mudanças em v3.0.0: {comparison['changes_a']}")
print(f"Mudanças em v3.1.0: {comparison['changes_b']}")

# Comparar resultados de backtest
for metric, data in comparison["backtest_comparison"].items():
    print(f"{metric}:")
    print(f"  v3.0.0: {data['version_a']}")
    print(f"  v3.1.0: {data['version_b']}")
    print(f"  Melhoria: {data['improvement']}")
```

## Parâmetros de Ajuste

### Sugestões de Alta Prioridade

| Condição | Ajuste | Efeito |
|----------|--------|--------|
| `hit_rate_11_13` < 10% | `increase_diversity` | Muda preset para mais agressivo |
| `triplet_hit_rate` < 15% | `increase_triplet_cap` | Aumenta triplet_freq em 0.02 |
| `suffix_hit_rate` < 15% | `increase_suffix_cap` | Aumenta suffix_freq em 0.02 |

### Ajustes de Tendência

| Tendência | Ajuste |
|-----------|--------|
| `declining` | Muda preset para mais conservador |
| `improving` | Mantém preset atual |
| `stable` | Mantém preset atual |

## Arquivos

| Arquivo | Função |
|---------|--------|
| `src/lotoia/generation/smart_orchestrator.py` | Smart Orchestrator principal |
| `src/lotoia/generation/core_003_pipeline.py` | Pipeline com integração |
| `src/lotoia/generation/post_contest_feedback.py` | Sistema de feedback |
| `src/lotoia/generation/model_versioning.py` | Versionamento de modelos |
| `tests/generation/test_smart_orchestrator.py` | 18 testes |

## Testes

```bash
# Executar todos os testes do Smart Orchestrator
pytest tests/generation/test_smart_orchestrator.py -v

# Executar todos os testes CORE_003
pytest tests/generation/test_core_003_pipeline.py \
       tests/generation/test_smart_orchestrator.py \
       tests/generation/test_feedback_and_versioning.py -v
```

**Status:** 53 testes passando

## Benefícios

| Benefício | Descrição |
|-----------|-----------|
| **Não quebra o que existe** | `Core003Pipeline` continua igual |
| **Separação de responsabilidades** | Feedback, versionamento e geração em módulos separados |
| **Retrocompatível** | Funciona igual para quem não quer auto-calibração |
| **Opt-in** | Quem quer feedback automático ativa com `auto_calibrate=True` |
| **Testável** | Cada camada pode ser testada isoladamente |
| **Melhoria contínua** | Sistema aprende com resultados anteriores |

## Referências

- [CORE_003 Pipeline](CORE_003_SIMPLIFIED_PIPELINE.md)
- [Feedback and Versioning](CORE_003_FEEDBACK_AND_VERSIONING.md)
- [Structural Policy Config](STRUCTURAL_POLICY_CONFIG.md)
