import argparse
import json

try:
    from . import _bootstrap  # type: ignore[import-not-found]  # noqa: F401
except ImportError:
    import _bootstrap  # type: ignore[no-redef]  # noqa: F401

from lotoia.backtesting import run_backtest


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa backtesting historico do LotoIA.")
    parser.add_argument("--contests", type=int, default=5, help="Quantidade de concursos analisados.")
    parser.add_argument("--games", type=int, default=5, help="Quantidade de jogos por concurso.")
    parser.add_argument("--pool-size", type=int, default=20, help="Tamanho do pool de candidatos.")
    parser.add_argument(
        "--history-window",
        type=int,
        default=200,
        help="Quantidade de concursos historicos anteriores usados por alvo.",
    )
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


if __name__ == "__main__":
    main()
