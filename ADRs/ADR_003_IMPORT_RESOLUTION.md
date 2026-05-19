# ADR 003 - Governança de Resolução de Imports

## Status
Aceito

---

## Contexto

A auditoria estrutural do projeto identificou risco real de resolução ambígua de imports entre:

- src/lotoia
- lotoia/

Foi comprovado que:
- o comportamento do sistema varia conforme:
  - ambiente Python;
  - editable install;
  - PYTHONPATH;
  - diretório de execução.

---

## Diagnóstico Técnico

A auditoria confirmou que:

- src/lotoia é o namespace oficial do projeto;
- o ambiente .venv resolve corretamente os imports;
- o Python global pode resolver o namespace paralelo lotoia/;
- o sistema atualmente depende implicitamente de:
  - pip install -e .
  - ambiente virtual ativo
  - cwd correto
  - sys.path configurado corretamente

---

## Risco Científico Identificado

Foi identificado risco crítico no módulo:

```text
lotoia.ml.rerank