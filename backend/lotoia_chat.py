from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from lotoia.clients.constants import DAILY_LIMIT, PLANS

router = APIRouter(tags=["lotoia-chat"])

_TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "lotoia_chat.html"

_PLAN_LABELS: dict[str, str] = {
    "basico": "Básico",
    "plus": "Plus",
    "avancado": "Avançado",
    "pro": "Pro",
    "master": "Master",
    "elite": "Elite",
}


def _build_plan_cards_html() -> str:
    cards: list[str] = []
    for index, (plan_key, config) in enumerate(PLANS.items()):
        price = float(config["price"])
        formato_max = int(config["formato_max"])
        label = _PLAN_LABELS.get(plan_key, plan_key.title())
        featured = " featured" if plan_key == "pro" else ""
        checked = " checked" if plan_key == "pro" else ""
        cards.append(
            f"""
            <label class="plan-card{featured}">
              <input type="radio" name="plan" value="{plan_key}"{checked} required />
              <span class="plan-badge">{label}</span>
              <strong class="plan-price">R$ {price:,.2f}</strong>
              <span class="plan-meta">Até {formato_max}D no WhatsApp</span>
              <span class="plan-meta">Até {DAILY_LIMIT} jogos/dia</span>
            </label>
            """.strip()
        )
    return "\n".join(cards)


def render_lotoia_chat_landing() -> str:
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    return template.replace("{{PLAN_CARDS}}", _build_plan_cards_html())


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def lotoia_chat_landing() -> HTMLResponse:
    return HTMLResponse(content=render_lotoia_chat_landing())
