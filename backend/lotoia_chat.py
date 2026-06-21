from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from lotoia.clients.constants import DAILY_LIMIT, PLANS

router = APIRouter(tags=["lotoia-chat"])

_TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "lotoia_chat.html"


def _build_plan_cards_html() -> str:
    config = PLANS["completo"]
    price = float(config["price"])
    cards = [
        f"""
            <label class="plan-card featured">
              <input type="radio" name="plan" value="completo" checked required />
              <span class="plan-badge">Completo</span>
              <strong class="plan-price">R$ {price:,.2f}</strong>
              <span class="plan-meta">7 dias 15D + 12 meses 15D/20D</span>
              <span class="plan-meta">Até {DAILY_LIMIT} jogos/dia</span>
            </label>
            """.strip()
    ]
    return "\n".join(cards)


def render_lotoia_chat_landing() -> str:
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    return template.replace("{{PLAN_CARDS}}", _build_plan_cards_html())


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def lotoia_chat_landing() -> HTMLResponse:
    return HTMLResponse(content=render_lotoia_chat_landing())
