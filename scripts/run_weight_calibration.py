import argparse
import json

try:
    from . import _bootstrap  # type: ignore[import-not-found]  # noqa: F401
except ImportError:
    import _bootstrap  # type: ignore[no-redef]  # noqa: F401

from lotoia.calibration import WeightConfiguration, compare_weight_configurations
from lotoia.statistics.advanced import FINAL_SCORE_WEIGHTS


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
    return WeightConfiguration(
        name="balanced_experimental",
        duo=12,
        terno=16,
        quadra=20,
        quina=18,
        delay=12,
        frequency=10,
        sum=6,
        sequence=6,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Compara configuracoes de pesos do LotoIA.")
    parser.add_argument("--contests", type=int, default=3, help="Quantidade de concursos analisados.")
    parser.add_argument("--games", type=int, default=3, help="Quantidade de jogos por concurso.")
    parser.add_argument("--pool-size", type=int, default=8, help="Tamanho do pool de candidatos.")
    parser.add_argument(
        "--history-window",
        type=int,
        default=100,
        help="Quantidade de concursos historicos anteriores usados por alvo.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Seed para geracao reprodutivel.")
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


if __name__ == "__main__":
    main()
