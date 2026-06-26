"""Testes para persistência do feedback no PostgreSQL (Fase 4)."""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from lotoia.generation.post_contest_feedback import (
    PostContestFeedback,
    _get_db_connection,
)


class TestFeedbackPersistence:
    """Testes de persistência do feedback no PostgreSQL."""

    def test_init_without_persistence(self):
        """Testa inicialização sem persistência."""
        feedback = PostContestFeedback(persist_to_db=False)
        assert feedback.persist_to_db is False
        assert feedback.history == []

    def test_init_with_persistence_no_db(self):
        """Testa inicialização com persistência mas sem banco disponível."""
        with patch(
            "lotoia.generation.post_contest_feedback._get_db_connection",
            return_value=None,
        ):
            feedback = PostContestFeedback(persist_to_db=True)
            assert feedback.persist_to_db is True
            assert feedback.history == []

    @patch("lotoia.generation.post_contest_feedback._get_db_connection")
    def test_save_to_db_success(self, mock_get_db):
        """Testa salvamento bem-sucedido no banco."""
        # Mock do engine e conexão
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_get_db.return_value = mock_engine

        feedback = PostContestFeedback(persist_to_db=True)

        analysis = {
            "contest_number": 3720,
            "format": "15D",
            "metrics": {"hit_rate_11_13": 0.15},
            "suggestions": [{"adjustment": "increase_triplet_cap"}],
            "version_applied": "v3.1.0",
        }

        # Resetar contadores após inicialização (que também chama _load_history_from_db)
        mock_conn.execute.reset_mock()
        mock_conn.commit.reset_mock()

        result = feedback._save_to_db(analysis)

        assert result is True
        mock_conn.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    @patch("lotoia.generation.post_contest_feedback._get_db_connection")
    def test_save_to_db_no_connection(self, mock_get_db):
        """Testa salvamento quando não há conexão com banco."""
        mock_get_db.return_value = None

        feedback = PostContestFeedback(persist_to_db=True)

        analysis = {
            "contest_number": 3720,
            "format": "15D",
            "metrics": {},
            "suggestions": [],
        }

        result = feedback._save_to_db(analysis)

        assert result is False

    @patch("lotoia.generation.post_contest_feedback._get_db_connection")
    def test_save_to_db_exception(self, mock_get_db):
        """Testa salvamento quando ocorre exceção."""
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("DB Error")
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_get_db.return_value = mock_engine

        feedback = PostContestFeedback(persist_to_db=True)

        analysis = {
            "contest_number": 3720,
            "format": "15D",
            "metrics": {},
            "suggestions": [],
        }

        result = feedback._save_to_db(analysis)

        assert result is False

    @patch("lotoia.generation.post_contest_feedback._get_db_connection")
    def test_load_history_from_db_success(self, mock_get_db):
        """Testa carregamento bem-sucedido do histórico do banco."""
        # Mock do engine e conexão
        mock_engine = MagicMock()
        mock_conn = MagicMock()

        # Mock do resultado da query
        mock_result = [
            Mock(
                contest_number=3720,
                format="15D",
                metrics=json.dumps({"hit_rate_11_13": 0.15}),
                suggestions=json.dumps([]),
                version_applied="v3.1.0",
                created_at=datetime(2026, 6, 25, 10, 0, 0),
            ),
            Mock(
                contest_number=3719,
                format="15D",
                metrics=json.dumps({"hit_rate_11_13": 0.12}),
                suggestions=json.dumps([{"adjustment": "increase_triplet_cap"}]),
                version_applied=None,
                created_at=datetime(2026, 6, 24, 10, 0, 0),
            ),
        ]
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_get_db.return_value = mock_engine

        feedback = PostContestFeedback(persist_to_db=True)

        # Verificar que o histórico foi carregado
        assert len(feedback.history) == 2
        assert feedback.history[0]["contest_number"] == 3719  # Ordenado por concurso
        assert feedback.history[1]["contest_number"] == 3720

    @patch("lotoia.generation.post_contest_feedback._get_db_connection")
    def test_load_history_from_db_no_connection(self, mock_get_db):
        """Testa carregamento quando não há conexão com banco."""
        mock_get_db.return_value = None

        feedback = PostContestFeedback(persist_to_db=True)

        assert feedback.history == []

    @patch("lotoia.generation.post_contest_feedback._get_db_connection")
    def test_analyze_contest_result_saves_to_db(self, mock_get_db):
        """Testa que analyze_contest_result salva no banco."""
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_get_db.return_value = mock_engine

        feedback = PostContestFeedback(persist_to_db=True)

        # Mock dos métodos internos
        feedback._compute_post_contest_metrics = Mock(
            return_value={
                "hit_rate_11_13": 0.15,
                "hit_rate_14_15": 0.05,
                "triplet_hit_rate": 0.20,
                "suffix_hit_rate": 0.18,
                "avg_hits": 11.5,
                "max_hits": 14,
                "total_hits_11_13": 3,
                "total_hits_14_15": 1,
            }
        )
        feedback._generate_suggestions = Mock(return_value=[])

        result = feedback.analyze_contest_result(
            contest_number=3720,
            contest_numbers=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
            generated_games=[
                {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]}
            ],
            format="15D",
            version_applied="v3.1.0",
        )

        # Verificar que salvou no banco
        mock_conn.execute.assert_called()
        mock_conn.commit.assert_called()

        # Verificar que adicionou ao histórico
        assert len(feedback.history) == 1
        assert feedback.history[0]["contest_number"] == 3720
        assert feedback.history[0]["version_applied"] == "v3.1.0"

    @patch("lotoia.generation.post_contest_feedback._get_db_connection")
    def test_get_history_from_db(self, mock_get_db):
        """Testa get_history_from_db."""
        mock_engine = MagicMock()
        mock_conn = MagicMock()

        mock_result = [
            Mock(
                contest_number=3720,
                format="15D",
                metrics=json.dumps({"hit_rate_11_13": 0.15}),
                suggestions=json.dumps([]),
                version_applied="v3.1.0",
                created_at=datetime(2026, 6, 25, 10, 0, 0),
            ),
        ]
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_get_db.return_value = mock_engine

        feedback = PostContestFeedback(persist_to_db=False)
        history = feedback.get_history_from_db(limit=10)

        assert len(history) == 1
        assert history[0]["contest_number"] == 3720

    @patch("lotoia.generation.post_contest_feedback._get_db_connection")
    def test_get_history_from_db_no_connection(self, mock_get_db):
        """Testa get_history_from_db quando não há conexão."""
        mock_get_db.return_value = None

        feedback = PostContestFeedback(persist_to_db=False)
        history = feedback.get_history_from_db()

        assert history == []


class TestFeedbackIntegration:
    """Testes de integração do feedback com persistência."""

    @patch("lotoia.generation.post_contest_feedback._get_db_connection")
    def test_full_workflow_with_persistence(self, mock_get_db):
        """Testa workflow completo com persistência."""
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_get_db.return_value = mock_engine

        # Criar feedback com persistência
        feedback = PostContestFeedback(persist_to_db=True)

        # Mock dos métodos internos
        feedback._compute_post_contest_metrics = Mock(
            return_value={
                "hit_rate_11_13": 0.08,  # Baixo para gerar sugestão
                "hit_rate_14_15": 0.02,
                "triplet_hit_rate": 0.10,  # Baixo para gerar sugestão
                "suffix_hit_rate": 0.12,
                "avg_hits": 10.5,
                "max_hits": 13,
                "total_hits_11_13": 2,
                "total_hits_14_15": 0,
            }
        )

        # Analisar concurso
        result = feedback.analyze_contest_result(
            contest_number=3720,
            contest_numbers=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
            generated_games=[
                {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]}
            ],
            format="15D",
        )

        # Verificar que gerou sugestões
        assert len(result["suggestions"]) > 0

        # Verificar que salvou no banco
        mock_conn.execute.assert_called()
        mock_conn.commit.assert_called()

        # Verificar que adicionou ao histórico
        assert len(feedback.history) == 1

    def test_workflow_without_persistence(self):
        """Testa workflow sem persistência."""
        feedback = PostContestFeedback(persist_to_db=False)

        # Mock dos métodos internos
        feedback._compute_post_contest_metrics = Mock(
            return_value={
                "hit_rate_11_13": 0.15,
                "hit_rate_14_15": 0.05,
                "triplet_hit_rate": 0.20,
                "suffix_hit_rate": 0.18,
                "avg_hits": 11.5,
                "max_hits": 14,
                "total_hits_11_13": 3,
                "total_hits_14_15": 1,
            }
        )
        feedback._generate_suggestions = Mock(return_value=[])

        result = feedback.analyze_contest_result(
            contest_number=3720,
            contest_numbers=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
            generated_games=[
                {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]}
            ],
            format="15D",
        )

        # Verificar que funcionou
        assert result["contest_number"] == 3720
        assert len(feedback.history) == 1
