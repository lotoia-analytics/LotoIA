# Corre??o Visual do Near Miss no Hist?rico Institucional

## Objetivo

Remover a exposi??o visual de comando operacional na se??o **Melhores near miss da ?ltima bateria** do Hist?rico Institucional, sem alterar l?gica funcional.

## Bloco exato alterado

Arquivo:
- `dashboard/institutional_app.py`

Bloco alterado:
- se??o `Melhores near miss da ?ltima bateria` dentro de `_render_scientific_memory_block()`

## Corre??o aplicada

### Antes

O card principal exibia o r?tulo:
- `A??o`

E mostrava diretamente um valor t?cnico iniciado por:
- `recalibrate_from_*`

### Depois

O card principal passou a exibir:
- `Registro t?cnico legado`

E o valor vis?vel passou a ser sanitizado por:
- `Preservado em quarentena documental`
- `Sem a??o operacional`
- `Registro t?cnico legado`

## Prote??o aplicada

Foi inclu?da a fun??o:
- `_institutional_safe_action_label(raw_action)`

Regras:
- se o valor come?ar com `recalibrate_from`, ele n?o ? mostrado como comando na ?rea principal;
- se o valor for vazio ou nulo, a interface mostra `Sem a??o operacional`;
- caso contr?rio, mostra `Registro t?cnico legado`.

## Ocorr?ncias restantes de `recalibrate_from`

As ocorr?ncias restantes em `dashboard/institutional_app.py` permanecem apenas como:
- defini??o t?cnica de recomenda??o cient?fica;
- metadata de pol?tica;
- chaves de persist?ncia/avalia??o;
- l?gica interna de calibra??o hist?rica.

Exemplos de ocorr?ncias restantes:
- `recalibrate_from_strong_near_miss_towards_11_plus_and_15`
- `recalibrate_from_near_miss_towards_15`

Essas ocorr?ncias n?o aparecem mais como card principal na ?rea de near miss.

## Strings vis?veis corrigidas

- `A??o` -> `Registro t?cnico legado`
- `Resumo inicial com 10 linhas mais recentes.` -> `?ltimos 10 concursos oficiais persistidos no banco.`
- texto de quarentena atualizado para linguagem institucional sem comando operacional

## Valida??o executada

- `python -m py_compile dashboard/institutional_app.py`
- `python -m pytest tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py -q`

Resultado:
- `26 passed`
- 1 warning de cache do pytest no ambiente

## Confirma??o final

- Nenhuma l?gica funcional foi alterada.
- Nenhuma regra de Lei 15 foi alterada.
- A corre??o foi exclusivamente visual/textual na p?gina Hist?rico Institucional.
