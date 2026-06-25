# Guia de Contribuição

Obrigado por considerar contribuir com o LotoIA! Este documento fornece diretrizes para contribuir com o projeto.

## Código de Conduta

Este projeto segue um código de conduta básico:

- Seja respeitoso e construtivo
- Foque no mérito técnico das contribuições
- Mantenha discussões profissionais
- Respeite diferentes perspectivas

## Como Contribuir

### Reportando Bugs

1. Verifique se o bug já foi reportado nas issues
2. Use o template de bug report
3. Inclua:
   - Descrição clara do problema
   - Passos para reproduzir
   - Comportamento esperado vs atual
   - Logs relevantes (se possível)
   - Versão do Python e dependências

### Sugerindo Melhorias

1. Abra uma issue com o label `enhancement`
2. Descreva a melhoria proposta
3. Explique o benefício para o projeto
4. Discuta a abordagem antes de implementar

### Submetendo Código

1. **Fork** o repositório
2. **Clone** seu fork:
   ```bash
   git clone https://github.com/seu-usuario/LotoIA.git
   cd LotoIA
   ```
3. **Crie uma branch** para sua feature:
   ```bash
   git checkout -b feature/nome-da-feature
   ```
4. **Faça suas alterações** seguindo os padrões do projeto
5. **Adicione testes** para novas funcionalidades
6. **Execute os testes**:
   ```bash
   pytest
   ```
7. **Commit** suas mudanças:
   ```bash
   git add .
   git commit -m "feat: descrição clara da mudança"
   ```
8. **Push** para seu fork:
   ```bash
   git push origin feature/nome-da-feature
   ```
9. **Abra um Pull Request** no repositório original

## Padrões de Código

### Python

- **Versão:** Python 3.11+
- **Formatação:** Siga PEP 8
- **Type hints:** Use quando possível
- **Docstrings:** Documente funções públicas
- **Imports:** Organize em grupos (stdlib, third-party, local)

### Estrutura de Commits

Use mensagens de commit claras e descritivas:

```
feat: adicionar validação de métricas estruturais
fix: corrigir cálculo de overlap médio
docs: atualizar README com instruções de instalação
test: adicionar testes para structural_metrics_validator
refactor: extrair constantes para módulo de configuração
```

### Testes

- Toda nova funcionalidade deve ter testes
- Mantenha cobertura acima de 80%
- Use nomes descritivos para testes:
  ```python
  def test_triplet_010203_below_minimum():
      """Triplet 01-02-03 abaixo de 10% deve violar."""
  ```

### Documentação

- Atualize o README se necessário
- Adicione entradas no CHANGELOG.md
- Documente APIs públicas
- Inclua exemplos de uso

## Áreas de Contribuição

### Estatística

- Novas métricas estruturais
- Validações de distribuição
- Análises de frequência

### Geração

- Otimização do pipeline CORE_002
- Novas políticas anti-viés
- Melhorias no anti-clone

### Machine Learning

- Modelos de calibração
- Feature engineering
- Validação de modelos

### Dashboard

- Novas visualizações
- Melhorias de UX
- Performance

### Testes

- Testes unitários
- Testes de integração
- Testes de performance

## Ambiente de Desenvolvimento

### Setup

```bash
# Clonar repositório
git clone https://github.com/lotoia-analytics/LotoIA.git
cd LotoIA

# Criar ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .\.venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt
pip install -e .

# Configurar variáveis de ambiente
cp .env.example .env
# Edite .env com suas configurações
```

### Executando Testes

```bash
# Todos os testes
pytest

# Testes específicos
pytest tests/generation/test_structural_metrics.py -v

# Com cobertura
pytest --cov=src/lotoia --cov-report=html

# Ver logs
pytest -s
```

### Linting

```bash
# Verificar estilo
ruff check src/lotoia/

# Auto-corrigir
ruff check --fix src/lotoia/
```

## Processo de Review

1. **CI/CD:** Todos os PRs passam por testes automatizados
2. **Review:** Pelo menos um maintainer deve aprovar
3. **Discussão:** Responda feedbacks de forma construtiva
4. **Merge:** Após aprovação, um maintainer fará o merge

## Dúvidas?

- Abra uma issue com a label `question`
- Consulte a documentação em `docs/`
- Verifique o CHANGELOG para mudanças recentes

## Reconhecimento

Contribuidores serão listados no README e no CHANGELOG.

Obrigado por contribuir!
