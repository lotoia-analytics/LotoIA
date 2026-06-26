"""
Migration: Criar tabela feedback_history para persistência de feedback pós-concurso.

Fase 4 do plano de melhorias do CORE_003.
"""

from sqlalchemy import text
from lotoia.database.database import get_engine


def migrate_feedback_history():
    """Cria a tabela feedback_history no PostgreSQL."""

    engine = get_engine()

    with engine.connect() as conn:
        # Criar tabela feedback_history
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS feedback_history (
                id SERIAL PRIMARY KEY,
                contest_number INTEGER NOT NULL,
                format VARCHAR(10) NOT NULL,
                metrics JSONB NOT NULL,
                suggestions JSONB NOT NULL,
                version_applied VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Índices para consultas comuns
                CONSTRAINT feedback_history_unique_contest_format 
                    UNIQUE (contest_number, format)
            )
        """)
        )

        # Criar índices
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_feedback_history_contest 
            ON feedback_history(contest_number)
        """)
        )

        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_feedback_history_format 
            ON feedback_history(format)
        """)
        )

        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_feedback_history_created_at 
            ON feedback_history(created_at DESC)
        """)
        )

        conn.commit()

    print("✓ Tabela feedback_history criada com sucesso")


def rollback_feedback_history():
    """Remove a tabela feedback_history (rollback)."""

    engine = get_engine()

    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS feedback_history"))
        conn.commit()

    print("✓ Tabela feedback_history removida")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_feedback_history()
    else:
        migrate_feedback_history()
