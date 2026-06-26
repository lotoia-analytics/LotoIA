"""Sistema de Feedback Automático pós-concurso para CORE_003.

Analisa resultados de concursos e sugere ajustes de calibração automaticamente.
Fase 4: Persistência no PostgreSQL adicionada.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from lotoia.config.core_003_config import CORE_003_CONFIG

logger = logging.getLogger(__name__)


def _get_db_connection():
    """Obtém conexão com o banco de dados PostgreSQL."""
    try:
        from sqlalchemy import create_engine
        from lotoia.config.settings import settings

        engine = create_engine(settings.database_url)
        return engine
    except Exception as e:
        logger.warning(f"[Feedback] Erro ao conectar ao banco: {e}")
        return None


class PostContestFeedback:
    """Sistema de feedback automático pós-concurso.

    Fase 4: Agora persiste histórico no PostgreSQL.
    """

    def __init__(self, persist_to_db: bool = True):
        """Inicializa o sistema de feedback.

        Args:
            persist_to_db: Se True, persiste histórico no PostgreSQL (Fase 4)
        """
        self.suggestions: list[dict[str, Any]] = []
        self.history: list[dict[str, Any]] = []
        self.persist_to_db = persist_to_db

        # Carregar histórico do banco se disponível
        if self.persist_to_db:
            self._load_history_from_db()

    def _save_to_db(self, analysis: dict[str, Any]) -> bool:
        """Salva análise no banco de dados PostgreSQL.

        Args:
            analysis: Dicionário com análise do concurso

        Returns:
            True se salvou com sucesso, False caso contrário
        """
        if not self.persist_to_db:
            return False

        engine = _get_db_connection()
        if not engine:
            return False

        try:
            from sqlalchemy import text

            with engine.connect() as conn:
                conn.execute(
                    text("""
                        INSERT INTO feedback_history 
                        (contest_number, format, metrics, suggestions, version_applied)
                        VALUES (:contest_number, :format, :metrics, :suggestions, :version)
                        ON CONFLICT (contest_number, format) 
                        DO UPDATE SET 
                            metrics = EXCLUDED.metrics,
                            suggestions = EXCLUDED.suggestions,
                            version_applied = EXCLUDED.version_applied
                    """),
                    {
                        "contest_number": analysis["contest_number"],
                        "format": analysis["format"],
                        "metrics": json.dumps(analysis["metrics"]),
                        "suggestions": json.dumps(analysis["suggestions"]),
                        "version": analysis.get("version_applied"),
                    },
                )
                conn.commit()

            logger.debug(
                f"[Feedback] Análise salva no banco: concurso {analysis['contest_number']}"
            )
            return True

        except Exception as e:
            logger.error(f"[Feedback] Erro ao salvar no banco: {e}")
            return False

    def _load_history_from_db(self) -> bool:
        """Carrega histórico do banco de dados PostgreSQL.

        Returns:
            True se carregou com sucesso, False caso contrário
        """
        if not self.persist_to_db:
            return False

        engine = _get_db_connection()
        if not engine:
            return False

        try:
            from sqlalchemy import text

            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT contest_number, format, metrics, suggestions, 
                               version_applied, created_at
                        FROM feedback_history
                        ORDER BY created_at DESC
                        LIMIT 100
                    """)
                )

                history = []
                for row in result:
                    history.append(
                        {
                            "contest_number": row.contest_number,
                            "format": row.format,
                            "metrics": json.loads(row.metrics),
                            "suggestions": json.loads(row.suggestions),
                            "version_applied": row.version_applied,
                            "timestamp": row.created_at.isoformat(),
                            "games_analyzed": 0,  # Não persistimos os jogos
                        }
                    )

                # Ordenar por concurso (crescente)
                history.sort(key=lambda x: x["contest_number"])
                self.history = history

            logger.debug(
                f"[Feedback] Histórico carregado do banco: {len(history)} análises"
            )
            return True

        except Exception as e:
            logger.error(f"[Feedback] Erro ao carregar do banco: {e}")
            return False

    def get_history_from_db(self, limit: int = 100) -> list[dict[str, Any]]:
        """Retorna histórico do banco de dados.

        Args:
            limit: Número máximo de registros a retornar

        Returns:
            Lista de análises do banco
        """
        engine = _get_db_connection()
        if not engine:
            return []

        try:
            from sqlalchemy import text

            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT contest_number, format, metrics, suggestions, 
                               version_applied, created_at
                        FROM feedback_history
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"limit": limit},
                )

                history = []
                for row in result:
                    history.append(
                        {
                            "contest_number": row.contest_number,
                            "format": row.format,
                            "metrics": json.loads(row.metrics),
                            "suggestions": json.loads(row.suggestions),
                            "version_applied": row.version_applied,
                            "timestamp": row.created_at.isoformat(),
                        }
                    )

                return history

        except Exception as e:
            logger.error(f"[Feedback] Erro ao buscar histórico do banco: {e}")
            return []

    def analyze_contest_result(
        self,
        contest_number: int,
        contest_numbers: list[int],
        generated_games: list[dict[str, Any]],
        format: str = "15D",
        version_applied: str | None = None,
    ) -> dict[str, Any]:
        """Analisa resultado de concurso e gera sugestões de ajuste.

        Args:
            contest_number: Número do concurso
            contest_numbers: Dezenas sorteadas no concurso
            generated_games: Jogos gerados para este concurso
            format: Formato dos jogos (15D, 17D, etc.)
            version_applied: Versão do modelo aplicada (opcional)

        Returns:
            Dicionário com métricas e sugestões
        """
        logger.info(
            "[Feedback] Analisando concurso %d | format=%s games=%d",
            contest_number,
            format,
            len(generated_games),
        )

        # Calcular métricas de desempenho
        metrics = self._compute_post_contest_metrics(
            contest_numbers, generated_games, format
        )

        # Gerar sugestões baseadas nas métricas
        suggestions = self._generate_suggestions(metrics, format)

        # Registrar análise
        analysis = {
            "contest_number": contest_number,
            "format": format,
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics,
            "suggestions": suggestions,
            "games_analyzed": len(generated_games),
            "version_applied": version_applied,
        }

        # Adicionar ao histórico em memória
        self.history.append(analysis)

        # Persistir no banco de dados (Fase 4)
        if self.persist_to_db:
            self._save_to_db(analysis)

        # Log de resultados
        logger.info(
            "[Feedback] Concurso %d | hit_11_13=%.1f%% triplet_hit=%.1f%% suggestions=%d",
            contest_number,
            metrics["hit_rate_11_13"] * 100,
            metrics["triplet_hit_rate"] * 100,
            len(suggestions),
        )

        if suggestions:
            logger.warning(
                "[Feedback] Sugestões geradas: %s",
                [s["adjustment"] for s in suggestions],
            )

        return analysis

    def _compute_post_contest_metrics(
        self,
        contest_numbers: list[int],
        generated_games: list[dict[str, Any]],
        format: str,
    ) -> dict[str, Any]:
        """Calcula métricas de desempenho pós-concurso."""
        contest_set = set(contest_numbers)
        total_games = len(generated_games)

        if total_games == 0:
            return {
                "hit_rate_11_13": 0.0,
                "hit_rate_14_15": 0.0,
                "triplet_hit_rate": 0.0,
                "suffix_hit_rate": 0.0,
                "avg_hits": 0.0,
                "max_hits": 0,
            }

        # Contar acertos por jogo
        hits_per_game = []
        hits_11_13 = 0
        hits_14_15 = 0
        triplet_hits = 0
        suffix_hits = 0

        for game in generated_games:
            game_numbers = set(game.get("numbers", []))
            hits = len(game_numbers & contest_set)
            hits_per_game.append(hits)

            # Faixas de acertos
            if 11 <= hits <= 13:
                hits_11_13 += 1
            elif 14 <= hits <= 15:
                hits_14_15 += 1

            # Triplet 01-02-03
            if all(n in game_numbers for n in [1, 2, 3]):
                if all(n in contest_set for n in [1, 2, 3]):
                    triplet_hits += 1

            # Suffix 23-24-25
            if all(n in game_numbers for n in [23, 24, 25]):
                if all(n in contest_set for n in [23, 24, 25]):
                    suffix_hits += 1

        # Calcular taxas
        hit_rate_11_13 = hits_11_13 / total_games
        hit_rate_14_15 = hits_14_15 / total_games
        triplet_hit_rate = triplet_hits / total_games if triplet_hits > 0 else 0.0
        suffix_hit_rate = suffix_hits / total_games if suffix_hits > 0 else 0.0
        avg_hits = sum(hits_per_game) / total_games
        max_hits = max(hits_per_game) if hits_per_game else 0

        return {
            "hit_rate_11_13": round(hit_rate_11_13, 4),
            "hit_rate_14_15": round(hit_rate_14_15, 4),
            "triplet_hit_rate": round(triplet_hit_rate, 4),
            "suffix_hit_rate": round(suffix_hit_rate, 4),
            "avg_hits": round(avg_hits, 2),
            "max_hits": max_hits,
            "total_hits_11_13": hits_11_13,
            "total_hits_14_15": hits_14_15,
        }

    def _generate_suggestions(
        self,
        metrics: dict[str, Any],
        format: str,
    ) -> list[dict[str, Any]]:
        """Gera sugestões de ajuste baseadas nas métricas."""
        suggestions = []

        # Baixa taxa de acertos 11-13 → aumentar diversidade
        if metrics["hit_rate_11_13"] < 0.10:
            suggestions.append(
                {
                    "adjustment": "increase_diversity",
                    "reason": f"hit_rate_11_13={metrics['hit_rate_11_13']:.1%} < 10%",
                    "priority": "high",
                    "parameters": {
                        "diversity_floor": "+0.03",
                        "overlap_penalty": "-0.05",
                    },
                }
            )

        # Baixa taxa de triplet → aumentar cap de triplet
        if metrics["triplet_hit_rate"] < 0.15:
            current_triplet_cap = CORE_003_CONFIG["structural_policy"][
                "triplet_010203"
            ]["freq"]
            suggestions.append(
                {
                    "adjustment": "increase_triplet_cap",
                    "reason": f"triplet_hit_rate={metrics['triplet_hit_rate']:.1%} < 15%",
                    "priority": "medium",
                    "parameters": {
                        "triplet_freq": f"{current_triplet_cap + 0.02:.2f}",
                    },
                }
            )

        # Baixa taxa de suffix → aumentar cap de suffix
        if metrics["suffix_hit_rate"] < 0.15:
            current_suffix_cap = CORE_003_CONFIG["structural_policy"]["suffix_232425"][
                "freq"
            ]
            suggestions.append(
                {
                    "adjustment": "increase_suffix_cap",
                    "reason": f"suffix_hit_rate={metrics['suffix_hit_rate']:.1%} < 15%",
                    "priority": "medium",
                    "parameters": {
                        "suffix_freq": f"{current_suffix_cap + 0.02:.2f}",
                    },
                }
            )

        # Muitos acertos 14-15 → sistema está funcionando bem
        if metrics["hit_rate_14_15"] > 0.05:
            suggestions.append(
                {
                    "adjustment": "maintain_current",
                    "reason": f"hit_rate_14_15={metrics['hit_rate_14_15']:.1%} > 5% (excelente)",
                    "priority": "low",
                    "parameters": {},
                }
            )

        return suggestions

    def get_suggestions_summary(self) -> dict[str, Any]:
        """Retorna resumo das sugestões pendentes."""
        if not self.history:
            return {"pending_suggestions": 0, "suggestions": []}

        # Consolidar sugestões da última análise
        last_analysis = self.history[-1]
        suggestions = last_analysis.get("suggestions", [])

        return {
            "pending_suggestions": len(suggestions),
            "suggestions": suggestions,
            "last_contest": last_analysis.get("contest_number"),
            "last_analysis": last_analysis.get("timestamp"),
        }

    def get_performance_trend(self, last_n: int = 10) -> dict[str, Any]:
        """Calcula tendência de desempenho nas últimas N análises."""
        if len(self.history) < 2:
            return {"trend": "insufficient_data", "analyses": 0}

        recent = self.history[-last_n:]

        # Calcular médias
        avg_hit_11_13 = sum(a["metrics"]["hit_rate_11_13"] for a in recent) / len(
            recent
        )
        avg_triplet = sum(a["metrics"]["triplet_hit_rate"] for a in recent) / len(
            recent
        )
        avg_suffix = sum(a["metrics"]["suffix_hit_rate"] for a in recent) / len(recent)

        # Determinar tendência
        if len(recent) >= 3:
            first_half = recent[: len(recent) // 2]
            second_half = recent[len(recent) // 2 :]

            first_avg = sum(a["metrics"]["hit_rate_11_13"] for a in first_half) / len(
                first_half
            )
            second_avg = sum(a["metrics"]["hit_rate_11_13"] for a in second_half) / len(
                second_half
            )

            if second_avg > first_avg * 1.1:
                trend = "improving"
            elif second_avg < first_avg * 0.9:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "trend": trend,
            "analyses": len(recent),
            "avg_hit_rate_11_13": round(avg_hit_11_13, 4),
            "avg_triplet_hit_rate": round(avg_triplet, 4),
            "avg_suffix_hit_rate": round(avg_suffix, 4),
        }


# Instância global
_feedback_system = PostContestFeedback()


def post_contest_feedback(
    contest_number: int,
    contest_numbers: list[int],
    generated_games: list[dict[str, Any]],
    format: str = "15D",
) -> dict[str, Any]:
    """Função simplificada para análise pós-concurso.

    Args:
        contest_number: Número do concurso
        contest_numbers: Dezenas sorteadas
        generated_games: Jogos gerados
        format: Formato dos jogos

    Returns:
        Análise com métricas e sugestões
    """
    return _feedback_system.analyze_contest_result(
        contest_number, contest_numbers, generated_games, format
    )


def get_feedback_suggestions() -> dict[str, Any]:
    """Retorna sugestões pendentes de ajuste."""
    return _feedback_system.get_suggestions_summary()


def get_performance_trend(last_n: int = 10) -> dict[str, Any]:
    """Retorna tendência de desempenho."""
    return _feedback_system.get_performance_trend(last_n)
