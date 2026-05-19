# ADR 004 - Consolidação do Rerank Supervisionado

## Status
Aceito

---

## Contexto

A auditoria estrutural do projeto identificou duplicidade funcional entre:

- lotoia/ml/rerank.py
- src/lotoia/ml/rerank.py

Foi confirmado que:
- o ambiente .venv resolve corretamente para src/lotoia/ml/rerank.py;
- o Python global pode resolver para lotoia/ml/rerank.py;
- existem diferenças comportamentais entre os módulos;
- e o dashboard depende do campo ml_enabled presente apenas na implementação oficial em src.

Também foi identificado que:
- o benchmark principal ainda não depende diretamente do rerank;
- o rerank atual atua apenas como placeholder incremental;
- não existe score_ml implementado;
- não existe benchmark supervisionado formal;
- não existe walk-forward validation do rerank.

---

## Diagnóstico Técnico

### Implementação Paralela

A implementação em:

```text
lotoia/ml/rerank.py