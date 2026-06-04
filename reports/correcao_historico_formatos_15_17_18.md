# Correção do Histórico Analítico para Formatos 15 / 17 / 18

## Contexto
A página limpa do gerador passou a expor os formatos 15, 17 e 18 dezenas como expansão auditada do núcleo da Lei 15.

## Correção aplicada
A saída final da página limpa foi conectada ao mecanismo de persistência do histórico institucional, preservando a geração original e gravando apenas metadados e apresentação do cartão final.

## Campos persistidos
- timestamp da geração
- quantidade solicitada
- formato_cartao
- núcleo_lei_15
- reservas_auditadas
- cartão_final
- quantidade do núcleo
- quantidade de reservas
- quantidade final
- generation_mode=CLEAN_LAW15_ISOLATED_PAGE
- policy_mode=CLEAN_LAW15_ISOLATED_PAGE
- scientific_law_role=COMMANDER
- clean_adm_runtime_role=EXECUTOR
- output_commander_role=AUDITOR
- legacy_calibrator_role=REMOVED_FROM_RUNTIME
- calibration_engine_role=DISABLED
- status de validação Lei 17
- status de validação Lei 18

## Compatibilidade institucional
- A Lei 15 continua gerando o núcleo.
- 17 e 18 continuam como expansão auditada.
- Lei 17 e Lei 18 continuam como validações pós-geração.
- O histórico registra o que foi gerado e exibido, sem recalibrar ou regenerar.

## Exibição no Histórico Analítico
O Histórico Analítico passou a ler e exibir:
- data/hora
- formato_cartao
- núcleo_lei_15
- reservas_auditadas
- cartão_final
- quantidade_final

## Conclusão
Os formatos 15, 17 e 18 dezenas da página limpa do gerador passaram a ser persistidos no Histórico Analítico com núcleo Lei 15, reservas auditadas e cartão final, sem alteração da Lei 15, sem recalibração, sem legado ativo e sem transformação do histórico em mecanismo de geração.
