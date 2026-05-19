def _find_contest(
    contest_id: int,
    history_path: Path,
):

    draws = list(
        load_draws_csv(history_path)
    )

    if not draws:

        raise PublicContestNotFoundError(
            "Nenhum concurso encontrado."
        )

    available_contests = [
        draw.contest
        for draw in draws
    ]

    latest_contest = max(
        available_contests
    )

    if contest_id > latest_contest:

        raise PublicContestNotFoundError(
            (
                f"Concurso {contest_id} "
                f"ainda não disponível. "
                f"Último concurso carregado: "
                f"{latest_contest}."
            )
        )

    for draw in draws:

        if draw.contest == contest_id:
            return draw

    raise PublicContestNotFoundError(
        (
            f"Concurso {contest_id} "
            f"não encontrado na base histórica."
        )
    )
