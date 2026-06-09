# Ativação do menu Apagar e Limpar Histórico

## O que foi ativado

- item de menu `Limpar Históricos`
- item de menu `Apagar Histórico`

## O que foi mantido protegido

- a confirmação destrutiva permanece dentro da tela
- a limpeza não foi transformada em atalho automático
- dados antigos do banco não foram apagados nesta missão

## Alteração aplicada

- remoção do `disabled=True` apenas nos itens de navegação da área restrita
- manutenção da mensagem institucional de proteção da ação

## Validação

- `python -m py_compile dashboard/institutional_app.py`

## Conclusão

O menu de limpeza foi ativado visualmente no ADM, com proteção interna ainda presente na própria tela.

