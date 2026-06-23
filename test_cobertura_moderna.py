#!/usr/bin/env python3
"""Script de teste para o módulo de Cobertura Estrutural Moderna v2.

Este script testa as funções principais do módulo sem precisar do Streamlit.
"""

import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from dashboard.institutional_structural_coverage_modern_v2 import (
    _load_latest_generation_data,
    _load_conference_stats,
    _analyze_games,
)


def test_load_generation_data():
    """Testa o carregamento de dados de geração."""
    print("📊 Testando carregamento de dados de geração...")
    data = _load_latest_generation_data()

    if not data.get("available"):
        print("❌ Nenhum dado de geração encontrado")
        return False

    print(f"✅ Event #{data['event_id']} encontrado")
    print(f"   Data: {data['event_date']}")
    print(f"   Batch: {data['batch_label']}")
    print(f"   Jogos: {len(data['games'])}")

    return True


def test_load_conference_stats():
    """Testa o carregamento de estatísticas de conferência."""
    print("\n🏆 Testando carregamento de estatísticas de conferência...")
    stats = _load_conference_stats()

    print(f"✅ Estatísticas carregadas:")
    print(f"   Total de runs: {stats.get('total_runs', 0)}")
    print(f"   Total de prêmios: {stats.get('total_prizes', 0)}")
    print(f"   Best hits: {stats.get('best_hits', 0)}")
    print(f"   Concursos distintos: {stats.get('distinct_contests', 0)}")

    return True


def test_analyze_games():
    """Testa a análise de jogos."""
    print("\n🔍 Testando análise de jogos...")
    data = _load_latest_generation_data()

    if not data.get("available") or not data.get("games"):
        print("❌ Nenhum jogo para analisar")
        return False

    analysis = _analyze_games(data["games"])

    print(f"✅ Análise concluída:")
    print(f"   Dezenas únicas: {len(analysis.get('dezena_frequency', {}))}")
    print(f"   Distribuição paridade: {analysis.get('odd_even_distribution', {})}")
    print(f"   Sequência máxima: {analysis.get('max_consecutive', 0)}")
    print(f"   Soma média: {analysis.get('average_sum', 0)}")

    score_stats = analysis.get("score_ml_stats", {})
    print(f"   Score ML: {score_stats.get('count', 0)} jogos com score")

    return True


def main():
    """Executa todos os testes."""
    print("=" * 60)
    print("🧪 Testes do Módulo Cobertura Estrutural Moderna v2")
    print("=" * 60)

    tests = [
        test_load_generation_data,
        test_load_conference_stats,
        test_analyze_games,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Erro no teste: {e}")
            import traceback

            traceback.print_exc()
            results.append(False)

    print("\n" + "=" * 60)
    print(f"📊 Resultados: {sum(results)}/{len(results)} testes passaram")
    print("=" * 60)

    if all(results):
        print("✅ Todos os testes passaram!")
        return 0
    else:
        print("❌ Alguns testes falharam")
        return 1


if __name__ == "__main__":
    sys.exit(main())
