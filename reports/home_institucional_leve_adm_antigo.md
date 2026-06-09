# Home Institucional Leve do ADM Antigo

## Página inicial anterior
- `Gerador LotoIA`
- Tela operacional pesada com cards, histórico, diagnóstico e botão de geração.

## Nova página inicial
- `Painel Institucional LotoIA`
- Home leve, sem execução de geração, sem recalibração e sem carga histórica pesada.

## Ajustes feitos
- Troca da rota inicial padrão para `home`.
- Inclusão de uma home institucional leve com status simples do runtime.
- Exibição de `build`, backend conectado e último concurso apenas em consulta leve.
- Inclusão de atalhos para:
  - `Gerador ADM - Lei 15 Limpo`
  - `Conferir Resultados`
  - `Simular Resultados`
  - `Histórico Analítico`
  - `Histórico Institucional`
  - `Auditoria e Monitoramento`
- Inclusão de aviso institucional:
  - Lei 15 como comando soberano
  - Lei 17/18 como validação / referência
  - quarentena e ações destrutivas bloqueadas

## Validação do comportamento
- O Gerador não carrega por padrão na abertura.
- A home não exibe botão de `Gerar jogos`.
- O Gerador permanece acessível apenas pelo menu `Gerador ADM - Lei 15 Limpo`.
- A home não executa geração, conferência, simulação nem recalibração.

## Confirmação funcional
- Nenhuma lógica funcional foi alterada.
- A mudança foi apenas de navegação inicial, renderização e apresentação institucional.

## Testes executados
- `python -m py_compile dashboard/institutional_app.py`
- `python -m pytest tests/test_scientific_calibration_engine.py tests/test_lotofacil_scientific_core.py tests/test_batch_scientific_memory.py -q`

