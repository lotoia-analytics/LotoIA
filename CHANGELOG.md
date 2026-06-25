# Changelog

Todas as mudanças notáveis no projeto LotoIA serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [Não Lançado]

### Adicionado
- **Testes de Métricas Estruturais** (2026-06-25)
  - 13 testes cobrindo `compute_structural_metrics` e `validate_structural_metrics`
  - Testes de triplet 01-02-03: frequência, limites, bug cap=0
  - Testes de overlap médio: dentro/fora dos limites
  - Testes de configuração de limites estruturais
  - Testes de casos edge: lista vazia, jogos sem numbers
  - Teste de modo strict (warnings viram violações)
  - Testes de estrutura de retorno
  - Arquivo: `tests/generation/test_structural_metrics.py`

- **Logs Estruturados CORE_002** (2026-06-25)
  - L1 `build_sovereign_pool`: triplet/suffix count e percentual
  - L4 `apply_anti_clone_gp`: input/selected/rejected counts
  - L5 `apply_critical_digit_layer`: boost/penalty stats
  - `compose_sovereign_gp`: métricas completas do GP final
    - triplet_010203, suffix_232425, avg_overlap, diversity_score
    - Warnings automáticos quando métricas fora do esperado:
      - triplet < 10% ou > 35% (target: 21%)
      - suffix < 10% ou > 35% (target: 21.67%)
      - overlap fora de 7.0-13.0
      - diversity < 0.70
  - Arquivo: `src/lotoia/generation/lei15_core_002.py`

- **Reorganizador de context_json** (2026-06-25)
  - Módulo `context_json_organizer.py` com `organize_context_json()`
  - Transforma 300+ campos planos em sub-objetos organizados:
    - `generation_info`: modo, formato, target_contest
    - `structural_metrics`: triplet, suffix, overlap, caps, pool
    - `validation`: structural, frequency, policy
    - `calibration`: dados de calibração ML
    - `hierarchy`: estágios, quality_tier
    - `diverse_top_slice`: swaps, iterations
  - Função `flatten_context_json()` para compatibilidade reversa
  - Integrado no `basic_generator.py` (organized_context no payload)
  - Arquivo: `src/lotoia/statistics/context_json_organizer.py`

- **Validação Automática de Métricas Estruturais** (2026-06-25)
  - Módulo `structural_metrics_validator.py` com limites aceitáveis
  - Triplet 01-02-03: min 10%, max 35%, target 21% (±6pp)
  - Overlap médio: min 7.0, max 13.0, target 10.0
  - Integrado no `basic_generator.py` após geração do GP final
  - Detecta bugs automaticamente (ex: triplet cap=0)
  - Loga violações como ERROR, warnings como WARNING
  - Persiste métricas e validação no context_json
  - Arquivo: `src/lotoia/statistics/structural_metrics_validator.py`

- **Configuração Centralizada de Políticas Estruturais** (2026-06-25)
  - Módulo `structural_policy_config.py` como fonte centralizada
  - `MAX_PREFIX_SUFFIX_SHARE` e `DEFAULT_PREFIX_SHARE_LIMIT` em módulo único
  - Elimina valores hardcoded duplicados em 4 arquivos
  - Previne bugs como triplet cap=0 (mudança em 1 linha agora)
  - Arquivos atualizados:
    - `diverse_top_slice_selection.py`
    - `supervised_output_calibration.py`
    - `structural_pool_15d_generator.py`
    - `m_core_003_prefix_suffix_policy.py`
  - Arquivo: `src/lotoia/config/structural_policy_config.py`

### Corrigido
- **Calibração do Triplet 01-02-03** (PR #323)
  - `structural_triplet_010203_cap` estava sendo definido como 0 em todas as gerações
  - Frequência histórica real: 21% (63 de 300 concursos)
  - Correção: `MAX_PREFIX_SUFFIX_SHARE` de 0.14 para 0.21
  - Cap proporcional: `ceil(pool_size * 0.21)` com mínimo 1
  - Versão atualizada: `M-STAT-002-v5`

- **Remoção de Viés das Dezenas 06/16** (PR #322)
  - Dezena 06: 83% (LotoIA) vs 62% (oficial) = +21pp
  - Dezena 16: 80% vs 55% = +25pp
  - Removidas de `_REINFORCE_DIGITS` e `target_coverage_digits`
  - Adicionado módulo `frequency_validation.py` para monitoramento

- **ML como Sensor Observacional** (PR #321)
  - ML não bloqueia mais conferibilidade
  - `official_release_allowed` sempre True
  - `is_ml_verdict_blocked` removido
  - `ml_verdict_blocked` renomeado para `ml_verdict_observational`

## [1.0.0] - 2026-06-17

### Adicionado
- Núcleo Soberano CORE_002 (ADR-046)
- Pipeline de 5 camadas (L1-L5)
- Suporte a formatos 15D-23D
- Central ML de calibração supervisionada
- Dashboard institucional Streamlit
- API FastAPI para geração e conferência
- Persistência PostgreSQL no Railway
- Feedback loop automatizado (22:50 BRT)
- Conferência por bateria operacional
- Memória evolutiva de cobertura estrutural

### Arquitetura
- **Geração**: CORE_002 soberano com 5 camadas
- **Calibração**: ML como sensor observacional
- **Conferência**: Backtesting contra 10 concursos
- **Feedback**: Loop automatizado pós-concurso
- **Dashboard**: Streamlit institucional
- **API**: FastAPI com endpoints bloqueados (ADR-047)
- **Banco**: PostgreSQL no Railway

### Estatísticas
- 6.353 jogos gerados em 143 generation events
- 81 concursos reconciliados com backtesting
- 8 JACKPOTS (15 acertos) identificados
- 47 eventos pendentes (1.540 jogos) aguardando reconciliação
- 67% de cobertura de reconciliação
- Baseline: últimos 300 concursos oficiais (3419-3718)

## Formato

### Tipos de Mudanças
- `Adicionado` para novas funcionalidades
- `Alterado` para mudanças em funcionalidades existentes
- `Depreciado` para funcionalidades que serão removidas
- `Removido` para funcionalidades removidas
- `Corrigido` para correções de bugs
- `Segurança` para correções de vulnerabilidades

### Versões
- Versão maior (X.0.0): mudanças incompatíveis
- Versão menor (0.X.0): novas funcionalidades compatíveis
- Patch (0.0.X): correções de bugs compatíveis
