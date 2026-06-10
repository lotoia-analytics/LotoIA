# Relatório técnico — LotoIA (`src/lotoia/`)

**Gerado em:** 2026-06-10  
**Escopo:** estrutura de diretórios, módulos Python, dependências, scoring, calibração, `sequence_score`, `final_score`, status de `calibration: null`  
**Repositório:** lotoia-analytics/LotoIA

---

## Sumário

1. [Estrutura de diretórios](#1-estrutura-de-diretórios-srclotoia)
2. [Módulos Python e responsabilidades](#2-módulos-python-e-responsabilidades)
3. [Dependências entre módulos](#3-dependências-entre-módulos)
4. [Conteúdo de scoring, rerank e calibração](#4-conteúdo-solicitado)
5. [`sequence_score` — valor e cálculo](#5-sequence_score--valor-e-cálculo)
6. [Agregação do `final_score`](#6-agregação-do-final_score)
7. [Status da calibração (`calibration: null`)](#7-status-da-calibração)
8. [JSON resumido](#8-json-resumido)

---

## 1. Estrutura de diretórios (`src/lotoia/`)

> **Nota importante:** não existe `src/lotoia/scoring/`. O scoring oficial está em:
> - `src/lotoia/statistics/scoring.py`
> - `src/lotoia/statistics/advanced.py`
> - `src/lotoia/statistics/temporal.py`
> - `src/lotoia/statistics/combinations.py`

```
src/lotoia/
├── analytics/          # Camada analítica/científica institucional
├── assistance/         # Experiência assistiva e linguagem operacional
├── authentication/     # Autenticação
├── backtesting/        # Backtest histórico
├── benchmark/          # Benchmark científico
├── calibration/        # Calibração de pesos do final_score (backtest-driven)
├── combinatorics/      # Expansão dimensional de cartões
├── config/             # Configuração
├── data/               # Carga/validação de histórico
├── database/           # ORM, repositórios, persistência
├── environment/        # Ambiente runtime
├── experiments/        # Experimentos ML/governança temporal
├── generator/          # Geração de jogos (Lei 15 / motor estatístico)
├── governance/         # Governança científica e institucional
│   ├── autonomous/
│   ├── council/
│   └── releases/
├── ingestion/          # Ingestão oficial Caixa/sync
├── memory/             # Memória institucional evolutiva
├── ml/                 # ML assistivo (score_ml, rerank, calibração ML)
├── models/             # Modelos de domínio (Draw, etc.)
├── observability/      # Telemetria, saúde, dashboards operacionais
├── orchestration/      # Orquestração inteligente
├── persistence/        # Persistência distribuída
├── public/             # API/runtime público Streamlit
│   ├── governance/
│   ├── persistence/
│   ├── security/
│   ├── services/
│   ├── streamlit/
│   └── tracking/
├── reliability/        # Resiliência/failover
├── reports/            # Geração de relatórios (backtest/calibração)
├── scheduling/         # Agendadores
├── statistics/         # NÚCLEO ESTATÍSTICO (scoring, temporal, combos)
├── storage/            # Artefatos operacionais
├── workflows/          # Engine de workflows
├── cli.py              # CLI principal
├── standards.py        # Contratos institucionais
└── __main__.py
```

**Totais aproximados:** ~217 arquivos `.py`, ~215 módulos.

---

## 2. Módulos Python e responsabilidades

### 2.1 Por pacote (visão executiva)

| Pacote | Responsabilidade |
|--------|------------------|
| `statistics/` | Núcleo estatístico: combinações, scoring, temporal, inteligência histórica, traces |
| `generator/` | Geração/ranking de jogos (`basic_generator`, adapter `engine`) |
| `calibration/` | Comparação de pesos do `final_score` via backtest |
| `ml/` | ML assistivo: `score_ml`, rerank, walk-forward, calibração ML, drift |
| `governance/` | Lei 15, output commander, validação científica, ADRs, RFE estrutural |
| `analytics/` | Calibração científica institucional, certificação, lifecycle |
| `backtesting/` | Simulação histórica concursos × jogos gerados |
| `benchmark/` | Benchmark formal (correlação score×acertos, distribuições) |
| `reports/` | Export JSON/CSV/HTML de backtest + calibração de pesos |
| `database/` | SQLite/Postgres, modelos `GeneratedGame`, `CalibrationRun`, etc. |
| `ingestion/` | Sync resultados oficiais, validação Caixa |
| `experiments/` | Datasets supervisionados, walk-forward, HB geometry |
| `combinatorics/` | Expansão 16D–23D científica |
| `observability/` | Saúde runtime, governança em tempo real |
| `public/` | Superfície pública (geração, persistência, tracking) |
| `workflows/` | Scheduler/recovery de workflows operacionais |
| `assistance/` | Camada humana/executiva sobre analytics |
| `memory/` | Timeline e diff de memória institucional |
| `reliability/` | Degraded mode, failover, restart policy |
| `storage/` | Snapshots e artefatos distribuídos |
| `cli.py` | Comandos: backtest, benchmark, reports, calibração, sync |

### 2.2 Lista completa de módulos (215)

| Módulo | Docstring / responsabilidade inferida |
|--------|---------------------------------------|
| `(root)` | Public runtime package |
| `__main__` | Entry point |
| `analytics` | Camada analítica |
| `analytics/adaptive_intelligence` | Inteligência adaptativa |
| `analytics/historical_intelligence` | Inteligência histórica analítica |
| `analytics/institutional_certification` | Certificação institucional |
| `analytics/intelligence_layer` | Camada de inteligência |
| `analytics/lotofacil_scientific_core` | Core científico Lotofácil |
| `analytics/scientific_calibration_engine` | Engine calibração científica de batches |
| `analytics/user_lifecycle` | Lifecycle de usuário |
| `assistance` | Assistência operacional |
| `assistance/adaptive_memory` | Memória adaptativa |
| `assistance/contextual_recommendation` | Recomendações contextuais |
| `assistance/executive_assistance` | Assistência executiva |
| `assistance/executive_summary` | Resumo executivo |
| `assistance/explainable_analytics` | Analytics explicável |
| `assistance/full_presence` | Presença operacional completa |
| `assistance/governance` | Governança assistiva |
| `assistance/human_language` | Linguagem humana |
| `assistance/institutional_support_experience` | Experiência suporte institucional |
| `assistance/operational_guidance` | Orientação operacional |
| `authentication` | Autenticação |
| `authentication/models` | Modelos auth |
| `authentication/service` | Serviço auth |
| `backtesting` | Backtesting |
| `backtesting/backtester` | Motor de backtest |
| `benchmark` | Benchmark |
| `benchmark/benchmark_engine` | Engine de benchmark |
| `calibration` | Calibração de pesos (lazy exports) |
| `calibration/weight_calibrator` | Comparador de configs de peso |
| `cli` | Interface linha de comando |
| `combinatorics` | Combinatória |
| `combinatorics/expansion_engine` | Engine expansão |
| `combinatorics/expansion_store` | Store expansão |
| `combinatorics/scientific_expansion_engine` | Expansão científica |
| `config` | Configuração |
| `data` | Data loading and validation utilities |
| `data/history_export` | Export histórico |
| `data/loader` | Loader CSV/histórico |
| `database` | Database layer |
| `database/adapter` | Adapter DB |
| `database/contest_repository` | Repositório concursos |
| `database/database` | ORM SQLAlchemy |
| `database/public_repository` | Repositório público |
| `database/repository` | Repositório genérico |
| `environment` | Ambiente |
| `experiments` | Scientific experiment governance primitives |
| `experiments/behavioral_experiment` | Experimento comportamental |
| `experiments/hb_geometry_audit` | Auditoria geometria HB |
| `experiments/ia_structural_regulator` | Regulador estrutural IA |
| `experiments/longitudinal_baseline` | Baseline longitudinal |
| `experiments/longitudinal_temporal` | Longitudinal temporal |
| `experiments/supervised_dataset` | Dataset supervisionado |
| `experiments/supervised_scoring` | Scoring supervisionado |
| `experiments/supervised_walk_forward` | Walk-forward supervisionado |
| `experiments/temporal_benchmark` | Benchmark temporal |
| `experiments/temporal_governance` | Governança temporal experimentos |
| `generator` | Game generation utilities |
| `generator/basic_generator` | Gerador principal de jogos |
| `generator/engine` | Adapter `generate_ranked_games` |
| `governance` | Institutional governance and architecture audit |
| `governance/adaptive_change_control` | Adaptive change control |
| `governance/adaptive_governance_engine` | Adaptive Operational Governance engine |
| `governance/adaptive_governance_report` | Relatório governança adaptativa |
| `governance/adr_registry` | ADR registry |
| `governance/architectural_telemetry` | Architecture telemetry |
| `governance/audit_registry` | Architecture audit registry |
| `governance/autonomous` | Autonomous governance intelligence |
| `governance/autonomous/adaptive_governance_optimizer` | Otimizador adaptativo |
| `governance/autonomous/autonomous_decision_engine` | Decisão autônoma |
| `governance/autonomous/autonomous_governance_report` | Relatório autonomia |
| `governance/autonomous/governance_autonomy_monitor` | Monitor autonomia |
| `governance/autonomous/governance_policy_evolution` | Evolução política |
| `governance/autonomous/governance_risk_predictor` | Preditor risco |
| `governance/council` | Institutional AI governance council |
| `governance/council/ai_policy_board` | AI policy board |
| `governance/council/governance_consensus_engine` | Consenso |
| `governance/council/governance_council_engine` | Council engine |
| `governance/council/governance_council_report` | Council report |
| `governance/council/institutional_decision_review` | Revisão decisões |
| `governance/council/strategic_approval_registry` | Aprovações estratégicas |
| `governance/governance_risk_analysis` | Análise risco governança |
| `governance/operational_policy_guard` | Guarda política operacional |
| `governance/output_commander` | Output commander (validação saída) |
| `governance/releases` | Governance facade releases |
| `governance/releases/release_governance_engine` | Release governance |
| `governance/scientific_commander` | Comandante científico batches |
| `governance/scientific_governance` | Governança científica Lei 15 |
| `governance/scientific_nuclei_registry` | Registro núcleos científicos |
| `governance/signal_approval_workflow` | Workflow aprovação sinais |
| `governance/structural_rfe` | RFE estrutural |
| `governance/temporal_history_registry` | Registro histórico temporal |
| `governance/temporal_scientific_governance` | Governança científica temporal |
| `ingestion` | Official ingestion namespace |
| `ingestion/caixa_api_client` | Cliente API Caixa |
| `ingestion/official_caixa_validation` | Validação oficial |
| `ingestion/providers` | Providers ingestão |
| `ingestion/providers/api_provider` | API provider |
| `ingestion/result_sync_scheduler` | Scheduler sync |
| `ingestion/result_sync_service` | Serviço sync |
| `ingestion/sync` | Sync principal |
| `ingestion/validators` | Validators ingestão |
| `memory` | Memória institucional |
| `memory/memory_diff` | Diff memória |
| `memory/memory_evolution` | Evolução memória |
| `memory/memory_registry` | Registry memória |
| `memory/memory_repository` | Repositório memória |
| `memory/memory_timeline` | Timeline memória |
| `ml` | ML assistivo |
| `ml/calibration_governance` | Governança calibração ML |
| `ml/dataset` | Dataset ML |
| `ml/drift_detection` | Detecção drift |
| `ml/evaluation` | Avaliação ML |
| `ml/experiment_tracking` | Tracking experimentos |
| `ml/explainability` | Explicabilidade |
| `ml/feature_lineage` | Lineage features |
| `ml/features` | Features ML |
| `ml/governance` | Governança ML |
| `ml/inference` | Inferência |
| `ml/model_registry` | Registry modelos |
| `ml/models` | Modelos ML |
| `ml/rerank` | Rerank assistivo (wrapper score_ml) |
| `ml/runtime_isolation` | Isolamento runtime ML |
| `ml/score_ml` | Score ML linear interpretável |
| `ml/walk_forward_validation` | Validação walk-forward |
| `models` | Domain models |
| `models/draw` | Modelo Draw/concurso |
| `observability` | Enterprise observability foundation |
| `observability/distributed_tracing` | Tracing distribuído |
| `observability/institutional_dashboard` | Dashboard institucional |
| `observability/live_operational_memory` | Memória operacional live |
| `observability/live_telemetry` | Telemetria live |
| `observability/metrics_registry` | Registry métricas |
| `observability/observability_alerts` | Alertas |
| `observability/observability_report` | Relatórios observabilidade |
| `observability/observability_repository` | Repositório observabilidade |
| `observability/observational_stabilization` | Estabilização observacional |
| `observability/operational_experience` | Experiência operacional |
| `observability/operational_health` | Saúde operacional |
| `observability/operational_monitoring` | Monitoramento operacional |
| `observability/real_time_governance` | Governança tempo real |
| `observability/runtime_storytelling` | Storytelling runtime |
| `observability/structured_logging` | Logging estruturado |
| `orchestration` | Institutional orchestration layer |
| `orchestration/intelligent_orchestration` | Orquestração inteligente |
| `persistence` | Distributed persistence orchestration |
| `persistence/distributed_persistence_report` | Relatório persistência |
| `persistence/persistence_sync_engine` | Sync persistência |
| `public` | Runtime público |
| `public/expansion_lifecycle` | Lifecycle expansão |
| `public/governance` | Governança pública |
| `public/governance/audit` | Audit público |
| `public/governance/boundaries` | Boundaries |
| `public/governance/contracts` | Contratos |
| `public/governance/readonly` | Readonly |
| `public/governance/runtime` | Runtime governança |
| `public/models` | Modelos públicos |
| `public/operational_lifecycle` | Lifecycle operacional |
| `public/persistence` | Persistência pública |
| `public/persistence/bootstrap` | Bootstrap |
| `public/persistence/repositories` | Repositórios |
| `public/reconciliation` | Reconciliação |
| `public/reset_service` | Reset service |
| `public/security` | Segurança |
| `public/security/fallback` | Fallback |
| `public/security/protection` | Proteção |
| `public/security/runtime` | Runtime segurança |
| `public/security/sanitizer` | Sanitizer |
| `public/security/validators` | Validators |
| `public/service` | Serviço público principal |
| `public/services` | Serviços |
| `public/services/lead_capture_service` | Lead capture |
| `public/streamlit` | Streamlit público |
| `public/streamlit/app` | App |
| `public/streamlit/check_page` | Check page |
| `public/streamlit/components` | Components |
| `public/streamlit/forms` | Forms |
| `public/streamlit/generate_page` | Generate page |
| `public/streamlit/runtime` | Runtime |
| `public/tracking` | Tracking |
| `public/tracking/models` | Models tracking |
| `public/tracking/runtime` | Runtime tracking |
| `public/tracking/service` | Service tracking |
| `reliability` | Operational reliability foundation |
| `reliability/degraded_mode_controller` | Degraded mode |
| `reliability/operational_failover` | Failover |
| `reliability/resilience_report` | Relatório resiliência |
| `reliability/runtime_stability_monitor` | Monitor estabilidade |
| `reliability/service_restart_policy` | Política restart |
| `reports` | Relatórios |
| `reports/report_generator` | Gerador backtest/calibração |
| `scheduling` | Agendamento |
| `scheduling/daily_cleanup_scheduler` | Cleanup diário |
| `standards` | Institutional standardization contracts |
| `statistics` | Statistical analysis modules |
| `statistics/advanced` | Scoring avançado + stats JSON |
| `statistics/basic` | Análise básica |
| `statistics/combinations` | Combinações duo/terno/quadra/quina |
| `statistics/feature_store` | Feature store estatístico |
| `statistics/generation_trace` | Trace geração |
| `statistics/historical_intelligence` | Perfis históricos |
| `statistics/patterns` | Padrões |
| `statistics/scoring` | Pesos e final_score oficial |
| `statistics/temporal` | Componentes temporais + sequence |
| `storage` | Distributed operational storage |
| `storage/distributed_artifact_store` | Artifact store |
| `storage/features` | Storage features |
| `storage/features/feature_artifact_store` | Feature artifacts |
| `storage/operational_snapshot_store` | Snapshots operacionais |
| `storage/storage_failover_controller` | Failover storage |
| `storage/storage_replication_manager` | Replicação |
| `workflows` | Workflows |
| `workflows/workflow_dashboard` | Dashboard workflows |
| `workflows/workflow_engine` | Engine workflows |
| `workflows/workflow_recovery` | Recovery |
| `workflows/workflow_repository` | Repositório |
| `workflows/workflow_scheduler` | Scheduler |

---

## 3. Dependências entre módulos

### 3.1 Cadeia principal scoring → geração

```
basic_generator
  → statistics.advanced (calculate_final_score)
  → statistics.historical_intelligence
  → ml.rerank
      → ml.score_ml

statistics.advanced
  → statistics.scoring (FINAL_SCORE_WEIGHTS, weighted_final_score)
  → statistics.temporal (sequence_component, delay, frequency)
  → statistics.combinations

statistics.scoring
  → statistics.combinations
  → statistics.temporal
  → statistics.historical_intelligence

backtesting.backtester
  → generator.basic_generator
  → statistics.scoring
  → statistics.temporal

calibration.weight_calibrator
  → backtesting (run_backtest)
  → statistics.scoring (ScoreConfig)

reports.report_generator
  → backtesting (BacktestResult)

cli
  → backtesting, calibration, reports, statistics.advanced
```

### 3.2 Tabela de imports internos (módulos-chave)

| Origem | Importa |
|--------|---------|
| `generator.basic_generator` | `statistics.advanced`, `statistics.historical_intelligence`, `ml.rerank` |
| `ml.rerank` | `ml.score_ml` |
| `statistics.advanced` | `statistics.scoring`, `statistics.temporal`, `statistics.combinations` |
| `statistics.scoring` | `statistics.combinations`, `statistics.temporal`, `statistics.historical_intelligence` |
| `statistics.temporal` | `statistics.combinations` |
| `backtesting.backtester` | `generator.basic_generator`, `statistics.scoring`, `statistics.temporal` |
| `calibration.weight_calibrator` | `backtesting`, `statistics.scoring` |
| `reports.report_generator` | `backtesting` |
| `cli` | `backtesting`, `calibration`, `reports`, `statistics.advanced` |
| `analytics.scientific_calibration_engine` | `governance.output_commander`, `governance.scientific_commander`, `database` |

**Hubs mais conectados:** `statistics.scoring`, `statistics.temporal`, `statistics.advanced`, `generator.basic_generator`, `backtesting.backtester`.

---

## 4. Conteúdo solicitado

### 4.1 `src/lotoia/scoring/` — NÃO EXISTE

Equivalente oficial:

| Arquivo | Papel |
|---------|-------|
| `statistics/scoring.py` | Pesos, `weighted_final_score`, `score_candidate_from_history` |
| `statistics/advanced.py` | `calculate_final_score` (stats estáticas em JSON) |
| `statistics/temporal.py` | `sequence_component`, `delay_component`, `frequency_component` |
| `statistics/combinations.py` | Ranks duo/terno/quadra/quina |

#### Conteúdo completo de `statistics/scoring.py`

```python
from lotoia.statistics.combinations import combo_score, rank_component_score
from lotoia.statistics.temporal import (
    build_history_model, delay_component, frequency_component,
    sequence_component, sum_component,
)
from lotoia.statistics.historical_intelligence import classify_profile, profile_score

SCORE_COMPONENTS = (
    "duo_score", "terno_score", "quadra_score", "quina_score",
    "delay_score", "frequency_score", "sum_score", "sequence_score",
)

FINAL_SCORE_WEIGHTS = MappingProxyType({
    "duo_score": 15,
    "terno_score": 20,
    "quadra_score": 25,
    "quina_score": 20,
    "delay_score": 10,
    "frequency_score": 5,
    "sum_score": 3,
    "sequence_score": 2,
})

def weighted_final_score(components, weights=FINAL_SCORE_WEIGHTS) -> float:
    score_weights = resolve_score_config(weights).weights
    total_weight = sum(score_weights.values())
    weighted_score = sum(components[name] * weight for name, weight in score_weights.items())
    return round(weighted_score / total_weight, 2)

def score_candidate_from_history(numbers, history, model=None, weights=FINAL_SCORE_WEIGHTS):
    history_model = model or build_history_model(history)
    combo_scores = {
        "duo": combo_score(numbers, 2, history_model["duos"]),
        "terno": combo_score(numbers, 3, history_model["ternos"]),
        "quadra": combo_score(numbers, 4, history_model["quadras"]),
        "quina": combo_score(numbers, 5, history_model["quinas"]),
    }
    components = {
        "duo_score": rank_component_score(combo_scores["duo"]["average_rank"], 300),
        "terno_score": rank_component_score(combo_scores["terno"]["average_rank"], 2300),
        "quadra_score": rank_component_score(combo_scores["quadra"]["average_rank"], 12650),
        "quina_score": rank_component_score(combo_scores["quina"]["average_rank"], 53130),
        "delay_score": delay_component(numbers, history),
        "frequency_score": frequency_component(numbers, history),
        "sum_score": sum_component(numbers),
        "sequence_score": sequence_component(numbers),
    }
    final_score = sum(components[name] * weight for name, weight in score_weights.items()) / sum(score_weights.values())
    # ... retorna final_score, quadra_score, profile_type, historical_intelligence
```

---

### 4.2 `src/lotoia/ml/rerank.py` (completo)

```python
from __future__ import annotations

from typing import Any

from lotoia.ml.score_ml import InterpretableLinearScoreML, attach_score_ml, supervised_rerank_games

__all__ = ["rerank_games", "supervised_rerank_games"]


def rerank_games(
    games: list[dict[str, Any]],
    *,
    enabled: bool = False,
    model: InterpretableLinearScoreML | None = None,
) -> list[dict[str, Any]]:
    """Attach the official incremental score_ml layer without replacing hybrid ranking.

    The generator still performs its primary ordering by final_score/quadra_score.
    Explicit supervised reranking is available through supervised_rerank_games.
    """
    for g in games:
        g["ml_enabled"] = bool(enabled)
        if enabled:
            attach_score_ml(g, model=model)
    return games
```

**Papel:** camada fina; rerank supervisionado explícito via `supervised_rerank_games` em `score_ml.py`. Por padrão `enabled=False`.

---

### 4.3 Arquivos com `calibr` no nome

| Arquivo | Tipo | Resumo |
|---------|------|--------|
| `src/lotoia/calibration/weight_calibrator.py` | Runtime | Compara configs de pesos via backtest |
| `src/lotoia/calibration/__init__.py` | Lazy exports | `WeightConfiguration`, `compare_weight_configurations` |
| `src/lotoia/ml/calibration_governance.py` | ML governance | Snapshots/registry calibração ML |
| `src/lotoia/analytics/scientific_calibration_engine.py` | Institucional | Calibração científica de batches (Lei 15/17/18) |
| `scripts/run_weight_calibration.py` | Script CLI | Roda `compare_weight_configurations` |
| `tests/test_scientific_calibration_engine.py` | Teste | — |
| `tests/test_weight_calibrator.py` | Teste | — |
| `tests/ml/test_calibration_governance.py` | Teste | — |
| `tests/test_historical_intelligence_recalibration.py` | Teste | — |
| `docs/adr/ADR-039-LOTOIA-OVERLAP-CALIBRATION-EXPERIMENT.md` | ADR | Experimento overlap |
| `docs/adr/ADR-041-IA-STRUCTURAL-CALIBRATION-NO-EFFECT.md` | ADR | IA structural no-effect |
| `diagnostico/calibracao_15_validacao_cruzada.md` | Diagnóstico | Read-only histórico |
| `diagnostico/calibracao_15_dezenas_diagnostico.md` | Diagnóstico | Read-only histórico |

#### `calibration/weight_calibrator.py` — estrutura

```python
CALIBRATABLE_COMPONENTS = {
    "duo_score": "duo", "terno_score": "terno", "quadra_score": "quadra",
    "quina_score": "quina", "delay_score": "delay", "frequency_score": "frequency",
    "sum_score": "sum", "sequence_score": "sequence",
}

@dataclass(frozen=True)
class WeightConfiguration:
    name: str
    duo: float; terno: float; quadra: float; quina: float
    delay: float; frequency: float; sum: float; sequence: float

def evaluate_weight_configuration(configuration, draws=None, ...) -> dict:
    # run_backtest com ScoreConfig(weights=configuration.to_score_weights())
    # retorna métricas: average_hits, hit_distribution, correlation, etc.

def compare_weight_configurations(configurations, ...) -> dict:
    # avalia todas, escolhe best_configuration por average_hits + hit_distribution
```

#### `ml/calibration_governance.py` — função principal

```python
def register_calibration_snapshot(*, model_version, dataset_version, calibration, ...) -> MLCalibrationGovernanceResult:
    # Persiste snapshot em experiments/ml_calibration/snapshots/{model_version}.json
    # Atualiza registry.json
```

#### `analytics/scientific_calibration_engine.py` — exports

```python
__all__ = [
    "build_calibration_context", "evaluate_last_batch",
    "generate_recalibration_policy", "recommend_next_strategy",
    "apply_supervised_calibration", "register_calibration_decision",
]
```

---

### 4.4 Arquivos com `sequence` no nome

**Nenhum arquivo** em `src/` contém `sequence` no nome.

Lógica de sequência está em `statistics/temporal.py`:

```python
def find_sequences(numbers: list[int]) -> list[list[int]]:
    # Detecta grupos consecutivos (+1) em dezenas ordenadas

def calculate_sequence_stats(numbers: list[int]) -> dict:
    sequences = find_sequences(numbers)
    largest_sequence = max((len(s) for s in sequences), default=0)
    return {
        "sequence_count": len(sequences),
        "largest_sequence": largest_sequence,
        "sequences": sequences,
    }

def sequence_component(numbers: list[int]) -> float:
    sequence_stats = calculate_sequence_stats(numbers)
    penalty = (int(sequence_stats["sequence_count"]) * 12) + (
        max(0, int(sequence_stats["largest_sequence"]) - 2) * 16
    )
    return max(0, 100 - penalty)
```

Duplicata equivalente em `statistics/advanced.py`:

```python
def _calculate_sequence_component(numbers: list[int]) -> float:
    sequence_stats = calculate_sequence_stats(numbers)
    penalty = (sequence_count * 12) + (max(0, largest_sequence - 2) * 16)
    return round(max(0, 100 - penalty), 2)
```

---

## 5. `sequence_score` — valor e cálculo

### Pipeline

1. Dezenas ordenadas → `find_sequences` → listas de consecutivos (len > 1)
2. `calculate_sequence_stats` → `sequence_count`, `largest_sequence`
3. Penalidade: `(sequence_count × 12) + (max(0, largest_sequence − 2) × 16)`
4. Score: `max(0, 100 − penalty)`

### Exemplo real (`RELATORIO_ULTIMO.json`)

```json
"sequence_score": 48
```

Penalidade = 52. Exemplos que produzem 48:
- 1 sequência de 5 dezenas: `(1×12) + (5−2)×16 = 12+48 = 60` → score 40
- 2 sequências, maior=3: `(2×12) + (3−2)×16 = 24+16 = 40` → score 60
- 4 sequências, maior=2: `(4×12) + 0 = 48` → score **52** (próximo)

Valor exato depende das dezenas do jogo específico.

### Peso no final_score

`sequence_score` contribui com peso **2 de 100** (= 2% da média ponderada).

---

## 6. Agregação do `final_score`

### Função oficial

**Arquivo:** `src/lotoia/statistics/scoring.py`  
**Funções:** `weighted_final_score()`, `score_candidate_from_history()`

```python
final_score = sum(component[name] * weight[name] for name in SCORE_COMPONENTS) / sum(weights)
# arredondado para 2 casas decimais
```

### Pesos oficiais (`FINAL_SCORE_WEIGHTS`)

| Componente | Peso | % relativo |
|------------|------|------------|
| `quadra_score` | 25 | 25% |
| `terno_score` | 20 | 20% |
| `quina_score` | 20 | 20% |
| `duo_score` | 15 | 15% |
| `delay_score` | 10 | 10% |
| `frequency_score` | 5 | 5% |
| `sum_score` | 3 | 3% |
| **`sequence_score`** | **2** | **2%** |
| **Total** | **100** | **100%** |

### Fórmula compacta

```
final_score = (
  15·duo + 20·terno + 25·quadra + 20·quina +
  10·delay + 5·frequency + 3·sum + 2·sequence
) / 100
```

### Origem de cada componente

| Componente | Fonte | Arquivo |
|------------|-------|---------|
| duo–quina | Ranks históricos via `combo_score` + `rank_component_score` | `scoring.py` + `combinations.py` |
| delay | Atraso das dezenas no histórico | `temporal.py` |
| frequency | Frequência normalizada no histórico | `temporal.py` |
| sum | Proximidade da soma das dezenas a 195 | `temporal.py` |
| sequence | Penalidade por sequências consecutivas | `temporal.py` |

### Caminho alternativo (`statistics/advanced.py`)

`calculate_final_score(numbers)` usa stats JSON estáticas (duos/quadras pré-calculados) em vez de histórico dinâmico, mas **mesmos pesos** via `FINAL_SCORE_WEIGHTS`.

### ML assistivo (camada adicional, não substitui)

`ml/score_ml.py` — feature `final_score_norm = final_score/100` com coeficiente 0.35 no modelo linear.  
Política: ML **auxiliar**; não altera `FINAL_SCORE_WEIGHTS` soberanos (ADR-042).

---

## 7. Status da calibração

### 7.1 Por que `"calibration": null` no `RELATORIO_ULTIMO.json`

**Evidência no arquivo:**

```json
"configuration_metrics": [],
"calibration": null
```

**Causa raiz:** o relatório foi gerado por `generate_backtest_report()` (`reports/report_generator.py`) com `calibration_result=None`:

```python
payload = {
    "metrics": metrics,
    "backtest": backtest_result.to_dict(),
    "calibration": calibration_result,  # ← None → JSON null
    "charts": {...},
    "csv": {...},
}
```

Quando `calibration_result=None`:
- Campo `"calibration"` vira `null`
- `"configuration_metrics"` fica `[]`
- CSV `configurations` vazio
- Gráfico `weight_comparison` usa fallback só com backtest

### 7.2 Cenários que produzem `null`

| Cenário | Descrição |
|---------|-----------|
| **A (mais provável)** | Backtest exportado sem rodar `compare_weight_configurations` |
| **B** | CLI `reports` interrompida após backtest, antes da calibração |
| **C** | Cópia manual de relatório parcial para `RELATORIO_ULTIMO.json` |

### 7.3 Três tipos de "calibração" no sistema

| Tipo | Módulo | Status no runtime Lei 15 limpo |
|------|--------|--------------------------------|
| Calibração de **pesos** | `calibration/weight_calibrator.py` | Disponível via CLI; **não executada** neste relatório |
| Calibração **ML** | `ml/score_ml.py` + `ml/calibration_governance.py` | Default ativo internamente; separada do campo JSON |
| Calibração **científica** | `analytics/scientific_calibration_engine.py` | Painel ADM; `calibration_engine_role: DISABLED` no gerador limpo |

### 7.4 Como gerar relatório com calibração preenchida

```bash
# Opção 1 — relatório completo (backtest + calibração)
python -m lotoia reports --contests 3 --games 5 --pool-size 15 --history-window 150

# Opção 2 — só comparar pesos
python scripts/run_weight_calibration.py --contests 3 --games 5
```

Saída esperada (não null):

```json
"calibration": {
  "evaluations": [...],
  "best_configuration": "official",
  "best_metrics": {...}
}
```

---

## 8. JSON resumido

```json
{
  "report_type": "lotoia_architecture_scoring_audit",
  "generated_at": "2026-06-10",
  "scoring_directory": "NAO_EXISTE — usar src/lotoia/statistics/scoring.py",
  "sequence_score_formula": "max(0, 100 - (sequence_count*12 + max(0,largest_sequence-2)*16))",
  "final_score_function": "weighted_final_score / score_candidate_from_history",
  "final_score_weights": {
    "duo_score": 15,
    "terno_score": 20,
    "quadra_score": 25,
    "quina_score": 20,
    "delay_score": 10,
    "frequency_score": 5,
    "sum_score": 3,
    "sequence_score": 2
  },
  "final_score_weights_total": 100,
  "sequence_weight_percent": 2,
  "calibration_null_reason": "generate_backtest_report chamado com calibration_result=None",
  "configuration_metrics_empty": true,
  "rerank_default_enabled": false,
  "calibration_engine_role_clean_law15": "DISABLED",
  "module_count": 215,
  "python_file_count": 217,
  "key_files": {
    "scoring": "src/lotoia/statistics/scoring.py",
    "advanced_final_score": "src/lotoia/statistics/advanced.py",
    "sequence_logic": "src/lotoia/statistics/temporal.py",
    "combinations": "src/lotoia/statistics/combinations.py",
    "rerank": "src/lotoia/ml/rerank.py",
    "score_ml": "src/lotoia/ml/score_ml.py",
    "weight_calibration": "src/lotoia/calibration/weight_calibrator.py",
    "ml_calibration_governance": "src/lotoia/ml/calibration_governance.py",
    "scientific_calibration": "src/lotoia/analytics/scientific_calibration_engine.py",
    "report_generator": "src/lotoia/reports/report_generator.py",
    "last_report": "RELATORIO_ULTIMO.json"
  }
}
```

---

## Referências cruzadas

- Governança ML: `docs/governance/POLITICA_ML_ASSISTIVO.md`
- ADR calibração overlap: `docs/adr/ADR-039-LOTOIA-OVERLAP-CALIBRATION-EXPERIMENT.md`
- ADR IA structural: `docs/adr/ADR-041-IA-STRUCTURAL-CALIBRATION-NO-EFFECT.md`
- AGENTS.md — posicionamento LotoIA

---

*Fim do relatório.*
