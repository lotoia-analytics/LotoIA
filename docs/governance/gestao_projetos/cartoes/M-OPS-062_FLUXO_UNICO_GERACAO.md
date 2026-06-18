# M-OPS-062 — Fluxo Único de Geração com Validação Estrutural

## Status

**CONCLUÍDA** — Gerador e Simulação usam CORE_002 + ML; oficialização só após Cobertura + Central ML.

## Build marker

`institutional-adm-runtime-v44`

## Fluxo

```
Gerador / Simulação (mesmo motor)
  → persistência PostgreSQL (context_json)
  → Cobertura Estrutural (lotes ativos)
  → Central ML (veredito)
  → oficialização / bloqueio
```

## Status operacionais (`context_json`)

- `pending_structural_review` (via trace)
- `officialized` / `approved_with_warning` / `approved_for_officialization`
- `needs_calibration` / `rejected` / `blocked_for_officialization`
- `calibration_source_only` / `not_officialized` (simulação)
- `superseded_by_calibration`

## Regras

| Tela | Comportamento |
|------|---------------|
| Gerador | Motor único; status persistido; bloqueio se veredito crítico |
| Simular Resultados | Mesmo motor; **não oficializa**; compara até 50 concursos |
| Conferir Resultados | Último concurso × todas gerações oficializadas; exibe 11+ |
| Cobertura Estrutural | Leitura ativa exclui reprovados/superseded |
| Histórico Analítico | Apenas lotes oficializados/aprovados |

## Módulos

- `src/lotoia/operations/lot_operational_status.py`
- Integração: `institutional_app.py`, `card_structure_diagnostics.py`
