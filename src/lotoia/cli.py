from __future__ import annotations

import argparse
import json
from pathlib import Path

from lotoia.backtesting import run_backtest
from lotoia.benchmark import run_benchmark
from lotoia.calibration import WeightConfiguration, compare_weight_configurations
from lotoia.database import DEFAULT_DATABASE_PATH, create_database, list_runs
from lotoia.reports import generate_backtest_report
from lotoia.statistics.advanced import FINAL_SCORE_WEIGHTS


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run_basic_analysis_cli() -> None:
    from lotoia.statistics.basic import summarize_draws

    summary = summarize_draws([])
    print("LotoIA - analise inicial")
    print(f"Concursos carregados: {summary['total_draws']}")
    print(f"Dezenas monitoradas: {summary['numbers_tracked']}")


def run_backtest_cli() -> None:
    parser = argparse.ArgumentParser(description="Executa backtesting historico do LotoIA.")
    parser.add_argument("--contests", type=int, default=5, help="Quantidade de concursos analisados.")
    parser.add_argument("--games", type=int, default=5, help="Quantidade de jogos por concurso.")
    parser.add_argument("--pool-size", type=int, default=20, help="Tamanho do pool de candidatos.")
    parser.add_argument("--history-window", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42, help="Seed para geracao reprodutivel.")
    args = parser.parse_args()

    result = run_backtest(
        contests_analyzed=args.contests,
        games_count=args.games,
        pool_size=args.pool_size,
        history_window=args.history_window,
        seed=args.seed,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


def run_benchmark_cli() -> None:
    parser = argparse.ArgumentParser(description="Executa benchmark cientifico do LotoIA.")
    parser.add_argument("--contests", type=int, default=5)
    parser.add_argument("--games", type=int, default=5)
    parser.add_argument("--pool-size", type=int, default=20)
    parser.add_argument("--history-window", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=Path("reports/benchmark"))
    args = parser.parse_args()

    result = run_benchmark(
        contests_analyzed=args.contests,
        games_count=args.games,
        pool_size=args.pool_size,
        history_window=args.history_window,
        seed=args.seed,
        output_dir=args.output_dir,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


def run_dashboard_cli() -> None:
    from streamlit.web import bootstrap

    dashboard_path = PROJECT_ROOT / "dashboard" / "app.py"
    bootstrap.run(
        str(dashboard_path),
        False,
        [],
        {
            "server.port": 8501,
            "server.headless": True,
            "browser.gatherUsageStats": False,
        },
    )


def init_database_cli() -> None:
    create_database()
    print(f"Banco inicializado em {DEFAULT_DATABASE_PATH}")


def show_runs_cli() -> None:
    print(json.dumps(list_runs(), ensure_ascii=False, indent=2, default=str))


def run_weight_calibration_cli() -> None:
    parser = argparse.ArgumentParser(description="Compara configuracoes de pesos do LotoIA.")
    parser.add_argument("--contests", type=int, default=3)
    parser.add_argument("--games", type=int, default=3)
    parser.add_argument("--pool-size", type=int, default=8)
    parser.add_argument("--history-window", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    result = compare_weight_configurations(
        configurations=[_official_configuration(), _balanced_configuration()],
        contests_analyzed=args.contests,
        games_count=args.games,
        pool_size=args.pool_size,
        history_window=args.history_window,
        seed=args.seed,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def run_reports_cli() -> None:
    parser = argparse.ArgumentParser(description="Gera relatorios analiticos do LotoIA.")
    parser.add_argument("--contests", type=int, default=3)
    parser.add_argument("--games", type=int, default=3)
    parser.add_argument("--pool-size", type=int, default=8)
    parser.add_argument("--history-window", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=Path("reports"))
    args = parser.parse_args()

    backtest = run_backtest(
        contests_analyzed=args.contests,
        games_count=args.games,
        pool_size=args.pool_size,
        history_window=args.history_window,
        seed=args.seed,
    )
    calibration = compare_weight_configurations(
        [_official_configuration(), _balanced_configuration()],
        contests_analyzed=args.contests,
        games_count=args.games,
        pool_size=args.pool_size,
        history_window=args.history_window,
        seed=args.seed,
    )
    summary = generate_backtest_report(backtest, calibration, args.output_dir)
    print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))


def _official_configuration() -> WeightConfiguration:
    return WeightConfiguration(
        name="official",
        duo=FINAL_SCORE_WEIGHTS["duo_score"],
        terno=FINAL_SCORE_WEIGHTS["terno_score"],
        quadra=FINAL_SCORE_WEIGHTS["quadra_score"],
        quina=FINAL_SCORE_WEIGHTS["quina_score"],
        delay=FINAL_SCORE_WEIGHTS["delay_score"],
        frequency=FINAL_SCORE_WEIGHTS["frequency_score"],
        sum=FINAL_SCORE_WEIGHTS["sum_score"],
        sequence=FINAL_SCORE_WEIGHTS["sequence_score"],
    )


def _balanced_configuration() -> WeightConfiguration:
    return WeightConfiguration("balanced_experimental", 12, 16, 20, 18, 12, 10, 6, 6)
