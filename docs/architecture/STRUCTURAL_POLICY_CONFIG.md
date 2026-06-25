# Configuração Centralizada de Políticas Estruturais

## Visão Geral

O módulo `src/lotoia/config/structural_policy_config.py` centraliza todas as constantes estruturais usadas pelo pipeline CORE_002, eliminando valores hardcoded duplicados em múltiplos arquivos.

**Versão:** 1.0.0  
**Baseline:** últimos 300 concursos oficiais (concursos 3419–3718)

## Por que Centralizar?

### Problema Anterior

Antes da centralização, valores como `MAX_PREFIX_SUFFIX_SHARE` estavam duplicados em 3+ arquivos:

```python
# diverse_top_slice_selection.py
MAX_PREFIX_SUFFIX_SHARE = 0.21

# supervised_output_calibration.py
DEFAULT_PREFIX_SHARE_LIMIT = 0.21

# structural_pool_15d_generator.py
MAX_PREFIX_SUFFIX_SHARE = 0.21
```

**Impacto:** O bug do triplet cap=0 (PR #323) passou despercebido porque a mudança precisava ser feita em múltiplos arquivos simultaneamente.

### Solução

Todas as constantes agora residem em um único módulo:

```python
# src/lotoia/config/structural_policy_config.py
MAX_PREFIX_SUFFIX_SHARE: Final = 0.21
DEFAULT_PREFIX_SHARE_LIMIT: Final = 0.21
HISTORICAL_WINDOW: Final = 300
```

## Constantes Disponíveis

### Políticas de Prefixo/Sufixo

```python
STRUCTURAL_POLICY = {
    "triplet_010203": {
        "label": "01-02-03",
        "historical_freq_pct": 0.21,  # 21% — últimos 300 concursos
        "min_cap": 1,
        "cap_formula": "ceil(pool_size * historical_freq_pct)",
    },
    "suffix_232425": {
        "label": "23-24-25",
        "historical_freq_pct": 0.2167,  # 21.67% — últimos 300 concursos
        "min_cap": 1,
        "cap_formula": "ceil(pool_size * historical_freq_pct)",
    },
    "overlap": {
        "max_overlap_15d": 10,
        "relaxation_thresholds": [20, 35, 50],  # tamanho do lote
        "relaxation_increments": [1, 2, 3],
    },
    "architecture": {
        "max_arch_share_pct": 0.12,
    },
}
```

### Dezenas Críticas

```python
CRITICAL_DIGITS = {
    "reinforce": frozenset({7, 12, 23}),  # reforço suave (+2.5)
    "discourage": frozenset({11, 15, 24, 25}),  # penalização contextual
    "never_hard_block": frozenset({15, 24, 25}),  # nunca bloquear
}
```

### Limites de Share

```python
MAX_PREFIX_SUFFIX_SHARE: Final = 0.21
DEFAULT_PREFIX_SHARE_LIMIT: Final = 0.21
```

### Janela Histórica

```python
HISTORICAL_WINDOW: Final = 300  # últimos 300 concursos
```

## Como Usar

### Importando Constantes

```python
from lotoia.config.structural_policy_config import (
    MAX_PREFIX_SUFFIX_SHARE,
    DEFAULT_PREFIX_SHARE_LIMIT,
    HISTORICAL_WINDOW,
    CRITICAL_DIGITS,
    STRUCTURAL_POLICY,
)

# Usar em cálculos
cap = math.ceil(pool_size * MAX_PREFIX_SUFFIX_SHARE)

# Verificar dezenas críticas
if dezena in CRITICAL_DIGITS["reinforce"]:
    score += 2.5
```

### Importando via Pacote

```python
from lotoia.config import (
    MAX_PREFIX_SUFFIX_SHARE,
    DEFAULT_PREFIX_SHARE_LIMIT,
)
```

## Arquivos que Usam a Configuração

| Arquivo | Constantes Importadas |
|---------|----------------------|
| `diverse_top_slice_selection.py` | `MAX_PREFIX_SUFFIX_SHARE`, `DEFAULT_PREFIX_SHARE_LIMIT` |
| `supervised_output_calibration.py` | `DEFAULT_PREFIX_SHARE_LIMIT` |
| `structural_pool_15d_generator.py` | `MAX_PREFIX_SUFFIX_SHARE` |
| `m_core_003_prefix_suffix_policy.py` | `HISTORICAL_WINDOW` |

## Atualizando Constantes

### Quando Atualizar

1. **Novo baseline histórico:** Quando a janela de 300 concursos mudar
2. **Ajuste de políticas:** Quando limites de share precisarem ser alterados
3. **Mudança de dezenas críticas:** Quando reforço/penalização mudar

### Como Atualizar

1. Edite **apenas** `src/lotoia/config/structural_policy_config.py`
2. Execute os testes para validar:
   ```bash
   pytest tests/generation/test_structural_metrics.py -v
   ```
3. Commit e push:
   ```bash
   git add src/lotoia/config/structural_policy_config.py
   git commit -m "feat(config): atualizar MAX_PREFIX_SUFFIX_SHARE para 0.22"
   git push origin main
   ```

### Exemplo: Atualizar Triplet Cap

```python
# Antes
MAX_PREFIX_SUFFIX_SHARE: Final = 0.21

# Depois
MAX_PREFIX_SUFFIX_SHARE: Final = 0.22  # Nova frequência histórica
```

Todos os módulos que importam essa constante serão atualizados automaticamente.

## Validação

### Testes Automatizados

```bash
# Testar métricas estruturais
pytest tests/generation/test_structural_metrics.py -v

# Testar configuração
python -c "from lotoia.config.structural_policy_config import MAX_PREFIX_SUFFIX_SHARE; print(MAX_PREFIX_SUFFIX_SHARE)"
```

### Verificação Manual

```python
from lotoia.config.structural_policy_config import (
    MAX_PREFIX_SUFFIX_SHARE,
    STRUCTURAL_POLICY,
)

# Verificar valor
assert MAX_PREFIX_SUFFIX_SHARE == 0.21

# Verificar política
triplet_policy = STRUCTURAL_POLICY["triplet_010203"]
assert triplet_policy["historical_freq_pct"] == 0.21
assert triplet_policy["min_cap"] == 1
```

## Benefícios

1. **Single Source of Truth:** Todas as constantes em um único lugar
2. **Facilidade de Manutenção:** Mudança em 1 arquivo, não em 3+
3. **Prevenção de Bugs:** Evita inconsistências entre módulos
4. **Rastreabilidade:** Versão da configuração documentada
5. **Testabilidade:** Fácil de mockar em testes

## Histórico de Mudanças

| Data | Mudança | PR |
|------|---------|-----|
| 2026-06-25 | Criação do módulo | d9a3f84 |
| 2026-06-25 | MAX_PREFIX_SUFFIX_SHARE = 0.21 | 1442a45 |

## Referências

- [CORE_002 Pipeline](CORE_002_SOVEREIGN_PIPELINE.md)
- [CHANGELOG](../../CHANGELOG.md)
- [README](../../README.md)
