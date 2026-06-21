from fastapi import FastAPI, HTTPException, Request

from lotoia_runtime import ensure_src_layout

ensure_src_layout()

from lotoia.clients.deploy_info import build_deploy_info
from lotoia.config import settings  # noqa: E402
from lotoia.data.loader import DEFAULT_HISTORY_PATH, load_draws_csv  # noqa: E402
from lotoia.database.database import DEFAULT_DATABASE_PATH  # noqa: E402
from lotoia.generator.basic_generator import (  # noqa: E402
    generate_best_games,
    generate_filtered_game,
    generate_multiple_games,
)
from lotoia.public import PublicCheckRequest, PublicGenerationRequest  # noqa: E402
from lotoia.public.service import (  # noqa: E402
    PublicContestNotFoundError,
    PublicRateLimitError,
    check_public_contest,
    generate_public_games,
)
from lotoia.statistics.basic import summarize_draws  # noqa: E402

from backend.asaas_webhook import router as asaas_webhook_router  # noqa: E402
from backend.lotoia_api_router import router as lotoia_api_router  # noqa: E402
from backend.lotoia_chat import router as lotoia_chat_router  # noqa: E402
from backend.messenger_webhook import router as messenger_router  # noqa: E402
from backend.whatsapp import router as whatsapp_router  # noqa: E402

app = FastAPI(
    title=settings.app_name,
    description="API para analises estatisticas da LOTOFACIL.",
    version="0.1.0",
)

app.include_router(lotoia_api_router)
app.include_router(lotoia_chat_router)
app.include_router(whatsapp_router)
app.include_router(messenger_router, prefix="/messenger")
app.include_router(asaas_webhook_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    info = build_deploy_info()
    return {
        "status": "ok",
        "environment": settings.app_env,
        "git_sha": info["git_sha"],
        "resultado_conference": info["resultado_conference"],
    }


@app.get("/analyses/summary")
def analysis_summary() -> dict[str, object]:
    try:
        draws = load_draws_csv(DEFAULT_HISTORY_PATH)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=(
                "Arquivo historico da LOTOFACIL nao encontrado. "
                f"Coloque o CSV em {DEFAULT_HISTORY_PATH}."
            ),
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return summarize_draws(draws)


@app.get("/generate/game")
def generate_game() -> dict[str, object]:
    try:
        return generate_filtered_game()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Erro ao gerar jogo filtrado.") from exc


@app.get("/generate/games")
def generate_games(count: int = 10, max_repeated: int = 9) -> dict[str, object]:
    try:
        games = generate_multiple_games(count=count, max_repeated=max_repeated)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Erro ao gerar jogos filtrados.") from exc

    return {"count": len(games), "games": games}


@app.get("/generate/best-games")
def generate_best_games_endpoint(count: int = 10, pool_size: int = 30) -> dict[str, object]:
    try:
        return generate_best_games(count=count, pool_size=pool_size)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Erro ao gerar melhores jogos.") from exc


@app.post("/api/public/generate")
def public_generate(payload: PublicGenerationRequest, request: Request) -> dict[str, object]:
    try:
        return generate_public_games(
            payload,
            db_path=DEFAULT_DATABASE_PATH,
            ip_address=_client_host(request),
            user_agent=request.headers.get("user-agent", ""),
            source="public_api",
        )
    except PublicRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Erro ao gerar jogos publicos.") from exc


@app.post("/api/public/check")
def public_check(payload: PublicCheckRequest, request: Request) -> dict[str, object]:
    try:
        return check_public_contest(
            payload,
            db_path=DEFAULT_DATABASE_PATH,
            ip_address=_client_host(request),
            user_agent=request.headers.get("user-agent", ""),
            source="public_api",
        )
    except PublicRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except PublicContestNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Erro ao conferir concurso.") from exc


def _client_host(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()
    return request.client.host if request.client else ""
