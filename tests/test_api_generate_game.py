import json
from urllib.parse import urlsplit

import anyio

from backend.main import app


def get_json(path: str) -> tuple[int, dict[str, object]]:
    async def request() -> tuple[int, dict[str, object]]:
        messages: list[dict[str, object]] = []
        received = False
        url = urlsplit(path)

        async def receive() -> dict[str, object]:
            nonlocal received
            if received:
                return {"type": "http.disconnect"}
            received = True
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        await app(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "GET",
                "scheme": "http",
                "path": url.path,
                "raw_path": url.path.encode(),
                "query_string": url.query.encode(),
                "headers": [],
                "client": ("testclient", 50000),
                "server": ("testserver", 80),
                "root_path": "",
            },
            receive,
            send,
        )

        start = next(message for message in messages if message["type"] == "http.response.start")
        body = b"".join(
            message.get("body", b"")
            for message in messages
            if message["type"] == "http.response.body"
        )
        return start["status"], json.loads(body)

    return anyio.run(request)


def test_generate_game_returns_status_200() -> None:
    status_code, _ = get_json("/generate/game")

    assert status_code == 200


def test_generate_game_returns_15_numbers() -> None:
    _, data = get_json("/generate/game")

    assert len(data["numbers"]) == 15
    assert len(set(data["numbers"])) == 15


def test_generate_game_numbers_are_between_1_and_25() -> None:
    _, data = get_json("/generate/game")

    assert all(1 <= number <= 25 for number in data["numbers"])


def test_generate_game_returns_expected_json() -> None:
    _, data = get_json("/generate/game")

    assert set(data) == {
        "numbers",
        "odd",
        "even",
        "sum",
        "frame",
        "center",
        "quadra_score",
        "final_score",
    }
    assert isinstance(data["numbers"], list)
    assert isinstance(data["odd"], int)
    assert isinstance(data["even"], int)
    assert isinstance(data["sum"], int)
    assert isinstance(data["frame"], int)
    assert isinstance(data["center"], int)


def test_generate_game_returns_quadra_score_structure() -> None:
    _, data = get_json("/generate/game")

    assert set(data["quadra_score"]) == {
        "found_quadras",
        "total_frequency",
        "average_frequency",
        "average_rank",
        "top_quadras",
    }


def test_generate_game_returns_final_score_structure() -> None:
    _, data = get_json("/generate/game")

    assert set(data["final_score"]) == {"final_score", "components"}
    assert set(data["final_score"]["components"]) == {
        "duo_score",
        "terno_score",
        "quadra_score",
        "quina_score",
        "delay_score",
        "frequency_score",
        "sum_score",
        "sequence_score",
    }


def test_generate_games_returns_requested_count() -> None:
    status_code, data = get_json("/generate/games?count=3&max_repeated=9")

    assert status_code == 200
    assert data["count"] == 3
    assert len(data["games"]) == 3


def test_generate_games_returns_unique_games() -> None:
    _, data = get_json("/generate/games?count=3&max_repeated=9")
    game_keys = [tuple(game["numbers"]) for game in data["games"]]

    assert len(set(game_keys)) == len(game_keys)


def test_generate_games_respects_max_repeated() -> None:
    _, data = get_json("/generate/games?count=3&max_repeated=9")

    for index, game in enumerate(data["games"]):
        for previous_game in data["games"][:index]:
            repeated = len(set(game["numbers"]) & set(previous_game["numbers"]))
            assert repeated <= 9


def test_generate_games_returns_valid_numbers() -> None:
    _, data = get_json("/generate/games?count=3&max_repeated=9")

    for game in data["games"]:
        assert len(game["numbers"]) == 15
        assert len(set(game["numbers"])) == 15
        assert all(1 <= number <= 25 for number in game["numbers"])


def test_generate_games_returns_quadra_score_for_all_games() -> None:
    _, data = get_json("/generate/games?count=3&max_repeated=9")

    assert all("quadra_score" in game for game in data["games"])


def test_generate_games_returns_final_score_for_all_games() -> None:
    _, data = get_json("/generate/games?count=3&max_repeated=9")

    assert all("final_score" in game for game in data["games"])


def test_generate_best_games_endpoint_returns_requested_count() -> None:
    status_code, data = get_json("/generate/best-games?count=3&pool_size=5")

    assert status_code == 200
    assert data["count"] == 3
    assert len(data["games"]) == 3


def test_generate_best_games_endpoint_returns_quadra_score() -> None:
    _, data = get_json("/generate/best-games?count=3&pool_size=5")

    assert all("quadra_score" in game for game in data["games"])


def test_generate_best_games_endpoint_returns_final_score() -> None:
    _, data = get_json("/generate/best-games?count=3&pool_size=5")

    assert all("final_score" in game for game in data["games"])
