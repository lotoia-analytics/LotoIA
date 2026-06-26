# Fase 4: Persistência do Feedback no PostgreSQL

## Visão Geral

A Fase 4 adiciona persistência do histórico de feedback no PostgreSQL, permitindo análise de longo prazo e recuperação após reinicializações do sistema.

## O que foi implementado

### 1. Tabela `feedback_history` no PostgreSQL

**Arquivo:** `scripts/migrations/004_create_feedback_history_table.py`

Estrutura da tabela:

```sql
CREATE TABLE feedback_history (
    id SERIAL PRIMARY KEY,
    contest_number INTEGER NOT NULL,
    format VARCHAR(10) NOT NULL,
    metrics JSONB NOT NULL,
    suggestions JSONB NOT NULL,
    version_applied VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT feedback_history_unique_contest_format 
        UNIQUE (contest_number, format)
);
```

Índices criados:
- `idx_feedback_history_contest` - Busca por número do concurso
- `idx_feedback_history_format` - Busca por formato
- `idx_feedback_history_created_at` - Busca ordenada por data

### 2. Persistência no `PostContestFeedback`

**Arquivo:** `src/lotoia/generation/post_contest_feedback.py`

Novos métodos adicionados:

```python
class PostContestFeedback:
    def __init__(self, persist_to_db: bool = True):
        """Inicializa com opção de persistência."""
        self.persist_to_db = persist_to_db
        if self.persist_to_db:
            self._load_history_from_db()
    
    def _save_to_db(self, analysis: dict) -> bool:
        """Salva análise no banco de dados."""
        # INSERT com UPSERT (ON CONFLICT)
        
    def _load_history_from_db(self) -> bool:
        """Carrega histórico do banco ao inicializar."""
        # SELECT ORDER BY created_at DESC LIMIT 100
        
    def get_history_from_db(self, limit: int = 100) -> list[dict]:
        """Retorna histórico do banco."""
        # SELECT com limite configurável
```

### 3. Testes

**Arquivo:** `tests/generation/test_feedback_persistence.py`

12 testes cobrindo:
- `TestFeedbackPersistence`: Testes de persistência
  - Inicialização com/sem persistência
  - Salvamento no banco (sucesso, erro, sem conexão)
  - Carregamento do histórico
  - Integração com `analyze_contest_result`
- `TestFeedbackIntegration`: Testes de integração
  - Workflow completo com persistência
  - Workflow sem persistência

## Como Usar

### Habilitar Persistência (padrão)

```python
from lotoia.generation.post_contest_feedback import PostContestFeedback

# Por padrão, persistência está habilitada
feedback = PostContestFeedback()

# Analisar concurso (salva automaticamente no banco)
result = feedback.analyze_contest_result(
    contest_number=3720,
    contest_numbers=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    generated_games=games,
    format="15D",
    version_applied="v3.1.0",
)
```

### Desabilitar Persistência

```python
# Para testes ou uso em memória apenas
feedback = PostContestFeedback(persist_to_db=False)
```

### Recuperar Histórico do Banco

```python
# Recuperar últimas 50 análises
history = feedback.get_history_from_db(limit=50)

for analysis in history:
    print(f"Concurso {analysis['contest_number']}: {analysis['metrics']}")
```

### Executar Migration

```bash
# Criar tabela
python scripts/migrations/004_create_feedback_history_table.py

# Rollback (remover tabela)
python scripts/migrations/004_create_feedback_history_table.py rollback
```

## Resultados dos Testes

```
============================== 12 passed in 0.10s ==============================
```

| Suite | Testes |
|-------|--------|
| `TestFeedbackPersistence` | 10 |
| `TestFeedbackIntegration` | 2 |

## Benefícios

| Benefício | Descrição |
|-----------|-----------|
| **Histórico persistente** | Dados sobrevivem reinicializações |
| **Análise de longo prazo** | Possibilidade de analisar tendências ao longo de meses |
| **Recuperação de estado** | Sistema recupera contexto ao reiniciar |
| **Debug facilitado** | Histórico consultável via SQL |
| **Integração com BI** | Dados disponíveis para ferramentas de BI |

## Arquivos Modificados

| Arquivo | Mudança |
|---------|---------|
| `src/lotoia/generation/post_contest_feedback.py` | Adicionados métodos de persistência |
| `scripts/migrations/004_create_feedback_history_table.py` | Novo script de migration |
| `tests/generation/test_feedback_persistence.py` | Novo arquivo de testes (12 testes) |

## Integração com Outras Fases

- **Fase 1 (Intervalos de Confiança)**: Pode usar histórico persistente para calcular ICs mais precisos
- **Fase 2 (Detecção de Mudanças)**: Pode comparar métricas atuais com histórico persistente
- **Fase 5 (Walk-Forward)**: Histórico é essencial para validação temporal
- **Fase 6 (Multi-Strategy)**: Pode analisar qual estratégia funcionou melhor em cada período

## Próximos Passos

Com a persistência implementada, as próximas fases podem:

1. **Fase 3 (Geração Nativa)**: Usar histórico para validar geração por formato
2. **Fase 5 (Walk-Forward)**: Dividir histórico em períodos de treino/validação/teste
3. **Fase 6 (Multi-Strategy)**: Analisar desempenho de diferentes estratégias ao longo do tempo

## Referências

- [Fase 1: Intervalos de Confiança](CORE_003_PHASE1_CONFIDENCE_INTERVALS.md)
- [Fase 2: Detecção de Mudanças](CORE_003_PHASE2_CHANGE_DETECTION.md)
- [CORE_003 Pipeline](CORE_003_SIMPLIFIED_PIPELINE.md)
