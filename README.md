# LotoIA

Sistema profissional em Python para organizar dados, executar analises estatisticas e disponibilizar insights sobre a LOTOFACIL.

## Objetivo

O LotoIA fornece uma base inicial para:

- importar e validar resultados historicos;
- calcular frequencias, atrasos, pares, impares e distribuicoes;
- expor analises por API;
- visualizar indicadores em dashboard;
- evoluir para modelos preditivos e simulacoes.

## Estrutura

```text
LotoIA/
  backend/              API e servicos HTTP
  dashboard/            Interface Streamlit
  data/                 Dados brutos, processados e externos
  docs/                 Documentacao tecnica
  notebooks/            Estudos exploratorios
  reports/              Relatorios gerados
  scripts/              Utilitarios de linha de comando
  src/lotoia/           Pacote principal do sistema
  tests/                Testes automatizados
```

## Ambiente

Requisitos:

- Python 3.11 ou superior

Criar e ativar ambiente virtual no Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copiar variaveis de ambiente:

```powershell
Copy-Item .env.example .env
```

## Execucao

API:

```powershell
uvicorn backend.main:app --reload
```

Dashboard:

```powershell
streamlit run dashboard/app.py
```

Analise inicial via script:

```powershell
python scripts/run_basic_analysis.py
```

Testes:

```powershell
pytest
```

## Status

Esta e a estrutura inicial do projeto. As rotinas estatisticas estao preparadas para receber dados historicos em `data/raw/`.

## Aviso

Este projeto e destinado a analise estatistica e estudo de dados. Ele nao garante resultados em sorteios futuros.
