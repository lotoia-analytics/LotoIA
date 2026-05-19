try:
    from . import _bootstrap  # type: ignore[import-not-found]  # noqa: F401
except ImportError:
    import _bootstrap  # type: ignore[no-redef]  # noqa: F401

from lotoia.statistics.basic import summarize_draws


def main() -> None:
    summary = summarize_draws([])
    print("LotoIA - analise inicial")
    print(f"Concursos carregados: {summary['total_draws']}")
    print(f"Dezenas monitoradas: {summary['numbers_tracked']}")


if __name__ == "__main__":
    main()
