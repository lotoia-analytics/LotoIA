# Sistema de Feedback Automático e Versionamento CORE_003

## Visão Geral

O CORE_003 possui dois sistemas complementares para melhoria contínua:

1. **Sistema de Feedback Automático**: Analisa resultados pós-concurso e sugere ajustes
2. **Sistema de Versionamento**: Rastreia versões do modelo com mudanças e resultados

## Sistema de Feedback Automático

### Funcionamento

Após cada concurso, o sistema:
1. Analisa os jogos gerados vs resultado oficial
2. Calcula métricas de desempenho (hit_rate_11_13, triplet_hit_rate, etc.)
3. Gera sugestões de ajuste baseadas nas métricas
4. Rastreia tendência de desempenho ao longo do tempo

### Uso Básico

```python
from lotoia.generation.post_contest_feedback import post_contest_feedback

# Após um concurso, analisar desempenho
result = post_contest_feedback(
    contest_number=3719,
    contest_numbers=[1, 2, 3, 5, 8, 10, 12, 15, 18, 20, 22, 23, 24, 25, 17],
    generated_games=generated_games,  # Jogos que foram gerados para este concurso
    format="15D",
)

# Ver métricas
print(f"Hit rate 11-13: {result['metrics']['hit_rate_11_13']:.1%}")
print(f"Triplet hit rate: {result['metrics']['triplet_hit_rate']:.1%}")

# Ver sugestões
for suggestion in result['suggestions']:
    print(f"Ajuste: {suggestion['adjustment']}")
    print(f"Motivo: {suggestion['reason']}")
    print(f"Prioridade: {suggestion['priority']}")
```

### Métricas Calculadas

| Métrica | Descrição | Threshold |
|---------|-----------|-----------|
| `hit_rate_11_13` | Taxa de jogos com 11-13 acertos | < 10% gera alerta |
| `hit_rate_14_15` | Taxa de jogos com 14-15 acertos | > 5% é excelente |
| `triplet_hit_rate` | Taxa de jogos com triplet 01-02-03 quando sorteado | < 15% gera alerta |
| `suffix_hit_rate` | Taxa de jogos com suffix 23-24-25 quando sorteado | < 15% gera alerta |
| `avg_hits` | Média de acertos por jogo | - |
| `max_hits` | Máximo de acertos em um jogo | - |

### Sugestões Automáticas

O sistema gera sugestões baseadas nas métricas:

| Condição | Sugestão | Prioridade |
|----------|----------|------------|
| `hit_rate_11_13` < 10% | `increase_diversity` | Alta |
| `triplet_hit_rate` < 15% | `increase_triplet_cap` | Média |
| `suffix_hit_rate` < 15% | `increase_suffix_cap` | Média |
| `hit_rate_14_15` > 5% | `maintain_current` | Baixa |

### Tendência de Desempenho

```python
from lotoia.generation.post_contest_feedback import get_performance_trend

# Ver tendência das últimas 10 análises
trend = get_performance_trend(last_n=10)

print(f"Tendência: {trend['trend']}")  # improving, declining, stable
print(f"Média hit rate: {trend['avg_hit_rate_11_13']:.1%}")
```

## Sistema de Versionamento

### Funcionamento

O sistema rastreia:
- Versões do modelo (v3.0.0, v3.1.0, etc.)
- Mudanças realizadas em cada versão
- Resultados de backtest
- Configurações alteradas

### Uso Básico

```python
from lotoia.generation.model_versioning import register_model_version

# Registrar nova versão
version_info = register_model_version(
    version="v3.1.0",
    changes=[
        "Ajustou triplet cap de 21% para 22%",
        "Melhorou diversidade em lotes grandes",
        "Otimizou performance do anti-clone",
    ],
    backtest_results={
        "hit_rate_11_13": 0.16,
        "avg_overlap": 9.3,
        "triplet_hit_rate": 0.22,
    },
    config_changes={
        "triplet_freq": 0.22,
        "overlap_penalty": 1.15,
    },
)
```

### Consultar Versões

```python
from lotoia.generation.model_versioning import (
    get_model_version,
    get_latest_model_version,
    list_model_versions,
)

# Obter versão específica
v3_1_0 = get_model_version("v3.1.0")
print(f"Mudanças: {v3_1_0['changes']}")
print(f"Backtest: {v3_1_0['backtest_results']}")

# Obter versão mais recente
latest = get_latest_model_version()
print(f"Versão atual: {latest['version']}")

# Listar todas as versões
all_versions = list_model_versions()
for v in all_versions:
    print(f"{v['version']}: {v['release_date']}")
```

### Comparar Versões

```python
from lotoia.generation.model_versioning import compare_model_versions

# Comparar duas versões
comparison = compare_model_versions("v3.0.0", "v3.1.0")

print(f"Mudanças em v3.0.0: {comparison['changes_a']}")
print(f"Mudanças em v3.1.0: {comparison['changes_b']}")

# Comparar resultados de backtest
for metric, data in comparison['backtest_comparison'].items():
    print(f"{metric}:")
    print(f"  v3.0.0: {data['version_a']}")
    print(f"  v3.1.0: {data['version_b']}")
    print(f"  Melhoria: {data['improvement']}")
```

### Atualizar Resultados de Backtest

```python
from lotoia.generation.model_versioning import ModelVersioning

versioning = ModelVersioning()

# Após novo backtest, atualizar resultados
versioning.update_backtest_results(
    "v3.1.0",
    {
        "hit_rate_11_13": 0.17,  # Melhorou de 0.16 para 0.17
        "avg_overlap": 9.2,
        "triplet_hit_rate": 0.23,
    },
)
```

## Integração Feedback + Versionamento

### Fluxo Completo

```python
from lotoia.generation.post_contest_feedback import post_contest_feedback
from lotoia.generation.model_versioning import ModelVersioning

# 1. Analisar desempenho pós-concurso
feedback_result = post_contest_feedback(
    contest_number=3720,
    contest_numbers=[...],
    generated_games=generated_games,
    format="15D",
)

# 2. Se houver sugestões, aplicar ajustes e registrar nova versão
if feedback_result['suggestions']:
    # Aplicar ajustes (exemplo)
    new_config = apply_suggestions(feedback_result['suggestions'])
    
    # Gerar novos jogos com configuração ajustada
    new_games = generate_core_003_games(
        format="15D",
        count=50,
        calibration="equilibrado",
    )
    
    # Registrar nova versão
    versioning = ModelVersioning()
    versioning.register_version(
        version="v3.2.0",
        changes=[s['adjustment'] for s in feedback_result['suggestions']],
        backtest_results={
            "hit_rate_11_13": feedback_result['metrics']['hit_rate_11_13'],
        },
        config_changes=new_config,
    )
```

## Persistência

### Arquivo de Versões

As versões são persistidas em `data/model_versions.json`:

```json
{
  "v3.0.0": {
    "version": "v3.0.0",
    "release_date": "2026-06-25T10:00:00",
    "changes": [
      "Consolidou M-STAT-002 + M-CORE-003",
      "Simplificou calibration plan"
    ],
    "backtest_results": {
      "hit_rate_11_13": 0.15,
      "avg_overlap": 9.5
    },
    "config_changes": {
      "triplet_freq": 0.21
    },
    "status": "active"
  }
}
```

### Histórico de Feedback

O histórico de feedback é mantido em memória durante a sessão. Para persistência longa, integrar com banco de dados.

## Exemplos Avançados

### Análise de Múltiplos Concursos

```python
from lotoia.generation.post_contest_feedback import PostContestFeedback

feedback = PostContestFeedback()

# Analisar últimos 10 concursos
for contest in recent_contests:
    feedback.analyze_contest_result(
        contest_number=contest['number'],
        contest_numbers=contest['numbers'],
        generated_games=contest['generated_games'],
        format="15D",
    )

# Ver tendência
trend = feedback.get_performance_trend(last_n=10)
print(f"Tendência: {trend['trend']}")
print(f"Análises: {trend['analyses']}")
```

### Relatório de Versão

```python
from lotoia.generation.model_versioning import get_model_version

def generate_version_report(version: str) -> str:
    """Gera relatório detalhado de uma versão."""
    v = get_model_version(version)
    
    report = f"""
# Relatório da Versão {v['version']}

**Data de Release:** {v['release_date']}
**Status:** {v['status']}

## Mudanças
"""
    
    for change in v['changes']:
        report += f"- {change}\n"
    
    report += "\n## Resultados de Backtest\n"
    
    for metric, value in v['backtest_results'].items():
        report += f"- **{metric}:** {value}\n"
    
    report += "\n## Mudanças de Configuração\n"
    
    for param, value in v['config_changes'].items():
        report += f"- **{param}:** {value}\n"
    
    return report

print(generate_version_report("v3.1.0"))
```

## Testes

```bash
# Executar todos os testes
pytest tests/generation/test_feedback_and_versioning.py -v

# Executar testes específicos
pytest tests/generation/test_feedback_and_versioning.py::TestPostContestFeedback -v
pytest tests/generation/test_feedback_and_versioning.py::TestModelVersioning -v
```

## Status

- **Feedback Automático:** ✓ Implementado e testado
- **Versionamento:** ✓ Implementado e testado
- **Integração:** ✓ Funcionando
- **Testes:** 16 testes passando

## Referências

- [CORE_003 Pipeline](CORE_003_SIMPLIFIED_PIPELINE.md)
- [Structural Policy Config](STRUCTURAL_POLICY_CONFIG.md)
- [CHANGELOG](../../CHANGELOG.md)
