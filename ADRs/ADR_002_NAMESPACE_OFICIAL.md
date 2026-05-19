# ADR 002 - Namespace Oficial do Projeto

## Status
Aceito

---

## Contexto

A auditoria arquitetural consolidada do projeto identificou a existência de múltiplos espaços estruturais relacionados ao domínio principal do sistema.

Foi identificado que:
- o pacote oficial configurado no pyproject.toml utiliza:
  - where = ["src"]
- o namespace principal instalado e utilizado pela aplicação é:
  - src/lotoia

Também foi identificado que coexistem estruturas paralelas:
- lotoia/
- src/database
- src/statistics
- src/ingestion

Essas estruturas:
- não representam o namespace oficial do sistema;
- possuem risco de redundância;
- podem gerar conflitos de import;
- e aumentam risco de ambiguidade arquitetural.

---

## Decisão

O LotoIA adota oficialmente:

```text
src/lotoia