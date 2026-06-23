"""Teste do módulo Cobertura Estrutural Moderna v2."""

import sys
from pathlib import Path

# Adiciona o diretório src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dashboard.institutional_structural_coverage_modern_v2 import (
    _load_latest_generation_data,
    _load_conference_stats,
    _analyze_games,
)


def test_load_latest_generation_data():
    """Testa o carregamento de dados da geração mais recente."""
    print("Testando _load_latest_generation_data...")
    try:
        data = _load_latest_generation_data()
        print(f"✓ Dados carregados: {data}")
        print(f"  Tipo: {type(data)}")
        if isinstance(data, dict):
            print(f"  Chaves: {data.keys()}")
            print(f"  Jogos: {len(data.get('games', []))}")
        return data
    except Exception as e:
        print(f"✗ Erro ao carregar dados: {e}")
        import traceback

        traceback.print_exc()
        return None


def test_load_conference_stats():
    """Testa o carregamento de estatísticas de conferência."""
    print("\nTestando _load_conference_stats...")
    try:
        stats = _load_conference_stats()
        print(f"✓ Estatísticas carregadas:")
        print(f"  - Total de conferências: {stats.get('total_conferences', 0)}")
        print(f"  - Total de prêmios: {stats.get('total_prizes', 0)}")
        print(f"  - Melhor resultado: {stats.get('best_hits', 0)} acertos")
        return stats
    except Exception as e:
        print(f"✗ Erro ao carregar estatísticas: {e}")
        return None


def test_analyze_games(games_data):
    """Testa a análise de jogos."""
    if not games_data:
        print("\n✗ Não há dados de jogos para analisar")
        return

    print("\nTestando _analyze_games...")
    try:
        analysis = _analyze_games(games_data)
        print(f"✓ Análise concluída:")
        print(f"  - Total de jogos: {analysis.get('total_games', 0)}")
        print(
            f"  - Frequência por dezena: {len(analysis.get('dezena_frequency', {}))} dezenas"
        )
        print(f"  - Distribuição paridade: {analysis.get('odd_even_distribution', {})}")
        print(f"  - Soma média: {analysis.get('average_sum', 0)}")
        return analysis
    except Exception as e:
        print(f"✗ Erro ao analisar jogos: {e}")
        return None


def test_load_conference_stats():
    """Testa o carregamento de estatísticas de conferência."""
    print("\nTestando load_conference_stats...")
    try:
        stats = load_conference_stats()
        print(f"✓ Estatísticas carregadas:")
        print(f"  - Total de conferências: {stats.get('total_conferences', 0)}")
        print(f"  - Total de prêmios: {stats.get('total_prizes', 0)}")
        print(f"  - Melhor resultado: {stats.get('best_hits', 0)} acertos")
        return stats
    except Exception as e:
        print(f"✗ Erro ao carregar estatísticas: {e}")
        return None


def test_analyze_games(games_data):
    """Testa a análise de jogos."""
    if not games_data:
        print("\n✗ Não há dados de jogos para analisar")
        return

    print("\nTestando analyze_games...")
    try:
        analysis = analyze_games(games_data)
        print(f"✓ Análise concluída:")
        print(f"  - Total de jogos: {analysis.get('total_games', 0)}")
        print(
            f"  - Frequência por dezena: {len(analysis.get('dezena_frequency', {}))} dezenas"
        )
        print(f"  - Distribuição paridade: {analysis.get('odd_even_distribution', {})}")
        print(f"  - Soma média: {analysis.get('average_sum', 0)}")
        return analysis
    except Exception as e:
        print(f"✗ Erro ao analisar jogos: {e}")
        return None


def main():
    """Executa todos os testes."""
    print("=" * 60)
    print("TESTE DO MÓDULO COBERTURA ESTRUTURAL MODERNA V2")
    print("=" * 60)

    # Testa carregamento de dados
    games_data = test_load_latest_generation_data()

    # Testa estatísticas de conferência
    conference_stats = test_load_conference_stats()

    # Testa análise de jogos
    if games_data and games_data.get("available") and games_data.get("games"):
        analysis = _analyze_games(games_data["games"])
    else:
        print("\n✗ Não há dados de jogos disponíveis para analisar")

    print("\n" + "=" * 60)
    print("TESTE CONCLUÍDO")
    print("=" * 60)


if __name__ == "__main__":
    main()
