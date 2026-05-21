from __future__ import annotations

import argparse
import json

try:
    from . import _bootstrap  # type: ignore[import-not-found]  # noqa: F401
except ImportError:
    import _bootstrap  # type: ignore[no-redef]  # noqa: F401

from lotoia.experiments.supervised_walk_forward import run_score_ml_walk_forward


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Execute the official score_ml expanding-window walk-forward validation.",
    )
    parser.add_argument("--min-train-size", type=int, default=2000)
    parser.add_argument("--test-size", type=int, default=10)
    parser.add_argument("--step-size", type=int, default=10)
    parser.add_argument("--games-count", type=int, default=10)
    parser.add_argument("--pool-size", type=int, default=30)
    parser.add_argument("--history-window", type=int, default=200)
    parser.add_argument("--max-training-contests", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-registry-update", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_score_ml_walk_forward(
        min_train_size=args.min_train_size,
        test_size=args.test_size,
        step_size=args.step_size,
        games_count=args.games_count,
        pool_size=args.pool_size,
        history_window=args.history_window,
        max_training_contests=args.max_training_contests,
        seed=args.seed,
        update_registries=not args.no_registry_update,
    )
    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
