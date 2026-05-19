from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

import anyio
from sqlalchemy import text

from backend.main import app
from lotoia.database.database import get_session
from lotoia.public.persistence import (
    CheckEventRepository,
    GenerationEventRepository,
    LeadRepository,
    initialize_public_persistence,
)
from lotoia.public.service import (
    PublicCheckRequest,
    PublicGenerationRequest,
    PublicLimiter,
    check_public_contest,
    generate_public_games,
)
from lotoia.public.services import LeadCaptureRequest, LeadCaptureService, hash_ip, normalize_whatsapp


def post_json(path: str, payload: dict[str, object]) -> tuple[int, dict[str, object]]:
    async def request() -> tuple[int, dict[str, object]]:
        messages: list[dict[str, object]] = []
        received = False
        url = urlsplit(path)
        body = json.dumps(payload).encode()

        async def receive() -> dict[str, object]:
            nonlocal received
            if received:
                return {"type": "http.disconnect"}
            received = True
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message: dict[str, object]) -> None:
            messages.append(message)

        await app(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "POST",
                "scheme": "http",
                "path": url.path,
                "raw_path": url.path.encode(),
                "query_string": url.query.encode(),
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"user-agent", b"pytest"),
                    (b"x-forwarded-for", b"127.0.0.1"),
                ],
                "client": ("testclient", 50000),
                "server": ("testserver", 80),
                "root_path": "",
            },
            receive,
            send,
        )

        start = next(message for message in messages if message["type"] == "http.response.start")
        response_body = b"".join(
            message.get("body", b"")
            for message in messages
            if message["type"] == "http.response.body"
        )
        return start["status"], json.loads(response_body)

    return anyio.run(request)


def test_public_repository_persists_lead_generation_and_check(tmp_path: Path) -> None:
    db_path = tmp_path / "lotoia.db"
    initialize_public_persistence(db_path)
    leads = LeadRepository(db_path)
    generations = GenerationEventRepository(db_path)
    checks = CheckEventRepository(db_path)
    lead = leads.insert(
        first_name="Ana",
        whatsapp="11999999999",
        source="test",
        ip_hash="hash",
        user_agent="pytest",
    )
    generation = generations.insert(
        lead_id=lead["id"],
        generated_games=[{"numbers": list(range(1, 16))}],
        ml_enabled=False,
        seed=123,
        strategy="test",
        ranking_score=10.5,
        execution_time_ms=1.2,
    )
    check = checks.insert(
        lead_id=lead["id"],
        contest_id=1,
        selected_numbers=list(range(1, 16)),
        hits=15,
        result_payload={"hits": 15},
    )

    with get_session(db_path) as session:
        assert lead["id"] == 1
        assert generation["lead_id"] == 1
        assert check["lead_id"] == 1
        assert session.execute(text("select count(*) from leads")).scalar() == 1
        assert len(generations.list_by_lead(1)) == 1
        assert len(checks.list_by_lead(1)) == 1


def test_lead_capture_rejects_invalid_first_name() -> None:
    for value in ["", " ", "A"]:
        try:
            LeadCaptureRequest(first_name=value, whatsapp="11999999999")
        except Exception as exc:
            assert "first_name" in str(exc)
        else:
            raise AssertionError("Expected first_name validation to fail")


def test_lead_capture_rejects_invalid_whatsapp() -> None:
    for value in ["", "abc", "11-1", "(11) 99999-999999999999"]:
        try:
            LeadCaptureRequest(first_name="Ana", whatsapp=value)
        except Exception as exc:
            assert "whatsapp" in str(exc)
        else:
            raise AssertionError("Expected whatsapp validation to fail")


def test_whatsapp_normalization_and_hashing() -> None:
    assert normalize_whatsapp("(11) 99999-9999") == "11999999999"
    assert len(hash_ip("127.0.0.1")) == 64


def test_public_limiter_enforces_cooldown() -> None:
    limiter = PublicLimiter(cooldown_seconds=10, max_requests_per_window=2, window_seconds=60)

    assert limiter.check("client", now=100) == (True, "ok")
    assert limiter.check("client", now=101) == (False, "cooldown")


def test_generate_public_games_limits_to_two_games(tmp_path: Path) -> None:
    response = generate_public_games(
        PublicGenerationRequest(first_name="Ana", whatsapp="11999999999", ml_enabled=False),
        db_path=tmp_path / "lotoia.db",
        ip_address="127.0.0.1",
        user_agent="pytest",
        active_limiter=PublicLimiter(cooldown_seconds=0),
    )

    assert len(response["games"]) == 2
    assert response["metadata"]["max_games"] == 2
    assert response["metadata"]["strategy"] == "public_hybrid_statistical_v1"


def test_check_public_contest_is_readonly_and_persists_event(tmp_path: Path) -> None:
    history_path = tmp_path / "history.csv"
    history_path.write_text(
        "concurso,data,d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14,d15\n"
        "100,2026-01-01,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15\n",
        encoding="utf-8",
    )

    response = check_public_contest(
        PublicCheckRequest(
            first_name="Ana",
            whatsapp="11999999999",
            contest_id=100,
            numbers=list(range(1, 16)),
        ),
        db_path=tmp_path / "lotoia.db",
        history_path=history_path,
        active_limiter=PublicLimiter(cooldown_seconds=0),
    )

    assert response["hits"] == 15
    assert response["correct_numbers"] == list(range(1, 16))


def test_public_generate_endpoint_returns_games() -> None:
    status, data = post_json(
        "/api/public/generate",
        {"first_name": "Ana", "whatsapp": "11999999999", "ml_enabled": False},
    )

    assert status == 200
    assert len(data["games"]) == 2
    assert data["metadata"]["max_games"] == 2


def test_public_check_endpoint_validates_numbers() -> None:
    status, data = post_json(
        "/api/public/check",
        {
            "first_name": "Ana",
            "whatsapp": "11999999999",
            "contest_id": 1,
            "numbers": [1, 1, *range(2, 15)],
        },
    )

    assert status == 422
    assert "detail" in data


def test_lead_capture_service_persists_and_deduplicates(tmp_path: Path) -> None:
    service = LeadCaptureService(tmp_path / "lotoia.db")

    first = service.capture(
        LeadCaptureRequest(first_name="  Ana   Maria  ", whatsapp="(11) 99999-9999"),
        ip_address="127.0.0.1",
        user_agent="pytest",
    )
    second = service.capture(
        LeadCaptureRequest(first_name="Ana Maria", whatsapp="11999999999"),
        ip_address="127.0.0.1",
        user_agent="pytest",
    )

    assert first.created is True
    assert first.normalized_whatsapp == "11999999999"
    assert second.created is False
    assert first.lead["id"] == second.lead["id"]
    assert len(first.ip_hash) == 64
