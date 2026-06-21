# M-OPS-283 — Conferir approved_with_warning

Correção necessária:

- lotes `approved_with_warning` devem ser conferíveis;
- lotes `pending_structural_review` continuam bloqueados;
- grupos recebidos pelo painel podem trazer status em `context_json`, `lot_operational_status`, `operational_status`, `officialization_status` ou `post_calibration_promotion_status`.

Patch alvo:

- `src/lotoia/operations/lot_operational_status.py`
- `dashboard/institutional_app.py` caso `_is_group_conference_selectable` gateie apenas por `is_official_conference_eligible`.
