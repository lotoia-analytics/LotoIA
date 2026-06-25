# LotoIA

Sistema profissional em Python para análise estatística estrutural da LOTOFACIL com geração de jogos, conferência automatizada e calibração ML.

## Visão Geral

O LotoIA é uma plataforma estatística institucional que combina:

- **Geração Estrutural CORE_002**: Pipeline de 5 camadas com políticas anti-viés
- **Conferência Automatizada**: Backtesting contra concursos oficiais da Caixa
- **Calibração ML**: Machine Learning como sensor observacional (não bloqueante)
- **Dashboard Institucional**: Interface Streamlit para operação e análise
- **API HTTP**: FastAPI para integração e automação
- **Feedback Loop**: Aprendizado contínuo pós-concurso

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    CORE_002 SOVEREIGN PIPELINE              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ENTRADA: formato (15D-23D) + quantidade + batch_label     │
│           ↓                                                 │
│  ┌────────────────────────────────────────────────────┐   │
│  │ L1: generation_cand_d                              │   │
│  │   - build_candidate_pool() (CAND-D N-C1..N-C6)    │   │
│  │   - apply_critical_digit_layer() (07/12/23)       │   │
│  └────────────────────────────────────────────────────┘   │
│           ↓                                                 │
│  ┌────────────────────────────────────────────────────┐   │
│  │ M-ML-072: Pool Estrutural 15D                      │   │
│  │   - build_ml_structural_15d_pool()                │   │
│  │   - calibration_plan integration                  │   │
│  └────────────────────────────────────────────────────┘   │
│           ↓                                                 │
│  ┌────────────────────────────────────────────────────┐   │
│  │ M-STAT-002: Seleção DiverSa (v5)                   │   │
│  │   - prefix_cap: 21% (triplet 01-02-03)            │   │
│  │   - suffix_cap: 21% (sufixo 23-24-25)             │   │
│  │   - anti-clone overlap                            │   │
│  │   - family diversity                              │   │
│  └────────────────────────────────────────────────────┘   │
│           ↓                                                 │
│  ┌────────────────────────────────────────────────────┐   │
│  │ L2: v1_selection_compose + M-CORE-003              │   │
│  │   - pre_filter_pool_diversity()                   │   │
│  │   - compose_diverse_gp() (V1)                     │   │
│  │   - enforce_gp_diversity_cap() (M-CORE-003)       │   │
│  └────────────────────────────────────────────────────┘   │
│           ↓                                                 │
│  ┌────────────────────────────────────────────────────┐   │
│  │ L4: anti_clone_gp                                  │   │
│  │   - overlap control (max 10)                      │   │
│  │   - architecture limit (max 12%)                  │   │
│  │   - V1-strong exception                           │   │
│  └────────────────────────────────────────────────────┘   │
│           ↓                                                 │
│  ┌────────────────────────────────────────────────────┐   │
│  │ L5: critical_digit_layer                           │   │
│  │   - reforço suave (07/12/23)                      │   │
│  │   - penalização contextual (11/15/24/25)          │   │
│  └────────────────────────────────────────────────────┘   │
│           ↓                                                 │
│  SAÍDA: GP final com metadados soberanos                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Estrutura do Projeto

```text
LotoIA/
├── backend/              API FastAPI (endpoints HTTP)
├── dashboard/            Interface Streamlit institucional
├── data/                 Dados brutos, processados e externos
├── docs/                 Documentação técnica
│   ├── adr/              Architecture Decision Records
│   ├── architecture/     Diagramas e políticas
│   ├── governance/       Políticas de governança
│   └── ops/              Operações e deploy
├── notebooks/            Estudos exploratórios (Jupyter)
├── reports/              Relatórios gerados
├── scripts/              Utilitários de linha de comando
│   ├── checks/           Scripts de verificação
│   └── ops/              Scripts operacionais
├── src/lotoia/           Pacote principal
│   ├── config/           Configuração centralizada
│   ├── generation/       Motor de geração CORE_002
│   ├── governance/       Políticas e ADRs
│   ├── ml/               Calibração ML (observacional)
│   ├── statistics/       Métricas e validação
│   └── operations/       Operações institucionais
└── tests/                Testes automatizados
```

## Requisitos

- Python 3.11 ou superior
- PostgreSQL 14+ (produção no Railway)
- Dependências listadas em `requirements.txt`

## Instalação

### Ambiente Virtual

```bash
# Linux/Mac
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Variáveis de Ambiente

```bash
# Copiar template
cp .env.example .env

# Editar .env com suas configurações
# DATABASE_URL, API keys, etc.
```

## Execução

### API (FastAPI)

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Acesse: http://localhost:8000/docs

### Dashboard (Streamlit)

```bash
streamlit run dashboard/institutional_app.py --server.port 8501
```

Acesse: http://localhost:8501

### Geração de Jogos

```python
from lotoia.generator.basic_generator import generate_best_games

# Gerar 50 jogos 15D via CORE_002
result = generate_best_games(
    count=50,
    pool_size=150,
    batch_label="STRUCT_LEI15_CORE_CANDIDATE_002_15D_001"
)

print(f"Jogos gerados: {result['count']}")
print(f"Métricas: {result.get('structural_metrics', {})}")
```

### Conferência

```python
from lotoia.public.reconciliation import reconcile_games

# Conferir jogos contra concurso oficial
result = reconcile_games(
    generation_event_id=123,
    official_contest_number=3718
)
```

## Testes

```bash
# Todos os testes
pytest

# Testes específicos
pytest tests/generation/test_structural_metrics.py -v

# Com cobertura
pytest --cov=src/lotoia --cov-report=html
```

## Configuração Centralizada

As políticas estruturais estão centralizadas em `src/lotoia/config/structural_policy_config.py`:

```python
from lotoia.config.structural_policy_config import (
    MAX_PREFIX_SUFFIX_SHARE,      # 0.21 (21%)
    DEFAULT_PREFIX_SHARE_LIMIT,   # 0.21 (21%)
    HISTORICAL_WINDOW,            # 300 concursos
    CRITICAL_DIGITS,              # {7, 12, 23}
)
```

## Métricas Estruturais

O sistema valida automaticamente as métricas pós-geração:

| Métrica | Mínimo | Target | Máximo |
|---------|--------|--------|--------|
| Triplet 01-02-03 | 10% | 21% | 35% |
| Suffix 23-24-25 | 10% | 21.67% | 35% |
| Overlap médio | 7.0 | 10.0 | 13.0 |
| Diversity score | 0.70 | 0.78 | 1.00 |

Violações geram logs ERROR e são persistidas no `context_json`.

## Status Operacional

- **Núcleo Soberano**: `NUCLEO_SOBERANO_LEI15` (ativo)
- **Geração**: Habilitada por padrão
- **Lei 15A**: Bloqueada (requer ordem institucional)
- **Core Legado**: Congelado (read-only)
- **Endpoints Públicos**: Bloqueados (ADR-047)
- **Dashboard ADM**: Único caminho autorizado

## Estatísticas do Sistema

- **6.353** jogos gerados em 143 generation events
- **81** concursos reconciliados com backtesting
- **8** JACKPOTS (15 acertos) identificados
- **300** concursos oficiais como baseline
- **67%** cobertura de reconciliação

## Documentação

- [CHANGELOG.md](CHANGELOG.md) - Histórico de mudanças
- [docs/architecture/](docs/architecture/) - Diagramas e políticas
- [docs/governance/](docs/governance/) - Políticas de governança
- [docs/adr/](docs/adr/) - Architecture Decision Records
- [AGENTS.md](AGENTS.md) - Governança arquitetural

## Aviso Legal

Este projeto é destinado a análise estatística e estudo de dados. Ele não garante resultados em sorteios futuros. A Lotofácil é um jogo de azar e os resultados são aleatórios.

## Licença

Projeto privado - Todos os direitos reservados.

## Contato

Para questões técnicas e operacionais, consulte a documentação interna ou entre em contato com a equipe de desenvolvimento.
