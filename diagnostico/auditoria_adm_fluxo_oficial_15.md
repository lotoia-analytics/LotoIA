# Auditoria Formal ADM G10/G20/G30/G50

Data da auditoria: 2026-06-04

## Objetivo

Documentar a trilha completa do fluxo do painel ADM para os grupos oficiais de 15 dezenas, com foco em identificar por que o pacote podia sair truncado antes do `OutputCommander`.

## Fluxo auditado

1. `selectbox` de quantidade oficial
   - Chave: `institutional_total_games`
   - Valores permitidos: `10`, `20`, `30`, `50`
   - Valor visual e valor de estado ficam alinhados pela mesma chave de `session_state`.

2. `session_state`
   - `institutional_total_games` define `selected_quantity`
   - `institutional_official_15_group` é derivado de `OFFICIAL_15_QUANTITY_TO_GROUP`
   - Mapeamento oficial:
     - `10 -> G10`
     - `20 -> G20`
     - `30 -> G30`
     - `50 -> G50`

3. Materialização
   - Função principal: `_run_institutional_generation(...)`
   - Caminho oficial: `_official_15_group_games_for_quantity(total_games)`
   - Contexto oficial: `_official_15_generation_context(...)`
   - Modo declarado:
     - `generation_mode = OFFICIAL_GROUP_MATERIALIZATION`
     - `policy_mode = OFFICIAL_GROUP_MATERIALIZATION`
     - `historical_deduplication_mode = AUDIT_ONLY`

4. `OutputCommander`
   - Função: `output_commander_validate_games(...)`
   - Parâmetros relevantes:
     - `target_size=15`
     - `required_total=total_games`
     - `candidate_total=total_games`
     - `historical_deduplication_mode="AUDIT_ONLY"` no modo oficial
   - Comportamento:
     - valida quantidade de dezenas por jogo
     - valida duplicidade interna
     - audita duplicidade histórica sem derrubar o pacote oficial em `AUDIT_ONLY`

5. Persistência
   - Snapshot institucional gravado via `_persist_generation_snapshot(...)`
   - `InstitutionalOutputSignature` persiste as assinaturas aprovadas
   - O estado final também é salvo em `session_state`:
     - `institutional_generation`
     - `institutional_generation_result`
     - `institutional_generation_batch_result`

## Causa confirmada do truncamento

A causa encontrada foi anterior ao `OutputCommander`.

No fluxo oficial de 15 dezenas, o painel ainda montava:

`used_signatures = set(load_all_output_signatures())`

Isso fazia a materialização oficial comparar o lote inteiro contra o histórico completo antes da auditoria final. Como consequência, jogos já existentes no banco eram removidos antes de chegarem ao `OutputCommander`, e o pacote podia cair de 30 para 19.

## Correção aplicada

Foi aplicado ajuste mínimo no caminho oficial:

- em modo oficial com pacote fechado, `used_signatures` não usa o histórico inteiro como filtro de corte;
- a deduplicação histórica permanece em modo de auditoria;
- o `OutputCommander` continua como guardião final sem ser afrouxado.

## Estado esperado após a correção

- `selected_quantity_from_ui == selected_quantity_from_state`
- `selected_group_from_ui == selected_group_from_state`
- `official_package_size_loaded == requested_games`
- `official_package_size_before_output_commander == requested_games`
- `official_package_size_after_output_commander == requested_games`
- `output_commander_status == APROVADO`

## Observação operacional

O painel ainda mostra blocos de diagnóstico histórico e trilha técnica porque isso é útil para auditoria operacional. O importante é que esses blocos agora mostram o pacote oficial preservado, e não um pacote truncado por filtro histórico antecipado.
