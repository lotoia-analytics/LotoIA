from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from . import _bootstrap  # type: ignore[import-not-found]  # noqa: F401
except ImportError:
    import _bootstrap  # type: ignore[no-redef]  # noqa: F401

from lotoia.benchmark import run_benchmark


def main() -> None:
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


if __name__ == "__main__":
    main()
