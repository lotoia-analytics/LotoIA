import json
from urllib.parse import urlsplit

import anyio
import pytest

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


def test_generate_game_legacy_path_blocked() -> None:
    status_code, _ = get_json("/generate/game")

    assert status_code == 500


def test_generate_games_legacy_path_blocked() -> None:
    status_code, data = get_json("/generate/games?count=3&max_repeated=9")

    assert status_code == 422
    assert "Geração Lei 15 bloqueada" in str(data.get("detail", ""))


def test_generate_best_games_legacy_path_blocked() -> None:
    status_code, data = get_json("/generate/best-games?count=3&pool_size=5")

    assert status_code == 422
    assert "Geração Lei 15 bloqueada" in str(data.get("detail", ""))
    assert "batch_label=None" in str(data.get("detail", ""))


@pytest.mark.parametrize(
    "path",
    [
        "/generate/game",
        "/generate/games?count=3&max_repeated=9",
        "/generate/best-games?count=3&pool_size=5",
    ],
)
def test_legacy_generate_endpoints_do_not_return_games(path: str) -> None:
    status_code, data = get_json(path)

    assert status_code != 200
    assert "games" not in data or not data.get("games")
    assert "numbers" not in data or not data.get("numbers")
