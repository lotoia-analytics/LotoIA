# Auditoria de Encaixe Técnico do Protocolo Estrutural

## 1. Onde a Lei 15 forma o núcleo

O núcleo de 15 dezenas é montado dentro de `dashboard/institutional_app.py`, no fluxo de geração institucional.

Pontos principais observados:

- `_generate_direct_15_games(...)`
- `_run_institutional_generation(...)`
- `_select_subset_from_candidate(...)`
- `_force_subset_from_universe(...)`

O fluxo seleciona candidatos, reduz para `target_size=15` e constrói o conjunto final de dezenas antes de qualquer persistência.

Na rotina de persistência, o núcleo já entra normalizado no contexto do jogo:

- `core_numbers`
- `display_core_numbers`
- `quantidade_nucleo = 15`

Conclusão:

- a Lei 15 forma o núcleo no estágio de montagem do jogo;
- não há evidência de outra camada substituindo esse núcleo antes da composição final.

## 2. Onde as reservas auditadas são adicionadas

As reservas auditadas aparecem no módulo de geração/expansão da interface institucional, principalmente no fluxo de cartões 17D e 18D.

Pontos observados:

- `_expand_generation_games_for_format(...)`
- `_persist_generation_snapshot(...)`
- `dashboard/institutional_app.py` nas rotinas de exibição e persistência

Os campos associados são:

- `audited_reserve_numbers`
- `display_audited_reserve_numbers`
- `quantidade_reservas`

Conclusão:

- as reservas auditadas entram depois do núcleo Lei 15, como composição de formato;
- não substituem o núcleo;
- são parte do cartão final, não da verdade soberana da Lei 15.

## 3. Onde o cartão final é montado

O cartão final é consolidado no fluxo de persistência e no material de visualização pós-geração.

Pontos observados:

- `_persist_generation_snapshot(...)`
- `GeneratedGame(... context_json={...})`
- campos:
  - `final_card_numbers`
  - `display_final_card_numbers`
  - `quantidade_final`

No desenho atual, o cartão final é produzido após a seleção do núcleo e da composição de reservas.

Conclusão:

- o cartão final é montado depois da formação do núcleo e da eventual adição de reservas auditadas;
- a persistência grava o cartão já consolidado.

## 4. Onde a validação estrutural futura deve entrar

A validação estrutural futura não está implementada como RFE explícita no fluxo atual.

O ponto técnico mais adequado para encaixe é entre a montagem do candidato e a aceitação pelo OutputCommander, isto é:

1. depois de formar o núcleo e o cartão final;
2. antes de registrar a assinatura e aceitar a bateria;
3. antes de persistir o jogo como válido.

Por que esse ponto:

- a RFE precisa avaliar o cartão já formado;
- não deve interferir na montagem do núcleo como regra concorrente;
- precisa atuar antes da aceitação final para impedir persistência indevida.

Conclusão:

- a RFE deve entrar depois da composição do cartão final e antes da aceitação/persistência;
- ela deve validar o cartão final, não apenas o núcleo isolado.

## 5. Onde a Lei 16 atua hoje

A Lei 16 aparece hoje como unicidade global da bateria, principalmente por meio da assinatura normalizada e do bloqueio de duplicidade.

Pontos observados:

- `src/lotoia/governance/output_commander.py`
  - `game_signature(...)`
  - `output_commander_validate_games(...)`
- `dashboard/institutional_app.py`
  - `seen_signatures`
  - `used_signatures`
  - `batch_seen_signatures`
- persistência:
  - `InstitutionalOutputSignature`
  - índice único por `batch_id + game_signature`

Comportamento atual:

- a assinatura normalizada é calculada por jogo;
- duplicatas dentro do lote/bateria são rejeitadas;
- `output_commander_validate_games(...)` bloqueia se houver duplicidade;
- a persistência de assinatura reforça a unicidade.

Conclusão:

- a Lei 16 está operando hoje como camada de integridade global baseada em assinatura;
- ela atua depois da geração do jogo e antes da persistência final da assinatura;
- isso está alinhado com unicidade global da bateria.

## 6. Onde o jogo é aceito

A aceitação formal do jogo acontece no `OutputCommander`.

Ponto principal:

- `src/lotoia/governance/output_commander.py::output_commander_validate_games(...)`

Condições observadas:

- jogo válido individualmente;
- sem duplicidade interna;
- sem conflito histórico quando o modo de deduplicação não for `AUDIT_ONLY`;
- `approved_total == requested_total`;
- ausência de `blocked_reasons`.

Se houver falha, o retorno vem com:

- `status_comandante_saida = "BLOQUEADO"`
- `blocked_reason`
- `invalid_games`
- `accepted_games`

Conclusão:

- a aceitação acontece no OutputCommander, não na persistência;
- a persistência depende da aprovação já resolvida.

## 7. Onde o jogo é persistido

A persistência ocorre após a aceitação, na rotina de snapshot e gravação operacional.

Pontos observados:

- `_persist_generation_snapshot(...)`
- `register_output_signatures(...)`
- `register_output_signatures` grava `InstitutionalOutputSignature`
- `GeneratedGame(...)` e `GenerationEvent(...)` recebem os jogos já aceitos

O fluxo de escrita indica:

1. gerar candidatos;
2. validar/aceitar;
3. persistir eventos e jogos;
4. registrar assinaturas.

Conclusão:

- a persistência acontece depois da aceitação;
- não foi encontrado caminho explícito que persista jogo antes da validação formal do comando.

## 8. Riscos encontrados

1. A RFE ainda não existe como etapa formal no fluxo.
2. A Lei 16 está materializada como unicidade por assinatura no `OutputCommander` e na persistência, mas não como uma etapa separada e nomeada no pipeline da geração.
3. Há duas camadas de deduplicação:
   - interna da bateria (`seen_signatures`, `used_signatures`)
   - histórica (`load_all_output_signatures`, `historical_deduplication_mode`)
4. O fluxo de geração institucional usa vários caminhos de fallback para completar lotes, então a futura RFE precisará ser encaixada em todos os pontos de aceitação para evitar bypass.
5. O arquivo `dashboard/institutional_app.py` concentra geração, validação, persistência e exibição, então a implementação futura da RFE precisa ser cuidadosamente isolada.

## 9. Pontos proibidos de alteração

Nesta auditoria não devem ser alterados:

- Lei 15;
- Lei 16;
- geração;
- reservas auditadas;
- persistência;
- OutputCommander;
- schemas;
- queries;
- rotas;
- endpoints;
- mútua deduplicação global;
- módulos observacionais Vazamento Lateral e Evolução 13/14/15;
- regras de banca;
- regras de premiação por canal.

## 10. Recomendação para implementação futura das RFE

Recomendação técnica:

1. Inserir a RFE no pipeline institucional de geração depois da composição do cartão final.
2. Executá-la antes de `output_commander_validate_games(...)` ou como etapa obrigatória imediatamente anterior à aceitação.
3. Fazer a RFE atuar sobre o cartão completo, não apenas sobre o núcleo de 15 dezenas.
4. Garantir que qualquer falha da RFE produza bloqueio institucional explícito, sem persistência silenciosa.
5. Replicar a validação em todos os fluxos de geração que possam persistir jogos.
6. Manter a Lei 15 como formadora do núcleo e a Lei 16 como garantidora de unicidade global, sem mistura de papéis.

### Resposta objetiva às perguntas do aceite

- A RFE deve entrar antes ou depois das reservas?
  - Depois da composição do cartão final, quando o cartão já estiver formado.
- A RFE deve validar núcleo de 15 ou cartão final?
  - Deve validar o cartão final, preservando o núcleo como base.
- A Lei 16 está depois da validação estrutural?
  - No desenho recomendado, sim. Ela deve atuar após a validação estrutural e antes da persistência.
- A persistência acontece somente depois da aceitação?
  - Sim, no fluxo atual a persistência vem depois da aceitação pelo OutputCommander.
- Existe algum caminho que persiste jogo antes de validar?
  - Não foi identificado caminho explícito de persistência antes da validação formal.
- Existe algum fluxo paralelo que bypassa Lei 16?
  - Não foi identificado bypass explícito; a unicidade global é reforçada por memória de assinaturas e pelo `OutputCommander`.
