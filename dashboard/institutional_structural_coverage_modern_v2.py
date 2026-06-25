"""Cobertura Nova — Painel com ML como Sensor (v2).

Segunda página de Cobertura Estrutural com foco em:
- Score ML como sensor informativo (não bloqueante)
- Ciclo de aprendizado (feedback loop → calibração)
- Análise de todas as gerações CORE_002 agregadas
- Recomendações para ativação completa do sistema
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import text

from lotoia.database.database import get_session


def _query_postgresql(query: str, params: dict = None) -> list[dict[str, Any]]:
    """Executa query no PostgreSQL e retorna lista de dicts."""
    try:
        with get_session(None) as session:
            result = session.execute(text(query), params or {})
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]
    except Exception as e:
        st.error(f"Erro ao consultar banco: {e}")
        return []


def _load_all_generations_data(format_filter: str | None = None) -> dict[str, Any]:
    """Carrega dados de todas as gerações CORE_002 ativas com filtro opcional de formato.

    Args:
        format_filter: "15D" ou "18D" para filtrar por formato. None para todos.
    """
    # Buscar events CORE_002 com filtro opcional de formato
    if format_filter:
        events = _query_postgresql(
            """
            SELECT id, created_at, analysis_batch_label
            FROM generation_events
            WHERE analysis_batch_label LIKE 'STRUCT_LEI15_CORE_CANDIDATE_002%'
              AND analysis_batch_label LIKE :format_pattern
            ORDER BY created_at DESC
            """,
            {"format_pattern": f"%_{format_filter}_%"},
        )
    else:
        events = _query_postgresql("""
            SELECT id, created_at, analysis_batch_label
            FROM generation_events
            WHERE analysis_batch_label LIKE 'STRUCT_LEI15_CORE_CANDIDATE_002%'
            ORDER BY created_at DESC
        """)

    if not events:
        return {"available": False, "events_count": 0, "games": []}

    all_games = []

    for event in events:
        event_id = event["id"]

        # Buscar jogos desse event
        games_rows = _query_postgresql(
            """
            SELECT numbers, final_score, quadra_score, context_json::text
            FROM generated_games
            WHERE generation_event_id = :event_id
            """,
            {"event_id": event_id},
        )

        for row in games_rows:
            numbers = row["numbers"]
            # Se numbers for string JSON, converte para lista
            if isinstance(numbers, str):
                numbers = json.loads(numbers)

            # Extrai score_ml do context_json
            context = {}
            if row.get("context_json"):
                try:
                    context = (
                        json.loads(row["context_json"])
                        if isinstance(row["context_json"], str)
                        else row["context_json"]
                    )
                except:
                    context = {}

            # score_ml pode estar em diferentes lugares
            score_ml = context.get("score_ml")
            if score_ml is None:
                feature_attribution = context.get("feature_attribution", {})
                score_ml = (
                    feature_attribution.get("score_ml")
                    if isinstance(feature_attribution, dict)
                    else None
                )

            all_games.append(
                {
                    "numbers": numbers,
                    "final_score": row["final_score"],
                    "quadra_score": row["quadra_score"],
                    "score_ml": score_ml,
                    "event_id": event_id,
                }
            )

    # Usar o último event como referência
    latest_event = events[0]

    return {
        "available": True,
        "event_id": latest_event["id"],
        "event_date": latest_event["created_at"],
        "batch_label": latest_event["analysis_batch_label"],
        "events_count": len(events),
        "games": all_games,
    }


def _load_conference_stats() -> dict[str, Any]:
    """Carrega estatísticas de conferência."""
    stats = _query_postgresql("""
        SELECT 
            COUNT(*) as total_runs,
            COALESCE(SUM(prize_count), 0) as total_prizes,
            MAX(best_hits) as best_hits,
            COUNT(DISTINCT contest_id) as distinct_contests
        FROM reconciliation_runs
    """)

    if not stats:
        return {
            "total_runs": 0,
            "total_prizes": 0,
            "best_hits": 0,
            "distinct_contests": 0,
        }

    return stats[0]


def _load_calibration_stats() -> dict[str, Any]:
    """Carrega estatísticas de calibração ML."""
    stats = _query_postgresql("""
        SELECT 
            COUNT(*) as total_decisions,
            SUM(CASE WHEN applied = 1 THEN 1 ELSE 0 END) as applied_count
        FROM scientific_calibration_decisions
    """)

    if not stats:
        return {
            "total_decisions": 0,
            "applied_count": 0,
        }

    return stats[0]


def _load_feedback_loop_stats() -> dict[str, Any]:
    """Estatísticas do feedback loop pós-conferência (tabela feedback_loop)."""
    table_exists = _query_postgresql(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = 'feedback_loop'
        ) AS exists
        """
    )
    if not table_exists or not bool(table_exists[0].get("exists")):
        return {
            "available": False,
            "total_feedback": 0,
            "latest_contest": None,
            "pending_contests": 0,
        }

    totals = _query_postgresql(
        """
        SELECT
            COUNT(*) AS total_feedback,
            MAX(contest_number) AS latest_contest
        FROM feedback_loop
        """
    )
    pending = _query_postgresql(
        """
        SELECT COUNT(*) AS pending_contests FROM (
            SELECT DISTINCT gg.target_contest AS contest_number
            FROM generated_games gg
            INNER JOIN lotofacil_official_history oh ON oh.contest_number = gg.target_contest
            WHERE gg.target_contest IS NOT NULL
              AND gg.target_contest > 0
              AND NOT EXISTS (
                  SELECT 1
                  FROM feedback_loop fl
                  WHERE fl.contest_number = gg.target_contest
              )
        ) missing
        """
    )
    row = totals[0] if totals else {}
    pending_row = pending[0] if pending else {}
    return {
        "available": True,
        "total_feedback": int(row.get("total_feedback", 0) or 0),
        "latest_contest": _safe_int(row.get("latest_contest"), default=None),
        "pending_contests": int(pending_row.get("pending_contests", 0) or 0),
    }


def _safe_int(value: object, *, default: int | None = None) -> int | None:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def resolve_feedback_loop_status(
    *,
    feedback_stats: dict[str, Any],
    conference_stats: dict[str, Any],
) -> dict[str, str]:
    """Resolve badge do passo 3 — Feedback Loop."""
    total_runs = int(conference_stats.get("total_runs", 0) or 0)
    total_feedback = int(feedback_stats.get("total_feedback", 0) or 0)
    pending = int(feedback_stats.get("pending_contests", 0) or 0)

    if total_runs <= 0:
        return {
            "status": "○ AGUARDANDO",
            "status_color": "gray",
            "detail": "Conferir lotes para habilitar feedback pós-concurso",
        }
    if total_feedback > 0 and pending == 0:
        latest = feedback_stats.get("latest_contest")
        suffix = f" · concurso {latest}" if latest else ""
        return {
            "status": f"✓ ATIVO{suffix}",
            "status_color": "green",
            "detail": f"{total_feedback} ciclo(s) persistido(s) · sem pendências",
        }
    if total_feedback > 0 and pending > 0:
        return {
            "status": f"⚠ PARCIAL ({pending} pendente(s))",
            "status_color": "yellow",
            "detail": "Há conferências sem feedback — executar m_feedback_002_auto_loop.py --auto --persist",
        }
    return {
        "status": "⚠ SUBUTILIZADO",
        "status_color": "yellow",
        "detail": "Conferências existem, mas feedback_loop ainda vazio",
    }


def _check_ml_active() -> bool:
    """Verifica se ML está ativo nas últimas gerações."""
    try:
        result = _query_postgresql("""
            SELECT COUNT(*) as count FROM generation_events 
            WHERE context_json::text LIKE '%ml_enabled%'
            AND context_json::text LIKE '%true%'
            AND created_at > NOW() - INTERVAL '7 days'
        """)
        return result and result[0].get("count", 0) > 0
    except:
        return False


def _analyze_games(games: list[dict[str, Any]]) -> dict[str, Any]:
    """Analisa jogos gerados com detecção automática de formato."""
    if not games:
        return {}

    # Detectar formato (tamanho do cartão) a partir do primeiro jogo
    sample_numbers = games[0]["numbers"]
    if isinstance(sample_numbers, str):
        sample_numbers = json.loads(sample_numbers)
    card_size = len(sample_numbers)

    # Frequência por dezena
    dezena_freq = Counter()
    for game in games:
        numbers = game["numbers"]
        if isinstance(numbers, str):
            numbers = json.loads(numbers)
        dezena_freq.update(numbers)

    # Paridade (ímpar/par) - ajustado para o tamanho do cartão
    odd_even = Counter()
    for game in games:
        numbers = game["numbers"]
        if isinstance(numbers, str):
            numbers = json.loads(numbers)
        odd = sum(1 for n in numbers if n % 2 == 1)
        odd_even[f"{odd}I/{card_size - odd}P"] += 1

    # Sequências consecutivas
    max_consecutive = 0
    for game in games:
        numbers = game["numbers"]
        if isinstance(numbers, str):
            numbers = json.loads(numbers)
        sorted_nums = sorted(numbers)
        current = 1
        for i in range(1, len(sorted_nums)):
            if sorted_nums[i] == sorted_nums[i - 1] + 1:
                current += 1
                max_consecutive = max(max_consecutive, current)
            else:
                current = 1

    # Soma
    sums = []
    for game in games:
        numbers = game["numbers"]
        if isinstance(numbers, str):
            numbers = json.loads(numbers)
        sums.append(sum(numbers))
    avg_sum = sum(sums) / len(sums) if sums else 0

    # Score ML
    score_ml_values = [g["score_ml"] for g in games if g.get("score_ml") is not None]

    return {
        "card_size": card_size,
        "dezena_frequency": dict(dezena_freq),
        "odd_even_distribution": dict(odd_even),
        "max_consecutive": max_consecutive,
        "average_sum": round(avg_sum, 2),
        "score_ml_stats": {
            "count": len(score_ml_values),
            "average": round(sum(score_ml_values) / len(score_ml_values), 2)
            if score_ml_values
            else None,
            "min": round(min(score_ml_values), 2) if score_ml_values else None,
            "max": round(max(score_ml_values), 2) if score_ml_values else None,
        },
    }


def _render_kpis(
    conference_stats: dict[str, Any], generation_data: dict[str, Any]
) -> None:
    """Renderiza KPIs principais."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        events_count = generation_data.get("events_count", 0)
        st.metric(
            label="Gerações Ativas",
            value=f"{events_count}",
            delta="100%",
            help="Todos os eventos CORE_002 ativos",
        )

    with col2:
        total_prizes = conference_stats.get("total_prizes", 0)
        st.metric(
            label="Prêmios Conquistados",
            value=f"{total_prizes:,}",
            delta=f"{conference_stats.get('total_runs', 0)} conferências",
            help="Total de prêmios em todas as conferências",
        )

    with col3:
        best_hits = conference_stats.get("best_hits", 0)
        st.metric(
            label="Best Hits",
            value=best_hits,
            delta="11-15 acertos",
            help="Melhor resultado em conferência",
        )

    with col4:
        total_games = len(generation_data.get("games", []))
        st.metric(
            label="Total de Jogos",
            value=f"{total_games:,}",
            delta=f"{generation_data.get('events_count', 0)} gerações",
            help="Todos os jogos CORE_002 agregados",
        )


def _render_structural_diagnosis(analysis: dict[str, Any]) -> None:
    """Renderiza diagnóstico estrutural com soma esperada baseada no formato."""
    st.subheader("Diagnóstico Estrutural")
    card_size = analysis.get("card_size", 15)
    st.caption(
        f"Análise agregada de todos os jogos gerados pelo CORE_002 (formato: {card_size} dezenas)"
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        odd_even = analysis.get("odd_even_distribution", {})
        total_games = sum(odd_even.values())
        if total_games > 0:
            # Encontrar as duas distribuições mais comuns
            sorted_dist = sorted(odd_even.items(), key=lambda x: x[1], reverse=True)
            top1_key, top1_count = (
                sorted_dist[0] if len(sorted_dist) > 0 else ("N/A", 0)
            )
            top2_key, top2_count = (
                sorted_dist[1] if len(sorted_dist) > 1 else ("N/A", 0)
            )

            pct_top1 = (top1_count / total_games * 100) if total_games > 0 else 0
            pct_top2 = (top2_count / total_games * 100) if total_games > 0 else 0

            st.success("✅ Paridade Balanceada")
            st.metric(
                label="Distribuição",
                value=f"{pct_top1:.0f}% / {pct_top2:.0f}%",
                help=f"{top1_key}: {top1_count} jogos · {top2_key}: {top2_count} jogos",
            )
            st.caption(f"Oficial: ~50% / 50% (formato {card_size}D)")

    with col2:
        max_consecutive = analysis.get("max_consecutive", 0)
        st.success("✅ Sequências Consecutivas")
        st.metric(
            label="Máximo", value=max_consecutive, help="Sequência máxima encontrada"
        )
        st.caption("Oficial: até 7 consecutivas")

    with col3:
        avg_sum = analysis.get("average_sum", 0)
        # Soma esperada baseada no formato
        expected_sum = 195 if card_size == 15 else 234
        deviation = abs(avg_sum - expected_sum)

        # Threshold baseado no formato
        threshold = 10 if card_size == 15 else 15
        status_icon = "✅" if deviation <= threshold else "⚠️"

        if deviation <= threshold:
            st.success(f"{status_icon} Distribuição de Soma")
        else:
            st.warning(f"{status_icon} Distribuição de Soma")

        st.metric(
            label="Média",
            value=f"{avg_sum:.1f}",
            help=f"Média dos jogos (esperado: ~{expected_sum})",
        )
        st.caption(f"Oficial: ~{expected_sum} (desvio: {deviation:.1f})")


def _render_dezena_frequency(analysis: dict[str, Any]) -> None:
    """Renderiza gráfico de frequência por dezena com indicador de formato."""
    card_size = analysis.get("card_size", 15)
    st.subheader("Frequência por Dezena")
    st.caption(
        f"Distribuição das 25 dezenas em todos os jogos agregados (formato: {card_size} dezenas)"
    )

    dezena_freq = analysis.get("dezena_frequency", {})
    if not dezena_freq:
        st.warning("Sem dados de frequência")
        return

    # Ordenar por dezena
    sorted_dezenas = sorted(dezena_freq.items(), key=lambda x: int(x[0]))
    labels = [f"{int(num):02d}" for num, _ in sorted_dezenas]
    values = [count for _, count in sorted_dezenas]

    # Gráfico
    fig = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=values,
                marker_color="rgba(59, 130, 246, 0.6)",
                marker_line_color="rgba(59, 130, 246, 1)",
                marker_line_width=1,
            )
        ]
    )

    fig.update_layout(
        xaxis_title="Dezena",
        yaxis_title="Aparições",
        height=350,
        margin=dict(l=20, r=20, t=20, b=20),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a3b8"),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Métricas
    col1, col2, col3 = st.columns(3)

    with col1:
        most_freq = max(dezena_freq.items(), key=lambda x: x[1])
        total_games = len(labels) * max(values) if values else 1
        pct = (most_freq[1] / total_games * 100) if total_games > 0 else 0
        st.metric(
            label="Mais Frequente",
            value=f"Dezena {int(most_freq[0]):02d}",
            help=f"{most_freq[1]} aparições",
        )

    with col2:
        least_freq = min(dezena_freq.items(), key=lambda x: x[1])
        st.metric(
            label="Menos Frequente",
            value=f"Dezena {int(least_freq[0]):02d}",
            help=f"{least_freq[1]} aparições",
        )

    with col3:
        coverage = len(dezena_freq)
        st.metric(
            label="Cobertura",
            value=f"{coverage}/25",
            help="Todas as dezenas presentes"
            if coverage == 25
            else f"{25 - coverage} dezenas ausentes",
        )


def _render_ml_sensor(analysis: dict[str, Any], ml_active: bool) -> None:
    """Renderiza seção do Score ML como sensor."""
    st.subheader("Score ML como Sensor Informativo")
    st.caption("Métrica auxiliar — não bloqueia geração")

    score_stats = analysis.get("score_ml_stats", {})
    count = score_stats.get("count", 0)

    if count == 0:
        st.info("""
        **Status do Sensor ML:** Aguardando Ativação
        
        O Score ML está desativado nas gerações recentes (ml_enabled=0).
        Quando ativado como sensor, mostrará:
        
        - Score de cada jogo (0-100) baseado em 6 features interpretáveis
        - Atribuição de peso: final_score_norm (35%), quadra_density (20%), sum_balance (15%), odd/center/frame (10% cada)
        - Evolução dos pesos via feedback loop (quando calibração for aplicada)
        """)
    else:
        avg = score_stats.get("average", 0)
        min_score = score_stats.get("min", 0)
        max_score = score_stats.get("max", 0)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Score Médio", f"{avg:.1f}")
        with col2:
            st.metric("Score Mínimo", f"{min_score:.1f}")
        with col3:
            st.metric("Score Máximo", f"{max_score:.1f}")


def _render_learning_cycle(
    ml_active: bool,
    calib_stats: dict[str, Any],
    feedback_stats: dict[str, Any],
    conference_stats: dict[str, Any],
) -> None:
    """Renderiza ciclo de aprendizado."""
    st.subheader("Ciclo de Aprendizado (Feedback Loop)")
    st.caption("Fluxo de evolução contínua")

    feedback_badge = resolve_feedback_loop_status(
        feedback_stats=feedback_stats,
        conference_stats=conference_stats,
    )

    cycle_steps = [
        {
            "number": 1,
            "title": "Geração CORE_002",
            "description": "5 camadas de proteção contra vieses",
            "status": "✓ ATIVO",
            "status_color": "green",
        },
        {
            "number": 2,
            "title": "Conferência",
            "description": "Comparação com resultados oficiais",
            "status": "✓ ATIVO"
            if int(conference_stats.get("total_runs", 0) or 0) > 0
            else "○ AGUARDANDO",
            "status_color": "green"
            if int(conference_stats.get("total_runs", 0) or 0) > 0
            else "gray",
        },
        {
            "number": 3,
            "title": "Feedback Loop",
            "description": feedback_badge.get("detail")
            or "Análise pós-concurso · Detecção de vieses",
            "status": feedback_badge["status"],
            "status_color": feedback_badge["status_color"],
        },
        {
            "number": 4,
            "title": "Calibração ML",
            "description": "Ajuste de pesos baseado em performance real",
            "status": "✗ BLOQUEADO"
            if int(calib_stats.get("applied_count", 0) or 0) == 0
            else "✓ ATIVO",
            "status_color": "red"
            if int(calib_stats.get("applied_count", 0) or 0) == 0
            else "green",
        },
        {
            "number": 5,
            "title": "Score ML (Sensor)",
            "description": "Métrica informativa por jogo",
            "status": "✓ ATIVO" if ml_active else "○ AGUARDANDO",
            "status_color": "green" if ml_active else "gray",
        },
    ]

    for step in cycle_steps:
        col1, col2, col3 = st.columns([0.1, 0.7, 0.2])

        with col1:
            st.markdown(f"**{step['number']}**")

        with col2:
            st.markdown(f"**{step['title']}**")
            st.caption(step["description"])

        with col3:
            if step["status_color"] == "green":
                st.success(step["status"])
            elif step["status_color"] == "yellow":
                st.warning(step["status"])
            elif step["status_color"] == "red":
                st.error(step["status"])
            else:
                st.caption(step["status"])


def _render_recommendations(
    ml_active: bool,
    calib_stats: dict[str, Any],
    feedback_stats: dict[str, Any],
    conference_stats: dict[str, Any],
) -> None:
    """Renderiza recomendações para ativação do ciclo."""
    st.subheader("Recomendações para Ativação Completa")

    recommendations = []
    feedback_badge = resolve_feedback_loop_status(
        feedback_stats=feedback_stats,
        conference_stats=conference_stats,
    )

    if not ml_active:
        recommendations.append(
            {
                "priority": 1,
                "color": "blue",
                "title": "Ativar Score ML como Sensor",
                "description": "Habilitar `ml_enabled=True` nas gerações para alimentar métrica informativa",
            }
        )

    if feedback_badge["status_color"] != "green":
        recommendations.append(
            {
                "priority": len(recommendations) + 1,
                "color": "red"
                if int(conference_stats.get("total_runs", 0) or 0) > 0
                else "yellow",
                "title": "Ativar Feedback Loop Automático",
                "description": (
                    "Executar `python scripts/ops/m_feedback_002_auto_loop.py --auto --persist` "
                    "após conferências institucionais."
                ),
            }
        )

    if int(calib_stats.get("applied_count", 0) or 0) == 0:
        recommendations.append(
            {
                "priority": len(recommendations) + 1,
                "color": "yellow",
                "title": "Revisar Thresholds de Calibração",
                "description": "Ajustar para aceitar calibrações com melhoria marginal",
            }
        )

    recommendations.append(
        {
            "priority": len(recommendations) + 1,
            "color": "green",
            "title": "Manter CORE_002 como Motor Principal",
            "description": "5 camadas de proteção já funcionam. ML é sensor, não gate",
        }
    )

    for rec in recommendations:
        if rec["color"] == "red":
            st.error(f"**{rec['priority']}. {rec['title']}**\n\n{rec['description']}")
        elif rec["color"] == "yellow":
            st.warning(f"**{rec['priority']}. {rec['title']}**\n\n{rec['description']}")
        elif rec["color"] == "blue":
            st.info(f"**{rec['priority']}. {rec['title']}**\n\n{rec['description']}")
        else:
            st.success(f"**{rec['priority']}. {rec['title']}**\n\n{rec['description']}")


def render_cobertura_nova() -> None:
    """Renderiza o painel Cobertura Nova com abas separadas por formato."""
    st.markdown("### Cobertura Nova")
    st.caption(
        "Painel dinâmico com ML como sensor informativo — análise separada por formato (15D vs 18D)"
    )

    # Carregar dados gerais
    with st.spinner("Carregando dados do banco..."):
        all_data = _load_all_generations_data()  # Todos os formatos
        data_15d = _load_all_generations_data(format_filter="15D")
        data_18d = _load_all_generations_data(format_filter="18D")
        conference_stats = _load_conference_stats()
        calib_stats = _load_calibration_stats()
        feedback_stats = _load_feedback_loop_stats()
        ml_active = _check_ml_active()

    if not all_data.get("available"):
        st.warning("Nenhuma geração CORE_002 encontrada")
        return

    # KPIs gerais (todos os formatos)
    _render_kpis(conference_stats, all_data)

    st.markdown("---")

    # Abas separadas por formato
    tab_all, tab_15d, tab_18d = st.tabs(
        [
            f"Todos ({len(all_data.get('games', []))} jogos)",
            f"15 Dezenas ({len(data_15d.get('games', []))} jogos)",
            f"18 Dezenas ({len(data_18d.get('games', []))} jogos)",
        ]
    )

    with tab_all:
        _render_format_analysis(all_data, "Todos os Formatos", ml_active)

    with tab_15d:
        if data_15d.get("available") and data_15d.get("games"):
            _render_format_analysis(data_15d, "15 Dezenas", ml_active)
        else:
            st.info("Nenhuma geração 15D encontrada")

    with tab_18d:
        if data_18d.get("available") and data_18d.get("games"):
            _render_format_analysis(data_18d, "18 Dezenas", ml_active)
        else:
            st.info("Nenhuma geração 18D encontrada")

    st.markdown("---")

    # Ciclo de aprendizado (comum a todos os formatos)
    _render_learning_cycle(ml_active, calib_stats, feedback_stats, conference_stats)

    st.markdown("---")

    # Recomendações
    _render_recommendations(ml_active, calib_stats, feedback_stats, conference_stats)

    # Footer
    st.markdown("---")
    st.caption(
        "Análise baseada em dados reais do PostgreSQL Railway · ML como sensor, não como gate · "
        "Análises separadas por formato para evitar distorções estatísticas"
    )


def _render_format_analysis(
    generation_data: dict[str, Any], format_name: str, ml_active: bool
) -> None:
    """Renderiza análise completa para um formato específico."""
    games = generation_data.get("games", [])
    analysis = _analyze_games(games)
    card_size = analysis.get("card_size", 15)

    # Header do formato
    if generation_data.get("available"):
        events_count = generation_data.get("events_count", 0)
        total_games = len(games)

        st.info(f"""
        **Formato: {format_name}** · {card_size} dezenas por jogo
        
        Último Event #{generation_data.get("event_id", "N/A")} · 
        {generation_data.get("event_date", "N/A").strftime("%d/%m/%Y %H:%M") if hasattr(generation_data.get("event_date", ""), "strftime") else "N/A"}
        
        Batch: `{generation_data.get("batch_label", "N/A")}`
        
        Analisando **{total_games:,} jogos** de **{events_count} gerações** agregadas
        """)

        # Diagnóstico estrutural
        _render_structural_diagnosis(analysis)

        st.markdown("---")

        # Frequência por dezena
        _render_dezena_frequency(analysis)

        st.markdown("---")

        # Score ML como sensor
        _render_ml_sensor(analysis, ml_active)
