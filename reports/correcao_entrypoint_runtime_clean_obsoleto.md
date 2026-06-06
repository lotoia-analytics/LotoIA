# Correção cirúrgica do entrypoint ADM

## Antes
- O `Procfile` apontava para `dashboard/admin_app.py`.
- A interface institucional ainda exibia o marcador `institutional-clean-runtime-v2-95a0bdb` e a legenda `Painel institucional limpo`.

## Depois
- O `Procfile` passou a iniciar `dashboard/institutional_app.py`.
- O marcador de build do runtime institucional foi alterado para `institutional-adm-runtime-v2`.
- A legenda lateral passou a exibir `Painel institucional ADM`.

## Onde estava a referência ao runtime clean
- `Procfile`
- `dashboard/institutional_app.py` (`BUILD_MARKER` e legenda lateral)

## Confirmações
- `dashboard/clean_app.py` não foi apagado.
- `dashboard/lotoia_clean_zero.py` não foi apagado.
- Eles saíram do caminho operacional principal porque o `Procfile` agora sobe a rota institucional.
- A rota operacional passa a usar o ADM institucional em `dashboard/institutional_app.py`.

## Testes executados
- `python -m py_compile dashboard/institutional_app.py dashboard/clean_app.py dashboard/lotoia_clean_zero.py`
- `python -m pytest tests/test_conferencia_19d_concurso_3700.py -q`
- `python -m pytest tests/test_conferencia_formatos_expandidos.py -q`

## Conclusão
- O entrypoint operacional foi corrigido para a rota institucional atual, reduzindo o risco de subir o runtime clean obsoleto no painel ADM.
