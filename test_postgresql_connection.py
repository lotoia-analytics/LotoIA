"""Teste de conexão com PostgreSQL Railway."""

import os
import sys
from pathlib import Path

# Adiciona o diretório src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Configura a URL do banco de dados
os.environ["DATABASE_URL"] = (
    "postgresql://postgres:gbkOvFoWDNlEWyywiqGtareFHpXALtzN@reseau.proxy.rlwy.net:17383/railway"
)

from dashboard.institutional_structural_coverage_modern_v2 import (
    _load_latest_generation_data,
    _load_conference_stats,
    _analyze_games,
)


def main():
    """Testa a conexão e carregamento de dados."""
    print("=" * 60)
    print("TESTE DE CONEXÃO COM POSTGRESQL RAILWAY")
    print("=" * 60)

    # Testa carregamento de dados
    print("\n1. Testando _load_latest_generation_data...")
    try:
        data = _load_latest_generation_data()
        print(f"   ✓ Dados carregados: {data.get('available', False)}")
        if data.get("available"):
            print(f"   - Event ID: {data.get('event_id')}")
            print(f"   - Batch: {data.get('batch_label')}")
            print(f"   - Jogos: {len(data.get('games', []))}")
    except Exception as e:
        print(f"   ✗ Erro: {e}")
        import traceback

        traceback.print_exc()

    # Testa estatísticas de conferência
    print("\n2. Testando _load_conference_stats...")
    try:
        stats = _load_conference_stats()
        print(f"   ✓ Estatísticas carregadas:")
        print(f"   - Total de conferências: {stats.get('total_runs', 0)}")
        print(f"   - Total de prêmios: {stats.get('total_prizes', 0)}")
        print(f"   - Melhor resultado: {stats.get('best_hits', 0)} acertos")
    except Exception as e:
        print(f"   ✗ Erro: {e}")
        import traceback

        traceback.print_exc()

    # Testa análise de jogos
    print("\n3. Testando _analyze_games...")
    if data.get("available") and data.get("games"):
        try:
            analysis = _analyze_games(data["games"])
            print(f"   ✓ Análise concluída:")
            print(f"   - Total de jogos: {len(data['games'])}")
            print(f"   - Dezenas únicas: {len(analysis.get('dezena_frequency', {}))}")
            print(f"   - Soma média: {analysis.get('average_sum', 0)}")
        except Exception as e:
            print(f"   ✗ Erro: {e}")
            import traceback

            traceback.print_exc()
    else:
        print("   ✗ Não há dados de jogos disponíveis")

    print("\n" + "=" * 60)
    print("TESTE CONCLUÍDO")
    print("=" * 60)


if __name__ == "__main__":
    main()
